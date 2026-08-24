"""
示例测试用例 — 展示各种错误类型和断言方法。

结构：
    每个函数名以 test_ 开头，符合 pytest 风格。
    直接使用 assert 或内置断言函数。
"""

import time
import math


# ═══════════════════════════════════════════════
#  通过 — 基础功能测试
# ═══════════════════════════════════════════════

def test_math_add():
    """测试加法运算"""
    assert 1 + 1 == 2


def test_math_multiply():
    """测试乘法运算"""
    assert 3 * 7 == 21


def test_string_concat():
    """测试字符串拼接"""
    result = "Hello" + " " + "World"
    assert result == "Hello World"


def test_list_operations():
    """测试列表操作"""
    lst = [1, 2, 3]
    lst.append(4)
    assert len(lst) == 4
    assert lst[-1] == 4


def test_dict_operations():
    """测试字典操作"""
    d = {"a": 1, "b": 2}
    assert "a" in d
    assert d.get("c", 0) == 0


def test_set_operations():
    """测试集合操作"""
    a = {1, 2, 3}
    b = {3, 4, 5}
    assert a & b == {3}
    assert a | b == {1, 2, 3, 4, 5}


def test_float_comparison():
    """测试浮点比较"""
    result = 0.1 + 0.2
    assert abs(result - 0.3) < 1e-9


def test_sqrt_calculation():
    """测试平方根计算"""
    assert math.isclose(math.sqrt(16), 4.0)


def test_slice_operations():
    """测试切片操作"""
    data = list(range(10))
    assert data[2:5] == [2, 3, 4]
    assert data[::-1] == [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]


def test_generator_expression():
    """测试生成器表达式"""
    squares = sum(x * x for x in range(5))
    assert squares == 30


# ═══════════════════════════════════════════════
#  失败 — 断言失败示例
# ═══════════════════════════════════════════════

def test_fail_assert_equal():
    """【演示-失败】断言相等失败"""
    assert 2 + 2 == 5, "期望 2+2=5，但实际得到 4"


def test_fail_assert_in():
    """【演示-失败】断言包含失败"""
    fruits = ["apple", "banana"]
    assert "orange" in fruits, "期望 orange 在水果列表中"


def test_fail_unexpected_result():
    """【演示-失败】意外返回值"""
    def broken_add(a, b):
        return a * b  # bug: 应该是 + 不是 *
    assert broken_add(3, 4) == 7, "期望 3+4=7，但函数实现有 bug"


# ═══════════════════════════════════════════════
#  错误 — 运行时错误示例
# ═══════════════════════════════════════════════

def test_error_zero_division():
    """【演示-错误】除零错误"""
    result = 1 / 0


def test_error_key_not_found():
    """【演示-错误】键错误"""
    d = {"name": "test"}
    value = d["age"]  # 不存在


def test_error_index_out_of_range():
    """【演示-错误】索引越界"""
    lst = [1, 2, 3]
    item = lst[10]


def test_error_attribute_missing():
    """【演示-错误】属性错误"""
    x = 42
    x.append(1)  # int 没有 append


def test_error_type_mismatch():
    """【演示-错误】类型错误"""
    result = "hello" + 42  # str + int


def test_error_value_invalid():
    """【演示-错误】值错误"""
    num = int("not_a_number")


def test_error_name_undefined():
    """【演示-错误】变量未定义"""
    result = undefined_variable


# ═══════════════════════════════════════════════
#  跳过 — 条件跳过示例
# ═══════════════════════════════════════════════

def test_skip_condition():
    """【演示-跳过】条件不满足"""
    import os
    token = os.environ.get("API_TOKEN")
    if not token:
        import pytest
        pytest.skip("缺少 API_TOKEN 环境变量")
    assert len(token) > 0


# ═══════════════════════════════════════════════
#  性能 — 耗时测试示例
# ═══════════════════════════════════════════════

def test_performance_sort():
    """测试排序性能"""
    data = list(range(10000, 0, -1))
    start = time.perf_counter()
    sorted_data = sorted(data)
    elapsed = time.perf_counter() - start
    assert sorted_data == list(range(1, 10001))
    assert elapsed < 0.1, f"排序耗时 {elapsed:.4f}s，超出 100ms 限制"


# ═══════════════════════════════════════════════
#  测试套件组织
# ═══════════════════════════════════════════════

# 全部测试（按顺序执行）
ALL_TESTS = [
    # ── 通过 ──
    test_math_add,
    test_math_multiply,
    test_string_concat,
    test_list_operations,
    test_dict_operations,
    test_set_operations,
    test_float_comparison,
    test_sqrt_calculation,
    test_slice_operations,
    test_generator_expression,
    test_performance_sort,
    # ── 失败 ──
    test_fail_assert_equal,
    test_fail_assert_in,
    test_fail_unexpected_result,
    # ── 错误 ──
    test_error_zero_division,
    test_error_key_not_found,
    test_error_index_out_of_range,
    test_error_attribute_missing,
    test_error_type_mismatch,
    test_error_value_invalid,
    test_error_name_undefined,
]

# 仅通过测试（用于快速验证）
PASSING_TESTS = [
    test_math_add,
    test_math_multiply,
    test_string_concat,
    test_list_operations,
    test_dict_operations,
    test_set_operations,
    test_float_comparison,
    test_sqrt_calculation,
    test_slice_operations,
    test_generator_expression,
    test_performance_sort,
]

# 错误演示套件
DEMO_TESTS = [
    test_math_add,
    test_string_concat,
    test_fail_assert_equal,
    test_error_zero_division,
    test_error_key_not_found,
]
