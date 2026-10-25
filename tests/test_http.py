"""HTTP 客户端测试（使用 mock session）。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from feishu_toolkit.errors import FeishuAPIError, FeishuNetworkError
from feishu_toolkit.http import HttpClient


def _resp(status_code=200, json_data=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data
    r.text = "error body"
    return r


def _client(session, token="t-1"):
    tm = MagicMock()
    tm.base_url = "https://open.feishu.cn"
    tm.get_token.return_value = token
    return HttpClient(tm, session=session), tm


def test_success_returns_data():
    session = MagicMock()
    session.request.return_value = _resp(200, {"code": 0, "data": {"ok": True}})
    client, _ = _client(session)
    assert client.get("/path") == {"ok": True}


def test_authorization_header_injected():
    session = MagicMock()
    session.request.return_value = _resp(200, {"code": 0, "data": {}})
    client, _ = _client(session, token="t-abc")
    client.get("/path")
    kwargs = session.request.call_args.kwargs
    assert kwargs["headers"] == {"Authorization": "Bearer t-abc"}


def test_business_error_raises():
    session = MagicMock()
    session.request.return_value = _resp(200, {"code": 91403, "msg": "forbidden"})
    client, _ = _client(session)
    with pytest.raises(FeishuAPIError) as exc:
        client.get("/path")
    assert exc.value.code == 91403


def test_token_refresh_retry_then_success():
    session = MagicMock()
    session.request.side_effect = [
        _resp(200, {"code": 99991663, "msg": "bad token"}),
        _resp(200, {"code": 0, "data": {"recovered": True}}),
    ]
    client, tm = _client(session)
    assert client.get("/path") == {"recovered": True}
    # 第二次获取 token 时强制刷新
    assert tm.get_token.call_count == 2
    assert tm.get_token.call_args_list[1].kwargs == {"force_refresh": True}


def test_network_exception_raises_after_retries():
    session = MagicMock()
    session.request.side_effect = requests.exceptions.ConnectionError("down")
    client, _ = _client(session)
    # 避免真实退避等待
    client._sleep_backoff = lambda attempt: None
    with pytest.raises(FeishuNetworkError):
        client.get("/path")
    assert session.request.call_count == 4  # 首次 + 3 次重试


def test_5xx_retries_then_success():
    session = MagicMock()
    session.request.side_effect = [
        _resp(500),
        _resp(200, {"code": 0, "data": {"ok": 1}}),
    ]
    client, _ = _client(session)
    client._sleep_backoff = lambda attempt: None
    assert client.get("/path") == {"ok": 1}


def test_invalid_json_raises_network_error():
    session = MagicMock()
    r = _resp(200)
    r.json.side_effect = ValueError("not json")
    session.request.return_value = r
    client, _ = _client(session)
    with pytest.raises(FeishuNetworkError):
        client.get("/path")
