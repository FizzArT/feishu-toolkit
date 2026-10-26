"""按看板档案（BoardProfile）把 GitHub Issue 同步到**任意已有表**。

和 :class:`~feishu_toolkit.adapters.github_issue_sync.GitHubIssueSync` 的区别：

- 标准同步固定往「需求管理 / Bug 管理」两张表写，字段名固定；
- 本模块按档案里的映射写到**指定的一张表**的**指定字段**，
  表可以是别的团队建的，字段名和单选选项都可以不一样。

去重键由档案的 ``key`` 指定（目标表里那个字段名），不存在时自动建一个
数字字段。

## 写单选字段的三条规则

目标表往往有自己的一套词表（模板里的「开发中」在别的表里叫「开发交付中」）。
往别人的表里塞一个词表外的选项，事后还得手动清理，所以这里的优先级是：

1. 档案里 ``values`` 显式映射过的值 —— 直接用，**目标表没有就建出来**；
2. 目标表**已有**的选项 —— 原样写；
3. 其余情况 —— **这一列不更新**，并在结果里记一条 warning。

也就是说：档案里的 ``values`` 是必须补全的映射表，漏了一个状态，
那一列就保持原样，而不是在目标表里长出一个新选项。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..api.fields import FieldType
from ..templates.board_profile import BoardProfile, TableProfile
from .field_options import ensure_select_options
from .github_issue import GitHubIssueMapper, IssueMapperConfig
from .github_issue_sync import SyncResult


def _label_names(issue: Dict[str, Any]) -> List[str]:
    """取出 issue 的标签名（GitHub REST 返回 [{"name": "..."}]）。"""
    names: List[str] = []
    for label in issue.get("labels") or []:
        name = label.get("name") if isinstance(label, dict) else label
        if name:
            names.append(str(name))
    return names


class ProfileIssueSync:
    """按档案同步 GitHub Issue。"""

    def __init__(
        self,
        client: Any,
        app_token: str,
        profile: BoardProfile,
        *,
        config: Optional[IssueMapperConfig] = None,
        mapper: Optional[GitHubIssueMapper] = None,
    ) -> None:
        self._client = client
        self._app_token = app_token
        self.profile = profile
        self.mapper = mapper or GitHubIssueMapper(config)
        # 去重键字段是否为文本类型（决定写 int 还是 str）
        self._key_is_text = False

    # ---- 表定位 ----

    def resolve_table_id(self, table: TableProfile) -> str:
        """按表名找到 table_id。找不到直接报错，不新建。

        新建出来的表结构和用户已有的表几乎不可能一致，硬建一张新表只会
        让数据散在两个地方，不如直接失败让人去改档案。
        """
        tables = self._client.tables.list(self._app_token)
        for item in tables:
            if item.get("name") == table.name:
                return str(item["table_id"])
        known = [t.get("name") for t in tables]
        raise LookupError(
            f"Base 里没有名为「{table.name}」的表。现有表：{known}。"
            f"确认 app_token 是否指向正确的 Base，以及档案里的表名是否写对。"
        )

    # ---- 同步 ----

    def sync_issues(self, issues: List[Dict[str, Any]]) -> SyncResult:
        """把 issues 同步到档案指定的那张表。"""
        if not self.profile.tables:
            raise ValueError("档案里没有配置任何表")

        result = SyncResult()
        for table in self.profile.tables:
            created, updated, rids, warnings = self._sync_table(table, issues)
            result.created += created
            result.updated += updated
            result.record_ids.extend(rids)
            result.warnings.extend(warnings)
        return result

    def _sync_table(
        self, table: TableProfile, issues: List[Dict[str, Any]]
    ) -> Tuple[int, int, List[str], List[str]]:
        app = self._app_token
        tid = self.resolve_table_id(table)
        self._ensure_key_field(app, tid, table.key)

        field_defs = {f["field_name"]: f for f in self._client.fields.list(app, tid)}
        index = self._build_index(app, tid, table.key)
        to_create: List[Dict[str, Any]] = []
        to_update: List[Dict[str, Any]] = []
        warnings: List[str] = []

        for issue in issues:
            fields, issue_warnings = self._map_issue(issue, table, field_defs)
            warnings.extend(issue_warnings)
            if not fields:
                continue
            rid = index.get(str(issue["number"]))
            if rid:
                to_update.append({"record_id": rid, "fields": fields})
            else:
                to_create.append({"fields": fields})

        # 写入前补齐单选选项（档案里显式映射出来的值，目标表没有就建）
        ensure_select_options(
            self._client,
            app,
            tid,
            [r["fields"] for r in to_create] + [r["fields"] for r in to_update],
        )

        created_ids: List[str] = []
        for chunk in _chunks(to_create, 200):
            resp = self._client.records.batch_create(app, tid, chunk)
            created_ids.extend(
                r.get("record_id") for r in resp.get("records", []) if r.get("record_id")
            )
        for chunk in _chunks(to_update, 200):
            self._client.records.batch_update(app, tid, chunk)

        rids = created_ids + [r["record_id"] for r in to_update]
        return len(to_create), len(to_update), rids, warnings

    # ---- 映射 ----

    def _map_issue(
        self,
        issue: Dict[str, Any],
        table: TableProfile,
        field_defs: Dict[str, Dict[str, Any]],
    ) -> Tuple[Dict[str, Any], List[str]]:
        """标准字段 → 档案映射 → 目标字段。"""
        semantic = self.mapper.map(issue)["fields"]
        out: Dict[str, Any] = {}
        warnings: List[str] = []

        for source, rule in table.fields.items():
            if rule.is_label_rule:
                # 从 issue 标签取值：取第一个命中的标签
                target = rule.to or source
                if target not in field_defs:
                    warnings.append(
                        f"#{issue['number']} 目标表没有字段「{target}」，"
                        f"档案里 {source} → {target} 跳过了"
                    )
                    continue
                for label in _label_names(issue):
                    if label in rule.labels:
                        out[target] = rule.labels[label]
                        break
                continue

            if source not in semantic:
                continue
            value = semantic[source]
            target = rule.to or source

            if target not in field_defs:
                warnings.append(
                    f"#{issue['number']} 目标表没有字段「{target}」，"
                    f"档案里 {source} → {target} 跳过了"
                )
                continue

            if isinstance(value, str) and value in rule.values:
                # 显式映射：目标表没有这个选项也要建出来
                out[target] = rule.values[value]
                continue

            if self._is_select(field_defs, target) and not self._has_option(
                field_defs, target, value
            ):
                # 目标表没有这个选项，又没有显式映射：
                # 宁可这一列不更新，也不在别人的表里塞一个词表外的选项
                warnings.append(
                    f"#{issue['number']} 「{target}」没有选项「{value}」，"
                    f"档案里补一条 values 映射再同步"
                )
                continue

            out[target] = value

        # 去重键最后写，保证它一定是 issue 编号
        out[table.key] = self._key_value(issue["number"])
        return out, warnings

    def _key_value(self, number: int) -> Any:
        """按目标字段类型决定写 int 还是 str。"""
        if self._key_is_text:
            return str(number)
        return number

    # ---- 内部 ----

    def _ensure_key_field(self, app: str, tid: str, key: str) -> None:
        """确保去重键字段存在；不存在则建一个数字字段。"""
        fields = {f["field_name"]: f for f in self._client.fields.list(app, tid)}
        fdef = fields.get(key)
        if fdef is None:
            self._client.fields.create(
                app,
                tid,
                {
                    "field_name": key,
                    "type": FieldType.NUMBER,
                    "property": {"formatter": "0"},
                },
            )
            self._key_is_text = False
            return
        self._key_is_text = fdef.get("type") == FieldType.TEXT

    @staticmethod
    def _is_select(field_defs: Dict[str, Dict[str, Any]], name: str) -> bool:
        fdef = field_defs.get(name) or {}
        return fdef.get("type") == FieldType.SINGLE_SELECT

    @staticmethod
    def _has_option(
        field_defs: Dict[str, Dict[str, Any]], name: str, value: Any
    ) -> bool:
        fdef = field_defs.get(name) or {}
        options = (fdef.get("property") or {}).get("options") or []
        return any(o.get("name") == value for o in options)

    def _build_index(self, app: str, tid: str, key: str) -> Dict[str, str]:
        """建立 去重键值 → record_id 索引。"""
        records = self._client.records.list(app, tid, field_names=[key], page_size=500)
        index: Dict[str, str] = {}
        for r in records:
            value = r.get("fields", {}).get(key)
            if value is None:
                continue
            index[str(value)] = r["record_id"]
        return index


def _chunks(seq: List[Any], size: int):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]
