"""
试验记录持久化服务模块

负责将 HPO 试验记录写入和读取数据库表 sc_hpo_trials。
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from loguru import logger

from app.utils.database import (
    get_db,
    HPOTrial,
    HPOStudy,
    HPONodeOverride,
)
from app.services.hpo.objective import HPOResult


class TrialStorageService:
    """试验记录持久化服务"""

    def create_trial(
        self,
        trial_id: str,
        study_id: str,
        model_type: str,
        framework: str,
        trial_number: int,
        params: Dict[str, Any],
        node_id: Optional[str] = None,
        node_type: Optional[str] = None,
        status: str = "running",
        tenant_id: int = 0,
    ) -> Optional[HPOTrial]:
        """
        创建新的试验记录

        Args:
            trial_id: 试验唯一ID
            study_id: 研究ID
            model_type: 模型类型
            framework: 优化框架
            trial_number: 试验序号
            params: 超参配置
            node_id: 节点ID
            node_type: 节点类型
            status: 状态
            tenant_id: 租户ID

        Returns:
            Optional[HPOTrial]: 创建的试验记录
        """
        try:
            with get_db() as db:
                if db is None:
                    logger.warning("数据库不可用，无法创建试验记录")
                    return None

                trial = HPOTrial(
                    trial_id=trial_id,
                    study_id=study_id,
                    model_type=model_type,
                    node_id=node_id,
                    node_type=node_type,
                    framework=framework,
                    status=status,
                    trial_number=trial_number,
                    num_layers=params.get("num_layers"),
                    hidden_size=params.get("hidden_size"),
                    dropout_rate=params.get("dropout_rate"),
                    learning_rate=params.get("learning_rate"),
                    sequence_length=params.get("sequence_length"),
                    params=json.dumps(params, ensure_ascii=False),
                    tenant_id=tenant_id,
                    create_time=datetime.now(),
                    update_time=datetime.now(),
                )

                db.add(trial)
                logger.info(f"试验记录已创建: trial_id={trial_id}")
                return trial

        except Exception as e:
            logger.error(f"创建试验记录失败: {e}")
            return None

    def complete_trial(
        self,
        trial_id: str,
        hpo_result: HPOResult,
        params: Dict[str, Any],
    ) -> bool:
        """
        完成试验记录，写入结果指标

        Args:
            trial_id: 试验ID
            hpo_result: HPO 结果
            params: 超参配置

        Returns:
            bool: 是否成功
        """
        try:
            with get_db() as db:
                if db is None:
                    logger.warning("数据库不可用，无法更新试验记录")
                    return False

                trial = db.query(HPOTrial).filter(
                    HPOTrial.trial_id == trial_id
                ).first()

                if not trial:
                    logger.warning(f"试验记录不存在: trial_id={trial_id}")
                    return False

                trial.status = "completed"
                trial.val_f1_score = hpo_result.val_f1_score
                trial.val_precision = hpo_result.val_precision
                trial.val_recall = hpo_result.val_recall
                trial.val_accuracy = hpo_result.val_accuracy
                trial.false_positive_rate = hpo_result.false_positive_rate
                trial.false_negative_rate = hpo_result.false_negative_rate
                trial.inference_latency_ms = hpo_result.inference_latency_ms
                trial.training_time_seconds = hpo_result.training_time_seconds
                trial.objective_value = hpo_result.objective_value
                trial.latency_constraint_violated = hpo_result.latency_constraint_violated
                trial.f1_constraint_violated = hpo_result.f1_constraint_violated
                trial.training_session_id = hpo_result.extra_metrics.get("training_session_id")
                trial.update_time = datetime.now()

                logger.info(
                    f"试验记录已更新: trial_id={trial_id}, "
                    f"objective={hpo_result.objective_value:.4f}"
                )
                return True

        except Exception as e:
            logger.error(f"更新试验记录失败: {e}")
            return False

    def update_trial_status(
        self,
        trial_id: str,
        status: str,
        error_message: Optional[str] = None,
        pruned_reason: Optional[str] = None,
    ) -> bool:
        """
        更新试验状态

        Args:
            trial_id: 试验ID
            status: 新状态
            error_message: 错误信息
            pruned_reason: 被修剪原因

        Returns:
            bool: 是否成功
        """
        try:
            with get_db() as db:
                if db is None:
                    return False

                trial = db.query(HPOTrial).filter(
                    HPOTrial.trial_id == trial_id
                ).first()

                if not trial:
                    return False

                trial.status = status
                trial.error_message = error_message
                trial.pruned_reason = pruned_reason
                trial.update_time = datetime.now()

                logger.info(f"试验状态已更新: trial_id={trial_id}, status={status}")
                return True

        except Exception as e:
            logger.error(f"更新试验状态失败: {e}")
            return False

    def get_trial(self, trial_id: str) -> Optional[Dict[str, Any]]:
        """
        获取试验记录

        Args:
            trial_id: 试验ID

        Returns:
            Optional[Dict[str, Any]]: 试验记录
        """
        try:
            with get_db() as db:
                if db is None:
                    return None

                trial = db.query(HPOTrial).filter(
                    HPOTrial.trial_id == trial_id
                ).first()

                if not trial:
                    return None

                return self._trial_to_dict(trial)

        except Exception as e:
            logger.error(f"获取试验记录失败: {e}")
            return None

    def list_trials(
        self,
        study_id: Optional[str] = None,
        model_type: Optional[str] = None,
        node_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        列出试验记录

        Args:
            study_id: 研究ID过滤
            model_type: 模型类型过滤
            node_id: 节点ID过滤
            status: 状态过滤
            limit: 限制数量
            offset: 偏移量

        Returns:
            List[Dict[str, Any]]: 试验记录列表
        """
        try:
            with get_db() as db:
                if db is None:
                    return []

                query = db.query(HPOTrial)

                if study_id:
                    query = query.filter(HPOTrial.study_id == study_id)
                if model_type:
                    query = query.filter(HPOTrial.model_type == model_type)
                if node_id:
                    query = query.filter(HPOTrial.node_id == node_id)
                if status:
                    query = query.filter(HPOTrial.status == status)

                trials = query.order_by(
                    HPOTrial.create_time.desc()
                ).offset(offset).limit(limit).all()

                return [self._trial_to_dict(t) for t in trials]

        except Exception as e:
            logger.error(f"列出试验记录失败: {e}")
            return []

    def get_best_trial(
        self,
        study_id: str,
        only_valid: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        获取研究的最佳试验

        Args:
            study_id: 研究ID
            only_valid: 只考虑未违反约束的试验

        Returns:
            Optional[Dict[str, Any]]: 最佳试验记录
        """
        try:
            with get_db() as db:
                if db is None:
                    return None

                query = db.query(HPOTrial).filter(
                    HPOTrial.study_id == study_id,
                    HPOTrial.status == "completed",
                )

                if only_valid:
                    query = query.filter(
                        HPOTrial.latency_constraint_violated == False,
                        HPOTrial.f1_constraint_violated == False,
                    )

                best_trial = query.order_by(
                    HPOTrial.objective_value.desc()
                ).first()

                if not best_trial:
                    return None

                return self._trial_to_dict(best_trial)

        except Exception as e:
            logger.error(f"获取最佳试验失败: {e}")
            return None

    def create_study(
        self,
        study_id: str,
        study_name: str,
        model_type: str,
        search_space_json: str,
        objective_config_json: str,
        node_id: Optional[str] = None,
        node_type: Optional[str] = None,
        framework: str = "optuna",
        optimizer: str = "tpe",
        max_trials: int = 50,
        max_concurrent_trials: int = 2,
        f1_weight: float = 1.0,
        false_positive_penalty: float = 0.5,
        latency_threshold_ms: float = 100.0,
        latency_weight: float = 0.3,
        per_node_hpo_enabled: bool = False,
        node_scope: str = "global",
        tenant_id: int = 0,
        created_by: Optional[str] = None,
    ) -> Optional[HPOStudy]:
        """
        创建研究记录

        Args:
            study_id: 研究ID
            study_name: 研究名称
            model_type: 模型类型
            search_space_json: 搜索空间JSON
            objective_config_json: 优化目标配置JSON
            node_id: 节点ID
            node_type: 节点类型
            framework: 优化框架
            optimizer: 优化算法
            max_trials: 最大试验次数
            max_concurrent_trials: 最大并发试验数
            f1_weight: F1权重
            false_positive_penalty: 误报惩罚系数
            latency_threshold_ms: 延迟阈值
            latency_weight: 延迟权重
            per_node_hpo_enabled: 是否启用per-node超参
            node_scope: 节点范围
            tenant_id: 租户ID
            created_by: 创建人

        Returns:
            Optional[HPOStudy]: 创建的研究记录
        """
        try:
            with get_db() as db:
                if db is None:
                    return None

                study = HPOStudy(
                    study_id=study_id,
                    study_name=study_name,
                    model_type=model_type,
                    node_id=node_id,
                    node_type=node_type,
                    search_space=search_space_json,
                    objective_config=objective_config_json,
                    f1_weight=f1_weight,
                    false_positive_penalty=false_positive_penalty,
                    latency_threshold_ms=latency_threshold_ms,
                    latency_weight=latency_weight,
                    framework=framework,
                    optimizer=optimizer,
                    max_trials=max_trials,
                    max_concurrent_trials=max_concurrent_trials,
                    per_node_hpo_enabled=per_node_hpo_enabled,
                    node_scope=node_scope,
                    tenant_id=tenant_id,
                    created_by=created_by,
                    status="pending",
                    create_time=datetime.now(),
                    update_time=datetime.now(),
                )

                db.add(study)
                logger.info(f"研究记录已创建: study_id={study_id}")
                return study

        except Exception as e:
            logger.error(f"创建研究记录失败: {e}")
            return None

    def update_study_status(
        self,
        study_id: str,
        status: str,
        best_trial_id: Optional[str] = None,
        best_params: Optional[Dict[str, Any]] = None,
        best_objective_value: Optional[float] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> bool:
        """
        更新研究状态

        Args:
            study_id: 研究ID
            status: 新状态
            best_trial_id: 最佳试验ID
            best_params: 最佳超参
            best_objective_value: 最佳目标值
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            bool: 是否成功
        """
        try:
            with get_db() as db:
                if db is None:
                    return False

                study = db.query(HPOStudy).filter(
                    HPOStudy.study_id == study_id
                ).first()

                if not study:
                    return False

                study.status = status
                if best_trial_id:
                    study.best_trial_id = best_trial_id
                if best_params:
                    study.best_params = json.dumps(best_params, ensure_ascii=False)
                if best_objective_value is not None:
                    study.best_objective_value = best_objective_value
                if start_time:
                    study.start_time = start_time
                if end_time:
                    study.end_time = end_time
                study.update_time = datetime.now()

                logger.info(f"研究状态已更新: study_id={study_id}, status={status}")
                return True

        except Exception as e:
            logger.error(f"更新研究状态失败: {e}")
            return False

    def get_study(self, study_id: str) -> Optional[Dict[str, Any]]:
        """获取研究记录"""
        try:
            with get_db() as db:
                if db is None:
                    return None

                study = db.query(HPOStudy).filter(
                    HPOStudy.study_id == study_id
                ).first()

                if not study:
                    return None

                return self._study_to_dict(study)

        except Exception as e:
            logger.error(f"获取研究记录失败: {e}")
            return None

    def list_studies(
        self,
        model_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """列出研究记录"""
        try:
            with get_db() as db:
                if db is None:
                    return []

                query = db.query(HPOStudy)

                if model_type:
                    query = query.filter(HPOStudy.model_type == model_type)
                if status:
                    query = query.filter(HPOStudy.status == status)

                studies = query.order_by(
                    HPOStudy.create_time.desc()
                ).offset(offset).limit(limit).all()

                return [self._study_to_dict(s) for s in studies]

        except Exception as e:
            logger.error(f"列出研究记录失败: {e}")
            return []

    def create_node_override(
        self,
        study_id: str,
        node_id: str,
        node_type: str,
        search_space_override: Optional[Dict[str, Any]] = None,
        fixed_params: Optional[Dict[str, Any]] = None,
        tenant_id: int = 0,
    ) -> Optional[HPONodeOverride]:
        """创建节点超参覆盖"""
        try:
            with get_db() as db:
                if db is None:
                    return None

                override = HPONodeOverride(
                    study_id=study_id,
                    node_id=node_id,
                    node_type=node_type,
                    search_space_override=json.dumps(search_space_override, ensure_ascii=False) if search_space_override else None,
                    fixed_params=json.dumps(fixed_params, ensure_ascii=False) if fixed_params else None,
                    tenant_id=tenant_id,
                    create_time=datetime.now(),
                    update_time=datetime.now(),
                )

                db.add(override)
                logger.info(f"节点超参覆盖已创建: study_id={study_id}, node_id={node_id}")
                return override

        except Exception as e:
            logger.error(f"创建节点超参覆盖失败: {e}")
            return None

    def get_node_override(
        self,
        study_id: str,
        node_id: str,
    ) -> Optional[Dict[str, Any]]:
        """获取节点超参覆盖"""
        try:
            with get_db() as db:
                if db is None:
                    return None

                override = db.query(HPONodeOverride).filter(
                    HPONodeOverride.study_id == study_id,
                    HPONodeOverride.node_id == node_id,
                ).first()

                if not override:
                    return None

                return self._node_override_to_dict(override)

        except Exception as e:
            logger.error(f"获取节点超参覆盖失败: {e}")
            return None

    def update_node_override_best(
        self,
        study_id: str,
        node_id: str,
        best_params: Dict[str, Any],
        best_trial_id: str,
        best_objective_value: float,
    ) -> bool:
        """更新节点最佳超参"""
        try:
            with get_db() as db:
                if db is None:
                    return False

                override = db.query(HPONodeOverride).filter(
                    HPONodeOverride.study_id == study_id,
                    HPONodeOverride.node_id == node_id,
                ).first()

                if not override:
                    return False

                override.best_params = json.dumps(best_params, ensure_ascii=False)
                override.best_trial_id = best_trial_id
                override.best_objective_value = best_objective_value
                override.update_time = datetime.now()

                return True

        except Exception as e:
            logger.error(f"更新节点最佳超参失败: {e}")
            return False

    def mark_node_override_applied(
        self,
        study_id: str,
        node_id: str,
    ) -> bool:
        """标记节点超参已应用到训练"""
        try:
            with get_db() as db:
                if db is None:
                    return False

                override = db.query(HPONodeOverride).filter(
                    HPONodeOverride.study_id == study_id,
                    HPONodeOverride.node_id == node_id,
                ).first()

                if not override:
                    return False

                override.applied_to_training = True
                override.applied_time = datetime.now()
                override.update_time = datetime.now()

                return True

        except Exception as e:
            logger.error(f"标记节点超参已应用失败: {e}")
            return False

    def _trial_to_dict(self, trial: HPOTrial) -> Dict[str, Any]:
        """转换试验记录为字典"""
        return {
            "id": trial.id,
            "trial_id": trial.trial_id,
            "study_id": trial.study_id,
            "model_type": trial.model_type,
            "node_id": trial.node_id,
            "node_type": trial.node_type,
            "framework": trial.framework,
            "status": trial.status,
            "trial_number": trial.trial_number,
            "num_layers": trial.num_layers,
            "hidden_size": trial.hidden_size,
            "dropout_rate": trial.dropout_rate,
            "learning_rate": trial.learning_rate,
            "sequence_length": trial.sequence_length,
            "params": json.loads(trial.params) if trial.params else {},
            "val_f1_score": trial.val_f1_score,
            "val_precision": trial.val_precision,
            "val_recall": trial.val_recall,
            "val_accuracy": trial.val_accuracy,
            "false_positive_rate": trial.false_positive_rate,
            "false_negative_rate": trial.false_negative_rate,
            "inference_latency_ms": trial.inference_latency_ms,
            "training_time_seconds": trial.training_time_seconds,
            "objective_value": trial.objective_value,
            "latency_constraint_violated": trial.latency_constraint_violated,
            "f1_constraint_violated": trial.f1_constraint_violated,
            "training_session_id": trial.training_session_id,
            "model_version": trial.model_version,
            "error_message": trial.error_message,
            "pruned_reason": trial.pruned_reason,
            "tenant_id": trial.tenant_id,
            "create_time": trial.create_time.isoformat() if trial.create_time else None,
            "update_time": trial.update_time.isoformat() if trial.update_time else None,
        }

    def _study_to_dict(self, study: HPOStudy) -> Dict[str, Any]:
        """转换研究记录为字典"""
        return {
            "id": study.id,
            "study_id": study.study_id,
            "study_name": study.study_name,
            "model_type": study.model_type,
            "node_id": study.node_id,
            "node_type": study.node_type,
            "search_space": json.loads(study.search_space) if study.search_space else {},
            "objective_config": json.loads(study.objective_config) if study.objective_config else {},
            "f1_weight": study.f1_weight,
            "false_positive_penalty": study.false_positive_penalty,
            "latency_threshold_ms": study.latency_threshold_ms,
            "latency_weight": study.latency_weight,
            "framework": study.framework,
            "optimizer": study.optimizer,
            "max_trials": study.max_trials,
            "max_concurrent_trials": study.max_concurrent_trials,
            "min_trials_to_prune": study.min_trials_to_prune,
            "pruner_type": study.pruner_type,
            "constraints": json.loads(study.constraints) if study.constraints else {},
            "status": study.status,
            "best_trial_id": study.best_trial_id,
            "best_params": json.loads(study.best_params) if study.best_params else {},
            "best_objective_value": study.best_objective_value,
            "per_node_hpo_enabled": study.per_node_hpo_enabled,
            "node_scope": study.node_scope,
            "tenant_id": study.tenant_id,
            "created_by": study.created_by,
            "start_time": study.start_time.isoformat() if study.start_time else None,
            "end_time": study.end_time.isoformat() if study.end_time else None,
            "create_time": study.create_time.isoformat() if study.create_time else None,
            "update_time": study.update_time.isoformat() if study.update_time else None,
        }

    def _node_override_to_dict(self, override: HPONodeOverride) -> Dict[str, Any]:
        """转换节点超参覆盖为字典"""
        return {
            "id": override.id,
            "study_id": override.study_id,
            "node_id": override.node_id,
            "node_type": override.node_type,
            "search_space_override": json.loads(override.search_space_override) if override.search_space_override else {},
            "fixed_params": json.loads(override.fixed_params) if override.fixed_params else {},
            "best_params": json.loads(override.best_params) if override.best_params else {},
            "best_trial_id": override.best_trial_id,
            "best_objective_value": override.best_objective_value,
            "applied_to_training": override.applied_to_training,
            "applied_time": override.applied_time.isoformat() if override.applied_time else None,
            "tenant_id": override.tenant_id,
            "create_time": override.create_time.isoformat() if override.create_time else None,
            "update_time": override.update_time.isoformat() if override.update_time else None,
        }

    def list_node_overrides(
        self,
        study_id: str,
    ) -> List[Dict[str, Any]]:
        """
        列出指定研究的所有节点超参覆盖

        Args:
            study_id: 研究ID

        Returns:
            List[Dict[str, Any]]: 节点覆盖列表
        """
        try:
            with get_db() as db:
                if db is None:
                    logger.warning("数据库不可用，无法获取节点覆盖列表")
                    return []

                overrides = db.query(HPONodeOverride).filter(
                    HPONodeOverride.study_id == study_id
                ).order_by(HPONodeOverride.create_time.desc()).all()

                return [self._node_override_to_dict(o) for o in overrides]

        except Exception as e:
            logger.error(f"获取节点覆盖列表失败: {e}")
            return []

    def delete_study(self, study_id: str) -> bool:
        """
        删除指定的研究及其关联的试验和节点覆盖

        Args:
            study_id: 研究ID

        Returns:
            bool: 是否删除成功
        """
        try:
            with get_db() as db:
                if db is None:
                    logger.warning("数据库不可用，无法删除研究")
                    return False

                # 删除节点覆盖
                db.query(HPONodeOverride).filter(
                    HPONodeOverride.study_id == study_id
                ).delete(synchronize_session=False)

                # 删除试验记录
                db.query(HPOTrial).filter(
                    HPOTrial.study_id == study_id
                ).delete(synchronize_session=False)

                # 删除研究记录
                db.query(HPOStudy).filter(
                    HPOStudy.study_id == study_id
                ).delete(synchronize_session=False)

                db.commit()
                logger.info(f"研究已删除: study_id={study_id}")
                return True

        except Exception as e:
            logger.error(f"删除研究失败: {e}")
            return False
