"""
冒烟测试探针用例 — 通过探针快速验证系统核心功能。

使用方式：
    python main.py --smoke       # 仅冒烟探针（priority=1）
    python main.py --smoke --all # 全部探针

探针 vs 测试用例的区别：
    探针是只读检查点，无副作用。适合：
    - 部署后快速验证
    - CI/CD 流水线第一道关卡
    - 核心模块健康检查

    测试用例可以执行任意操作，适合：
    - 功能正确性验证
    - 边界条件测试
    - 回归测试
"""

import os
import sys
import math
from pathlib import Path

from core.test_probe import Probe, ProbeManager


def register_probes(mgr: ProbeManager):
    """注册全部冒烟测试探针"""

    # ═══════════════════════════════════════════════════
    #  🔥  Priority 1 — 关键冒烟探针（必须全部通过）
    # ═══════════════════════════════════════════════════

    mgr.register(ProbeManager.simple(
        "Python 版本检查",
        sys.version_info >= (3, 8),
        f"Python {sys.version}",
        category="环境",
        priority=1,
        tags={"env", "startup"},
    ))

    mgr.register(ProbeManager.simple(
        "工作目录可访问",
        os.access(os.getcwd(), os.R_OK),
        f"cwd={os.getcwd()}",
        category="环境",
        priority=1,
        tags={"env", "startup"},
    ))

    mgr.register(Probe(
        name="数学库正常",
        check=lambda: (math.sqrt(4) == 2.0, "sqrt(4) = 2.0"),
        category="核心",
        priority=1,
        tags={"core", "startup"},
    ))

    mgr.register(ProbeManager.simple(
        "日志目录存在",
        Path("logs").exists(),
        "logs/ 目录可访问",
        category="文件系统",
        priority=1,
        tags={"fs", "startup"},
    ))

    # ── 路径存在性探针 ──
    mgr.register(ProbeManager.simple(
        "main.py 存在",
        Path("main.py").exists(),
        "入口文件正常",
        category="文件系统",
        priority=1,
        tags={"fs"},
    ))

    mgr.register(ProbeManager.simple(
        "core 模块存在",
        Path("core").is_dir(),
        "核心模块目录正常",
        category="文件系统",
        priority=1,
        tags={"fs"},
    ))

    mgr.register(ProbeManager.simple(
        "gui 模块存在",
        Path("gui").is_dir(),
        "GUI 模块目录正常",
        category="文件系统",
        priority=1,
        tags={"fs"},
    ))

    # ═══════════════════════════════════════════════════
    #  Priority 2 — 快速验证探针
    # ═══════════════════════════════════════════════════

    mgr.register(Probe(
        name="字符串操作",
        check=lambda: (
            "Hello World" == "Hello" + " " + "World",
            "字符串拼接正常",
        ),
        category="核心",
        priority=2,
        tags={"core"},
    ))

    mgr.register(Probe(
        name="列表操作",
        check=lambda: (
            [1, 2, 3] + [4, 5] == [1, 2, 3, 4, 5],
            "列表拼接正常",
        ),
        category="核心",
        priority=2,
        tags={"core"},
    ))

    mgr.register(Probe(
        name="字典操作",
        check=lambda: (
            {"a": 1, "b": 2}.get("a") == 1,
            "字典取值正常",
        ),
        category="核心",
        priority=2,
        tags={"core"},
    ))

    mgr.register(Probe(
        name="模块导入: error_types",
        check=lambda: (
            __import__("core.error_types", fromlist=["ErrorCode"]) is not None,
            "error_types 模块可导入",
        ),
        category="导入",
        priority=2,
        tags={"import"},
    ))

    mgr.register(Probe(
        name="模块导入: test_runner",
        check=lambda: (
            __import__("core.test_runner", fromlist=["TestRunner"]) is not None,
            "test_runner 模块可导入",
        ),
        category="导入",
        priority=2,
        tags={"import"},
    ))

    mgr.register(Probe(
        name="模块导入: log_manager",
        check=lambda: (
            __import__("core.log_manager", fromlist=["LogManager"]) is not None,
            "log_manager 模块可导入",
        ),
        category="导入",
        priority=2,
        tags={"import"},
    ))

    mgr.register(Probe(
        name="模块导入: canvas_view",
        check=lambda: (
            __import__("gui.canvas_view", fromlist=["CanvasTestView"]) is not None,
            "canvas_view 模块可导入",
        ),
        category="导入",
        priority=2,
        tags={"import"},
    ))

    # ═══════════════════════════════════════════════════
    #  Priority 3 — 常规探针（可选）
    # ═══════════════════════════════════════════════════

    mgr.register(ProbeManager.simple(
        "test_cases.py 存在",
        Path("test_cases.py").exists(),
        "测试用例文件存在",
        category="文件系统",
        priority=3,
        tags={"fs"},
    ))

    mgr.register(ProbeManager.simple(
        "运行测试.bat 存在",
        Path("运行测试.bat").exists(),
        "启动脚本存在",
        category="文件系统",
        priority=3,
        tags={"fs"},
    ))

    # ── 故意失败的探针（演示用）──

    mgr.register(ProbeManager.simple(
        "【演示-失败】不存在的文件",
        Path("不存在的文件.txt").exists(),
        "文件不应存在",
        category="文件系统",
        priority=3,
        tags={"demo", "fail"},
    ))

    mgr.register(ProbeManager.simple(
        "【演示-失败】错误的断言",
        1 == 2,
        "这个探针必然失败",
        category="核心",
        priority=3,
        tags={"demo", "fail"},
    ))

    # 异常探针：check 函数本身抛异常
    def _will_crash():
        return 1 / 0

    mgr.register(Probe(
        name="【演示-失败】异常探针",
        check=_will_crash,
        category="核心",
        priority=3,
        tags={"demo", "fail"},
    ))

    # ── 环境探针细节 ──

    mgr.register(Probe(
        name="Python 路径信息",
        check=lambda: (
            "python" in sys.executable.lower(),
            f"Python: {sys.executable}",
        ),
        category="环境",
        priority=3,
        tags={"env"},
    ))

    mgr.register(Probe(
        name="编码检查",
        check=lambda: (
            sys.getdefaultencoding() == "utf-8",
            f"默认编码: {sys.getdefaultencoding()}",
        ),
        category="环境",
        priority=3,
        tags={"env"},
    ))
