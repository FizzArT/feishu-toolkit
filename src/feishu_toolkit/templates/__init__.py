"""标准看板模板与同步服务：统一字段、选项、视图与幂等创建。"""

from .board_service import BoardRef, BoardService
from .requirements_bug_board import (
    BUG_TABLE,
    BUG_VIEWS,
    REQUIREMENT_TABLE,
    REQUIREMENT_VIEWS,
    STANDARD_BOARD,
)

__all__ = [
    "BoardService",
    "BoardRef",
    "STANDARD_BOARD",
    "REQUIREMENT_TABLE",
    "REQUIREMENT_VIEWS",
    "BUG_TABLE",
    "BUG_VIEWS",
]
