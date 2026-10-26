"""看板档案（BoardProfile）与按档案同步的测试。"""

from __future__ import annotations

import json
from typing import Any, Dict, List

import pytest

from feishu_toolkit.adapters.github_issue import GitHubIssueMapper, IssueMapperConfig
from feishu_toolkit.adapters.profile_sync import ProfileIssueSync
from feishu_toolkit.api.fields import FieldType
from feishu_toolkit.templates.board_profile import BoardProfile


# ---- 假客户端 ----


class FakeTables:
    def __init__(self, client: "FakeClient") -> None:
        self.c = client

    def list(self, app_token: str, *, page_size: int = 100) -> List[Dict[str, Any]]:
        return [
            {"table_id": tid, "name": t["name"]}
            for tid, t in self.c.data.items()
        ]


class FakeFields:
    def __init__(self, client: "FakeClient") -> None:
        self.c = client

    def list(self, app_token: str, table_id: str, *, page_size: int = 100):
        return [dict(f) for f in self.c.data[table_id]["fields"]]

    def create(self, app_token: str, table_id: str, field: Dict[str, Any]):
        f = dict(field)
        f.setdefault("field_id", f"fld{len(self.c.data[table_id]['fields'])}")
        self.c.data[table_id]["fields"].append(f)
        return {"field": f}

    def update(self, app_token, table_id, field_id, field):
        fields = self.c.data[table_id]["fields"]
        for i, f in enumerate(fields):
            if f.get("field_id") == field_id:
                fields[i] = {**f, **field}
                return {"field": fields[i]}
        raise KeyError(field_id)


class FakeRecords:
    def __init__(self, client: "FakeClient") -> None:
        self.c = client

    def list(self, app_token, table_id, *, field_names=None, page_size=100, **kw):
        out = []
        for rec in self.c.data[table_id]["records"]:
            if field_names:
                fields = {k: v for k, v in rec["fields"].items() if k in field_names}
            else:
                fields = dict(rec["fields"])
            out.append({"record_id": rec["record_id"], "fields": fields})
        return out

    def batch_create(self, app_token, table_id, records):
        created = []
        for r in records:
            rid = f"rec{len(self.c.data[table_id]['records']) + 1}"
            self.c.data[table_id]["records"].append(
                {"record_id": rid, "fields": dict(r["fields"])}
            )
            created.append({"record_id": rid})
        return {"records": created}

    def batch_update(self, app_token, table_id, records):
        for r in records:
            for rec in self.c.data[table_id]["records"]:
                if rec["record_id"] == r["record_id"]:
                    rec["fields"].update(r["fields"])
        return {"records": records}


class FakeClient:
    """和 FeishuClient 一样，``tables`` / ``fields`` / ``records`` 都是 API 命名空间。"""

    def __init__(self, data: Dict[str, Dict[str, Any]]) -> None:
        self.data = data
        self.tables = FakeTables(self)
        self.fields = FakeFields(self)
        self.records = FakeRecords(self)


def _select(field_id: str, name: str, options: List[str]) -> Dict[str, Any]:
    return {
        "field_name": name,
        "field_id": field_id,
        "type": FieldType.SINGLE_SELECT,
        "property": {"options": [{"name": o} for o in options]},
    }


# 目标表长得像用户那张「需求池」：字段名和标准看板不一样
DEFAULT_FIELDS: List[Dict[str, Any]] = [
    {"field_name": "需求描述", "field_id": "f0", "type": FieldType.TEXT},
    _select("f1", "需求状态", ["待评估", "方案设计中", "开发交付中", "验收中", "已完成"]),
    _select("f2", "优先级", ["P0", "P1", "P2"]),
    _select("f3", "需求分类", ["资源支持", "产品缺陷", "客户卡点需求"]),
]


