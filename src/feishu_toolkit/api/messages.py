"""资源层：消息（Message）相关接口。

封装飞书 IM 消息发送：文本、富文本、交互卡片等。
对应 ``POST /open-apis/im/v1/messages``。
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional


# 接收者 ID 类型
class ReceiveIDType:
    OPEN_ID = "open_id"
    USER_ID = "user_id"
    UNION_ID = "union_id"
    EMAIL = "email"
    CHAT_ID = "chat_id"


# 消息类型
class MessageType:
    TEXT = "text"
    POST = "post"
    INTERACTIVE = "interactive"
    IMAGE = "image"
    FILE = "file"


class MessageAPI:
    """消息发送。"""

    def __init__(self, client: Any) -> None:
        self._client = client
        self._prefix = "/open-apis/im/v1/messages"

    def send(
        self,
        receive_id: str,
        msg_type: str,
        content: Any,
        *,
        receive_id_type: str = ReceiveIDType.CHAT_ID,
        uuid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """发送消息。

        Args:
            receive_id: 接收者 ID（群为 chat_id，个人为 open_id）。
            msg_type: 消息类型（text / interactive / ...）。
            content: 消息内容。dict 会被序列化为 JSON 字符串，
                str 原样发送。
            receive_id_type: 接收者 ID 类型。
            uuid: 去重字符串（1 小时内相同 uuid 只成功一条）。
        """
        body: Dict[str, Any] = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": content
            if isinstance(content, str)
            else json.dumps(content, ensure_ascii=False),
        }
        if uuid:
            body["uuid"] = uuid
        return self._client.post(
            self._prefix,
            params={"receive_id_type": receive_id_type},
            json=body,
        )

    def send_text(
        self,
        receive_id: str,
        text: str,
        *,
        receive_id_type: str = ReceiveIDType.CHAT_ID,
    ) -> Dict[str, Any]:
        """发送文本消息。"""
        return self.send(
            receive_id,
            MessageType.TEXT,
            {"text": text},
            receive_id_type=receive_id_type,
        )

    def send_card(
        self,
        receive_id: str,
        card: Dict[str, Any],
        *,
        receive_id_type: str = ReceiveIDType.CHAT_ID,
    ) -> Dict[str, Any]:
        """发送交互卡片。"""
        return self.send(
            receive_id,
            MessageType.INTERACTIVE,
            card,
            receive_id_type=receive_id_type,
        )
