"""飞书 HTTP 客户端：统一请求、重试、错误解析与分页。"""

from __future__ import annotations

import time
from typing import Any, Dict, Iterator, Optional

import requests

from .errors import FeishuAPIError, FeishuNetworkError, is_auth_error
from .auth import TokenManager

# 可重试的网络请求次数（首次 + 重试次数）。
_MAX_RETRIES = 3
# 退避基础秒数（指数退避）。
_BACKOFF_BASE = 0.5


class HttpClient:
    """封装对飞书 OpenAPI 的 HTTP 调用。"""

    def __init__(
        self,
        token_manager: TokenManager,
        *,
        timeout: float = 15.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.token_manager = token_manager
        self.base_url = token_manager.base_url
        self.timeout = timeout
        self._session = session or requests.Session()

    # ---- 核心请求 ----

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        expect_json: bool = True,
    ) -> Any:
        """发起一次 HTTP 请求，返回解析后的 JSON（data 字段）。

        - 自动注入 Authorization 头；
        - token 失效时自动刷新并重试一次；
        - 网络错误 / 限流时按指数退避重试。
        """
        url = self.base_url + path
        method = method.upper()
        last_exc: Optional[Exception] = None
        token_refreshed = False

        for attempt in range(_MAX_RETRIES + 1):
            token = self.token_manager.get_token(
                force_refresh=token_refreshed and attempt == 1
            )
            headers = {"Authorization": f"Bearer {token}"}
            try:
                resp = self._session.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=headers,
                    timeout=self.timeout,
                )
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    self._sleep_backoff(attempt)
                    continue
                raise FeishuNetworkError(f"请求失败: {exc}") from exc

            # HTTP 层错误：5xx 与 429 可重试。
            if resp.status_code >= 500 or resp.status_code == 429:
                last_exc = FeishuNetworkError(
                    f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
                if attempt < _MAX_RETRIES:
                    self._sleep_backoff(attempt)
                    continue
                raise last_exc

            if not expect_json:
                return resp

            try:
                data = resp.json()
            except ValueError as exc:
                raise FeishuNetworkError(
                    f"响应不是合法 JSON（HTTP {resp.status_code}）"
                ) from exc

            code = data.get("code", -1)
            if code == 0:
                return data.get("data", {})

            # token 失效：刷新后重试一次。
            if is_auth_error(code) and not token_refreshed:
                token_refreshed = True
                continue

            raise FeishuAPIError(
                code,
                data.get("msg", "unknown"),
                log_id=data.get("log_id"),
                data=data.get("data"),
            )

        # 理论上不会走到这里。
        raise FeishuNetworkError("请求失败（重试耗尽）") from last_exc

    def get(self, path: str, **kwargs: Any) -> Any:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Any:
        return self.request("POST", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Any:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Any:
        return self.request("DELETE", path, **kwargs)

    # ---- 分页 ----

    def iter_pages(
        self,
        path: str,
        *,
        items_key: str = "items",
        page_size: Optional[int] = None,
        page_size_param: str = "page_size",
        page_token_param: str = "page_token",
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Iterator[Dict[str, Any]]:
        """逐页迭代列表接口，yield 每个条目。

        适用于使用 page_token / has_more 分页的飞书接口。
        """
        params: Dict[str, Any] = dict(extra_params or {})
        if page_size is not None:
            params[page_size_param] = page_size
        page_token: Optional[str] = None

        while True:
            if page_token:
                params[page_token_param] = page_token
            data = self.get(path, params=params)
            for item in data.get(items_key, []) or []:
                yield item
            if not data.get("has_more"):
                break
            page_token = data.get("page_token")
            if not page_token:
                break

    @staticmethod
    def _sleep_backoff(attempt: int) -> None:
        delay = _BACKOFF_BASE * (2 ** attempt)
        time.sleep(delay)
