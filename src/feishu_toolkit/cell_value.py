"""单元格值（Cell Value）构造：友好输入 → 飞书 API 格式。"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List, Optional, Sequence


def text(value: str) -> str:
    """多行文本：直接传字符串（API 要求字符串，不接受富文本数组）。"""
    return str(value)


def number(value: Any) -> Any:
    """数字。"""
    return value


def single_select(option: str) -> str:
    """单选：传选项名。"""
    return option


def multi_select(options: Sequence[str]) -> List[str]:
    """多选：传选项名数组。"""
    return list(options)


def checkbox(value: bool) -> bool:
    """复选框。"""
    return bool(value)


def datetime(value: Any) -> int:
    """日期：接受 datetime / ISO 字符串 / 毫秒时间戳，返回毫秒时间戳。"""
    if value is None:
        raise ValueError("日期值不能为 None")
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, _dt.datetime):
        dt = value
    elif isinstance(value, str):
        dt = _parse_iso(value)
    else:
        raise TypeError(f"不支持的日期类型: {type(value)}")
    return int(dt.timestamp() * 1000)


def users(open_ids: Sequence[str]) -> List[Dict[str, str]]:
    """人员：传飞书 open_id 数组。"""
    return [{"id": str(oid)} for oid in open_ids]


def url(link: str, text: Optional[str] = None) -> Dict[str, str]:
    """超链接。"""
    return {"link": link, "text": text or link}


def attachments(file_tokens: Sequence[str]) -> List[Dict[str, str]]:
    """附件：传文件 file_token 数组。"""
    return [{"file_token": str(t)} for t in file_tokens]


def _parse_iso(value: str) -> _dt.datetime:
    """解析 ISO 8601 字符串（兼容末尾 Z）。"""
    cleaned = value.strip().replace("Z", "+00:00")
    try:
        return _dt.datetime.fromisoformat(cleaned)
    except ValueError:
        # 退化处理：仅日期
        return _dt.datetime.fromisoformat(value[:10])
