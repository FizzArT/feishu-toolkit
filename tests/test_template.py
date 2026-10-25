"""标准看板模板结构测试。"""

from __future__ import annotations

from feishu_toolkit.api.fields import FieldType
from feishu_toolkit.templates.requirements_bug_board import (
    BUG_TABLE,
    BUG_VIEWS,
    REQUIREMENT_TABLE,
    REQUIREMENT_VIEWS,
    STANDARD_BOARD,
)


def _fields(table):
    return table["fields"]


def _by_name(table):
    return {f["field_name"]: f for f in table["fields"]}


def _select_options(field):
    return field["property"]["options"]


def test_requirement_primary_field_is_text():
    first = _fields(REQUIREMENT_TABLE)[0]
    assert first["type"] == FieldType.TEXT
    assert first["field_name"] == "需求名称"


def test_bug_primary_field_is_text():
    first = _fields(BUG_TABLE)[0]
    assert first["type"] == FieldType.TEXT
    assert first["field_name"] == "Bug 描述"


def test_issue_number_field_exists():
    req = _by_name(REQUIREMENT_TABLE)
    bug = _by_name(BUG_TABLE)
    assert req["Issue编号"]["type"] == FieldType.NUMBER
    assert bug["Issue编号"]["type"] == FieldType.NUMBER


def test_requirement_status_options():
    status = _by_name(REQUIREMENT_TABLE)["状态"]
    names = [o["name"] for o in _select_options(status)]
    assert names == ["待讨论", "待启动", "设计中", "开发中", "验收中", "已完成"]


def test_bug_status_options():
    status = _by_name(BUG_TABLE)["状态"]
    names = [o["name"] for o in _select_options(status)]
    assert names == ["未解决", "修复中", "待验收", "已关闭"]


def test_priority_options():
    req = _by_name(REQUIREMENT_TABLE)["优先级"]
    bug = _by_name(BUG_TABLE)["优先级"]
    assert [o["name"] for o in _select_options(req)] == ["P0", "P1", "P2"]
    assert [o["name"] for o in _select_options(bug)] == ["P0", "P1", "P2"]


def test_terminal_options():
    terminal = _by_name(BUG_TABLE)["终端"]
    names = [o["name"] for o in _select_options(terminal)]
    assert names == ["Web", "iOS", "Android", "Windows", "Mac"]


def test_all_select_colors_are_ints():
    for table in (REQUIREMENT_TABLE, BUG_TABLE):
        for f in _fields(table):
            if f["type"] == FieldType.SINGLE_SELECT:
                for opt in _select_options(f):
                    assert isinstance(opt["color"], int)
                    assert 0 <= opt["color"] <= 54


def test_default_view_names():
    assert REQUIREMENT_TABLE["default_view_name"] == "需求池"
    assert BUG_TABLE["default_view_name"] == "Bug 列表"


def test_extra_views():
    req_types = [v["view_type"] for v in REQUIREMENT_VIEWS]
    assert "kanban" in req_types
    assert "gantt" in req_types
    assert [v["view_type"] for v in BUG_VIEWS] == ["form"]


def test_standard_board_has_two_tables():
    specs = [t["spec"] for t in STANDARD_BOARD["tables"]]
    assert REQUIREMENT_TABLE in specs
    assert BUG_TABLE in specs
