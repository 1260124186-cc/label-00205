from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import time

import numpy as np
from loguru import logger

from edge_sdk.local_inference import EdgeInferenceEngine, InferenceConfig, InferenceResult, STATUS_LABELS
from edge_sdk.model_sync import ModelSyncService, SyncConfig
from edge_sdk.edge_cache import EdgeCache, CacheConfig, CacheEntry


@dataclass
class EdgeClientConfig:
    device_id: str = ""
    server_url: str = "http://localhost:8000"
    model_type: str = "bolt"
    node_id: str = ""
    model_format: str = "onnx"
    local_model_dir: str = "./edge_models"
    cache_dir: str = "./edge_cache"
    sync_interval_seconds: int = 3600
    num_inference_threads: int = 4
    warmup_runs: int = 3
    verify_integrity: bool = True
    batch_upload_size: int = 100
    max_cache_entries: int = 10000


@dataclass
class EdgeClientStatus:
    is_initialized: bool
    model_loaded: bool
    model_version: str
    is_syncing: bool
    last_sync_time: Optional[str]
    cache_stats: dict
    device_id: str
    uptime_seconds: float


class EdgeClient:
    def __init__(self, config: EdgeClientConfig):
        self._config = config
        self._inference_engine: Optional[EdgeInferenceEngine] = None
        self._sync_service: Optional[ModelSyncService] = None
        self._cache: Optional[EdgeCache] = None
        self._initialized = False
        self._start_time: Optional[float] = None
        self._current_model_version = ""

    def initialize(self) -> bool:
        if self._initialized:
            logger.warning("EdgeClient already initialized")
            return True

        self._start_time = time.time()

        if not self._init_inference_engine():
            logger.error("Failed to initialize inference engine")
            return False

        self._init_sync_service()
        self._init_cache()

        self._initialized = True
        logger.info("EdgeClient initialized successfully")
        return True

    def shutdown(self):
        if not self._initialized:
            return

        if self._sync_service is not None:
            self._sync_service.stop()
            self._sync_service = None

        if self._cache is not None:
            self._cache.stop_sync_loop()
            self._cache = None

        self._inference_engine = None
        self._initialized = False
        logger.info("EdgeClient shut down")

    def predict(self, data: np.ndarray) -> dict:
        if not self._initialized or self._inference_engine is None:
            logger.error("EdgeClient not initialized")
            return {
                "predicted_class": -1,
                "confidence": 0.0,
                "status": "error",
                "inference_time_ms": 0.0,
                "model_version": "",
                "cached": False,
            }

        result: InferenceResult = self._inference_engine.predict(data)

        prediction = {
            "predicted_class": result.predicted_class,
            "confidence": result.confidence,
            "status": STATUS_LABELS.get(result.status, "unknown"),
            "inference_time_ms": result.inference_time_ms,
            "model_version": self._current_model_version,
            "cached": False,
        }

        self._store_prediction(data, prediction)

        return prediction

    def predict_batch(self, data_list: List[np.ndarray]) -> List[dict]:
        if not self._initialized or self._inference_engine is None:
            logger.error("EdgeClient not initialized")
            return [
                {
                    "predicted_class": -1,
                    "confidence": 0.0,
                    "status": "error",
                    "inference_time_ms": 0.0,
                    "model_version": "",
                    "cached": False,
                }
                for _ in data_list
            ]

        results: List[InferenceResult] = self._inference_engine.predict_batch(data_list)

        predictions = []
        for result in results:
            prediction = {
                "predicted_class": result.predicted_class,
                "confidence": result.confidence,
                "status": STATUS_LABELS.get(result.status, "unknown"),
                "inference_time_ms": result.inference_time_ms,
                "model_version": self._current_model_version,
                "cached": False,
            }
            predictions.append(prediction)

        for data, prediction in zip(data_list, predictions):
            self._store_prediction(data, prediction)

        return predictions

    def get_status(self) -> EdgeClientStatus:
        cache_stats = {
            "total": 0,
            "unsynced": 0,
            "synced": 0,
            "size_bytes": 0,
        }
        is_syncing = False
        last_sync_time = None

        if self._cache is not None:
            cache_stats = self._cache.get_stats()

        if self._sync_service is not None:
            is_syncing = self._sync_service.is_syncing
            last_sync_time = self._sync_service.last_sync_time

        uptime = 0.0
        if self._start_time is not None:
            uptime = time.time() - self._start_time

        return EdgeClientStatus(
            is_initialized=self._initialized,
            model_loaded=self._inference_engine is not None,
            model_version=self._current_model_version,
            is_syncing=is_syncing,
            last_sync_time=last_sync_time,
            cache_stats=cache_stats,
            device_id=self._config.device_id,
            uptime_seconds=uptime,
        )

    def force_sync(self) -> bool:
        if not self._initialized or self._sync_service is None:
            logger.error("EdgeClient not initialized or sync service unavailable")
            return False

        return self._sync_service.force_sync()

    def force_upload(self) -> int:
        if not self._initialized or self._cache is None:
            logger.error("EdgeClient not initialized or cache unavailable")
            return 0

        return self._cache.batch_upload(max_entries=self._config.batch_upload_size)

    def _init_inference_engine(self) -> bool:
        inference_config = InferenceConfig(
            model_path=self._config.local_model_dir,
            model_format=self._config.model_format,
            num_threads=self._config.num_inference_threads,
            warmup_runs=self._config.warmup_runs,
        )

        self._inference_engine = EdgeInferenceEngine(inference_config)

        if not self._inference_engine.load_model():
            logger.error("Failed to load model")
            self._inference_engine = None
            return False

        self._current_model_version = self._inference_engine.model_version
        logger.info(f"Inference engine initialized, model version: {self._current_model_version}")
        return True

    def _init_sync_service(self):
        sync_config = SyncConfig(
            server_url=self._config.server_url,
            model_type=self._config.model_type,
            node_id=self._config.node_id,
            device_id=self._config.device_id,
            local_model_dir=self._config.local_model_dir,
            sync_interval_seconds=self._config.sync_interval_seconds,
            verify_integrity=self._config.verify_integrity,
        )

        self._sync_service = ModelSyncService(sync_config, on_model_updated=self._on_model_updated)
        self._sync_service.start()
        logger.info("Sync service started")

    def _init_cache(self):
        cache_config = CacheConfig(
            cache_dir=self._config.cache_dir,
            max_entries=self._config.max_cache_entries,
            batch_upload_size=self._config.batch_upload_size,
            server_url=self._config.server_url,
            device_id=self._config.device_id,
        )

        self._cache = EdgeCache(cache_config)
        self._cache.start_sync_loop(interval_seconds=self._config.sync_interval_seconds)
        logger.info("Cache initialized and sync loop started")

    def _on_model_updated(self, version: str):
        logger.info(f"Model updated to version {version}, reloading inference engine")
        self._inference_engine = None

        inference_config = InferenceConfig(
            model_path=self._config.local_model_dir,
            model_format=self._config.model_format,
            num_threads=self._config.num_inference_threads,
            warmup_runs=self._config.warmup_runs,
        )

        self._inference_engine = EdgeInferenceEngine(inference_config)

        if self._inference_engine.load_model():
            self._current_model_version = version
            logger.info(f"Inference engine reloaded with model version {version}")
        else:
            logger.error(f"Failed to reload inference engine for model version {version}")
            self._inference_engine = None

    def _store_prediction(self, input_data: np.ndarray, result: dict):
        if self._cache is None:
            return

        entry = CacheEntry(
            device_id=self._config.device_id,
            model_version=self._current_model_version,
            input_data=input_data,
            result=result,
            timestamp=datetime.utcnow().isoformat(),
        )

        self._cache.add(entry)
