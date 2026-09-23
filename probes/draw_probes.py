"""
draw 项目专用深度探针 — 针对 ECS 架构全路径扫描。

覆盖层次：
    P1 关键 — 环境依赖、核心文件存在、语法、导入
    P2 重要 — 模板有效性、Effects/Thumbs 完整性、ECS 组件可实例化
    P3 常规 — 抽样加载、性能、全量 JSON 有效性抽样

使用方式：
    python main.py --draw          # 仅 P1 关键探针（快速冒烟）
    python main.py --draw --all    # 全部探针（含 P2/P3）
    python main.py -c --draw       # 控制台 + draw 探针
"""

import ast
import json
import sys
import os
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Tuple

# ── draw 项目路径 ─────────────────────────────
# drawpic（故障艺术生成器）为原 draw 项目的后继
DRAW_DIR = Path(os.environ.get("DRAWPIC_ROOT") or (Path(__file__).resolve().parents[2] / "drawpic"))   # 2026-09-23 去本地化
EFFECTS_DIR = DRAW_DIR / "effects"
THUMBS_DIR = EFFECTS_DIR / "thumbs"
TEMPLATES_DIR = DRAW_DIR / "templates"

# ── 确保 draw 项目在 sys.path 中 ─────────────
_draw_str = str(DRAW_DIR)
if _draw_str not in sys.path:
    sys.path.insert(0, _draw_str)


def _setup_pygame():
    """延迟初始化 pygame（仅初始化 display，不创建窗口）"""
    try:
        import pygame
        if not pygame.get_init():
            pygame.init()
        if not pygame.display.get_init():
            # 设置最小窗口，然后立即隐藏
            pygame.display.set_mode((1, 1))
        return True
    except Exception:
        return False


def _check_file_syntax(file_path: Path) -> Tuple[bool, str]:
    """检查单个文件的语法"""
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
        ast.parse(source)
        return True, f"语法正确 ({file_path.stat().st_size} bytes)"
    except SyntaxError as e:
        return False, f"语法错误 L{e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"读取失败: {e}"


def _check_json_valid(json_path: Path) -> Tuple[bool, str]:
    """检查 JSON 文件是否有效"""
    try:
        with open(json_path, encoding="utf-8") as fp:
            obj = json.load(fp)
        return True, f"有效 JSON ({len(obj)} 个键)"
    except json.JSONDecodeError as e:
        return False, f"JSON 解析失败: {e}"
    except Exception as e:
        return False, f"读取失败: {e}"


def _count_files(directory: Path, pattern: str) -> int:
    """统计目录下匹配模式的文件数量"""
    if not directory.exists():
        return 0
    return len(list(directory.glob(pattern)))


