"""Money formatting and rounding (D-01, D-02)."""

import pytest

from app.money import bps, fmt, parse, round_half_up_bps


def test_fmt_indian_grouping():
    assert fmt(12345600) == "1,23,456.00"
    assert fmt(100000) == "1,000.00"
    assert fmt(10000000) == "1,00,000.00"
    assert fmt(0) == "0.00"
    assert fmt(5) == "0.05"


def test_fmt_negative_in_parentheses():
    assert fmt(-500) == "(5.00)"
    assert fmt(-12345600) == "(1,23,456.00)"


def test_parse_roundtrip():
    assert parse("1,23,456.00") == 12345600
    assert parse("1234.5") == 123450
    assert parse("(5.00)") == -500
    assert parse("-5.00") == -500
    assert parse("₹1,234") == 123400
    assert parse("INR 1,234.56") == 123456


@pytest.mark.parametrize("bad", ["", "abc", "1.234", "1,2,3.4.5", "()"])
def test_parse_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse(bad)


def test_round_half_up_bps():
    assert round_half_up_bps(555900, 1800) == 100062
    assert round_half_up_bps(5, 1000) == 1
    assert round_half_up_bps(4, 1000) == 0
    assert round_half_up_bps(-5, 1000) == -1
    assert round_half_up_bps(0, 1800) == 0


def test_bps_from_percent():
    assert bps("18%") == 1800
    assert bps("0.18") == 1800
    assert bps("5%") == 500
