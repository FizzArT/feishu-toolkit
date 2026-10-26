"""GitHub Issue 适配器：把 GitHub Issue 映射到标准看板字段。

输入为 GitHub REST API 的 Issue 原始 JSON（dict），输出为
``(table_name, fields)``，其中 fields 已转换为飞书多维表格可写入的格式。

设计要点：
- 通过标签（labels）判断是「需求」还是「Bug」：含 bug / 缺陷 标签 → Bug 管理。
- 状态、优先级、迭代版本、终端等均通过标签 / milestone 识别，支持中英文。
- GitHub 用户名 → 飞书 open_id 的映射通过 ``user_map`` 显式提供，
  未配置的人员字段会被跳过（不报错）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .. import cell_value as cv

# 标准表名
TABLE_REQUIREMENT = "需求管理"
TABLE_BUG = "Bug 管理"


# 标签关键词表（小写匹配）
_BUG_KEYWORDS = ("bug", "缺陷", "错误", "故障", "issue")

# 需求状态
_REQ_STATUS = {
    "已完成": ("已完成", "closed", "done"),
    "设计中": ("设计", "design"),
    "开发中": ("开发", "in progress", "进行中", "wip", "doing"),
    "验收中": ("验收", "review", "测试", "qa", "testing"),
    "待启动": ("待启动", "todo", "待办"),
    "待讨论": ("待讨论", "discussion", "discuss"),
}

# Bug 状态
_BUG_STATUS = {
    "已关闭": ("已关闭", "closed", "done"),
    "修复中": ("修复中", "修复", "in progress", "wip", "doing"),
    "待验收": ("待验收", "验收", "review", "测试", "qa"),
    "未解决": ("未解决", "open", "待处理"),
}

# 优先级
_PRIORITY = {
    "P0": ("p0", "priority:high", "high", "urgent", "紧急", "高"),
    "P1": ("p1", "priority:medium", "medium", "中"),
    "P2": ("p2", "priority:low", "low", "低"),
    "P3": ("p3", "priority:lowest", "lowest"),
}

# 终端
_TERMINAL = {
    "Web": ("web", "网页"),
    "iOS": ("ios", "iphone", "ipad"),
    "Android": ("android", "安卓"),
    "Windows": ("windows", "win"),
    "Mac": ("mac", "macos", "osx"),
}


@dataclass
class IssueMapperConfig:
    """映射配置。

    user_map: GitHub 登录名（小写）→ 飞书 open_id。
    default_priority: 无法识别时的默认优先级。
    """

    user_map: Dict[str, str] = field(default_factory=dict)
    default_priority: str = "P1"
    include_link_in_description: bool = True


class GitHubIssueMapper:
    """把单个 GitHub Issue 映射为标准看板记录。"""

    def __init__(self, config: Optional[IssueMapperConfig] = None) -> None:
        self.config = config or IssueMapperConfig()

    # ---- 公共入口 ----

    def map(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """返回 {"table": 表名, "fields": {字段名: 值}}。"""
        labels = self._labels(issue)
        is_bug = self._match(labels, _BUG_KEYWORDS)
        if is_bug:
            return {"table": TABLE_BUG, "fields": self._map_bug(issue, labels)}
        return {"table": TABLE_REQUIREMENT, "fields": self._map_requirement(issue, labels)}

    # ---- 需求映射 ----

    def _map_requirement(self, issue: Dict[str, Any], labels: List[str]) -> Dict[str, Any]:
        fields: Dict[str, Any] = {
            "需求名称": cv.text(issue["title"]),
            "Issue编号": issue["number"],
            "状态": cv.single_select(self._resolve_status(labels, issue, _REQ_STATUS, "待讨论")),
            "优先级": cv.single_select(self._resolve_priority(labels)),
        }
        body = self._build_body(issue)
        if body:
            fields["需求描述"] = cv.text(body)

        version = self._resolve_version(labels, issue)
        if version:
            fields["迭代版本"] = cv.single_select(version)

        owner = self._resolve_user(issue.get("assignees") or self._single_assignee(issue))
        if owner:
            fields["负责人"] = cv.users(owner)

        start = self._to_ms(issue.get("created_at"))
        if start:
            fields["开始时间"] = start
        end = self._to_ms(issue.get("closed_at"))
        if end:
            fields["结束时间"] = end
        return fields

    # ---- Bug 映射 ----

    def _map_bug(self, issue: Dict[str, Any], labels: List[str]) -> Dict[str, Any]:
        fields: Dict[str, Any] = {
            "Bug 描述": cv.text(issue["title"]),
            "Issue编号": issue["number"],
            "状态": cv.single_select(self._resolve_status(labels, issue, _BUG_STATUS, "未解决")),
            "优先级": cv.single_select(self._resolve_priority(labels)),
        }
        version = self._resolve_version(labels, issue)
        if version:
            fields["修复版本"] = cv.single_select(version)

        terminal = self._match_table(labels, _TERMINAL)
        if terminal:
            fields["终端"] = cv.single_select(terminal)

        reporter = self._resolve_user([issue.get("user")])
        if reporter:
            fields["提交人"] = cv.users(reporter)
        assignee = self._resolve_user(issue.get("assignees") or self._single_assignee(issue))
        if assignee:
            fields["指派人"] = cv.users(assignee)
        return fields

    # ---- 解析辅助 ----

    def _resolve_status(self, labels, issue, table, default_open: str) -> str:
        if issue.get("state") == "closed":
            return "已完成" if table is _REQ_STATUS else "已关闭"
        hit = self._match_table(labels, table)
        return hit or default_open

    def _resolve_priority(self, labels: List[str]) -> str:
        return self._match_table(labels, _PRIORITY) or self.config.default_priority

    def _resolve_version(self, labels: List[str], issue: Dict[str, Any]) -> Optional[str]:
        # 优先 milestone
        milestone = issue.get("milestone")
        if milestone and milestone.get("title"):
            return milestone["title"]
        # 标签里匹配 v1.x / V1.x
        for lb in labels:
            s = lb.strip()
            if s.lower().startswith("v") and any(ch.isdigit() for ch in s):
                return s
        return None

    def _resolve_user(self, users: List[Optional[Dict[str, Any]]]) -> List[str]:
        open_ids: List[str] = []
        for u in users or []:
            if not u:
                continue
            login = (u.get("login") or "").lower()
            oid = self.config.user_map.get(login)
            if oid and oid not in open_ids:
                open_ids.append(oid)
        return open_ids

    @staticmethod
    def _single_assignee(issue: Dict[str, Any]) -> List[Dict[str, Any]]:
        a = issue.get("assignee")
        return [a] if a else []

    def _build_body(self, issue: Dict[str, Any]) -> str:
        body = (issue.get("body") or "").strip()
        if self.config.include_link_in_description:
            link = issue.get("html_url", "")
            if link:
                body = (body + "\n\n" if body else "") + "GitHub: " + link
        return body

    @staticmethod
    def _to_ms(value: Optional[str]) -> Optional[int]:
        if not value:
            return None
        return cv.datetime(value)

    @staticmethod
    def _labels(issue: Dict[str, Any]) -> List[str]:
        return [l.get("name", "") for l in issue.get("labels", [])]

    @staticmethod
    def _match(labels: List[str], keywords) -> bool:
        for lb in labels:
            low = lb.lower()
            if any(k in low for k in keywords):
                return True
        return False

    @staticmethod
    def _match_table(labels: List[str], table: Dict[str, List[str]]) -> Optional[str]:
        """先精确匹配，再退化到子串匹配。

        顺序不能反：``priority:lowest`` 是 P2 关键词 ``priority:low`` 的
        子串，只做子串匹配的话 P3 会被 P2 抢走。
        """
        lowered = [lb.lower().strip() for lb in labels]
        for canonical, kws in table.items():
            for k in kws:
                if k in lowered:
                    return canonical
        for canonical, kws in table.items():
            for lb in lowered:
                if any(k in lb for k in kws):
                    return canonical
        return None
