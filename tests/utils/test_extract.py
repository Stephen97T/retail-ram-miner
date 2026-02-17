import typing

from ram_miner.utils.extract import (
    calculate_price_per_gb,
    extract_azerty_specs,
    extract_int,
    get_brand_id,
    get_store_id,
)


def test_extract_int() -> None:
    cases = {
        "32 GB": 32,
        "DDR5-6000": 5,
        "foo 123 bar": 123,
        "no digits": None,
    }

    for input_val, expected in cases.items():
        assert extract_int(input_val) == expected, f"Failed for input: {input_val}"


def test_calculate_price_per_gb() -> None:
    cases: list[
        tuple[tuple[float | str | int | None, int | str | None], float | None]
    ] = [
        ((100.0, 10), 10.0),
        (("100", "50"), 2.0),
        ((100, 0), None),
        ((None, 10), None),
        ((100, None), None),
    ]

    for (price, cap), expected in cases:
        assert calculate_price_per_gb(price, cap) == expected, (
            f"Failed for price={price}, cap={cap}"
        )


# Mocking for extract_azerty_specs


class MockSelector:
    def __init__(self, content: typing.Any):
        self.content = content

    def get(self, default: typing.Any = None) -> typing.Any:
        return self.content if self.content is not None else default

    def strip(self) -> None:
        # The code is .get().strip(), so strip is called on the string result of get()
        # This mock method is not needed if get() returns a string or None.
        pass


class MockRow:
    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value

    def css(self, query: str) -> "MockSelector":
        if "th" in query or "dt" in query:
            return MockSelector(self.key)
        if "td" in query or "dd" in query:
            return MockSelector(self.value)
        return MockSelector(None)


class MockResponse:
    def __init__(self, data: dict[str, str]):
        self.data = data

    def css(self, query: str) -> list[MockRow]:
        if query == "table tr":
            return [MockRow(k, v) for k, v in self.data.items()]
        return []


def test_extract_azerty_specs() -> None:
    data = {
        "Intern geheugen": "32 GB",
        "Kloksnelheid geheugen": "6000 MHz",
        "Overdrachtssnelheid geheugengegevens": "5600 MT/s",
        "CAS-latentie": "36",
        "Intern geheugentype": "DDR5",
        "Merk": "Corsair",
        "Artikelnummer": "12345",
        "Fabrikantcode": "CMH32GX5M2F6000Z36",
        "EAN": "0840440419396",
        "Component voor": "PC/server",
        "Geheugenlayout (modules x formaat)": "2 x 16 GB",
    }

    response = MockResponse(data)
    result = extract_azerty_specs(response)

    expected_values = {
        "capacity_gb": 32,
        "clock_speed": 6000,
        "transfer_speed": 5600,
        "latency": 36,
        "generation": "DDR5",
        "brand": "Corsair",
        "sku": "12345",
        "mpn": "CMH32GX5M2F6000Z36",
        "ean": "0840440419396",
        "system_of_usage": "desktop",
        "modules_count": 2,
        "module_capacity_gb": 16,
    }

    for key, expected in expected_values.items():
        assert result[key] == expected, f"Mismatch for field '{key}'"


def test_get_store_id() -> None:
    assert get_store_id("Azerty") == 1
    assert get_store_id("Alternate") == 2
    assert get_store_id("Unknown Store") == 999


def test_get_brand_id() -> None:
    id_corsair = get_brand_id("Corsair")
    id_gskill = get_brand_id("G.Skill")
    id_none = get_brand_id(None)

    assert isinstance(id_corsair, int)
    assert id_corsair > 0
    assert id_corsair != id_gskill
    assert id_none == 0

    # Determinism check
    id_corsair_2 = get_brand_id("Corsair")
    assert id_corsair == id_corsair_2
