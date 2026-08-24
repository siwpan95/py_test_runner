"""
测试报告生成器 — 生成详细的 HTML/JSON 测试报告。

功能：
    1. 生成交互式 HTML 报告（带图表）
    2. 导出 JSON 格式的结果（便于 CI/CD 集成）
    3. 覆盖率趋势图
    4. 测试结果统计分析

使用方式：
    from report_generator import ReportGenerator

    gen = ReportGenerator()
    gen.generate_html(results, output_file="report.html")
    gen.generate_json(results, output_file="report.json")
"""

import json
import html
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict


# ── HTML 模板 ─────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 30px;
        }}

        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}

        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .summary-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            border-left: 4px solid #3498db;
        }}

        .summary-card.pass {{
            border-left-color: #27ae60;
        }}

        .summary-card.fail {{
            border-left-color: #e74c3c;
        }}

        .summary-card.error {{
            border-left-color: #e67e22;
        }}

        .summary-card.skipped {{
            border-left-color: #95a5a6;
        }}

        .summary-card h2 {{
            font-size: 2em;
            margin-bottom: 5px;
        }}

        .summary-card.pass h2 {{ color: #27ae60; }}
        .summary-card.fail h2 {{ color: #e74c3c; }}
        .summary-card.error h2 {{ color: #e67e22; }}
        .summary-card.skipped h2 {{ color: #95a5a6; }}

        .chart-container {{
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }}

        canvas {{
            max-width: 100%;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}

        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}

        th {{
            background: #3498db;
            color: white;
            font-weight: 600;
        }}

        tr:hover {{
            background: #f5f5f5;
        }}

        .status-pass {{
            color: #27ae60;
            font-weight: 600;
        }}

        .status-fail {{
            color: #e74c3c;
            font-weight: 600;
        }}

        .status-error {{
            color: #e67e22;
            font-weight: 600;
        }}

        .status-skipped {{
            color: #95a5a6;
            font-weight: 600;
        }}

        .timestamp {{
            color: #7f8c8d;
            font-size: 0.9em;
            margin-bottom: 20px;
        }}

        .filter-buttons {{
            margin: 20px 0;
        }}

        .filter-buttons button {{
            padding: 8px 16px;
            margin-right: 10px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}

        .filter-buttons button.active {{
            background: #3498db;
            color: white;
        }}

        .filter-buttons button:not(.active) {{
            background: #ecf0f1;
            color: #333;
        }}

        .progress-bar {{
            width: 100%;
            height: 24px;
            background: #ecf0f1;
            border-radius: 12px;
            overflow: hidden;
            margin: 20px 0;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #27ae60, #2ecc71);
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            font-size: 12px;
        }}

        .details {{
            font-size: 0.9em;
            color: #7f8c8d;
            margin-top: 5px;
        }}

        pre {{
            background: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 0.85em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div class="timestamp">生成时间: {timestamp}</div>

        {summary_section}

        {progress_section}

        {chart_section}

        {filter_section}

        {results_table}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script>
        {chart_script}
    </script>

    <script>
        // 过滤功能
        function filterResults(status) {{
            const rows = document.querySelectorAll('tbody tr');
            rows.forEach(row => {{
                if (status === 'all' || row.classList.contains('row-' + status)) {{
                    row.style.display = '';
                }} else {{
                    row.style.display = 'none';
                }}
            }});

            // 更新按钮状态
            document.querySelectorAll('.filter-buttons button').forEach(btn => {{
                btn.classList.remove('active');
            }});
            event.target.classList.add('active');
        }}

        // 初始化
        document.addEventListener('DOMContentLoaded', () => {{
            console.log('测试报告已加载');
        }});
    </script>
</body>
</html>"""

# ── JavaScript 图表模板 ─────────────────────────

CHART_SCRIPT_TEMPLATE = """
// 状态分布饼图
const ctxPie = document.getElementById('pieChart');
if (ctxPie) {{
    new Chart(ctxPie, {{
        type: 'pie',
        data: {{
            labels: ['通过', '失败', '错误', '跳过'],
            datasets: [{{
                data: [{pass_count}, {fail_count}, {error_count}, {skipped_count}],
                backgroundColor: ['#27ae60', '#e74c3c', '#e67e22', '#95a5a6'],
            }}]
        }},
        options: {{
            responsive: true,
            plugins: {{
                title: {{
                    display: true,
                    text: '测试结果分布'
                }}
            }}
        }}
    }});
}}

// 时间趋势图（如果有历史数据）
const ctxLine = document.getElementById('trendChart');
if (ctxLine) {{
    new Chart(ctxLine, {{
        type: 'line',
        data: {{
            labels: {trend_labels},
            datasets: [{{
                label: '覆盖率 (%)',
                data: {trend_data},
                borderColor: '#3498db',
                tension: 0.1
            }}]
        }},
        options: {{
            responsive: true,
            plugins: {{
                title: {{
                    display: true,
                    text: '覆盖率趋势'
                }}
            }}
        }}
    }});
}}
"""


class ReportGenerator:
    """测试报告生成器"""

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate_html(
        self,
        results: List[Any],
        output_file: str = "report.html",
        title: str = "测试报告",
    ) -> str:
        """
        生成 HTML 报告

        Args:
            results: TestError 对象列表
            output_file: 输出文件名
            title: 报告标题
        """
        # 统计数据
        stats = self._calculate_stats(results)

        # 生成各部分
        summary_section = self._generate_summary_section(stats)
        progress_section = self._generate_progress_section(stats)
        chart_section = self._generate_chart_section(stats)
        filter_section = self._generate_filter_section()
        results_table = self._generate_results_table(results)

        # 生成图表脚本
        chart_script = CHART_SCRIPT_TEMPLATE.format(
            pass_count=stats["pass"],
            fail_count=stats["fail"],
            error_count=stats["error"],
            skipped_count=stats["skipped"],
            trend_labels=[],
            trend_data=[],
        )

        # 组装 HTML
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html_content = HTML_TEMPLATE.format(
            title=title,
            timestamp=timestamp,
            summary_section=summary_section,
            progress_section=progress_section,
            chart_section=chart_section,
            filter_section=filter_section,
            results_table=results_table,
            chart_script=chart_script,
        )

        # 保存文件
        output_path = self.output_dir / output_file
        output_path.write_text(html_content, encoding="utf-8")

        print(f"📊 HTML 报告已生成: {output_path}")
        return str(output_path)

    def generate_json(
        self,
        results: List[Any],
        output_file: str = "report.json",
    ) -> str:
        """
        生成 JSON 报告

        Args:
            results: TestError 对象列表
            output_file: 输出文件名
        """
        stats = self._calculate_stats(results)

        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": stats,
            "results": [],
        }

        for result in results:
            report_data["results"].append({
                "name": result.test_name,
                "status": result.error_code.category.value,
                "message": result.message,
                "traceback": result.traceback,
            })

        output_path = self.output_dir / output_file
        with open(output_path, "w", encoding="utf-8") as fp:
            json.dump(report_data, fp, ensure_ascii=False, indent=2)

        print(f"📊 JSON 报告已生成: {output_path}")
        return str(output_path)

    def _calculate_stats(self, results: List[Any]) -> Dict[str, int]:
        """统计测试结果"""
        stats = defaultdict(int)

        for result in results:
            category = result.error_code.category.value
            if category == "通过":
                stats["pass"] += 1
            elif category == "失败":
                stats["fail"] += 1
            elif category == "错误":
                stats["error"] += 1
            elif category == "跳过":
                stats["skipped"] += 1
            else:
                stats["unknown"] += 1

        stats["total"] = len(results)
        return dict(stats)

    def _generate_summary_section(self, stats: Dict[str, int]) -> str:
        """生成统计卡片区域"""
        return f"""
        <div class="summary">
            <div class="summary-card pass">
                <h2>{stats.get("pass", 0)}</h2>
                <p>通过</p>
            </div>
            <div class="summary-card fail">
                <h2>{stats.get("fail", 0)}</h2>
                <p>失败</p>
            </div>
            <div class="summary-card error">
                <h2>{stats.get("error", 0)}</h2>
                <p>错误</p>
            </div>
            <div class="summary-card skipped">
                <h2>{stats.get("skipped", 0)}</h2>
                <p>跳过</p>
            </div>
        </div>
        """

    def _generate_progress_section(self, stats: Dict[str, int]) -> str:
        """生成进度条区域"""
        total = stats.get("total", 1)
        pass_count = stats.get("pass", 0)
        percentage = (pass_count / total) * 100 if total > 0 else 0

        return f"""
        <div class="progress-bar">
            <div class="progress-fill" style="width: {percentage}%">
                {percentage:.1f}%
            </div>
        </div>
        <div class="details">
            总计 {total} 个测试，通过 {pass_count} 个 ({percentage:.1f}%)
        </div>
        """

    def _generate_chart_section(self, stats: Dict[str, int]) -> str:
        """生成图表区域"""
        return """
        <div class="chart-container">
            <canvas id="pieChart"></canvas>
        </div>
        """

    def _generate_filter_section(self) -> str:
        """生成过滤按钮区域"""
        return """
        <div class="filter-buttons">
            <button class="active" onclick="filterResults('all')">全部</button>
            <button onclick="filterResults('pass')">通过</button>
            <button onclick="filterResults('fail')">失败</button>
            <button onclick="filterResults('error')">错误</button>
            <button onclick="filterResults('skipped')">跳过</button>
        </div>
        """

    def _generate_results_table(self, results: List[Any]) -> str:
        """生成结果表格"""
        rows = []
        for result in results:
            category = result.error_code.category.value
            status_class = f"status-{category}"
            row_class = f"row-{category}"

            # 处理 traceback
            traceback_html = ""
            if result.traceback:
                traceback_html = f"<pre>{html.escape(result.traceback)}</pre>"

            rows.append(f"""
            <tr class="{row_class}">
                <td>{html.escape(result.test_name)}</td>
                <td class="{status_class}">{category}</td>
                <td>{html.escape(result.message)}</td>
                <td>{traceback_html}</td>
            </tr>
            """)

        table = f"""
        <table>
            <thead>
                <tr>
                    <th>测试名称</th>
                    <th>状态</th>
                    <th>消息</th>
                    <th>详情</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """

        return table


# ── CLI 入口 ─────────────────────────────────────

def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="测试报告生成器")
    parser.add_argument(
        "--input",
        required=True,
        help="输入 JSON 文件（测试结果的 JSON）",
    )
    parser.add_argument(
        "--output",
        default="report.html",
        help="输出 HTML 文件（默认: report.html）",
    )
    parser.add_argument(
        "--format",
        choices=["html", "json"],
        default="html",
        help="输出格式（默认: html）",
    )

    args = parser.parse_args()

    # 读取输入文件
    with open(args.input, encoding="utf-8") as fp:
        data = json.load(fp)

    results = data.get("results", [])

    # 生成报告
    gen = ReportGenerator()
    if args.format == "html":
        gen.generate_html(results, output_file=args.output)
    else:
        gen.generate_json(results, output_file=args.output)


if __name__ == "__main__":
    main()
