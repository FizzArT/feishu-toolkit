"""单元格值构造测试。"""

from __future__ import annotations

import datetime as dt

import pytest

from feishu_toolkit import cell_value as cv


def test_text_returns_plain_string():
    assert cv.text("hello") == "hello"
    assert isinstance(cv.text("hello"), str)


def test_text_coerces_non_string():
    assert cv.text(123) == "123"


def test_number_passthrough():
    assert cv.number(5) == 5
    assert cv.number(3.5) == 3.5


def test_single_select_returns_name():
    assert cv.single_select("P0") == "P0"


def test_multi_select_returns_list():
    assert cv.multi_select(["a", "b"]) == ["a", "b"]
    assert cv.multi_select(("a",)) == ["a"]


def test_checkbox():
    assert cv.checkbox(True) is True
    assert cv.checkbox(False) is False


def test_datetime_from_millisecond_int():
    assert cv.datetime(1_700_000_000_000) == 1_700_000_000_000


def test_datetime_from_iso_z():
    ms = cv.datetime("2026-01-01T00:00:00Z")
    assert isinstance(ms, int)
    assert ms > 0


def test_datetime_from_datetime():
    d = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    assert cv.datetime(d) == int(d.timestamp() * 1000)


def test_datetime_none_raises():
    with pytest.raises(ValueError):
        cv.datetime(None)


def test_datetime_unsupported_type_raises():
    with pytest.raises(TypeError):
        cv.datetime(["bad"])


def test_users():
    result = cv.users(["ou_1", "ou_2"])
    assert result == [{"id": "ou_1"}, {"id": "ou_2"}]


def test_url_with_text():
    assert cv.url("https://x.com", "X") == {"link": "https://x.com", "text": "X"}


def test_url_uses_link_as_text():
    assert cv.url("https://x.com") == {"link": "https://x.com", "text": "https://x.com"}


def test_attachments():
    assert cv.attachments(["tok1"]) == [{"file_token": "tok1"}]
