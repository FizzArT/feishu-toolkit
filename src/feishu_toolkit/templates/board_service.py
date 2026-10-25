"""标准看板服务：幂等创建 / 复用标准看板。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .requirements_bug_board import STANDARD_BOARD


@dataclass
class BoardRef:
    """一次标准看板的结构引用。"""

    app_token: str
    url: str = ""
    table_ids: Dict[str, str] = field(default_factory=dict)
    view_ids: Dict[str, List[str]] = field(default_factory=dict)

    def table_id(self, table_name: str) -> str:
        return self.table_ids[table_name]


class BoardService:
    """创建并管理标准看板（需求管理 + Bug 管理）。"""

    def __init__(self, client: Any) -> None:
        self._client = client

    def create(
        self,
        name: str,
        *,
        folder_token: Optional[str] = None,
        delete_default_table: bool = True,
    ) -> BoardRef:
        """创建一个全新的标准看板。

        Returns:
            BoardRef，包含 app_token、各表/视图 ID。
        """
        app = self._client.bases.create(name, folder_token=folder_token)
        app_token = app.get("app_token")
        url = app.get("url", "")
        default_table_id = app.get("default_table_id")

        ref = BoardRef(app_token=app_token, url=url)
        for entry in STANDARD_BOARD["tables"]:
            spec = entry["spec"]
            created = self._client.tables.create(app_token, spec)
            table_id = created.get("table_id")
            ref.table_ids[spec["name"]] = table_id

            view_ids: List[str] = [created.get("default_view_id")]
            for view in entry.get("extra_views", []):
                v = self._client.views.create(
                    app_token,
                    table_id,
                    view["view_name"],
                    view["view_type"],
                )
                view_ids.append(v.get("view", {}).get("view_id"))
            ref.view_ids[spec["name"]] = view_ids

        if delete_default_table and default_table_id:
            self._client.tables.delete(app_token, default_table_id)

        return ref

    def ensure(
        self,
        name: str,
        *,
        app_token: Optional[str] = None,
        folder_token: Optional[str] = None,
    ) -> BoardRef:
        """幂等入口：提供 app_token 则复用（暂不做结构补齐），否则新建。"""
        if app_token:
            return self._build_ref_for_existing(app_token)
        return self.create(name, folder_token=folder_token)

    def _build_ref_for_existing(self, app_token: str) -> BoardRef:
        """为已存在的 Base 构建 BoardRef（按表名匹配）。"""
        ref = BoardRef(app_token=app_token)
        tables = self._client.tables.list(app_token)
        by_name = {t["name"]: t["table_id"] for t in tables}
        for entry in STANDARD_BOARD["tables"]:
            tname = entry["spec"]["name"]
            if tname in by_name:
                tid = by_name[tname]
                ref.table_ids[tname] = tid
                views = self._client.views.list(app_token, tid)
                ref.view_ids[tname] = [v.get("view_id") for v in views]
        return ref
