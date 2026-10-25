"""资源层：视图（View）相关接口。"""

from __future__ import annotations

from typing import Any, Dict, List


class ViewType:
    """视图类型。"""

    GRID = "grid"            # 表格
    KANBAN = "kanban"        # 看板
    GANTT = "gantt"          # 甘特
    FORM = "form"            # 表单
    GALLERY = "gallery"      # 画册
    LIST = "list"            # 列表


class ViewAPI:
    """视图的增删改查。"""

    def __init__(self, client: Any) -> None:
        self._client = client

    @staticmethod
    def _prefix(app_token: str, table_id: str) -> str:
        return (
            f"/open-apis/bitable/v1/apps/{app_token}"
            f"/tables/{table_id}/views"
        )

    def create(
        self,
        app_token: str,
        table_id: str,
        view_name: str,
        view_type: str = ViewType.GRID,
    ) -> Dict[str, Any]:
        """创建视图。"""
        return self._client.post(
            self._prefix(app_token, table_id),
            json={"view_name": view_name, "view_type": view_type},
        )

    def list(self, app_token: str, table_id: str) -> List[Dict[str, Any]]:
        """列出视图。"""
        data = self._client.get(self._prefix(app_token, table_id))
        return data.get("items", []) or []

    def get(self, app_token: str, table_id: str, view_id: str) -> Dict[str, Any]:
        """获取视图详情。"""
        return self._client.get(
            f"{self._prefix(app_token, table_id)}/{view_id}"
        )

    def update(
        self,
        app_token: str,
        table_id: str,
        view_id: str,
        view: Dict[str, Any],
    ) -> Dict[str, Any]:
        """更新视图（PATCH）。"""
        return self._client.patch(
            f"{self._prefix(app_token, table_id)}/{view_id}",
            json=view,
        )

    def delete(self, app_token: str, table_id: str, view_id: str) -> Any:
        """删除视图。"""
        return self._client.delete(
            f"{self._prefix(app_token, table_id)}/{view_id}"
        )
