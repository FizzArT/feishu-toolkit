"""资源层：多维表格 Base（应用）相关接口。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class BaseAPI:
    """多维表格 Base 的创建、查询。"""

    def __init__(self, client: Any) -> None:
        self._client = client

    def create(self, name: str, *, folder_token: Optional[str] = None) -> Dict[str, Any]:
        """创建一个多维表格 Base。

        应用自建的 Base，应用自动拥有全部权限，无需额外添加协作者。

        Args:
            name: Base 名称。
            folder_token: 目标文件夹 token，不传则放在应用根目录。

        Returns:
            包含 app_token / name / url / default_table_id 的字典。
        """
        body: Dict[str, Any] = {"name": name}
        if folder_token:
            body["folder_token"] = folder_token
        data = self._client.post("/open-apis/bitable/v1/apps", json=body)
        return data.get("app", data)

    def get(self, app_token: str) -> Dict[str, Any]:
        """获取 Base 元信息。"""
        data = self._client.get(f"/open-apis/bitable/v1/apps/{app_token}")
        return data.get("app", data)

    def search(
        self,
        *,
        query: Optional[str] = None,
        page_size: int = 20,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """搜索当前应用可见的 Base。

        **这个接口只接受 GET。** POST 会命中路由层的 404
        （响应体是纯文本 ``404 page not found``，不是飞书的 JSON 错误），
        排查时很容易误判成「权限不足」。

        Returns:
            包含 items / has_more / page_token 的字典。
        """
        params: Dict[str, Any] = {"page_size": page_size}
        if query:
            params["query"] = query
        if page_token:
            params["page_token"] = page_token
        return self._client.get("/open-apis/bitable/v1/apps/search", params=params)
