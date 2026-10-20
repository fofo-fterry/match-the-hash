"""Spec sections 0 and 1: money helpers."""
from decimal import Decimal

import pytest

import farmstand as fs


@pytest.mark.parametrize("text, cents", [
    ("3", 300),
    ("3.5", 350),
    ("$3.50", 350),
    ("0.07", 7),
    ("0", 0),
    ("  $12.00 ", 1200),
    ("$1000", 100000),
    ("1,000", 100000),
    ("$1,234.56", 123456),
    ("12,345,678.9", 1234567890),
])
def test_parse_price(text, cents):
    result = fs.parse_price(text)
    assert result == cents
    assert type(result) is int


@pytest.mark.parametrize("text", [
    "",
    "   ",
    "$",
    "abc",
    "3.",
    ".50",
    "3.505",
    "-1",
    "1,00",
    "1,0000",
    ",100",
    "$ 3",
    "3$",
    "$$3",
    "1.2.3",
])
def test_parse_price_rejects(text):
    with pytest.raises(ValueError):
        fs.parse_price(text)


@pytest.mark.parametrize("cents, text", [
    (0, "$0.00"),
    (5, "$0.05"),
    (99, "$0.99"),
    (100, "$1.00"),
    (350, "$3.50"),
    (99999, "$999.99"),
    (100000, "$1,000.00"),
    (123456, "$1,234.56"),
    (100000000, "$1,000,000.00"),
    (-250, "-$2.50"),
    (-123456, "-$1,234.56"),
])
def test_format_price(cents, text):
    assert fs.format_price(cents) == text


@pytest.mark.parametrize("cents", [0, 1, 99, 1000, 123456, 987654321])
def test_parse_price_reads_what_format_price_writes(cents):
    assert fs.parse_price(fs.format_price(cents)) == cents


@pytest.mark.parametrize("cents, percent, expected", [
    (1000, 10, 100),
    (1000, "8.25", 83),            # 82.5 -> halves round UP
    (250, 9, 23),                  # 22.5 -> 23 (round() would give 22)
    (1, 50, 1),                    # 0.5  -> 1
    (3, 50, 2),                    # 1.5  -> 2
    (1050, "9.125", 96),           # 95.8125
    (199, Decimal("12.5"), 25),    # 24.875
    (100, "33.333", 33),           # 33.333
    (10000, "0.005", 1),           # 0.5
    (3000, "1.15", 35),            # 34.5 -> 35 (float math gets 34)
    (0, 50, 0),
    (999, 0, 0),
])
def test_percent_of(cents, percent, expected):
    result = fs.percent_of(cents, percent)
    assert result == expected
    assert type(result) is int