def _table(
    name: str = "需求池",
    fields=None,
    records=None,
) -> Dict[str, Dict[str, Any]]:
    return {
        "tbl1": {
            "name": name,
            "fields": [dict(f) for f in (fields if fields is not None else DEFAULT_FIELDS)],
            "records": records if records is not None else [],
        }
    }


PROFILE = {
    "tables": [
        {
            "name": "需求池",
            "key": "Issue编号",
            "fields": {
                "需求名称": {"to": "需求描述"},
                "状态": {"to": "需求状态", "values": {"待讨论": "待评估"}},
                "优先级": {"to": "优先级"},
                "需求分类": {"to": "需求分类", "labels": {"产品缺陷": "产品缺陷"}},
            },
        }
    ]
}


def _sync(client, issues, profile=None):
    p = BoardProfile.from_dict(profile or PROFILE)
    return ProfileIssueSync(client, "app1", p).sync_issues(issues)


def _issue(**kw) -> Dict[str, Any]:
    base = {
        "number": 1,
        "title": "接入飞书",
        "labels": [],
        "state": "open",
        "body": "",
        "created_at": "2026-01-01T00:00:00Z",
    }
    base.update(kw)
    return base


# ---- 档案解析 ----


def test_profile_parses_tables_and_rules():
    profile = BoardProfile.from_dict(PROFILE)
    assert len(profile.tables) == 1
    table = profile.tables[0]
    assert table.name == "需求池"
    assert table.key == "Issue编号"
    assert table.target_of("需求名称") == "需求描述"
    assert table.target_of("状态") == "需求状态"


def test_profile_label_rule_has_no_target_of():
    profile = BoardProfile.from_dict(PROFILE)
    table = profile.tables[0]
    assert table.fields["需求分类"].is_label_rule
    assert table.target_of("需求分类") is None


def test_profile_requires_key():
    with pytest.raises(ValueError):
        BoardProfile.from_dict({"tables": [{"name": "x"}]})


def test_profile_from_json_file(tmp_path):
    path = tmp_path / "board.json"
    path.write_text(json.dumps(PROFILE), encoding="utf-8")
    profile = BoardProfile.from_json_file(path)
    assert profile.tables[0].name == "需求池"


# ---- 同步 ----


def test_missing_table_raises_with_table_names():
    client = FakeClient(_table(name="别的表"))
    with pytest.raises(LookupError) as exc:
        _sync(client, [_issue()])
    assert "需求池" in str(exc.value)


def test_create_writes_mapped_fields():
    client = FakeClient(_table())
    result = _sync(client, [_issue(number=7)])
    assert result.created == 1
    assert result.updated == 0

    rec = client.data["tbl1"]["records"][0]
    assert rec["fields"]["需求描述"] == "接入飞书"
    assert rec["fields"]["需求状态"] == "待评估"
    assert rec["fields"]["优先级"] == "P1"
    assert rec["fields"]["Issue编号"] == 7
    # 没在档案里列出的标准字段不写
    assert "需求名称" not in rec["fields"]
    assert "开始时间" not in rec["fields"]


def test_key_field_is_created_when_missing():
    client = FakeClient(_table())
    _sync(client, [_issue(number=3)])
    names = [f["field_name"] for f in client.data["tbl1"]["fields"]]
    assert "Issue编号" in names
    created = next(
        f for f in client.data["tbl1"]["fields"] if f["field_name"] == "Issue编号"
    )
    assert created["type"] == FieldType.NUMBER


def test_existing_key_updates_instead_of_creating():
    fields = DEFAULT_FIELDS + [
        {"field_name": "Issue编号", "field_id": "f9", "type": FieldType.NUMBER}
    ]
    client = FakeClient(
        _table(
            fields=fields,
            records=[{"record_id": "rec_old", "fields": {"Issue编号": 5}}],
        )
    )
    result = _sync(client, [_issue(number=5, title="改过了")])
    assert result.created == 0
    assert result.updated == 1
    assert len(client.data["tbl1"]["records"]) == 1
    assert client.data["tbl1"]["records"][0]["fields"]["需求描述"] == "改过了"


