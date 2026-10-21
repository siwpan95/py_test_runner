"""pytrunner —— Python 项目全覆盖测试框架（命名空间根包）。"""

import sys

# 兼容仓库「脚本模式」（根目录在 sys.path 上时 `from core.x` / `from tests.x` 等可用）。
# 打包为命名空间包后顶层不再有这些子包，这里把别名指回本包子模块，
# 使既有绝对导入在包模式下仍能解析。若已有同名顶层包则不动（setdefault）。
for _alias, _sub in (
    ("core", "pytrunner.core"),
    ("console", "pytrunner.console"),
    ("gui", "pytrunner.gui"),
    ("tests", "pytrunner.tests"),
    ("probes", "pytrunner.probes"),
    ("scanners", "pytrunner.scanners"),
):
    try:
        __import__(_sub)
        sys.modules.setdefault(_alias, sys.modules[_sub])
    except ImportError:
        pass
del _alias, _sub
