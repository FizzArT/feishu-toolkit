"""资源层：字段（Field）相关接口与字段类型常量。"""

from __future__ import annotations

from typing import Any, Dict, List


class FieldType:
    """多维表格字段类型编码（与官方 API 对应）。"""

    TEXT = 1            # 多行文本
    NUMBER = 2          # 数字
    SINGLE_SELECT = 3   # 单选
    MULTI_SELECT = 4    # 多选
    DATETIME = 5        # 日期
    CHECKBOX = 7        # 复选框
    USER = 11           # 人员
    PHONE = 13          # 电话
    URL = 15            # 超链接
    ATTACHMENT = 17     # 附件
    LINK = 18           # 单向关联
    FORMULA = 20        # 公式
    DUPLEX_LINK = 21    # 双向关联
    LOCATION = 22       # 地理位置
    GROUP_CHAT = 23     # 群聊
    CREATED_TIME = 1001     # 创建时间
    MODIFIED_TIME = 1002    # 最后更新时间
    CREATED_USER = 1003     # 创建人
    MODIFIED_USER = 1004    # 修改人
    AUTO_NUMBER = 1005      # 自动编号


class FieldAPI:
    """字段的增删改查。"""

    def __init__(self, client: Any) -> None:
        self._client = client

    @staticmethod
    def _prefix(app_token: str, table_id: str) -> str:
        return (
            f"/open-apis/bitable/v1/apps/{app_token}"
            f"/tables/{table_id}/fields"
        )

    def create(self, app_token: str, table_id: str, field: Dict[str, Any]) -> Dict[str, Any]:
        """创建字段。

        field 形如：{"field_name": "状态", "type": 3,
        "property": {"options": [{"name": "已完成"}]}}
        """
        return self._client.post(self._prefix(app_token, table_id), json=field)

    def list(self, app_token: str, table_id: str, *, page_size: int = 100) -> List[Dict[str, Any]]:
        """列出数据表全部字段。"""
        items: List[Dict[str, Any]] = []
        for item in self._client.iter_pages(
            self._prefix(app_token, table_id),
            page_size=page_size,
        ):
            items.append(item)
        return items

    def get(self, app_token: str, table_id: str, field_id: str) -> Dict[str, Any]:
        """获取字段详情。"""
        return self._client.get(f"{self._prefix(app_token, table_id)}/{field_id}")

    def update(
        self,
        app_token: str,
        table_id: str,
        field_id: str,
        field: Dict[str, Any],
    ) -> Dict[str, Any]:
        """更新字段（PUT，全量覆盖）。"""
        return self._client.request(
            "PUT",
            f"{self._prefix(app_token, table_id)}/{field_id}",
            json=field,
        )

    def delete(self, app_token: str, table_id: str, field_id: str) -> Any:
        """删除字段。"""
        return self._client.delete(
            f"{self._prefix(app_token, table_id)}/{field_id}"
        )
