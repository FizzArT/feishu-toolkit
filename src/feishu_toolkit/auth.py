"""飞书认证：tenant_access_token 的获取、缓存与自动刷新。"""

from __future__ import annotations

import threading
import time
from typing import Optional

import requests

from .errors import FeishuAPIError, FeishuConfigError, FeishuNetworkError

# 提前刷新的安全余量（秒），避免临界时间内 token 过期。
_REFRESH_MARGIN = 5 * 60

_TOKEN_PATH = "/open-apis/auth/v3/tenant_access_token/internal"


class TokenManager:
    """管理飞书企业自建应用的 tenant_access_token。

    线程安全：内部使用锁保护 token 缓存。
    """

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        base_url: str,
        *,
        timeout: float = 10.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        if not app_id:
            raise FeishuConfigError("app_id 不能为空")
        if not app_secret:
            raise FeishuConfigError("app_secret 不能为空")
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()
        self._lock = threading.Lock()
        self._token: Optional[str] = None
        self._expire_at: float = 0.0

    def get_token(self, *, force_refresh: bool = False) -> str:
        """返回一个有效的 tenant_access_token，必要时自动刷新。

        Args:
            force_refresh: 强制重新获取（token 失效时调用）。
        """
        with self._lock:
            if force_refresh or self._need_refresh():
                self._refresh()
            assert self._token is not None
            return self._token

    def _need_refresh(self) -> bool:
        if not self._token:
            return True
        return time.time() >= (self._expire_at - _REFRESH_MARGIN)

    def _refresh(self) -> None:
        url = self.base_url + _TOKEN_PATH
        payload = {"app_id": self.app_id, "app_secret": self.app_secret}
        try:
            resp = self._session.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise FeishuNetworkError(f"获取 tenant_access_token 失败: {exc}") from exc

        data = resp.json()
        if data.get("code", -1) != 0:
            raise FeishuAPIError(
                data.get("code", -1),
                data.get("msg", "unknown"),
                log_id=data.get("log_id"),
                data=data.get("data"),
            )

        token = data.get("tenant_access_token")
        if not token:
            raise FeishuAPIError(-1, "响应中缺少 tenant_access_token")

        expire = int(data.get("expire", 7200))
        self._token = token
        self._expire_at = time.time() + expire
