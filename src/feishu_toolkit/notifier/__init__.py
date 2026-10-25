"""通知模块：消息 / 卡片发送与 GitHub Issue 事件通知。

两种发送方式：
- :class:`Notifier`：应用身份，通过 IM API 发送，需应用进群。
- :class:`WebhookNotifier`：自定义群机器人，直接 POST webhook。

GitHub 事件通知：
- :class:`GitHubNotifier`：把 GitHub Issue 事件转成交互卡片。
"""

from .cards import (
    CardTemplate,
    action_group,
    build_card,
    divider,
    link_button,
    markdown,
    note,
)
from .notifier import Notifier, WebhookNotifier
from .github_notifier import GitHubNotifier

__all__ = [
    "Notifier",
    "WebhookNotifier",
    "GitHubNotifier",
    "CardTemplate",
    "build_card",
    "markdown",
    "divider",
    "note",
    "link_button",
    "action_group",
]
