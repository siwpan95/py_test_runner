# py_test_runner — Python 项目全覆盖测试框架

> 仓库：<https://gitee.com/siwpan/py_test_runner> ｜ 许可：MIT（见 [LICENSE](LICENSE)）
> 注：文中 <PATH> 为路径占位符，请替换为你本机实际的目录 / 可执行文件路径。

> 多功能 Python 测试框架，支持静态扫描、架构检测、动态运行三大类测试。
> 由全哥创建，用于 G 盘项目（10,700+ Python 文件）的日常质量保障。

---

## 快速开始

```bash
cd <PATH>

python main.py -c                # 控制台模式（最常用）
python main.py --smoke -c        # 探针冒烟测试
python main.py --allin -c         # 全项目扫描（P1 快速）
python main.py --arch -c          # 架构模式检测
python main.py --dynamic -c       # 动态测试（尝试运行）
python main.py --simple -c        # 简单测试：编译 + JSON 校验
python main.py --simple -c --simple-target <PATH>
```

---

## 功能模式一览

| 模式 | 命令 | 说明 |
|------|------|------|
| 控制台模式 | `python main.py -c` | 运行内置测试用例 |
| GUI 模式 | `python main.py` | Tkinter Canvas 可视化界面 |
| 探针模式 | `python main.py --smoke -c` | 冒烟测试（P1 关键探针） |
| OK 库扫描 | `python main.py --ok -c` | 扫描 `not/OK` 下所有项目 |
| draw 项目 | `python main.py --draw -c` | 深度扫描 ECS 架构项目 |
| 全项目扫描 | `python main.py --allin -c` | 递归扫描 `<PATH>` 全部目录 |
| 架构检测 | `python main.py --arch -c` | 识别 13 种架构模式 |
| 动态测试 | `python main.py --dynamic -c` | 尝试导入并运行 Python 文件 |

---

## 文档

| 文档 | 说明 |
|------|------|
| [docs/user_manual.md](docs/user_manual.md) | 完整使用手册（全参数说明、各模式详解、常见工作流、故障排查） |
| [docs/architecture_patterns.md](docs/architecture_patterns.md) | 架构模式详解（13 种模式原理、适用场景、检测依据） |

---

## 项目结构

```
py_testrunner/
├── main.py              # 入口
├── README.md            # 本文件
├── requirements.txt
├── core/               # 核心引擎（日志、错误类型、测试运行器、探针系统）
├── gui/                # Tkinter Canvas 图形界面
├── console/            # 控制台界面
├── logs/               # 日志 & 测试报告输出
├── scanners/           # 扫描器（全项目、架构检测、动态测试）
├── probes/             # 探针定义（通用、OK 库、draw 项目）
├── reports/            # 报告生成器（HTML/JSON、coverage）
├── tests/              # 测试脚本（自用）
└── docs/               # 文档（使用手册、架构模式详解）
```

---

## 依赖

**必需（标准库）**：`tkinter` · `ast` · `subprocess` · `dataclasses`

> ⚠️ `tkinter` 在 WorkBuddy managed Python 中不含，动态测试会自动回退到系统 Python。

**可选**：`coverage`（覆盖率）、`matplotlib`（图表）

---

*内部项目，全哥创建。*