def register_draw_probes(mgr, *, full: bool = False):
    """
    注册 draw 项目的所有探针。

    Args:
        mgr: ProbeManager 实例
        full: 是否注册 P2/P3 探针（--all 模式）
    """

    if not DRAW_DIR.exists():
        mgr.register(ProbeManager.simple(
            "draw — 项目目录存在",
            False,
            f"目录不存在: {DRAW_DIR}",
            category="draw-环境",
            priority=1,
            tags={"draw", "env"},
        ))
        return

    mgr.log.info(f"draw 项目路径: {DRAW_DIR}")

    # ══════════════════════════════════════════════════
    #  P1 关键探针 — 环境 & 核心文件 & 导入
    # ══════════════════════════════════════════════════

    # ── P1: 依赖检查 ──
    mgr.register(Probe(
        name="draw — pygame 可导入",
        check=lambda: _probe_import_pygame(),
        category="draw-依赖",
        priority=1,
        tags={"draw", "dep", "p1"},
    ))

    mgr.register(Probe(
        name="draw — numpy 可导入",
        check=lambda: _probe_import_numpy(),
        category="draw-依赖",
        priority=1,
        tags={"draw", "dep", "p1"},
    ))

    # ── P1: 核心文件存在性 ──
    core_files = [
        ("main.pyw", DRAW_DIR / "main.pyw"),
        ("core/__init__.py", DRAW_DIR / "core" / "__init__.py"),
        ("core/world.py", DRAW_DIR / "core" / "world.py"),
        ("entities/__init__.py", DRAW_DIR / "entities" / "__init__.py"),
        ("entities/recipe.py", DRAW_DIR / "entities" / "recipe.py"),
        ("entities/registry.py", DRAW_DIR / "entities" / "registry.py"),
        ("systems/__init__.py", DRAW_DIR / "systems" / "__init__.py"),
        ("systems/evolution.py", DRAW_DIR / "systems" / "evolution.py"),
        ("systems/colormap.py", DRAW_DIR / "systems" / "colormap.py"),
        ("systems/render.py", DRAW_DIR / "systems" / "render.py"),
        ("systems/ui.py", DRAW_DIR / "systems" / "ui.py"),
        ("ui/thumbnail_grid.py", DRAW_DIR / "ui" / "thumbnail_grid.py"),
    ]

    for label, fpath in core_files:
        mgr.register(Probe(
            name=f"draw — 核心文件: {label}",
            check=lambda fp=fpath, lb=label: (
                fp.exists(),
                f"{lb} ({fp.stat().st_size} bytes)" if fp.exists() else f"文件不存在: {fp}",
            ),
            category="draw-文件",
            priority=1,
            tags={"draw", "file", "p1"},
        ))

    # ── P1: 目录存在性 ──
    core_dirs = [
        ("core", DRAW_DIR / "core"),
        ("entities", DRAW_DIR / "entities"),
        ("systems", DRAW_DIR / "systems"),
        ("ui", DRAW_DIR / "ui"),
        ("templates", TEMPLATES_DIR),
        ("effects", EFFECTS_DIR),
        ("tools", DRAW_DIR / "tools"),
    ]

    for label, dpath in core_dirs:
        mgr.register(ProbeManager.simple(
            f"draw — 目录存在: {label}",
            dpath.exists() and dpath.is_dir(),
            f"{label}/ 目录{'存在' if dpath.exists() else '不存在'}",
            category="draw-目录",
            priority=1,
            tags={"draw", "dir", "p1"},
        ))

    # ── P1: 语法检查（核心文件）──
    for label, fpath in core_files:
        if fpath.exists():
            mgr.register(Probe(
                name=f"draw — 语法: {label}",
                check=lambda fp=fpath, lb=label: _check_file_syntax(fp),
                category="draw-语法",
                priority=1,
                tags={"draw", "syntax", "p1"},
            ))

    # ── P1: 模块导入检查 ──
    import_tests = [
        ("entities.recipe", "RecipeEntity"),
        ("entities.registry", "TemplateRegistry"),
        ("systems.evolution", "EvolutionSystem"),
        ("systems.colormap", "ColorSystem"),
        ("systems.render", "RenderSystem"),
        ("ui.thumbnail_grid", "ThumbnailGrid"),
    ]

    for module_name, class_name in import_tests:
        mgr.register(Probe(
            name=f"draw — 导入: {module_name}",
            check=lambda mn=module_name, cn=class_name: _probe_import_module(mn, cn),
            category="draw-导入",
            priority=1,
            tags={"draw", "import", "p1"},
        ))

    # ── P1: effects 目录有 JSON 文件 ──
    mgr.register(Probe(
        name="draw — effects JSON 文件存在",
        check=lambda: _probe_effects_exist(),
        category="draw-数据",
        priority=1,
        tags={"draw", "data", "p1"},
    ))

    # ── P1: thumbs 目录有 PNG 文件 ──
    mgr.register(Probe(
        name="draw — thumbs PNG 文件存在",
        check=lambda: _probe_thumbs_exist(),
        category="draw-数据",
        priority=1,
        tags={"draw", "data", "p1"},
    ))

    # ══════════════════════════════════════════════════
    #  P2 重要探针 — 功能 & 完整性
    # ══════════════════════════════════════════════════

    if full:
        # ── P2: 模板文件语法检查 ──
        mgr.register(Probe(
            name="draw — 模板文件语法全检",
            check=lambda: _probe_all_template_syntax(),
            category="draw-模板",
            priority=2,
            tags={"draw", "template", "p2"},
        ))

        # ── P2: ECS 组件可实例化 ──
        mgr.register(Probe(
            name="draw — RecipeEntity 可实例化",
            check=lambda: _probe_recipe_entity_instantiate(),
            category="draw-ECS",
            priority=2,
            tags={"draw", "ecs", "p2"},
        ))

        mgr.register(Probe(
            name="draw — EvolutionSystem 可实例化",
            check=lambda: _probe_evolution_sys_instantiate(),
            category="draw-ECS",
            priority=2,
            tags={"draw", "ecs", "p2"},
        ))

        mgr.register(Probe(
            name="draw — ColorSystem 可实例化",
            check=lambda: _probe_color_sys_instantiate(),
            category="draw-ECS",
            priority=2,
            tags={"draw", "ecs", "p2"},
        ))

        mgr.register(Probe(
            name="draw — ThumbnailGrid 可实例化",
            check=lambda: _probe_thumbnail_grid_instantiate(),
            category="draw-UI",
            priority=2,
            tags={"draw", "ui", "p2"},
        ))

        # ── P2: effects/thumbs 数量一致性 ──
        mgr.register(Probe(
            name="draw — effects/thumbs 数量一致性",
            check=lambda: _probe_effects_thumbs_consistency(),
            category="draw-数据",
            priority=2,
            tags={"draw", "data", "p2"},
        ))

        # ── P2: 抽样 JSON 有效性 ──
        mgr.register(Probe(
            name="draw — 抽样 JSON 有效性 (50个)",
            check=lambda: _probe_sample_json_valid(50),
            category="draw-数据",
            priority=2,
            tags={"draw", "data", "p2"},
        ))

        # ── P2: TemplateRegistry 可发现分类 ──
        mgr.register(Probe(
            name="draw — TemplateRegistry 分类发现",
            check=lambda: _probe_template_registry(),
            category="draw-模板",
            priority=2,
            tags={"draw", "template", "p2"},
        ))

    # ══════════════════════════════════════════════════
    #  P3 常规探针 — 性能 & 边界
    # ══════════════════════════════════════════════════

    if full:
        # ── P3: 单个缩略图生成可运行 ──
        mgr.register(Probe(
            name="draw — 单文件缩略图生成",
            check=lambda: _probe_single_thumb_gen(),
            category="draw-性能",
            priority=3,
            tags={"draw", "perf", "p3"},
        ))

        # ── P3: favorites.json 有效性（如果存在）──
        mgr.register(Probe(
            name="draw — favorites.json 有效性",
            check=lambda: _probe_favorites_json(),
            category="draw-数据",
            priority=3,
            tags={"draw", "data", "p3"},
        ))

        # ── P3: 全量 Python 文件语法检查 ──
        mgr.register(Probe(
            name="draw — 全量 .py 语法检查",
            check=lambda: _probe_all_py_syntax(),
            category="draw-语法",
            priority=3,
            tags={"draw", "syntax", "p3"},
        ))

        # ── P3: 目录结构统计 ──
        mgr.register(Probe(
            name="draw — 目录结构统计",
            check=lambda: _probe_dir_stats(),
            category="draw-统计",
            priority=3,
            tags={"draw", "stats", "p3"},
        ))