def test_label_rule_picks_matching_label():
    client = FakeClient(_table())
    _sync(client, [_issue(number=11, title="崩了", labels=[{"name": "产品缺陷"}])])
    assert client.data["tbl1"]["records"][0]["fields"]["需求分类"] == "产品缺陷"


def test_label_rule_absent_label_writes_nothing():
    client = FakeClient(_table())
    _sync(client, [_issue(number=12, labels=[{"name": "enhancement"}])])
    assert "需求分类" not in client.data["tbl1"]["records"][0]["fields"]


def test_unmapped_single_select_value_is_skipped_not_invented():
    """目标表词表外的值不能硬塞进去——这一列不更新，并记一条 warning。"""
    client = FakeClient(_table())
    result = _sync(client, [_issue(number=20, labels=[{"name": "wip"}])])
    rec = client.data["tbl1"]["records"][0]
    assert "需求状态" not in rec["fields"]
    # 词表没被污染
    field = next(
        f for f in client.data["tbl1"]["fields"] if f["field_name"] == "需求状态"
    )
    assert [o["name"] for o in field["property"]["options"]] == [
        "待评估",
        "方案设计中",
        "开发交付中",
        "验收中",
        "已完成",
    ]
    assert any("开发中" in w for w in result.warnings)


def test_value_remap_creates_option_in_target_table():
    fields = [
        f for f in DEFAULT_FIELDS if f["field_name"] != "需求状态"
    ] + [_select("f1", "需求状态", [])]
    client = FakeClient(_table(fields=fields))
    _sync(client, [_issue(number=21)])
    field = next(
        f for f in client.data["tbl1"]["fields"] if f["field_name"] == "需求状态"
    )
    options = [o["name"] for o in field["property"]["options"]]
    assert options == ["待评估"]


def test_existing_option_passes_through_without_mapping():
    """目标表已经有「开发中」这个选项时，原样写，不必在档案里映射。"""
    fields = [
        f for f in DEFAULT_FIELDS if f["field_name"] != "需求状态"
    ] + [_select("f1", "需求状态", ["待评估", "开发中"])]
    client = FakeClient(_table(fields=fields))
    _sync(client, [_issue(number=22, labels=[{"name": "wip"}])])
    rec = client.data["tbl1"]["records"][0]
    assert rec["fields"]["需求状态"] == "开发中"


def test_missing_target_field_is_skipped_with_warning():
    client = FakeClient(_table())
    result = _sync(
        client,
        [_issue(number=30)],
        profile={
            "tables": [
                {
                    "name": "需求池",
                    "key": "Issue编号",
                    "fields": {"需求名称": {"to": "不存在的一列"}},
                }
            ]
        },
    )
    rec = client.data["tbl1"]["records"][0]
    assert "不存在的一列" not in rec["fields"]
    assert any("不存在的一列" in w for w in result.warnings)


def test_label_containing_bug_keyword_still_routes_to_bug_by_default():
    """默认 auto：「产品缺陷」含「缺陷」，mapper 会判成 Bug。"""
    out = GitHubIssueMapper().map(
        _issue(number=60, labels=[{"name": "产品缺陷"}])
    )
    assert out["table"] == "Bug 管理"
    assert "Bug 描述" in out["fields"]


def test_variant_requirement_overrides_label_based_routing():
    """variant=requirement 时，分类标签不再影响字段集。"""
    fields = DEFAULT_FIELDS + [
        {"field_name": "需求提出人", "field_id": "f8", "type": FieldType.USER}
    ]
    client = FakeClient(_table(fields=fields))
    profile = {
        "tables": [
            {
                "name": "需求池",
                "key": "Issue编号",
                "variant": "requirement",
                "fields": {"需求名称": {"to": "需求描述"}},
            }
        ]
    }
    issue = _issue(number=61, labels=[{"name": "产品缺陷"}])
    ProfileIssueSync(
        client, "app1", BoardProfile.from_dict(profile)
    ).sync_issues([issue])
    rec = client.data["tbl1"]["records"][0]
    # 标题写进了「需求描述」，而不是因为被判成 Bug 就丢在「Bug 描述」上
    assert rec["fields"]["需求描述"] == "接入飞书"


