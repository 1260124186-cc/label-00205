import hashlib
import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import numpy as np
from loguru import logger


@dataclass
class CacheEntry:
    id: str
    timestamp: str
    device_id: str
    model_type: str
    node_id: str
    input_hash: str
    prediction: Dict[str, Any]
    synced: bool = False
    sync_attempts: int = 0
    last_sync_attempt: Optional[str] = None


@dataclass
class CacheConfig:
    cache_dir: str = "./edge_cache"
    max_cache_size_mb: float = 500.0
    max_entries: int = 10000
    batch_upload_size: int = 100
    upload_url: str = ""
    retry_interval_seconds: int = 300
    max_sync_attempts: int = 5
    cleanup_synced_after_hours: int = 24
    device_id: str = ""


@dataclass
class CacheStats:
    total_entries: int
    unsynced_entries: int
    synced_entries: int
    cache_size_bytes: int
    oldest_unsynced: Optional[str]
    newest_entry: Optional[str]


class EdgeCache:

    def __init__(self, config: CacheConfig):
        self._config = config
        self._entries: List[CacheEntry] = []
        self._lock = threading.Lock()
        self._sync_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._cache_dir = Path(config.cache_dir)
        self._cache_file = self._cache_dir / "cache_entries.json"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._entries = self._load_entries()

    def store(
        self,
        device_id: str,
        model_type: str,
        node_id: str,
        input_data: np.ndarray,
        prediction_result: Dict[str, Any],
    ) -> CacheEntry:
        input_hash = hashlib.sha256(input_data.tobytes()).hexdigest()
        entry = CacheEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            device_id=device_id,
            model_type=model_type,
            node_id=node_id,
            input_hash=input_hash,
            prediction=prediction_result,
        )
        with self._lock:
            self._entries.append(entry)
            self._evict_if_needed()
            self._cleanup_old_synced()
            self._persist_entries(self._entries)
        logger.info(f"Cache entry stored: id={entry.id}, model={model_type}, node={node_id}")
        return entry

    def get_unsynced(self, limit: Optional[int] = None) -> List[CacheEntry]:
        with self._lock:
            unsynced = [e for e in self._entries if not e.synced]
            if limit is not None:
                unsynced = unsynced[:limit]
            return unsynced

    def mark_synced(self, entry_ids: List[str]) -> None:
        id_set = set(entry_ids)
        with self._lock:
            for entry in self._entries:
                if entry.id in id_set:
                    entry.synced = True
            self._persist_entries(self._entries)
        logger.info(f"Marked {len(id_set)} entries as synced")

    def batch_upload(self) -> int:
        unsynced = self.get_unsynced(limit=self._config.batch_upload_size)
        if not unsynced:
            return 0
        total_uploaded = 0
        for i in range(0, len(unsynced), self._config.batch_upload_size):
            batch = unsynced[i : i + self._config.batch_upload_size]
            success = self._try_upload(batch)
            if success:
                self.mark_synced([e.id for e in batch])
                total_uploaded += len(batch)
            else:
                with self._lock:
                    for entry in batch:
                        entry.sync_attempts += 1
                        entry.last_sync_attempt = datetime.now(timezone.utc).isoformat()
                    self._persist_entries(self._entries)
                break
        return total_uploaded

    def _try_upload(self, entries: List[CacheEntry]) -> bool:
        if not self._config.upload_url:
            logger.warning("Upload URL not configured")
            return False
        payload = {
            "device_id": self._config.device_id,
            "predictions": [asdict(e) for e in entries],
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self._config.upload_url}/edge/predictions/upload",
                    json=payload,
                )
                if response.status_code == 200:
                    logger.info(f"Uploaded {len(entries)} entries successfully")
                    return True
                else:
                    logger.warning(f"Upload failed: status={response.status_code}")
                    return False
        except httpx.HTTPError as e:
            logger.error(f"Upload error: {e}")
            return False

    def _persist_entries(self, entries: List[CacheEntry]) -> None:
        data = [asdict(e) for e in entries]
        tmp_file = self._cache_file.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(data, ensure_ascii=False))
        tmp_file.replace(self._cache_file)

    def _load_entries(self) -> List[CacheEntry]:
        if not self._cache_file.exists():
            return []
        try:
            raw = json.loads(self._cache_file.read_text())
            return [CacheEntry(**item) for item in raw]
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to load cache entries: {e}")
            return []

    def _evict_if_needed(self) -> None:
        if len(self._entries) <= self._config.max_entries:
            cache_size = sum(
                len(json.dumps(asdict(e), ensure_ascii=False).encode()) for e in self._entries
            )
            if cache_size <= self._config.max_cache_size_mb * 1024 * 1024:
                return
        synced = [e for e in self._entries if e.synced]
        synced.sort(key=lambda e: e.timestamp)
        while synced and (
            len(self._entries) > self._config.max_entries
            or sum(
                len(json.dumps(asdict(e), ensure_ascii=False).encode())
                for e in self._entries
            )
            > self._config.max_cache_size_mb * 1024 * 1024
        ):
            oldest = synced.pop(0)
            self._entries.remove(oldest)
            logger.debug(f"Evicted synced entry: {oldest.id}")

    def _cleanup_old_synced(self) -> None:
        now = datetime.now(timezone.utc)
        threshold_hours = self._config.cleanup_synced_after_hours
        to_remove = []
        for entry in self._entries:
            if not entry.synced:
                continue
            try:
                entry_time = datetime.fromisoformat(entry.timestamp)
                if entry_time.tzinfo is None:
                    entry_time = entry_time.replace(tzinfo=timezone.utc)
                age_hours = (now - entry_time).total_seconds() / 3600
                if age_hours > threshold_hours:
                    to_remove.append(entry)
            except (ValueError, TypeError):
                continue
        for entry in to_remove:
            self._entries.remove(entry)
        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} old synced entries")

    def get_stats(self) -> CacheStats:
        with self._lock:
            total = len(self._entries)
            unsynced = [e for e in self._entries if not e.synced]
            synced = [e for e in self._entries if e.synced]
            cache_size = sum(
                len(json.dumps(asdict(e), ensure_ascii=False).encode()) for e in self._entries
            )
            oldest_unsynced = None
            if unsynced:
                oldest_unsynced = min(unsynced, key=lambda e: e.timestamp).timestamp
            newest_entry = None
            if self._entries:
                newest_entry = max(self._entries, key=lambda e: e.timestamp).timestamp
            return CacheStats(
                total_entries=total,
                unsynced_entries=len(unsynced),
                synced_entries=len(synced),
                cache_size_bytes=cache_size,
                oldest_unsynced=oldest_unsynced,
                newest_entry=newest_entry,
            )

    def start_sync_loop(self) -> None:
        if self._sync_thread is not None and self._sync_thread.is_alive():
            logger.warning("Sync loop already running")
            return
        self._stop_event.clear()
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()
        logger.info("Sync loop started")

    def stop_sync_loop(self) -> None:
        self._stop_event.set()
        if self._sync_thread is not None:
            self._sync_thread.join(timeout=10.0)
            self._sync_thread = None
        logger.info("Sync loop stopped")

    def _sync_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.batch_upload()
                with self._lock:
                    self._entries = [
                        e
                        for e in self._entries
                        if not e.synced or e.sync_attempts < self._config.max_sync_attempts
                    ]
                    self._persist_entries(self._entries)
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
            self._stop_event.wait(self._config.retry_interval_seconds)