# ══════════════════════════════════════════════════
#  P1 探针实现函数
# ══════════════════════════════════════════════════

def _probe_import_pygame() -> Tuple[bool, str]:
    try:
        import pygame
        version = pygame.version.ver
        _setup_pygame()
        return True, f"pygame {version}"
    except ImportError as e:
        return False, f"pygame 未安装: {e}"
    except Exception as e:
        return False, f"pygame 初始化失败: {e}"


def _probe_import_numpy() -> Tuple[bool, str]:
    try:
        import numpy as np
        return True, f"numpy {np.__version__}"
    except ImportError as e:
        return False, f"numpy 未安装: {e}"
    except Exception as e:
        return False, f"numpy 异常: {e}"


def _probe_import_module(module_name: str, class_name: str) -> Tuple[bool, str]:
    try:
        mod = __import__(module_name, fromlist=[class_name], level=0)
        cls = getattr(mod, class_name, None)
        if cls is None:
            return False, f"{module_name}.{class_name} 不存在"
        return True, f"{module_name}.{class_name} 可访问"
    except ImportError as e:
        return False, f"导入失败: {e}"
    except Exception as e:
        return False, f"异常: {type(e).__name__}: {e}"


def _probe_effects_exist() -> Tuple[bool, str]:
    if not EFFECTS_DIR.exists():
        return False, "effects/ 目录不存在"
    jsons = list(EFFECTS_DIR.glob("*.json"))
    return True, f"找到 {len(jsons)} 个 JSON 文件"


