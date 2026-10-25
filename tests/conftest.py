"""pytest 共享夹具。"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest


def make_issue(
    number: int = 1,
    title: str = "测试标题",
    *,
    state: str = "open",
    labels: List[str] | None = None,
    assignees: List[str] | None = None,
    user: str = "alice",
    body: str = "正文",
    milestone: str | None = None,
    created_at: str = "2026-01-01T00:00:00Z",
    closed_at: str | None = None,
) -> Dict[str, Any]:
    """构造一个 GitHub REST API 风格的 Issue dict。"""
    return {
        "number": number,
        "title": title,
        "body": body,
        "state": state,
        "labels": [{"name": n} for n in (labels or [])],
        "assignees": [{"login": a} for a in (assignees or [])],
        "assignee": None,
        "user": {"login": user},
        "html_url": f"https://github.com/owner/repo/issues/{number}",
        "created_at": created_at,
        "closed_at": closed_at,
        "milestone": {"title": milestone} if milestone else None,
    }


@pytest.fixture
def issue_factory():
    return make_issue
