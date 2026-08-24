"""
全项目扫描器 — 对 D:\\allin 下所有 Python 文件进行全覆盖测试。

扫描层次：
    P1 关键 — 文件存在性、语法检查、编码检查
    P2 重要 — 导入检查、依赖分析、文件大小异常检测
    P3 常规 — 目录结构统计、重复文件检测、复杂度分析

使用方式：
    python main.py --allin          # 仅 P1 关键扫描（快速）
    python main.py --allin --all    # 全部扫描（含 P2/P3）
    python main.py -c --allin       # 控制台 + 全项目扫描

设计原则：
    - 只读检查，无副作用
    - 递归扫描，自动发现所有 .py 文件
    - 分类统计，按目录维度汇总
    - 异常容忍，单文件失败不影响整体
"""

import ast
import os
import sys
import json
import hashlib
import time
from pathlib import Path
from typing import List, Tuple, Dict, Set, Optional
from collections import defaultdict

# ── 项目根目录 ─────────────────────────────
# 原 D:\allin 项目已失效，默认改为 G:\tools 工具箱根目录
ALLIN_ROOT = Path(r"G:\tools")

# ── 需要扫描的目录 ─────────────────────────
SCAN_DIRS = [
    ALLIN_ROOT / "ai",
    ALLIN_ROOT / "audio",
    ALLIN_ROOT / "crawler",
    ALLIN_ROOT / "dev",
    ALLIN_ROOT / "desktop",
    ALLIN_ROOT / "game",
    ALLIN_ROOT / "visual",
]

# ── 排除的目录/文件模式 ─────────────────────
EXCLUDE_PATTERNS = {
    "__pycache__",
    ".git",
    ".pytest_cache",
    "node_modules",
    ".vscode",
    ".idea",
}


def discover_py_files(scan_dir: Path) -> List[Path]:
    """递归发现目录下所有 .py 文件"""
    py_files = []
    if not scan_dir.exists():
        return py_files

    for root, dirs, files in os.walk(scan_dir):
        # 过滤排除目录
        dirs[:] = [d for d in dirs if d not in EXCLUDE_PATTERNS]

        for file in files:
            if file.endswith(".py"):
                py_files.append(Path(root) / file)
            elif file.endswith(".pyw"):
                py_files.append(Path(root) / file)

    return sorted(py_files)


def check_syntax(file_path: Path) -> Tuple[bool, str]:
    """语法检查 — 用 ast.parse 验证"""
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
        ast.parse(source)
        return True, "语法正确"
    except SyntaxError as e:
        line = e.lineno if e.lineno else "?"
        return False, f"语法错误 L{line}: {e.msg}"
    except UnicodeDecodeError as e:
        return False, f"编码错误: {e}"
    except Exception as e:
        return False, f"解析失败: {type(e).__name__}: {e}"


def check_encoding(file_path: Path) -> Tuple[bool, str]:
    """编码检查 — 验证文件编码"""
    try:
        content = file_path.read_text(encoding="utf-8")
        return True, f"UTF-8 ({len(content)} 字符)"
    except UnicodeDecodeError:
        # 尝试其他编码
        for enc in ["gbk", "gb2312", "latin-1"]:
            try:
                content = file_path.read_text(encoding=enc)
                return False, f"非 UTF-8 编码 (推测 {enc})"
            except UnicodeDecodeError:
                continue
        return False, "无法识别的编码"
    except Exception as e:
        return False, f"读取失败: {e}"


def check_file_size(file_path: Path, *, warn_kb: int = 100) -> Tuple[bool, str]:
    """文件大小检查 — 检测异常大文件"""
    try:
        size_bytes = file_path.stat().st_size
        size_kb = size_bytes / 1024
        if size_kb > warn_kb:
            return False, f"文件过大: {size_kb:.1f}KB"
        return True, f"{size_kb:.1f}KB"
    except Exception as e:
        return False, f"统计失败: {e}"


def try_import_module(file_path: Path, project_root: Path) -> Tuple[bool, str]:
    """尝试导入模块"""
    try:
        # 计算模块导入路径
        rel_path = file_path.relative_to(project_root)
        module_parts = []
        for part in rel_path.parts:
            if part.endswith(".py"):
                module_name = part[:-3]
                if module_name != "__init__":
                    module_parts.append(module_name)
            elif part.endswith(".pyw"):
                module_name = part[:-4]
                module_parts.append(module_name)
            else:
                module_parts.append(part)

        if not module_parts:
            return True, "跳过（__init__.py 或根模块）"

        module_dot_path = ".".join(module_parts)

        # 临时添加到 sys.path
        project_str = str(project_root)
        if project_str not in sys.path:
            sys.path.insert(0, project_str)

        # 尝试导入
        __import__(module_dot_path, fromlist=["__name__"], level=0)
        return True, f"导入成功: {module_dot_path}"

    except ImportError as e:
        return False, f"导入失败: {e}"
    except SyntaxError as e:
        return False, f"语法错误: {e}"
    except Exception as e:
        return False, f"导入异常: {type(e).__name__}: {e}"


