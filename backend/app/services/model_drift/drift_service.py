"""
模型漂移检测服务 ModelDriftService

负责每日批处理计算每个模型的各维度漂移分数，
超阈值时写入 sc_model_drift_events 并触发响应策略。
"""

import json
import uuid
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
from loguru import logger
from sqlalchemy.orm import Session

from app.utils.database import (
    get_db,
    BoltData,
    AbnormalPrediction,
    AnomalyData,
    FeatureSnapshot,
    ModelVersionORM,
    ModelDriftConfig,
    ModelDriftBaseline,
    ModelDriftEvent,
)
from app.utils.config import config
from app.core.event_bus import EventBus, event_bus, EventType
from app.services.model_drift.drift_algorithms import (
    DriftDimension,
    DriftResult,
    calculate_psi,
    calculate_ks_test,
    calculate_confidence_drift,
    calculate_false_positive_rate,
    calculate_feature_mean_shift,
    compute_composite_drift_score,
    CompositeDriftResult,
)


class ModelDriftService:
    """
    模型漂移检测服务

    核心职责:
    1. 每日批处理遍历所有启用了漂移检测的模型
    2. 收集基线数据和当前生产数据
    3. 计算5个维度的漂移分数
    4. 写入 sc_model_drift_events 表
    5. 发布 MODEL_DRIFT_DETECTED 事件
    """

    def __init__(self, db: Optional[Session] = None, event_bus_instance: Optional[EventBus] = None):
        self._db = db
        self._event_bus = event_bus_instance or event_bus

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = next(get_db())
        return self._db

    # ============================================================
    # 主入口：每日批处理
    # ============================================================

    def run_daily_drift_detection(
        self,
        detection_date: Optional[date] = None,
        model_types: Optional[List[str]] = None,
        tenant_id: Optional[int] = None,
    ) -> Dict:
        """
        执行每日漂移检测批处理

        Args:
            detection_date: 检测日期，默认为今天
            model_types: 限定检测的模型类型列表，None表示全部
            tenant_id: 限定租户ID，None表示全部租户

        Returns:
            Dict: 批处理执行统计结果
        """
        if detection_date is None:
            detection_date = date.today()

        logger.info(f"[ModelDrift] 开始每日漂移检测, 日期={detection_date}, "
                    f"model_types={model_types}, tenant_id={tenant_id}")

        models = self._get_models_to_check(model_types, tenant_id)
        if not models:
            logger.warning("[ModelDrift] 没有找到需要检测的模型配置")
            return {"status": "skipped", "reason": "no_models_configured", "total": 0}

        stats = {
            "total": 0,
            "processed": 0,
            "drift_detected": 0,
            "no_drift": 0,
            "failed": 0,
            "events_written": 0,
            "details": [],
        }

        for model_info in models:
            stats["total"] += 1
            try:
                result = self._detect_single_model_drift(
                    model_id=model_info["model_id"],
                    model_type=model_info["model_type"],
                    version=model_info.get("version"),
                    drift_config=model_info["config"],
                    detection_date=detection_date,
                    tenant_id=model_info.get("tenant_id"),
                )
                stats["processed"] += 1
                if result.get("drift_detected"):
                    stats["drift_detected"] += 1
                else:
                    stats["no_drift"] += 1
                if result.get("event_written"):
                    stats["events_written"] += 1
                stats["details"].append(result)
            except Exception as e:
                stats["failed"] += 1
                logger.exception(f"[ModelDrift] 模型 {model_info} 漂移检测失败: {e}")
                stats["details"].append({
                    "model_id": model_info["model_id"],
                    "model_type": model_info["model_type"],
                    "status": "failed",
                    "error": str(e),
                })

        logger.info(
            f"[ModelDrift] 每日漂移检测完成: 总计={stats['total']}, "
            f"成功={stats['processed']}, 检测到漂移={stats['drift_detected']}, "
            f"无漂移={stats['no_drift']}, 失败={stats['failed']}, "
            f"写入事件={stats['events_written']}"
        )
        return stats

    # ============================================================
    # 单模型漂移检测
    # ============================================================

    def _detect_single_model_drift(
        self,
        model_id: str,
        model_type: str,
        version: Optional[str],
        drift_config: ModelDriftConfig,
        detection_date: date,
        tenant_id: Optional[int],
    ) -> Dict:
        """对单个模型执行完整的漂移检测流程"""

        if version is None:
            version = self._get_active_model_version(model_type, tenant_id)
        if version is None:
            logger.warning(f"[ModelDrift] 模型 {model_id}/{model_type} 没有活跃版本，跳过")
            return {"model_id": model_id, "model_type": model_type, "status": "skipped", "reason": "no_active_version"}

        consecutive_days = self._get_consecutive_drift_days(model_id, model_type, detection_date)

        data_window_days = drift_config.false_positive_window_days or 7
        current_window_end = datetime.combine(detection_date, datetime.min.time())
        current_window_start = current_window_end - timedelta(days=data_window_days)

        dim_results: Dict[DriftDimension, DriftResult] = {}

        # 1. 数据分布漂移 (PSI + KS)
        try:
            psi_result, ks_result = self._detect_data_distribution_drift(
                model_id, model_type, version,
                current_window_start, current_window_end,
                drift_config, tenant_id,
            )
            dim_results[DriftDimension.DATA_PSI] = psi_result
            dim_results[DriftDimension.DATA_KS] = ks_result
        except Exception as e:
            logger.exception(f"[ModelDrift] 数据分布漂移检测失败: {e}")

        # 2. 置信度分布漂移
        try:
            conf_result = self._detect_confidence_distribution_drift(
                model_id, model_type, version,
                current_window_start, current_window_end,
                drift_config, tenant_id,
            )
            dim_results[DriftDimension.CONFIDENCE] = conf_result
        except Exception as e:
            logger.exception(f"[ModelDrift] 置信度分布漂移检测失败: {e}")

        # 3. 误报率上升
        try:
            fpr_result = self._detect_false_positive_rate(
                model_id, model_type, version,
                current_window_start, current_window_end,
                drift_config, tenant_id,
            )
            dim_results[DriftDimension.FALSE_POSITIVE] = fpr_result
        except Exception as e:
            logger.exception(f"[ModelDrift] 误报率检测失败: {e}")

        # 4. 特征均值偏移
        feature_drift_details: Dict = {}
        try:
            feat_result, feature_drift_details = self._detect_feature_mean_shift(
                model_id, model_type, version,
                current_window_start, current_window_end,
                drift_config, tenant_id,
            )
            dim_results[DriftDimension.FEATURE_SHIFT] = feat_result
        except Exception as e:
            logger.exception(f"[ModelDrift] 特征均值偏移检测失败: {e}")

        # 5. 综合漂移分数
        weights = self._parse_weights(drift_config.weights)
        composite = compute_composite_drift_score(dim_results, weights)

        # 判断是否超阈值
        is_above_threshold = (
            composite.composite_score > (drift_config.composite_score_threshold or 0.6)
            or len(composite.triggered_dims) >= 2
        )

        drift_level = composite.drift_level if is_above_threshold else "none"

        # 写入事件表
        event = self._write_drift_event(
            model_id=model_id,
            model_type=model_type,
            version=version,
            detection_date=detection_date,
            dim_results=dim_results,
            composite=composite,
            feature_drift_details=feature_drift_details,
            is_above_threshold=is_above_threshold,
            drift_level=drift_level,
            consecutive_days=consecutive_days + 1 if is_above_threshold else 0,
            drift_config=drift_config,
            tenant_id=tenant_id,
        )

        # 发布事件
        if is_above_threshold and event:
            self._publish_drift_event(event, composite, drift_config)

        return {
            "model_id": model_id,
            "model_type": model_type,
            "version": version,
            "status": "drift_detected" if is_above_threshold else "no_drift",
            "composite_score": composite.composite_score,
            "drift_level": drift_level,
            "triggered_dims": composite.triggered_dims,
            "consecutive_days": consecutive_days + 1 if is_above_threshold else 0,
            "event_written": event is not None,
            "event_id": event.id if event else None,
        }

    # ============================================================
    # 单维度检测实现
    # ============================================================

    def _detect_data_distribution_drift(
        self,
        model_id: str,
        model_type: str,
        version: str,
        current_start: datetime,
        current_end: datetime,
        drift_config: ModelDriftConfig,
        tenant_id: Optional[int],
    ) -> Tuple[DriftResult, DriftResult]:
        """检测数据分布漂移（PSI + KS）"""

        baseline_values = self._get_baseline_data_distribution(model_id, model_type, version, tenant_id)
        current_values = self._get_current_data_distribution(
            model_type, current_start, current_end, tenant_id
        )

        baseline_arr = np.asarray(baseline_values, dtype=np.float64) if baseline_values else np.array([])
        current_arr = np.asarray(current_values, dtype=np.float64) if current_values else np.array([])

        psi_result = calculate_psi(baseline_arr, current_arr)
        psi_result.threshold = drift_config.psi_threshold or 0.2
        psi_result.is_drifted = psi_result.score > (drift_config.psi_threshold or 0.2)

        ks_result = calculate_ks_test(baseline_arr, current_arr)
        ks_result.threshold = drift_config.ks_threshold or 0.05
        ks_p_value = ks_result.details.get("p_value", 1.0)
        ks_result.is_drifted = ks_p_value < (drift_config.ks_threshold or 0.05)

        return psi_result, ks_result

    def _detect_confidence_distribution_drift(
        self,
        model_id: str,
        model_type: str,
        version: str,
        current_start: datetime,
        current_end: datetime,
        drift_config: ModelDriftConfig,
        tenant_id: Optional[int],
    ) -> DriftResult:
        """检测预测置信度分布漂移"""

        baseline_conf = self._get_baseline_confidence_distribution(model_id, model_type, version, tenant_id)
        current_conf = self._get_current_confidence_distribution(
            model_type, current_start, current_end, tenant_id
        )

        baseline_arr = np.asarray(baseline_conf, dtype=np.float64) if baseline_conf else np.array([])
        current_arr = np.asarray(current_conf, dtype=np.float64) if current_conf else np.array([])

        result = calculate_confidence_drift(baseline_arr, current_arr)
        result.threshold = drift_config.confidence_drift_threshold or 0.15
        result.is_drifted = result.score > (drift_config.confidence_drift_threshold or 0.15)

        return result

    def _detect_false_positive_rate(
        self,
        model_id: str,
        model_type: str,
        version: str,
        current_start: datetime,
        current_end: datetime,
        drift_config: ModelDriftConfig,
        tenant_id: Optional[int],
    ) -> DriftResult:
        """检测误报率上升"""

        total_count, fp_count = self._compute_false_positive_stats(
            model_type, current_start, current_end, tenant_id
        )

        baseline_fpr = self._get_baseline_false_positive_rate(model_id, model_type, version, tenant_id)
        if baseline_fpr is None:
            baseline_fpr = drift_config.false_positive_rate_threshold or 0.05

        window_days = drift_config.false_positive_window_days or 7
        result = calculate_false_positive_rate(total_count, fp_count, baseline_fpr, window_days)
        result.threshold = drift_config.false_positive_rate_threshold or 0.10
        result.is_drifted = result.score > (drift_config.false_positive_rate_threshold or 0.10)

        return result

    def _detect_feature_mean_shift(
        self,
        model_id: str,
        model_type: str,
        version: str,
        current_start: datetime,
        current_end: datetime,
        drift_config: ModelDriftConfig,
        tenant_id: Optional[int],
    ) -> Tuple[DriftResult, Dict]:
        """检测特征均值偏移"""

        baseline_stats = self._get_baseline_feature_stats(model_id, model_type, version, tenant_id)
        current_stats = self._compute_current_feature_stats(
            model_type, current_start, current_end, tenant_id
        )

        std_threshold = drift_config.feature_mean_shift_threshold or 2.0
        result, details = calculate_feature_mean_shift(baseline_stats, current_stats, std_threshold)

        return result, details

    # ============================================================
    # 数据获取方法
    # ============================================================

    def _get_models_to_check(
        self,
        model_types: Optional[List[str]],
        tenant_id: Optional[int],
    ) -> List[Dict]:
        """获取所有需要进行漂移检测的模型配置列表"""
        query = self.db.query(ModelDriftConfig).filter(ModelDriftConfig.enabled == True)
        if tenant_id is not None:
            query = query.filter(
                (ModelDriftConfig.tenant_id == tenant_id) | (ModelDriftConfig.tenant_id.is_(None))
            )
        if model_types:
            query = query.filter(ModelDriftConfig.model_type.in_(model_types))

        configs = query.all()

        result = []
        for cfg in configs:
            if cfg.model_id == "default":
                for mt in ["bolt", "flange"]:
                    if model_types and mt not in model_types:
                        continue
                    result.append({
                        "model_id": f"global_{mt}",
                        "model_type": mt,
                        "version": None,
                        "config": cfg,
                        "tenant_id": cfg.tenant_id,
                    })
            else:
                result.append({
                    "model_id": cfg.model_id,
                    "model_type": cfg.model_type,
                    "version": cfg.version,
                    "config": cfg,
                    "tenant_id": cfg.tenant_id,
                })
        return result

    def _get_active_model_version(self, model_type: str, tenant_id: Optional[int]) -> Optional[str]:
        """获取指定模型类型的活跃版本号"""
        query = self.db.query(ModelVersionORM).filter(
            ModelVersionORM.model_type == model_type,
            ModelVersionORM.is_active == True,
        )
        if tenant_id:
            query = query.filter(
                (ModelVersionORM.tenant_id == tenant_id) | (ModelVersionORM.tenant_id.is_(None))
            )
        version = query.order_by(ModelVersionORM.create_time.desc()).first()
        return version.version if version else None

    def _get_consecutive_drift_days(
        self,
        model_id: str,
        model_type: str,
        detection_date: date,
    ) -> int:
        """获取连续漂移天数（截止到昨天）"""
        yesterday = detection_date - timedelta(days=1)
        query = self.db.query(ModelDriftEvent).filter(
            ModelDriftEvent.model_id == model_id,
            ModelDriftEvent.model_type == model_type,
            ModelDriftEvent.detection_date == yesterday,
            ModelDriftEvent.consecutive_days > 0,
        )
        last_event = query.order_by(ModelDriftEvent.detection_date.desc()).first()
        return last_event.consecutive_days if last_event else 0

    def _get_baseline_data_distribution(
        self,
        model_id: str,
        model_type: str,
        version: str,
        tenant_id: Optional[int],
    ) -> List[float]:
        """获取基线数据分布（优先从 drift_baselines 读，否则回退到历史 BoltData）"""
        baseline = self.db.query(ModelDriftBaseline).filter(
            ModelDriftBaseline.model_id == model_id,
            ModelDriftBaseline.model_type == model_type,
            ModelDriftBaseline.version == version,
            ModelDriftBaseline.baseline_type == "data_distribution",
            ModelDriftBaseline.feature_name.is_(None),
        ).first()
        if baseline and baseline.bins:
            bins_info = baseline.bins
            values = []
            for i, cnt in enumerate(bins_info.get("counts", [])):
                values.extend([i] * int(cnt))
            if values:
                return values

        return self._sample_historical_bolt_data(model_type, 30, tenant_id)

    def _get_current_data_distribution(
        self,
        model_type: str,
        start: datetime,
        end: datetime,
        tenant_id: Optional[int],
    ) -> List[float]:
        """获取当前窗口数据分布（使用预紧力 ptf 字段）"""
        query = self.db.query(BoltData).filter(
            BoltData.collect_time >= start,
            BoltData.collect_time < end,
            BoltData.ptf.isnot(None),
        )
        if tenant_id:
            query = query.filter(BoltData.tenant_id == tenant_id)
        rows = query.limit(5000).all()
        return [float(r.ptf) for r in rows if r.ptf is not None]

    def _sample_historical_bolt_data(
        self,
        model_type: str,
        days: int,
        tenant_id: Optional[int],
    ) -> List[float]:
        """从历史数据中采样基线数据"""
        end = datetime.now()
        start = end - timedelta(days=days)
        return self._get_current_data_distribution(model_type, start, end, tenant_id)

    def _get_baseline_confidence_distribution(
        self,
        model_id: str,
        model_type: str,
        version: str,
        tenant_id: Optional[int],
    ) -> List[float]:
        """获取基线置信度分布"""
        baseline = self.db.query(ModelDriftBaseline).filter(
            ModelDriftBaseline.model_id == model_id,
            ModelDriftBaseline.model_type == model_type,
            ModelDriftBaseline.version == version,
            ModelDriftBaseline.baseline_type == "confidence_distribution",
        ).first()
        if baseline and baseline.bins:
            bins_info = baseline.bins
            values = []
            for i, cnt in enumerate(bins_info.get("counts", [])):
                low = bins_info.get("edges", [0, 1])[i] if i < len(bins_info.get("edges", [])) else 0.5
                values.extend([low] * int(cnt))
            if values:
                return values

        return self._sample_historical_confidence(model_type, 30, tenant_id)

    def _get_current_confidence_distribution(
        self,
        model_type: str,
        start: datetime,
        end: datetime,
        tenant_id: Optional[int],
    ) -> List[float]:
        """获取当前窗口的预测置信度分布"""
        query = self.db.query(AbnormalPrediction).filter(
            AbnormalPrediction.prediction_time >= start,
            AbnormalPrediction.prediction_time < end,
            AbnormalPrediction.confidence.isnot(None),
        )
        if tenant_id:
            query = query.filter(AbnormalPrediction.tenant_id == tenant_id)
        rows = query.limit(5000).all()
        return [float(r.confidence) for r in rows if r.confidence is not None]

    def _sample_historical_confidence(
        self,
        model_type: str,
        days: int,
        tenant_id: Optional[int],
    ) -> List[float]:
        """从历史数据中采样基线置信度"""
        end = datetime.now()
        start = end - timedelta(days=days)
        return self._get_current_confidence_distribution(model_type, start, end, tenant_id)

    def _compute_false_positive_stats(
        self,
        model_type: str,
        start: datetime,
        end: datetime,
        tenant_id: Optional[int],
    ) -> Tuple[int, int]:
        """计算当前窗口的总预测数和误报数"""
        query = self.db.query(AnomalyData).filter(
            AnomalyData.detection_time >= start,
            AnomalyData.detection_time < end,
        )
        if tenant_id:
            query = query.filter(AnomalyData.tenant_id == tenant_id)
        all_predictions = query.all()

        total = len(all_predictions)
        fp_count = sum(1 for a in all_predictions if a.is_false_positive)

        return total, fp_count

    def _get_baseline_false_positive_rate(
        self,
        model_id: str,
        model_type: str,
        version: str,
        tenant_id: Optional[int],
    ) -> Optional[float]:
        """从模型版本 metrics 中获取基线误报率"""
        query = self.db.query(ModelVersionORM).filter(
            ModelVersionORM.model_type == model_type,
            ModelVersionORM.version == version,
        )
        if tenant_id:
            query = query.filter(
                (ModelVersionORM.tenant_id == tenant_id) | (ModelVersionORM.tenant_id.is_(None))
            )
        mv = query.first()
        if not mv or not mv.metrics:
            return None
        try:
            metrics = json.loads(mv.metrics) if isinstance(mv.metrics, str) else mv.metrics
            return metrics.get("false_positive_rate") or metrics.get("fpr")
        except (json.JSONDecodeError, TypeError):
            return None

    def _get_baseline_feature_stats(
        self,
        model_id: str,
        model_type: str,
        version: str,
        tenant_id: Optional[int],
    ) -> Dict[str, Dict[str, float]]:
        """获取基线特征统计量（均值、标准差）"""
        baselines = self.db.query(ModelDriftBaseline).filter(
            ModelDriftBaseline.model_id == model_id,
            ModelDriftBaseline.model_type == model_type,
            ModelDriftBaseline.version == version,
            ModelDriftBaseline.baseline_type == "feature_stats",
            ModelDriftBaseline.feature_name.isnot(None),
        ).all()

        result: Dict[str, Dict[str, float]] = {}
        for b in baselines:
            if b.feature_name and b.stats:
                result[b.feature_name] = {
                    "mean": b.stats.get("mean"),
                    "std": b.stats.get("std"),
                }
        if result:
            return result

        return self._compute_historical_feature_stats(model_type, 30, tenant_id)

    def _compute_current_feature_stats(
        self,
        model_type: str,
        start: datetime,
        end: datetime,
        tenant_id: Optional[int],
    ) -> Dict[str, Dict[str, float]]:
        """计算当前窗口特征统计量"""
        query = self.db.query(FeatureSnapshot).filter(
            FeatureSnapshot.compute_time >= start,
            FeatureSnapshot.compute_time < end,
            FeatureSnapshot.node_type == model_type,
        )
        if tenant_id:
            query = query.filter(FeatureSnapshot.tenant_id == tenant_id)
        snapshots = query.limit(2000).all()

        feature_values: Dict[str, List[float]] = {}
        for snap in snapshots:
            if not snap.vector:
                continue
            try:
                vec = json.loads(snap.vector) if isinstance(snap.vector, str) else snap.vector
                if isinstance(vec, list):
                    for i, v in enumerate(vec):
                        key = f"feat_{i}"
                        feature_values.setdefault(key, []).append(float(v))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue

        result: Dict[str, Dict[str, float]] = {}
        for feat, values in feature_values.items():
            if len(values) >= 5:
                arr = np.asarray(values, dtype=np.float64)
                result[feat] = {
                    "mean": float(np.mean(arr)),
                    "std": float(np.std(arr)),
                }
        return result

    def _compute_historical_feature_stats(
        self,
        model_type: str,
        days: int,
        tenant_id: Optional[int],
    ) -> Dict[str, Dict[str, float]]:
        """从历史数据计算基线特征统计量"""
        end = datetime.now()
        start = end - timedelta(days=days)
        return self._compute_current_feature_stats(model_type, start, end, tenant_id)

    # ============================================================
    # 事件写入与发布
    # ============================================================

    def _write_drift_event(
        self,
        model_id: str,
        model_type: str,
        version: str,
        detection_date: date,
        dim_results: Dict[DriftDimension, DriftResult],
        composite: CompositeDriftResult,
        feature_drift_details: Dict,
        is_above_threshold: bool,
        drift_level: str,
        consecutive_days: int,
        drift_config: ModelDriftConfig,
        tenant_id: Optional[int],
    ) -> Optional[ModelDriftEvent]:
        """写入漂移事件到 sc_model_drift_events"""
        try:
            psi = dim_results.get(DriftDimension.DATA_PSI)
            ks = dim_results.get(DriftDimension.DATA_KS)
            conf = dim_results.get(DriftDimension.CONFIDENCE)
            fpr = dim_results.get(DriftDimension.FALSE_POSITIVE)
            feat = dim_results.get(DriftDimension.FEATURE_SHIFT)

            existing = self.db.query(ModelDriftEvent).filter(
                ModelDriftEvent.model_id == model_id,
                ModelDriftEvent.model_type == model_type,
                ModelDriftEvent.detection_date == detection_date,
            ).first()
            if existing:
                logger.debug(f"[ModelDrift] 事件已存在，跳过写入: {model_id}/{model_type}/{detection_date}")
                return existing

            event = ModelDriftEvent(
                event_no=f"DRIFT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
                model_id=model_id,
                model_type=model_type,
                version=version,
                detection_date=detection_date,
                psi_score=psi.score if psi else None,
                ks_p_value=ks.details.get("p_value") if ks else None,
                ks_statistic=ks.score if ks else None,
                confidence_drift_score=conf.score if conf else None,
                confidence_ks_p_value=conf.details.get("p_value") if conf else None,
                false_positive_rate=fpr.score if fpr else None,
                false_positive_count=fpr.details.get("false_positive_count") if fpr else None,
                total_prediction_count=fpr.details.get("total_predictions") if fpr else None,
                feature_drift_json=json.dumps(feature_drift_details, ensure_ascii=False) if feature_drift_details else None,
                feature_mean_shift_count=feat.details.get("shifted_count") if feat else None,
                composite_drift_score=composite.composite_score,
                drift_level=drift_level,
                triggered_dims=json.dumps(composite.triggered_dims, ensure_ascii=False),
                consecutive_days=consecutive_days,
                response_action="none",
                response_status="pending" if is_above_threshold else "skipped",
                notification_sent=False,
                alert_level=self._map_drift_level_to_alert(drift_level),
                tenant_id=tenant_id,
            )
            self.db.add(event)
            self.db.flush()
            logger.info(
                f"[ModelDrift] 写入漂移事件: {event.event_no}, "
                f"model={model_id}/{model_type}, score={composite.composite_score:.3f}, "
                f"level={drift_level}, dims={composite.triggered_dims}"
            )
            return event
        except Exception as e:
            logger.exception(f"[ModelDrift] 写入漂移事件失败: {e}")
            self.db.rollback()
            return None

    def _publish_drift_event(
        self,
        event: ModelDriftEvent,
        composite: CompositeDriftResult,
        drift_config: ModelDriftConfig,
    ) -> None:
        """发布 MODEL_DRIFT_DETECTED 事件到事件总线"""
        try:
            if not hasattr(EventType, "MODEL_DRIFT_DETECTED"):
                logger.debug("[ModelDrift] EventType.MODEL_DRIFT_DETECTED 未定义，跳过事件发布")
                return

            event_data = {
                "event_id": event.id,
                "event_no": event.event_no,
                "model_id": event.model_id,
                "model_type": event.model_type,
                "version": event.version,
                "detection_date": event.detection_date.isoformat(),
                "composite_score": event.composite_drift_score,
                "drift_level": event.drift_level,
                "triggered_dims": composite.triggered_dims,
                "consecutive_days": event.consecutive_days,
                "response_strategy": drift_config.response_strategy,
                "alert_level": event.alert_level,
                "tenant_id": event.tenant_id,
            }
            self._event_bus.publish(EventType.MODEL_DRIFT_DETECTED, event_data, asynchronous=False)
            logger.debug(f"[ModelDrift] 发布漂移事件: {event.event_no}")
        except Exception as e:
            logger.warning(f"[ModelDrift] 发布漂移事件失败: {e}")

    # ============================================================
    # 工具方法
    # ============================================================

    @staticmethod
    def _parse_weights(weights_json: Optional[str]) -> Optional[Dict[DriftDimension, float]]:
        """解析权重配置 JSON"""
        if not weights_json:
            return None
        try:
            raw = json.loads(weights_json) if isinstance(weights_json, str) else weights_json
            result = {}
            for k, v in raw.items():
                try:
                    dim = DriftDimension(k)
                    result[dim] = float(v)
                except ValueError:
                    continue
            return result or None
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

    @staticmethod
    def _map_drift_level_to_alert(drift_level: str) -> int:
        """漂移等级映射到告警级别"""
        mapping = {
            "none": 1,
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4,
        }
        return mapping.get(drift_level, 2)

    # ============================================================
    # 查询接口
    # ============================================================

    def query_drift_events(
        self,
        model_id: Optional[str] = None,
        model_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        drift_level: Optional[str] = None,
        response_action: Optional[str] = None,
        tenant_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[ModelDriftEvent], int]:
        """查询漂移事件列表"""
        query = self.db.query(ModelDriftEvent)
        if model_id:
            query = query.filter(ModelDriftEvent.model_id == model_id)
        if model_type:
            query = query.filter(ModelDriftEvent.model_type == model_type)
        if start_date:
            query = query.filter(ModelDriftEvent.detection_date >= start_date)
        if end_date:
            query = query.filter(ModelDriftEvent.detection_date <= end_date)
        if drift_level:
            query = query.filter(ModelDriftEvent.drift_level == drift_level)
        if response_action:
            query = query.filter(ModelDriftEvent.response_action == response_action)
        if tenant_id:
            query = query.filter(
                (ModelDriftEvent.tenant_id == tenant_id) | (ModelDriftEvent.tenant_id.is_(None))
            )

        total = query.count()
        rows = query.order_by(ModelDriftEvent.detection_date.desc(), ModelDriftEvent.id.desc()) \
            .limit(limit).offset(offset).all()
        return rows, total

    def get_drift_configs(
        self,
        model_type: Optional[str] = None,
        tenant_id: Optional[int] = None,
    ) -> List[ModelDriftConfig]:
        """查询漂移检测配置列表"""
        query = self.db.query(ModelDriftConfig)
        if model_type:
            query = query.filter(ModelDriftConfig.model_type == model_type)
        if tenant_id:
            query = query.filter(
                (ModelDriftConfig.tenant_id == tenant_id) | (ModelDriftConfig.tenant_id.is_(None))
            )
        return query.order_by(ModelDriftConfig.model_type, ModelDriftConfig.model_id).all()

    def save_baseline(
        self,
        model_id: str,
        model_type: str,
        version: str,
        baseline_type: str,
        stats: Optional[Dict] = None,
        bins: Optional[Dict] = None,
        feature_name: Optional[str] = None,
        sample_count: Optional[int] = None,
        tenant_id: Optional[int] = None,
    ) -> ModelDriftBaseline:
        """保存或更新漂移基线"""
        existing = self.db.query(ModelDriftBaseline).filter(
            ModelDriftBaseline.model_id == model_id,
            ModelDriftBaseline.model_type == model_type,
            ModelDriftBaseline.version == version,
            ModelDriftBaseline.baseline_type == baseline_type,
            (ModelDriftBaseline.feature_name == feature_name)
            if feature_name else ModelDriftBaseline.feature_name.is_(None),
        ).first()

        now = datetime.now()
        if existing:
            existing.stats_json = json.dumps(stats, ensure_ascii=False) if stats else existing.stats_json
            existing.bins_json = json.dumps(bins, ensure_ascii=False) if bins else existing.bins_json
            existing.sample_count = sample_count or existing.sample_count
            existing.computed_at = now
            baseline = existing
        else:
            baseline = ModelDriftBaseline(
                model_id=model_id,
                model_type=model_type,
                version=version,
                baseline_type=baseline_type,
                feature_name=feature_name,
                bins_json=json.dumps(bins, ensure_ascii=False) if bins else None,
                stats_json=json.dumps(stats, ensure_ascii=False) if stats else None,
                sample_count=sample_count,
                computed_at=now,
                tenant_id=tenant_id,
            )
            self.db.add(baseline)
        self.db.flush()
        return baseline
