"""
漂移响应编排器 DriftOrchestrator

实现三种响应策略的编排逻辑:
1. notify         - 仅发送通知告警
2. shadow_retrain - 训练新版本模型并进 Shadow 模式验证
3. auto_retrain   - 自动重训并部署新版本

编排器消费 MODEL_DRIFT_DETECTED 事件，根据配置和规则选择响应策略。
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.utils.database import (
    get_db,
    ModelDriftConfig,
    ModelDriftEvent,
    ModelVersionORM,
)
from app.services.model_drift.drift_service import ModelDriftService


class DriftOrchestrator:
    """
    漂移响应编排器

    职责:
    - 订阅漂移检测事件
    - 根据配置和规则判断是否需要响应以及响应级别
    - 执行具体响应动作 (notify / shadow_retrain / auto_retrain)
    - 更新事件表中的响应状态
    """

    RESPONSE_NOTIFY = "notify"
    RESPONSE_SHADOW = "shadow_retrain"
    RESPONSE_AUTO = "auto_retrain"
    RESPONSE_NONE = "none"

    def __init__(
        self,
        db: Optional[Session] = None,
        drift_service: Optional[ModelDriftService] = None,
    ):
        self._db = db
        self._drift_service = drift_service or ModelDriftService(db=db)

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = next(get_db())
        return self._db

    # ============================================================
    # 主入口：处理单个漂移事件
    # ============================================================

    def handle_drift_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理单个漂移检测事件

        Args:
            event_data: 从事件总线接收到的漂移事件数据

        Returns:
            Dict: 响应执行结果
        """
        event_id = event_data.get("event_id") or event_data.get("id")
        if not event_id:
            logger.warning("[DriftOrchestrator] 事件缺少ID，跳过")
            return {"status": "skipped", "reason": "missing_event_id"}

        event = self.db.query(ModelDriftEvent).filter(ModelDriftEvent.id == event_id).first()
        if not event:
            logger.warning(f"[DriftOrchestrator] 事件 {event_id} 不存在，跳过")
            return {"status": "skipped", "reason": "event_not_found"}

        if event.response_status not in ("pending", "failed"):
            logger.info(f"[DriftOrchestrator] 事件 {event.event_no} 已处理 (status={event.response_status})，跳过")
            return {"status": "skipped", "reason": f"already_processed:{event.response_status}"}

        try:
            config = self._resolve_config(event)
            if not config or not config.enabled:
                self._mark_response(event, self.RESPONSE_NONE, "skipped", {"reason": "config_disabled"})
                return {"status": "skipped", "reason": "config_disabled"}

            should_respond = self._should_take_action(event, config)
            if not should_respond:
                self._mark_response(event, self.RESPONSE_NONE, "skipped",
                                    {"reason": "below_consecutive_days_threshold"})
                return {"status": "skipped", "reason": "below_consecutive_days_threshold"}

            strategy = config.response_strategy or self.RESPONSE_NOTIFY
            result = self._execute_strategy(event, config, strategy)
            return result

        except Exception as e:
            logger.exception(f"[DriftOrchestrator] 处理事件 {event.event_no} 失败: {e}")
            self._mark_response(event, event.response_action or self.RESPONSE_NONE, "failed",
                                {"error": str(e)})
            return {"status": "failed", "error": str(e)}

    def process_pending_events(self, limit: int = 50) -> Dict[str, int]:
        """
        批量处理所有 pending 状态的漂移事件

        Args:
            limit: 最多处理事件数

        Returns:
            Dict: 处理统计
        """
        pending_events = (
            self.db.query(ModelDriftEvent)
            .filter(ModelDriftEvent.response_status == "pending")
            .order_by(ModelDriftEvent.detection_date.asc(), ModelDriftEvent.id.asc())
            .limit(limit)
            .all()
        )

        stats = {"total": len(pending_events), "notified": 0, "shadow": 0, "auto": 0, "skipped": 0, "failed": 0}

        for event in pending_events:
            try:
                event_data = {
                    "event_id": event.id,
                    "event_no": event.event_no,
                    "model_id": event.model_id,
                    "model_type": event.model_type,
                    "version": event.version,
                    "detection_date": event.detection_date.isoformat(),
                    "composite_score": event.composite_drift_score,
                    "drift_level": event.drift_level,
                    "triggered_dims": event.triggered_dimensions,
                    "consecutive_days": event.consecutive_days,
                    "tenant_id": event.tenant_id,
                }
                result = self.handle_drift_event(event_data)
                action = result.get("action", "skipped")
                if action == self.RESPONSE_NOTIFY:
                    stats["notified"] += 1
                elif action == self.RESPONSE_SHADOW:
                    stats["shadow"] += 1
                elif action == self.RESPONSE_AUTO:
                    stats["auto"] += 1
                elif result.get("status") == "failed":
                    stats["failed"] += 1
                else:
                    stats["skipped"] += 1
            except Exception as e:
                stats["failed"] += 1
                logger.exception(f"[DriftOrchestrator] 批量处理事件 {event.id} 异常: {e}")

        logger.info(f"[DriftOrchestrator] 批量处理完成: {stats}")
        return stats

    # ============================================================
    # 策略执行
    # ============================================================

    def _execute_strategy(
        self,
        event: ModelDriftEvent,
        config: ModelDriftConfig,
        strategy: str,
    ) -> Dict[str, Any]:
        """根据策略类型执行具体响应动作"""

        if strategy == self.RESPONSE_NOTIFY:
            return self._execute_notify(event, config)
        elif strategy == self.RESPONSE_SHADOW:
            return self._execute_shadow_retrain(event, config)
        elif strategy == self.RESPONSE_AUTO:
            return self._execute_auto_retrain(event, config)
        else:
            logger.warning(f"[DriftOrchestrator] 未知策略 {strategy}，回退到 notify")
            return self._execute_notify(event, config)

    def _execute_notify(
        self,
        event: ModelDriftEvent,
        config: ModelDriftConfig,
    ) -> Dict[str, Any]:
        """策略1: 仅发送通知"""
        try:
            self._update_event_response(event, self.RESPONSE_NOTIFY, "running")

            sent_count = self._send_drift_notifications(event, config)

            success = sent_count > 0
            status = "completed" if success else "failed"
            details = {
                "channels": config.notify_channels_list,
                "sent_count": sent_count,
                "sent_at": datetime.now().isoformat(),
            }

            self._update_event_response(event, self.RESPONSE_NOTIFY, status, details)
            event.notification_sent = success
            self.db.commit()

            logger.info(
                f"[DriftOrchestrator] notify 策略完成: event={event.event_no}, "
                f"sent={sent_count}, status={status}"
            )
            return {"status": status, "action": self.RESPONSE_NOTIFY, "sent_count": sent_count}

        except Exception as e:
            logger.exception(f"[DriftOrchestrator] notify 策略失败: {e}")
            self._update_event_response(event, self.RESPONSE_NOTIFY, "failed", {"error": str(e)})
            return {"status": "failed", "action": self.RESPONSE_NOTIFY, "error": str(e)}

    def _execute_shadow_retrain(
        self,
        event: ModelDriftEvent,
        config: ModelDriftConfig,
    ) -> Dict[str, Any]:
        """策略2: Shadow重训（训练新版本但不激活）"""
        try:
            self._update_event_response(event, self.RESPONSE_SHADOW, "running")

            notification_result = self._send_drift_notifications(event, config)

            session_id, new_version = self._trigger_retraining(
                event, config, activate=False
            )

            status = "running" if session_id else "failed"
            details = {
                "notification_sent": notification_result > 0,
                "retrain_session_id": session_id,
                "new_version": new_version,
                "quality_bar": config.shadow_retrain_quality_bar,
                "started_at": datetime.now().isoformat(),
            }

            self._update_event_response(event, self.RESPONSE_SHADOW, status, details)
            event.retrain_session_id = session_id
            event.new_version = new_version
            event.notification_sent = notification_result > 0
            self.db.commit()

            logger.info(
                f"[DriftOrchestrator] shadow_retrain 策略完成: event={event.event_no}, "
                f"session={session_id}, version={new_version}"
            )
            return {
                "status": status,
                "action": self.RESPONSE_SHADOW,
                "session_id": session_id,
                "new_version": new_version,
            }

        except Exception as e:
            logger.exception(f"[DriftOrchestrator] shadow_retrain 策略失败: {e}")
            self._update_event_response(event, self.RESPONSE_SHADOW, "failed", {"error": str(e)})
            return {"status": "failed", "action": self.RESPONSE_SHADOW, "error": str(e)}

    def _execute_auto_retrain(
        self,
        event: ModelDriftEvent,
        config: ModelDriftConfig,
    ) -> Dict[str, Any]:
        """策略3: 自动重训并部署新版本"""
        try:
            min_days = config.auto_retrain_min_days or 7
            if self._has_recent_retrain(event.model_id, event.model_type, min_days):
                logger.info(
                    f"[DriftOrchestrator] {event.model_id}/{event.model_type} "
                    f"{min_days}天内已重训过，本次仅通知"
                )
                return self._execute_notify(event, config)

            self._update_event_response(event, self.RESPONSE_AUTO, "running")

            notification_result = self._send_drift_notifications(event, config)

            session_id, new_version = self._trigger_retraining(
                event, config, activate=True
            )

            status = "running" if session_id else "failed"
            details = {
                "notification_sent": notification_result > 0,
                "retrain_session_id": session_id,
                "new_version": new_version,
                "auto_activate": True,
                "started_at": datetime.now().isoformat(),
            }

            self._update_event_response(event, self.RESPONSE_AUTO, status, details)
            event.retrain_session_id = session_id
            event.new_version = new_version
            event.notification_sent = notification_result > 0
            self.db.commit()

            logger.info(
                f"[DriftOrchestrator] auto_retrain 策略完成: event={event.event_no}, "
                f"session={session_id}, version={new_version}"
            )
            return {
                "status": status,
                "action": self.RESPONSE_AUTO,
                "session_id": session_id,
                "new_version": new_version,
            }

        except Exception as e:
            logger.exception(f"[DriftOrchestrator] auto_retrain 策略失败: {e}")
            self._update_event_response(event, self.RESPONSE_AUTO, "failed", {"error": str(e)})
            return {"status": "failed", "action": self.RESPONSE_AUTO, "error": str(e)}

    # ============================================================
    # 规则判断
    # ============================================================

    def _should_take_action(self, event: ModelDriftEvent, config: ModelDriftConfig) -> bool:
        """判断是否需要采取响应动作（连续天数阈值）"""
        required_days = config.consecutive_days_alert or 2
        current_days = event.consecutive_days or 1

        if current_days < required_days:
            logger.info(
                f"[DriftOrchestrator] 连续天数不足: current={current_days}, "
                f"required={required_days}, 仅记录不响应"
            )
            return False
        return True

    def _has_recent_retrain(self, model_id: str, model_type: str, min_days: int) -> bool:
        """检查最近N天内是否已经执行过重训"""
        cutoff = datetime.now() - timedelta(days=min_days)
        recent = (
            self.db.query(ModelDriftEvent)
            .filter(
                ModelDriftEvent.model_id == model_id,
                ModelDriftEvent.model_type == model_type,
                ModelDriftEvent.response_action.in_([self.RESPONSE_SHADOW, self.RESPONSE_AUTO]),
                ModelDriftEvent.response_status.in_(["running", "completed"]),
                ModelDriftEvent.create_time >= cutoff,
            )
            .first()
        )
        return recent is not None

    def _resolve_config(self, event: ModelDriftEvent) -> Optional[ModelDriftConfig]:
        """解析事件对应的漂移配置"""
        query = self.db.query(ModelDriftConfig).filter(
            ModelDriftConfig.model_type == event.model_type,
            ModelDriftConfig.enabled == True,
        )
        if event.tenant_id:
            query = query.filter(
                (ModelDriftConfig.tenant_id == event.tenant_id)
                | (ModelDriftConfig.tenant_id.is_(None))
            )

        configs = query.all()

        for cfg in configs:
            if cfg.model_id == event.model_id:
                return cfg

        for cfg in configs:
            if cfg.model_id == "default":
                return cfg

        return configs[0] if configs else None

    # ============================================================
    # 通知发送
    # ============================================================

    def _send_drift_notifications(self, event: ModelDriftEvent, config: ModelDriftConfig) -> int:
        """发送漂移检测通知"""
        try:
            from app.services.alert.notification_service import NotificationService
        except ImportError:
            logger.warning("[DriftOrchestrator] NotificationService 不可用，跳过通知")
            return 0

        try:
            alert_content = self._build_alert_content(event, config)
            channels = config.notify_channels_list or ["email"]

            sent = 0
            for channel in channels:
                try:
                    svc = NotificationService(db=self.db)
                    func = getattr(svc, f"send_{channel}", None)
                    if not func:
                        logger.warning(f"[DriftOrchestrator] 不支持的通知渠道: {channel}")
                        continue

                    targets = self._get_notify_targets(config, channel)
                    if not targets:
                        logger.warning(f"[DriftOrchestrator] 渠道 {channel} 没有配置目标")
                        continue

                    title = alert_content["title"]
                    body = alert_content["body"]
                    for target in targets:
                        try:
                            func(target, title, body)
                            sent += 1
                        except Exception as e:
                            logger.warning(f"[DriftOrchestrator] 发送 {channel} 通知失败: {e}")
                except Exception as e:
                    logger.warning(f"[DriftOrchestrator] 通知渠道 {channel} 异常: {e}")

            logger.info(f"[DriftOrchestrator] 通知发送完成: {sent}/{len(channels)} 渠道")
            return sent

        except Exception as e:
            logger.exception(f"[DriftOrchestrator] 发送通知失败: {e}")
            return 0

    @staticmethod
    def _build_alert_content(event: ModelDriftEvent, config: ModelDriftConfig) -> Dict[str, str]:
        """构建告警通知内容"""
        level_map = {"low": "轻微", "medium": "中等", "high": "严重", "critical": "紧急", "none": "无"}
        level_cn = level_map.get(event.drift_level, "未知")

        title = f"[模型漂移告警][{level_cn}] {event.model_type} 模型检测到数据漂移"

        dims = event.triggered_dimensions or []
        dim_cn = {
            "psi": "数据分布(PSI)",
            "ks": "数据分布(KS检验)",
            "confidence": "置信度分布",
            "false_positive": "误报率上升",
            "feature_shift": "特征均值偏移",
        }
        dim_names = "、".join([dim_cn.get(d, d) for d in dims])

        body_lines = [
            f"事件编号: {event.event_no}",
            f"模型类型: {event.model_type}",
            f"模型标识: {event.model_id}",
            f"当前版本: {event.version}",
            f"检测日期: {event.detection_date}",
            f"漂移等级: {level_cn}",
            f"综合分数: {event.composite_drift_score:.3f} (阈值 {config.composite_score_threshold or 0.6})",
            f"触发维度: {dim_names or '无'}",
            f"连续天数: {event.consecutive_days} 天 (阈值 {config.consecutive_days_alert or 2})",
            "",
            "详细指标:",
            f"  - PSI分数: {event.psi_score:.4f}" if event.psi_score is not None else "  - PSI分数: N/A",
            f"  - KS统计量: {event.ks_statistic:.4f}" if event.ks_statistic is not None else "  - KS统计量: N/A",
            f"  - 置信度漂移: {event.confidence_drift_score:.4f}" if event.confidence_drift_score is not None else "  - 置信度漂移: N/A",
            f"  - 误报率: {event.false_positive_rate:.2%}" if event.false_positive_rate is not None else "  - 误报率: N/A",
            f"  - 特征偏移数: {event.feature_mean_shift_count}" if event.feature_mean_shift_count is not None else "  - 特征偏移数: N/A",
            "",
            f"响应策略: {config.response_strategy}",
        ]
        body = "\n".join(body_lines)
        return {"title": title, "body": body}

    @staticmethod
    def _get_notify_targets(config: ModelDriftConfig, channel: str) -> List[str]:
        """解析通知目标列表"""
        import json as _json
        if not config.notify_targets:
            return []
        try:
            targets = _json.loads(config.notify_targets) if isinstance(config.notify_targets, str) else config.notify_targets
            if isinstance(targets, dict):
                return targets.get(channel, [])
            elif isinstance(targets, list):
                return targets
        except (_json.JSONDecodeError, TypeError, ValueError):
            pass
        return []

    # ============================================================
    # 重训触发
    # ============================================================

    def _trigger_retraining(
        self,
        event: ModelDriftEvent,
        config: ModelDriftConfig,
        activate: bool = False,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        触发模型重训

        Args:
            event: 漂移事件
            config: 漂移配置
            activate: 是否自动激活新版本

        Returns:
            Tuple[session_id, version]: 训练会话ID和新版本号
        """
        try:
            from app.services.training_service import TrainingService
            from app.services.model_version_service import ModelVersionService
        except ImportError:
            logger.warning("[DriftOrchestrator] TrainingService/ModelVersionService 不可用")
            return None, None

        try:
            node_id = event.model_id if not event.model_id.startswith("global_") else None

            ts = TrainingService(db=self.db)
            session_id = ts.start_training(
                model_type=event.model_type,
                node_id=node_id,
                force_retrain=True,
                is_incremental=True,
                base_model_version=event.version,
            )
            logger.info(f"[DriftOrchestrator] 已触发训练: session={session_id}")

            new_version = None
            try:
                result = ts.execute_training(session_id)
                if result and result.get("status") == "completed":
                    new_version = result.get("version")
                    metrics = result.get("metrics") or {}
                    if activate and new_version:
                        mvs = ModelVersionService(db=self.db)
                        mvs.activate_version(
                            model_type=event.model_type,
                            node_id=node_id,
                            version=new_version,
                            tenant_id=event.tenant_id,
                        )
                        logger.info(f"[DriftOrchestrator] 新版本已激活: {new_version}")
            except Exception as e:
                logger.warning(f"[DriftOrchestrator] 同步等待训练结果失败，将异步处理: {e}")

            return session_id, new_version

        except Exception as e:
            logger.exception(f"[DriftOrchestrator] 触发重训失败: {e}")
            return None, None

    # ============================================================
    # 数据库辅助方法
    # ============================================================

    def _update_event_response(
        self,
        event: ModelDriftEvent,
        action: str,
        status: str,
        details: Optional[Dict] = None,
    ) -> None:
        """更新事件的响应动作和状态"""
        event.response_action = action
        event.response_status = status
        if details:
            try:
                existing = event.response_detail_dict or {}
                existing.update(details)
                event.response_details = json.dumps(existing, ensure_ascii=False)
            except Exception:
                pass
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()

    def _mark_response(
        self,
        event: ModelDriftEvent,
        action: str,
        status: str,
        details: Optional[Dict] = None,
    ) -> None:
        """标记事件响应状态（不触发实际动作）"""
        self._update_event_response(event, action, status, details)