def analyze_imports(file_path: Path) -> Tuple[List[str], str]:
    """分析文件中的 import 语句"""
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)

        return imports, f"发现 {len(imports)} 个导入"

    except Exception as e:
        return [], f"分析失败: {e}"


def calculate_file_hash(file_path: Path) -> str:
    """计算文件哈希（用于重复检测）"""
    try:
        content = file_path.read_bytes()
        return hashlib.md5(content).hexdigest()
    except Exception:
        return ""


def register_allin_probes(mgr, *, full: bool = False):
    """
    注册全项目扫描探针。

    Args:
        mgr: ProbeManager 实例
        full: 是否注册 P2/P3 探针（--all 模式）
    """

    # ── 发现所有需要扫描的目录 ──
    scan_targets = []
    for scan_dir in SCAN_DIRS:
        if scan_dir.exists():
            scan_targets.append(scan_dir)
            mgr.log.info(f"扫描目标: {scan_dir}")
        else:
            mgr.log.warning(f"目录不存在: {scan_dir}")

    if not scan_targets:
        mgr.register(ProbeManager.simple(
            "allin — 扫描目标存在",
            False,
            "没有可扫描的目录",
            category="allin-环境",
            priority=1,
            tags={"allin", "env"},
        ))
        return

    # ── 发现所有 Python 文件 ──
    all_py_files = []
    for target in scan_targets:
        py_files = discover_py_files(target)
        all_py_files.extend(py_files)
        mgr.log.info(f"  {target.name}: {len(py_files)} 个 Python 文件")

    mgr.log.info(f"总计发现 {len(all_py_files)} 个 Python 文件")

    # ══════════════════════════════════════════════════
    #  P1 关键探针 — 文件存在性 & 语法 & 编码
    # ══════════════════════════════════════════════════

    mgr.register(ProbeManager.simple(
        "allin — Python 文件总数",
        len(all_py_files) > 0,
        f"发现 {len(all_py_files)} 个 Python 文件",
        category="allin-统计",
        priority=1,
        tags={"allin", "stats"},
    ))

    # ── P1: 语法检查（分批，每批 100 个文件）──
    batch_size = 100
    file_batches = [
        all_py_files[i:i + batch_size]
        for i in range(0, len(all_py_files), batch_size)
    ]

    for batch_idx, batch in enumerate(file_batches):
        mgr.register(Probe(
            name=f"allin — 语法检查 (批次 {batch_idx + 1}/{len(file_batches)})",
            check=lambda b=batch, bi=batch_idx: _check_batch_syntax(b, bi),
            category="allin-语法",
            priority=1,
            tags={"allin", "syntax", "p1"},
        ))

    # ── P1: 编码检查（抽样）──
    sample_size = min(200, len(all_py_files))
    import random
    sample_files = random.sample(all_py_files, sample_size) if all_py_files else []

    mgr.register(Probe(
        name=f"allin — 编码检查 (抽样 {sample_size} 个文件)",
        check=lambda s=sample_files: _check_batch_encoding(s),
        category="allin-编码",
        priority=1,
        tags={"allin", "encoding", "p1"},
    ))

    # ══════════════════════════════════════════════════
    #  P2 重要探针 — 导入 & 依赖分析
    # ══════════════════════════════════════════════════

    if full:
        # ── P2: 导入检查（仅项目根目录的 __init__.py 或 main.py）──
        for target in scan_targets:
            entry_points = [
                target / "main.py",
                target / "main.pyw",
                target / "__init__.py",
            ]
            for ep in entry_points:
                if ep.exists():
                    mgr.register(Probe(
                        name=f"allin — 导入: {ep.relative_to(ALLIN_ROOT)}",
                        check=lambda e=ep, t=target: try_import_module(e, t),
                        category="allin-导入",
                        priority=2,
                        tags={"allin", "import", "p2"},
                    ))

        # ── P2: 依赖分析（抽样）──
        mgr.register(Probe(
            name="allin — 依赖分析 (抽样 50 个文件)",
            check=lambda f=all_py_files: _analyze_batch_imports(f[:50]),
            category="allin-依赖",
            priority=2,
            tags={"allin", "dep", "p2"},
        ))

        # ── P2: 文件大小异常检测 ──
        mgr.register(Probe(
            name="allin — 文件大小检查",
            check=lambda f=all_py_files: _check_batch_file_size(f),
            category="allin-文件",
            priority=2,
            tags={"allin", "file", "p2"},
        ))

    # ══════════════════════════════════════════════════
    #  P3 常规探针 — 统计分析
    # ══════════════════════════════════════════════════

    if full:
        # ── P3: 目录结构统计 ──
        mgr.register(Probe(
            name="allin — 目录结构统计",
            check=lambda: _stats_directory_structure(),
            category="allin-统计",
            priority=3,
            tags={"allin", "stats", "p3"},
        ))

        # ── P3: 重复文件检测 ──
        mgr.register(Probe(
            name="allin — 重复文件检测 (抽样)",
            check=lambda f=all_py_files: _detect_duplicate_files(f[:500]),
            category="allin-质量",
            priority=3,
            tags={"allin", "quality", "p3"},
        ))


