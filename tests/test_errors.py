"""异常定义测试。"""

from __future__ import annotations

import pytest

from feishu_toolkit.errors import (
    FeishuAPIError,
    FeishuConfigError,
    FeishuError,
    FeishuNetworkError,
    is_auth_error,
)


def test_error_hierarchy():
    assert issubclass(FeishuConfigError, FeishuError)
    assert issubclass(FeishuNetworkError, FeishuError)
    assert issubclass(FeishuAPIError, FeishuError)


def test_api_error_format():
    err = FeishuAPIError(91403, "forbidden")
    assert err.code == 91403
    assert err.msg == "forbidden"
    assert "91403" in str(err)
    assert "forbidden" in str(err)


def test_api_error_with_log_id():
    err = FeishuAPIError(1, "x", log_id="log123")
    assert "log123" in str(err)
    assert err.log_id == "log123"


@pytest.mark.parametrize(
    "code,expected",
    [
        (99991661, True),
        (99991664, True),
        (99991663, True),
        (91403, False),
        (91404, False),
    ],
)
def test_is_auth_error(code, expected):
    assert is_auth_error(code) is expected
