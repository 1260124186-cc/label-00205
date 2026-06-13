import threading
import time
import json
import shutil
import zipfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, List
from datetime import datetime

import httpx
from loguru import logger

from edge_sdk.model_package import IntegrityVerifier


@dataclass
class SyncConfig:
    server_url: str = "http://localhost:8000"
    sync_interval_seconds: int = 3600
    model_type: str = "bolt"
    node_id: str = ""
    local_model_dir: str = "./edge_models"
    verify_integrity: bool = True
    max_retries: int = 3
    retry_delay_seconds: int = 30
    timeout_seconds: int = 60
    edge_device_id: str = ""


@dataclass
class ModelVersionInfo:
    version: str
    model_type: str
    node_id: str
    download_url: str
    file_hash: str
    file_size: int
    created_at: str
    metrics: Dict[str, float]


class ModelSyncService:
    def __init__(self, config: SyncConfig):
        self._config = config
        self._stop_event = threading.Event()
        self._sync_thread: Optional[threading.Thread] = None
        self._is_syncing = False
        self._last_sync_time: Optional[datetime] = None
        self._last_sync_status: str = "never"
        self._callbacks: List[Callable] = []
        self._local_model_dir = Path(config.local_model_dir)
        self._client = httpx.Client(timeout=config.timeout_seconds)

    @property
    def is_syncing(self) -> bool:
        return self._is_syncing

    @property
    def last_sync_time(self) -> Optional[datetime]:
        return self._last_sync_time

    @property
    def last_sync_status(self) -> str:
        return self._last_sync_status

    def start(self):
        if self._sync_thread is not None and self._sync_thread.is_alive():
            logger.warning("Sync thread already running")
            return
        self._stop_event.clear()
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()
        logger.info("Model sync service started")

    def stop(self):
        self._stop_event.set()
        if self._sync_thread is not None and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=10)
        self._sync_thread = None
        logger.info("Model sync service stopped")

    def sync_once(self) -> bool:
        self._is_syncing = True
        try:
            server_version = self.check_server_version()
            if server_version is None:
                self._last_sync_status = "server_unreachable"
                logger.error("Failed to check server version")
                return False

            local_version = self.get_local_version()
            if local_version == server_version.version:
                self._last_sync_status = "up_to_date"
                self._last_sync_time = datetime.now()
                logger.info(f"Model is up to date: {local_version}")
                return True

            logger.info(f"New version available: {server_version.version} (local: {local_version})")
            package_path = self.download_model(server_version)
            if package_path is None:
                self._last_sync_status = "download_failed"
                logger.error("Failed to download model")
                return False

            if not self.apply_model(package_path):
                self._last_sync_status = "apply_failed"
                logger.error("Failed to apply model")
                return False

            self._last_sync_status = "success"
            self._last_sync_time = datetime.now()
            self._notify_model_updated(server_version.version)
            logger.info(f"Model updated to version {server_version.version}")
            return True
        except Exception as e:
            self._last_sync_status = "error"
            logger.exception(f"Sync failed: {e}")
            return False
        finally:
            self._is_syncing = False

    def check_server_version(self) -> Optional[ModelVersionInfo]:
        try:
            params = {"model_type": self._config.model_type, "node_id": self._config.node_id}
            if self._config.edge_device_id:
                params["edge_device_id"] = self._config.edge_device_id
            response = self._client.get(
                f"{self._config.server_url}/edge/model/latest",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            return ModelVersionInfo(
                version=data["version"],
                model_type=data["model_type"],
                node_id=data["node_id"],
                download_url=data["download_url"],
                file_hash=data["file_hash"],
                file_size=data["file_size"],
                created_at=data["created_at"],
                metrics=data.get("metrics", {}),
            )
        except Exception as e:
            logger.error(f"Failed to check server version: {e}")
            return None

    def get_local_version(self) -> Optional[str]:
        metadata_path = self._local_model_dir / "metadata.json"
        if not metadata_path.exists():
            return None
        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            return metadata.get("version")
        except Exception as e:
            logger.error(f"Failed to read local version: {e}")
            return None

    def download_model(self, version_info: ModelVersionInfo) -> Optional[str]:
        self._local_model_dir.mkdir(parents=True, exist_ok=True)
        filename = f"model_{version_info.version}.zip"
        output_path = self._local_model_dir / filename
        url = f"{self._config.server_url}/edge/model/download/{version_info.version}"
        if not self._download_with_retry(url, str(output_path)):
            return None
        if self._config.verify_integrity:
            if not IntegrityVerifier.verify(str(output_path), version_info.file_hash):
                logger.error("Integrity verification failed for downloaded model")
                output_path.unlink(missing_ok=True)
                return None
        return str(output_path)

    def apply_model(self, package_path: str) -> bool:
        package = Path(package_path)
        if not package.exists():
            logger.error(f"Package not found: {package_path}")
            return False
        try:
            temp_dir = self._local_model_dir / "_staging"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(package, "r") as zf:
                zf.extractall(temp_dir)

            model_files_dir = self._local_model_dir / "active"
            if model_files_dir.exists():
                shutil.rmtree(model_files_dir)

            shutil.move(str(temp_dir), str(model_files_dir))

            package.unlink(missing_ok=True)

            staging = self._local_model_dir / "_staging"
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)

            return True
        except Exception as e:
            logger.error(f"Failed to apply model: {e}")
            return False

    def _sync_loop(self):
        while not self._stop_event.is_set():
            self.sync_once()
            self._stop_event.wait(timeout=self._config.sync_interval_seconds)

    def _download_with_retry(self, url: str, output_path: str) -> bool:
        for attempt in range(1, self._config.max_retries + 1):
            try:
                with self._client.stream("GET", url) as response:
                    response.raise_for_status()
                    with open(output_path, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                logger.info(f"Downloaded {url} to {output_path}")
                return True
            except Exception as e:
                logger.warning(f"Download attempt {attempt}/{self._config.max_retries} failed: {e}")
                if attempt < self._config.max_retries:
                    time.sleep(self._config.retry_delay_seconds)
        return False

    def _notify_model_updated(self, version: str):
        for callback in self._callbacks:
            try:
                callback(version)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def on_model_updated(self, callback: Callable):
        self._callbacks.append(callback)
