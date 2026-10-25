"""GitHub Issue → 标准看板同步服务（upsert）。

以「Issue编号」为关联键：
- 看板中不存在该编号 → 创建记录；
- 已存在 → 更新记录。

支持单条与批量；批量时按表分组，分别走 batch_create / batch_update，
减少请求次数。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .github_issue import (
    GitHubIssueMapper,
    IssueMapperConfig,
    TABLE_BUG,
    TABLE_REQUIREMENT,
)


@dataclass
class SyncResult:
    """一次同步的统计结果。"""

    created: int = 0
    updated: int = 0
    record_ids: List[str] = None

    def __post_init__(self) -> None:
        if self.record_ids is None:
            self.record_ids = []


class GitHubIssueSync:
    """把 GitHub Issue 列表同步到标准看板。"""

    def __init__(
        self,
        client: Any,
        board_ref: Any,
        *,
        config: Optional[IssueMapperConfig] = None,
        mapper: Optional[GitHubIssueMapper] = None,
    ) -> None:
        self._client = client
        self._board = board_ref
        self.mapper = mapper or GitHubIssueMapper(config)

    # ---- 单条 ----

    def sync_issue(self, issue: Dict[str, Any]) -> str:
        """同步单条 Issue，返回 record_id。"""
        mapped = self.mapper.map(issue)
        table = mapped["table"]
        tid = self._board.table_id(table)
        app = self._board.app_token

        existing = self._find_record_id(app, tid, issue["number"])
        if existing:
            self._client.records.update(app, tid, existing, mapped["fields"])
            return existing
        rec = self._client.records.create(app, tid, mapped["fields"])
        return rec.get("record", {}).get("record_id")

    # ---- 批量 ----

    def sync_issues(self, issues: List[Dict[str, Any]]) -> SyncResult:
        """批量同步，按表分组后批量创建 / 更新。"""
        result = SyncResult()
        # 预先建立两张表的 编号 → record_id 索引
        indexes = {
            t: self._build_index(self._board.app_token, self._board.table_id(t))
            for t in (TABLE_REQUIREMENT, TABLE_BUG)
        }
        to_create: Dict[str, List[Dict[str, Any]]] = {
            TABLE_REQUIREMENT: [], TABLE_BUG: []
        }
        to_update: Dict[str, List[Dict[str, Any]]] = {
            TABLE_REQUIREMENT: [], TABLE_BUG: []
        }

        for issue in issues:
            mapped = self.mapper.map(issue)
            table = mapped["table"]
            num = issue["number"]
            rid = indexes[table].get(num)
            if rid:
                to_update[table].append({"record_id": rid, "fields": mapped["fields"]})
            else:
                to_create[table].append({"fields": mapped["fields"]})

        for table in (TABLE_REQUIREMENT, TABLE_BUG):
            app = self._board.app_token
            tid = self._board.table_id(table)
            for chunk in self._chunks(to_create[table], 200):
                resp = self._client.records.batch_create(app, tid, chunk)
                rids = [r.get("record_id") for r in resp.get("records", [])]
                result.created += len(chunk)
                result.record_ids.extend(rids)
            for chunk in self._chunks(to_update[table], 200):
                self._client.records.batch_update(app, tid, chunk)
                result.updated += len(chunk)
                result.record_ids.extend([r["record_id"] for r in chunk])
        return result

    # ---- 内部 ----

    def _build_index(self, app: str, tid: str) -> Dict[int, str]:
        """读取表内全部记录，建立 Issue编号 → record_id 索引。"""
        records = self._client.records.list(
            app, tid, field_names=["Issue编号"], page_size=500
        )
        index: Dict[int, str] = {}
        for r in records:
            num = r.get("fields", {}).get("Issue编号")
            if num is not None:
                index[int(num)] = r["record_id"]
        return index

    def _find_record_id(self, app: str, tid: str, number: int) -> Optional[str]:
        records = self._client.records.list(
            app, tid, field_names=["Issue编号"], page_size=500
        )
        for r in records:
            if r.get("fields", {}).get("Issue编号") == number:
                return r["record_id"]
        return None

    @staticmethod
    def _chunks(seq: List[Any], size: int):
        for i in range(0, len(seq), size):
            yield seq[i : i + size]