def test_variant_bug_uses_bug_field_set():
    fields = DEFAULT_FIELDS + [
        {"field_name": "Bug 描述", "field_id": "f9", "type": FieldType.TEXT}
    ]
    client = FakeClient(_table(fields=fields))
    profile = {
        "tables": [
            {
                "name": "需求池",
                "key": "Issue编号",
                "variant": "bug",
                "fields": {"Bug 描述": {"to": "Bug 描述"}},
            }
        ]
    }
    issue = _issue(number=62, labels=[{"name": "enhancement"}])
    ProfileIssueSync(
        client, "app1", BoardProfile.from_dict(profile)
    ).sync_issues([issue])
    rec = client.data["tbl1"]["records"][0]
    assert rec["fields"]["Bug 描述"] == "接入飞书"


def test_invalid_variant_rejected():
    with pytest.raises(ValueError):
        BoardProfile.from_dict(
            {"tables": [{"name": "x", "key": "k", "variant": "nope"}]}
        )


def test_create_opt_in_allows_new_option():
    """档案里写 create: true 才允许往目标表里建新选项。"""
    fields = [
        f for f in DEFAULT_FIELDS if f["field_name"] != "优先级"
    ] + [_select("f2", "优先级", ["P0", "P1", "P2"])]
    client = FakeClient(_table(fields=fields))
    profile = {
        "tables": [
            {
                "name": "需求池",
                "key": "Issue编号",
                "fields": {"优先级": {"to": "优先级", "create": True}},
            }
        ]
    }
    issue = _issue(number=50, labels=[{"name": "P3"}])
    ProfileIssueSync(
        client, "app1", BoardProfile.from_dict(profile)
    ).sync_issues([issue])
    rec = client.data["tbl1"]["records"][0]
    assert rec["fields"]["优先级"] == "P3"
    field = next(
        f for f in client.data["tbl1"]["fields"] if f["field_name"] == "优先级"
    )
    assert "P3" in [o["name"] for o in field["property"]["options"]]


def test_author_source_writes_issue_author():
    """「提出人」取的是 issue 作者（不是 assignee）。"""
    fields = DEFAULT_FIELDS + [
        {"field_name": "需求提出人", "field_id": "f8", "type": FieldType.USER}
    ]
    client = FakeClient(_table(fields=fields))
    profile = {
        "tables": [
            {
                "name": "需求池",
                "key": "Issue编号",
                "fields": {"提出人": {"to": "需求提出人"}},
            }
        ]
    }
    issue = _issue(number=40, user={"login": "alice"})
    ProfileIssueSync(
        client,
        "app1",
        BoardProfile.from_dict(profile),
        config=IssueMapperConfig(user_map={"alice": "ou_alice"}),
    ).sync_issues([issue])
    rec = client.data["tbl1"]["records"][0]
    assert rec["fields"]["需求提出人"] == [{"id": "ou_alice"}]


def test_author_source_skipped_without_user_map():
    fields = DEFAULT_FIELDS + [
        {"field_name": "需求提出人", "field_id": "f8", "type": FieldType.USER}
    ]
    client = FakeClient(_table(fields=fields))
    profile = {
        "tables": [
            {
                "name": "需求池",
                "key": "Issue编号",
                "fields": {"提出人": {"to": "需求提出人"}},
            }
        ]
    }
    issue = _issue(number=41, user={"login": "alice"})
    ProfileIssueSync(
        client, "app1", BoardProfile.from_dict(profile)
    ).sync_issues([issue])
    rec = client.data["tbl1"]["records"][0]
    assert "需求提出人" not in rec["fields"]
