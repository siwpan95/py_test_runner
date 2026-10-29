"""
对 merged_gui 项目进行动态测试（使用系统 Python + tkinter）
"""
import subprocess
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError

# 系统 Python 路径
SYSTEM_PYTHON = r"python"

# 项目路径
# 原路径已失效，改为动态测试本工具自身代码
PROJECT_PATH = Path(__file__).resolve().parents[1]

# 超时时间（秒）
TIMEOUT = 5


def test_file_import(file_path: Path) -> dict:
    """测试文件是否能成功导入"""
    result = {
        "file": file_path.name,
        "import_success": False,
        "import_error": None,
        "runtime_error": None,
    }

    try:
        # 使用系统 Python 测试导入
        # 注意：这里的命令字符串中的 { 和 } 需要转义
        cmd_str = """
import sys
sys.path.insert(0, r'{project_path}')
try:
    import {module_name}
    print('IMPORT_SUCCESS')
except ImportError as e:
    print('IMPORT_ERROR: ' + str(e))
except Exception as e:
    print('RUNTIME_ERROR: ' + type(e).__name__ + ': ' + str(e))
""".format(project_path=PROJECT_PATH, module_name=file_path.stem)

        cmd = [
            SYSTEM_PYTHON,
            "-c",
            cmd_str
        ]

        proc_result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            cwd=PROJECT_PATH
        )

        output = proc_result.stdout.strip()
        if "IMPORT_SUCCESS" in output:
            result["import_success"] = True
        elif "IMPORT_ERROR" in output:
            # 提取错误信息
            lines = output.split("\n")
            for line in lines:
                if "IMPORT_ERROR:" in line:
                    result["import_error"] = line.split("IMPORT_ERROR: ")[-1]
                    break
        elif "RUNTIME_ERROR" in output:
            lines = output.split("\n")
            for line in lines:
                if "RUNTIME_ERROR:" in line:
                    result["runtime_error"] = line.split("RUNTIME_ERROR: ")[-1]
                    break

    except subprocess.TimeoutExpired:
        result["runtime_error"] = f"超时（>{TIMEOUT}秒）"
    except Exception as e:
        result["runtime_error"] = str(e)

    return result


def test_file_gui_start(file_path: Path) -> dict:
    """测试文件是否能启动 GUI（尝试创建窗口）"""
    result = {
        "file": file_path.name,
        "gui_start_success": False,
        "error": None,
    }

    try:
        # 尝试导入并调用主函数（如果有）
        # 注意：这里的命令字符串中的 { 和 } 需要转义
        cmd_str = """
import sys
import tkinter as tk
sys.path.insert(0, r'{project_path}')

try:
    # 导入模块
    import {module_name}
    
    # 尝试创建 tkinter 窗口（仅测试是否能启动）
    root = tk.Tk()
    root.title('Test')
    root.geometry('100x100')
    
    # 立即销毁（不显示）
    root.destroy()
    
    print('GUI_START_SUCCESS')
    
except ImportError as e:
    print('IMPORT_ERROR: ' + str(e))
except tk.TclError as e:
    print('GUI_ERROR: ' + str(e))
except Exception as e:
    print('ERROR: ' + type(e).__name__ + ': ' + str(e))
""".format(project_path=PROJECT_PATH, module_name=file_path.stem)

        cmd = [
            SYSTEM_PYTHON,
            "-c",
            cmd_str
        ]

        proc_result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            cwd=PROJECT_PATH
        )

        output = proc_result.stdout.strip()
        if "GUI_START_SUCCESS" in output:
            result["gui_start_success"] = True
        elif "IMPORT_ERROR" in output:
            lines = output.split("\n")
            for line in lines:
                if "IMPORT_ERROR:" in line:
                    result["error"] = line.split("IMPORT_ERROR: ")[-1]
                    break
        elif "GUI_ERROR" in output:
            lines = output.split("\n")
            for line in lines:
                if "GUI_ERROR:" in line:
                    result["error"] = line.split("GUI_ERROR: ")[-1]
                    break
        elif "ERROR" in output:
            lines = output.split("\n")
            for line in lines:
                if "ERROR:" in line:
                    result["error"] = line.split("ERROR: ")[-1]
                    break

    except subprocess.TimeoutExpired:
        result["error"] = f"超时（>{TIMEOUT}秒）"
    except Exception as e:
        result["error"] = str(e)

    return result


def main():
    print("=" * 80)
    print("🚀 merged_gui 项目 — 动态测试（使用系统 Python + tkinter）")
    print("=" * 80)
    print()

    # 获取所有 Python 文件
    py_files = sorted([f for f in PROJECT_PATH.glob("*.py") if f.name != "__init__.py"])
    print(f"📁 项目路径: {PROJECT_PATH}")
    print(f"📄 Python 文件数: {len(py_files)}")
    print(f"🐍 使用 Python: {SYSTEM_PYTHON}")
    print()

    # 阶段 1: 导入测试
    print("=" * 80)
    print("📦 阶段 1: 导入测试")
    print("=" * 80)
    print()

    import_results = []
    for py_file in py_files:
        result = test_file_import(py_file)
        import_results.append(result)

        status = "✅" if result["import_success"] else "❌"
        print(f"{status} {result['file']}")
        if result["import_error"]:
            print(f"    导入错误: {result['import_error']}")
        if result["runtime_error"]:
            print(f"    运行时错误: {result['runtime_error']}")

    print()

    # 统计
    import_success_count = sum(1 for r in import_results if r["import_success"])
    import_failed_count = len(import_results) - import_success_count
    print(f"✅ 导入成功: {import_success_count}/{len(import_results)}")
    print(f"❌ 导入失败: {import_failed_count}/{len(import_results)}")
    print()

    # 阶段 2: GUI 启动测试（仅测试能导入的文件）
    print("=" * 80)
    print("🖥️  阶段 2: GUI 启动测试（尝试创建窗口）")
    print("=" * 80)
    print()

    gui_results = []
    for result in import_results:
        if not result["import_success"]:
            continue

        file_path = PROJECT_PATH / result["file"]
        gui_result = test_file_gui_start(file_path)
        gui_results.append(gui_result)

        status = "✅" if gui_result["gui_start_success"] else "❌"
        print(f"{status} {gui_result['file']}")
        if gui_result["error"]:
            print(f"    错误: {gui_result['error']}")

    print()

    # 统计
    gui_success_count = sum(1 for r in gui_results if r["gui_start_success"])
    gui_failed_count = len(gui_results) - gui_success_count
    print(f"✅ GUI 启动成功: {gui_success_count}/{len(gui_results)}")
    print(f"❌ GUI 启动失败: {gui_failed_count}/{len(gui_results)}")
    print()

    # 汇总
    print("=" * 80)
    print("📊 测试汇总")
    print("=" * 80)
    print()
    print(f"总文件数: {len(py_files)}")
    print(f"导入成功: {import_success_count}")
    print(f"导入失败: {import_failed_count}")
    print(f"GUI 启动成功: {gui_success_count}")
    print(f"GUI 启动失败: {gui_failed_count}")
    print()

    # 失败的文件的详细信息
    if import_failed_count > 0:
        print("=" * 80)
        print("❌ 导入失败的文件")
        print("=" * 80)
        for result in import_results:
            if not result["import_success"]:
                print(f"  - {result['file']}")
                if result["import_error"]:
                    print(f"    导入错误: {result['import_error']}")
                if result["runtime_error"]:
                    print(f"    运行时错误: {result['runtime_error']}")
        print()

    print("=" * 80)
    print("✅ 测试完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
