"""标准看板模板：Requirements and Bug Management（需求与 Bug 管理）。

字段、单选项、配色与视图均复刻自飞书模板市场「Requirements and Bug
Management」，作为所有项目的统一标准（SSOT）。

说明：
- 字段创建接口的选项颜色使用数字 ``color``（0-54），不接受 hue/lightness；
  本模板中的 color 值已通过模板实际结构核对。
- 模板中的「建群按钮 / Bug 工单群」依赖自动化建群能力，属于进阶特性，
  默认不创建；后续可在扩展版本中按需开启。
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..api.fields import FieldType


def _text(name: str) -> Dict[str, Any]:
    return {"field_name": name, "type": FieldType.TEXT}


def _number(name: str) -> Dict[str, Any]:
    """数字字段（用作 Issue 编号关联键）。"""
    return {"field_name": name, "type": FieldType.NUMBER, "property": {"formatter": "0"}}


def _select(name: str, options: List[Dict[str, Any]]) -> Dict[str, Any]:
    """单选字段。options 项形如 {"name": "P0", "color": 11}。"""
    return {
        "field_name": name,
        "type": FieldType.SINGLE_SELECT,
        "property": {
            "options": [
                {"name": o["name"], "color": o["color"]} for o in options
            ]
        },
    }


def _user(name: str, multiple: bool = False) -> Dict[str, Any]:
    return {
        "field_name": name,
        "type": FieldType.USER,
        "property": {"multiple": multiple},
    }


def _attachment(name: str) -> Dict[str, Any]:
    return {"field_name": name, "type": FieldType.ATTACHMENT}


def _date(name: str, formatter: str = "yyyy/MM/dd") -> Dict[str, Any]:
    return {
        "field_name": name,
        "type": FieldType.DATETIME,
        "property": {"date_formatter": formatter, "auto_fill": False},
    }


def _created_time(name: str, formatter: str = "yyyy/MM/dd HH:mm") -> Dict[str, Any]:
    return {
        "field_name": name,
        "type": FieldType.CREATED_TIME,
        "property": {"date_formatter": formatter},
    }


# ---- 需求管理表 ----

REQUIREMENT_TABLE: Dict[str, Any] = {
    "name": "需求管理",
    "default_view_name": "需求池",
    "fields": [
        _text("需求名称"),          # 主字段（第一个必须为文本）
        _number("Issue编号"),        # GitHub Issue 关联键
        _text("需求描述"),
        _text("AI 总结"),
        _select(
            "迭代版本",
            [
                {"name": "v1.1", "color": 0},
                {"name": "V1.2", "color": 1},
                {"name": "待排期", "color": 2},
            ],
        ),
        _user("负责人"),
        _select(
            "状态",
            [
                {"name": "待讨论", "color": 10},
                {"name": "待启动", "color": 6},
                {"name": "设计中", "color": 5},
                {"name": "开发中", "color": 13},
                {"name": "验收中", "color": 0},
                {"name": "已完成", "color": 15},
            ],
        ),
        _attachment("附件"),
        _select(
            "优先级",
            [
                {"name": "P0", "color": 11},
                {"name": "P1", "color": 17},
                {"name": "P2", "color": 21},
            ],
        ),
        _date("开始时间"),
        _date("结束时间"),
    ],
}

# 额外视图（默认视图「需求池」已随表创建）
REQUIREMENT_VIEWS: List[Dict[str, str]] = [
    {"view_name": "任务看板", "view_type": "kanban"},
    {"view_name": "迭代甘特图", "view_type": "gantt"},
]


# ---- Bug 管理表 ----

BUG_TABLE: Dict[str, Any] = {
    "name": "Bug 管理",
    "default_view_name": "Bug 列表",
    "fields": [
        _text("Bug 描述"),          # 主字段
        _number("Issue编号"),        # GitHub Issue 关联键
        _select(
            "修复版本",
            [
                {"name": "V1.1", "color": 0},
                {"name": "V1.2", "color": 1},
                {"name": "待排期", "color": 2},
            ],
        ),
        _select(
            "终端",
            [
                {"name": "Web", "color": 0},
                {"name": "iOS", "color": 1},
                {"name": "Android", "color": 2},
                {"name": "Windows", "color": 3},
                {"name": "Mac", "color": 4},
            ],
        ),
        _select(
            "状态",
            [
                {"name": "未解决", "color": 0},
                {"name": "修复中", "color": 1},
                {"name": "待验收", "color": 2},
                {"name": "已关闭", "color": 3},
            ],
        ),
        _select(
            "优先级",
            [
                {"name": "P0", "color": 11},
                {"name": "P1", "color": 1},
                {"name": "P2", "color": 2},
            ],
        ),
        _user("提交人"),
        _user("指派人"),
        _created_time("创建时间"),
        _attachment("截图或视频"),
    ],
}

BUG_VIEWS: List[Dict[str, str]] = [
    {"view_name": "提交 Bug 表单", "view_type": "form"},
]


# ---- 汇总 ----

STANDARD_BOARD: Dict[str, Any] = {
    "tables": [
        {"spec": REQUIREMENT_TABLE, "extra_views": REQUIREMENT_VIEWS},
        {"spec": BUG_TABLE, "extra_views": BUG_VIEWS},
    ],
}
