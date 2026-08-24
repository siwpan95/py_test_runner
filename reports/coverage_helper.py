"""
覆盖率集成模块 — 集成 coverage.py 进行代码覆盖率分析。

功能：
    1. 运行测试时自动收集覆盖率数据
    2. 生成多种格式的报告（终端、HTML、JSON、XML）
    3. 跟踪覆盖率趋势
    4. 与现有测试框架无缝集成

使用方式：
    from coverage_helper import CoverageAnalyzer

    analyzer = CoverageAnalyzer()
    analyzer.start()
    # 运行测试...
    analyzer.stop()
    analyzer.report()

依赖：
    pip install coverage
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Optional, Dict, Any

try:
    import coverage
    from coverage import Coverage
    COVERAGE_AVAILABLE = True
except ImportError:
    COVERAGE_AVAILABLE = False
    Coverage = None


class CoverageAnalyzer:
    """覆盖率分析器"""

    def __init__(
        self,
        source_dir: Optional[str] = None,
        include: Optional[List[str]] = None,
        omit: Optional[List[str]] = None,
        data_file: str = ".coverage",
    ):
        """
        Args:
            source_dir: 源代码目录（要分析覆盖率的目录）
            include: 包含的文件模式（如 ["src/*.py"]）
            omit: 排除的文件模式（如 ["*/tests/*", "*/.venv/*"]）
            data_file: coverage 数据文件路径
        """
        self.source_dir = source_dir
        self.include = include or []
        self.omit = omit or [
            "*/tests/*",
            "*/test_*",
            "*/.venv/*",
            "*/venv/*",
            "*/__pycache__/*",
            "*/.git/*",
        ]
        self.data_file = data_file
        self._cov = None

        if not COVERAGE_AVAILABLE:
            print("⚠️  coverage.py 未安装，请运行: pip install coverage")

    def start(self):
        """开始收集覆盖率数据"""
        if not COVERAGE_AVAILABLE:
            return

        self._cov = Coverage(
            source=self.source_dir,
            include=self.include,
            omit=self.omit,
            data_file=self.data_file,
        )
        self._cov.start()
        print("📊 覆盖率收集已开始")

    def stop(self):
        """停止收集覆盖率数据"""
        if self._cov:
            self._cov.stop()
            self._cov.save()
            print(f"📊 覆盖率数据已保存: {self.data_file}")

    def report(self, style: str = "all"):
        """
        生成覆盖率报告

        Args:
            style: 报告类型
                - "terminal": 终端输出
                - "html": HTML 报告
                - "json": JSON 报告
                - "xml": XML 报告
                - "all": 全部
        """
        if not self._cov:
            print("⚠️  没有覆盖率数据，请先调用 start() 和 stop()")
            return

        if style in ("terminal", "all"):
            print("\n" + "=" * 60)
            print("📊 覆盖率报告（终端）")
            print("=" * 60)
            self._cov.report(show_missing=True)

        reports = []

        if style in ("html", "all"):
            html_dir = "htmlcov"
            self._cov.html_report(directory=html_dir)
            reports.append(f"HTML 报告: {html_dir}/index.html")
            print(f"📊 HTML 报告已生成: {html_dir}/")

        if style in ("json", "all"):
            json_file = "coverage.json"
            self._cov.json_report(outfile=json_file)
            reports.append(f"JSON 报告: {json_file}")
            print(f"📊 JSON 报告已生成: {json_file}")

        if style in ("xml", "all"):
            xml_file = "coverage.xml"
            self._cov.xml_report(outfile=xml_file)
            reports.append(f"XML 报告: {xml_file}")
            print(f"📊 XML 报告已生成: {xml_file}")

        if reports:
            print("\n📊 生成的报告:")
            for r in reports:
                print(f"   - {r}")

    def get_coverage_data(self) -> Dict[str, Any]:
        """获取覆盖率数据（用于程序化分析）"""
        if not self._cov:
            return {}

        data = self._cov.get_data()
        results = {}

        for filename in data.measured_files():
            lines = data.lines(filename)
            if lines:
                results[filename] = {
                    "covered_lines": len(lines),
                    "file": filename,
                }

        return results

    def combine(self, data_files: List[str]):
        """合并多个 coverage 数据文件"""
        if not COVERAGE_AVAILABLE:
            return

        self._cov = Coverage(data_file=self.data_file)
        self._cov.combine(data_files)
        print(f"📊 已合并 {len(data_files)} 个 coverage 数据文件")

    @staticmethod
    def install_hook():
        """安装 coverage 的 pytest 插件（如果使用 pytest）"""
        print("提示: 如果使用 pytest，可以安装 pytest-cov:")
        print("  pip install pytest-cov")
        print("  pytest --cov=src --cov-report=html")


def analyze_test_coverage(
    test_runner,
    test_fns: List,
    source_dir: str = ".",
    report_style: str = "html",
):
    """
    运行测试并分析覆盖率

    Args:
        test_runner: TestRunner 实例
        test_fns: 测试函数列表
        source_dir: 源代码目录
        report_style: 报告类型
    """
    if not COVERAGE_AVAILABLE:
        print("⚠️  coverage.py 未安装，跳过覆盖率分析")
        print("   请运行: pip install coverage")
        return

    analyzer = CoverageAnalyzer(source_dir=source_dir)
    analyzer.start()

    try:
        results = test_runner.run_tests(test_fns)
    finally:
        analyzer.stop()
        analyzer.report(style=report_style)

    return results


def generate_coverage_badge(coverage_percent: float) -> str:
    """生成覆盖率徽章（Markdown 格式）"""
    if coverage_percent >= 90:
        color = "brightgreen"
    elif coverage_percent >= 75:
        color = "green"
    elif coverage_percent >= 60:
        color = "yellowgreen"
    elif coverage_percent >= 40:
        color = "yellow"
    else:
        color = "red"

    badge = f"![coverage](https://img.shields.io/badge/coverage-{coverage_percent:.1f}%25-{color})"
    return badge


# ── CLI 入口 ─────────────────────────────────────
def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="覆盖率分析工具")
    parser.add_argument(
        "--source",
        default=".",
        help="源代码目录（默认: 当前目录）",
    )
    parser.add_argument(
        "--style",
        choices=["terminal", "html", "json", "xml", "all"],
        default="all",
        help="报告类型（默认: all）",
    )
    parser.add_argument(
        "--data-file",
        default=".coverage",
        help="coverage 数据文件（默认: .coverage）",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="运行测试并收集覆盖率",
    )

    args = parser.parse_args()

    if not COVERAGE_AVAILABLE:
        print("错误: coverage.py 未安装")
        print("请运行: pip install coverage")
        sys.exit(1)

    analyzer = CoverageAnalyzer(
        source_dir=args.source,
        data_file=args.data_file,
    )

    if args.run:
        print("提示: --run 模式需要指定测试文件")
        print("示例: python -m coverage run -m pytest")
        print("然后: python coverage_helper.py --style html")
    else:
        # 尝试加载已有的覆盖率数据
        if os.path.exists(args.data_file):
            analyzer._cov = Coverage(data_file=args.data_file)
            analyzer.report(style=args.style)
        else:
            print(f"错误: 找不到覆盖率数据文件 {args.data_file}")
            print("请先运行测试收集覆盖率数据")
            sys.exit(1)


if __name__ == "__main__":
    main()
