"""GitHub Issue 事件 → 飞书卡片通知。

把 GitHub ``issues`` webhook 事件转换为交互卡片并发送到群。
支持的动作：opened / closed / reopened / edited / labeled / assigned 等。

卡片内容复用 :class:`GitHubIssueMapper` 的分类与状态 / 优先级口径，
保证「看板里的值」和「通知里的值」一致。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..adapters.github_issue import GitHubIssueMapper, IssueMapperConfig
from .notifier import WebhookNotifier
from . import cards


# 动作 → (卡片标题, 头部颜色)
def _presentation(action: str, issue: Dict[str, Any]) -> Dict[str, str]:
    state_reason = issue.get("state_reason")
    table = {
        "opened": ("🆕 新 Issue", cards.CardTemplate.GREEN),
        "reopened": ("🔄 重新打开", cards.CardTemplate.ORANGE),
        "edited": ("✏️ Issue 已更新", cards.CardTemplate.BLUE),
        "labeled": ("🏷️ 新增标签", cards.CardTemplate.TURQUOISE),
        "unlabeled": ("🏷️ 移除标签", cards.CardTemplate.TURQUOISE),
        "assigned": ("👤 指派负责人", cards.CardTemplate.PURPLE),
        "unassigned": ("👤 取消指派", cards.CardTemplate.PURPLE),
    }
    if action == "closed":
        if state_reason == "not_planned":
            return ("⚪ 已关闭（不计划）", cards.CardTemplate.GREY)
        return ("✅ Issue 已完成", cards.CardTemplate.GREEN)
    return table.get(action, ("📌 Issue 通知", cards.CardTemplate.BLUE))


class GitHubNotifier:
    """把 GitHub Issue 事件通知到飞书群。"""

    def __init__(
        self,
        notifier: Any,
        *,
        config: Optional[IssueMapperConfig] = None,
    ) -> None:
        self._notifier = notifier
        self.mapper = GitHubIssueMapper(config)

    # ---- 公共入口 ----

    def notify_event(
        self,
        event: Dict[str, Any],
        *,
        receive_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """处理一个 GitHub ``issues`` 事件。

        Args:
            event: GitHub webhook 事件 payload（含 action / issue / repository）。
            receive_id: 群 chat_id（应用 Notifier 时必填；
                WebhookNotifier 时忽略）。
        """
        action = event.get("action", "")
        issue = event.get("issue", {})
        repo = event.get("repository", {}).get("full_name", "")
        sender = event.get("sender", {}).get("login", "")
        card = self.build_event_card(action, issue, repo, sender)
        return self._send(card, receive_id)

    def build_event_card(
        self,
        action: str,
        issue: Dict[str, Any],
        repo: str,
        sender: str = "",
    ) -> Dict[str, Any]:
        """构建事件卡片。"""
        title, template = _presentation(action, issue)
        mapped = self.mapper.map(issue)
        f = mapped["fields"]

        num = issue.get("number", "")
        issue_title = issue.get("title", "")
        status = f.get("状态", "")
        priority = f.get("优先级", "")

        lines = [
            f"**#{num} {issue_title}**",
            f"📦 仓库：{repo}",
            f"📊 状态：{status}　🔖 优先级：{priority}",
        ]

        # 标签
        labels = [l.get("name", "") for l in issue.get("labels", []) if l.get("name")]
        if labels:
            lines.append("🏷️ 标签：" + "、".join(labels))

        # 负责人
        assignees = [
            a.get("login", "") for a in issue.get("assignees", []) if a.get("login")
        ]
        if assignees:
            lines.append("👤 负责人：" + "、".join(assignees))

        elements = [cards.markdown("\n".join(lines))]

        # 跳转按钮
        url = issue.get("html_url", "")
        if url:
            elements.append(
                cards.action_group(
                    [cards.link_button("查看 Issue", url, button_type="primary")]
                )
            )

        if sender:
            elements.append(cards.note(f"操作人：{sender}"))

        return cards.build_card(title, template=template, elements=elements)

    # ---- 内部 ----

    def _send(self, card: Dict[str, Any], receive_id: Optional[str]) -> Any:
        # WebhookNotifier.send_card 不接收 receive_id
        if isinstance(self._notifier, WebhookNotifier):
            return self._notifier.send_card(card)
        if not receive_id:
            raise ValueError("应用 Notifier 必须提供 receive_id（群 chat_id）")
        return self._notifier.send_card(receive_id, card)
