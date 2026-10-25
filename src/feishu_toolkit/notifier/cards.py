"""飞书交互卡片构建。

输出为飞书 Card JSON（v1 结构，兼容自定义群机器人与应用消息），
可直接作为 ``msg_type=interactive`` 的内容。

卡片结构：
- header：标题 + 颜色模板；
- body 元素：markdown 文本、分割线、备注、按钮（跳转链接）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# 卡片头部颜色模板
class CardTemplate:
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"
    PURPLE = "purple"
    TURQUOISE = "turquoise"
    GREY = "grey"
    DEFAULT = "default"


def _plain_text(content: str) -> Dict[str, str]:
    return {"tag": "plain_text", "content": str(content)}


def markdown(content: str) -> Dict[str, Any]:
    """markdown 元素。"""
    return {"tag": "markdown", "content": str(content)}


def divider() -> Dict[str, str]:
    """分割线。"""
    return {"tag": "hr"}


def note(content: str) -> Dict[str, Any]:
    """备注（小字）。"""
    return {"tag": "note", "elements": [_plain_text(content)]}


def link_button(
    text: str,
    url: str,
    *,
    button_type: str = "primary",
) -> Dict[str, Any]:
    """跳转按钮（放在 action 元素里）。"""
    return {
        "tag": "button",
        "text": _plain_text(text),
        "type": button_type,
        "url": url,
    }


def action_group(buttons: List[Dict[str, Any]]) -> Dict[str, Any]:
    """按钮组容器。"""
    return {"tag": "action", "actions": buttons}


def build_card(
    title: str,
    *,
    template: str = CardTemplate.BLUE,
    elements: Optional[List[Dict[str, Any]]] = None,
    subtitle: Optional[str] = None,
    wide_screen: bool = True,
) -> Dict[str, Any]:
    """构建一张完整卡片。

    Args:
        title: 卡片标题。
        template: 头部颜色模板。
        elements: 卡片正文元素列表。
        subtitle: 副标题（可选）。
        wide_screen: 是否宽屏自适应。
    """
    header: Dict[str, Any] = {
        "title": _plain_text(title),
        "template": template,
    }
    if subtitle:
        header["subtitle"] = _plain_text(subtitle)

    return {
        "config": {"wide_screen_mode": wide_screen},
        "header": header,
        "elements": elements or [],
    }
