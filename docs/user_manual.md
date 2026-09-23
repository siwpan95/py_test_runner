# 使用手册 — py_test_runner

完整的使用指南，包含全部命令行参数说明、各模式详解和常见工作流。

---

## 目录

1. [安装与依赖](#安装与依赖)
2. [命令行参数全表](#命令行参数全表)
3. [各模式详解](#各模式详解)
4. [常见工作流](#常见工作流)
5. [输出解读](#输出解读)
6. [故障排查](#故障排查)

---

## 安装与依赖

### 必需依赖（Python 标准库）

| 模块 | 用途 | 备注 |
|------|------|------|
| `tkinter` | GUI 模式 / 动态测试 | **WorkBuddy managed Python 不含此库**，动态测试会自动回退到系统 Python |
| `ast` | 语法检查 / 架构检测 | 标准库 |
| `subprocess` | 动态测试（启动子进程） | 标准库 |
| `dataclasses` | 数据结构定义 | Python 3.7+ 标准库 |
| `json` / `hashlib` | 缓存和报告导出 | 标准库 |

### 可选依赖

```bash
# 覆盖率分析
pip install coverage

# 报告图表（可选）
pip install matplotlib
```

### 关于 tkinter 的说明

动态测试需要 `tkinter` 创建测试窗口。当前环境情况：

| Python 版本 | 来源 | tkinter |
|-------------|------|---------|
| 3.13.12 | WorkBuddy managed | ❌ 不含 |
| 3.14.4 | WorkBuddy managed | ❌ 不含 |
| 3.14.4 | 系统 Python | ✅ 含 |

**框架会自动检测**：动态测试时优先使用系统 Python（通常有 tkinter）。
也可通过 `--dynamic-python` 参数手动指定。

---

## 命令行参数全表

### 基础参数

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--console` | `-c` | 关闭 | 控制台模式（不启动 GUI 窗口） |
| `--timeout N` | — | 30 | 单测试用例超时时间（秒） |
| `--demo` | — | 关闭 | 仅运行演示测试用例（5 个，快速验证框架是否正常） |
| `--passing` | — | 关闭 | 仅运行已知通过的测试用例 |

**示例**：

```bash
# 控制台模式，超时 60 秒
python main.py -c --timeout 60

# 仅运行演示用例
python main.py -c --demo

# GUI 模式（默认）
python main.py
```

---

### 探针模式（`--smoke`）

| 参数 | 说明 |
|------|------|
| `--smoke` | 启用探针模式 |
| `--all` | 配合 `--smoke`，运行全量探针（默认仅运行 P1） |
| `--category CAT` | 按分类过滤探针（如 `file`、`import`、`env`） |
| `--draw-p1` | 配合 `--draw`，仅运行 P1 关键探针 |

**探针优先级**：

| 优先级 | 内容 | 建议 |
|---------|------|------|
| P1 | 环境检查、文件存在、语法检查 | 必须全部通过，日常每次运行 |
| P2~P3 | 导入检查、依赖分析 | 定期运行 |
| P4~P5 | 深度检查、项目特定规则 | 提交前运行 |

**示例**：

```bash
# P1 快速检查（默认）
python main.py --smoke -c

# 全量探针
python main.py --smoke --all -c

# 仅检查文件相关探针
python main.py --smoke --category file -c
```

---

### OK 库扫描（`--ok`）

扫描 `not/OK` 目录下所有项目（每个子目录视为一个独立项目）。

| 参数 | 说明 |
|------|------|
| `--ok` | 启用 OK 库扫描 |
| `--ok-priority N` | 仅运行指定优先级（1-5）的探针 |

**示例**：

```bash
# 扫描所有 OK 项目
python main.py --ok -c

# 仅运行 P1 探针（快速）
python main.py --ok --ok-priority 1 -c
```

---

### draw 项目扫描（`--draw`）

针对 `not/OK/draw` 项目（ECS 架构文字冒险游戏）设计的专用探针。

| 参数 | 说明 |
|------|------|
| `--draw` | 启用 draw 项目扫描 |
| `--draw-p1` | 仅运行 P1 关键探针（环境 + 文件 + 导入） |

**示例**：

```bash
# 全量 draw 探针
python main.py --draw -c

# 仅 P1（快速）
python main.py --draw --draw-p1 -c
```

---

### 全项目扫描（`--allin`）

递归扫描根目录下**所有** Python 文件。根目录由环境变量 **`SCAN_ROOT`** 指定；未设置时默认为**本仓的上一级目录**（一仓一目录的仓库根，`scanners/allin_scanner.py`、`probes/ok_probes.py` 同为该口径）。扫描规模随根目录而定。

| 参数 | 说明 |
|------|------|
| `--allin` | 启用全项目扫描 |
| `--allin-all` | 配合 `--allin`，运行 P2/P3 扫描（默认仅 P1） |
| `--allin-p1` | 配合 `--allin`，显式指定仅 P1（默认行为） |

**扫描层次说明**：

| 层次 | 内容 | 速度 | 建议频率 |
|------|------|------|-----------|
| P1（默认） | 文件存在、语法检查、编码检查 | 快（~30s） | 每次提交前 |
| P2（`--all`） | 导入检查、依赖分析、文件大小异常 | 中 | 每日一次 |
| P3（`--all`） | 目录结构统计、重复文件检测、复杂度分析 | 慢 | 每周一次 |

**示例**：

```bash
# P1 快速扫描（推荐日常使用）
python main.py --allin -c

# 全量扫描（P1 + P2 + P3）
python main.py --allin --allin-all -c

# 输出到文件
python main.py --allin -c > scan_result.txt
```

---

### 架构模式检测（`--arch`）

自动识别项目代码中的软件架构模式（共 13 种）。

| 参数 | 说明 |
|------|------|
| `--arch` | 启用架构模式检测 |
| `--arch-detail` | 显示详细结果（含匹配文件和证据） |

**检测原理**：
- **AST 分析**：解析 Python 代码，提取类名、函数名、导入语句
- **关键词匹配**：根据各架构的特征关键词判断
- **目录结构分析**：检查目录组织是否符合特定架构

**示例**：

```bash
# 简洁报告
python main.py --arch -c

# 详细报告（显示涉及的文件列表）
python main.py --arch --arch-detail -c

# 全项目扫描 + 架构检测
python main.py --allin --arch -c
```

各类架构模式的详细解释见 [架构模式详解](architecture_patterns.md)。

---

### 动态测试（`--dynamic`）

尝试实际**导入并运行** Python 文件，检查是否能正常启动。

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--dynamic` | — | 启用动态测试 |
| `--dynamic-timeout N` | 10 | 单文件超时时间（秒） |
| `--dynamic-parallel` | 关闭 | 启用多进程并行执行 |
| `--dynamic-workers N` | 4 | 并行进程数 |
| `--dynamic-incremental` | 关闭 | 增量扫描（基于 mtime + hash 缓存） |
| `--dynamic-python PATH` | 自动检测 | 手动指定 Python 解释器路径 |
| `--dynamic-project PATH` | 当前目录 | 指定被测项目目录 |

**增量扫描原理**：
- 基于文件修改时间（mtime）和内容的 MD5 hash 判断是否变更
- 未变更的文件直接读取上次缓存结果，跳过重复测试
- 首次运行建立缓存，后续运行极快（0.00s）

**示例**：

```bash
# 基本用法（测试当前目录）
python main.py --dynamic -c

# 指定项目目录
python main.py --dynamic --dynamic-project <项目目录> -c

# 并行执行（加速）
python main.py --dynamic --dynamic-parallel -c

# 增量扫描（跳过未变更文件）
python main.py --dynamic --dynamic-incremental -c

# 并行 + 增量（推荐组合）
python main.py --dynamic --dynamic-parallel --dynamic-incremental -c

# 自定义参数
python main.py --dynamic --dynamic-timeout 30 --dynamic-workers 8 -c

# 手动指定 Python（当自动检测失败时）
python main.py --dynamic --dynamic-python "<Python 解释器路径>" -c
```

---

## 各模式详解

### 控制台模式 vs GUI 模式

**控制台模式（`-c`）**：
- 输出到终端，适合脚本化/CI 环境
- 无头环境（无 Display）自动切换到此模式

**GUI 模式（默认）**：
- 使用 Tkinter Canvas 可视化界面
- 实时显示测试进度和结果
- 需要 Display（无头环境不可用）

---

### 探针系统

探针是比测试用例更轻量的检查单元，专注于**快速发现明显问题**。

**与测试用例的区别**：

| | 探针（Probe） | 测试用例（Test Case） |
|--|----------------|---------------------|
| 速度 | 极快（秒级） | 较慢（分钟级） |
| 深度 | 浅层检查 | 深度验证 |
| 用途 | 快速健康状态检查 | 功能正确性验证 |
| 示例 | 文件是否存在、语法是否正确 | 函数返回值是否符合预期 |

**探针分类**（以 OK 库探针为例）：

| 分类 | 说明 | 示例 |
|------|------|------|
| `env` | 环境检查 | Python 版本、依赖库是否存在 |
| `file` | 文件检查 | 入口文件是否存在、文件编码 |
| `syntax` | 语法检查 | Python 语法是否正确 |
| `import` | 导入检查 | 模块是否能成功导入 |
| `structure` | 结构检查 | 目录结构是否符合约定 |

---

### 全项目扫描的三层设计

`--allin` 模式设计为三层，平衡**覆盖深度**和**运行速度**：

**P1 — 关键层（默认运行）**：
- 文件存在性检查
- Python 语法正确性（`ast.parse`）
- 文件编码检查（是否为 UTF-8，有无 BOM）

**P2 — 重要层（`--allin-all`）**：
- 模块导入检查（能否成功 `import`）
- 依赖分析（使用了哪些第三方库）
- 文件大小异常检测（空文件或超大文件）

**P3 — 常规层（`--allin-all`）**：
- 目录结构统计
- 重复文件检测（基于内容 hash）
- 代码复杂度分析（圈复杂度）

---

## 常见工作流

### 工作流 1：提交前快速检查

```bash
# 步骤 1：探针快速检查（P1）
python main.py --smoke -c

# 步骤 2：如果探针通过，运行完整测试
python main.py -c

# 步骤 3：动态测试（检查 GUI 是否能启动）
python main.py --dynamic --dynamic-parallel -c
```

---

### 工作流 2：新项目接入检查

```bash
# 步骤 1：检查项目是否能导入
python main.py --dynamic --dynamic-project <新项目目录> -c

# 步骤 2：检测项目使用的架构模式
python main.py --arch --arch-detail --dynamic-project <新项目目录> -c

# 步骤 3：如果没问题，为该项目添加 OK 探针
# （编辑 ok_probes.py，添加新项目的探针生成逻辑）
```

---

### 工作流 3：定期全项目健康扫描

```bash
# 每周运行一次全量扫描
python main.py --allin --allin-all -c > weekly_scan_$(date +%Y%m%d).txt

# 架构模式变化追踪
python main.py --arch --arch-detail -c > arch_report_$(date +%Y%m%d).txt
```

---

### 工作流 4：CI/CD 集成

```bash
# 在 CI 环境中运行（无头，纯控制台）
python main.py -c --timeout 60

# 动态测试（使用系统 Python，跳过需要 Display 的测试）
python main.py --dynamic --dynamic-parallel --dynamic-timeout 5 -c

# 检查退出码
echo $?   # 0 = 全部通过，1 = 有失败
```

---

## 输出解读

### 探针输出格式

```
📍 [探针] OK/merged_gui — 目录存在         PROBE-PASS  (0.00s)
📍 [探针] OK/merged_gui — 入口文件         PROBE-PASS  (0.01s)
📍 [探针] OK/merged_gui — 语法           PROBE-FAIL  (0.05s)
    SyntaxError: invalid syntax (L34)
```

| 状态 | 含义 |
|------|------|
| `PROBE-PASS` | 探针通过 |
| `PROBE-FAIL` | 探针失败（检测到问题） |
| `PROBE-SKIP` | 探针跳过（条件不满足） |

### 架构检测输出格式

```
✅ MVC
   置信度: 100.0%
   说明: 检测到 Model-View-Controller 模式特征
   证据数: 5 条
   涉及文件: 57 个
```

| 置信度 | 含义 |
|--------|------|
| 100% | 明确检测到该模式的特征 |
| 50-99% | 疑似使用该模式（可能有误报） |
| <50% | 弱信号，建议人工确认 |

---

## 故障排查

### 问题 1：`tkinter` 不可用

**现象**：
```
导入失败: No module named 'tkinter'
```

**原因**：WorkBuddy managed Python 是精简版，不含 tkinter。

**解决**：
- 动态测试会自动回退到系统 Python（通常有 tkinter）
- 或手动指定：`--dynamic-python "<Python 解释器路径>"`

---

### 问题 2：动态测试超时

**现象**：
```
⚠️  python_file.py: 超时（>10秒）
```

**原因**：某些文件（如 `neural_text.py`）需要加载大模型，耗时较长。

**解决**：
```bash
# 增加超时时间
python main.py --dynamic --dynamic-timeout 60 -c

# 或跳过该文件（在 dynamic_tester.py 中添加 SKIP_LIST）
```

---

### 问题 3：架构检测误报

**现象**：检测到了某个架构模式，但你认为项目并未使用该模式。

**原因**：当前检测逻辑基于关键词匹配，可能存在误报。

**解决**：
- 使用 `--arch-detail` 查看具体证据
- 误报率较高的模式：MVI、事件溯源
- 可手动在 `architecture_detector.py` 中调整检测逻辑

---

### 问题 4：增量扫描缓存过期

**现象**：修改了文件但增量扫描仍然跳过。

**原因**：缓存基于 mtime + hash，某些情况下 mtime 可能不准确。

**解决**：
```bash
# 强制全量重测
python main.py --dynamic --dynamic-incremental -c
# （删除 logs/dynamic_cache.json 可清除缓存）

# 或直接强制
python main.py --dynamic -c
```

---

*文档版本：2026-06-19*
