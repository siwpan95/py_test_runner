"""
测试运行器 — 核心测试执行引擎。

架构：
    TestRunner 接收测试用例列表，按顺序执行，捕获所有异常，
    并将结果通过 LogManager 输出。

支持特性：
    - setUp / tearDown 生命周期
    - 超时控制（独立线程 + join 超时）
    - 异常自动归类
    - 执行时间统计
"""

import time
import traceback
import threading
from typing import List, Callable, Optional, Any

from .error_types import ErrorCode, TestError, ErrorCategory
from .log_manager import LogManager


class TestRunner:
    """测试执行引擎"""

    def __init__(self, log_manager: LogManager, timeout: float = 30.0):
        """
        Args:
            log_manager: 日志管理器
            timeout: 单个测试超时时间（秒）
        """
        self.log = log_manager
        self.timeout = timeout
        self._setup_fn: Optional[Callable] = None
        self._teardown_fn: Optional[Callable] = None

    # ── 生命周期钩子 ──
    def set_setup(self, fn: Callable):
        """设置 setUp：每个测试前执行"""
        self._setup_fn = fn

    def set_teardown(self, fn: Callable):
        """设置 tearDown：每个测试后执行"""
        self._teardown_fn = fn

    # ── 测试执行 ──
    def run_test(self, test_fn: Callable) -> TestError:
        """执行单个测试函数，返回 TestError 对象"""
        test_name = test_fn.__name__
        start_time = time.perf_counter()

        # ── setUp ──
        if self._setup_fn:
            try:
                self._setup_fn()
            except Exception as e:
                return self._create_error(
                    ErrorCode.SETUP_ERROR,
                    f"setUp 失败: {e}",
                    test_name,
                )

        # ── 执行测试（带超时控制）──
        exception_info = [None]  # 用列表在线程间传递异常
        done_event = threading.Event()

        def _runner():
            try:
                test_fn()
            except AssertionError as e:
                exception_info[0] = ("assert", e)
            except Exception as e:
                exception_info[0] = ("exception", e)
            finally:
                done_event.set()

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()

        finished = done_event.wait(timeout=self.timeout)

        if not finished:
            # 超时：线程会在 daemon 模式下随进程结束
            return self._create_error(
                ErrorCode.TIMEOUT_ERROR,
                f"测试超时（>{self.timeout}s）",
                test_name,
            )

        # ── tearDown ──
        if self._teardown_fn:
            try:
                self._teardown_fn()
            except Exception as e:
                self.log.warning(f"tearDown 异常: {e}")

        # ── 检查结果 ──
        err = exception_info[0]

        if err is None:
            # 通过
            duration = time.perf_counter() - start_time
            return TestError(
                error_code=ErrorCode.TEST_PASS,
                message=f"通过 ({duration:.3f}s)",
                test_name=test_name,
            )
        else:
            err_type, err_value = err
            if err_type == "assert":
                error_code = ErrorCode.from_exception(err_value)
                return self._create_error(
                    error_code,
                    str(err_value) or "断言失败",
                    test_name,
                )
            else:
                error_code = ErrorCode.from_exception(err_value)
                return self._create_error(
                    error_code,
                    f"{type(err_value).__name__}: {err_value}",
                    test_name,
                )

    def run_tests(self, test_fns: List[Callable]) -> List[TestError]:
        """批量执行测试

        Ctrl+C 处理：中断后保留已完成结果，打印部分汇总。
        """
        results = []
        total = len(test_fns)

        self.log.section(f"开始执行 {total} 个测试")
        self.log.info(f"超时设置: {self.timeout}s / 每个测试")

        run_start = time.perf_counter()

        try:
            for i, test_fn in enumerate(test_fns, 1):
                test_name = test_fn.__name__
                self.log.info(f"[{i}/{total}] 执行: {test_name}")

                result = self.run_test(test_fn)
                self.log.print_result(result.error_code, test_name)
                self.log.error(result)
                results.append(result)

        except KeyboardInterrupt:
            remaining = total - len(results)
            self.log.section("⚠️  用户中断 (Ctrl+C)")
            self.log.warning(f"已执行 {len(results)}/{total} 个测试，剩余 {remaining} 个未执行")
            self.log.print_colored(f"\n⚠️  用户中断 — 已执行 {len(results)}/{total} 个测试", bold=True)

        total_time = time.perf_counter() - run_start
        self.log.info(f"全部测试完成，耗时 {total_time:.2f}s")

        return results

    # ── 辅助 ──
    def _create_error(
        self,
        error_code: ErrorCode,
        message: str,
        test_name: str,
    ) -> TestError:
        tb = traceback.format_exc()
        return TestError(
            error_code=error_code,
            message=message,
            test_name=test_name,
            traceback=tb if tb and "NoneType" not in tb else None,
        )
