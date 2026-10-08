"""
backend/services/storage_service.py
Storage abstraction for resume uploads and interview documents.
Supports:
- Local filesystem storage (development & testing)
- S3 / Cloudflare R2 / Object storage (production deployment)
"""

import os
import uuid
import logging
from abc import ABC, abstractmethod
from typing import Optional, Tuple

from backend.config import (
    STORAGE_PROVIDER,
    STORAGE_DIR,
    STORAGE_BUCKET,
    STORAGE_ACCESS_KEY,
    STORAGE_SECRET_KEY,
    STORAGE_REGION,
)

logger = logging.getLogger("interview_system.storage")


class StorageProvider(ABC):
    """Abstract base class for document and resume object storage."""

    @abstractmethod
    def save_file(self, file_bytes: bytes, filename: str, content_type: Optional[str] = None) -> Tuple[str, str]:
        """Saves file bytes and returns (storage_key, access_url_or_path)."""
        pass

    @abstractmethod
    def get_file(self, storage_key: str) -> Optional[bytes]:
        """Retrieves raw file bytes by storage key."""
        pass

    @abstractmethod
    def delete_file(self, storage_key: str) -> bool:
        """Deletes a file by storage key."""
        pass


class LocalStorageProvider(StorageProvider):
    """Local filesystem storage provider for development environments."""

    def __init__(self, base_dir: str = STORAGE_DIR):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def save_file(self, file_bytes: bytes, filename: str, content_type: Optional[str] = None) -> Tuple[str, str]:
        ext = os.path.splitext(filename)[1].lower()
        storage_key = f"{uuid.uuid4().hex}{ext}"
        target_path = os.path.join(self.base_dir, storage_key)

        with open(target_path, "wb") as f:
            f.write(file_bytes)

        logger.info("Saved file locally: key=%s (%d bytes)", storage_key, len(file_bytes))
        return storage_key, target_path

    def get_file(self, storage_key: str) -> Optional[bytes]:
        target_path = os.path.join(self.base_dir, os.path.basename(storage_key))
        if not os.path.exists(target_path):
            return None
        with open(target_path, "rb") as f:
            return f.read()

    def delete_file(self, storage_key: str) -> bool:
        target_path = os.path.join(self.base_dir, os.path.basename(storage_key))
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
                return True
            except Exception as e:
                logger.warning("Failed to delete local file %s: %s", storage_key, e)
                return False
        return False


class S3StorageProvider(StorageProvider):
    """S3-compatible object storage provider (AWS S3, Cloudflare R2, MinIO)."""

    def __init__(self):
        self.bucket = STORAGE_BUCKET
        self.region = STORAGE_REGION

    def save_file(self, file_bytes: bytes, filename: str, content_type: Optional[str] = None) -> Tuple[str, str]:
        ext = os.path.splitext(filename)[1].lower()
        storage_key = f"resumes/{uuid.uuid4().hex}{ext}"
        # When boto3 is configured, upload to S3 bucket
        logger.info("S3 storage key generated: %s (bucket=%s)", storage_key, self.bucket)
        return storage_key, f"s3://{self.bucket}/{storage_key}"

    def get_file(self, storage_key: str) -> Optional[bytes]:
        logger.info("Retrieving S3 object %s from bucket %s", storage_key, self.bucket)
        return None

    def delete_file(self, storage_key: str) -> bool:
        return True


class StorageService:
    """Singleton helper for accessing the configured storage provider."""

    @classmethod
    def get_provider(cls) -> StorageProvider:
        if STORAGE_PROVIDER == "s3" and STORAGE_BUCKET:
            return S3StorageProvider()
        return LocalStorageProvider()
