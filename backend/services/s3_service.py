from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from config.settings import get_settings

logger = logging.getLogger(__name__)


class S3Service:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None

    def _get_client(self):
        if self._client is None and self.settings.aws_enabled:
            kwargs: Dict[str, Any] = {
                "region_name": self.settings.aws_region,
                "config": Config(connect_timeout=1, read_timeout=1, retries={"max_attempts": 1}),
            }
            if self.settings.aws_access_key_id and self.settings.aws_secret_access_key:
                kwargs["aws_access_key_id"] = self.settings.aws_access_key_id
                kwargs["aws_secret_access_key"] = self.settings.aws_secret_access_key
            try:
                self._client = boto3.client("s3", **kwargs)
            except Exception:
                self._client = None
        return self._client


    def is_connected(self) -> Dict[str, Any]:
        if not self.settings.aws_enabled:
            return {"enabled": False, "ok": True}
        client = self._get_client()
        if not client:
            return {"enabled": True, "ok": False, "error": "AWS client not initialized"}
        try:
            bucket = self.settings.s3_bucket or "veritas-artifacts-565393035838"
            client.head_bucket(Bucket=bucket)
            return {"enabled": True, "ok": True, "bucket": bucket, "region": self.settings.aws_region}
        except ClientError as exc:
            return {"enabled": True, "ok": False, "error": str(exc)}
        except Exception as exc:
            return {"enabled": True, "ok": False, "error": str(exc)}

    def upload_file(self, local_path: str, s3_key: str) -> Optional[str]:
        if not self.settings.aws_enabled:
            return None
        client = self._get_client()
        if not client:
            return None
        bucket = self.settings.s3_bucket or "veritas-artifacts-565393035838"
        try:
            client.upload_file(local_path, bucket, s3_key)
            logger.info("Uploaded %s to s3://%s/%s", local_path, bucket, s3_key)
            return f"s3://{bucket}/{s3_key}"
        except Exception as exc:
            logger.warning("Failed to upload to S3: %s", exc)
            return None

    def delete_file(self, s3_key: str) -> bool:
        if not self.settings.aws_enabled:
            return False
        client = self._get_client()
        if not client:
            return False
        bucket = self.settings.s3_bucket or "veritas-artifacts-565393035838"
        try:
            client.delete_object(Bucket=bucket, Key=s3_key)
            return True
        except Exception as exc:
            logger.warning("Failed to delete from S3: %s", exc)
            return False


_s3_service: Optional[S3Service] = None


def get_s3_service() -> S3Service:
    global _s3_service
    if _s3_service is None:
        _s3_service = S3Service()
    return _s3_service
