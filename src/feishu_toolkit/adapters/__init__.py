"""适配器：把外部系统（如 GitHub Issue）映射为标准看板字段。"""

from .github_issue import GitHubIssueMapper, IssueMapperConfig
from .github_issue_sync import GitHubIssueSync, SyncResult

__all__ = [
    "GitHubIssueMapper",
    "IssueMapperConfig",
    "GitHubIssueSync",
    "SyncResult",
]
