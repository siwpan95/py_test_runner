"""
merged_gui 动态测试脚本

尝试运行每个 Python 文件，检查是否能正常启动。
使用超时机制避免卡住。
"""

import subprocess
import sys
import os
import time
from pathlib import Path
from typing import List, Tuple

# merged_gui 目录
# merged_gui 目录（2026-09-23 去本地化：原路径已失效；
# MERGED_GUI_DIR 环境变量优先，默认 <工作区>/notpython/merged_gui）
MERGED_GUI_DIR = Path(os.environ.get("MERGED_GUI_DIR")
                      or (Path(__file__).resolve().parents[3] / "notpython" / "merged_gui"))


def run_with_timeout(py_file: Path, timeout: int = 5) -> Tuple[bool, str, str]:
    """
    在超时限制内运行 Python 文件

    Args:
        py_file: Python 文件路径
        timeout: 超时时间（秒）

    Returns:
        (是否成功, stdout, stderr)
    """
    try:
        # 使用 subprocess 运行，设置超时
        result = subprocess.run(
            [sys.executable, str(py_file)],
            cwd=str(MERGED_GUI_DIR),
            capture_output=True,
            text=True,
            timeout=timeout,
            # 忽略退出码（GUI 程序可能无法正常退出）
            check=False,
        )

        # 判断是否成功
        # 有些程序可能启动后等待用户交互，超时后被杀掉
        # 这种情况我们认为"启动成功"
        if result.returncode == 0:
            return True, result.stdout, result.stderr
        elif result.returncode == -15:  # 被 kill 掉
            return True, result.stdout, "（超时退出，但可能启动成功）"
        else:
            return False, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        # 超时说明程序还在运行（可能启动成功，等待用户交互）
        return True, "", f"（超时 {timeout}s，程序可能正常运行）"

    except Exception as e:
        return False, "", str(e)


def check_gui_imports(py_file: Path) -> List[str]:
    """
    检查文件导入的 GUI 库

    Returns:
        导入的 GUI 库列表
    """
    gui_libs = []
    try:
        with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()

        import ast
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(
                        lib in alias.name.lower()
                        for lib in ["tkinter", "pygame", "qt", "kivy", "wx"]
                    ):
                        gui_libs.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and any(
                    lib in node.module.lower()
                    for lib in ["tkinter", "pygame", "qt", "kivy", "wx"]
                ):
                    gui_libs.append(node.module)

    except Exception:
        pass

    return gui_libs


def main():
    """主函数"""
    print("=" * 70)
    print("🚀 merged_gui 动态测试")
    print("=" * 70)
    print()

    if not MERGED_GUI_DIR.exists():
        print(f"❌ 目录不存在: {MERGED_GUI_DIR}")
        sys.exit(1)

    # 发现所有 Python 文件
    py_files = sorted(MERGED_GUI_DIR.glob("*.py"))
    print(f"发现 {len(py_files)} 个 Python 文件")
    print()

    # 动态测试
    results = []

    for i, py_file in enumerate(py_files, 1):
        print(f"[{i}/{len(py_files)}] 测试: {py_file.name}")

        # 检查 GUI 库导入
        gui_libs = check_gui_imports(py_file)
        if gui_libs:
            print(f"    GUI 库: {', '.join(gui_libs)}")

        # 尝试运行
        print(f"    运行中（超时 5 秒）...", end=" ", flush=True)

        success, stdout, stderr = run_with_timeout(py_file, timeout=5)

        if success:
            print("✅ 启动成功（或超时）")
            if stdout.strip():
                print(f"    stdout: {stdout.strip()[:100]}")
            if stderr.strip():
                print(f"    stderr: {stderr.strip()[:100]}")
            results.append(("成功", py_file.name, ""))
        else:
            print("❌ 启动失败")
            print(f"    stderr: {stderr.strip()[:200]}")
            results.append(("失败", py_file.name, stderr.strip()))

        print()

    # 汇总
    print("=" * 70)
    print("📊 测试汇总")
    print("=" * 70)

    success_count = sum(1 for r in results if r[0] == "成功")
    failed_count = sum(1 for r in results if r[0] == "失败")

    print(f"总文件数: {len(py_files)}")
    print(f"启动成功: {success_count} ✅")
    print(f"启动失败: {failed_count} ❌")
    print()

    if failed_count > 0:
        print("失败文件列表:")
        for status, name, error in results:
            if status == "失败":
                print(f"  ❌ {name}")
                print(f"     错误: {error[:100]}")
        print()

    print("=" * 70)


if __name__ == "__main__":
    main()
