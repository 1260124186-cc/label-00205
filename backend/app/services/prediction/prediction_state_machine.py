"""
预测结果状态机与幂等写入模块

为每个 bolt_id / flm_id 维护当前有效预测快照，历史变更写入变更表。

状态跃迁规则：
    - 升级（severity 增加）：自动，即时生效
    - 关注→正常：需连续 N 次正常确认后才降级
    - 紧急级（status_code >= 3）不可自动降级，需人工确认
    - 相同状态重复预测（幂等窗口内）：仅更新 recent_time，不重复触发告警/工单

幂等策略：
    同一窗口内重复预测（定时任务 + 流式）应幂等。
    若 idempotency_key 相同且状态未变，只更新 recent_time，
    不重复触发告警/工单。
"""

import json
import hashlib
import threading
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from loguru import logger
from sqlalchemy import and_

from app.models.bolt_lstm import STATUS_LABELS
from app.utils.database import (
    get_db,
    PredictionSnapshot,
    PredictionStateChange,
)
from app.utils.config import config


class TransitionType(str, Enum):
    UPGRADE = 'upgrade'
    CONFIRM_DOWNGRADE = 'confirm_downgrade'
    MANUAL_DOWNGRADE = 'manual_downgrade'
    IDEMPOTENT_TOUCH = 'idempotent_touch'


@dataclass
class StateTransitionResult:
    state_changed: bool = False
    should_trigger_alert: bool = False
    transition_type: Optional[TransitionType] = None
    old_status_code: int = 0
    new_status_code: int = 0
    old_status_label: str = '正常'
    new_status_label: str = '正常'
    is_idempotent: bool = False
    snapshot: Optional[Dict[str, Any]] = None


