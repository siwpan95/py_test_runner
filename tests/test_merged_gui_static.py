"""
merged_gui 增强静态检查

检查内容：
1. 依赖检查（导入的第三方库）
2. 代码质量检查（函数长度、复杂度）
3. 文件编码一致性检查
4. 缺少依赖检查（requirements.txt 或导入语句分析）
"""

import ast
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set


# 常见的 Python 标准库模块
STDLIB_MODULES = {
    "os", "sys", "time", "datetime", "json", "csv", "math", "random",
    "collections", "itertools", "functools", "typing", "pathlib", "argparse",
    "subprocess", "threading", "multiprocessing", "socket", "http", "urllib",
    "hashlib", "base64", "re", "string", "logging", "unittest", "doctest",
    "tkinter", "pygame", "sqlite3", "xml", "html", "email", "wave", "audioop",
}

# merged_gui 目录
MERGED_GUI_DIR = Path("D:/allin/not/OK/merged_gui")


def analyze_imports(py_file: Path) -> Dict[str, List[str]]:
    """
    分析文件的导入语句

    Returns:
        {
            "stdlib": [标准库导入],
            "third_party": [第三方库导入],
            "local": [本地模块导入],
        }
    """
    result = {"stdlib": [], "third_party": [], "local": []}

    try:
        with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()

        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    if module in STDLIB_MODULES:
                        result["stdlib"].append(alias.name)
                    else:
                        result["third_party"].append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split(".")[0]
                    if module in STDLIB_MODULES:
                        result["stdlib"].append(node.module)
                    elif node.module.startswith("."):
                        # 相对导入，认为是本地模块
                        result["local"].append(node.module)
                    else:
                        result["third_party"].append(node.module)

    except Exception as e:
        print(f"⚠️  分析导入失败: {py_file.name} - {e}")

    return result


def check_code_quality(py_file: Path) -> Dict[str, any]:
    """
    检查代码质量

    Returns:
        {
            "functions": 函数数量,
            "classes": 类数量,
            "lines": 代码行数,
            "avg_function_length": 平均函数长度,
            "max_function_length": 最大函数长度,
            "complexity_issues": 复杂度问题列表,
        }
    """
    result = {
        "functions": 0,
        "classes": 0,
        "lines": 0,
        "avg_function_length": 0,
        "max_function_length": 0,
        "complexity_issues": [],
    }

    try:
        with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()

        result["lines"] = len(source.splitlines())

        tree = ast.parse(source)

        function_lengths = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                result["functions"] += 1
                # 计算函数长度
                if hasattr(node, "end_lineno") and node.end_lineno:
                    length = node.end_lineno - node.lineno + 1
                    function_lengths.append(length)

                    # 检查过长函数
                    if length > 50:
                        result["complexity_issues"].append(
                            f"函数 {node.name} 过长（{length} 行）"
                        )

            elif isinstance(node, ast.ClassDef):
                result["classes"] += 1

        if function_lengths:
            result["avg_function_length"] = sum(function_lengths) / len(function_lengths)
            result["max_function_length"] = max(function_lengths)

    except Exception as e:
        print(f"⚠️  代码质量检查失败: {py_file.name} - {e}")

    return result


def check_encoding_consistency(py_file: Path) -> Dict[str, any]:
    """
    检查文件编码一致性

    Returns:
        {
            "encoding": 检测到的编码,
            "has_bom": 是否有 BOM,
            "non_ascii_count": 非 ASCII 字符数,
        }
    """
    result = {
        "encoding": "unknown",
        "has_bom": False,
        "non_ascii_count": 0,
    }

    try:
        with open(py_file, "rb") as f:
            raw = f.read()

        # 检查 BOM
        if raw.startswith(b"\xef\xbb\xbf"):
            result["has_bom"] = True
            raw = raw[3:]

        # 尝试解码
        for encoding in ["utf-8", "gbk", "gb2312", "latin-1"]:
            try:
                raw.decode(encoding)
                result["encoding"] = encoding
                break
            except UnicodeDecodeError:
                continue

        # 统计非 ASCII 字符
        if result["encoding"] != "unknown":
            text = raw.decode(result["encoding"], errors="ignore")
            result["non_ascii_count"] = sum(1 for c in text if ord(c) > 127)

    except Exception as e:
        print(f"⚠️  编码检查失败: {py_file.name} - {e}")

    return result


def main():
    """主函数"""
    print("=" * 70)
    print("📊 merged_gui 增强静态检查")
    print("=" * 70)
    print()

    if not MERGED_GUI_DIR.exists():
        print(f"❌ 目录不存在: {MERGED_GUI_DIR}")
        return

    # 发现所有 Python 文件
    py_files = sorted(MERGED_GUI_DIR.glob("*.py"))
    print(f"发现 {len(py_files)} 个 Python 文件")
    print()

    # 汇总数据
    all_third_party = defaultdict(int)
    all_quality_issues = []
    encoding_stats = defaultdict(int)

    # 逐个检查
    for i, py_file in enumerate(py_files, 1):
        print(f"[{i}/{len(py_files)}] 检查: {py_file.name}")

        # 1. 导入分析
        imports = analyze_imports(py_file)
        if imports["third_party"]:
            third_party = set(imports["third_party"])
            print(f"    第三方库: {', '.join(third_party)}")
            for lib in third_party:
                all_third_party[lib] += 1

        # 2. 代码质量
        quality = check_code_quality(py_file)
        if quality["functions"] > 0:
            print(f"    函数: {quality['functions']} 个", end="")
            print(f", 平均长度: {quality['avg_function_length']:.1f} 行", end="")
            if quality["max_function_length"] > 50:
                print(f", ⚠️  最长: {quality['max_function_length']} 行")
            else:
                print()

        if quality["complexity_issues"]:
            for issue in quality["complexity_issues"]:
                all_quality_issues.append((py_file.name, issue))
                print(f"    ⚠️  {issue}")

        # 3. 编码检查
        encoding = check_encoding_consistency(py_file)
        print(f"    编码: {encoding['encoding']}", end="")
        if encoding["has_bom"]:
            print(", ⚠️  有 BOM", end="")
        if encoding["non_ascii_count"] > 0:
            print(f", 非 ASCII: {encoding['non_ascii_count']} 字符", end="")
        print()

        encoding_stats[encoding["encoding"]] += 1

        print()

    # 汇总报告
    print("=" * 70)
    print("📊 汇总报告")
    print("=" * 70)
    print()

    # 第三方库依赖
    if all_third_party:
        print("📦 第三方库依赖（按使用频率排序）:")
        for lib, count in sorted(all_third_party.items(), key=lambda x: -x[1]):
            print(f"  - {lib}: {count} 个文件使用")
        print()

    # 代码质量问题
    if all_quality_issues:
        print(f"⚠️  代码质量问题（共 {len(all_quality_issues)} 个）:")
        for filename, issue in all_quality_issues[:10]:
            print(f"  - {filename}: {issue}")
        if len(all_quality_issues) > 10:
            print(f"  ... 还有 {len(all_quality_issues) - 10} 个问题（略）")
        print()

    # 编码统计
    print("📝 文件编码统计:")
    for encoding, count in encoding_stats.items():
        print(f"  - {encoding}: {count} 个文件")
    print()

    print("=" * 70)


if __name__ == "__main__":
    main()
