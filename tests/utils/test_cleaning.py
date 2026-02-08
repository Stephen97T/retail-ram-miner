from datetime import datetime

from ram_miner.utils.cleaning import (
    clean_price,
    ensure_timestamp,
    normalize_identifier,
    normalize_system,
    parse_modules,
)


def test_parse_modules_valid_cases() -> None:
    cases = {
        "2 x 16": (2, 16),
        "2x16GB": (2, 16),
        "2x16": (2, 16),
        "4x8 GB": (4, 8),
        "1x32gb": (1, 32),
        "2 x 32 G b": (2, 32),
    }

    for input_val, expected in cases.items():
        assert parse_modules(input_val) == expected, f"Failed for input: {input_val}"


def test_parse_modules_invalid_cases() -> None:
    cases = [None, "", "kit of 2"]

    for input_val in cases:
        assert parse_modules(input_val) == (None, None), (
            f"Failed for input: {input_val}"
        )


def test_normalize_system_cases() -> None:
    cases = {
        "PC": "desktop",
        "Desktop": "desktop",
        "Laptop": "laptop",
        "Notebook": "laptop",
        "Unknown": None,
    }

    for input_val, expected in cases.items():
        assert normalize_system(input_val) == expected, f"Failed for input: {input_val}"


def test_clean_price() -> None:
    cases = {
        "€ 1.000,00": 1000.0,
        "100,50": 100.50,
        "1.234,56": 1234.56,
        "€ 99,-": 99.0,
        "invalid": None,
        None: None,
    }

    for input_val, expected in cases.items():
        assert clean_price(input_val) == expected, f"Failed for input: {input_val}"


def test_normalize_identifier() -> None:
    cases = {
        "  abc  ": "ABC",
        "123": "123",
        456: "456",
        None: None,
        "": None,
    }

    for input_val, expected in cases.items():
        assert normalize_identifier(input_val) == expected, (
            f"Failed for input: {input_val}"
        )


def test_ensure_timestamp() -> None:
    # Case 1: Item has no timestamp
    item = {"sku": "123"}
    ensure_timestamp(item)
    assert "timestamp" in item
    assert isinstance(item["timestamp"], datetime)

    # Case 2: Item already has a timestamp
    existing_time = datetime(2020, 1, 1)
    item_with_ts = {"timestamp": existing_time}
    ensure_timestamp(item_with_ts)
    assert item_with_ts["timestamp"] == existing_time
