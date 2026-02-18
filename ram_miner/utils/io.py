import json
import os
from collections.abc import Iterator
from typing import Any

from google.cloud import storage


def get_gcs_client() -> storage.Client:
    return storage.Client()


def read_lines(
    file_path: str, bucket_name: str | None = None
) -> Iterator[dict[str, Any]]:
    """
    Reads JSONL lines from a file.
    If bucket_name is provided, downloads the file from GCS first (if it exists)
    to the local path, then reads it.
    """
    if bucket_name:
        _download_from_gcs(bucket_name, file_path)

    if os.path.exists(file_path):
        try:
            with open(file_path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        yield json.loads(line)
        except Exception:
            pass


def _download_from_gcs(bucket_name: str, local_path: str) -> None:
    """Downloads a file from GCS to local path if it exists in the bucket."""
    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    # Convert local path (e.g. data/spider/file.jsonl) to GCS key
    # We assume the structure in GCS mirrors the local relative structure
    blob_path = local_path.replace("\\", "/")
    blob = bucket.blob(blob_path)

    if blob.exists():
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        blob.download_to_filename(local_path)


def upload_to_gcs(bucket_name: str, local_path: str) -> None:
    """Uploads a local file to GCS."""
    if not os.path.exists(local_path):
        return

    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob_path = local_path.replace("\\", "/")
    blob = bucket.blob(blob_path)
    blob.upload_from_filename(local_path)
