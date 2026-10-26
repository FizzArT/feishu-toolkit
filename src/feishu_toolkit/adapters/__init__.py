"""适配器：把外部系统（如 GitHub Issue）映射为标准看板字段。"""

from .field_options import ensure_select_options
from .github_issue import GitHubIssueMapper, IssueMapperConfig
from .github_issue_sync import GitHubIssueSync, SyncResult
from .profile_sync import ProfileIssueSync

__all__ = [
    "GitHubIssueMapper",
    "IssueMapperConfig",
    "GitHubIssueSync",
    "SyncResult",
    "ProfileIssueSync",
    "ensure_select_options",
]
