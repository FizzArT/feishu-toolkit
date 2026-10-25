"""飞书集成工具（Feishu Toolkit）。

飞书开放平台 Python SDK，首批提供多维表格（Bitable）与标准看板能力。

快速上手：

    from feishu_toolkit import FeishuClient

    client = FeishuClient(app_id="cli_xxx", app_secret="xxx")
    client.bases.create("我的看板")
"""

from .client import FeishuClient
from .errors import (
    FeishuAPIError,
    FeishuConfigError,
    FeishuError,
    FeishuNetworkError,
)

__version__ = "0.1.0"

__all__ = [
    "FeishuClient",
    "FeishuError",
    "FeishuConfigError",
    "FeishuNetworkError",
    "FeishuAPIError",
    "__version__",
]
