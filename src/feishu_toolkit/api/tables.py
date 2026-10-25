"""资源层：数据表（Table）相关接口。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class TableAPI:
    """数据表的增删改查。"""

    def __init__(self, client: Any) -> None:
        self._client = client

    @staticmethod
    def _prefix(app_token: str) -> str:
        return f"/open-apis/bitable/v1/apps/{app_token}/tables"

    def create(
        self,
        app_token: str,
        table: Dict[str, Any],
    ) -> Dict[str, Any]:
        """创建数据表。

        table 可包含 name、default_view_name、fields（字段定义数组）。
        注意：官方接口要求将表定义放在 ``table`` 键下。
        """
        data = self._client.post(self._prefix(app_token), json={"table": table})
        return data

    def list(self, app_token: str, *, page_size: int = 100) -> List[Dict[str, Any]]:
        """列出 Base 内所有数据表。"""
        items: List[Dict[str, Any]] = []
        for item in self._client.iter_pages(
            self._prefix(app_token),
            items_key="items",
            page_size=page_size,
        ):
            items.append(item)
        return items

    def get(self, app_token: str, table_id: str) -> Dict[str, Any]:
        """获取数据表详情。"""
        return self._client.get(f"{self._prefix(app_token)}/{table_id}")

    def update(self, app_token: str, table_id: str, *, name: str) -> Dict[str, Any]:
        """更新数据表（目前仅支持改名）。"""
        return self._client.patch(
            f"{self._prefix(app_token)}/{table_id}",
            json={"name": name},
        )

    def delete(self, app_token: str, table_id: str) -> Any:
        """删除数据表。"""
        return self._client.delete(f"{self._prefix(app_token)}/{table_id}")