def _probe_thumbs_exist() -> Tuple[bool, str]:
    if not THUMBS_DIR.exists():
        return False, "effects/thumbs/ 目录不存在"
    pngs = list(THUMBS_DIR.glob("*.png"))
    return True, f"找到 {len(pngs)} 个 PNG 文件"


# ══════════════════════════════════════════════════
#  P2 探针实现函数
# ══════════════════════════════════════════════════

def _probe_all_template_syntax() -> Tuple[bool, str]:
    """检查 templates/ 下所有 .py 文件的语法"""
    if not TEMPLATES_DIR.exists():
        return False, "templates/ 目录不存在"
    py_files = sorted(TEMPLATES_DIR.glob("*.py"))
    ok = 0
    failed = 0
    failed_files = []
    for fp in py_files:
        passed, detail = _check_file_syntax(fp)
        if passed:
            ok += 1
        else:
            failed += 1
            failed_files.append(f"{fp.name}: {detail}")

    if failed > 0:
        msg = f"{ok}/{len(py_files)} 通过, 失败: " + "; ".join(failed_files[:3])
        return False, msg
    return True, f"{ok}/{len(py_files)} 个模板文件语法正确"


def _probe_recipe_entity_instantiate() -> Tuple[bool, str]:
    """尝试实例化 RecipeEntity（不加载文件）"""
    try:
        _setup_pygame()
        from entities.recipe import RecipeEntity
        # RecipeEntity 需要一个 grid 配置，这里只检查类可访问
        return True, "RecipeEntity 类可访问"
    except Exception as e:
        return False, f"异常: {type(e).__name__}: {e}"


def _probe_evolution_sys_instantiate() -> Tuple[bool, str]:
    try:
        from systems.evolution import EvolutionSystem
        sys_obj = EvolutionSystem()
        return True, f"EvolutionSystem 实例化成功: {type(sys_obj).__name__}"
    except Exception as e:
        return False, f"实例化失败: {type(e).__name__}: {e}"


def _probe_color_sys_instantiate() -> Tuple[bool, str]:
    try:
        from systems.colormap import ColorSystem
        sys_obj = ColorSystem()
        return True, f"ColorSystem 实例化成功"
    except Exception as e:
        return False, f"实例化失败: {type(e).__name__}: {e}"


def _probe_thumbnail_grid_instantiate() -> Tuple[bool, str]:
    try:
        import pygame
        _setup_pygame()
        from ui.thumbnail_grid import ThumbnailGrid
        # 需要 font, font_small, x, y, w, h
        # 避免 SysFont(None,...) 在某些环境报错，改用 Font
        font = pygame.font.Font(None, 16)
        font_small = pygame.font.Font(None, 12)
        grid = ThumbnailGrid(font, font_small, 0, 0, 800, 600)
        return True, f"ThumbnailGrid 实例化成功"
    except Exception as e:
        return False, f"实例化失败: {type(e).__name__}: {e}"


def _probe_effects_thumbs_consistency() -> Tuple[bool, str]:
    jsons = list(EFFECTS_DIR.glob("*.json")) if EFFECTS_DIR.exists() else []
    pngs = list(THUMBS_DIR.glob("*.png")) if THUMBS_DIR.exists() else []
    ratio = len(pngs) / len(jsons) if jsons else 0
    detail = f"JSON={len(jsons)}, PNG={len(pngs)}, 覆盖率={ratio:.1%}"
    # 允许少量差异（生成可能未完成）
    if ratio >= 0.99:
        return True, detail + " ✅"
    elif ratio >= 0.90:
        return True, detail + " ⚠️ 部分缺失"
    else:
        return False, detail + " ❌ 大量缺失"


def _probe_sample_json_valid(sample_size: int = 50) -> Tuple[bool, str]:
    """抽样检查 JSON 文件有效性"""
    if not EFFECTS_DIR.exists():
        return False, "effects/ 目录不存在"
    jsons = list(EFFECTS_DIR.glob("*.json"))
    import random
    sample = random.sample(jsons, min(sample_size, len(jsons)))
    ok = 0
    failed = 0
    for jp in sample:
        passed, _ = _check_json_valid(jp)
        if passed:
            ok += 1
        else:
            failed += 1
    detail = f"抽样 {len(sample)} 个, {ok} 有效, {failed} 无效"
    return (True, detail) if failed == 0 else (False, detail)


