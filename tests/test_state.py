import os
from typing import Any
from unittest.mock import MagicMock, patch

from ram_miner.state import load_state


@patch("ram_miner.state._read_lines")
def test_load_state(mock_read_lines: MagicMock) -> None:
    data_dir = "mock_dir"

    def side_effect(fp: str, bucket_name: str | None = None) -> list[dict[str, Any]]:
        filename = fp.split(os.sep)[-1]
        if filename == "stores.jsonl":
            return [{"store_id": 1}, {"store_id": 2}]
        if filename == "brands.jsonl":
            return [{"brand_id": 10}, {"brand_id": 20}]
        if filename == "hardware.jsonl":
            return [{"mpn": "MPN1"}, {"mpn": "MPN2"}]
        if filename == "listings.jsonl":
            return [
                {"store_id": 1, "store_sku": "SKU1"},
                {"store_id": 2, "store_sku": "SKU2"},
            ]
        return []

    mock_read_lines.side_effect = side_effect

    state = load_state(data_dir)

    assert state["seen_store_ids"] == {1, 2}
    assert state["seen_brand_ids"] == {10, 20}
    assert state["seen_hardware_mpns"] == {"MPN1", "MPN2"}
    assert state["seen_listings"] == {(1, "SKU1"), (2, "SKU2")}


@patch("ram_miner.state._read_lines")
def test_load_state_missing_fields(mock_read_lines: MagicMock) -> None:
    """Test that records missing required keys are skipped."""
    data_dir = "mock_dir"

    def side_effect(fp: str, bucket_name: str | None = None) -> list[dict[str, Any]]:
        filename = fp.split(os.sep)[-1]
        if filename == "stores.jsonl":
            return [{"name": "No ID"}]
        if filename == "brands.jsonl":
            return [{"name": "No ID"}]
        if filename == "hardware.jsonl":
            return [{"other": "No MPN"}]
        if filename == "listings.jsonl":
            return [{"store_id": 1}]  # Missing store_sku
        return []

    mock_read_lines.side_effect = side_effect

    state = load_state(data_dir)

    assert state["seen_store_ids"] == set()
    assert state["seen_brand_ids"] == set()
    assert state["seen_hardware_mpns"] == set()
    assert state["seen_listings"] == set()


@patch("ram_miner.state._read_lines")
def test_load_state_with_bucket(mock_read_lines: MagicMock) -> None:
    """Test loading state with a GCS bucket."""
    data_dir = "mock_dir"
    bucket_name = "test-bucket"

    def side_effect(fp: str, bucket: str | None = None) -> list[dict[str, Any]]:
        # Verify bucket name is passed through
        if bucket != bucket_name:
            return []
        filename = fp.split(os.sep)[-1]
        if filename == "stores.jsonl":
            return [{"store_id": 1}]
        return []

    mock_read_lines.side_effect = side_effect

    state = load_state(data_dir, bucket_name=bucket_name)

    assert state["seen_store_ids"] == {1}
    mock_read_lines.assert_any_call(os.path.join(data_dir, "stores.jsonl"), bucket_name)
