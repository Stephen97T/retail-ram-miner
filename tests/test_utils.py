from ram_miner.utils.cleaning import normalize_system, parse_modules


def test_parse_modules_valid_cases():
    assert parse_modules("2 x 16") == (2, 16)
    assert parse_modules("2x16GB") == (2, 16)
    assert parse_modules("2x16") == (2, 16)
    assert parse_modules("4x8 GB") == (4, 8)
    assert parse_modules("1x32gb") == (1, 32)
    assert parse_modules("2 x 32 G b") == (2, 32)


def test_parse_modules_invalid_cases():
    assert parse_modules(None) == (None, None)
    assert parse_modules("") == (None, None)
    assert parse_modules("kit of 2") == (None, None)


def test_normalize_system_cases():
    assert normalize_system("PC") == "desktop"
    assert normalize_system("Desktop") == "desktop"
    assert normalize_system("Laptop") == "laptop"
    assert normalize_system("Notebook") == "laptop"
    assert normalize_system("Unknown") is None