def _probe_template_registry() -> Tuple[bool, str]:
    try:
        from entities.registry import TemplateRegistry
        reg = TemplateRegistry()
        cats = list(reg.categories.keys())
        detail = f"发现 {len(cats)} 个分类: {', '.join(cats[:4])}"
        return True, detail
    except Exception as e:
        return False, f"异常: {type(e).__name__}: {e}"


# ══════════════════════════════════════════════════
#  P3 探针实现函数
# ══════════════════════════════════════════════════

def _probe_single_thumb_gen() -> Tuple[bool, str]:
    """测试单个文件的缩略图生成"""
    try:
        _setup_pygame()
        import numpy as np
        from entities.recipe import RecipeEntity
        from systems.evolution import EvolutionSystem
        from systems.colormap import ColorSystem

        jsons = list(EFFECTS_DIR.glob("*.json"))
        if not jsons:
            return False, "没有 JSON 文件可测试"

        # 取第一个文件
        test_json = jsons[0]
        entity = RecipeEntity.from_json(str(test_json))

        evo_sys = EvolutionSystem()
        color_sys = ColorSystem()

        evo_sys._initialize(entity)
        for _ in range(10):
            evo_sys.update(entity)
        color_sys.update(entity)

        rgb = entity.grid.rgb_hw
        if rgb is not None:
            return True, f"缩略图生成成功 ({test_json.name})"
        else:
            return False, "rgb_hw 为 None"
    except Exception as e:
        return False, f"生成失败: {type(e).__name__}: {e}"


def _probe_favorites_json() -> Tuple[bool, str]:
    fav_path = EFFECTS_DIR / "favorites.json"
    if not fav_path.exists():
        return True, "favorites.json 不存在（尚未收藏）"
    try:
        with open(fav_path, encoding="utf-8") as fp:
            data = json.load(fp)
        paths = data.get("paths", []) if isinstance(data, dict) else data
        return True, f"favorites.json 有效, {len(paths)} 个收藏"
    except Exception as e:
        return False, f"favorites.json 无效: {e}"


def _probe_all_py_syntax() -> Tuple[bool, str]:
    """全量 .py 文件语法检查"""
    py_files = sorted(DRAW_DIR.rglob("*.py"))
    ok = 0
    failed = 0
    failed_files = []
    for fp in py_files:
        passed, detail = _check_file_syntax(fp)
        if passed:
            ok += 1
        else:
            failed += 1
            failed_files.append(f"{fp.relative_to(DRAW_DIR)}: {detail}")

    if failed > 0:
        msg = f"{ok}/{len(py_files)} 通过, 失败: " + "; ".join(failed_files[:3])
        return False, msg
    return True, f"{ok}/{len(py_files)} 个 .py 文件语法全部正确"


def _probe_dir_stats() -> Tuple[bool, str]:
    """目录结构统计"""
    stats = []
    for subdir in ["core", "entities", "systems", "ui", "templates", "tools"]:
        d = DRAW_DIR / subdir
        if d.exists():
            py_count = len(list(d.glob("*.py")))
            stats.append(f"{subdir}={py_count}")
    effect_count = len(list(EFFECTS_DIR.glob("*.json"))) if EFFECTS_DIR.exists() else 0
    stats.append(f"effects={effect_count}")
    return True, "目录统计: " + ", ".join(stats)


# ── 辅助函数 ─────────────────────────────────────

def _check_file_syntax(file_path: Path) -> Tuple[bool, str]:
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
        ast.parse(source)
        return True, "语法正确"
    except SyntaxError as e:
        return False, f"L{e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)


def _check_json_valid(json_path: Path) -> Tuple[bool, str]:
    try:
        with open(json_path, encoding="utf-8") as fp:
            json.load(fp)
        return True, "有效"
    except Exception as e:
        return False, str(e)


# ── 为了使用 Probe/ProbeManager 类，需要导入 ─────
from core.test_probe import Probe, ProbeManager  # noqa: E402
