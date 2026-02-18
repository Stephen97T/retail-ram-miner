import os
from unittest.mock import MagicMock, mock_open, patch

from ram_miner.utils.io import read_lines, upload_to_gcs


@patch("ram_miner.utils.io.get_gcs_client")
@patch("os.path.exists")
@patch("builtins.open", new_callable=mock_open, read_data='{"id": 1}\n')
def test_read_lines_bucket(
    mock_file: MagicMock, mock_exists: MagicMock, mock_get_client: MagicMock
) -> None:
    data_dir = "data/test"
    filename = "test.jsonl"
    file_path = os.path.join(data_dir, filename)
    bucket_name = "test-bucket"

    mock_exists.return_value = True

    # Setup GCS mocks
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_blob.exists.return_value = True

    results = list(read_lines(file_path, bucket_name))

    # Verify download triggered
    mock_client.bucket.assert_called_with(bucket_name)
    # Blob path should use forward slashes even on Windows
    expected_blob_path = file_path.replace("\\", "/")
    mock_bucket.blob.assert_called_with(expected_blob_path)
    mock_blob.download_to_filename.assert_called_with(file_path)

    # Verify read
    assert len(results) == 1
    assert results[0] == {"id": 1}


@patch("ram_miner.utils.io.get_gcs_client")
@patch("os.path.exists")
def test_upload_to_gcs(mock_exists: MagicMock, mock_get_client: MagicMock) -> None:
    local_path = "data/test/stores.jsonl"
    bucket_name = "test-bucket"

    mock_exists.return_value = True

    # Setup GCS mocks
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    upload_to_gcs(bucket_name, local_path)

    mock_client.bucket.assert_called_with(bucket_name)
    expected_blob_path = local_path.replace("\\", "/")
    mock_bucket.blob.assert_called_with(expected_blob_path)
    mock_blob.upload_from_filename.assert_called_with(local_path)
