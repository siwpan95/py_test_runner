"""
测试框架入口 — 支持 GUI 模式、Console 模式和探针模式。

用法：
    python main.py                  # 默认 GUI 模式
    python main.py --console        # 控制台模式
    python main.py -c               # 控制台模式（简写）
    python main.py --smoke          # 冒烟探针测试（仅 priority=1 关键探针）
    python main.py --smoke --all    # 全部探针
    python main.py -c --smoke       # 控制台 + 冒烟探针
    python main.py --ok             # OK 测试对象库全量扫描
    python main.py -c --ok          # 控制台 + OK 库扫描
    python main.py --draw            # draw 项目深度扫描
    python main.py --allin          # 全项目扫描 G:\tools
    python main.py -c --allin       # 控制台 + 全项目扫描
    python main.py --timeout 10     # 设置超时（秒）
    python main.py --demo           # 仅运行演示套件（5个测试）

项目结构：
    core/           — 核心引擎（错误类型、日志、测试运行器、探针系统）
    gui/            — tkinter Canvas 图形界面
    console/        — 控制台界面
    scanners/       — 扫描器（全项目扫描、架构检测、动态测试）
    probes/         — 探针定义（冒烟探针、OK库探针、draw项目探针）
    reports/        — 报告生成器（HTML/JSON报告、覆盖率分析）
    tests/          — 测试脚本和用例
    docs/           — 文档
    logs/           — 日志输出目录
"""

import sys
import os
import argparse
import signal
import time
from pathlib import Path
from typing import List, Optional

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ── 全局 Ctrl+C 信号处理 ──
_sigint_received = False


def _on_sigint(signum, frame):
    global _sigint_received
    _sigint_received = True
    # 第一次 Ctrl+C：温和提示
    # 第二次 Ctrl+C：系统默认行为会杀掉进程
    print("\n⚠️  收到中断信号 (Ctrl+C)，正在安全退出...", flush=True)
    print("   再按一次 Ctrl+C 将强制退出", flush=True)
    # 恢复默认信号处理器，第二次 Ctrl+C 会直接杀掉进程
    signal.signal(signal.SIGINT, signal.SIG_DFL)

signal.signal(signal.SIGINT, _on_sigint)

# ── 条件导入 GUI 模块（处理无头环境）──
try:
    from gui.canvas_view import CanvasTestView
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    CanvasTestView = None

from core.log_manager import LogManager
from core.test_runner import TestRunner
from core.test_probe import ProbeManager
from console.console_ui import ConsoleUI
from tests.test_cases import ALL_TESTS, PASSING_TESTS, DEMO_TESTS
from probes.probe_cases import register_probes
from probes.ok_probes import register_ok_probes
from probes.draw_probes import register_draw_probes
from scanners.allin_scanner import register_allin_probes
from scanners.architecture_detector import ArchitectureDetector, print_architecture_report
from scanners.dynamic_tester import DynamicTester


