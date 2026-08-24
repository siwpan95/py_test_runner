"""
Canvas 测试视图 — 基于 tkinter Canvas 的测试结果可视化界面。

架构：
    CanvasTestView 使用多个 Canvas 组件绘制所有界面元素，
    包括自定义样式按钮、状态卡片、统计图表、日志面板。

设计理念：
    - 全部使用 Canvas 绘制，不依赖标准 tkinter widget 样式
    - 颜色编码错误类型，一目了然
    - 支持滚动的测试结果列表
    - 实时日志输出
"""

import tkinter as tk
from tkinter import font as tkfont
from typing import List, Optional, Callable
from datetime import datetime

from gui.config import Colors, Fonts, Sizes
from core.error_types import ErrorCode, TestError, ErrorCategory
from core.log_manager import LogManager


class CanvasTestView:
    """基于 Canvas 的测试 GUI 视图"""

    def __init__(self, root: tk.Tk, log_manager: LogManager):
        self.root = root
        self.log = log_manager

        # 状态
        self._results: List[TestError] = []
        self._running = False
        self._selected_index: Optional[int] = None

        # 回调
        self._on_run: Optional[Callable] = None
        self._on_view_log: Optional[Callable] = None

        self._setup_window()
        self._create_layout()

        # 注册日志回调
        self.log.on_log(self._append_log_line)
        self.log.on_error(self._on_result_arrived)

        # 键盘
        self.root.bind("<Escape>", lambda e: self.root.destroy())

    # ── 窗口设置 ──
    def _setup_window(self):
        self.root.title("测试框架 — tkinter Canvas 版")
        self.root.geometry(f"{Sizes.WINDOW_W}x{Sizes.WINDOW_H}")
        self.root.configure(bg=Colors.BG_DARK)
        self.root.minsize(800, 500)

        # 居中
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - Sizes.WINDOW_W) // 2
        y = (sh - Sizes.WINDOW_H) // 2
        self.root.geometry(f"+{x}+{y}")

    def set_callbacks(
        self,
        on_run: Optional[Callable] = None,
        on_view_log: Optional[Callable] = None,
    ):
        self._on_run = on_run
        self._on_view_log = on_view_log

    # ── 布局 ──
    def _create_layout(self):
        """创建整体布局：Header | Stats + Results | Log | Footer"""
        self._create_header()
        self._create_stats_panel()
        self._create_results_panel()
        self._create_log_panel()
        self._create_footer()

        # 配置网格权重
        self.root.grid_rowconfigure(1, weight=1)      # 中间区域伸展
        self.root.grid_rowconfigure(2, weight=0)      # 日志区固定高度
        self.root.grid_columnconfigure(1, weight=1)   # 结果区伸展

    # ── Header ──
    def _create_header(self):
        h = Sizes.HEADER_H
        self.header_canvas = tk.Canvas(
            self.root,
            height=h,
            bg=Colors.BG_PANEL,
            highlightthickness=0,
        )
        self.header_canvas.grid(row=0, column=0, columnspan=2, sticky="ew")

        # 渐变背景
        self._draw_gradient(self.header_canvas, 0, 0, Sizes.WINDOW_W, h,
                            Colors.BG_PANEL, "#111128")

        # 标题
        self.header_canvas.create_text(
            Sizes.PADDING + 4, h // 2,
            text="🧪 测试框架",
            anchor="w",
            fill=Colors.PRIMARY,
            font=Fonts.TITLE,
        )

        # 版本号
        self.header_canvas.create_text(
            Sizes.PADDING + 170, h // 2,
            text="v1.0  |  tkinter Canvas",
            anchor="w",
            fill=Colors.TEXT_MUTED,
            font=Fonts.SMALL,
        )

        # ── 按钮：运行全部 ──
        btn_w, btn_h = 130, 32
        btn_x = Sizes.WINDOW_W - Sizes.PADDING - btn_w - 100
        btn_y = (h - btn_h) // 2
        self._btn_run = self._create_button(
            self.header_canvas,
            btn_x, btn_y, btn_w, btn_h,
            text="▶  运行全部",
            fill=Colors.SECONDARY,
            command=self._handle_run,
        )

        # ── 按钮：查看日志 ──
        btn2_x = Sizes.WINDOW_W - Sizes.PADDING - 85
        self._btn_log = self._create_button(
            self.header_canvas,
            btn2_x, btn_y, 80, btn_h,
            text="📋 日志",
            fill=Colors.PRIMARY,
            command=self._handle_view_log,
        )

    # ── 统计面板 ──
    def _create_stats_panel(self):
        self.stats_frame = tk.Frame(self.root, bg=Colors.BG_DARK)
        self.stats_frame.grid(row=1, column=0, sticky="ns", padx=(0, 2))
        self.stats_frame.grid_propagate(False)
        self.stats_frame.config(width=Sizes.STATS_W)

        self.stats_canvas = tk.Canvas(
            self.stats_frame,
            bg=Colors.BG_DARK,
            highlightthickness=0,
        )
        self.stats_canvas.pack(fill="both", expand=True)

        # 初始绘制
        self._draw_stats_placeholder()

    def _draw_stats_placeholder(self):
        """绘制统计面板初始状态"""
        c = self.stats_canvas
        c.delete("all")
        w = Sizes.STATS_W
        pad = Sizes.PADDING

        # 标题
        c.create_text(
            pad, pad,
            text="📊 测试统计",
            anchor="nw",
            fill=Colors.TEXT_PRIMARY,
            font=Fonts.SUBTITLE,
        )

        # 分割线
        c.create_line(pad, pad + 28, w - pad, pad + 28,
                       fill=Colors.DIVIDER, width=1)

        # 占位文字
        c.create_text(
            w // 2, 120,
            text="等待执行...",
            fill=Colors.TEXT_MUTED,
            font=Fonts.BODY,
        )

        # 图例
        legend_y = 180
        legends = [
            ("✅ 通过", Colors.PASS_GREEN),
            ("❌ 失败", Colors.FAIL_RED),
            ("💥 错误", Colors.ERROR_PURPLE),
            ("⏭️ 跳过", Colors.SKIP_YELLOW),
        ]
        for i, (label, color) in enumerate(legends):
            y = legend_y + i * 22
            c.create_rectangle(pad, y, pad + 14, y + 14,
                               fill=color, outline="")
            c.create_text(pad + 22, y + 8,
                          text=label, anchor="w",
                          fill=Colors.TEXT_SECONDARY, font=Fonts.SMALL)

    def _draw_stats(self, summary: dict):
        """更新统计面板"""
        c = self.stats_canvas
        c.delete("all")
        w = Sizes.STATS_W
        pad = Sizes.PADDING

        total = summary.get("total", 0)
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        errored = summary.get("errored", 0)
        skipped = summary.get("skipped", 0)

        # 标题
        c.create_text(pad, pad, text="📊 测试统计", anchor="nw",
                       fill=Colors.TEXT_PRIMARY, font=Fonts.SUBTITLE)

        # 分割线
        c.create_line(pad, pad + 28, w - pad, pad + 28,
                       fill=Colors.DIVIDER, width=1)

        y = pad + 42

        # 各项统计（大字）
        stats = [
            ("总计", total, Colors.TEXT_PRIMARY),
            ("通过", passed, Colors.PASS_GREEN),
            ("失败", failed, Colors.FAIL_RED),
            ("错误", errored, Colors.ERROR_PURPLE),
            ("跳过", skipped, Colors.SKIP_YELLOW),
        ]
        for label, count, color in stats:
            c.create_text(pad, y, text=label, anchor="w",
                          fill=Colors.TEXT_SECONDARY, font=Fonts.BODY)
            c.create_text(w - pad, y, text=str(count), anchor="e",
                          fill=color, font=Fonts.SUBTITLE)
            y += 30

        # ── 进度条 ──
        y += 8
        bar_x = pad
        bar_w = w - pad * 2
        bar_h = 22
        bar_y = y

        # 背景条
        c.create_rectangle(bar_x, bar_y, bar_x + bar_w, bar_y + bar_h,
                           fill=Colors.BG_PANEL, outline=Colors.BORDER)

        if total > 0:
            # 分段绘制
            segments = [
                (passed, Colors.PASS_GREEN),
                (failed, Colors.FAIL_RED),
                (errored, Colors.ERROR_PURPLE),
                (skipped, Colors.SKIP_YELLOW),
            ]
            seg_x = bar_x
            for count, color in segments:
                if count > 0:
                    seg_w = (count / total) * bar_w
                    self._draw_rounded_rect(
                        c, seg_x, bar_y, seg_x + seg_w, bar_y + bar_h,
                        fill=color, outline=""
                    )
                    seg_x += seg_w

        # 百分比文字
        pct = f"{passed/total*100:.1f}%" if total > 0 else "0%"
        c.create_text(bar_x + bar_w // 2, bar_y + bar_h // 2,
                       text=pct,
                       fill=Colors.TEXT_PRIMARY, font=Fonts.SMALL)

        # ── 图例 ──
        y = bar_y + bar_h + 20
        legends = [
            ("✅ 通过", Colors.PASS_GREEN),
            ("❌ 失败", Colors.FAIL_RED),
            ("💥 错误", Colors.ERROR_PURPLE),
            ("⏭️ 跳过", Colors.SKIP_YELLOW),
        ]
        for i, (label, color) in enumerate(legends):
            ly = y + i * 22
            c.create_rectangle(pad, ly, pad + 14, ly + 14,
                               fill=color, outline="")
            c.create_text(pad + 22, ly + 8, text=label, anchor="w",
                          fill=Colors.TEXT_SECONDARY, font=Fonts.SMALL)

    # ── 结果列表面板 ──
    def _create_results_panel(self):
        # 外层容器
        self.results_frame = tk.Frame(self.root, bg=Colors.BG_DARK)
        self.results_frame.grid(row=1, column=1, sticky="nsew")
        self.results_frame.grid_rowconfigure(0, weight=1)
        self.results_frame.grid_columnconfigure(0, weight=1)

        # 带滚动条的 Canvas
        self.results_canvas = tk.Canvas(
            self.results_frame,
            bg=Colors.BG_DARK,
            highlightthickness=0,
        )
        self.results_scrollbar = tk.Scrollbar(
            self.results_frame,
            orient="vertical",
            command=self.results_canvas.yview,
            bg=Colors.BG_PANEL,
            troughcolor=Colors.BG_DARK,
            activebackground=Colors.BG_HOVER,
        )
        self.results_canvas.configure(yscrollcommand=self.results_scrollbar.set)

        self.results_scrollbar.grid(row=0, column=1, sticky="ns")
        self.results_canvas.grid(row=0, column=0, sticky="nsew")

        # 结果绘制容器
        self.results_inner = tk.Frame(self.results_canvas, bg=Colors.BG_DARK)
        self.results_window = self.results_canvas.create_window(
            (0, 0), window=self.results_inner, anchor="nw", tags="results_window"
        )

        # 绑定大小调整
        self.results_inner.bind("<Configure>", self._on_results_configure)
        self.results_canvas.bind("<Configure>", self._on_canvas_configure)

        # 鼠标滚轮
        self.results_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.results_inner.bind("<MouseWheel>", self._on_mousewheel)

        # 初始标题
        self._results_title = tk.Label(
            self.results_inner,
            text="📋 测试结果",
            bg=Colors.BG_DARK,
            fg=Colors.TEXT_PRIMARY,
            font=Fonts.SUBTITLE,
        )
        self._results_title.pack(anchor="nw", padx=Sizes.PADDING, pady=(Sizes.PADDING, 4))

        self._results_empty = tk.Label(
            self.results_inner,
            text="  点击「运行全部」开始测试...",
            bg=Colors.BG_DARK,
            fg=Colors.TEXT_MUTED,
            font=Fonts.BODY,
        )
        self._results_empty.pack(anchor="nw", padx=Sizes.PADDING)

    def _on_results_configure(self, event):
        self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.results_canvas.itemconfig(self.results_window, width=event.width)

    def _on_mousewheel(self, event):
        self.results_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _add_result_card(self, error: TestError, index: int):
        """在结果列表中添加一张结果卡片"""
        cat = error.error_code.category
        color_map = {
            ErrorCategory.PASS: Colors.PASS_GREEN,
            ErrorCategory.FAIL: Colors.FAIL_RED,
            ErrorCategory.ERROR: Colors.ERROR_PURPLE,
            ErrorCategory.SKIP: Colors.SKIP_YELLOW,
        }
        color = color_map.get(cat, Colors.TEXT_MUTED)

        card = tk.Frame(
            self.results_inner,
            bg=Colors.BG_CARD,
            height=Sizes.CARD_H,
        )
        card.pack(fill="x", padx=Sizes.PADDING, pady=Sizes.CARD_PAD // 2)
        card.pack_propagate(False)

        # 左侧状态指示条
        indicator = tk.Frame(card, bg=color, width=4)
        indicator.pack(side="left", fill="y")

        # 内容
        content = tk.Frame(card, bg=Colors.BG_CARD)
        content.pack(side="left", fill="both", expand=True, padx=(8, 0))

        emoji = error.error_code.emoji
        name = error.test_name[:35]
        code = error.error_code.code
        msg = error.message[:50]

        tk.Label(
            content, text=f"{emoji} {name}",
            bg=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY,
            font=Fonts.SMALL, anchor="w",
        ).pack(side="top", fill="x")

        tk.Label(
            content, text=f"{code}  {msg}",
            bg=Colors.BG_CARD, fg=Colors.TEXT_SECONDARY,
            font=Fonts.MONO_SMALL, anchor="w",
        ).pack(side="top", fill="x")

        # 右侧错误码标签
        code_label = tk.Label(
            card, text=code,
            bg=Colors.BG_CARD, fg=color,
            font=Fonts.MONO_SMALL,
        )
        code_label.pack(side="right", padx=8)

        # 点击查看详情
        card.bind("<Button-1>", lambda e, i=index: self._select_card(i))
        content.bind("<Button-1>", lambda e, i=index: self._select_card(i))

    def _select_card(self, index: int):
        self._selected_index = index

    def _clear_results(self):
        """清空结果列表"""
        self._results = []
        self._selected_index = None
        for w in self.results_inner.winfo_children():
            w.destroy()
        self._results_title = tk.Label(
            self.results_inner,
            text="📋 测试结果",
            bg=Colors.BG_DARK,
            fg=Colors.TEXT_PRIMARY,
            font=Fonts.SUBTITLE,
        )
        self._results_title.pack(anchor="nw", padx=Sizes.PADDING, pady=(Sizes.PADDING, 4))

    def _on_result_arrived(self, error: TestError):
        """接收到单条测试结果"""
        self._results.append(error)
        self._add_result_card(error, len(self._results) - 1)
        # 自动滚动到底部
        self.root.after_idle(lambda: self.results_canvas.yview_moveto(1.0))

    # ── 日志面板 ──
    def _create_log_panel(self):
        h = Sizes.LOG_H
        self.log_frame = tk.Frame(self.root, bg=Colors.BG_DARK, height=h)
        self.log_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.log_frame.grid_propagate(False)

        # 标题条
        title_bar = tk.Frame(self.log_frame, bg=Colors.BG_PANEL, height=26)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        tk.Label(
            title_bar, text="  📝 日志输出",
            bg=Colors.BG_PANEL, fg=Colors.TEXT_SECONDARY,
            font=Fonts.SMALL, anchor="w",
        ).pack(side="left", padx=4)

        # 清空按钮
        tk.Label(
            title_bar, text="清空 ",
            bg=Colors.BG_PANEL, fg=Colors.PRIMARY,
            font=Fonts.SMALL, cursor="hand2",
        ).pack(side="right", padx=4)
        title_bar.bind("<Button-1>", lambda e: self._clear_log())

        # 日志文本区
        log_container = tk.Frame(self.log_frame, bg=Colors.BG_DARK)
        log_container.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            log_container,
            bg=Colors.BG_DARK,
            fg=Colors.TEXT_SECONDARY,
            font=Fonts.MONO,
            wrap="word",
            state="disabled",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=Sizes.PADDING,
            pady=4,
        )
        self.log_scroll = tk.Scrollbar(
            log_container,
            command=self.log_text.yview,
            bg=Colors.BG_PANEL,
            troughcolor=Colors.BG_DARK,
        )
        self.log_text.configure(yscrollcommand=self.log_scroll.set)

        self.log_scroll.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True)

        # 颜色标签
        self.log_text.tag_configure("info", foreground=Colors.TEXT_SECONDARY)
        self.log_text.tag_configure("warn", foreground=Colors.SKIP_YELLOW)
        self.log_text.tag_configure("error", foreground=Colors.FAIL_RED)
        self.log_text.tag_configure("pass", foreground=Colors.PASS_GREEN)
        self.log_text.tag_configure("header", foreground=Colors.PRIMARY)

    def _append_log_line(self, line: str):
        """追加日志行到 Text 组件"""
        self.log_text.configure(state="normal")

        # 根据内容选标签
        if "ERROR" in line:
            tag = "error"
        elif "WARN" in line:
            tag = "warn"
        elif "通过" in line or "PASS" in line:
            tag = "pass"
        elif "━" in line:
            tag = "header"
        else:
            tag = "info"

        self.log_text.insert("end", line + "\n", tag)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # ── Footer ──
    def _create_footer(self):
        h = Sizes.FOOTER_H
        self.footer_canvas = tk.Canvas(
            self.root,
            height=h,
            bg=Colors.BG_PANEL,
            highlightthickness=0,
        )
        self.footer_canvas.grid(row=3, column=0, columnspan=2, sticky="ew")

        self._footer_status = self.footer_canvas.create_text(
            Sizes.PADDING, h // 2,
            text="就绪",
            anchor="w",
            fill=Colors.TEXT_MUTED,
            font=Fonts.SMALL,
        )

        self._footer_time = self.footer_canvas.create_text(
            Sizes.WINDOW_W - Sizes.PADDING, h // 2,
            text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            anchor="e",
            fill=Colors.TEXT_MUTED,
            font=Fonts.SMALL,
        )

    def set_status(self, text: str):
        self.footer_canvas.itemconfig(self._footer_status, text=text)

    def set_running(self, running: bool):
        self._running = running
        if running:
            self.set_status("运行中...")
            self._clear_results()
        else:
            self.set_status("完成")

    # ── Canvas 绘制工具 ──
    def _create_button(self, canvas, x, y, w, h, text, fill, command):
        """Canvas 自定义按钮"""
        radius = 4
        # 按钮背景
        btn = self._draw_rounded_rect(canvas, x, y, x + w, y + h,
                                      fill=fill, outline=fill, radius=radius)
        # 文字
        txt = canvas.create_text(
            x + w // 2, y + h // 2,
            text=text,
            fill=Colors.TEXT_PRIMARY,
            font=Fonts.SMALL,
        )

        # 绑定事件
        for item in (btn, txt):
            canvas.tag_bind(item, "<Button-1>", lambda e: command())
            canvas.tag_bind(item, "<Enter>",
                           lambda e, c=canvas, b=btn, f=fill:
                           c.itemconfig(b, fill=self._lighten(f, 0.2)))
            canvas.tag_bind(item, "<Leave>",
                           lambda e, c=canvas, b=btn, f=fill:
                           c.itemconfig(b, fill=f))

        return btn

    def _draw_rounded_rect(self, canvas, x1, y1, x2, y2, fill, outline, radius=6):
        """绘制圆角矩形"""
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return canvas.create_polygon(points, fill=fill, outline=outline,
                                     smooth=True, width=1)

    def _draw_gradient(self, canvas, x1, y1, x2, y2, color_top, color_bottom):
        """绘制垂直渐变"""
        steps = 20
        height = y2 - y1
        step_h = height / steps
        for i in range(steps):
            ratio = i / (steps - 1)
            r = self._interp_color(color_top, color_bottom, ratio)
            canvas.create_rectangle(
                x1, y1 + i * step_h,
                x2, y1 + (i + 1) * step_h,
                fill=r, outline="",
            )

    @staticmethod
    def _interp_color(c1, c2, ratio):
        """颜色插值"""
        r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
        r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _lighten(hex_color, amount):
        """颜色变亮"""
        r = min(255, int(int(hex_color[1:3], 16) * (1 + amount)))
        g = min(255, int(int(hex_color[3:5], 16) * (1 + amount)))
        b = min(255, int(int(hex_color[5:7], 16) * (1 + amount)))
        return f"#{r:02x}{g:02x}{b:02x}"

    # ── 事件处理 ──
    def _handle_run(self):
        if self._on_run:
            self._on_run()

    def _handle_view_log(self):
        if self._on_view_log:
            self._on_view_log()

    # ── 公共方法 ──
    def update_stats(self, summary: dict):
        self._draw_stats(summary)

    def show_result_detail(self, error: TestError):
        """在文本区展示错误详情"""
        self.log_text.configure(state="normal")
        self.log_text.insert("end", "\n" + error.detail() + "\n", "error")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def run(self):
        self.root.mainloop()
