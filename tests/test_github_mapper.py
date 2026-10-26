"""GitHub Issue 适配器映射测试。"""

from __future__ import annotations

from feishu_toolkit.adapters import GitHubIssueMapper, IssueMapperConfig
from feishu_toolkit.adapters.github_issue import TABLE_BUG, TABLE_REQUIREMENT


def _map(issue):
    return GitHubIssueMapper().map(issue)


def test_plain_issue_is_requirement(issue_factory):
    out = _map(issue_factory())
    assert out["table"] == TABLE_REQUIREMENT


def test_bug_label_routes_to_bug(issue_factory):
    out = _map(issue_factory(labels=["bug"]))
    assert out["table"] == TABLE_BUG


def test_bug_label_chinese(issue_factory):
    out = _map(issue_factory(labels=["缺陷"]))
    assert out["table"] == TABLE_BUG


def test_not_a_bug_label_routes_to_bug(issue_factory):
    # "Question/Not a bug" 包含 "bug"，按关键词命中
    out = _map(issue_factory(labels=["Question/Not a bug"]))
    assert out["table"] == TABLE_BUG


def test_requirement_core_fields(issue_factory):
    out = _map(issue_factory(number=42, title="标题"))
    fields = out["fields"]
    assert fields["需求名称"] == "标题"
    assert fields["Issue编号"] == 42
    assert fields["状态"] == "待讨论"
    assert fields["优先级"] == "P1"


def test_bug_core_fields(issue_factory):
    out = _map(issue_factory(number=9, title="崩溃", labels=["bug"]))
    fields = out["fields"]
    assert fields["Bug 描述"] == "崩溃"
    assert fields["Issue编号"] == 9
    assert fields["状态"] == "未解决"


def test_requirement_closed_status(issue_factory):
    out = _map(issue_factory(state="closed"))
    assert out["fields"]["状态"] == "已完成"


def test_bug_closed_status(issue_factory):
    out = _map(issue_factory(state="closed", labels=["bug"]))
    assert out["fields"]["状态"] == "已关闭"


def test_requirement_status_design(issue_factory):
    out = _map(issue_factory(labels=["设计"]))
    assert out["fields"]["状态"] == "设计中"


def test_requirement_status_dev(issue_factory):
    out = _map(issue_factory(labels=["进行中"]))
    assert out["fields"]["状态"] == "开发中"


def test_requirement_status_review(issue_factory):
    out = _map(issue_factory(labels=["验收"]))
    assert out["fields"]["状态"] == "验收中"


def test_bug_status_fixing(issue_factory):
    out = _map(issue_factory(labels=["bug", "修复"]))
    assert out["fields"]["状态"] == "修复中"


def test_bug_status_acceptance(issue_factory):
    out = _map(issue_factory(labels=["bug", "待验收"]))
    assert out["fields"]["状态"] == "待验收"


def test_priority_high(issue_factory):
    out = _map(issue_factory(labels=["high"]))
    assert out["fields"]["优先级"] == "P0"


def test_priority_medium(issue_factory):
    out = _map(issue_factory(labels=["medium"]))
    assert out["fields"]["优先级"] == "P1"


def test_priority_low(issue_factory):
    out = _map(issue_factory(labels=["low"]))
    assert out["fields"]["优先级"] == "P2"


def test_priority_explicit_p0(issue_factory):
    out = _map(issue_factory(labels=["P0"]))
    assert out["fields"]["优先级"] == "P0"


def test_default_priority_override(issue_factory):
    mapper = GitHubIssueMapper(IssueMapperConfig(default_priority="P2"))
    out = mapper.map(issue_factory())
    assert out["fields"]["优先级"] == "P2"


def test_priority_p3(issue_factory):
    out = _map(issue_factory(labels=["P3"]))
    assert out["fields"]["优先级"] == "P3"


def test_priority_lowest_beats_p2_substring(issue_factory):
    """'priority:lowest' 是 P2 关键词 'priority:low' 的子串，精确匹配必须先判。"""
    out = _map(issue_factory(labels=["priority:lowest"]))
    assert out["fields"]["优先级"] == "P3"


def test_priority_p2_still_low(issue_factory):
    out = _map(issue_factory(labels=["priority:low"]))
    assert out["fields"]["优先级"] == "P2"


def test_version_from_milestone(issue_factory):
    out = _map(issue_factory(milestone="v2.0"))
    assert out["fields"]["迭代版本"] == "v2.0"


def test_bug_version_from_milestone(issue_factory):
    out = _map(issue_factory(labels=["bug"], milestone="v1.5"))
    assert out["fields"]["修复版本"] == "v1.5"


def test_version_from_label(issue_factory):
    out = _map(issue_factory(labels=["v1.3"]))
    assert out["fields"]["迭代版本"] == "v1.3"


def test_terminal_android(issue_factory):
    out = _map(issue_factory(labels=["bug", "android"]))
    assert out["fields"]["终端"] == "Android"


def test_terminal_ios(issue_factory):
    out = _map(issue_factory(labels=["bug", "ios"]))
    assert out["fields"]["终端"] == "iOS"


def test_terminal_mac(issue_factory):
    out = _map(issue_factory(labels=["bug", "macos"]))
    assert out["fields"]["终端"] == "Mac"


def test_user_mapping_assignee(issue_factory):
    mapper = GitHubIssueMapper(
        IssueMapperConfig(user_map={"bob": "ou_bob"})
    )
    out = mapper.map(issue_factory(assignees=["bob"]))
    assert out["fields"]["负责人"] == [{"id": "ou_bob"}]


def test_user_mapping_unknown_skipped(issue_factory):
    out = _map(issue_factory(assignees=["stranger"]))
    assert "负责人" not in out["fields"]


def test_bug_reporter_and_assignee(issue_factory):
    mapper = GitHubIssueMapper(
        IssueMapperConfig(user_map={"alice": "ou_a", "bob": "ou_b"})
    )
    out = mapper.map(issue_factory(labels=["bug"], user="alice", assignees=["bob"]))
    assert out["fields"]["提交人"] == [{"id": "ou_a"}]
    assert out["fields"]["指派人"] == [{"id": "ou_b"}]


def test_description_includes_link(issue_factory):
    out = _map(issue_factory(body="内容"))
    desc = out["fields"]["需求描述"]
    assert "内容" in desc
    assert "GitHub: https://github.com" in desc


def test_description_no_link_when_disabled(issue_factory):
    mapper = GitHubIssueMapper(
        IssueMapperConfig(include_link_in_description=False)
    )
    out = mapper.map(issue_factory(body="内容"))
    assert out["fields"]["需求描述"] == "内容"


def test_start_time_from_created(issue_factory):
    out = _map(issue_factory(created_at="2026-01-01T00:00:00Z"))
    assert out["fields"]["开始时间"] > 0


def test_end_time_from_closed(issue_factory):
    out = _map(
        issue_factory(
            state="closed",
            created_at="2026-01-01T00:00:00Z",
            closed_at="2026-01-02T00:00:00Z",
        )
    )
    assert out["fields"]["结束时间"] > out["fields"]["开始时间"]