class PredictionStateMachine:
    """
    预测结果状态机

    状态码：0=正常, 1=关注, 2=检查, 3=紧急, 4=故障
    """

    STATUS_NORMAL = 0
    STATUS_ATTENTION = 1
    STATUS_INSPECTION = 2
    STATUS_EMERGENCY = 3
    STATUS_FAILURE = 4

    NON_AUTO_DOWNGRADE_THRESHOLD = 3

    def __init__(self):
        self._downgrade_confirm_n = config.get(
            'state_machine.downgrade_confirm_n', 3
        )
        self._idempotency_window_seconds = config.get(
            'state_machine.idempotency_window_seconds', 300
        )
        logger.info(
            f"预测状态机初始化: 降级确认次数={self._downgrade_confirm_n}, "
            f"幂等窗口={self._idempotency_window_seconds}s"
        )

    def _build_idempotency_key(
        self,
        node_type: str,
        node_id: str,
        status_code: int,
        window_minutes: int = 5,
    ) -> str:
        now = datetime.now()
        window_slot = int(now.timestamp() / (window_minutes * 60))
        raw = f"{node_type}:{node_id}:{status_code}:{window_slot}"
        return hashlib.md5(raw.encode()).hexdigest()[:32]

    def _can_auto_downgrade(self, current_status_code: int) -> bool:
        return current_status_code < self.NON_AUTO_DOWNGRADE_THRESHOLD

    def _needs_confirm_downgrade(self, current_status_code: int) -> bool:
        return current_status_code in (self.STATUS_ATTENTION, self.STATUS_INSPECTION)

    def evaluate(
        self,
        node_type: str,
        node_id: str,
        new_status_code: int,
        confidence: float = 0.0,
        risk_score: float = 0.0,
        risk_level: str = '',
        trigger_source: str = 'scheduled',
        prediction_source: str = '',
        model_version: str = '',
        recent_time: Optional[datetime] = None,
        tenant_id: Optional[int] = None,
    ) -> StateTransitionResult:
        """
        评估状态跃迁并持久化

        Args:
            node_type: bolt / flange
            node_id: 节点ID
            new_status_code: 预测出的新状态码
            confidence: 预测置信度
            risk_score: 风险评分
            risk_level: 风险等级
            trigger_source: 触发来源 scheduled/streaming/manual
            prediction_source: 预测来源 lstm/rule/ensemble
            model_version: 模型版本
            recent_time: 最近状态时间
            tenant_id: 租户ID

        Returns:
            StateTransitionResult
        """
        idempotency_key = self._build_idempotency_key(node_type, node_id, new_status_code)
        new_status_label = STATUS_LABELS.get(new_status_code, '未知')
        now = datetime.now()
        effective_recent_time = recent_time or now

        try:
            with get_db() as db:
                if db is None:
                    logger.warning(f"状态机: DB不可用, 跳过状态评估 {node_type}/{node_id}")
                    return StateTransitionResult(
                        state_changed=False,
                        should_trigger_alert=new_status_code > 0,
                        old_status_code=0,
                        new_status_code=new_status_code,
                        new_status_label=new_status_label,
                    )

                snapshot = db.query(PredictionSnapshot).filter(
                    and_(
                        PredictionSnapshot.node_type == node_type,
                        PredictionSnapshot.node_id == str(node_id),
                    )
                ).first()

                if snapshot is None:
                    return self._create_initial_snapshot(
                        db=db,
                        node_type=node_type,
                        node_id=str(node_id),
                        status_code=new_status_code,
                        status_label=new_status_label,
                        confidence=confidence,
                        risk_score=risk_score,
                        risk_level=risk_level,
                        prediction_source=prediction_source,
                        model_version=model_version,
                        recent_time=effective_recent_time,
                        idempotency_key=idempotency_key,
                        trigger_source=trigger_source,
                        tenant_id=tenant_id,
                    )

                if snapshot.idempotency_key == idempotency_key:
                    return self._handle_idempotent(
                        db=db,
                        snapshot=snapshot,
                        recent_time=effective_recent_time,
                        confidence=confidence,
                        risk_score=risk_score,
                        idempotency_key=idempotency_key,
                    )

                old_status_code = snapshot.status_code
                old_status_label = snapshot.status_label

                if new_status_code > old_status_code:
                    return self._handle_upgrade(
                        db=db,
                        snapshot=snapshot,
                        old_status_code=old_status_code,
                        old_status_label=old_status_label,
                        new_status_code=new_status_code,
                        new_status_label=new_status_label,
                        confidence=confidence,
                        risk_score=risk_score,
                        risk_level=risk_level,
                        prediction_source=prediction_source,
                        model_version=model_version,
                        recent_time=effective_recent_time,
                        idempotency_key=idempotency_key,
                        trigger_source=trigger_source,
                        tenant_id=tenant_id,
                    )

                if new_status_code == old_status_code:
                    return self._handle_same_state(
                        db=db,
                        snapshot=snapshot,
                        confidence=confidence,
                        risk_score=risk_score,
                        risk_level=risk_level,
                        prediction_source=prediction_source,
                        model_version=model_version,
                        recent_time=effective_recent_time,
                        idempotency_key=idempotency_key,
                    )

                if new_status_code < old_status_code:
                    return self._handle_downgrade(
                        db=db,
                        snapshot=snapshot,
                        old_status_code=old_status_code,
                        old_status_label=old_status_label,
                        new_status_code=new_status_code,
                        new_status_label=new_status_label,
                        confidence=confidence,
                        risk_score=risk_score,
                        risk_level=risk_level,
                        prediction_source=prediction_source,
                        model_version=model_version,
                        recent_time=effective_recent_time,
                        idempotency_key=idempotency_key,
                        trigger_source=trigger_source,
                        tenant_id=tenant_id,
                    )

        except Exception as e:
            logger.error(f"状态机评估异常 {node_type}/{node_id}: {e}")
            return StateTransitionResult(
                state_changed=False,
                should_trigger_alert=new_status_code > 0,
                old_status_code=0,
                new_status_code=new_status_code,
                new_status_label=new_status_label,
            )

    def _create_initial_snapshot(
        self,
        db,
        node_type: str,
        node_id: str,
        status_code: int,
        status_label: str,
        confidence: float,
        risk_score: float,
        risk_level: str,
        prediction_source: str,
        model_version: str,
        recent_time: datetime,
        idempotency_key: str,
        trigger_source: str,
        tenant_id: Optional[int],
    ) -> StateTransitionResult:
        snapshot = PredictionSnapshot(
            node_type=node_type,
            node_id=node_id,
            status_code=status_code,
            status_label=status_label,
            confidence=confidence,
            risk_score=risk_score,
            risk_level=risk_level,
            consecutive_normal_count=1 if status_code == 0 else 0,
            consecutive_same_count=1,
            recent_time=recent_time,
            prediction_source=prediction_source,
            model_version=model_version,
            idempotency_key=idempotency_key,
            tenant_id=tenant_id,
        )
        db.add(snapshot)

        self._record_state_change(
            db=db,
            node_type=node_type,
            node_id=node_id,
            old_status_code=0,
            old_status_label='正常',
            new_status_code=status_code,
            new_status_label=status_label,
            transition_type=TransitionType.UPGRADE if status_code > 0 else TransitionType.IDEMPOTENT_TOUCH,
            confidence=confidence,
            risk_score=risk_score,
            consecutive_normal_count=1 if status_code == 0 else 0,
            trigger_source=trigger_source,
            prediction_source=prediction_source,
            model_version=model_version,
            idempotency_key=idempotency_key,
            snapshot_before=None,
            snapshot_after=self._snapshot_to_dict(snapshot),
            tenant_id=tenant_id,
        )
        db.commit()

        logger.info(
            f"状态机: 初始快照 {node_type}/{node_id} -> {status_label}({status_code})"
        )

        return StateTransitionResult(
            state_changed=status_code > 0,
            should_trigger_alert=status_code > 0,
            transition_type=TransitionType.UPGRADE if status_code > 0 else TransitionType.IDEMPOTENT_TOUCH,
            old_status_code=0,
            new_status_code=status_code,
            old_status_label='正常',
            new_status_label=status_label,
            snapshot=self._snapshot_to_dict(snapshot),
        )

    def _handle_idempotent(
        self,
        db,
        snapshot: PredictionSnapshot,
        recent_time: datetime,
        confidence: float,
        risk_score: float,
        idempotency_key: str,
    ) -> StateTransitionResult:
        snapshot.recent_time = recent_time
        if confidence > 0:
            snapshot.confidence = confidence
        if risk_score > 0:
            snapshot.risk_score = risk_score
        snapshot.update_time = datetime.now()
        db.commit()

        logger.debug(
            f"状态机: 幂等命中 {snapshot.node_type}/{snapshot.node_id}, "
            f"状态={snapshot.status_code}, 仅更新recent_time"
        )

        return StateTransitionResult(
            state_changed=False,
            should_trigger_alert=False,
            transition_type=TransitionType.IDEMPOTENT_TOUCH,
            old_status_code=snapshot.status_code,
            new_status_code=snapshot.status_code,
            old_status_label=snapshot.status_label,
            new_status_label=snapshot.status_label,
            is_idempotent=True,
            snapshot=self._snapshot_to_dict(snapshot),
        )

    def _handle_upgrade(
        self,
        db,
        snapshot: PredictionSnapshot,
        old_status_code: int,
        old_status_label: str,
        new_status_code: int,
        new_status_label: str,
        confidence: float,
        risk_score: float,
        risk_level: str,
        prediction_source: str,
        model_version: str,
        recent_time: datetime,
        idempotency_key: str,
        trigger_source: str,
        tenant_id: Optional[int],
    ) -> StateTransitionResult:
        before_dict = self._snapshot_to_dict(snapshot)

        snapshot.status_code = new_status_code
        snapshot.status_label = new_status_label
        snapshot.confidence = confidence
        snapshot.risk_score = risk_score
        snapshot.risk_level = risk_level
        snapshot.consecutive_normal_count = 0
        snapshot.consecutive_same_count = 1
        snapshot.recent_time = recent_time
        snapshot.prediction_source = prediction_source
        snapshot.model_version = model_version
        snapshot.idempotency_key = idempotency_key
        snapshot.update_time = datetime.now()
        if tenant_id is not None:
            snapshot.tenant_id = tenant_id

        after_dict = self._snapshot_to_dict(snapshot)

        self._record_state_change(
            db=db,
            node_type=snapshot.node_type,
            node_id=snapshot.node_id,
            old_status_code=old_status_code,
            old_status_label=old_status_label,
            new_status_code=new_status_code,
            new_status_label=new_status_label,
            transition_type=TransitionType.UPGRADE,
            confidence=confidence,
            risk_score=risk_score,
            consecutive_normal_count=0,
            trigger_source=trigger_source,
            prediction_source=prediction_source,
            model_version=model_version,
            idempotency_key=idempotency_key,
            snapshot_before=before_dict,
            snapshot_after=after_dict,
            tenant_id=tenant_id,
        )
        db.commit()

        logger.info(
            f"状态机: 升级 {snapshot.node_type}/{snapshot.node_id} "
            f"{old_status_label}({old_status_code}) -> {new_status_label}({new_status_code})"
        )

        return StateTransitionResult(
            state_changed=True,
            should_trigger_alert=True,
            transition_type=TransitionType.UPGRADE,
            old_status_code=old_status_code,
            new_status_code=new_status_code,
            old_status_label=old_status_label,
            new_status_label=new_status_label,
            snapshot=after_dict,
        )

    def _handle_same_state(
        self,
        db,
        snapshot: PredictionSnapshot,
        confidence: float,
        risk_score: float,
        risk_level: str,
        prediction_source: str,
        model_version: str,
        recent_time: datetime,
        idempotency_key: str,
    ) -> StateTransitionResult:
        snapshot.consecutive_same_count += 1
        if snapshot.status_code == 0:
            snapshot.consecutive_normal_count += 1
        snapshot.recent_time = recent_time
        snapshot.confidence = confidence
        snapshot.risk_score = risk_score
        snapshot.risk_level = risk_level
        snapshot.prediction_source = prediction_source
        snapshot.model_version = model_version
        snapshot.idempotency_key = idempotency_key
        snapshot.update_time = datetime.now()
        db.commit()

        logger.debug(
            f"状态机: 相同状态 {snapshot.node_type}/{snapshot.node_id} "
            f"状态={snapshot.status_code}, consecutive_same={snapshot.consecutive_same_count}"
        )

        return StateTransitionResult(
            state_changed=False,
            should_trigger_alert=False,
            transition_type=TransitionType.IDEMPOTENT_TOUCH,
            old_status_code=snapshot.status_code,
            new_status_code=snapshot.status_code,
            old_status_label=snapshot.status_label,
            new_status_label=snapshot.status_label,
            snapshot=self._snapshot_to_dict(snapshot),
        )

    def _handle_downgrade(
        self,
        db,
        snapshot: PredictionSnapshot,
        old_status_code: int,
        old_status_label: str,
        new_status_code: int,
        new_status_label: str,
        confidence: float,
        risk_score: float,
        risk_level: str,
        prediction_source: str,
        model_version: str,
        recent_time: datetime,
        idempotency_key: str,
        trigger_source: str,
        tenant_id: Optional[int],
    ) -> StateTransitionResult:
        if not self._can_auto_downgrade(old_status_code):
            snapshot.recent_time = recent_time
            snapshot.confidence = confidence
            snapshot.risk_score = risk_score
            snapshot.idempotency_key = idempotency_key
            snapshot.consecutive_same_count += 1
            snapshot.update_time = datetime.now()
            db.commit()

            logger.info(
                f"状态机: 降级被拒绝（紧急级不可自动降级） "
                f"{snapshot.node_type}/{snapshot.node_id} "
                f"当前={old_status_label}({old_status_code}), "
                f"预测={new_status_label}({new_status_code}), "
                f"需人工确认"
            )

            return StateTransitionResult(
                state_changed=False,
                should_trigger_alert=False,
                transition_type=None,
                old_status_code=old_status_code,
                new_status_code=old_status_code,
                old_status_label=old_status_label,
                new_status_label=old_status_label,
                snapshot=self._snapshot_to_dict(snapshot),
            )

        if self._needs_confirm_downgrade(old_status_code) and new_status_code == 0:
            if new_status_code == 0:
                snapshot.consecutive_normal_count += 1
            snapshot.recent_time = recent_time
            snapshot.confidence = confidence
            snapshot.risk_score = risk_score
            snapshot.idempotency_key = idempotency_key
            snapshot.consecutive_same_count += 1
            snapshot.update_time = datetime.now()

            if snapshot.consecutive_normal_count >= self._downgrade_confirm_n:
                before_dict = self._snapshot_to_dict(snapshot)

                snapshot.status_code = new_status_code
                snapshot.status_label = new_status_label
                snapshot.risk_level = risk_level
                snapshot.prediction_source = prediction_source
                snapshot.model_version = model_version
                snapshot.consecutive_normal_count = 0
                snapshot.consecutive_same_count = 1

                after_dict = self._snapshot_to_dict(snapshot)

                self._record_state_change(
                    db=db,
                    node_type=snapshot.node_type,
                    node_id=snapshot.node_id,
                    old_status_code=old_status_code,
                    old_status_label=old_status_label,
                    new_status_code=new_status_code,
                    new_status_label=new_status_label,
                    transition_type=TransitionType.CONFIRM_DOWNGRADE,
                    confidence=confidence,
                    risk_score=risk_score,
                    consecutive_normal_count=snapshot.consecutive_normal_count,
                    trigger_source=trigger_source,
                    prediction_source=prediction_source,
                    model_version=model_version,
                    idempotency_key=idempotency_key,
                    snapshot_before=before_dict,
                    snapshot_after=after_dict,
                    tenant_id=tenant_id,
                )
                db.commit()

                logger.info(
                    f"状态机: 确认降级 {snapshot.node_type}/{snapshot.node_id} "
                    f"{old_status_label}({old_status_code}) -> {new_status_label}({new_status_code}), "
                    f"连续正常{self._downgrade_confirm_n}次"
                )

                return StateTransitionResult(
                    state_changed=True,
                    should_trigger_alert=False,
                    transition_type=TransitionType.CONFIRM_DOWNGRADE,
                    old_status_code=old_status_code,
                    new_status_code=new_status_code,
                    old_status_label=old_status_label,
                    new_status_label=new_status_label,
                    snapshot=after_dict,
                )
            else:
                db.commit()
                logger.info(
                    f"状态机: 降级等待确认 {snapshot.node_type}/{snapshot.node_id} "
                    f"连续正常={snapshot.consecutive_normal_count}/{self._downgrade_confirm_n}"
                )

                return StateTransitionResult(
                    state_changed=False,
                    should_trigger_alert=False,
                    transition_type=None,
                    old_status_code=old_status_code,
                    new_status_code=old_status_code,
                    old_status_label=old_status_label,
                    new_status_label=old_status_label,
                    snapshot=self._snapshot_to_dict(snapshot),
                )

        if old_status_code == self.STATUS_INSPECTION and new_status_code == self.STATUS_ATTENTION:
            if new_status_code == 0:
                snapshot.consecutive_normal_count += 1

            snapshot.recent_time = recent_time
            snapshot.confidence = confidence
            snapshot.risk_score = risk_score
            snapshot.risk_level = risk_level
            snapshot.prediction_source = prediction_source
            snapshot.model_version = model_version
            snapshot.idempotency_key = idempotency_key
            snapshot.consecutive_same_count = 1
            snapshot.update_time = datetime.now()

            before_dict = self._snapshot_to_dict(snapshot)

            snapshot.status_code = new_status_code
            snapshot.status_label = new_status_label
            snapshot.consecutive_normal_count = 0

            after_dict = self._snapshot_to_dict(snapshot)

            self._record_state_change(
                db=db,
                node_type=snapshot.node_type,
                node_id=snapshot.node_id,
                old_status_code=old_status_code,
                old_status_label=old_status_label,
                new_status_code=new_status_code,
                new_status_label=new_status_label,
                transition_type=TransitionType.CONFIRM_DOWNGRADE,
                confidence=confidence,
                risk_score=risk_score,
                consecutive_normal_count=0,
                trigger_source=trigger_source,
                prediction_source=prediction_source,
                model_version=model_version,
                idempotency_key=idempotency_key,
                snapshot_before=before_dict,
                snapshot_after=after_dict,
                tenant_id=tenant_id,
            )
            db.commit()

            logger.info(
                f"状态机: 部分降级 {snapshot.node_type}/{snapshot.node_id} "
                f"{old_status_label}({old_status_code}) -> {new_status_label}({new_status_code})"
            )

            return StateTransitionResult(
                state_changed=True,
                should_trigger_alert=False,
                transition_type=TransitionType.CONFIRM_DOWNGRADE,
                old_status_code=old_status_code,
                new_status_code=new_status_code,
                old_status_label=old_status_label,
                new_status_label=new_status_label,
                snapshot=after_dict,
            )

        snapshot.recent_time = recent_time
        snapshot.confidence = confidence
        snapshot.risk_score = risk_score
        snapshot.idempotency_key = idempotency_key
        snapshot.consecutive_same_count += 1
        snapshot.update_time = datetime.now()
        db.commit()

        return StateTransitionResult(
            state_changed=False,
            should_trigger_alert=False,
            transition_type=None,
            old_status_code=old_status_code,
            new_status_code=old_status_code,
            old_status_label=old_status_label,
            new_status_label=old_status_label,
            snapshot=self._snapshot_to_dict(snapshot),
        )

    def manual_downgrade(
        self,
        node_type: str,
        node_id: str,
        target_status_code: int,
        operator_id: str = '',
        operator_name: str = '',
        tenant_id: Optional[int] = None,
    ) -> StateTransitionResult:
        """
        人工降级（紧急级/故障级恢复用）

        Args:
            node_type: bolt / flange
            node_id: 节点ID
            target_status_code: 目标状态码
            operator_id: 操作人ID
            operator_name: 操作人姓名
            tenant_id: 租户ID

        Returns:
            StateTransitionResult
        """
        target_label = STATUS_LABELS.get(target_status_code, '未知')

        try:
            with get_db() as db:
                if db is None:
                    logger.warning("状态机: DB不可用, 无法执行人工降级")
                    return StateTransitionResult()

                snapshot = db.query(PredictionSnapshot).filter(
                    and_(
                        PredictionSnapshot.node_type == node_type,
                        PredictionSnapshot.node_id == str(node_id),
                    )
                ).first()

                if snapshot is None:
                    logger.warning(f"状态机: 未找到快照 {node_type}/{node_id}")
                    return StateTransitionResult()

                if target_status_code >= snapshot.status_code:
                    logger.warning(
                        f"状态机: 人工降级目标 {target_status_code} >= 当前 {snapshot.status_code}, 无效操作"
                    )
                    return StateTransitionResult(
                        old_status_code=snapshot.status_code,
                        new_status_code=snapshot.status_code,
                        old_status_label=snapshot.status_label,
                        new_status_label=snapshot.status_label,
                    )

                before_dict = self._snapshot_to_dict(snapshot)
                old_status_code = snapshot.status_code
                old_status_label = snapshot.status_label

                snapshot.status_code = target_status_code
                snapshot.status_label = target_label
                snapshot.consecutive_normal_count = 1 if target_status_code == 0 else 0
                snapshot.consecutive_same_count = 1
                snapshot.recent_time = datetime.now()
                snapshot.update_time = datetime.now()

                after_dict = self._snapshot_to_dict(snapshot)

                self._record_state_change(
                    db=db,
                    node_type=node_type,
                    node_id=str(node_id),
                    old_status_code=old_status_code,
                    old_status_label=old_status_label,
                    new_status_code=target_status_code,
                    new_status_label=target_label,
                    transition_type=TransitionType.MANUAL_DOWNGRADE,
                    confidence=snapshot.confidence,
                    risk_score=snapshot.risk_score,
                    consecutive_normal_count=snapshot.consecutive_normal_count,
                    trigger_source='manual',
                    prediction_source=snapshot.prediction_source,
                    model_version=snapshot.model_version,
                    idempotency_key=snapshot.idempotency_key,
                    snapshot_before=before_dict,
                    snapshot_after=after_dict,
                    tenant_id=tenant_id,
                )
                db.commit()

                logger.info(
                    f"状态机: 人工降级 {node_type}/{node_id} "
                    f"{old_status_label}({old_status_code}) -> {target_label}({target_status_code}), "
                    f"操作人={operator_name}({operator_id})"
                )

                return StateTransitionResult(
                    state_changed=True,
                    should_trigger_alert=False,
                    transition_type=TransitionType.MANUAL_DOWNGRADE,
                    old_status_code=old_status_code,
                    new_status_code=target_status_code,
                    old_status_label=old_status_label,
                    new_status_label=target_label,
                    snapshot=after_dict,
                )

        except Exception as e:
            logger.error(f"状态机人工降级异常 {node_type}/{node_id}: {e}")
            return StateTransitionResult()

    def get_current_snapshot(
        self,
        node_type: str,
        node_id: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            with get_db() as db:
                if db is None:
                    return None
                snapshot = db.query(PredictionSnapshot).filter(
                    and_(
                        PredictionSnapshot.node_type == node_type,
                        PredictionSnapshot.node_id == str(node_id),
                    )
                ).first()
                return self._snapshot_to_dict(snapshot) if snapshot else None
        except Exception as e:
            logger.warning(f"状态机查询快照异常 {node_type}/{node_id}: {e}")
            return None

    @staticmethod
    def _snapshot_to_dict(snapshot: PredictionSnapshot) -> Dict[str, Any]:
        return {
            'node_type': snapshot.node_type,
            'node_id': snapshot.node_id,
            'status_code': snapshot.status_code,
            'status_label': snapshot.status_label,
            'confidence': snapshot.confidence,
            'risk_score': snapshot.risk_score,
            'risk_level': snapshot.risk_level,
            'consecutive_normal_count': snapshot.consecutive_normal_count,
            'consecutive_same_count': snapshot.consecutive_same_count,
            'recent_time': snapshot.recent_time.isoformat() if snapshot.recent_time else None,
            'prediction_source': snapshot.prediction_source,
            'model_version': snapshot.model_version,
            'idempotency_key': snapshot.idempotency_key,
            'tenant_id': snapshot.tenant_id,
        }

    @staticmethod
    def _record_state_change(
        db,
        node_type: str,
        node_id: str,
        old_status_code: int,
        old_status_label: str,
        new_status_code: int,
        new_status_label: str,
        transition_type: TransitionType,
        confidence: float,
        risk_score: float,
        consecutive_normal_count: int,
        trigger_source: str,
        prediction_source: str,
        model_version: str,
        idempotency_key: str,
        snapshot_before: Optional[Dict[str, Any]],
        snapshot_after: Optional[Dict[str, Any]],
        tenant_id: Optional[int],
    ):
        change = PredictionStateChange(
            node_type=node_type,
            node_id=node_id,
            old_status_code=old_status_code,
            old_status_label=old_status_label,
            new_status_code=new_status_code,
            new_status_label=new_status_label,
            transition_type=transition_type.value if isinstance(transition_type, TransitionType) else transition_type,
            confidence=confidence,
            risk_score=risk_score,
            consecutive_normal_count=consecutive_normal_count,
            trigger_source=trigger_source,
            prediction_source=prediction_source,
            model_version=model_version,
            idempotency_key=idempotency_key,
            snapshot_before=json.dumps(snapshot_before, ensure_ascii=False) if snapshot_before else None,
            snapshot_after=json.dumps(snapshot_after, ensure_ascii=False) if snapshot_after else None,
            tenant_id=tenant_id,
        )
        db.add(change)


_state_machine_instance = None
_state_machine_lock = threading.Lock()


def get_state_machine() -> PredictionStateMachine:
    global _state_machine_instance
    if _state_machine_instance is None:
        with _state_machine_lock:
            if _state_machine_instance is None:
                _state_machine_instance = PredictionStateMachine()
    return _state_machine_instance
