#!/usr/bin/env python3
"""
测试架构模式检测器

使用方法：
    python test_architecture_detector.py
    python test_architecture_detector.py D:/allin
"""

import sys
from pathlib import Path

# 添加当前目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from architecture_detector import ArchitectureDetector, print_architecture_report


def main():
    """主函数"""
    if len(sys.argv) > 1:
        project_root = Path(sys.argv[1])
    else:
        # 默认扫描 allin 项目
        project_root = Path("D:/allin")

    if not project_root.exists():
        print(f"❌ 项目路径不存在: {project_root}")
        sys.exit(1)

    print(f"🔍 开始检测项目架构模式...")
    print(f"   项目路径: {project_root}")
    print()

    # 创建检测器并扫描
    detector = ArchitectureDetector(project_root)
    report = detector.scan_project()

    # 打印报告
    detector.print_report()

    # 导出报告
    output_path = Path(__file__).parent / "logs" / "architecture_report.json"
    output_path.parent.mkdir(exist_ok=True)
    detector.export_report(output_path)

    print(f"\n📄 详细报告已保存: {output_path}")


if __name__ == "__main__":
    main()
