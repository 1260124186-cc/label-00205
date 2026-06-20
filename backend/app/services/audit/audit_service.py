"""
合规审计服务模块

功能:
1. 预测完整快照记录（输入哈希、模型版本、特征摘要、中间结果、最终决策、策略版本）
2. 数据保留策略（N 年可配置，自动清理过期记录）
3. 审计记录查询
"""

import uuid
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import numpy as np
from loguru import logger
from sqlalchemy import and_, text

from app.utils.database import get_db, PredictionAudit
from app.utils.config import config


class AuditService:
    """
    合规审计服务

    每次预测完成时记录完整快照到 sc_prediction_audit，
    并按可配置的保留年限自动清理过期记录。
    """

    def __init__(self):
        audit_config = config.get('audit', {})
        self.default_retention_years = audit_config.get(
            'retention_years', 3
        )
        logger.info(
            f"合规审计服务初始化完成, 默认保留年限={self.default_retention_years}"
        )

    @staticmethod
    def compute_input_hash(data: np.ndarray) -> str:
        """
        计算输入数据的SHA256哈希

        Args:
            data: 输入数据数组

        Returns:
            SHA256哈希字符串
        """
        data_bytes = data.astype(np.float64).tobytes()
        return hashlib.sha256(data_bytes).hexdigest()

    @staticmethod
    def compute_feature_summary(data: np.ndarray) -> str:
        """
        计算特征摘要

        Args:
            data: 输入数据数组

        Returns:
            JSON格式的特征摘要
        """
        summary = {
            'mean': float(np.mean(data)),
            'std': float(np.std(data)),
            'min': float(np.min(data)),
            'max': float(np.max(data)),
            'count': int(len(data)),
            'median': float(np.median(data)),
            'q1': float(np.percentile(data, 25)),
            'q3': float(np.percentile(data, 75)),
        }
        return json.dumps(summary, ensure_ascii=False)

    def record_prediction(
        self,
        node_type: str,
        node_id: str,
        input_data: np.ndarray,
        model_version: str,
        model_type: str,
        intermediate_results: Dict[str, Any],
        final_decision: Dict[str, Any],
        strategy_version: str,
        strategy_type: int,
        explainability: Optional[Dict[str, Any]] = None,
        retention_years: Optional[int] = None,
        uncertainty_metrics: Optional[Dict[str, Any]] = None,
    ) -> Optional[PredictionAudit]:
        """
        记录预测审计快照

        Args:
            node_type: 节点类型 bolt/flange
            node_id: 节点ID
            input_data: 原始输入数据
            model_version: 模型版本号
            model_type: 模型类型 lstm/rule/attention
            intermediate_results: 中间结果
            final_decision: 最终决策
            strategy_version: 策略版本
            strategy_type: 策略类型
            explainability: 可解释性报告
            retention_years: 保留年限
            uncertainty_metrics: 不确定性度量 (MC Dropout 量化结果)

        Returns:
            PredictionAudit 记录
        """
        retention = retention_years or self.default_retention_years

        try:
            with get_db() as db:
                if db is None:
                    logger.warning("数据库不可用，跳过审计记录")
                    return None

                now = datetime.now()
                prediction_id = str(uuid.uuid4())
                input_hash = self.compute_input_hash(input_data)
                feature_summary = self.compute_feature_summary(input_data)

                record = PredictionAudit(
                    prediction_id=prediction_id,
                    node_type=node_type,
                    node_id=str(node_id),
                    input_hash=input_hash,
                    model_version=model_version,
                    model_type=model_type,
                    feature_summary=feature_summary,
                    intermediate_results=json.dumps(
                        intermediate_results, ensure_ascii=False, default=str
                    ),
                    final_decision=json.dumps(
                        final_decision, ensure_ascii=False, default=str
                    ),
                    strategy_version=strategy_version,
                    strategy_type=strategy_type,
                    explainability=json.dumps(
                        explainability or {}, ensure_ascii=False, default=str
                    ),
                    uncertainty_metrics=json.dumps(
                        uncertainty_metrics, ensure_ascii=False, default=str
                    ) if uncertainty_metrics else None,
                    retention_years=retention,
                    expire_time=now + timedelta(days=retention * 365),
                    create_time=now,
                )

                db.add(record)
                db.commit()

                logger.info(
                    f"审计快照已记录: {prediction_id}, "
                    f"node={node_type}/{node_id}, model={model_version}"
                )
                return record

        except Exception as e:
            logger.error(f"记录审计快照失败: {e}")
            return None

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
                expired = db.query(PredictionAudit).filter(
                    PredictionAudit.expire_time < now,
                ).all()

                count = len(expired)
                for record in expired:
                    db.delete(record)

                db.commit()

                if count > 0:
                    logger.info(f"已清理 {count} 条过期审计记录")
                return count

        except Exception as e:
            logger.error(f"清理过期审计记录失败: {e}")
            return 0

    def query_audits(
        self,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
        model_version: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PredictionAudit]:
        """
        查询审计记录

        Args:
            node_type: 节点类型过滤
            node_id: 节点ID过滤
            model_version: 模型版本过滤
            start_time: 起始时间
            end_time: 结束时间
            limit: 返回数量
            offset: 偏移量

        Returns:
            审计记录列表
        """
        try:
            with get_db() as db:
                if db is None:
                    return []

                query = db.query(PredictionAudit)

                if node_type:
                    query = query.filter(
                        PredictionAudit.node_type == node_type
                    )
                if node_id:
                    query = query.filter(
                        PredictionAudit.node_id == str(node_id)
                    )
                if model_version:
                    query = query.filter(
                        PredictionAudit.model_version == model_version
                    )
                if start_time:
                    query = query.filter(
                        PredictionAudit.create_time >= start_time
                    )
                if end_time:
                    query = query.filter(
                        PredictionAudit.create_time <= end_time
                    )

                return query.order_by(
                    PredictionAudit.create_time.desc()
                ).offset(offset).limit(limit).all()

        except Exception as e:
            logger.error(f"查询审计记录失败: {e}")
            return []

    def get_audit(self, audit_id: int) -> Optional[PredictionAudit]:
        """
        获取单条审计记录详情

        Args:
            audit_id: 审计记录ID

        Returns:
            PredictionAudit 或 None
        """
        try:
            with get_db() as db:
                if db is None:
                    return None
                return db.query(PredictionAudit).filter(
                    PredictionAudit.id == audit_id
                ).first()
        except Exception as e:
            logger.error(f"获取审计记录失败: {e}")
            return None

    def get_audit_by_prediction_id(
        self, prediction_id: str
    ) -> Optional[PredictionAudit]:
        """
        通过预测ID获取审计记录

        Args:
            prediction_id: 预测唯一ID

        Returns:
            PredictionAudit 或 None
        """
        try:
            with get_db() as db:
                if db is None:
                    return None
                return db.query(PredictionAudit).filter(
                    PredictionAudit.prediction_id == prediction_id
                ).first()
        except Exception as e:
            logger.error(f"获取审计记录失败: {e}")
            return None

    def update_retention(
        self, audit_id: int, retention_years: int
    ) -> Optional[PredictionAudit]:
        """
        更新审计记录的保留年限

        Args:
            audit_id: 审计记录ID
            retention_years: 新的保留年限

        Returns:
            更新后的 PredictionAudit
        """
        try:
            with get_db() as db:
                if db is None:
                    return None

                record = db.query(PredictionAudit).filter(
                    PredictionAudit.id == audit_id
                ).first()
                if not record:
                    return None

                record.retention_years = retention_years
                record.expire_time = record.create_time + timedelta(
                    days=retention_years * 365
                )
                db.commit()

                logger.info(
                    f"审计记录 {audit_id} 保留年限已更新为 {retention_years} 年"
                )
                return record

        except Exception as e:
            logger.error(f"更新保留年限失败: {e}")
            return None
