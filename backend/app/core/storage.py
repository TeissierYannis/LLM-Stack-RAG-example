"""Cloud object storage for raw document files.

Supports:
- AWS S3
- Google Cloud Storage (GCS)
- Azure Blob Storage
- Local filesystem (development fallback)

Documents are stored with key: {assistant_id}/{document_id}/{filename}
"""

import io
import logging
import os
from enum import Enum

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageProvider(str, Enum):
    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    AZURE_BLOB = "azure_blob"


async def upload_file(
    assistant_id: str,
    document_id: str,
    filename: str,
    content: bytes,
) -> str:
    """Upload a file to the configured storage backend.

    Returns the storage key/path.
    """
    key = f"{assistant_id}/{document_id}/{filename}"
    provider = StorageProvider(settings.storage_provider)

    if provider == StorageProvider.S3:
        return await _upload_s3(key, content)
    elif provider == StorageProvider.GCS:
        return await _upload_gcs(key, content)
    elif provider == StorageProvider.AZURE_BLOB:
        return await _upload_azure(key, content)
    else:
        return await _upload_local(key, content)


async def download_file(key: str) -> bytes:
    """Download a file from the configured storage backend."""
    provider = StorageProvider(settings.storage_provider)

    if provider == StorageProvider.S3:
        return await _download_s3(key)
    elif provider == StorageProvider.GCS:
        return await _download_gcs(key)
    elif provider == StorageProvider.AZURE_BLOB:
        return await _download_azure(key)
    else:
        return await _download_local(key)


async def delete_file(key: str) -> None:
    """Delete a file from the configured storage backend."""
    provider = StorageProvider(settings.storage_provider)

    if provider == StorageProvider.S3:
        await _delete_s3(key)
    elif provider == StorageProvider.GCS:
        await _delete_gcs(key)
    elif provider == StorageProvider.AZURE_BLOB:
        await _delete_azure(key)
    else:
        await _delete_local(key)


async def delete_prefix(prefix: str) -> None:
    """Delete all files under a prefix (e.g. for assistant deletion)."""
    provider = StorageProvider(settings.storage_provider)

    if provider == StorageProvider.S3:
        await _delete_prefix_s3(prefix)
    elif provider == StorageProvider.GCS:
        await _delete_prefix_gcs(prefix)
    elif provider == StorageProvider.AZURE_BLOB:
        await _delete_prefix_azure(prefix)
    else:
        await _delete_prefix_local(prefix)


# ---------------------------------------------------------------------------
# Local filesystem
# ---------------------------------------------------------------------------

def _local_path(key: str) -> str:
    base = settings.storage_local_path
    path = os.path.join(base, key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


async def _upload_local(key: str, content: bytes) -> str:
    path = _local_path(key)
    with open(path, "wb") as f:
        f.write(content)
    logger.info(f"Stored locally: {path}")
    return key


async def _download_local(key: str) -> bytes:
    path = _local_path(key)
    with open(path, "rb") as f:
        return f.read()


async def _delete_local(key: str) -> None:
    path = _local_path(key)
    if os.path.exists(path):
        os.remove(path)


async def _delete_prefix_local(prefix: str) -> None:
    import shutil
    base = settings.storage_local_path
    path = os.path.join(base, prefix)
    if os.path.exists(path):
        shutil.rmtree(path)


# ---------------------------------------------------------------------------
# AWS S3
# ---------------------------------------------------------------------------

def _get_s3_client():
    import boto3
    return boto3.client(
        "s3",
        region_name=settings.aws_region or None,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
    )


async def _upload_s3(key: str, content: bytes) -> str:
    client = _get_s3_client()
    client.put_object(
        Bucket=settings.storage_bucket,
        Key=key,
        Body=content,
        ServerSideEncryption="aws:kms" if settings.storage_encrypt else "AES256",
    )
    logger.info(f"Stored in S3: s3://{settings.storage_bucket}/{key}")
    return key


async def _download_s3(key: str) -> bytes:
    client = _get_s3_client()
    response = client.get_object(Bucket=settings.storage_bucket, Key=key)
    return response["Body"].read()


async def _delete_s3(key: str) -> None:
    client = _get_s3_client()
    client.delete_object(Bucket=settings.storage_bucket, Key=key)


async def _delete_prefix_s3(prefix: str) -> None:
    client = _get_s3_client()
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.storage_bucket, Prefix=prefix):
        objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
        if objects:
            client.delete_objects(
                Bucket=settings.storage_bucket,
                Delete={"Objects": objects},
            )


# ---------------------------------------------------------------------------
# Google Cloud Storage
# ---------------------------------------------------------------------------

async def _upload_gcs(key: str, content: bytes) -> str:
    from google.cloud import storage
    client = storage.Client()
    bucket = client.bucket(settings.storage_bucket)
    blob = bucket.blob(key)
    blob.upload_from_string(content)
    logger.info(f"Stored in GCS: gs://{settings.storage_bucket}/{key}")
    return key


async def _download_gcs(key: str) -> bytes:
    from google.cloud import storage
    client = storage.Client()
    bucket = client.bucket(settings.storage_bucket)
    blob = bucket.blob(key)
    return blob.download_as_bytes()


async def _delete_gcs(key: str) -> None:
    from google.cloud import storage
    client = storage.Client()
    bucket = client.bucket(settings.storage_bucket)
    blob = bucket.blob(key)
    blob.delete()


async def _delete_prefix_gcs(prefix: str) -> None:
    from google.cloud import storage
    client = storage.Client()
    bucket = client.bucket(settings.storage_bucket)
    blobs = bucket.list_blobs(prefix=prefix)
    for blob in blobs:
        blob.delete()


# ---------------------------------------------------------------------------
# Azure Blob Storage
# ---------------------------------------------------------------------------

def _get_azure_container_client():
    from azure.storage.blob import ContainerClient
    return ContainerClient.from_connection_string(
        settings.azure_storage_connection_string,
        container_name=settings.storage_bucket,
    )


async def _upload_azure(key: str, content: bytes) -> str:
    container = _get_azure_container_client()
    container.upload_blob(name=key, data=content, overwrite=True)
    logger.info(f"Stored in Azure Blob: {settings.storage_bucket}/{key}")
    return key


async def _download_azure(key: str) -> bytes:
    container = _get_azure_container_client()
    blob = container.download_blob(key)
    return blob.readall()


async def _delete_azure(key: str) -> None:
    container = _get_azure_container_client()
    container.delete_blob(key)


async def _delete_prefix_azure(prefix: str) -> None:
    container = _get_azure_container_client()
    blobs = container.list_blobs(name_starts_with=prefix)
    for blob in blobs:
        container.delete_blob(blob.name)
