"""通知器：把消息 / 卡片发送到飞书群或个人。

支持两种发送方式：

1. **Notifier（应用身份）**：通过 ``im/v1/messages``，需要把应用加进群，
   用 chat_id 发送；适合统一走应用、可发个人。
2. **WebhookNotifier（自定义群机器人）**：直接 POST 群机器人 webhook，
   无需应用、无需权限；适合快速接入单个群。
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import requests

from ..api.messages import MessageType, ReceiveIDType
from ..errors import FeishuAPIError, FeishuNetworkError
from . import cards as _cards


class Notifier:
    """应用身份通知器。"""

    def __init__(self, client: Any) -> None:
        self._client = client
        self._messages = client.messages

    def send_text(
        self,
        receive_id: str,
        text: str,
        *,
        receive_id_type: str = ReceiveIDType.CHAT_ID,
    ) -> Dict[str, Any]:
        """发送文本。"""
        return self._messages.send_text(
            receive_id, text, receive_id_type=receive_id_type
        )

    def send_card(
        self,
        receive_id: str,
        card: Dict[str, Any],
        *,
        receive_id_type: str = ReceiveIDType.CHAT_ID,
    ) -> Dict[str, Any]:
        """发送交互卡片。"""
        return self._messages.send_card(
            receive_id, card, receive_id_type=receive_id_type
        )


class WebhookNotifier:
    """自定义群机器人通知器（无需应用）。

    用法：群设置 → 机器人 → 添加「自定义机器人」→ 复制 webhook 地址。
    """

    def __init__(
        self,
        webhook_url: str,
        *,
        timeout: float = 15.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        if not webhook_url:
            raise ValueError("webhook_url 不能为空")
        self.webhook_url = webhook_url
        self.timeout = timeout
        self._session = session or requests.Session()

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            resp = self._session.post(
                self.webhook_url, json=payload, timeout=self.timeout
            )
            resp.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise FeishuNetworkError(f"webhook 请求失败: {exc}") from exc

        try:
            data = resp.json()
        except ValueError as exc:
            raise FeishuNetworkError("webhook 响应不是合法 JSON") from exc

        # 自定义机器人成功时 code / StatusCode 为 0。
        code = data.get("code", data.get("StatusCode", -1))
        if code != 0:
            raise FeishuAPIError(code, data.get("msg", "webhook 发送失败"), data=data)
        return data

    def send_text(self, text: str) -> Dict[str, Any]:
        """发送文本。"""
        return self._post(
            {"msg_type": MessageType.TEXT, "content": {"text": text}}
        )

    def send_card(self, card: Dict[str, Any]) -> Dict[str, Any]:
        """发送交互卡片。"""
        return self._post({"msg_type": MessageType.INTERACTIVE, "card": card})


# 便捷再导出，便于 from feishu_toolkit.notifier import build_card
build_card = _cards.build_card
