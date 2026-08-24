"""
架构模式检测器 — 识别 Python 项目中的软件架构模式

支持的架构模式：
  UI/前端架构: MVC, MVP, MVVM, MVI, MVU, VIPER
  系统架构: 分层架构, 六边形架构, 微服务, 事件驱动, 微内核
  业务架构: CQRS, 事件溯源, DDD

使用方法：
  from architecture_detector import ArchitectureDetector

  detector = ArchitectureDetector()
  results = detector.scan_project(Path("D:/allin"))
  detector.print_report()
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


# ── 架构模式枚举 ────────────────────────────────────────────────────────────


class ArchitecturePattern(Enum):
    """支持的架构模式"""

    # UI/前端架构
    MVC = "MVC"
    MVP = "MVP"
    MVVM = "MVVM"
    MVI = "MVI"
    MVU = "MVU"
    VIPER = "VIPER"
    MVVM_C = "MVVM-C"

    # 系统架构
    LAYERED = "分层架构"
    HEXAGONAL = "六边形架构"
    MICROSERVICES = "微服务"
    EVENT_DRIVEN = "事件驱动"
    MICROKERNEL = "微内核"

    # 业务架构
    CQRS = "CQRS"
    EVENT_SOURCING = "事件溯源"
    DDD = "领域驱动设计(DDD)"


# ── 数据结构 ──────────────────────────────────────────────────────────────────


@dataclass
class PatternEvidence:
    """架构模式证据"""

    pattern: ArchitecturePattern
    confidence: float  # 置信度 0.0-1.0
    evidence: List[str] = field(default_factory=list)
    files: List[Path] = field(default_factory=list)
    description: str = ""


@dataclass
class ModuleInfo:
    """模块信息"""

    path: Path
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    has_model: bool = False
    has_view: bool = False
    has_controller: bool = False
    has_presenter: bool = False
    has_viewmodel: bool = False
    has_event: bool = False
    has_command: bool = False
    has_query: bool = False
    layers: Set[str] = field(default_factory=set)


# ── 检测器实现 ──────────────────────────────────────────────────────────────


class ArchitectureDetector:
    """架构模式检测器"""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()
        self.modules: List[ModuleInfo] = []
        self.pattern_evidences: List[PatternEvidence] = []
        self.file_patterns: Dict[Path, Set[ArchitecturePattern]] = defaultdict(set)

        # 关键词模式
        self._init_patterns()

    def _init_patterns(self):
        """初始化检测模式"""
        # MVC 模式关键词
        self.mvc_keywords = {
            "model": ["Model", "models", "Entity", "entities"],
            "view": ["View", "view", "Template", "template", "UI", "ui"],
            "controller": ["Controller", "controller", "Handler", "handler", "Route", "route"],
        }

        # MVP 模式关键词
        self.mvp_keywords = {
            "model": ["Model", "models", "Entity", "entities"],
            "view": ["View", "view", "Interface", "IView"],
            "presenter": ["Presenter", "presenter", "Presenter"],
        }

        # MVVM 模式关键词
        self.mvvm_keywords = {
            "model": ["Model", "models"],
            "view": ["View", "view", "Window", "window"],
            "viewmodel": ["ViewModel", "ViewModel", "VM", "vm"],
        }

        # 事件驱动关键词
        self.event_keywords = [
            "event",
            "Event",
            "subscribe",
            "publish",
            "emit",
            "on/",
            "listener",
            "Listener",
            "handler",
            "Handler",
            "dispatch",
            "Dispatch",
        ]

        # 分层架构关键词
        self.layer_keywords = {
            "presentation": ["view", "View", "ui", "UI", "controller", "Controller", "api", "API"],
            "business": ["service", "Service", "bll", "BLL", "domain", "Domain", "logic"],
            "persistence": [
                "repository",
                "Repository",
                "dao",
                "DAO",
                "model",
                "Model",
                "db",
                "DB",
                "persistence",
            ],
        }

        # MVI 关键词 (Model-View-Intent)
        self.mvi_keywords = ["intent", "Intent", "state", "State", "reduce", "Reducer"]

        # MVU 关键词 (Model-View-Update)
        self.mvu_keywords = ["update", "Update", "message", "Message", "dispatch"]

        # VIPER 关键词
        self.viper_keywords = [
            "interactor",
            "Interactor",
            "entity",
            "Entity",
            "router",
            "Router",
        ]

        # 六边形架构关键词 (端口-适配器)
        self.hexagonal_keywords = [
            "port",
            "Port",
            "adapter",
            "Adapter",
            "primary",
            "secondary",
        ]

        # 微内核关键词 (插件架构)
        self.microkernel_keywords = [
            "plugin",
            "Plugin",
            "extension",
            "Extension",
            "hook",
            "Hook",
        ]

        # 事件溯源关键词
        self.event_sourcing_keywords = [
            "event_store",
            "EventStore",
            "append",
            "replay",
            "snapshot",
            "Snapshot",
        ]

        # DDD 关键词 (领域驱动设计)
        self.ddd_keywords = [
            "aggregate",
            "Aggregate",
            "entity",
            "Entity",
            "value_object",
            "ValueObject",
            "repository",
            "Repository",
            "domain_service",
            "DomainService",
        ]

    def scan_project(self, root: Path | None = None) -> Dict[str, Any]:
        """
        扫描项目并检测架构模式

        Args:
            root: 项目根目录

        Returns:
            检测结果字典
        """
        root = root or self.project_root
        print(f"🔍 开始扫描项目: {root}")

        # 1. 发现所有 Python 文件
        py_files = list(root.rglob("*.py"))
        print(f"   发现 {len(py_files)} 个 Python 文件")

        # 2. 分析每个文件
        for py_file in py_files:
            try:
                module_info = self._analyze_file(py_file)
                if module_info:
                    self.modules.append(module_info)
            except Exception as e:
                # 忽略分析失败的文件
                pass

        print(f"   成功分析 {len(self.modules)} 个模块")

        # 3. 检测架构模式
        self._detect_patterns()

        # 4. 生成报告
        return self._generate_report()

    def _analyze_file(self, file_path: Path) -> Optional[ModuleInfo]:
        """
        分析单个 Python 文件

        Args:
            file_path: 文件路径

        Returns:
            ModuleInfo 或 None
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                source = f.read()

            tree = ast.parse(source)
            module_info = ModuleInfo(path=file_path)

            # 分析 AST
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    module_info.classes.append(node.name)
                    # 检查是否是架构相关类
                    self._check_arch_class(node.name, module_info)

                elif isinstance(node, ast.FunctionDef):
                    module_info.functions.append(node.name)

                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        module_info.imports.append(alias.name)

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_info.imports.append(node.module)

            # 基于文件名判断
            self._check_file_name(file_path, module_info)

            return module_info

        except SyntaxError:
            return None
        except Exception:
            return None

    def _check_arch_class(self, class_name: str, module_info: ModuleInfo):
        """检查类名是否包含架构关键词"""
        name_lower = class_name.lower()

        # MVC
        if any(k.lower() in name_lower for k in ["model", "entity"]):
            module_info.has_model = True
        if any(k.lower() in name_lower for k in ["view", "ui", "window"]):
            module_info.has_view = True
        if any(k.lower() in name_lower for k in ["controller", "handler", "route"]):
            module_info.has_controller = True

        # MVP
        if any(k.lower() in name_lower for k in ["presenter"]):
            module_info.has_presenter = True

        # MVVM
        if any(k.lower() in name_lower for k in ["viewmodel", "vm"]):
            module_info.has_viewmodel = True

        # 事件驱动
        if any(k.lower() in name_lower for k in ["event", "listener", "subscriber"]):
            module_info.has_event = True

        # CQRS
        if any(k.lower() in name_lower for k in ["command", "cmd"]):
            module_info.has_command = True
        if any(k.lower() in name_lower for k in ["query", "qry"]):
            module_info.has_query = True

    def _check_file_name(self, file_path: Path, module_info: ModuleInfo):
        """基于文件名判断架构角色"""
        name = file_path.stem.lower()
        parent = file_path.parent.name.lower()

        # 检查文件名
        if any(k in name for k in ["model", "entity"]):
            module_info.has_model = True
            module_info.layers.add("model")
        if any(k in name for k in ["view", "ui", "window"]):
            module_info.has_view = True
            module_info.layers.add("view")
        if any(k in name for k in ["controller", "handler", "route"]):
            module_info.has_controller = True
            module_info.layers.add("controller")
        if any(k in name for k in ["presenter"]):
            module_info.has_presenter = True
        if any(k in name for k in ["viewmodel", "vm"]):
            module_info.has_viewmodel = True

        # 检查父目录名（分层架构）
        if any(k in parent for k in ["view", "ui", "presentation", "api"]):
            module_info.layers.add("presentation")
        if any(k in parent for k in ["service", "bll", "domain", "business"]):
            module_info.layers.add("business")
        if any(k in parent for k in ["repository", "dao", "model", "db", "persistence"]):
            module_info.layers.add("persistence")

    def _detect_patterns(self):
        """检测架构模式"""
        # UI/前端架构
        self._detect_mvc()
        self._detect_mvp()
        self._detect_mvvm()
        self._detect_mvi()
        self._detect_mvu()
        self._detect_viper()

        # 系统架构
        self._detect_layered()
        self._detect_hexagonal()
        self._detect_microservices()
        self._detect_event_driven()
        self._detect_microkernel()

        # 业务架构
        self._detect_cqrs()
        self._detect_event_sourcing()
        self._detect_ddd()

    def _detect_mvc(self):
        """检测 MVC 模式"""
        evidence_files = []
        evidence_details = []

        for module in self.modules:
            # 检查是否同时包含 Model, View, Controller
            has_all = module.has_model and module.has_view and module.has_controller
            has_partial = (module.has_model and module.has_view) or (
                module.has_model and module.has_controller
            )

            if has_all:
                evidence_files.append(module.path)
                evidence_details.append(f"{module.path.name}: 包含 Model+View+Controller")
            elif has_partial and len(module.classes) >= 3:
                evidence_files.append(module.path)
                evidence_details.append(f"{module.path.name}: 可能包含 MVC 组件")

        if evidence_files:
            confidence = min(1.0, len(evidence_files) / 10.0)
            self.pattern_evidences.append(
                PatternEvidence(
                    pattern=ArchitecturePattern.MVC,
                    confidence=confidence,
                    evidence=evidence_details[:5],
                    files=evidence_files,
                    description="检测到 Model-View-Controller 模式特征",
                )
            )

            # 记录文件级别的检测
            for f in evidence_files:
                self.file_patterns[f].add(ArchitecturePattern.MVC)

    def _detect_mvp(self):
        """检测 MVP 模式"""
        evidence_files = []
        evidence_details = []

        for module in self.modules:
            if module.has_presenter and (module.has_model or module.has_view):
                evidence_files.append(module.path)
                evidence_details.append(f"{module.path.name}: 包含 Presenter + (Model/View)")

        if evidence_files:
            confidence = min(1.0, len(evidence_files) / 5.0)
            self.pattern_evidences.append(
                PatternEvidence(
                    pattern=ArchitecturePattern.MVP,
                    confidence=confidence,
                    evidence=evidence_details[:5],
                    files=evidence_files,
                    description="检测到 Model-View-Presenter 模式特征",
                )
            )

    def _detect_mvvm(self):
        """检测 MVVM 模式"""
        evidence_files = []
        evidence_details = []

        for module in self.modules:
            if module.has_viewmodel and (module.has_model or module.has_view):
                evidence_files.append(module.path)
                evidence_details.append(f"{module.path.name}: 包含 ViewModel + (Model/View)")

        if evidence_files:
            confidence = min(1.0, len(evidence_files) / 5.0)
            self.pattern_evidences.append(
                PatternEvidence(
                    pattern=ArchitecturePattern.MVVM,
                    confidence=confidence,
                    evidence=evidence_details[:5],
                    files=evidence_files,
                    description="检测到 Model-View-ViewModel 模式特征",
                )
            )

    def _detect_layered(self):
        """检测分层架构"""
        evidence_files = []
        evidence_details = []

        # 统计各层目录
        layer_dirs = defaultdict(set)

        for module in self.modules:
            layers = module.layers
            if layers:
                layer_dirs[tuple(sorted(layers))].add(module.path.parent)

        # 如果有多个层，可能是分层架构
        all_layers = set()
        for layers_tuple in layer_dirs.keys():
            all_layers.update(layers_tuple)

        if len(all_layers) >= 2:
            evidence_details.append(f"检测到多层结构: {', '.join(all_layers)}")
            evidence_files.extend([f for m in self.modules for f in [m.path] if m.layers])

            confidence = min(1.0, len(all_layers) / 3.0)
            self.pattern_evidences.append(
                PatternEvidence(
                    pattern=ArchitecturePattern.LAYERED,
                    confidence=confidence,
                    evidence=evidence_details,
                    files=evidence_files[:10],
                    description="检测到分层架构特征",
                )
            )

    def _detect_event_driven(self):
        """检测事件驱动架构"""
        evidence_files = []
        evidence_details = []

        for module in self.modules:
            # 检查事件相关关键词
            has_event_import = any(
                any(k in imp for k in ["event", "Event", "signal", "Signal"])
                for imp in module.imports
            )

            if module.has_event or has_event_import:
                evidence_files.append(module.path)
                evidence_details.append(f"{module.path.name}: 包含事件相关代码")

        if evidence_files:
            confidence = min(1.0, len(evidence_files) / 8.0)
            self.pattern_evidences.append(
                PatternEvidence(
                    pattern=ArchitecturePattern.EVENT_DRIVEN,
                    confidence=confidence,
                    evidence=evidence_details[:5],
                    files=evidence_files,
                    description="检测到事件驱动架构特征",
                )
            )

    def _detect_cqrs(self):
        """检测 CQRS 模式"""
        evidence_files = []
        evidence_details = []

        for module in self.modules:
            if module.has_command and module.has_query:
                evidence_files.append(module.path)
                evidence_details.append(f"{module.path.name}: 同时包含 Command 和 Query")

        if len(evidence_files) >= 2:
            confidence = min(1.0, len(evidence_files) / 5.0)
            self.pattern_evidences.append(
                PatternEvidence(
                    pattern=ArchitecturePattern.CQRS,
                    confidence=confidence,
                    evidence=evidence_details,
                    files=evidence_files,
                    description="检测到 CQRS (命令查询职责分离) 模式特征",
                )
            )

    def _detect_microservices(self):
        """检测微服务架构（基于目录结构）"""
        # 检查是否有多个独立服务目录
        service_dirs = []

        for item in self.project_root.iterdir():
            if item.is_dir() and any(
                svc in item.name.lower() for svc in ["service", "api", "micro"]
            ):
                service_dirs.append(item.name)

        if len(service_dirs) >= 2:
            confidence = min(1.0, len(service_dirs) / 5.0)
            self.pattern_evidences.append(
                PatternEvidence(
                    pattern=ArchitecturePattern.MICROSERVICES,
                    confidence=confidence,
                    evidence=[f"发现 {len(service_dirs)} 个服务目录: {', '.join(service_dirs[:5])}"],
                    files=[],
                    description="基于目录结构推测可能使用微服务架构",
                )
            )

    def _detect_mvi(self):
        """检测 MVI (Model-View-Intent) 模式"""
        evidence_files = []
        evidence_details = []

        for module in self.modules:
            # 检查是否包含 MVI 关键词
            has_intent = any(
                any(k.lower() in cls.lower() for k in self.mvi_keywords)
                for cls in module.classes
            )
            has_state = any(
                any(k.lower() in cls.lower() for k in ["state", "State"])
                for cls in module.classes
            )

            if has_intent and has_state:
                evidence_files.append(module.path)
                evidence_details.append(f"{module.path.name}: 包含 Intent + State (MVI 特征)")

        if len(evidence_files) >= 2:
            confidence = min(1.0, len(evidence_files) / 5.0)
            self.pattern_evidences.append(
                PatternEvidence(
                    pattern=ArchitecturePattern.MVI,
                    confidence=confidence,
                    evidence=evidence_details,
                    files=evidence_files,
                    description="检测到 Model-View-Intent (MVI) 模式特征（单向数据流）",
                )
            )

    def _detect_mvu(self):
        """检测 MVU (Model-View-Update) 模式"""
        evidence_files = []
        evidence_details = []

        for module in self.modules:
            # 检查是否包含 MVU 关键词
            has_update = any(
                any(k.lower() in cls.lower() for k in self.mvu_keywords)
                for cls in module.classes
            )
            has_message = any(
                any(k.lower() in cls.lower() for k in ["message", "msg"])
                for cls in module.classes
            )

            if has_update and has_message:
                evidence_files.append(module.path)
                evidence_details.append(f"{module.path.name}: 包含 Update + Message (MVU 特征)")

        if len(evidence_files) >= 2:
            confidence = min(1.0, len(evidence_files) / 5.0)
            self.pattern_evidences.append(
                PatternEvidence(
                    pattern=ArchitecturePattern.MVU,
                    confidence=confidence,
                    evidence=evidence_details,
                    files=evidence_files,
                    description="检测到 Model-View-Update (MVU) 模式特征（函数式更新）",
                )
            )

    def _detect_viper(self):
        """检测 VIPER (View-Interactor-Presenter-Entity-Router) 模式

        VIPER 通常按文件组织，每个组件一个文件：
        - XView.py
        - XInteractor.py
        - XPresenter.py
        - XEntity.py
        - XRouter.py
        """
        evidence_dirs = defaultdict(list)
        evidence_details = []

        # 按父目录分组文件
        dir_modules = defaultdict(list)
        for module in self.modules:
            dir_modules[module.path.parent].append(module)

        # 检查每个目录
        for dir_path, modules in dir_modules.items():
            # 统计该目录下的 VIPER 组件
            viper_components = {
                "View": 0,
                "Interactor": 0,
                "Presenter": 0,
                "Entity": 0,
                "Router": 0,
            }

            for module in modules:
                for cls in module.classes:
                    cls_lower = cls.lower()
                    if cls_lower.endswith("view"):
                        viper_components["View"] += 1
                    elif "interactor" in cls_lower:
                        viper_components["Interactor"] += 1
                    elif cls_lower.endswith("presenter"):
                        viper_components["Presenter"] += 1
                    elif cls_lower.endswith("entity"):
                        viper_components["Entity"] += 1
                    elif cls_lower.endswith("router"):
                        viper_components["Router"] += 1

            # 如果包含至少 3 个 VIPER 组件，则可能是 VIPER
            components_found = [k for k, v in viper_components.items() if v > 0]
            if len(components_found) >= 3:
                evidence_dirs[str(dir_path)].extend([m.path for m in modules])
                evidence_details.append(f"{dir_path.name}: 包含 VIPER 组件: {', '.join(components_found)}")

        # 汇总证据文件
        evidence_files = []
        for files in evidence_dirs.values():
            evidence_files.extend(files)

        if len(evidence_dirs) >= 1:
            confidence = min(1.0, len(evidence_dirs) / 3.0)
            self.pattern_evidences.append(
                PatternEvidence(
                    pattern=ArchitecturePattern.VIPER,
                    confidence=confidence,
                    evidence=evidence_details,
                    files=list(set(evidence_files)),
                    description="检测到 VIPER (View-Interactor-Presenter-Entity-Router) 模式特征",
                )
            )

    def _detect_hexagonal(self):
        """检测六边形架构 (Hexagonal Architecture / Ports and Adapters)"""
        evidence_files = []
        evidence_details = []

        for module in self.modules:
            # 检查是否包含端口-适配器关键词
            has_port = any(
                any(k.lower() in imp.lower() for k in self.hexagonal_keywords)
                for imp in module.imports
            )
            has_adapter = any(
                any(k.lower() in cls.lower() for k in ["adapter", "Adapter"])
                for cls in module.classes
            )

            if has_port or has_adapter:
                evidence_files.append(module.path)
                evidence_details.append(f"{module.path.name}: 包含端口/适配器模式")

        if len(evidence_files) >= 3:
            confidence = min(1.0, len(evidence_files) / 8.0)
            self.pattern_evidences.append(
                PatternEvidence(
                    pattern=ArchitecturePattern.HEXAGONAL,
                    confidence=confidence,
                    evidence=evidence_details,
                    files=evidence_files,
                    description="检测到六边形架构 (Ports and Adapters) 特征",
                )
            )

    def _detect_microkernel(self):
        """检测微内核架构 (Microkernel / Plugin Architecture)"""
        evidence_files = []
        evidence_details = []

        for module in self.modules:
            # 检查是否包含插件/扩展关键词
            has_plugin = any(
                any(k.lower() in cls.lower() for k in self.microkernel_keywords)
                for cls in module.classes
            )
            has_hook = any(
                any(k.lower() in imp.lower() for k in ["hook", "plugin", "extension"])
                for imp in module.imports
            )

            if has_plugin or has_hook:
                evidence_files.append(module.path)
                evidence_details.append(f"{module.path.name}: 包含插件/扩展机制")

        if len(evidence_files) >= 2:
            confidence = min(1.0, len(evidence_files) / 5.0)
            self.pattern_evidences.append(
                PatternEvidence(
                    pattern=ArchitecturePattern.MICROKERNEL,
                    confidence=confidence,
                    evidence=evidence_details,
                    files=evidence_files,
                    description="检测到微内核架构 (Plugin Architecture) 特征",
                )
            )

    def _detect_event_sourcing(self):
        """检测事件溯源 (Event Sourcing) 模式"""
        evidence_files = []
        evidence_details = []

        for module in self.modules:
            # 检查是否包含事件溯源关键词
            has_event_store = any(
                any(k.lower() in cls.lower() for k in self.event_sourcing_keywords)
                for cls in module.classes
            )
            has_append_replay = any(
                any(k.lower() in func.lower() for k in ["append", "replay", "load_events"])
                for func in module.functions
            )

            if has_event_store or has_append_replay:
                evidence_files.append(module.path)
                evidence_details.append(f"{module.path.name}: 包含事件存储/重放逻辑")

        if len(evidence_files) >= 2:
            confidence = min(1.0, len(evidence_files) / 5.0)
            self.pattern_evidences.append(
                PatternEvidence(
                    pattern=ArchitecturePattern.EVENT_SOURCING,
                    confidence=confidence,
                    evidence=evidence_details,
                    files=evidence_files,
                    description="检测到事件溯源 (Event Sourcing) 模式特征",
                )
            )

    def _detect_ddd(self):
        """检测领域驱动设计 (Domain-Driven Design) 模式"""
        evidence_files = []
        evidence_details = []

        for module in self.modules:
            # 检查是否包含 DDD 关键词
            has_aggregate = any(
                any(k.lower() in cls.lower() for k in ["aggregate", "Aggregate"])
                for cls in module.classes
            )
            has_value_object = any(
                any(k.lower() in cls.lower() for k in ["value", "ValueObject"])
                for cls in module.classes
            )
            has_domain_service = any(
                any(k.lower() in cls.lower() for k in ["domain", "DomainService"])
                for cls in module.classes
            )

            # DDD 通常需要多个组件
            ddd_score = sum([has_aggregate, has_value_object, has_domain_service])
            if ddd_score >= 2:
                evidence_files.append(module.path)
                evidence_details.append(f"{module.path.name}: 包含 DDD 组件 (聚合/值对象/领域服务)")

        if len(evidence_files) >= 2:
            confidence = min(1.0, len(evidence_files) / 5.0)
            self.pattern_evidences.append(
                PatternEvidence(
                    pattern=ArchitecturePattern.DDD,
                    confidence=confidence,
                    evidence=evidence_details,
                    files=evidence_files,
                    description="检测到领域驱动设计 (DDD) 模式特征",
                )
            )

    def _generate_report(self) -> Dict[str, Any]:
        """生成检测报告"""
        report = {
            "project_root": str(self.project_root),
            "modules_analyzed": len(self.modules),
            "patterns_detected": [],
            "pattern_details": {},
            "file_patterns": {str(k): [p.value for p in v] for k, v in self.file_patterns.items()},
        }

        # 按置信度排序
        sorted_evidences = sorted(self.pattern_evidences, key=lambda x: x.confidence, reverse=True)

        for evidence in sorted_evidences:
            pattern_info = {
                "pattern": evidence.pattern.value,
                "confidence": f"{evidence.confidence:.1%}",
                "description": evidence.description,
                "evidence_count": len(evidence.evidence),
                "files_count": len(evidence.files),
                "sample_evidence": evidence.evidence[:3],
            }
            report["patterns_detected"].append(pattern_info)
            report["pattern_details"][evidence.pattern.value] = pattern_info

        return report

    def print_report(self):
        """打印检测报告"""
        report = self._generate_report()

        print("\n" + "=" * 70)
        print("🏗️  架构模式检测报告")
        print("=" * 70)
        print(f"项目路径: {report['project_root']}")
        print(f"分析模块: {report['modules_analyzed']} 个")
        print()

        if not report["patterns_detected"]:
            print("⚠️  未检测到明显的架构模式")
            print("   可能原因：")
            print("   - 项目使用了自定义架构")
            print("   - 代码组织较为简单（单体脚本）")
            print("   - 需要更深入的语义分析")
            return

        print("📊 检测到的架构模式（按置信度排序）:")
        print("-" * 70)

        for i, pattern_info in enumerate(report["patterns_detected"], 1):
            confidence = float(pattern_info["confidence"].strip("%")) / 100

            # 置信度图标
            if confidence >= 0.7:
                icon = "✅"
            elif confidence >= 0.4:
                icon = "⚠️ "
            else:
                icon = "❓"

            print(f"\n{i}. {icon} {pattern_info['pattern']}")
            print(f"   置信度: {pattern_info['confidence']}")
            print(f"   说明: {pattern_info['description']}")
            print(f"   证据数: {pattern_info['evidence_count']} 条")
            print(f"   涉及文件: {pattern_info['files_count']} 个")

            if pattern_info["sample_evidence"]:
                print(f"   示例证据:")
                for evidence in pattern_info["sample_evidence"]:
                    print(f"     - {evidence}")

        print("\n" + "=" * 70)
        print("💡 建议:")
        print("-" * 70)

        # 基于检测结果给出建议
        detected_patterns = [p["pattern"] for p in report["patterns_detected"]]

        if "MVC" in detected_patterns:
            print("- 项目使用了 MVC 模式，建议确保 Model-View-Controller 职责清晰分离")
        if "分层架构" in detected_patterns:
            print("- 项目使用了分层架构，建议避免层与层之间的双向依赖")
        if "事件驱动" in detected_patterns:
            print("- 项目使用了事件驱动架构，建议确保事件命名的清晰性和处理逻辑的幂等性")
        if not detected_patterns:
            print("- 未检测到明显架构模式，建议根据项目规模引入合适的架构模式")

        print("=" * 70)

    def export_report(self, output_path: Path):
        """导出报告到文件"""
        import json

        report = self._generate_report()

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📄 报告已导出: {output_path}")


# ── 便捷函数 ────────────────────────────────────────────────────────────────


def scan_project_architecture(project_root: Path | str) -> Dict[str, Any]:
    """
    扫描项目架构模式（便捷函数）

    Args:
        project_root: 项目根目录

    Returns:
        检测报告字典
    """
    detector = ArchitectureDetector(Path(project_root))
    return detector.scan_project()


def print_architecture_report(project_root: Path | str):
    """打印项目架构检测报告（便捷函数）"""
    detector = ArchitectureDetector(Path(project_root))
    detector.scan_project()
    detector.print_report()


# ── CLI 入口 ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        project_path = Path(sys.argv[1])
    else:
        project_path = Path.cwd()

    if not project_path.exists():
        print(f"❌ 路径不存在: {project_path}")
        sys.exit(1)

    print_architecture_report(project_path)
