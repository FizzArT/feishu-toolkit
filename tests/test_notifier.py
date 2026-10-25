"""notifier 模块测试（卡片构建 + 发送，使用 mock）。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from feishu_toolkit.errors import FeishuAPIError
from feishu_toolkit.notifier import (
    CardTemplate,
    GitHubNotifier,
    Notifier,
    WebhookNotifier,
    build_card,
)
from feishu_toolkit.notifier import cards


# ---------- 卡片构建 ----------

def test_build_card_structure():
    card = build_card("标题", template=CardTemplate.RED, elements=[cards.markdown("hi")])
    assert card["config"]["wide_screen_mode"] is True
    assert card["header"]["title"]["content"] == "标题"
    assert card["header"]["template"] == "red"
    assert card["elements"][0]["tag"] == "markdown"


def test_build_card_subtitle_and_empty_elements():
    card = build_card("t", subtitle="s")
    assert card["header"]["subtitle"]["content"] == "s"
    assert card["elements"] == []


def test_link_button_and_action_group():
    btn = cards.link_button("打开", "https://x", button_type="danger")
    assert btn["type"] == "danger"
    assert btn["url"] == "https://x"
    grp = cards.action_group([btn])
    assert grp["actions"] == [btn]


def test_divider_and_note():
    assert cards.divider()["tag"] == "hr"
    note = cards.note("备注")
    assert note["elements"][0]["content"] == "备注"


# ---------- GitHub 事件 → 卡片 ----------

def _issue(**over):
    base = {
        "number": 1,
        "title": "做个功能",
        "state": "open",
        "labels": [],
        "assignees": [],
        "html_url": "https://github.com/o/r/issues/1",
    }
    base.update(over)
    return base


def _notifier():
    return GitHubNotifier(MagicMock())


def test_opened_card_green():
    gh = _notifier()
    card = gh.build_event_card("opened", _issue(), "o/r", "bob")
    assert card["header"]["template"] == "green"
    assert card["header"]["title"]["content"] == "🆕 新 Issue"


def test_closed_completed_green():
    gh = _notifier()
    card = gh.build_event_card(
        "closed", _issue(state="closed", state_reason="completed"), "o/r"
    )
    assert card["header"]["template"] == "green"
    assert "已完成" in card["header"]["title"]["content"]


def test_closed_not_planned_grey():
    gh = _notifier()
    card = gh.build_event_card(
        "closed", _issue(state="closed", state_reason="not_planned"), "o/r"
    )
    assert card["header"]["template"] == "grey"


def test_reopened_orange():
    gh = _notifier()
    card = gh.build_event_card("reopened", _issue(), "o/r")
    assert card["header"]["template"] == "orange"


def test_bug_label_shows_bug_status():
    gh = _notifier()
    issue = _issue(labels=[{"name": "bug"}, {"name": "high"}])
    card = gh.build_event_card("opened", issue, "o/r")
    body = card["elements"][0]["content"]
    assert "未解决" in body
    assert "P0" in body


def test_card_has_issue_button():
    gh = _notifier()
    card = gh.build_event_card("opened", _issue(), "o/r")
    action = card["elements"][1]
    assert action["actions"][0]["url"] == "https://github.com/o/r/issues/1"


def test_card_shows_assignee_and_labels():
    gh = _notifier()
    issue = _issue(labels=[{"name": "ui"}], assignees=[{"login": "alice"}])
    card = gh.build_event_card("opened", issue, "o/r")
    body = card["elements"][0]["content"]
    assert "alice" in body
    assert "ui" in body


# ---------- WebhookNotifier ----------

def _webhook(json_data):
    session = MagicMock()
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    session.post.return_value = resp
    return session, resp


def test_webhook_send_text_payload():
    session, _ = _webhook({"code": 0, "msg": "success"})
    wh = WebhookNotifier("https://open.feishu.cn/open-apis/bot/v2/hook/x", session=session)
    wh.send_text("hello")
    payload = session.post.call_args.kwargs["json"]
    assert payload == {"msg_type": "text", "content": {"text": "hello"}}


def test_webhook_send_card_payload():
    session, _ = _webhook({"code": 0})
    wh = WebhookNotifier("https://x", session=session)
    card = build_card("t")
    wh.send_card(card)
    payload = session.post.call_args.kwargs["json"]
    assert payload == {"msg_type": "interactive", "card": card}


def test_webhook_statuscode_zero_accepted():
    session, _ = _webhook({"StatusCode": 0, "code": 0})
    wh = WebhookNotifier("https://x", session=session)
    assert wh.send_text("hi")["StatusCode"] == 0


def test_webhook_error_raises():
    session, _ = _webhook({"code": 19021, "msg": "bad"})
    wh = WebhookNotifier("https://x", session=session)
    with pytest.raises(FeishuAPIError):
        wh.send_text("hi")


def test_webhook_empty_url_raises():
    with pytest.raises(ValueError):
        WebhookNotifier("")


# ---------- notify_event 流程 ----------

def test_notify_event_webhook_no_receive_id():
    session, _ = _webhook({"code": 0})
    wh = WebhookNotifier("https://x", session=session)
    gh = GitHubNotifier(wh)
    event = {"action": "opened", "issue": _issue(), "repository": {"full_name": "o/r"}}
    gh.notify_event(event)
    assert session.post.called


def test_notify_event_app_notifier_requires_receive_id():
    gh = _notifier()
    event = {"action": "opened", "issue": _issue(), "repository": {"full_name": "o/r"}}
    with pytest.raises(ValueError):
        gh.notify_event(event)


def test_notify_event_app_notifier_sends_card():
    inner = MagicMock()
    gh = GitHubNotifier(inner)
    event = {"action": "opened", "issue": _issue(), "repository": {"full_name": "o/r"}}
    gh.notify_event(event, receive_id="oc_123")
    inner.send_card.assert_called_once()
    args = inner.send_card.call_args.args
    assert args[0] == "oc_123"
