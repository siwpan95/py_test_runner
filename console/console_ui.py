"""
控制台测试界面 — 纯终端交互模式。

适用场景：
    - CI/CD 流水线
    - 无 GUI 环境
    - 脚本自动化
"""

import sys
import os
from typing import List, Callable

# 强制 stdout 使用 UTF-8，避免 emoji 等字符在 GBK 下报错
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from core.log_manager import LogManager
from core.test_runner import TestRunner
from core.error_types import ErrorCode


class ConsoleUI:
    """控制台测试界面"""

    def __init__(self, log_manager: LogManager):
        self.log = log_manager
        self.runner = TestRunner(log_manager)

    def print_banner(self):
        """打印启动横幅"""
        banner = r"""
   ╔══════════════════════════════════════════════════╗
   ║            🧪  测试框架  v1.0                     ║
   ║            Console Mode                         ║
   ╚══════════════════════════════════════════════════╝
        """
        self.log.print_colored(banner, bold=True)

    def run(self, test_fns: List[Callable], timeout: float = 30.0):
        """执行测试套件"""
        self.print_banner()
        self.runner.timeout = timeout

        try:
            results = self.runner.run_tests(test_fns)
            self.log.print_summary()

            # 返回退出码
            has_failure = any(
                r.error_code.category.value in ("失败", "错误")
                for r in results
            )
            if has_failure:
                self.log.print_colored("⚠️  有测试未通过！", bold=True)
                return 1
            else:
                self.log.print_colored("✅ 全部测试通过！", bold=True)
                return 0

        except KeyboardInterrupt:
            self.log.print_colored("\n⚠️  测试被用户中断", bold=True)
            return 2
        except Exception as e:
            self.log.print_colored(f"\n💥 测试框架崩溃: {e}", bold=True)
            import traceback
            traceback.print_exc()
            return 3
