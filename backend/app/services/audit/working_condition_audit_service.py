"""
工况审计服务模块

功能:
1. 工况变更事件记录
2. 工况基线持久化
3. 审计记录查询
4. 数据保留策略
5. 工况统计分析
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from loguru import logger

from app.utils.database import get_db, WorkingConditionAudit, WorkingConditionBaseline
from app.utils.config import config
from app.models.working_condition_classifier import (
    WorkingCondition,
    WORKING_CONDITION_LABELS,
    ConditionClassificationResult,
)


@dataclass
class WorkingConditionAuditRecord:
    """
    工况审计记录
    """
    event_id: str
    node_type: str
    node_id: str
    from_condition: Optional[str]
    from_condition_label: Optional[str]
    from_confidence: float
    to_condition: str
    to_condition_label: str
    to_confidence: float
    is_transition: bool
    trigger_data_points: int
    feature_evidence: Dict[str, Any]
    condition_probabilities: Dict[str, float]
    baseline_info: Optional[Dict[str, Any]]
    anomaly_summary: Optional[Dict[str, Any]]
    create_time: datetime


class WorkingConditionAuditService:
    """
    工况审计服务

    负责工况变更事件的记录、查询和管理。
    """

    def __init__(self):
        """
        初始化工况审计服务
        """
        audit_config = config.get('working_condition.audit', {})
        self.default_retention_days = audit_config.get('retention_days', 365)
        self.enabled = audit_config.get('enabled', True)

        logger.info(
            f"工况审计服务初始化完成, "
            f"默认保留天数={self.default_retention_days}, "
            f"启用={self.enabled}"
        )

    def record_condition_change(
        self,
        node_type: str,
        node_id: str,
        from_condition: Optional[WorkingCondition],
        to_condition: WorkingCondition,
        from_confidence: float,
        to_confidence: float,
        is_transition: bool = False,
        trigger_data_points: int = 0,
        feature_evidence: Optional[Dict[str, Any]] = None,
        condition_probabilities: Optional[Dict[WorkingCondition, float]] = None,
        baseline_info: Optional[Dict[str, Any]] = None,
        anomaly_summary: Optional[Dict[str, Any]] = None,
        retention_days: Optional[int] = None,
        tenant_id: Optional[int] = None,
    ) -> Optional[str]:
        """
        记录工况变更事件

        Args:
            node_type: 节点类型 bolt/flange
            node_id: 节点ID
            from_condition: 原工况
            to_condition: 新工况
            from_confidence: 原置信度
            to_confidence: 新置信度
            is_transition: 是否为过渡态
            trigger_data_points: 触发数据点数
            feature_evidence: 特征证据
            condition_probabilities: 各工况概率
            baseline_info: 基线信息
            anomaly_summary: 异常摘要
            retention_days: 保留天数
            tenant_id: 租户ID

        Returns:
            事件ID（失败返回None）
        """
        if not self.enabled:
            return None

        try:
            with get_db() as db:
                if db is None:
                    logger.warning("数据库不可用，跳过工况审计记录")
                    return None

                event_id = str(uuid.uuid4())
                retention = retention_days or self.default_retention_days
                now = datetime.now()

                from_cond_value = from_condition.value if from_condition else None
                from_cond_label = WORKING_CONDITION_LABELS.get(from_condition) if from_condition else None

                prob_dict = {}
                if condition_probabilities:
                    prob_dict = {
                        cond.value: prob
                        for cond, prob in condition_probabilities.items()
                    }

                record = WorkingConditionAudit(
                    event_id=event_id,
                    node_type=node_type,
                    node_id=str(node_id),
                    from_condition=from_cond_value,
                    from_condition_label=from_cond_label,
                    from_confidence=float(from_confidence),
                    to_condition=to_condition.value,
                    to_condition_label=WORKING_CONDITION_LABELS.get(to_condition, to_condition.value),
                    to_confidence=float(to_confidence),
                    is_transition=is_transition,
                    trigger_data_points=trigger_data_points,
                    feature_evidence=json.dumps(feature_evidence or {}, ensure_ascii=False, default=str),
                    condition_probabilities=json.dumps(prob_dict, ensure_ascii=False, default=str),
                    baseline_info=json.dumps(baseline_info or {}, ensure_ascii=False, default=str),
                    anomaly_summary=json.dumps(anomaly_summary or {}, ensure_ascii=False, default=str),
                    retention_days=retention,
                    expire_time=now + timedelta(days=retention),
                    tenant_id=tenant_id,
                    create_time=now,
                )

                db.add(record)
                db.commit()

                logger.info(
                    f"工况变更已记录: {event_id}, "
                    f"node={node_type}/{node_id}, "
                    f"{from_cond_label or 'None'} -> {WORKING_CONDITION_LABELS.get(to_condition)}"
                )

                return event_id

        except Exception as e:
            logger.error(f"记录工况变更失败: {e}")
            return None

    def save_baseline(
        self,
        node_type: str,
        node_id: str,
        condition: WorkingCondition,
        mean_value: float,
        std_value: float,
        upper_bound: float,
        lower_bound: float,
        warning_upper: float,
        warning_lower: float,
        trend_slope: float = 0.0,
        trend_intercept: float = 0.0,
        sample_count: int = 0,
        threshold_config: Optional[Dict[str, Any]] = None,
        version: int = 1,
        tenant_id: Optional[int] = None,
    ) -> Optional[int]:
        """
        保存工况基线配置

        Args:
            node_type: 节点类型
            node_id: 节点ID
            condition: 工况类型
            mean_value: 均值
            std_value: 标准差
            upper_bound: 上界
            lower_bound: 下界
            warning_upper: 预警上界
            warning_lower: 预警下界
            trend_slope: 趋势斜率
            trend_intercept: 趋势截距
            sample_count: 样本数
            threshold_config: 阈值配置
            version: 版本号
            tenant_id: 租户ID

        Returns:
            记录ID（失败返回None）
        """
        try:
            with get_db() as db:
                if db is None:
                    return None

                existing = db.query(WorkingConditionBaseline).filter(
                    WorkingConditionBaseline.node_type == node_type,
                    WorkingConditionBaseline.node_id == str(node_id),
                    WorkingConditionBaseline.condition == condition.value,
                    WorkingConditionBaseline.is_active == True,
                ).first()

                if existing:
                    existing.is_active = False
                    db.flush()
                    version = existing.version + 1

                record = WorkingConditionBaseline(
                    node_type=node_type,
                    node_id=str(node_id),
                    condition=condition.value,
                    condition_label=WORKING_CONDITION_LABELS.get(condition, condition.value),
                    mean_value=float(mean_value),
                    std_value=float(std_value),
                    upper_bound=float(upper_bound),
                    lower_bound=float(lower_bound),
                    warning_upper=float(warning_upper),
                    warning_lower=float(warning_lower),
                    trend_slope=float(trend_slope),
                    trend_intercept=float(trend_intercept),
                    sample_count=sample_count,
                    threshold_config=json.dumps(threshold_config or {}, ensure_ascii=False, default=str),
                    is_active=True,
                    version=version,
                    tenant_id=tenant_id,
                )

                db.add(record)
                db.commit()

                logger.info(
                    f"基线已保存: node={node_type}/{node_id}, "
                    f"condition={condition.value}, version={version}"
                )

                return record.id

        except Exception as e:
            logger.error(f"保存基线失败: {e}")
            return None

    def load_baselines(
        self,
        node_type: str,
        node_id: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        加载节点的所有工况基线

        Args:
            node_type: 节点类型
            node_id: 节点ID

        Returns:
            各工况基线字典
        """
        try:
            with get_db() as db:
                if db is None:
                    return {}

                records = db.query(WorkingConditionBaseline).filter(
                    WorkingConditionBaseline.node_type == node_type,
                    WorkingConditionBaseline.node_id == str(node_id),
                    WorkingConditionBaseline.is_active == True,
                ).all()

                baselines = {}
                for record in records:
                    baselines[record.condition] = {
                        'mean': record.mean_value,
                        'std': record.std_value,
                        'upper_bound': record.upper_bound,
                        'lower_bound': record.lower_bound,
                        'warning_upper': record.warning_upper,
                        'warning_lower': record.warning_lower,
                        'trend_slope': record.trend_slope,
                        'trend_intercept': record.trend_intercept,
                        'sample_count': record.sample_count,
                        'version': record.version,
                        'threshold_config': json.loads(record.threshold_config) if record.threshold_config else {},
                    }

                return baselines

        except Exception as e:
            logger.error(f"加载基线失败: {e}")
            return {}

    def query_condition_changes(
        self,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
        from_condition: Optional[str] = None,
        to_condition: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        查询工况变更记录

        Args:
            node_type: 节点类型过滤
            node_id: 节点ID过滤
            from_condition: 原工况过滤
            to_condition: 新工况过滤
            start_time: 起始时间
            end_time: 结束时间
            limit: 返回数量
            offset: 偏移量

        Returns:
            变更记录列表
        """
        try:
            with get_db() as db:
                if db is None:
                    return []

                query = db.query(WorkingConditionAudit)

                if node_type:
                    query = query.filter(WorkingConditionAudit.node_type == node_type)
                if node_id:
                    query = query.filter(WorkingConditionAudit.node_id == str(node_id))
                if from_condition:
                    query = query.filter(WorkingConditionAudit.from_condition == from_condition)
                if to_condition:
                    query = query.filter(WorkingConditionAudit.to_condition == to_condition)
                if start_time:
                    query = query.filter(WorkingConditionAudit.create_time >= start_time)
                if end_time:
                    query = query.filter(WorkingConditionAudit.create_time <= end_time)

                records = query.order_by(
                    WorkingConditionAudit.create_time.desc()
                ).offset(offset).limit(limit).all()

                return [self._record_to_dict(r) for r in records]

        except Exception as e:
            logger.error(f"查询工况变更记录失败: {e}")
            return []

    def _record_to_dict(self, record: WorkingConditionAudit) -> Dict[str, Any]:
        """
        将数据库记录转换为字典

        Args:
            record: 数据库记录

        Returns:
            字典
        """
        return {
            'id': record.id,
            'event_id': record.event_id,
            'node_type': record.node_type,
            'node_id': record.node_id,
            'from_condition': record.from_condition,
            'from_condition_label': record.from_condition_label,
            'from_confidence': record.from_confidence,
            'to_condition': record.to_condition,
            'to_condition_label': record.to_condition_label,
            'to_confidence': record.to_confidence,
            'is_transition': record.is_transition,
            'trigger_data_points': record.trigger_data_points,
            'feature_evidence': json.loads(record.feature_evidence) if record.feature_evidence else {},
            'condition_probabilities': json.loads(record.condition_probabilities) if record.condition_probabilities else {},
            'baseline_info': json.loads(record.baseline_info) if record.baseline_info else {},
            'anomaly_summary': json.loads(record.anomaly_summary) if record.anomaly_summary else {},
            'retention_days': record.retention_days,
            'create_time': record.create_time.isoformat(),
        }

    def get_condition_statistics(
        self,
        node_type: str,
        node_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        获取工况统计信息

        Args:
            node_type: 节点类型
            node_id: 节点ID
            start_time: 起始时间
            end_time: 结束时间

        Returns:
            统计信息字典
        """
        try:
            with get_db() as db:
                if db is None:
                    return {}

                query = db.query(WorkingConditionAudit).filter(
                    WorkingConditionAudit.node_type == node_type,
                    WorkingConditionAudit.node_id == str(node_id),
                )

                if start_time:
                    query = query.filter(WorkingConditionAudit.create_time >= start_time)
                if end_time:
                    query = query.filter(WorkingConditionAudit.create_time <= end_time)

                records = query.all()

                condition_counts: Dict[str, int] = {}
                total_changes = len(records)

                for record in records:
                    cond = record.to_condition
                    condition_counts[cond] = condition_counts.get(cond, 0) + 1

                transition_count = sum(1 for r in records if r.is_transition)

                return {
                    'node_type': node_type,
                    'node_id': node_id,
                    'total_changes': total_changes,
                    'transition_count': transition_count,
                    'condition_distribution': condition_counts,
                    'time_range': {
                        'start': start_time.isoformat() if start_time else None,
                        'end': end_time.isoformat() if end_time else None,
                    },
                }

        except Exception as e:
            logger.error(f"获取工况统计失败: {e}")
            return {}

    def cleanup_expired(self) -> int:
        """
        清理过期的审计记录

        Returns:
            清理的记录数量
        """
        try:
            with get_db() as db:
                if db is None:
                    return 0

                now = datetime.now()
                expired = db.query(WorkingConditionAudit).filter(
                    WorkingConditionAudit.expire_time < now,
                ).all()

                count = len(expired)
                for record in expired:
                    db.delete(record)

                db.commit()

                if count > 0:
                    logger.info(f"已清理 {count} 条过期工况审计记录")

                return count

        except Exception as e:
            logger.error(f"清理过期工况审计记录失败: {e}")
            return 0

    def get_audit_by_event_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        通过事件ID获取审计记录

        Args:
            event_id: 事件ID

        Returns:
            审计记录字典
        """
        try:
            with get_db() as db:
                if db is None:
                    return None

                record = db.query(WorkingConditionAudit).filter(
                    WorkingConditionAudit.event_id == event_id,
                ).first()

                if record:
                    return self._record_to_dict(record)
                return None

        except Exception as e:
            logger.error(f"获取工况审计记录失败: {e}")
            return None


_working_condition_audit_service: Optional[WorkingConditionAuditService] = None


def get_working_condition_audit_service() -> WorkingConditionAuditService:
    """
    获取工况审计服务单例

    Returns:
        WorkingConditionAuditService 实例
    """
    global _working_condition_audit_service
    if _working_condition_audit_service is None:
        _working_condition_audit_service = WorkingConditionAuditService()
    return _working_condition_audit_service
