"""
CMMS/EAM 集成服务模块

负责与第三方 CMMS/EAM 系统对接，支持 REST API 推送和 Webhook 接收。

主要功能:
- create_cmms_config: 创建 CMMS 配置
- update_cmms_config: 更新 CMMS 配置
- list_cmms_configs: 查询 CMMS 配置列表
- sync_work_order: 同步工单到 CMMS
- handle_webhook: 处理 CMMS Webhook 回调
- sync_work_order_status: 同步工单状态
"""

import json
import time
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from loguru import logger
import httpx

from app.utils.database import (
    get_db,
    CmmsIntegrationConfig,
    CmmsSyncLog,
    WorkOrder,
)
from app.utils.config import config


class CmmsService:
    """
    CMMS/EAM 集成服务类
    """

    DEFAULT_STATUS_MAPPING = {
        'pending_assignment': 'NEW',
        'open': 'NEW',
        'assigned': 'ASSIGNED',
        'in_progress': 'INPROG',
        'retested': 'COMPLETED',
        'resolved': 'RESOLVED',
        'closed': 'CLOSED',
    }

    DEFAULT_PRIORITY_MAPPING = {
        'low': 'LOW',
        'medium': 'MEDIUM',
        'high': 'HIGH',
        'urgent': 'URGENT',
    }

    def __init__(self):
        logger.info("CMMS集成服务初始化完成")

    # ---------- 配置管理 ----------

    def create_config(
        self,
        system_name: str,
        system_type: str = None,
        base_url: str = None,
        auth_type: str = None,
        auth_config: Dict[str, Any] = None,
        work_order_sync: bool = False,
        work_order_webhook_url: str = None,
        work_order_push_url: str = None,
        status_mapping: Dict[str, str] = None,
        priority_mapping: Dict[str, str] = None,
        field_mapping: Dict[str, Any] = None,
        enabled: bool = True,
        sync_direction: str = 'push',
        sync_interval: int = 60,
        tenant_id: int = None,
        extra_info: Dict[str, Any] = None,
    ) -> Optional[CmmsIntegrationConfig]:
        """
        创建 CMMS 集成配置
        """
        with get_db() as db:
            if db is None:
                return None

            cfg = CmmsIntegrationConfig(
                system_name=system_name,
                system_type=system_type,
                base_url=base_url,
                auth_type=auth_type,
                auth_config=json.dumps(auth_config or {}, ensure_ascii=False) if auth_config else None,
                work_order_sync=work_order_sync,
                work_order_webhook_url=work_order_webhook_url,
                work_order_push_url=work_order_push_url,
                status_mapping=json.dumps(status_mapping or self.DEFAULT_STATUS_MAPPING, ensure_ascii=False),
                priority_mapping=json.dumps(priority_mapping or self.DEFAULT_PRIORITY_MAPPING, ensure_ascii=False),
                field_mapping=json.dumps(field_mapping or {}, ensure_ascii=False) if field_mapping else None,
                enabled=enabled,
                sync_direction=sync_direction,
                sync_interval=sync_interval,
                tenant_id=tenant_id,
                extra_info=json.dumps(extra_info or {}, ensure_ascii=False) if extra_info else None,
            )

            db.add(cfg)
            db.flush()
            cfg_id = cfg.id
            db.commit()

            logger.info(f"CMMS配置已创建: id={cfg_id}, 系统={system_name}")
            return db.query(CmmsIntegrationConfig).filter(
                CmmsIntegrationConfig.id == cfg_id
            ).first()

    def get_config(self, config_id: int) -> Optional[CmmsIntegrationConfig]:
        """
        获取 CMMS 配置详情
        """
        with get_db() as db:
            if db is None:
                return None
            return db.query(CmmsIntegrationConfig).filter(
                CmmsIntegrationConfig.id == config_id
            ).first()

    def list_configs(
        self,
        enabled: bool = None,
        system_type: str = None,
        tenant_id: int = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[CmmsIntegrationConfig], int]:
        """
        查询 CMMS 配置列表
        """
        with get_db() as db:
            if db is None:
                return [], 0

            query = db.query(CmmsIntegrationConfig)

            if enabled is not None:
                query = query.filter(CmmsIntegrationConfig.enabled == enabled)
            if system_type:
                query = query.filter(CmmsIntegrationConfig.system_type == system_type)
            if tenant_id:
                query = query.filter(CmmsIntegrationConfig.tenant_id == tenant_id)

            total = query.count()
            configs = query.order_by(
                CmmsIntegrationConfig.create_time.desc()
            ).offset(offset).limit(limit).all()

            return configs, total

    def update_config(
        self, config_id: int, **kwargs
    ) -> Optional[CmmsIntegrationConfig]:
        """
        更新 CMMS 配置
        """
        with get_db() as db:
            if db is None:
                return None

            cfg = db.query(CmmsIntegrationConfig).filter(
                CmmsIntegrationConfig.id == config_id
            ).first()
            if not cfg:
                return None

            json_fields = {'auth_config', 'status_mapping', 'priority_mapping', 'field_mapping', 'extra_info'}

            for key, value in kwargs.items():
                if value is None:
                    continue
                if hasattr(cfg, key):
                    if key in json_fields and value is not None:
                        setattr(cfg, key, json.dumps(value, ensure_ascii=False))
                    else:
                        setattr(cfg, key, value)

            db.commit()
            logger.info(f"CMMS配置已更新: id={config_id}")
            return db.query(CmmsIntegrationConfig).filter(
                CmmsIntegrationConfig.id == config_id
            ).first()

    def delete_config(self, config_id: int) -> bool:
        """
        删除 CMMS 配置
        """
        with get_db() as db:
            if db is None:
                return False

            cfg = db.query(CmmsIntegrationConfig).filter(
                CmmsIntegrationConfig.id == config_id
            ).first()
            if not cfg:
                return False

            db.delete(cfg)
            db.commit()
            logger.info(f"CMMS配置已删除: id={config_id}")
            return True

    # ---------- 工单同步 ----------

    def sync_work_order(
        self,
        work_order_id: int,
        config_id: int = None,
        sync_type: str = 'work_order_create',
    ) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
        """
        同步工单到 CMMS 系统

        Args:
            work_order_id: 工单ID
            config_id: CMMS配置ID（None则同步所有启用的配置）
            sync_type: 同步类型

        Returns:
            (是否成功, 同步日志ID, 外部ID, 错误信息)
        """
        with get_db() as db:
            if db is None:
                return False, None, None, "数据库不可用"

            wo = db.query(WorkOrder).filter(
                WorkOrder.id == work_order_id
            ).first()
            if not wo:
                return False, None, None, "工单不存在"

            if config_id:
                configs = [db.query(CmmsIntegrationConfig).filter(
                    CmmsIntegrationConfig.id == config_id,
                    CmmsIntegrationConfig.enabled == True,
                    CmmsIntegrationConfig.work_order_sync == True,
                ).first()]
            else:
                configs = db.query(CmmsIntegrationConfig).filter(
                    CmmsIntegrationConfig.enabled == True,
                    CmmsIntegrationConfig.work_order_sync == True,
                ).all()

            if not configs or all(c is None for c in configs):
                return False, None, None, "无可用的CMMS配置"

            last_result = (False, None, None, "无可用的CMMS配置")

            for cfg in configs:
                if cfg is None:
                    continue
                result = self._sync_to_single_config(wo, cfg, sync_type)
                last_result = result
                if result[0]:
                    pass

            return last_result

    def _sync_to_single_config(
        self,
        work_order: WorkOrder,
        config: CmmsIntegrationConfig,
        sync_type: str,
    ) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
        """
        同步工单到单个 CMMS 配置
        """
        with get_db() as db:
            if db is None:
                return False, None, None, "数据库不可用"

            sync_log = CmmsSyncLog(
                config_id=config.id,
                sync_type=sync_type,
                sync_direction='push',
                work_order_id=work_order.id,
                status='pending',
                sync_time=datetime.now(),
            )
            db.add(sync_log)
            db.flush()
            log_id = sync_log.id

            try:
                payload = self._build_work_order_payload(work_order, config)
                sync_log.request_data = json.dumps(payload, ensure_ascii=False)

                url = config.work_order_push_url or f"{config.base_url}/api/workorders"
                headers = self._build_auth_headers(config)

                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        url,
                        json=payload,
                        headers=headers,
                    )

                    sync_log.response_data = response.text[:2000] if response.text else ''
                    sync_log.sync_time = datetime.now()

                    if response.status_code in (200, 201, 202):
                        try:
                            resp_data = response.json()
                            external_id = resp_data.get('id') or resp_data.get('workorder_id') or resp_data.get('wo_id')
                        except (json.JSONDecodeError, ValueError):
                            external_id = None

                        sync_log.status = 'success'
                        sync_log.external_id = str(external_id) if external_id else None

                        extra = {}
                        if work_order.extra_info:
                            try:
                                extra = json.loads(work_order.extra_info)
                            except (json.JSONDecodeError, TypeError):
                                pass
                        extra[f'cmms_{config.id}_external_id'] = external_id
                        work_order.extra_info = json.dumps(extra, ensure_ascii=False)

                        config.last_sync_time = datetime.now()

                        db.commit()
                        logger.info(
                            f"工单同步成功: 工单={work_order.order_no}, "
                            f"CMMS={config.system_name}, 外部ID={external_id}"
                        )
                        return True, log_id, external_id, None
                    else:
                        sync_log.status = 'failed'
                        sync_log.error_message = f"HTTP {response.status_code}: {response.text[:500]}"
                        db.commit()
                        logger.warning(
                            f"工单同步失败: 工单={work_order.order_no}, "
                            f"CMMS={config.system_name}, HTTP {response.status_code}"
                        )
                        return False, log_id, None, f"HTTP {response.status_code}"

            except httpx.HTTPError as e:
                sync_log.status = 'failed'
                sync_log.error_message = str(e)[:500]
                db.commit()
                logger.error(f"工单同步请求异常: {e}")
                return False, log_id, None, str(e)
            except Exception as e:
                sync_log.status = 'failed'
                sync_log.error_message = str(e)[:500]
                db.commit()
                logger.error(f"工单同步异常: {e}")
                return False, log_id, None, str(e)

    def _build_work_order_payload(
        self, work_order: WorkOrder, config: CmmsIntegrationConfig
    ) -> Dict[str, Any]:
        """
        构建工单同步 payload
        """
        try:
            status_mapping = json.loads(config.status_mapping) if config.status_mapping else self.DEFAULT_STATUS_MAPPING
        except (json.JSONDecodeError, TypeError):
            status_mapping = self.DEFAULT_STATUS_MAPPING

        try:
            priority_mapping = json.loads(config.priority_mapping) if config.priority_mapping else self.DEFAULT_PRIORITY_MAPPING
        except (json.JSONDecodeError, TypeError):
            priority_mapping = self.DEFAULT_PRIORITY_MAPPING

        try:
            field_mapping = json.loads(config.field_mapping) if config.field_mapping else {}
        except (json.JSONDecodeError, TypeError):
            field_mapping = {}

        payload = {
            'workOrderNo': work_order.order_no,
            'title': work_order.title,
            'description': work_order.description,
            'status': status_mapping.get(work_order.status, work_order.status),
            'priority': priority_mapping.get(work_order.priority, work_order.priority),
            'nodeType': work_order.node_type,
            'nodeId': work_order.node_id,
            'alertLevel': work_order.alert_level,
            'riskScore': work_order.risk_score,
            'assignee': work_order.assignee_name,
            'assigneeId': work_order.assignee_id,
            'creator': work_order.creator_name,
            'creatorId': work_order.creator_id,
            'dueTime': work_order.due_time.isoformat() if work_order.due_time else None,
            'createTime': work_order.create_time.isoformat() if work_order.create_time else None,
            'recommendations': work_order.recommendations,
            'alertId': work_order.alert_id,
        }

        if field_mapping:
            mapped_payload = {}
            for src_field, dst_field in field_mapping.items():
                if src_field in payload:
                    mapped_payload[dst_field] = payload[src_field]
            payload = mapped_payload

        return payload

    def _build_auth_headers(self, config: CmmsIntegrationConfig) -> Dict[str, str]:
        """
        构建认证请求头
        """
        headers = {'Content-Type': 'application/json'}

        if not config.auth_type:
            return headers

        try:
            auth_config = json.loads(config.auth_config) if config.auth_config else {}
        except (json.JSONDecodeError, TypeError):
            auth_config = {}

        auth_type = config.auth_type.lower()

        if auth_type == 'basic':
            import base64
            username = auth_config.get('username', '')
            password = auth_config.get('password', '')
            token = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers['Authorization'] = f"Basic {token}"

        elif auth_type == 'api_key':
            api_key = auth_config.get('api_key', '')
            header_name = auth_config.get('header_name', 'X-API-Key')
            headers[header_name] = api_key

        elif auth_type == 'bearer' or auth_type == 'token':
            token = auth_config.get('token', '')
            headers['Authorization'] = f"Bearer {token}"

        elif auth_type == 'oauth2':
            token = auth_config.get('access_token', '')
            headers['Authorization'] = f"Bearer {token}"

        return headers

    # ---------- Webhook 处理 ----------

    def handle_webhook(
        self,
        config_id: int,
        payload: Dict[str, Any],
        signature: str = None,
    ) -> Tuple[bool, int, str]:
        """
        处理 CMMS Webhook 回调

        Args:
            config_id: CMMS配置ID
            payload: Webhook payload
            signature: 签名（用于验证）

        Returns:
            (是否成功, 处理数量, 消息)
        """
        with get_db() as db:
            if db is None:
                return False, 0, "数据库不可用"

            config = db.query(CmmsIntegrationConfig).filter(
                CmmsIntegrationConfig.id == config_id,
                CmmsIntegrationConfig.enabled == True,
            ).first()

            if not config:
                return False, 0, "CMMS配置不存在或未启用"

            if signature:
                valid = self._verify_webhook_signature(config, payload, signature)
                if not valid:
                    logger.warning(f"Webhook签名验证失败: config_id={config_id}")
                    return False, 0, "签名验证失败"

            processed_count = 0
            message = "处理成功"

            event_type = payload.get('event') or payload.get('eventType') or payload.get('type', 'unknown')

            if event_type in ('work_order_update', 'workorder_update', 'status_update'):
                wo_data = payload.get('workOrder') or payload.get('data') or payload
                processed = self._update_work_order_from_webhook(db, config, wo_data)
                if processed:
                    processed_count += 1

            elif event_type in ('work_order_create', 'workorder_create', 'create'):
                pass

            else:
                message = f"未知事件类型: {event_type}"

            sync_log = CmmsSyncLog(
                config_id=config_id,
                sync_type=f'webhook_{event_type}',
                sync_direction='pull',
                status='success' if processed_count > 0 else 'failed',
                request_data=json.dumps(payload, ensure_ascii=False)[:2000],
                error_message=None if processed_count > 0 else message,
                sync_time=datetime.now(),
            )
            db.add(sync_log)
            db.commit()

            logger.info(
                f"Webhook处理完成: config_id={config_id}, "
                f"事件={event_type}, 处理数量={processed_count}"
            )

            return True, processed_count, message

    def _verify_webhook_signature(
        self,
        config: CmmsIntegrationConfig,
        payload: Dict[str, Any],
        signature: str,
    ) -> bool:
        """
        验证 Webhook 签名
        """
        try:
            auth_config = json.loads(config.auth_config) if config.auth_config else {}
        except (json.JSONDecodeError, TypeError):
            auth_config = {}

        secret = auth_config.get('webhook_secret')
        if not secret:
            return True

        try:
            payload_str = json.dumps(payload, separators=(',', ':'), sort_keys=True)
            expected = hashlib.sha256(f"{secret}{payload_str}".encode()).hexdigest()
            return signature == expected
        except Exception as e:
            logger.error(f"签名验证异常: {e}")
            return False

    def _update_work_order_from_webhook(
        self, db, config: CmmsIntegrationConfig, wo_data: Dict[str, Any]
    ) -> bool:
        """
        根据 Webhook 数据更新本地工单
        """
        try:
            external_id = str(wo_data.get('id') or wo_data.get('workOrderNo') or wo_data.get('order_no'))

            status_value = wo_data.get('status') or wo_data.get('statusCode')
            if not status_value:
                return False

            try:
                status_mapping = json.loads(config.status_mapping) if config.status_mapping else {}
            except (json.JSONDecodeError, TypeError):
                status_mapping = {}

            reverse_mapping = {v: k for k, v in status_mapping.items()}
            local_status = reverse_mapping.get(status_value, status_value.lower())

            valid_statuses = {'open', 'assigned', 'in_progress', 'resolved', 'closed',
                            'retested', 'pending_assignment'}
            if local_status not in valid_statuses:
                local_status = 'in_progress'

            wo = None
            if 'workOrderNo' in wo_data or 'order_no' in wo_data:
                order_no = wo_data.get('workOrderNo') or wo_data.get('order_no')
                wo = db.query(WorkOrder).filter(
                    WorkOrder.order_no == order_no
                ).first()

            if not wo and external_id:
                wo = db.query(WorkOrder).filter(
                    WorkOrder.extra_info.like(f'%{external_id}%')
                ).first()

            if wo:
                wo.status = local_status
                if local_status in ('resolved', 'closed', 'retested') and not wo.resolve_time:
                    wo.resolve_time = datetime.now()
                return True

            return False

        except Exception as e:
            logger.error(f"Webhook更新工单失败: {e}")
            return False

    # ---------- 同步日志 ----------

    def list_sync_logs(
        self,
        config_id: int = None,
        work_order_id: int = None,
        status: str = None,
        sync_direction: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[CmmsSyncLog], int]:
        """
        查询同步日志列表
        """
        with get_db() as db:
            if db is None:
                return [], 0

            query = db.query(CmmsSyncLog)

            if config_id:
                query = query.filter(CmmsSyncLog.config_id == config_id)
            if work_order_id:
                query = query.filter(CmmsSyncLog.work_order_id == work_order_id)
            if status:
                query = query.filter(CmmsSyncLog.status == status)
            if sync_direction:
                query = query.filter(CmmsSyncLog.sync_direction == sync_direction)
            if start_time:
                query = query.filter(CmmsSyncLog.sync_time >= start_time)
            if end_time:
                query = query.filter(CmmsSyncLog.sync_time <= end_time)

            total = query.count()
            logs = query.order_by(
                CmmsSyncLog.sync_time.desc()
            ).offset(offset).limit(limit).all()

            return logs, total

    def get_sync_log(self, log_id: int) -> Optional[CmmsSyncLog]:
        """
        获取同步日志详情
        """
        with get_db() as db:
            if db is None:
                return None
            return db.query(CmmsSyncLog).filter(
                CmmsSyncLog.id == log_id
            ).first()

    def retry_sync(self, log_id: int) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        重试失败的同步
        """
        with get_db() as db:
            if db is None:
                return False, None, "数据库不可用"

            log = db.query(CmmsSyncLog).filter(
                CmmsSyncLog.id == log_id
            ).first()
            if not log:
                return False, None, "同步日志不存在"

            config = db.query(CmmsIntegrationConfig).filter(
                CmmsIntegrationConfig.id == log.config_id
            ).first()
            if not config:
                return False, None, "CMMS配置不存在"

            wo = db.query(WorkOrder).filter(
                WorkOrder.id == log.work_order_id
            ).first()
            if not wo:
                return False, None, "工单不存在"

            log.retry_count = (log.retry_count or 0) + 1
            log.status = 'pending'
            db.commit()

            success, new_log_id, external_id, error = self._sync_to_single_config(
                wo, config, log.sync_type
            )

            return success, external_id, error
