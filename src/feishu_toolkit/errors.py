"""飞书集成工具：统一异常定义。"""

from __future__ import annotations

from typing import Any, Optional


class FeishuError(Exception):
    """所有飞书 SDK 异常的基类。"""


class FeishuConfigError(FeishuError):
    """配置缺失或非法（如缺少 app_id / app_secret）。"""


class FeishuNetworkError(FeishuError):
    """网络层错误（连接失败、超时、HTTP 非 2xx 等）。"""


class FeishuAPIError(FeishuError):
    """飞书 OpenAPI 返回业务错误（code != 0）。

    Attributes:
        code: 飞书返回的错误码（int）。
        msg: 错误描述。
        log_id: 请求日志 ID，便于排查。
        data: 原始返回中的 data 字段（可能为 None）。
    """

    def __init__(
        self,
        code: int,
        msg: str,
        *,
        log_id: Optional[str] = None,
        data: Any = None,
    ) -> None:
        self.code = code
        self.msg = msg
        self.log_id = log_id
        self.data = data
        text = f"[{code}] {msg}"
        if log_id:
            text += f" (log_id={log_id})"
        super().__init__(text)


# 常见错误码（参考飞书开放平台文档，仅用于友好分类）。
CODE_FORBIDDEN = 99991663
CODE_INVALID_TOKEN = 99991661
CODE_TOKEN_EXPIRED = 99991664
CODE_NOT_FOUND = 91404
CODE_NO_PERMISSION = 91403
CODE_RATE_LIMIT = 99991400
CODE_CONFLICT = 1254291


def is_auth_error(code: int) -> bool:
    """判断错误码是否属于 token 失效/过期（可通过刷新 token 重试）。"""
    return code in (CODE_INVALID_TOKEN, CODE_TOKEN_EXPIRED, CODE_FORBIDDEN)
