"""飞书集成工具入口：FeishuClient。"""

from __future__ import annotations

import os
from typing import Optional

from .auth import TokenManager
from .errors import FeishuConfigError
from .http import HttpClient
from .api import BaseAPI, FieldAPI, MessageAPI, RecordAPI, TableAPI, ViewAPI
from .templates import BoardService
from .adapters import GitHubIssueSync, IssueMapperConfig
from .notifier import GitHubNotifier, Notifier

DEFAULT_BASE_URL = "https://open.feishu.cn"


class FeishuClient:
    """飞书开放平台客户端。

    组合认证与各资源命名空间，统一入口：

        client = FeishuClient(app_id="cli_xxx", app_secret="xxx")
        client.bases.create("我的看板")
        client.records.batch_create(app_token, table_id, records)

    凭证也可通过环境变量 FEISHU_APP_ID / FEISHU_APP_SECRET 提供。
    """

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 15.0,
    ) -> None:
        app_id = app_id or os.environ.get("FEISHU_APP_ID")
        app_secret = app_secret or os.environ.get("FEISHU_APP_SECRET")
        if not app_id or not app_secret:
            raise FeishuConfigError(
                "必须提供 app_id / app_secret，或设置环境变量 "
                "FEISHU_APP_ID / FEISHU_APP_SECRET"
            )

        self.app_id = app_id
        self.base_url = base_url.rstrip("/")

        self._token_manager = TokenManager(
            app_id, app_secret, self.base_url, timeout=timeout
        )
        self._http = HttpClient(self._token_manager, timeout=timeout)

        # 资源命名空间
        self.bases = BaseAPI(self._http)
        self.tables = TableAPI(self._http)
        self.fields = FieldAPI(self._http)
        self.records = RecordAPI(self._http)
        self.views = ViewAPI(self._http)
        self.messages = MessageAPI(self._http)

        # 高层服务：标准看板
        self.issue_board = BoardService(self)

        # 通知器（应用身份）
        self._notifier = Notifier(self)

    def github_issue_sync(self, board_ref, *, config: Optional[IssueMapperConfig] = None) -> GitHubIssueSync:
        """针对某个标准看板构建 GitHub Issue 同步器。"""
        return GitHubIssueSync(self, board_ref, config=config)

    def github_notifier(self, *, config: Optional[IssueMapperConfig] = None) -> GitHubNotifier:
        """构建 GitHub Issue 事件通知器（应用身份，发群用 chat_id）。"""
        return GitHubNotifier(self._notifier, config=config)

    @property
    def notifier(self) -> Notifier:
        """应用身份通知器（可发文本 / 卡片到群或个人）。"""
        return self._notifier

    @property
    def http(self) -> HttpClient:
        """底层 HTTP 客户端（用于高级/自定义调用）。"""
        return self._http

    @property
    def token_manager(self) -> TokenManager:
        """Token 管理器。"""
        return self._token_manager
