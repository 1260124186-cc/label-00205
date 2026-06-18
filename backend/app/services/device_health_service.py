"""
采集器/传感器设备健康监控服务

监控采集器和传感器的运行健康状态，包括：
1. 心跳追踪：记录最后数据时间、预期采样间隔、连续缺失次数
2. 离线判定：超过 3× 采样间隔无数据判定为离线
3. 卡死判定：连续 N 次数值完全不变判定为卡死
4. 跳变判定：相邻采样值突变量超阈值，疑似接线故障
5. 设备异常不参与训练、降低预测置信度
6. 产生 device_fault 类告警（与预紧力预警区分）
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from loguru import logger

from app.utils.database import (
    get_db,
    CollectorHeartbeat,
    DeviceFaultAlert,
)
from app.utils.config import config


class DeviceFaultType(str, Enum):
    OFFLINE = "offline"
    STUCK = "stuck"
    JUMP = "jump"


class DeviceHealthStatus(str, Enum):
    HEALTHY = "healthy"
    OFFLINE = "offline"
    STUCK = "stuck"
    JUMP = "jump"
    DEGRADED = "degraded"


FAULT_LEVEL_MAP = {
    DeviceFaultType.OFFLINE: 3,
    DeviceFaultType.STUCK: 2,
    DeviceFaultType.JUMP: 2,
}

FAULT_LABEL_MAP = {
    DeviceFaultType.OFFLINE: "离线",
    DeviceFaultType.STUCK: "卡死",
    DeviceFaultType.JUMP: "跳变",
}

CONFIDENCE_PENALTY_MAP = {
    DeviceFaultType.OFFLINE: 0.3,
    DeviceFaultType.STUCK: 0.5,
    DeviceFaultType.JUMP: 0.6,
}

MULTI_FAULT_PENALTY = 0.2


class DeviceHealthService:
    """
    设备健康监控服务

    提供心跳更新、故障检测、置信度惩罚、训练排除等能力。
    """

    def __init__(self):
        dh_config = config.get('device_health', {})
        self.offline_threshold_multiplier = dh_config.get('offline_threshold_multiplier', 3)
        self.stuck_consecutive_threshold = dh_config.get('stuck_consecutive_threshold', 5)
        self.jump_threshold_ratio = dh_config.get('jump_threshold_ratio', 0.3)
        self.jump_min_absolute = dh_config.get('jump_min_absolute', 10.0)
        self.default_sampling_interval = dh_config.get('default_sampling_interval', 60.0)
        self.silence_minutes = dh_config.get('silence_minutes', 30)
        self.auto_resolve = dh_config.get('auto_resolve', True)
        logger.info("设备健康监控服务初始化完成")

    def record_heartbeat(
        self,
        collector_id: str,
        sensor_id: str,
        value: float,
        timestamp: Optional[datetime] = None,
        sampling_interval: Optional[float] = None,
        device_name: str = "",
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        记录采集器/传感器心跳数据

        每收到一条数据调用一次，更新心跳状态并检测故障。

        Args:
            collector_id: 采集器ID
            sensor_id: 传感器/螺栓ID
            value: 采样数值
            timestamp: 数据时间戳，默认当前时间
            sampling_interval: 采样间隔（秒），为空则沿用已有配置
            device_name: 设备名称
            tenant_id: 租户ID

        Returns:
            心跳更新结果，包含检测到的故障列表
        """
        if timestamp is None:
            timestamp = datetime.now()

        detected_faults: List[str] = []

        with get_db() as db:
            if db is None:
                return {'status': 'db_unavailable', 'faults': []}

            heartbeat = db.query(CollectorHeartbeat).filter(
                CollectorHeartbeat.collector_id == collector_id,
                CollectorHeartbeat.sensor_id == sensor_id,
            ).first()

            is_new = heartbeat is None
            previous_fault_types: Set[str] = set()

            if is_new:
                heartbeat = CollectorHeartbeat(
                    collector_id=collector_id,
                    sensor_id=sensor_id,
                    device_name=device_name,
                    expected_interval_seconds=sampling_interval or self.default_sampling_interval,
                    tenant_id=tenant_id,
                )
                db.add(heartbeat)
                db.flush()
            else:
                try:
                    previous_fault_types = set(json.loads(heartbeat.fault_types or '[]'))
                except (json.JSONDecodeError, TypeError):
                    previous_fault_types = set()

            if sampling_interval is not None:
                heartbeat.expected_interval_seconds = sampling_interval

            heartbeat.previous_value = heartbeat.last_value
            heartbeat.last_value = value
            heartbeat.last_data_time = timestamp
            heartbeat.consecutive_missing_count = 0

            if device_name:
                heartbeat.device_name = device_name
            if tenant_id is not None:
                heartbeat.tenant_id = tenant_id

            if not is_new and heartbeat.previous_value is not None:
                if self._detect_stuck(heartbeat, value):
                    detected_faults.append(DeviceFaultType.STUCK.value)
                else:
                    heartbeat.stuck_count = 0

                if self._detect_jump(heartbeat, value):
                    detected_faults.append(DeviceFaultType.JUMP.value)

            new_fault_types = set(detected_faults)

            if new_fault_types:
                self._apply_faults(heartbeat, new_fault_types, timestamp)
                for ft in new_faults - previous_fault_types:
                    self._create_device_fault_alert(
                        db, heartbeat, ft, value, timestamp, tenant_id
                    )
            else:
                if previous_fault_types and self.auto_resolve:
                    self._resolve_faults(heartbeat, timestamp)

            db.commit()

            result_heartbeat = db.query(CollectorHeartbeat).filter(
                CollectorHeartbeat.id == heartbeat.id
            ).first()

        return {
            'status': 'ok',
            'faults': detected_faults,
            'health_status': result_heartbeat.health_status if result_heartbeat else 'healthy',
            'confidence_penalty': result_heartbeat.confidence_penalty if result_heartbeat else 1.0,
            'excluded_from_training': result_heartbeat.excluded_from_training if result_heartbeat else False,
        }

    def check_offline_devices(self) -> List[Dict[str, Any]]:
        """
        批量检查所有设备的离线状态

        遍历心跳表，对 last_data_time 超过 3× 预期间隔的设备判定为离线。
        应由定时任务周期调用。

        Returns:
            检测到的离线设备列表
        """
        offline_devices = []
        now = datetime.now()

        with get_db() as db:
            if db is None:
                return []

            heartbeats = db.query(CollectorHeartbeat).filter(
                CollectorHeartbeat.health_status != DeviceHealthStatus.OFFLINE.value,
            ).all()

            for hb in heartbeats:
                if hb.last_data_time is None:
                    continue

                elapsed = (now - hb.last_data_time).total_seconds()
                threshold = hb.expected_interval_seconds * self.offline_threshold_multiplier

                if elapsed > threshold:
                    previous_fault_types: Set[str] = set()
                    try:
                        previous_fault_types = set(json.loads(hb.fault_types or '[]'))
                    except (json.JSONDecodeError, TypeError):
                        pass

                    hb.consecutive_missing_count = int(elapsed / hb.expected_interval_seconds)
                    new_fault_types = previous_fault_types | {DeviceFaultType.OFFLINE.value}

                    self._apply_faults(hb, new_fault_types, now)

                    if DeviceFaultType.OFFLINE.value not in previous_fault_types:
                        self._create_device_fault_alert(
                            db, hb, DeviceFaultType.OFFLINE.value,
                            hb.last_value, now, hb.tenant_id,
                            offline_duration_seconds=elapsed,
                        )

                    offline_devices.append({
                        'collector_id': hb.collector_id,
                        'sensor_id': hb.sensor_id,
                        'last_data_time': hb.last_data_time.isoformat() if hb.last_data_time else None,
                        'offline_duration_seconds': elapsed,
                        'expected_interval_seconds': hb.expected_interval_seconds,
                        'consecutive_missing_count': hb.consecutive_missing_count,
                    })

            if offline_devices:
                db.commit()

        if offline_devices:
            logger.warning(f"检测到 {len(offline_devices)} 个离线设备")

        return offline_devices

    def get_device_health(
        self,
        collector_id: Optional[str] = None,
        sensor_id: Optional[str] = None,
        health_status: Optional[str] = None,
        tenant_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        查询设备健康状态

        Args:
            collector_id: 采集器ID过滤
            sensor_id: 传感器ID过滤
            health_status: 健康状态过滤
            tenant_id: 租户ID过滤

        Returns:
            设备健康状态列表
        """
        with get_db() as db:
            if db is None:
                return []

            query = db.query(CollectorHeartbeat)

            if collector_id:
                query = query.filter(CollectorHeartbeat.collector_id == collector_id)
            if sensor_id:
                query = query.filter(CollectorHeartbeat.sensor_id == sensor_id)
            if health_status:
                query = query.filter(CollectorHeartbeat.health_status == health_status)
            if tenant_id is not None:
                query = query.filter(CollectorHeartbeat.tenant_id == tenant_id)

            results = query.order_by(CollectorHeartbeat.update_time.desc()).all()

            return [self._heartbeat_to_dict(hb) for hb in results]

    def get_faulty_sensor_ids(
        self,
        collector_id: Optional[str] = None,
        tenant_id: Optional[int] = None,
    ) -> Set[str]:
        """
        获取当前处于故障状态的传感器ID集合

        用于训练服务排除故障设备数据。

        Args:
            collector_id: 可选采集器ID过滤
            tenant_id: 租户ID过滤

        Returns:
            被排除的传感器ID集合
        """
        with get_db() as db:
            if db is None:
                return set()

            query = db.query(CollectorHeartbeat.sensor_id).filter(
                CollectorHeartbeat.excluded_from_training == True,
            )

            if collector_id:
                query = query.filter(CollectorHeartbeat.collector_id == collector_id)
            if tenant_id is not None:
                query = query.filter(CollectorHeartbeat.tenant_id == tenant_id)

            return {row.sensor_id for row in query.all()}

    def get_confidence_penalty(
        self,
        sensor_id: str,
        collector_id: Optional[str] = None,
    ) -> float:
        """
        获取指定传感器的置信度惩罚系数

        用于预测服务降低故障设备的预测置信度。
        系数范围 0-1，1.0 表示无惩罚。

        Args:
            sensor_id: 传感器ID
            collector_id: 可选采集器ID

        Returns:
            置信度惩罚系数
        """
        with get_db() as db:
            if db is None:
                return 1.0

            query = db.query(CollectorHeartbeat.confidence_penalty).filter(
                CollectorHeartbeat.sensor_id == sensor_id,
            )

            if collector_id:
                query = query.filter(CollectorHeartbeat.collector_id == collector_id)

            result = query.first()
            return result.confidence_penalty if result else 1.0

    def handle_fault_alert(
        self,
        alert_id: int,
        action: str,
        handler_id: Optional[str] = None,
        handler_name: Optional[str] = None,
        handle_note: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        处理设备故障告警

        Args:
            alert_id: 告警ID
            action: 处理动作 acknowledged/resolved/ignored
            handler_id: 处理人ID
            handler_name: 处理人姓名
            handle_note: 处理备注

        Returns:
            更新后的告警信息
        """
        if action not in ('acknowledged', 'resolved', 'ignored'):
            raise ValueError(f"无效的处理动作: {action}")

        with get_db() as db:
            if db is None:
                return None

            alert = db.query(DeviceFaultAlert).filter(
                DeviceFaultAlert.id == alert_id
            ).first()
            if not alert:
                return None

            alert.status = action
            alert.handler_id = handler_id
            alert.handler_name = handler_name
            alert.handle_note = handle_note

            if action == 'resolved':
                alert.handle_time = datetime.now()

            if action in ('resolved', 'ignored'):
                heartbeat = db.query(CollectorHeartbeat).filter(
                    CollectorHeartbeat.collector_id == alert.collector_id,
                    CollectorHeartbeat.sensor_id == alert.sensor_id,
                ).first()

                if heartbeat:
                    try:
                        fault_types = set(json.loads(heartbeat.fault_types or '[]'))
                    except (json.JSONDecodeError, TypeError):
                        fault_types = set()

                    fault_types.discard(alert.fault_type)

                    if not fault_types:
                        self._resolve_faults(heartbeat, datetime.now())
                    else:
                        heartbeat.fault_types = json.dumps(list(fault_types))
                        heartbeat.health_status = DeviceHealthStatus.DEGRADED.value

            db.commit()

            return {
                'id': alert.id,
                'alert_no': alert.alert_no,
                'status': alert.status,
                'fault_type': alert.fault_type,
                'collector_id': alert.collector_id,
                'sensor_id': alert.sensor_id,
            }

    def list_fault_alerts(
        self,
        fault_type: Optional[str] = None,
        status: Optional[str] = None,
        collector_id: Optional[str] = None,
        sensor_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        查询设备故障告警列表

        Args:
            fault_type: 故障类型过滤
            status: 状态过滤
            collector_id: 采集器ID过滤
            sensor_id: 传感器ID过滤
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            告警列表
        """
        with get_db() as db:
            if db is None:
                return []

            query = db.query(DeviceFaultAlert)

            if fault_type:
                query = query.filter(DeviceFaultAlert.fault_type == fault_type)
            if status:
                query = query.filter(DeviceFaultAlert.status == status)
            if collector_id:
                query = query.filter(DeviceFaultAlert.collector_id == collector_id)
            if sensor_id:
                query = query.filter(DeviceFaultAlert.sensor_id == sensor_id)

            alerts = query.order_by(
                DeviceFaultAlert.create_time.desc()
            ).offset(offset).limit(limit).all()

            return [self._fault_alert_to_dict(a) for a in alerts]

    def register_device(
        self,
        collector_id: str,
        sensor_id: str,
        device_name: str = "",
        device_type: str = "collector",
        expected_interval_seconds: float = 60.0,
        tenant_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        注册设备到心跳监控

        Args:
            collector_id: 采集器ID
            sensor_id: 传感器/螺栓ID
            device_name: 设备名称
            device_type: 设备类型
            expected_interval_seconds: 预期采样间隔（秒）
            tenant_id: 租户ID

        Returns:
            注册结果
        """
        with get_db() as db:
            if db is None:
                return None

            existing = db.query(CollectorHeartbeat).filter(
                CollectorHeartbeat.collector_id == collector_id,
                CollectorHeartbeat.sensor_id == sensor_id,
            ).first()

            if existing:
                existing.expected_interval_seconds = expected_interval_seconds
                if device_name:
                    existing.device_name = device_name
                existing.device_type = device_type
                if tenant_id is not None:
                    existing.tenant_id = tenant_id
                db.commit()
                return self._heartbeat_to_dict(existing)

            heartbeat = CollectorHeartbeat(
                collector_id=collector_id,
                sensor_id=sensor_id,
                device_name=device_name,
                device_type=device_type,
                expected_interval_seconds=expected_interval_seconds,
                tenant_id=tenant_id,
            )
            db.add(heartbeat)
            db.commit()

            return self._heartbeat_to_dict(heartbeat)

    def _detect_stuck(self, heartbeat: CollectorHeartbeat, current_value: float) -> bool:
        """
        检测卡死：连续 N 次数值完全不变
        """
        if heartbeat.previous_value is not None and current_value == heartbeat.previous_value:
            heartbeat.stuck_count = (heartbeat.stuck_count or 0) + 1
        else:
            heartbeat.stuck_count = 0

        return heartbeat.stuck_count >= self.stuck_consecutive_threshold

    def _detect_jump(self, heartbeat: CollectorHeartbeat, current_value: float) -> bool:
        """
        检测跳变：相邻采样值突变量超阈值，疑似接线故障

        跳变判定同时检查：
        1. 相对跳变：|Δ| / |基准值| > jump_threshold_ratio
        2. 绝对跳变：|Δ| > jump_min_absolute
        满足任一即判定为跳变
        """
        if heartbeat.previous_value is None:
            return False

        delta = abs(current_value - heartbeat.previous_value)
        baseline = abs(heartbeat.previous_value) if heartbeat.previous_value != 0 else 1.0

        relative_jump = delta / baseline
        is_jump = relative_jump > self.jump_threshold_ratio or delta > self.jump_min_absolute

        if is_jump:
            heartbeat.jump_count = (heartbeat.jump_count or 0) + 1
        else:
            heartbeat.jump_count = max(0, (heartbeat.jump_count or 0) - 1)

        return is_jump and (heartbeat.jump_count or 0) >= 2

    def _apply_faults(
        self,
        heartbeat: CollectorHeartbeat,
        fault_types: Set[str],
        timestamp: datetime,
    ) -> None:
        """
        对心跳记录应用故障状态

        更新健康状态、置信度惩罚系数、训练排除标记。
        """
        heartbeat.fault_types = json.dumps(list(fault_types))
        heartbeat.last_fault_time = timestamp

        if DeviceFaultType.OFFLINE.value in fault_types:
            heartbeat.health_status = DeviceHealthStatus.OFFLINE.value
        elif len(fault_types) > 1:
            heartbeat.health_status = DeviceHealthStatus.DEGRADED.value
        elif DeviceFaultType.STUCK.value in fault_types:
            heartbeat.health_status = DeviceHealthStatus.STUCK.value
        elif DeviceFaultType.JUMP.value in fault_types:
            heartbeat.health_status = DeviceHealthStatus.JUMP.value
        else:
            heartbeat.health_status = DeviceHealthStatus.DEGRADED.value

        penalty = 1.0
        for ft in fault_types:
            ft_enum = DeviceFaultType(ft)
            penalty *= CONFIDENCE_PENALTY_MAP.get(ft_enum, 1.0)

        if len(fault_types) > 1:
            penalty *= MULTI_FAULT_PENALTY

        heartbeat.confidence_penalty = max(0.1, min(1.0, penalty))

        heartbeat.excluded_from_training = (
            DeviceFaultType.OFFLINE.value in fault_types
            or DeviceFaultType.STUCK.value in fault_types
        )

    def _resolve_faults(
        self,
        heartbeat: CollectorHeartbeat,
        timestamp: datetime,
    ) -> None:
        """
        恢复设备健康状态
        """
        heartbeat.health_status = DeviceHealthStatus.HEALTHY.value
        heartbeat.fault_types = '[]'
        heartbeat.recovery_time = timestamp
        heartbeat.confidence_penalty = 1.0
        heartbeat.excluded_from_training = False
        heartbeat.stuck_count = 0
        heartbeat.jump_count = 0

        logger.info(
            f"设备已恢复: {heartbeat.collector_id}/{heartbeat.sensor_id}"
        )

    def _create_device_fault_alert(
        self,
        db,
        heartbeat: CollectorHeartbeat,
        fault_type: str,
        value: float,
        timestamp: datetime,
        tenant_id: Optional[int] = None,
        offline_duration_seconds: Optional[float] = None,
    ) -> None:
        """
        创建 device_fault 类型告警

        与预紧力预警区分，告警编号前缀为 DEV。
        检查静默期，避免重复告警。
        """
        if self._is_in_silence_period(db, heartbeat.collector_id, heartbeat.sensor_id, fault_type):
            logger.debug(
                f"设备告警被静默期抑制: {heartbeat.collector_id}/{heartbeat.sensor_id} {fault_type}"
            )
            return

        alert_no = self._generate_alert_no()
        ft_enum = DeviceFaultType(fault_type)
        fault_level = FAULT_LEVEL_MAP.get(ft_enum, 2)
        fault_label = FAULT_LABEL_MAP.get(ft_enum, fault_type)

        title = f"[设备故障] {heartbeat.device_name or heartbeat.collector_id}/{heartbeat.sensor_id} {fault_label}"

        content_parts = [
            f"采集器: {heartbeat.collector_id}",
            f"传感器: {heartbeat.sensor_id}",
            f"故障类型: {fault_label}",
        ]

        evidence: Dict[str, Any] = {
            'collector_id': heartbeat.collector_id,
            'sensor_id': heartbeat.sensor_id,
            'fault_type': fault_type,
            'last_value': value,
            'previous_value': heartbeat.previous_value,
            'expected_interval': heartbeat.expected_interval_seconds,
            'last_data_time': heartbeat.last_data_time.isoformat() if heartbeat.last_data_time else None,
        }

        if fault_type == DeviceFaultType.OFFLINE.value:
            duration = offline_duration_seconds or 0
            content_parts.append(f"离线时长: {duration:.0f}秒")
            content_parts.append(f"连续缺失: {heartbeat.consecutive_missing_count}次")
            evidence['offline_duration_seconds'] = duration
            evidence['consecutive_missing_count'] = heartbeat.consecutive_missing_count
        elif fault_type == DeviceFaultType.STUCK.value:
            content_parts.append(f"连续不变次数: {heartbeat.stuck_count}")
            evidence['stuck_count'] = heartbeat.stuck_count
        elif fault_type == DeviceFaultType.JUMP.value:
            delta = abs(value - (heartbeat.previous_value or 0))
            content_parts.append(f"跳变幅度: {delta:.2f}")
            evidence['jump_magnitude'] = delta
            evidence['jump_count'] = heartbeat.jump_count

        content_parts.append("注意: 此为设备故障告警，与预紧力预警不同")

        alert = DeviceFaultAlert(
            alert_no=alert_no,
            collector_id=heartbeat.collector_id,
            sensor_id=heartbeat.sensor_id,
            fault_type=fault_type,
            fault_level=fault_level,
            title=title,
            content='\n'.join(content_parts),
            evidence=json.dumps(evidence, ensure_ascii=False),
            last_value=value,
            stuck_count=heartbeat.stuck_count,
            silence_until=datetime.now() + timedelta(minutes=self.silence_minutes),
            tenant_id=tenant_id or heartbeat.tenant_id,
        )

        if fault_type == DeviceFaultType.OFFLINE.value:
            alert.offline_duration_seconds = offline_duration_seconds
            alert.consecutive_missing = heartbeat.consecutive_missing_count
        elif fault_type == DeviceFaultType.JUMP.value and heartbeat.previous_value is not None:
            alert.jump_magnitude = abs(value - heartbeat.previous_value)

        db.add(alert)
        db.flush()

        logger.warning(
            f"设备故障告警已创建: {alert_no}, "
            f"type={fault_type}, "
            f"device={heartbeat.collector_id}/{heartbeat.sensor_id}"
        )

        try:
            from app.services.alert import NotificationService
            notif_service = NotificationService()
            notif_service.dispatch_alert_notifications(alert)
        except Exception as e:
            logger.error(f"发送设备故障告警通知失败: {e}")

    def _is_in_silence_period(
        self,
        db,
        collector_id: str,
        sensor_id: str,
        fault_type: str,
    ) -> bool:
        """
        检查同设备同类型告警是否在静默期内
        """
        if self.silence_minutes <= 0:
            return False

        cutoff = datetime.now() - timedelta(minutes=self.silence_minutes)

        existing = db.query(DeviceFaultAlert).filter(
            DeviceFaultAlert.collector_id == collector_id,
            DeviceFaultAlert.sensor_id == sensor_id,
            DeviceFaultAlert.fault_type == fault_type,
            DeviceFaultAlert.create_time >= cutoff,
            DeviceFaultAlert.status.in_(['pending', 'acknowledged']),
        ).first()

        return existing is not None

    def _generate_alert_no(self) -> str:
        """生成唯一告警编号（DEV前缀与预紧力ALT前缀区分）"""
        now = datetime.now()
        prefix = now.strftime('DEV%Y%m%d%H%M%S')
        short_uuid = uuid.uuid4().hex[:6]
        return f"{prefix}{short_uuid}"

    def _heartbeat_to_dict(self, hb: CollectorHeartbeat) -> Dict[str, Any]:
        """心跳记录转字典"""
        return {
            'id': hb.id,
            'collector_id': hb.collector_id,
            'sensor_id': hb.sensor_id,
            'device_type': hb.device_type,
            'device_name': hb.device_name,
            'last_data_time': hb.last_data_time.isoformat() if hb.last_data_time else None,
            'expected_interval_seconds': hb.expected_interval_seconds,
            'consecutive_missing_count': hb.consecutive_missing_count,
            'last_value': hb.last_value,
            'previous_value': hb.previous_value,
            'stuck_count': hb.stuck_count,
            'jump_count': hb.jump_count,
            'health_status': hb.health_status,
            'fault_types': hb.fault_types,
            'last_fault_time': hb.last_fault_time.isoformat() if hb.last_fault_time else None,
            'recovery_time': hb.recovery_time.isoformat() if hb.recovery_time else None,
            'confidence_penalty': hb.confidence_penalty,
            'excluded_from_training': hb.excluded_from_training,
            'tenant_id': hb.tenant_id,
            'create_time': hb.create_time.isoformat() if hb.create_time else None,
            'update_time': hb.update_time.isoformat() if hb.update_time else None,
        }

    def _fault_alert_to_dict(self, alert: DeviceFaultAlert) -> Dict[str, Any]:
        """设备故障告警转字典"""
        return {
            'id': alert.id,
            'alert_no': alert.alert_no,
            'collector_id': alert.collector_id,
            'sensor_id': alert.sensor_id,
            'fault_type': alert.fault_type,
            'fault_level': alert.fault_level,
            'title': alert.title,
            'content': alert.content,
            'evidence': alert.evidence,
            'last_value': alert.last_value,
            'offline_duration_seconds': alert.offline_duration_seconds,
            'consecutive_missing': alert.consecutive_missing,
            'stuck_count': alert.stuck_count,
            'jump_magnitude': alert.jump_magnitude,
            'status': alert.status,
            'handler_id': alert.handler_id,
            'handler_name': alert.handler_name,
            'handle_time': alert.handle_time.isoformat() if alert.handle_time else None,
            'handle_note': alert.handle_note,
            'is_auto_resolved': alert.is_auto_resolved,
            'tenant_id': alert.tenant_id,
            'create_time': alert.create_time.isoformat() if alert.create_time else None,
        }


_device_health_service: Optional[DeviceHealthService] = None


def get_device_health_service() -> DeviceHealthService:
    """获取设备健康监控服务单例"""
    global _device_health_service
    if _device_health_service is None:
        _device_health_service = DeviceHealthService()
    return _device_health_service
