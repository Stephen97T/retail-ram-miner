from typing import Any
from unittest.mock import MagicMock, mock_open, patch

from ram_miner.state import load_lines, load_state


@patch("builtins.open", new_callable=mock_open, read_data='{"id": 1}\n{"id": 2}\n')
@patch("os.path.exists", return_value=True)
def test_load_lines_basic(mock_exists: MagicMock, mock_file: MagicMock) -> None:
    data_dir = "mock_dir"
    filename = "test.jsonl"

    results = list(load_lines(data_dir, filename))

    assert len(results) == 2
    assert results[0] == {"id": 1}
    assert results[1] == {"id": 2}


@patch(
    "builtins.open", new_callable=mock_open, read_data='{"id": 1}\n\n{"id": 2}\n   \n'
)
@patch("os.path.exists", return_value=True)
def test_load_lines_empty_lines(mock_exists: MagicMock, mock_file: MagicMock) -> None:
    """Test that empty lines are skipped."""
    data_dir = "mock_dir"
    filename = "test.jsonl"

    results = list(load_lines(data_dir, filename))

    assert len(results) == 2
    assert results[0] == {"id": 1}
    assert results[1] == {"id": 2}


@patch("os.path.exists", return_value=False)
def test_load_lines_file_not_found(mock_exists: MagicMock) -> None:
    data_dir = "mock_dir"
    filename = "test.jsonl"

    results = list(load_lines(data_dir, filename))

    assert results == []


@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data='{"id": 1}\nINVALID JSON\n{"id": 2}',
)
@patch("os.path.exists", return_value=True)
def test_load_lines_error_handling(
    mock_exists: MagicMock, mock_file: MagicMock
) -> None:
    """Test that any error during file reading/parsing is handled gracefully (returns partial? or nothing?)."""
    # The code catches Exception and passes, so it likely stops yielding.
    data_dir = "mock_dir"
    filename = "test.jsonl"

    results = list(load_lines(data_dir, filename))

    # Based on implementation:
    # try:
    #   with open...
    #      for line in f:
    #         yield json.loads(line)  <-- Raises JSONDecodeError
    # except Exception:
    #   pass
    # So if line 2 fails, it stops yielding and returns what was yielded so far.
    assert len(results) == 1
    assert results[0] == {"id": 1}


@patch("ram_miner.state.load_lines")
def test_load_state(mock_load: MagicMock) -> None:
    data_dir = "mock_dir"

    def side_effect(d: str, f: str) -> list[dict[str, Any]]:
        if f == "stores.jsonl":
            return [{"store_id": 1}, {"store_id": 2}]
        if f == "brands.jsonl":
            return [{"brand_id": 10}, {"brand_id": 20}]
        if f == "hardware.jsonl":
            return [{"mpn": "MPN1"}, {"mpn": "MPN2"}]
        if f == "listings.jsonl":
            return [
                {"store_id": 1, "store_sku": "SKU1"},
                {"store_id": 2, "store_sku": "SKU2"},
            ]
        return []

    mock_load.side_effect = side_effect

    state = load_state(data_dir)

    assert state["seen_store_ids"] == {1, 2}
    assert state["seen_brand_ids"] == {10, 20}
    assert state["seen_hardware_mpns"] == {"MPN1", "MPN2"}
    assert state["seen_listings"] == {(1, "SKU1"), (2, "SKU2")}


@patch("ram_miner.state.load_lines")
def test_load_state_missing_fields(mock_load: MagicMock) -> None:
    """Test that records missing required keys are skipped."""
    data_dir = "mock_dir"

    def side_effect(d: str, f: str) -> list[dict[str, Any]]:
        if f == "stores.jsonl":
            return [{"name": "No ID"}]
        if f == "brands.jsonl":
            return [{"name": "No ID"}]
        if f == "hardware.jsonl":
            return [{"other": "No MPN"}]
        if f == "listings.jsonl":
            return [{"store_id": 1}]  # Missing store_sku
        return []

    mock_load.side_effect = side_effect

    state = load_state(data_dir)

    assert state["seen_store_ids"] == set()
    assert state["seen_brand_ids"] == set()
    assert state["seen_hardware_mpns"] == set()
    assert state["seen_listings"] == set()