def parse_args():
    parser = argparse.ArgumentParser(
        description="测试框架 — tkinter Canvas / Console / 探针 多模式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                    GUI 模式（默认）
  python main.py -c                 控制台模式
  python main.py --smoke            冒烟探针（仅关键路径）
  python main.py --smoke --all      全部探针
  python main.py -c --smoke         控制台 + 冒烟探针
  python main.py --console --demo   控制台 + 演示套件
  python main.py -t 60              超时 60 秒
        """,
    )
    parser.add_argument(
        "-c", "--console",
        action="store_true",
        help="使用控制台模式（默认 GUI 模式）",
    )
    parser.add_argument(
        "-t", "--timeout",
        type=float,
        default=30.0,
        help="单个测试超时时间（秒），默认 30",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="仅运行演示套件（5 个测试 + 3 个演示探针）",
    )
    parser.add_argument(
        "--passing",
        action="store_true",
        help="仅运行通过测试（不含失败/错误演示）",
    )
    # ── 探针参数 ──
    parser.add_argument(
        "--smoke", "--probe",
        action="store_true",
        dest="smoke",
        help="探针模式：运行测试探针进行冒烟测试",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="（配合 --smoke）运行全部探针，而非仅关键探针",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        metavar="CAT",
        help="（配合 --smoke）仅运行指定分类的探针，如: 环境、核心、文件系统、导入",
    )
    parser.add_argument(
        "--priority",
        type=int,
        default=None,
        metavar="N",
        help="（配合 --smoke）仅运行优先级 <= N 的探针",
    )
    # ── OK 库参数 ──
    parser.add_argument(
        "--ok",
        action="store_true",
        help="扫描 D:\\allin\\not\\OK 测试对象库全部项目",
    )
    parser.add_argument(
        "--ok-p1",
        action="store_true",
        help="（配合 --ok）仅 P1 关键探针（存在性+语法）",
    )
    parser.add_argument(
        "--draw",
        action="store_true",
        help="扫描 draw 项目（专用深度探针）",
    )
    parser.add_argument(
        "--draw-p1",
        action="store_true",
        help="（配合 --draw）仅 P1 关键探针（环境+文件+导入）",
    )
    # ── 全项目扫描参数 ──
    parser.add_argument(
        "--allin",
        action="store_true",
        help="全项目扫描 D:\\allin（语法+编码+导入+统计）",
    )
    parser.add_argument(
        "--allin-p1",
        action="store_true",
        help="（配合 --allin）仅 P1 关键探针（语法+编码）",
    )
    # ── 架构模式检测参数 ──
    parser.add_argument(
        "--arch",
        "--architecture",
        action="store_true",
        dest="architecture",
        help="扫描项目架构模式（MVC/MVVM/分层/事件驱动等）",
    )
    parser.add_argument(
        "--arch-detail",
        action="store_true",
        dest="arch_detail",
        help="（配合 --arch）显示详细的架构检测结果和文件列表",
    )
    # ── 动态测试参数 ──
    parser.add_argument(
        "--dynamic",
        action="store_true",
        help="动态测试：尝试导入并运行 Python 文件，检查是否能正常启动 GUI",
    )
    parser.add_argument(
        "--dynamic-timeout",
        type=int,
        default=10,
        metavar="SEC",
        help="（配合 --dynamic）动态测试超时时间（秒），默认 10",
    )
    parser.add_argument(
        "--dynamic-python",
        type=str,
        default=None,
        metavar="PATH",
        help="（配合 --dynamic）指定 Python 解释器路径（默认自动检测）",
    )
    parser.add_argument(
        "--dynamic-parallel",
        action="store_true",
        dest="dynamic_parallel",
        help="（配合 --dynamic）并行执行动态测试（多进程加速）",
    )
    parser.add_argument(
        "--dynamic-workers",
        type=int,
        default=4,
        metavar="N",
        help="（配合 --dynamic-parallel）并行进程数，默认 4",
    )
    parser.add_argument(
        "--dynamic-incremental",
        action="store_true",
        dest="dynamic_incremental",
        help="（配合 --dynamic）增量扫描：跳过未变更的文件（基于 mtime+hash 缓存）",
    )
    # ── 简单测试模式 ──
    parser.add_argument(
        "--simple",
        action="store_true",
        help="简单测试模式：仅编译目标目录下的 Python 文件并校验 JSON 文件",
    )
    parser.add_argument(
        "--simple-target",
        type=str,
        default=None,
        metavar="PATH",
        help="（配合 --simple）指定目标目录，默认当前项目根目录",
    )

    return parser.parse_args()


def run_probes(log_manager: LogManager, args):
    """探针模式"""
    mgr = ProbeManager(log_manager)
    register_probes(mgr)

    # 选择探针集
    if args.category:
        probes = mgr.filter(category=args.category)
    elif args.priority is not None:
        probes = mgr.filter(max_priority=args.priority)
    elif args.all:
        probes = None  # 全部
    else:
        probes = mgr.smoke_probes()  # 默认仅关键探针

    label = (f"分类={args.category}" if args.category else
             f"优先级<={args.priority}" if args.priority else
             "全部探针" if args.all else
             "冒烟探针（P1 关键路径）")

    log_manager.section(f"📍 探针模式 — {label}")
    results = mgr.run(probes)
    log_manager.print_summary()

    has_failure = any(
        r.error_code.category.value in ("失败", "错误")
        for r in results
    )
    return 1 if has_failure else 0


def run_ok_probes(log_manager: LogManager, args):
    """OK 测试对象库全量扫描"""
    mgr = ProbeManager(log_manager)
    register_ok_probes(mgr)

    if args.ok_p1:
        probes = mgr.filter(max_priority=1)
        label = "P1 关键探针"
    elif args.category:
        probes = mgr.filter(category=args.category)
        label = f"分类={args.category}"
    else:
        probes = None
        label = "全量探针"

    total = mgr.count
    log_manager.section(f"🔬 OK 测试对象库扫描 — {label}")
    log_manager.info(f"目标目录: D:\\allin\\not\\OK")
    log_manager.info(f"探针总数: {total}")

    results = mgr.run(probes)

    # 分组汇总
    passed = sum(1 for r in results if r.error_code.category.value == "通过")
    failed = sum(1 for r in results if r.error_code.category.value in ("失败", "错误"))

    log_manager.print_summary()

    # 失败明细
    failures = [r for r in results if r.error_code.category.value in ("失败", "错误")]
    if failures:
        log_manager.section("失败/错误明细")
        for r in failures:
            log_manager.print_colored(f"  {r.brief()}", r.error_code.category)

    return 1 if failed > 0 else 0


def run_draw_probes(log_manager: LogManager, args):
    """draw 项目专用深度探针"""
    full = args.all  # --all 时运行 P2/P3 探针
    label = "全量探针（P1+P2+P3）" if full else "P1 关键探针"
    log_manager.section(f"🎨 draw 项目深度扫描 — {label}")

    mgr = ProbeManager(log_manager)
    register_draw_probes(mgr, full=full)

    total = mgr.count
    log_manager.info(f"探针总数: {total}")

    if args.draw_p1:
        probes = mgr.filter(max_priority=1)
        label = "P1 关键探针"
    elif args.category:
        probes = mgr.filter(category=args.category)
        label = f"分类={args.category}"
    elif not full:
        probes = mgr.filter(max_priority=1)
        label = "P1 关键探针（默认）"
    else:
        probes = None
        label = "全量探针"

    log_manager.info(f"执行范围: {label}")

    results = mgr.run(probes)

    passed = sum(1 for r in results if r.error_code.category.value == "通过")
    failed = sum(1 for r in results if r.error_code.category.value in ("失败", "错误"))

    log_manager.print_summary()

    failures = [r for r in results if r.error_code.category.value in ("失败", "错误")]
    if failures:
        log_manager.section("失败/错误明细")
        for r in failures[:10]:
            log_manager.print_colored(f"  {r.brief()}", r.error_code.category)
        if len(failures) > 10:
            log_manager.info(f"  ... 还有 {len(failures) - 10} 个失败（略）")

    return 1 if failed > 0 else 0


def run_allin_probes(log_manager: LogManager, args):
    """全项目扫描 D:\\allin"""
    full = args.all  # --all 时运行 P2/P3 探针
    label = "全量探针（P1+P2+P3）" if full else "P1 关键探针"
    log_manager.section(f"🌍 全项目扫描 — {label}")

    mgr = ProbeManager(log_manager)
    register_allin_probes(mgr, full=full)

    total = mgr.count
    log_manager.info(f"探针总数: {total}")

    if args.allin_p1:
        probes = mgr.filter(max_priority=1)
        label = "P1 关键探针"
    elif args.category:
        probes = mgr.filter(category=args.category)
        label = f"分类={args.category}"
    elif not full:
        probes = mgr.filter(max_priority=1)
        label = "P1 关键探针（默认）"
    else:
        probes = None
        label = "全量探针"

    log_manager.info(f"执行范围: {label}")

    results = mgr.run(probes)

    # 分组汇总
    passed = sum(1 for r in results if r.error_code.category.value == "通过")
    failed = sum(1 for r in results if r.error_code.category.value in ("失败", "错误"))

    log_manager.print_summary()

    # 失败明细
    failures = [r for r in results if r.error_code.category.value in ("失败", "错误")]
    if failures:
        log_manager.section("失败/错误明细")
        for r in failures[:20]:
            log_manager.print_colored(f"  {r.brief()}", r.error_code.category)
        if len(failures) > 20:
            log_manager.info(f"  ... 还有 {len(failures) - 20} 个失败（略）")

    # 保存结果到 JSON
    result_file = os.path.join(PROJECT_ROOT, "logs", f"allin_scan_{int(time.time())}.json")
    try:
        import json
        result_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_probes": total,
            "passed": passed,
            "failed": failed,
            "results": [
                {
                    "name": r.test_name,
                    "status": r.error_code.category.value,
                    "message": r.message,
                }
                for r in results
            ],
        }
        with open(result_file, "w", encoding="utf-8") as fp:
            json.dump(result_data, fp, ensure_ascii=False, indent=2)
        log_manager.info(f"扫描结果已保存: {result_file}")
    except Exception as e:
        log_manager.warning(f"保存结果失败: {e}")

    return 1 if failed > 0 else 0


def run_gui(log_manager: LogManager, test_fns, timeout: float):
    """启动 tkinter Canvas GUI 模式"""
    if not GUI_AVAILABLE:
        log_manager.warning("tkinter 不可用，切换到控制台模式")
        return run_console(log_manager, test_fns, timeout)

    import tkinter as tk

    root = tk.Tk()
    view = CanvasTestView(root, log_manager)

    # 组装运行逻辑
    def on_run():
        if view._running:
            return
        view.set_running(True)
        runner = TestRunner(log_manager, timeout=timeout)

        def _run():
            results = runner.run_tests(test_fns)
            root.after(0, lambda: _on_done(results))

        import threading
        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def _on_done(results):
        view.set_running(False)
        summary = log_manager.get_summary()
        view.update_stats(summary)
        log_manager.print_summary()

    def on_view_log():
        summary = log_manager.get_summary()
        log_path = summary.get("log_path", "")
        if log_path and os.path.exists(log_path):
            os.startfile(log_path)

    view.set_callbacks(on_run=on_run, on_view_log=on_view_log)

    test_names = ", ".join(f.__name__ for f in test_fns[:5])
    if len(test_fns) > 5:
        test_names += f" ... 共 {len(test_fns)} 个"

    log_manager.info(f"GUI 模式启动，加载 {len(test_fns)} 个测试用例")
    log_manager.info(f"测试列表: {test_names}")
    view.set_status(f"已加载 {len(test_fns)} 个测试")

    view.run()


def run_console(log_manager: LogManager, test_fns, timeout: float):
    """控制台模式"""
    ui = ConsoleUI(log_manager)
    exit_code = ui.run(test_fns, timeout=timeout)
    return exit_code


def run_architecture_detection(log_manager: LogManager, args):
    """
    架构模式检测模式

    扫描项目并识别使用的软件架构模式：
    - UI/前端架构: MVC, MVP, MVVM, MVI, MVU, VIPER
    - 系统架构: 分层架构, 六边形架构, 微服务, 事件驱动, 微内核
    - 业务架构: CQRS, 事件溯源, DDD
    """
    log_manager.section("🏗️  架构模式检测")

    project_root = Path(os.environ.get("SCAN_ROOT") or Path(__file__).resolve().parent.parent)   # 2026-09-23 去本地化（原 D:/allin）
    log_manager.info(f"项目路径: {project_root}")

    if not project_root.exists():
        log_manager.error(f"项目路径不存在: {project_root}")
        return 1

    # 创建检测器
    detector = ArchitectureDetector(project_root)

    # 扫描项目
    log_manager.info("开始扫描项目架构模式...")
    report = detector.scan_project()

    # 打印报告
    detector.print_report()

    # 如果指定了详细模式，显示更多细节
    if args.arch_detail:
        log_manager.section("📝 详细架构检测结果")

        for pattern_info in report.get("patterns_detected", []):
            pattern_name = pattern_info["pattern"]
            confidence = pattern_info["confidence"]
            files_count = pattern_info["files_count"]

            log_manager.info(f"\n→ {pattern_name} (置信度: {confidence})")
            log_manager.info(f"  涉及文件数: {files_count}")

            # 显示部分文件名
            file_patterns = report.get("file_patterns", {})
            matched_files = [
                f for f, patterns in file_patterns.items()
                if pattern_name in patterns
            ]

            if matched_files:
                log_manager.info(f"  示例文件:")
                for file_str in matched_files[:5]:
                    log_manager.info(f"    - {file_str}")

    # 导出报告
    try:
        output_path = Path(PROJECT_ROOT) / "logs" / "architecture_report.json"
        output_path.parent.mkdir(exist_ok=True)
        detector.export_report(output_path)
        log_manager.info(f"\n📄 详细报告已保存: {output_path}")
    except Exception as e:
        log_manager.warning(f"导出报告失败: {e}")

    return 0


def collect_target_dirs(targets_str: str) -> List[Path]:
    """
    解析 --targets 参数，返回去重且存在的目录列表

    Args:
        targets_str: 逗号分隔的目录路径列表

    Returns:
        目录路径列表（去重、排序）
    """
    dirs_set: set = set()
    dirs_list: List[Path] = []

    for d in targets_str.split(","):
        d = d.strip()
        if not d:
            continue
        p = Path(d)
        if not p.exists():
            print(f"  ⚠️  目录不存在，跳过: {d}")
            continue
        resolved = p.resolve()
        if resolved not in dirs_set:
            dirs_set.add(resolved)
            dirs_list.append(resolved)

    return sorted(dirs_list, key=lambda p: str(p).lower())


def collect_target_files(targets_str: str) -> List[Path]:
    """
    解析 --targets 参数，收集所有目标目录中的 .py 文件（递归）

    Args:
        targets_str: 逗号分隔的目录路径列表

    Returns:
        Python 文件路径列表（去重、排序）
    """
    files: List[Path] = []
    seen: set = set()

    for d in collect_target_dirs(targets_str):
        py_files = list(d.rglob("*.py"))
        py_files = [f for f in py_files if f.name != "__init__.py"]
        for f in py_files:
            resolved = f.resolve()
            if resolved not in seen:
                seen.add(resolved)
                files.append(resolved)

    return sorted(files, key=lambda p: str(p).lower())


def run_dynamic_tests(log_manager: LogManager, args):
    """
    动态测试模式

    尝试导入并运行 Python 文件，检查是否能正常启动 GUI。
    会自动检测系统 Python（通常有 tkinter）。

    支持并行执行（--dynamic-parallel）和增量扫描（--dynamic-incremental）。
    支持 --targets 指定目标目录列表（逗号分隔）。
    """
    log_manager.section("🚀 Dynamic Test")
    
    # 确定待测目录列表
    if args.targets:
        target_dirs = collect_target_dirs(args.targets)
        if not target_dirs:
            log_manager.error("未在指定目录中找到任何有效目录")
            return 1
        log_manager.info(f"指定目标目录数: {len(target_dirs)}")
    else:
        target_dirs = [Path(PROJECT_ROOT)]
        log_manager.info(f"项目路径: {PROJECT_ROOT}")
    
    log_manager.info(f"超时时间: {args.dynamic_timeout} 秒")
    
    if args.dynamic_python:
        log_manager.info(f"使用指定的 Python: {args.dynamic_python}")
    
    if getattr(args, 'dynamic_parallel', False):
        workers = getattr(args, 'dynamic_workers', 4)
        log_manager.info(f"并行执行: ON ({workers} 进程)")
    
    if getattr(args, 'dynamic_incremental', False):
        log_manager.info(f"增量扫描: ON (跳过未变更文件)")
    
    # 预先收集所有文件（避免循环中重复计算）
    all_files: Optional[List[Path]] = None
    if args.targets:
        all_files = collect_target_files(args.targets)

    # 对每个目标目录单独运行 DynamicTester
    all_results: List[DynamicTestResult] = []
    start_time = time.time()
    
    for i, target_dir in enumerate(target_dirs, 1):
        log_manager.section(f"[{i}/{len(target_dirs)}] 测试: {target_dir.name}")
        
        tester = DynamicTester(
            project_path=str(target_dir),
            python_path=args.dynamic_python,
            timeout=args.dynamic_timeout,
            workers=1,
        )
        
        # 收集当前目录（含子目录）中的文件
        dir_files: Optional[List[Path]] = None
        if all_files is not None:
            dir_files = [f for f in all_files if target_dir in f.parents]
        else:
            dir_files = None
        
        dir_results = tester.run_tests(
            file_paths=dir_files,
            parallel=getattr(args, 'dynamic_parallel', False),
            incremental=getattr(args, 'dynamic_incremental', False),
        )
        all_results.extend(dir_results)
    
    elapsed_time = time.time() - start_time
    
    # 打印汇总报告
    log_manager.section("📊 汇总报告")
    import_success = sum(1 for r in all_results if r.import_success)
    gui_success   = sum(1 for r in all_results if r.gui_start_success)
    total = len(all_results)

    log_manager.info(f"总文件数       : {total}")
    if total > 0:
        log_manager.info(f"导入成功       : {import_success} ({import_success/total*100:.1f}%)")
        log_manager.info(f"GUI 启动成功   : {gui_success} ({gui_success/total*100:.1f}%)")
    else:
        log_manager.info("导入成功       : N/A")
        log_manager.info("GUI 启动成功   : N/A")

    # 导入失败的文件
    failures = [r for r in all_results if not r.import_success]
    if failures:
        log_manager.section("导入失败的文件")
        for r in failures:
            try:
                rel_path = Path(r.file_path).relative_to(Path(os.environ.get("SCAN_ROOT") or Path(__file__).resolve().parent.parent))   # 2026-09-23 去本地化
            except ValueError:
                rel_path = Path(r.file_path).name
            log_manager.print_colored(f"  X {rel_path} -- {r.import_error}", "错误")

    # 导出结果
    try:
        output_path = Path(PROJECT_ROOT) / "logs" / "dynamic_test_report.json"
        output_path.parent.mkdir(exist_ok=True)
        result_data = [r.__dict__ for r in all_results]
        import json
        with open(output_path, "w", encoding="utf-8") as fp:
            json.dump(result_data, fp, ensure_ascii=False, indent=2)
        log_manager.info(f"\n  📄 详细报告已保存: {output_path}")
    except Exception as e:
        log_manager.warning(f"导出报告失败: {e}")

    log_manager.info(f"\n  ⏱️  总耗时: {elapsed_time:.2f} 秒")

    return 0 if import_success == total else 1


def run_simple_tests(log_manager: LogManager, args):
    """
    简单测试模式

    对目标目录进行快速健康检查：
      - 编译所有 .py 文件
      - 解析所有 .json 文件
    适合快速验证单个项目的语法和基础数据合法性。
    """
    target = args.simple_target or os.getcwd()
    target_path = Path(target)

    if not target_path.exists():
        log_manager.error(f"目标目录不存在: {target}")
        return 1

    log_manager.section(f"🔧 简单测试模式 — {target_path}")

    py_compile_results = []
    json_results = []

    # 编译所有 .py 文件
    py_files = list(target_path.rglob("*.py"))
    log_manager.info(f"发现 Python 文件: {len(py_files)} 个")
    for f in py_files:
        try:
            import py_compile
            py_compile.compile(str(f), doraise=True)
            py_compile_results.append((str(f), True, None))
        except Exception as e:
            py_compile_results.append((str(f), False, str(e)))

    # 解析所有 .json 文件
    json_files = list(target_path.rglob("*.json"))
    log_manager.info(f"发现 JSON 文件: {len(json_files)} 个")
    for f in json_files:
        try:
            import json
            with open(f, "r", encoding="utf-8") as fp:
                json.load(fp)
            json_results.append((str(f), True, None))
        except Exception as e:
            json_results.append((str(f), False, str(e)))

    # 汇总
    py_failures = [r for r in py_compile_results if not r[1]]
    json_failures = [r for r in json_results if not r[1]]
    total_failures = len(py_failures) + len(json_failures)

    log_manager.info(f"Python 编译通过: {len(py_compile_results) - len(py_failures)}/{len(py_compile_results)}")
    log_manager.info(f"JSON 解析通过: {len(json_results) - len(json_failures)}/{len(json_results)}")

    if py_failures:
        log_manager.section("Python 编译失败")
        for path, _, err in py_failures[:20]:
            log_manager.print_colored(f"  X {path}\n     {err}", "错误")
        if len(py_failures) > 20:
            log_manager.info(f"  ... 还有 {len(py_failures) - 20} 个失败")

    if json_failures:
        log_manager.section("JSON 解析失败")
        for path, _, err in json_failures[:20]:
            log_manager.print_colored(f"  X {path}\n     {err}", "错误")
        if len(json_failures) > 20:
            log_manager.info(f"  ... 还有 {len(json_failures) - 20} 个失败")

    if total_failures == 0:
        log_manager.print_colored("\n✅ 简单测试通过", "通过")
    else:
        log_manager.print_colored(f"\n❌ 简单测试失败：共 {total_failures} 个问题", "错误")

    return 0 if total_failures == 0 else 1


def main():
    args = parse_args()
    log_manager = LogManager(log_dir=os.path.join(PROJECT_ROOT, "logs"))

    # ── GUI 不可用提示 ──
    if not args.console and not GUI_AVAILABLE:
        log_manager.warning("tkinter 不可用，自动切换到控制台模式")
        args.console = True

    # ── 架构模式检测 ──
    if args.architecture:
        exit_code = run_architecture_detection(log_manager, args)
        sys.exit(exit_code)

    # ── 动态测试模式 ──
    if args.dynamic:
        exit_code = run_dynamic_tests(log_manager, args)
        sys.exit(exit_code)

    # ── 全项目扫描模式 ──
    if args.allin:
        exit_code = run_allin_probes(log_manager, args)
        sys.exit(exit_code)

    # ── OK 库扫描模式 ──
    if args.ok:
        exit_code = run_ok_probes(log_manager, args)
        sys.exit(exit_code)

    # ── draw 项目扫描模式 ──
    if args.draw:
        exit_code = run_draw_probes(log_manager, args)
        sys.exit(exit_code)

    # ── 探针模式 ──
    if args.smoke:
        exit_code = run_probes(log_manager, args)
        sys.exit(exit_code)

    # ── 简单测试模式 ──
    if args.simple:
        exit_code = run_simple_tests(log_manager, args)
        sys.exit(exit_code)

    # ── 测试模式 ──
    if args.demo:
        test_fns = DEMO_TESTS
    elif args.passing:
        test_fns = PASSING_TESTS
    else:
        test_fns = ALL_TESTS

    if args.console:
        exit_code = run_console(log_manager, test_fns, args.timeout)
        sys.exit(exit_code)
    else:
        run_gui(log_manager, test_fns, args.timeout)


if __name__ == "__main__":
    main()