# ══════════════════════════════════════════════════
#  探针实现函数
# ══════════════════════════════════════════════════

def _check_batch_syntax(py_files: List[Path], batch_idx: int) -> Tuple[bool, str]:
    """检查一批文件的语法"""
    ok = 0
    failed = 0
    failed_files = []

    for fp in py_files:
        passed, detail = check_syntax(fp)
        if passed:
            ok += 1
        else:
            failed += 1
            rel_path = fp.relative_to(ALLIN_ROOT)
            failed_files.append(f"{rel_path}: {detail}")

    total = len(py_files)
    if failed > 0:
        msg = f"{ok}/{total} 通过; 失败: " + "; ".join(failed_files[:3])
        return False, msg

    return True, f"{ok}/{total} 个文件语法正确"


def _check_batch_encoding(py_files: List[Path]) -> Tuple[bool, str]:
    """检查一批文件的编码"""
    utf8_count = 0
    non_utf8_count = 0
    issues = []

    for fp in py_files:
        passed, detail = check_encoding(fp)
        if passed:
            utf8_count += 1
        else:
            non_utf8_count += 1
            if len(issues) < 3:
                rel_path = fp.relative_to(ALLIN_ROOT)
                issues.append(f"{rel_path}: {detail}")

    total = len(py_files)
    if non_utf8_count > 0:
        msg = f"UTF-8: {utf8_count}/{total}, 非 UTF-8: {non_utf8_count}; "
        msg += "; ".join(issues)
        return False, msg

    return True, f"{utf8_count}/{total} 个文件编码为 UTF-8"


def _analyze_batch_imports(py_files: List[Path]) -> Tuple[bool, str]:
    """分析一批文件的导入依赖"""
    all_imports = []
    failed = 0

    for fp in py_files:
        imports, detail = analyze_imports(fp)
        if imports:
            all_imports.extend(imports)
        else:
            failed += 1

    # 统计最常见的导入
    from collections import Counter
    import_counter = Counter(all_imports)
    top_imports = import_counter.most_common(5)

    detail = f"分析 {len(py_files)} 个文件, 发现 {len(all_imports)} 个导入; "
    detail += "最常见: " + ", ".join(f"{imp}({cnt})" for imp, cnt in top_imports)

    return True, detail


def _check_batch_file_size(py_files: List[Path]) -> Tuple[bool, str]:
    """检查一批文件的大小"""
    large_files = []
    total_size = 0

    for fp in py_files:
        passed, detail = check_file_size(fp, warn_kb=100)
        if not passed:
            rel_path = fp.relative_to(ALLIN_ROOT)
            large_files.append(f"{rel_path}: {detail}")

        try:
            total_size += fp.stat().st_size
        except Exception:
            pass

    total_size_kb = total_size / 1024
    detail = f"总大小: {total_size_kb:.1f}KB, "

    if large_files:
        detail += f"大文件: {len(large_files)} 个; "
        detail += "; ".join(large_files[:3])
        return False, detail

    return True, detail + f"无异常大文件"


def _stats_directory_structure() -> Tuple[bool, str]:
    """统计目录结构"""
    stats = {}

    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue

        py_count = len(list(scan_dir.rglob("*.py")))
        pyw_count = len(list(scan_dir.rglob("*.pyw")))
        subdirs = len([d for d in scan_dir.rglob("*") if d.is_dir()])

        stats[scan_dir.name] = f"py={py_count}, pyw={pyw_count}, dirs={subdirs}"

    detail = "目录统计: " + "; ".join(f"{k}({v})" for k, v in stats.items())
    return True, detail


def _detect_duplicate_files(py_files: List[Path]) -> Tuple[bool, str]:
    """检测重复文件（基于内容哈希）"""
    hash_map = defaultdict(list)

    for fp in py_files:
        file_hash = calculate_file_hash(fp)
        if file_hash:
            hash_map[file_hash].append(fp)

    duplicates = {h: files for h, files in hash_map.items() if len(files) > 1}

    if duplicates:
        dup_examples = []
        for h, files in list(duplicates.items())[:3]:
            rel_paths = [fp.relative_to(ALLIN_ROOT) for fp in files]
            dup_examples.append(f"{rel_paths[0]} (+{len(files) - 1} 个重复)")

        msg = f"发现 {len(duplicates)} 组重复文件; "
        msg += "; ".join(dup_examples)
        return False, msg

    return True, f"抽样 {len(py_files)} 个文件，未发现重复"


# ── 导入 Probe/ProbeManager ─────────────────────────
from core.test_probe import Probe, ProbeManager  # noqa: E402
