"""资源层：记录（Record）相关接口。"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


class RecordAPI:
    """记录的增删改查与批量操作。"""

    def __init__(self, client: Any) -> None:
        self._client = client

    @staticmethod
    def _prefix(app_token: str, table_id: str) -> str:
        return (
            f"/open-apis/bitable/v1/apps/{app_token}"
            f"/tables/{table_id}/records"
        )

    # ---- 单条 ----

    def create(
        self,
        app_token: str,
        table_id: str,
        fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        """创建一条记录。"""
        return self._client.post(
            self._prefix(app_token, table_id),
            json={"fields": fields},
        )

    def get(
        self,
        app_token: str,
        table_id: str,
        record_id: str,
    ) -> Dict[str, Any]:
        """获取一条记录。"""
        return self._client.get(
            f"{self._prefix(app_token, table_id)}/{record_id}"
        )

    def update(
        self,
        app_token: str,
        table_id: str,
        record_id: str,
        fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        """更新一条记录（PUT）。"""
        return self._client.request(
            "PUT",
            f"{self._prefix(app_token, table_id)}/{record_id}",
            json={"fields": fields},
        )

    def delete(self, app_token: str, table_id: str, record_id: str) -> Any:
        """删除一条记录。"""
        return self._client.delete(
            f"{self._prefix(app_token, table_id)}/{record_id}"
        )

    # ---- 批量（单批最多 200 条）----

    def batch_create(
        self,
        app_token: str,
        table_id: str,
        records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """批量创建记录。records 为 [{"fields": {...}}, ...]。"""
        return self._client.post(
            f"{self._prefix(app_token, table_id)}/batch_create",
            json={"records": records},
        )

    def batch_update(
        self,
        app_token: str,
        table_id: str,
        records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """批量更新记录。records 为 [{"record_id": "...", "fields": {...}}, ...]。"""
        return self._client.post(
            f"{self._prefix(app_token, table_id)}/batch_update",
            json={"records": records},
        )

    def batch_delete(
        self,
        app_token: str,
        table_id: str,
        record_ids: List[str],
    ) -> Dict[str, Any]:
        """批量删除记录。"""
        return self._client.post(
            f"{self._prefix(app_token, table_id)}/batch_delete",
            json={"records": record_ids},
        )

    # ---- 查询 ----

    def list(
        self,
        app_token: str,
        table_id: str,
        *,
        view_id: Optional[str] = None,
        filter_expr: Optional[str] = None,
        sort: Optional[str] = None,
        field_names: Optional[List[str]] = None,
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """列出记录（自动分页，返回全部）。"""
        params: Dict[str, Any] = {"page_size": page_size}
        if view_id:
            params["view_id"] = view_id
        if filter_expr:
            params["filter"] = filter_expr
        if sort:
            params["sort"] = sort
        if field_names:
            params["field_names"] = json.dumps(list(field_names), ensure_ascii=False)
        items: List[Dict[str, Any]] = []
        for item in self._iter_list(app_token, table_id, params):
            items.append(item)
        return items

    def _iter_list(self, app_token: str, table_id: str, params: Dict[str, Any]):
        path = self._prefix(app_token, table_id)
        page_token: Optional[str] = None
        while True:
            if page_token:
                params["page_token"] = page_token
            data = self._client.get(path, params=params)
            for item in data.get("items", []) or []:
                yield item
            if not data.get("has_more"):
                break
            page_token = data.get("page_token")
            if not page_token:
                break

    def search(
        self,
        app_token: str,
        table_id: str,
        *,
        view_id: Optional[str] = None,
        field_names: Optional[List[str]] = None,
        filter_: Optional[Dict[str, Any]] = None,
        sort: Optional[List[Dict[str, Any]]] = None,
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """通过 search 接口查询记录（支持结构化 filter）。"""
        body: Dict[str, Any] = {"page_size": page_size}
        if view_id:
            body["view_id"] = view_id
        if field_names:
            body["field_names"] = field_names
        if filter_:
            body["filter"] = filter_
        if sort:
            body["sort"] = sort
        items: List[Dict[str, Any]] = []
        path = f"{self._prefix(app_token, table_id)}/search"
        page_token: Optional[str] = None
        while True:
            if page_token:
                body["page_token"] = page_token
            data = self._client.post(path, json=body)
            for item in data.get("items", []) or []:
                items.append(item)
            if not data.get("has_more"):
                break
            page_token = data.get("page_token")
            if not page_token:
                break
        return items
