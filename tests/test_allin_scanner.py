"""
测试 allin_scanner 模块的功能。

运行方式：
    python test_allin_scanner.py
"""

import sys
import os

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.log_manager import LogManager
from core.test_probe import ProbeManager
from allin_scanner import register_allin_probes, discover_py_files, check_syntax, ALLIN_ROOT


def main():
    """主测试函数"""
    print("=" * 60)
    print("测试 allin_scanner 模块")
    print("=" * 60)

    # ── 测试 1: 发现 Python 文件 ──
    print("\n[测试 1] 发现 Python 文件")
    print("-" * 60)

    tools_dir = ALLIN_ROOT / "tools" / "py_test_runner"
    py_files = discover_py_files(tools_dir)
    print(f"在 {tools_dir} 中发现 {len(py_files)} 个 Python 文件")

    if py_files:
        print("前 5 个文件:")
        for fp in py_files[:5]:
            print(f"  - {fp.name}")

    # ── 测试 2: 语法检查 ──
    print("\n[测试 2] 语法检查")
    print("-" * 60)

    if py_files:
        for fp in py_files[:5]:
            passed, detail = check_syntax(fp)
            status = "✅" if passed else "❌"
            print(f"{status} {fp.name}: {detail}")

    # ── 测试 3: 注册探针 ──
    print("\n[测试 3] 注册探针")
    print("-" * 60)

    log_manager = LogManager(log_dir=os.path.join(PROJECT_ROOT, "logs"))
    mgr = ProbeManager(log_manager)

    print("正在注册探针...")
    register_allin_probes(mgr, full=False)  # 仅 P1 探针
    print(f"已注册 {mgr.count} 个探针")

    # ── 测试 4: 运行探针（限制数量）──
    print("\n[测试 4] 运行探针（仅前 5 个）")
    print("-" * 60)

    if mgr.count > 0:
        # 仅运行前 5 个探针
        test_probes = mgr._probes[:5]
        print(f"运行 {len(test_probes)} 个探针...")

        results = mgr.run(test_probes)

        # 统计结果
        passed = sum(1 for r in results if r.error_code.category.value == "通过")
        failed = sum(1 for r in results if r.error_code.category.value in ("失败", "错误"))

        print(f"\n结果: {passed} 通过, {failed} 失败")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
