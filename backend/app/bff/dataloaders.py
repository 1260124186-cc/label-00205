from typing import Dict, List, Any, Callable
from collections import defaultdict
from loguru import logger


class DataLoader:
    def __init__(self, batch_fn: Callable[[List[str]], Dict[str, Any]]):
        self._batch_fn = batch_fn
        self._cache: Dict[str, Any] = {}
        self._queue: List[str] = []
        self._resolved: Dict[str, Any] = {}

    def clear(self) -> None:
        self._cache.clear()
        self._queue.clear()
        self._resolved.clear()

    def prime(self, key: str, value: Any) -> "DataLoader":
        if key not in self._cache:
            self._cache[key] = value
        return self

    async def load(self, key: str) -> Any:
        if key in self._cache:
            return self._cache[key]
        if key not in self._resolved:
            self._queue.append(key)
            result = await self._dispatch()
            self._resolved.update(result)
            self._cache.update(result)
        return self._resolved.get(key)

    async def load_many(self, keys: List[str]) -> List[Any]:
        results = []
        for key in keys:
            results.append(await self.load(key))
        return results

    async def _dispatch(self) -> Dict[str, Any]:
        if not self._queue:
            return {}
        keys = list(dict.fromkeys(self._queue))
        self._queue.clear()
        try:
            result = self._batch_fn(keys)
            if not isinstance(result, dict):
                return {}
            return result
        except Exception as e:
            logger.error(f"DataLoader batch load failed: {e}")
            return {k: None for k in keys}


class DataLoaderRegistry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaders: Dict[str, DataLoader] = {}
        return cls._instance

    def register(self, name: str, loader: DataLoader) -> None:
        self._loaders[name] = loader

    def get(self, name: str) -> DataLoader:
        return self._loaders.get(name)

    def clear_all(self) -> None:
        for loader in self._loaders.values():
            loader.clear()


def _batch_prediction(bolt_ids: List[str]) -> Dict[str, Any]:
    from app.utils.database import get_db, AbnormalPrediction
    from sqlalchemy import desc

    result = {}
    try:
        with get_db() as db:
            if db is None:
                return {bid: None for bid in bolt_ids}
            rows = (
                db.query(AbnormalPrediction)
                .filter(AbnormalPrediction.bolt_id.in_([str(b) for b in bolt_ids]))
                .order_by(desc(AbnormalPrediction.create_time))
                .all()
            )
            grouped: Dict[str, list] = defaultdict(list)
            for row in rows:
                grouped[str(row.bolt_id)].append(row)
            for bid in bolt_ids:
                recs = grouped.get(str(bid), [])
                result[bid] = recs[0] if recs else None
    except Exception as e:
        logger.warning(f"DataLoader: prediction batch load failed: {e}")
        result = {bid: None for bid in bolt_ids}
    return result


def _batch_health(bolt_ids: List[str]) -> Dict[str, Any]:
    from app.utils.database import get_db, BoltHealthHistory
    from sqlalchemy import desc

    result = {}
    try:
        with get_db() as db:
            if db is None:
                return {bid: None for bid in bolt_ids}
            rows = (
                db.query(BoltHealthHistory)
                .filter(BoltHealthHistory.bolt_id.in_([str(b) for b in bolt_ids]))
                .order_by(desc(BoltHealthHistory.create_time))
                .all()
            )
            grouped: Dict[str, list] = defaultdict(list)
            for row in rows:
                grouped[row.bolt_id].append(row)
            for bid in bolt_ids:
                recs = grouped.get(str(bid), [])
                if recs:
                    latest = recs[0]
                    result[bid] = {
                        "bolt_id": bid,
                        "hi_score": latest.hi_score,
                        "hi_level": latest.hi_level,
                        "trend": getattr(latest, "trend", None),
                        "trend_rate": getattr(latest, "trend_rate", None),
                        "create_time": latest.create_time,
                    }
                else:
                    result[bid] = None
    except Exception as e:
        logger.warning(f"DataLoader: health batch load failed: {e}")
        result = {bid: None for bid in bolt_ids}
    return result


def _batch_rul(bolt_ids: List[str]) -> Dict[str, Any]:
    from app.utils.database import get_db, RULPrediction
    from sqlalchemy import desc

    result = {}
    try:
        with get_db() as db:
            if db is None:
                return {bid: None for bid in bolt_ids}
            rows = (
                db.query(RULPrediction)
                .filter(
                    RULPrediction.node_id.in_([str(b) for b in bolt_ids]),
                    RULPrediction.node_type == "bolt",
                )
                .order_by(desc(RULPrediction.create_time))
                .all()
            )
            grouped: Dict[str, list] = defaultdict(list)
            for row in rows:
                grouped[row.node_id].append(row)
            for bid in bolt_ids:
                recs = grouped.get(str(bid), [])
                if recs:
                    latest = recs[0]
                    result[bid] = latest
                else:
                    result[bid] = None
    except Exception as e:
        logger.warning(f"DataLoader: RUL batch load failed: {e}")
        result = {bid: None for bid in bolt_ids}
    return result


def _batch_anomalies(bolt_ids: List[str]) -> Dict[str, Any]:
    from app.utils.database import get_db, AnomalyData
    from sqlalchemy import desc

    result = {}
    try:
        with get_db() as db:
            if db is None:
                return {bid: [] for bid in bolt_ids}
            rows = (
                db.query(AnomalyData)
                .filter(AnomalyData.sensor_id.in_([str(b) for b in bolt_ids]))
                .order_by(desc(AnomalyData.original_time))
                .limit(len(bolt_ids) * 10)
                .all()
            )
            grouped: Dict[str, list] = defaultdict(list)
            for row in rows:
                grouped[row.sensor_id].append(row)
            for bid in bolt_ids:
                result[bid] = grouped.get(str(bid), [])
    except Exception as e:
        logger.warning(f"DataLoader: anomaly batch load failed: {e}")
        result = {bid: [] for bid in bolt_ids}
    return result


def _batch_work_orders(bolt_ids: List[str]) -> Dict[str, Any]:
    from app.utils.database import get_db, WorkOrder
    from sqlalchemy import desc

    result = {}
    try:
        with get_db() as db:
            if db is None:
                return {bid: [] for bid in bolt_ids}
            rows = (
                db.query(WorkOrder)
                .filter(WorkOrder.node_id.in_([str(b) for b in bolt_ids]))
                .order_by(desc(WorkOrder.create_time))
                .limit(len(bolt_ids) * 10)
                .all()
            )
            grouped: Dict[str, list] = defaultdict(list)
            for row in rows:
                grouped[row.node_id].append(row)
            for bid in bolt_ids:
                result[bid] = grouped.get(str(bid), [])
    except Exception as e:
        logger.warning(f"DataLoader: work order batch load failed: {e}")
        result = {bid: [] for bid in bolt_ids}
    return result


def create_dataloader_registry() -> DataLoaderRegistry:
    registry = DataLoaderRegistry()
    registry.register("prediction", DataLoader(_batch_prediction))
    registry.register("health", DataLoader(_batch_health))
    registry.register("rul", DataLoader(_batch_rul))
    registry.register("anomalies", DataLoader(_batch_anomalies))
    registry.register("work_orders", DataLoader(_batch_work_orders))
    return registry
