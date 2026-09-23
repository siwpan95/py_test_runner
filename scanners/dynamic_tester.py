"""
动态测试模块 — 尝试实际运行 Python 文件，检查是否能正常导入和启动 GUI

功能：
1. 导入测试：检查模块是否能成功导入
2. GUI 启动测试：检查是否能创建 tkinter 窗口
3. 使用系统 Python（如果 managed Python 没有 tkinter）
4. 🆕 并行执行：使用多进程加速批量测试
5. 🆕 增量扫描：基于文件修改时间跳过未变更的文件

使用方法：
    from scanners.dynamic_tester import DynamicTester
    
    tester = DynamicTester(project_path=os.environ.get("SCAN_ROOT") or str(Path(__file__).resolve().parents[2]))
    
    # 并行测试（4 进程）
    results = tester.run_tests(parallel=True, workers=4)
    
    # 增量扫描
    results = tester.run_tests(incremental=True)
    
    tester.print_report()
"""

import subprocess
import sys
import time
import os
import json
import hashlib
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import pickle


# ── 数据结构 ────────────────────────────────────────────────

@dataclass
class DynamicTestResult:
    """动态测试结果"""
    file_name: str
    file_path: str
    
    # 导入测试
    import_success: bool = False
    import_error: Optional[str] = None
    import_time: float = 0.0
    
    # GUI 启动测试
    gui_start_success: bool = False
    gui_error: Optional[str] = None
    gui_start_time: float = 0.0
    
    # 元数据
    test_duration: float = 0.0
    from_cache: bool = False  # 是否来自缓存（增量模式）


# ── 缓存管理 ────────────────────────────────────────────────

