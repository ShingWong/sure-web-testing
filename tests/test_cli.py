"""tests/test_cli.py"""
from src.cli import format_result


def test_format_ok():
    result = format_result({"status": "ok", "data": {"url": "http://example.com", "title": "Example"}})
    assert "ok" in result.lower()
    assert "http://example.com" in result


def test_format_error():
    result = format_result({"status": "error", "error": "Something went wrong"})
    assert "error" in result.lower()
    assert "Something went wrong" in result


def test_format_list():
    result = format_result({"status": "ok", "data": [{"name": "foo"}, {"name": "bar"}]})
    assert "foo" in result
    assert "bar" in result
