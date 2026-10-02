"""Thin S3-compatible object storage wrapper (works against MinIO locally
or real AWS S3 in production — same code, different endpoint/credentials).

Every function degrades gracefully instead of raising: if storage isn't
configured (blank credentials) or the service is unreachable, callers get
None back and log a warning, never a hard failure. A missing export is a
UX gap, not a reason to fail a completed research job — exports are also
still available client-side (Markdown/PDF) regardless of this.
"""

import logging

import boto3
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(settings.storage_endpoint_url and settings.storage_access_key and settings.storage_secret_key)


def _client() -> BaseClient:
    return boto3.client(
        "s3",
        endpoint_url=settings.storage_endpoint_url,
        aws_access_key_id=settings.storage_access_key,
        aws_secret_access_key=settings.storage_secret_key,
    )


def _ensure_bucket(client: BaseClient) -> None:
    try:
        client.head_bucket(Bucket=settings.storage_bucket_name)
    except ClientError:
        client.create_bucket(Bucket=settings.storage_bucket_name)


def upload_report(job_id: str, markdown_content: str) -> str | None:
    """Upload a job's final report as a .md object. Returns the object key
    (not a URL — use get_download_url for that), or None if storage isn't
    configured/reachable."""
    if not is_configured():
        return None

    key = f"reports/{job_id}.md"
    try:
        client = _client()
        _ensure_bucket(client)
        client.put_object(
            Bucket=settings.storage_bucket_name,
            Key=key,
            Body=markdown_content.encode("utf-8"),
            ContentType="text/markdown",
        )
    except (BotoCoreError, ClientError) as exc:
        logger.warning("Failed to upload report for job %s to object storage: %s", job_id, exc)
        return None

    return key


def get_download_url(object_key: str, expires_in_seconds: int = 3600) -> str | None:
    if not is_configured():
        return None

    try:
        client = _client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.storage_bucket_name, "Key": object_key},
            ExpiresIn=expires_in_seconds,
        )
    except (BotoCoreError, ClientError) as exc:
        logger.warning("Failed to generate a download URL for %s: %s", object_key, exc)
        return None