class TestCache:
    """增量扫描缓存：基于文件修改时间和内容哈希跳过未变更的文件"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path.home() / ".workbuddy" / "py_test_runner" / "cache"
        self.cache_file = self.cache_dir / "dynamic_test_cache.json"
        self._cache: Dict[str, Dict] = {}
        
    def load(self):
        """加载缓存"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception:
                self._cache = {}
    
    def save(self):
        """保存缓存"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)
    
    def get_file_hash(self, file_path: Path) -> str:
        """计算文件的 MD5 哈希（用于内容变更检测）"""
        try:
            return hashlib.md5(file_path.read_bytes()).hexdigest()
        except Exception:
            return ""
    
    def is_unchanged(self, file_path: Path) -> Tuple[bool, Optional[DynamicTestResult]]:
        """
        检查文件是否未变更
        
        Returns:
            (是否未变更, 缓存的结果或 None)
        """
        try:
            mtime = file_path.stat().st_mtime
            file_hash = self.get_file_hash(file_path)
            key = str(file_path.resolve())
            
            cached = self._cache.get(key)
            if not cached:
                return False, None
            
            # 检查修改时间和哈希
            if cached.get("mtime") == mtime and cached.get("hash") == file_hash:
                result = DynamicTestResult(**{k: v for k, v in cached.items()
                                              if k in DynamicTestResult.__dataclass_fields__})
                result.from_cache = True
                return True, result
            
            return False, None
            
        except Exception:
            return False, None
    
    def update(self, file_path: Path, result: DynamicTestResult):
        """更新缓存记录"""
        key = str(file_path.resolve())
        self._cache[key] = {
            **asdict(result),
            "mtime": file_path.stat().st_mtime,
            "hash": self.get_file_hash(file_path),
        }
    
    @property
    def stats(self) -> Dict[str, int]:
        """缓存统计"""
        total = len(self._cache)
        valid = sum(1 for v in self._cache.values() if v.get("import_success", False))
        return {"total": total, "valid": valid}


# ── 工作函数（供并行调用） ─────────────────────────────────

def _compute_module_name(file_path: Path, project_path: Path) -> str:
    """
    根据文件路径计算 Python 模块名
    
    core/data_loader.py (相对于 project_path) → "core.data_loader"
    main.py (直接在 project_path 下)     → "main"
    """
    try:
        rel = file_path.relative_to(project_path)
    except ValueError:
        return file_path.stem  # 回退到文件名
    
    parts = [p for p in rel.parts[:-1]]  # 目录部分
    stem = rel.stem
    
    if stem == "__init__":
        # __init__.py → 包名（目录名）
        return ".".join(parts) if parts else ""
    elif parts:
        return ".".join(parts + [stem])
    else:
        return stem


def _test_single_file(args_tuple: tuple) -> Dict:
    """
    单个文件的完整动态测试（导入 + GUI 启动）
    
    此函数在子进程中调用，必须独立、无外部依赖。
    
    args_tuple: (file_path_str, project_path_str, python_path, timeout)
               或 (file_path_str, project_path_str, python_path, timeout, module_name)
    """
    if len(args_tuple) >= 5:
        file_path_str, project_path_str, python_path, timeout, module_name = args_tuple
    else:
        file_path_str, project_path_str, python_path, timeout = args_tuple
        module_name = None
    
    file_path = Path(file_path_str)
    project_path = Path(project_path_str)
    
    # 计算模块名（如果未提供）
    if module_name is None:
        module_name = _compute_module_name(file_path, project_path)
    
    result = {
        "file_name": file_path.name,
        "file_path": str(file_path),
        "import_success": False,
        "import_error": None,
        "import_time": 0.0,
        "gui_start_success": False,
        "gui_error": None,
        "gui_start_time": 0.0,
        "test_duration": 0.0,
    }
    
    start = time.time()
    
    # === 阶段 1: 导入测试 ===
    # 使用 importlib.import_module 支持包内模块（如 core.data_loader）
    safe_module = module_name.replace("'", "\\'")
    cmd_str = (
        "import sys, time, importlib\n"
        "t0 = time.time()\n"
        f"sys.path.insert(0, r'{project_path}')\n"
        "try:\n"
        f"    mod = importlib.import_module('{safe_module}')\n"
        "    print(f'IMPORT_SUCCESS {{time.time()-t0:.3f}}')\n"
        "except ImportError as e:\n"
        "    print(f'IMPORT_ERROR: ' + str(e))\n"
        "except Exception as e:\n"
        "    print(f'RUNTIME_ERROR: ' + type(e).__name__ + ': ' + str(e))\n"
    )
    
    try:
        proc = subprocess.run(
            [python_path, "-c", cmd_str],
            capture_output=True, text=True,
            timeout=timeout, cwd=project_path,
        )
        output = proc.stdout.strip()
        for line in output.split("\n"):
            if line.startswith("IMPORT_SUCCESS"):
                result["import_success"] = True
                try:
                    result["import_time"] = float(line.split()[1])
                except (IndexError, ValueError):
                    pass
                break
            elif line.startswith("IMPORT_ERROR"):
                result["import_error"] = line.split(":", 1)[1].strip() if ":" in line else line
                break
            elif line.startswith("RUNTIME_ERROR"):
                result["import_error"] = line.split(":", 1)[1].strip() if ":" in line else line
                break
    except subprocess.TimeoutExpired:
        result["import_error"] = f"超时(>{timeout}s)"
    except Exception as e:
        result["import_error"] = str(e)
    
    # === 阶段 2: GUI 启动测试（仅导入成功时）===
    if result["import_success"]:
        safe_module = module_name.replace("'", "\\'")
        cmd_str = (
            "import sys, tkinter as tk, importlib\n"
            f"sys.path.insert(0, r'{project_path}')\n"
            "try:\n"
            f"    mod = importlib.import_module('{safe_module}')\n"
            "    root = tk.Tk(); root.title('T'); root.geometry('100x100')\n"
            "    root.destroy()\n"
            "    print('GUI_START_SUCCESS')\n"
            "except ImportError as e:\n"
            "    print(f'IMPORT_ERROR: ' + str(e))\n"
            "except tk.TclError as e:\n"
            "    print(f'GUI_ERROR: ' + str(e))\n"
            "except Exception as e:\n"
            "    print(f'ERROR: ' + type(e).__name__ + ': ' + str(e))\n"
        )
        try:
            proc = subprocess.run(
                [python_path, "-c", cmd_str],
                capture_output=True, text=True,
                timeout=timeout, cwd=project_path,
            )
            output = proc.stdout.strip()
            if "GUI_START_SUCCESS" in output:
                result["gui_start_success"] = True
            elif any(k in output for k in ("IMPORT_ERROR", "GUI_ERROR", "ERROR")):
                for line in output.split("\n"):
                    if ":" in line and any(line.startswith(k) for k in ("IMPORT_ERROR", "GUI_ERROR", "ERROR")):
                        result["gui_error"] = line.split(":", 1)[1].strip()
                        break
        except subprocess.TimeoutExpired:
            result["gui_error"] = f"GUI超时(>{timeout}s)"
        except Exception as e:
            result["gui_error"] = str(e)
    
    result["test_duration"] = time.time() - start
    return result


# ── 动态测试器主类 ─────────────────────────────────────────

class DynamicTester:
    """
    动态测试器
    
    功能：
    - 导入测试：检查模块能否成功导入
    - GUI 启动测试：检查能否创建 tkinter 窗口
    - 并行执行：使用多进程加速批量测试
    - 增量扫描：基于文件修改时间跳过未变更的文件
    """
    
    def __init__(
        self,
        project_path: str = ".",
        python_path: Optional[str] = None,
        timeout: int = 10,
        workers: int = 4,
    ):
        self.project_path = Path(project_path).resolve()
        self.timeout = timeout
        self.workers = workers
        
        # Python 解释器检测与选择
        self.python_path = python_path or self._detect_python()
        
        # 结果列表
        self.results: List[DynamicTestResult] = []
        
        # 增量扫描缓存
        self.cache = TestCache()
    
    def _detect_python(self) -> str:
        """自动检测有 tkinter 的系统 Python"""
        # 2026-09-23 去本地化：当前解释器优先，可用 PYEXE 覆盖
        candidates = [
            os.environ.get("PYEXE", "").strip(),
            sys.executable,
        ]
        candidates = [c for c in candidates if c]
        for py in candidates:
            try:
                r = subprocess.run([py, "-c", "import tkinter;print('ok')"],
                                   capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    print(f"[DynamicTester] 使用系统 Python: {py}")
                    return py
            except Exception:
                continue
        
        fallback = sys.executable
        print(f"[DynamicTester] 回退到当前 Python: {fallback} （可能缺少 tkinter）")
        return fallback
    
    def _discover_files(self) -> List[Path]:
        """发现待测 .py 文件"""
        files = list(self.project_path.glob("*.py"))
        files = [f for f in files if f.name != "__init__.py"]
        return sorted(files, key=lambda p: p.name.lower())
    
    # ── 核心执行逻辑 ──
    
    def run_tests(
        self,
        file_paths: Optional[List[Path]] = None,
        parallel: bool = False,
        incremental: bool = False,
        force: bool = False,
    ) -> List[DynamicTestResult]:
        """
        运行动态测试
        
        Args:
            file_paths: 待测文件列表（默认自动发现项目根目录 *.py）
            parallel:   是否启用并行执行（多进程）
            incremental:是否启用增量扫描（跳过未变更文件）
            force:      强制重新测试所有文件（忽略缓存）
        
        Returns:
            测试结果列表
        """
        # 文件发现
        if file_paths is None:
            file_paths = self._discover_files()
        
        total = len(file_paths)
        print("=" * 72)
        print("  Dynamic Tester")
        print("=" * 72)
        print(f"  项目路径 : {self.project_path}")
        print(f"  Python   : {self.python_path}")
        print(f"  文件数   : {total}")
        print(f"  超时     : {self.timeout}s")
        print(f"  并行     : {'ON (%d workers)' % self.workers if parallel else 'OFF'}")
        print(f"  增量     : {'ON' if incremental else 'OFF'}")
        print("=" * 72)
        
        # 增量模式：加载缓存并筛选
        cached_results: List[DynamicTestResult] = []
        to_test: List[Path] = []
        
        if incremental and not force:
            self.cache.load()
            print(f"\n  缓存状态 : {self.cache.stats['total']} 条记录")
            
            for fp in file_paths:
                unchanged, cached_result = self.cache.is_unchanged(fp)
                if unchanged and cached_result is not None:
                    cached_results.append(cached_result)
                else:
                    to_test.append(fp)
            
            print(f"  跳过缓存: {len(cached_results)} 个文件")
            print(f"  待测试  : {len(to_test)} 个文件")
        else:
            to_test = list(file_paths)
        
        t0 = time.time()
        
        # 执行测试
        if parallel and len(to_test) > 1:
            new_results = self._run_parallel(to_test)
        else:
            new_results = self._run_sequential(to_test)
        
        elapsed = time.time() - t0
        
        # 合并结果（缓存在前，新测试在后）
        self.results = cached_results + new_results
        
        # 更新缓存
        if incremental:
            for r in new_results:
                fp = Path(r.file_path)
                if fp.exists():
                    self.cache.update(fp, r)
            self.cache.save()
        
        # 打印摘要
        self._print_summary(elapsed, len(cached_results), len(new_results))
        
        return self.results
    
    def _run_sequential(self, file_paths: List[Path]) -> List[DynamicTestResult]:
        """顺序执行测试"""
        results = []
        total = len(file_paths)
        
        for i, fp in enumerate(file_paths, 1):
            module_name = _compute_module_name(fp, self.project_path)
            print(f"  [{i}/{total}] {fp.name}", end="", flush=True)
            
            raw = _test_single_file((str(fp), str(self.project_path),
                                      self.python_path, self.timeout, module_name))
            result = DynamicTestResult(
                file_name=raw["file_name"], file_path=raw["file_path"],
                import_success=raw["import_success"],
                import_error=raw["import_error"],
                import_time=raw["import_time"],
                gui_start_success=raw["gui_start_success"],
                gui_error=raw["gui_error"],
                gui_start_time=raw["gui_start_time"],
                test_duration=raw["test_duration"],
            )
            
            status = " OK" if result.import_success else " FAIL"
            if result.import_error:
                status += f" ({result.import_error[:40]})"
            print(status)
            
            results.append(result)
        
        return results
    
    def _run_parallel(self, file_paths: List[Path]) -> List[DynamicTestResult]:
        """并行执行测试（多进程）"""
        results = []
        total = len(file_paths)
        
        args_list = []
        for fp in file_paths:
            module_name = _compute_module_name(fp, self.project_path)
            args_list.append((str(fp), str(self.project_path),
                             self.python_path, self.timeout, module_name))
        
        # 使用 ProcessPoolExecutor 实现真正的并行
        # 注意：Windows 下需要在 if __name__ == "__main__" 中运行
        workers = min(self.workers, total, os.cpu_count() or 4)
        
        print(f"\n  并行执行: {workers} 进程 x {total} 任务 ...\n")
        
        completed = 0
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_test_single_file, args): args[0]
                       for args in args_list}
            
            for future in as_completed(futures):
                completed += 1
                orig_path = futures[future]
                
                try:
                    raw = future.result()
                    result = DynamicTestResult(
                        file_name=raw["file_name"], file_path=raw["file_path"],
                        import_success=raw["import_success"],
                        import_error=raw["import_error"],
                        import_time=raw["import_time"],
                        gui_start_success=raw["gui_start_success"],
                        gui_error=raw["gui_error"],
                        gui_start_time=raw["gui_start_time"],
                        test_duration=raw["test_duration"],
                    )
                    
                    name = Path(orig_path).name
                    status = "OK" if result.import_success else "FAIL"
                    print(f"  [{completed}/{total}] {name}: {status}")
                    results.append(result)
                    
                except Exception as e:
                    name = Path(orig_path).name
                    print(f"  [{completed}/{total}] {name}: ERROR {e}")
                    results.append(DynamicTestResult(
                        file_name=name, file_path=str(orig_path),
                        import_error=str(e),
                    ))
        
        # 按原始顺序排列（并行完成顺序不确定）
        path_set = {str(p) for p in file_paths}
        ordered = []
        for fp in file_paths:
            for r in results:
                if r.file_path == str(fp):
                    ordered.append(r)
                    break
        return ordered if ordered else results
    
    def _print_summary(self, elapsed: float, cached: int, tested: int):
        """打印摘要信息"""
        total = len(self.results)
        ok_import = sum(1 for r in self.results if r.import_success)
        fail_import = total - ok_import
        ok_gui = sum(1 for r in self.results if r.gui_start_success)
        
        print(f"\n{'='*72}")
        print(f"  完成! 耗时: {elapsed:.2f}s | "
              f"导入: {ok_import}/{total} OK | "
              f"GUI: {ok_gui}/{ok_import} OK")
        if cached > 0:
            print(f"  (其中 {cached} 个来自缓存)")
        print(f"{'='*72}")
    
    # ── 报告输出 ──
    
    def print_report(self):
        """打印详细报告"""
        print("\n" + "=" * 72)
        print("  详细报告")
        print("=" * 72)
        
        total = len(self.results)
        ok_import = sum(1 for r in self.results if r.import_success)
        fail_import = total - ok_import
        ok_gui = sum(1 for r in self.results if r.gui_start_success)
        
        print(f"\n  总文件数     : {total}")
        print(f"  导入成功     : {ok_import} ({ok_import/total*100:.1f}%)" if total else "")
        print(f"  导入失败     : {fail_import} ({fail_import/total*100:.1f}%)" if total else "")
        if ok_import:
            print(f"  GUI 启动成功 : {ok_gui} ({ok_gui/ok_import*100:.1f}%)")
            print(f"  GUI 启动失败 : {ok_import-ok_gui} ({(ok_import-ok_gui)/ok_import*100:.1f}%)" if ok_import else "")
        
        # 失败明细
        failed = [r for r in self.results if not r.import_success]
        if failed:
            print(f"\n  导入失败的文件:")
            for r in failed:
                print(f"    X {r.file_name}" + (f" -- {r.import_error}" if r.import_error else ""))
        
        gui_fail = [r for r in self.results if r.import_success and not r.gui_start_success]
        if gui_fail:
            print(f"\n  GUI 启动失败的文件:")
            for r in gui_fail:
                print(f"    X {r.file_name}" + (f" -- {r.gui_error}" if r.gui_error else ""))
        
        print(f"\n{'='*72}\n")
    
    def export_json(self, output_path: Optional[str] = None) -> str:
        """导出 JSON 报告"""
        out = Path(output_path or str(self.project_path / "logs" / "dynamic_test_report.json"))
        out.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "project_path": str(self.project_path),
            "python_path": self.python_path,
            "timeout": self.timeout,
            "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": [asdict(r) for r in self.results],
        }
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  已导出: {out}")
        return str(out)


# ── CLI 入口 ───────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Dynamic Test Runner")
    parser.add_argument("--project", default=".", help="项目路径")
    parser.add_argument("--python", default=None, help="Python 路径")
    parser.add_argument("--timeout", type=int, default=10, help="单文件超时(s)")
    parser.add_argument("--workers", type=int, default=4, help="并行进程数")
    parser.add_argument("--parallel", action="store_true", help="并行执行")
    parser.add_argument("--incremental", action="store_true", help="增量扫描")
    parser.add_argument("--force", action="store_true", help="强制全量测试")
    parser.add_argument("--export", default=None, help="导出路径")
    args = parser.parse_args()
    
    tester = DynamicTester(
        project_path=args.project,
        python_path=args.python,
        timeout=args.timeout,
        workers=args.workers,
    )
    
    tester.run_tests(
        parallel=args.parallel,
        incremental=args.incremental,
        force=args.force,
    )
    tester.print_report()
    tester.export_json(args.export)


if __name__ == "__main__":
    main()
