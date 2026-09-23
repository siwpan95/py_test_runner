"""
OK 测试对象库 — 全量项目探针生成器。

自动扫描 D:\\allin\\not\\OK 下所有项目，
为每个项目生成语法检查 + 导入检查探针。

探针分类：
    P1 关键 ─ 项目存在、有 .py 文件、入口文件语法正确
    P2 快速 ─ 模块可导入（仅 complex 项目）
    P3 常规 ─ 文件数量统计、目录结构
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Tuple

from core.test_probe import Probe, ProbeManager
from core.error_types import ErrorCode

OK_DIR = Path(os.environ.get("SCAN_ROOT") or Path(__file__).resolve().parents[2])   # 2026-09-23 去本地化（原 D:\allin\not\OK → G:\tools 均已失效）


def discover_projects() -> List[Path]:
    """发现 OK 目录下所有有效项目"""
    projects = []
    for entry in sorted(OK_DIR.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("__"):
            continue
        # 跳过空目录（同时检查 .py 和 .pyw）
        py_files = list(entry.glob("*.py")) + list(entry.glob("*.pyw"))
        if not py_files and not any(entry.iterdir()):
            continue
        projects.append(entry)
    return projects


def find_entry_file(project_dir: Path) -> Path:
    """找到一个项目的入口 .py / .pyw 文件"""
    # main.py / main.pyw 优先
    for entry_name in ("main.py", "main.pyw"):
        entry = project_dir / entry_name
        if entry.exists():
            return entry

    # 找同名 .py / .pyw 文件
    for ext in (".py", ".pyw"):
        name_entry = project_dir / f"{project_dir.name}{ext}"
        if name_entry.exists():
            return name_entry

    # 找任意 .py / .pyw 文件（优先级：.pyw > .py，预防某些 GUI 项目）
    all_py = sorted(project_dir.glob("*.pyw")) + sorted(project_dir.glob("*.py"))
    if all_py:
        return all_py[0]

    return None


def classify_project(project_dir: Path) -> Tuple[str, int]:
    """分类项目：类型 + .py/.pyw 文件数量"""
    py_count = len(list(project_dir.rglob("*.py"))) + len(list(project_dir.rglob("*.pyw")))
    subdirs = [d for d in project_dir.iterdir() if d.is_dir() and not d.name.startswith("__")]

    if py_count == 1:
        return "单文件", py_count
    elif py_count <= 10 and len(subdirs) <= 3:
        return "小型", py_count
    elif py_count <= 50 and len(subdirs) <= 10:
        return "中型", py_count
    else:
        return "大型", py_count


def check_syntax(file_path: Path) -> Tuple[bool, str]:
    """语法检查 — 用 ast.parse 验证"""
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
        ast.parse(source)
        return True, "语法正确"
    except SyntaxError as e:
        return False, f"语法错误 L{e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"读取失败: {e}"


def check_import(project_dir: Path) -> Tuple[bool, str]:
    """导入检查 — 尝试作为包导入（仅含 __init__.py 的项目）"""
    init = project_dir / "__init__.py"
    if not init.exists():
        return True, "跳过（非包结构）"

    # 把 OK 父目录加入路径
    parent = str(project_dir.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)

    try:
        mod = __import__(project_dir.name)
        return True, f"导入成功 ({len(dir(mod))} 个属性)"
    except ImportError as e:
        return False, f"导入失败: {e}"
    except Exception as e:
        return False, f"导入异常: {type(e).__name__}: {e}"


def register_ok_probes(mgr: ProbeManager):
    """为 OK 库全部项目注册探针"""

    projects = discover_projects()
    mgr.log.info(f"发现 {len(projects)} 个测试对象")

    for proj_dir in projects:
        name = proj_dir.name
        ptype, py_count = classify_project(proj_dir)

        # ── P1: 存在性探针 ──
        mgr.register(ProbeManager.simple(
            f"OK/{name} — 目录存在",
            proj_dir.is_dir(),
            f"类型={ptype}, py文件={py_count}",
            category="存在性",
            priority=1,
            tags={"ok", "exist"},
        ))

        # ── P1: 入口文件探针 ──
        entry = find_entry_file(proj_dir)
        if entry:
            mgr.register(Probe(
                name=f"OK/{name} — 入口文件",
                check=lambda ep=entry, pn=name: (
                    ep.exists(),
                    f"入口: {ep.name} ({ep.stat().st_size} bytes)",
                ),
                category="语法",
                priority=1,
                tags={"ok", "entry"},
            ))

            # ── P1: 语法检查 ──
            mgr.register(Probe(
                name=f"OK/{name} — 语法",
                check=lambda ep=entry, pn=name: check_syntax(ep),
                category="语法",
                priority=1,
                tags={"ok", "syntax"},
            ))
        else:
            mgr.register(ProbeManager.simple(
                f"OK/{name} — 入口文件",
                False,
                "无 .py 文件",
                category="语法",
                priority=1,
                tags={"ok", "entry"},
            ))

        # ── P2: 导入检查（仅复杂项目）──
        if ptype in ("中型", "大型"):
            mgr.register(Probe(
                name=f"OK/{name} — 导入",
                check=lambda pd=proj_dir, pn=name: check_import(pd),
                category="导入",
                priority=2,
                tags={"ok", "import"},
            ))

    mgr.log.info(f"已注册 {mgr.count} 个探针点（{len(projects)} 个项目 x 3-4 探针/项目）")
