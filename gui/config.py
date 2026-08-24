r"""
GUI 配置 — 集中的颜色、字体、尺寸定义。

设计参考原 allin 项目群的一致风格。
"""


class Colors:
    """全局色板"""
    # 背景色
    BG_DARK = "#0f0f1a"          # 最深背景
    BG_PANEL = "#1a1a2e"         # 面板背景
    BG_CARD = "#16213e"          # 卡片背景
    BG_HOVER = "#1f2d4a"         # 悬停

    # 功能色
    PRIMARY = "#4fc3f7"          # 主色调（蓝）
    SECONDARY = "#81c784"        # 辅色调（绿）
    ACCENT = "#ffb74d"           # 强调色（橙）

    # 状态色
    PASS_GREEN = "#66bb6a"       # 通过
    FAIL_RED = "#ef5350"         # 失败
    ERROR_PURPLE = "#ce93d8"     # 错误
    SKIP_YELLOW = "#ffca28"      # 跳过
    RUNNING_BLUE = "#42a5f5"     # 运行中

    # 文字色
    TEXT_PRIMARY = "#eceff1"
    TEXT_SECONDARY = "#90a4ae"
    TEXT_MUTED = "#546e7a"

    # 边框
    BORDER = "#263850"
    DIVIDER = "#1e2d45"


class Fonts:
    """字体配置"""
    FAMILY = "Consolas"
    TITLE = (FAMILY, 18, "bold")
    SUBTITLE = (FAMILY, 14, "bold")
    BODY = (FAMILY, 11)
    SMALL = (FAMILY, 9)
    MONO = ("Courier New", 10)
    MONO_SMALL = ("Courier New", 9)


class Sizes:
    """尺寸常量"""
    WINDOW_W = 1000
    WINDOW_H = 700
    HEADER_H = 50
    STATS_W = 280
    FOOTER_H = 30
    LOG_H = 180
    CARD_H = 36
    CARD_PAD = 4
    RADIUS = 6                # 圆角半径
    PADDING = 12
