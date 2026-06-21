"""
维护窗口服务模块

负责维护窗口的CRUD、提前结束、延期、以及告警静默匹配检查。

主要功能:
- create_window: 创建维护窗口
- get_window: 查询单个维护窗口
- list_windows: 查询维护窗口列表
- update_window: 更新维护窗口
- delete_window: 删除维护窗口
- end_window: 提前结束维护窗口
- extend_window: 延期维护窗口
- check_maintenance_suppression: 检查节点是否在维护窗口内（告警静默用）
- refresh_window_status: 刷新维护窗口状态（pending→active→ended）
"""

import json
import uuid
from datetime import datetime
from typing import List, Optional, Tuple
from loguru import logger
from sqlalchemy import and_, or_

from app.utils.database import get_db, MaintenanceWindow


def _generate_window_no() -> str:
    """生成维护窗口编号 MW+时间戳+随机串"""
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    rand = uuid.uuid4().hex[:6].upper()
    return f"MW{ts}{rand}"


def _parse_node_ids(node_ids_text: Optional[str]) -> List[str]:
    """解析 node_ids JSON 字段"""
    if not node_ids_text:
        return []
    try:
        data = json.loads(node_ids_text)
        if isinstance(data, list):
            return [str(x) for x in data]
        return []
    except (json.JSONDecodeError, TypeError):
        return []


def _serialize_node_ids(node_ids: Optional[List[str]]) -> Optional[str]:
    """序列化 node_ids 列表为 JSON"""
    if node_ids is None:
        return None
    return json.dumps(node_ids, ensure_ascii=False)


class MaintenanceWindowService:
    """维护窗口服务类"""

    def __init__(self):
        logger.info("维护窗口服务初始化完成")

    # ---------- 内部工具方法 ----------

    def _refresh_status_if_needed(self, window: MaintenanceWindow, now: datetime) -> bool:
        """
        根据时间刷新窗口状态，返回是否发生变化

        状态流转:
        - pending + start_time <= now <= end_time → active
        - active + now > end_time → ended
        - pending + now > end_time → ended
        """
        changed = False
        if window.status == 'pending' and window.start_time <= now:
            if now <= window.end_time:
                window.status = 'active'
                changed = True
                logger.info(f"维护窗口自动激活: {window.window_no}")
            else:
                window.status = 'ended'
                window.actual_end_time = window.end_time
                changed = True
                logger.info(f"维护窗口自动结束(从未开始): {window.window_no}")
        elif window.status == 'active' and now > window.end_time:
            window.status = 'ended'
            window.actual_end_time = window.end_time
            changed = True
            logger.info(f"维护窗口自动结束: {window.window_no}")
        return changed

    def _match_scope(
        self,
        window: MaintenanceWindow,
        node_type: str,
        node_id: str,
        device_id: Optional[str] = None,
    ) -> bool:
        """
        检查维护窗口的作用范围是否匹配目标节点

        匹配规则:
        - device 级: 匹配 window.device_id == device_id
        - flange 级: 匹配 window.node_type == 'flange' 且 node_id 在 window.node_ids 中
        - bolt 级: 匹配 window.node_type == 'bolt' 且 node_id 在 window.node_ids 中
        """
        scope = window.node_scope
        if scope == 'device':
            if not window.device_id or not device_id:
                return False
            return window.device_id == device_id
        elif scope in ('flange', 'bolt'):
            if window.node_type and window.node_type != node_type:
                return False
            ids = _parse_node_ids(window.node_ids)
            if not ids:
                return False
            return str(node_id) in ids
        return False

    # ---------- CRUD ----------

    def create_window(
        self,
        window_name: str,
        node_scope: str,
        start_time: datetime,
        end_time: datetime,
        window_type: str = 'planned',
        suppress_level: str = 'all',
        node_type: Optional[str] = None,
        node_ids: Optional[List[str]] = None,
        device_id: Optional[str] = None,
        reason: Optional[str] = None,
        operator_id: Optional[str] = None,
        operator_name: Optional[str] = None,
        extra_info: Optional[dict] = None,
        tenant_id: Optional[int] = None,
    ) -> MaintenanceWindow:
        """创建维护窗口"""
        if start_time >= end_time:
            raise ValueError("开始时间必须早于结束时间")
        if node_scope not in ('device', 'flange', 'bolt'):
            raise ValueError("node_scope 必须是 device/flange/bolt")
        if window_type not in ('planned', 'temporary'):
            raise ValueError("window_type 必须是 planned/temporary")
        if suppress_level not in ('all', 'non_emergency'):
            raise ValueError("suppress_level 必须是 all/non_emergency")

        with get_db() as db:
            if db is None:
                raise RuntimeError("数据库不可用")

            now = datetime.now()
            status = 'pending'
            if start_time <= now <= end_time:
                status = 'active'
            elif now > end_time:
                status = 'ended'

            window = MaintenanceWindow(
                window_no=_generate_window_no(),
                window_name=window_name,
                node_scope=node_scope,
                node_type=node_type,
                node_ids=_serialize_node_ids(node_ids),
                device_id=device_id,
                start_time=start_time,
                end_time=end_time,
                actual_end_time=end_time if status == 'ended' else None,
                window_type=window_type,
                suppress_level=suppress_level,
                status=status,
                reason=reason,
                operator_id=operator_id,
                operator_name=operator_name,
                suppressed_count=0,
                extra_info=json.dumps(extra_info, ensure_ascii=False) if extra_info else None,
                tenant_id=tenant_id,
            )
            db.add(window)
            db.commit()
            db.refresh(window)
            logger.info(
                f"维护窗口已创建: {window.window_no}, scope={node_scope}, "
                f"type={window_type}, status={status}"
            )
            return window

    def get_window(self, window_id: int) -> Optional[MaintenanceWindow]:
        """根据ID查询维护窗口"""
        with get_db() as db:
            if db is None:
                return None
            window = db.query(MaintenanceWindow).filter(
                MaintenanceWindow.id == window_id
            ).first()
            if window:
                self._refresh_status_if_needed(window, datetime.now())
                db.commit()
                db.refresh(window)
            return window

    def list_windows(
        self,
        status: Optional[str] = None,
        node_scope: Optional[str] = None,
        window_type: Optional[str] = None,
        device_id: Optional[str] = None,
        keyword: Optional[str] = None,
        start_from: Optional[datetime] = None,
        end_to: Optional[datetime] = None,
        tenant_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[int, List[MaintenanceWindow]]:
        """查询维护窗口列表（分页）"""
        with get_db() as db:
            if db is None:
                return 0, []

            now = datetime.now()
            query = db.query(MaintenanceWindow)

            if tenant_id is not None:
                query = query.filter(MaintenanceWindow.tenant_id == tenant_id)
            if status:
                query = query.filter(MaintenanceWindow.status == status)
            if node_scope:
                query = query.filter(MaintenanceWindow.node_scope == node_scope)
            if window_type:
                query = query.filter(MaintenanceWindow.window_type == window_type)
            if device_id:
                query = query.filter(MaintenanceWindow.device_id == device_id)
            if keyword:
                like = f"%{keyword}%"
                query = query.filter(or_(
                    MaintenanceWindow.window_name.like(like),
                    MaintenanceWindow.window_no.like(like),
                    MaintenanceWindow.reason.like(like),
                ))
            if start_from:
                query = query.filter(MaintenanceWindow.start_time >= start_from)
            if end_to:
                query = query.filter(MaintenanceWindow.end_time <= end_to)

            total = query.count()

            # 刷新状态（先查出来再刷新）
            all_items = query.order_by(
                MaintenanceWindow.create_time.desc()
            ).all()
            changed_any = False
            for w in all_items:
                if self._refresh_status_if_needed(w, now):
                    changed_any = True
            if changed_any:
                db.commit()
                for w in all_items:
                    db.refresh(w)

            # 再次按状态过滤（刷新后可能状态变化）
            if status:
                all_items = [w for w in all_items if w.status == status]
                total = len(all_items)

            start_idx = (page - 1) * page_size
            items = all_items[start_idx:start_idx + page_size]
            return total, items

    def update_window(
        self,
        window_id: int,
        **kwargs,
    ) -> Optional[MaintenanceWindow]:
        """更新维护窗口（仅允许 pending/active 状态）"""
        with get_db() as db:
            if db is None:
                return None
            window = db.query(MaintenanceWindow).filter(
                MaintenanceWindow.id == window_id
            ).first()
            if not window:
                return None
            if window.status not in ('pending', 'active'):
                raise ValueError(
                    f"仅 pending/active 状态的窗口可更新，当前状态: {window.status}"
                )

            now = datetime.now()
            self._refresh_status_if_needed(window, now)

            allowed_fields = {
                'window_name', 'node_scope', 'node_type', 'device_id',
                'start_time', 'end_time', 'window_type', 'suppress_level',
                'reason', 'operator_id', 'operator_name',
            }
            for key, value in kwargs.items():
                if key not in allowed_fields or value is None:
                    continue
                if key == 'node_ids':
                    setattr(window, key, _serialize_node_ids(value))
                else:
                    setattr(window, key, value)

            if 'node_ids' in kwargs and kwargs['node_ids'] is not None:
                window.node_ids = _serialize_node_ids(kwargs['node_ids'])
            if 'extra_info' in kwargs and kwargs['extra_info'] is not None:
                window.extra_info = json.dumps(kwargs['extra_info'], ensure_ascii=False)

            if 'start_time' in kwargs and kwargs['start_time'] is not None:
                if 'end_time' in kwargs and kwargs['end_time'] is not None:
                    if kwargs['start_time'] >= kwargs['end_time']:
                        raise ValueError("开始时间必须早于结束时间")
                elif kwargs['start_time'] >= window.end_time:
                    raise ValueError("开始时间必须早于结束时间")

            self._refresh_status_if_needed(window, now)
            db.commit()
            db.refresh(window)
            logger.info(f"维护窗口已更新: {window.window_no}")
            return window

    def delete_window(self, window_id: int) -> bool:
        """删除维护窗口（逻辑删除：状态置为 cancelled）"""
        with get_db() as db:
            if db is None:
                return False
            window = db.query(MaintenanceWindow).filter(
                MaintenanceWindow.id == window_id
            ).first()
            if not window:
                return False
            if window.status in ('ended', 'cancelled'):
                logger.warning(f"窗口已是终态，无需删除: {window.window_no}")
                return True
            window.status = 'cancelled'
            if not window.actual_end_time:
                window.actual_end_time = datetime.now()
            db.commit()
            logger.info(f"维护窗口已取消: {window.window_no}")
            return True

    # ---------- 提前结束与延期 ----------

    def end_window(
        self,
        window_id: int,
        operator_id: Optional[str] = None,
        operator_name: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Optional[MaintenanceWindow]:
        """
        提前结束维护窗口

        仅 pending/active 状态可提前结束
        """
        with get_db() as db:
            if db is None:
                return None
            window = db.query(MaintenanceWindow).filter(
                MaintenanceWindow.id == window_id
            ).first()
            if not window:
                return None
            if window.status not in ('pending', 'active'):
                raise ValueError(
                    f"仅 pending/active 状态可提前结束，当前状态: {window.status}"
                )

            now = datetime.now()
            window.status = 'ended'
            window.actual_end_time = now
            if operator_id:
                window.operator_id = operator_id
            if operator_name:
                window.operator_name = operator_name
            if reason:
                old_reason = window.reason or ''
                suffix = f"[提前结束] {reason}"
                window.reason = f"{old_reason}\n{suffix}".strip() if old_reason else suffix

            db.commit()
            db.refresh(window)
            logger.info(
                f"维护窗口提前结束: {window.window_no}, "
                f"operator={operator_name or operator_id}"
            )
            return window

    def extend_window(
        self,
        window_id: int,
        new_end_time: datetime,
        operator_id: Optional[str] = None,
        operator_name: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Optional[MaintenanceWindow]:
        """
        延期维护窗口（延长结束时间）

        仅 pending/active 状态可延期，且新结束时间必须晚于当前结束时间
        """
        with get_db() as db:
            if db is None:
                return None
            window = db.query(MaintenanceWindow).filter(
                MaintenanceWindow.id == window_id
            ).first()
            if not window:
                return None
            if window.status not in ('pending', 'active'):
                raise ValueError(
                    f"仅 pending/active 状态可延期，当前状态: {window.status}"
                )
            if new_end_time <= window.end_time:
                raise ValueError(
                    f"新结束时间必须晚于当前结束时间 {window.end_time}"
                )

            now = datetime.now()
            self._refresh_status_if_needed(window, now)

            old_end = window.end_time
            window.end_time = new_end_time
            if window.status == 'ended' and now <= new_end_time:
                window.status = 'active'
                window.actual_end_time = None
                logger.info(f"延期使窗口重新激活: {window.window_no}")
            if operator_id:
                window.operator_id = operator_id
            if operator_name:
                window.operator_name = operator_name
            if reason:
                old_reason = window.reason or ''
                suffix = f"[延期] 从 {old_end} 延至 {new_end_time}: {reason}"
                window.reason = f"{old_reason}\n{suffix}".strip() if old_reason else suffix

            db.commit()
            db.refresh(window)
            logger.info(
                f"维护窗口已延期: {window.window_no}, "
                f"原结束={old_end}, 新结束={new_end_time}"
            )
            return window

    # ---------- 告警静默匹配 ----------

    def check_maintenance_suppression(
        self,
        node_type: str,
        node_id: str,
        alert_level: int,
        device_id: Optional[str] = None,
        tenant_id: Optional[int] = None,
    ) -> Tuple[bool, Optional[MaintenanceWindow]]:
        """
        检查节点当前是否处于维护窗口内，决定是否静默告警

        Args:
            node_type: 节点类型 bolt/flange
            node_id: 节点ID
            alert_level: 告警级别 1-4
            device_id: 装置ID（用于 device 级窗口匹配）
            tenant_id: 租户ID

        Returns:
            (是否静默, 命中的维护窗口对象)
        """
        now = datetime.now()
        with get_db() as db:
            if db is None:
                return False, None

            query = db.query(MaintenanceWindow).filter(
                MaintenanceWindow.status == 'active',
                MaintenanceWindow.start_time <= now,
                MaintenanceWindow.end_time >= now,
            )
            if tenant_id is not None:
                query = query.filter(MaintenanceWindow.tenant_id == tenant_id)

            active_windows = query.all()

            for window in active_windows:
                if not self._match_scope(window, node_type, node_id, device_id):
                    continue

                if window.suppress_level == 'all':
                    # 增加静默计数
                    window.suppressed_count = (window.suppressed_count or 0) + 1
                    db.commit()
                    logger.info(
                        f"告警被维护窗口全部静默: window={window.window_no}, "
                        f"node={node_type}/{node_id}, level={alert_level}"
                    )
                    return True, window

                elif window.suppress_level == 'non_emergency':
                    # 级别1、2静默，级别3、4照常
                    if alert_level <= 2:
                        window.suppressed_count = (window.suppressed_count or 0) + 1
                        db.commit()
                        logger.info(
                            f"告警被维护窗口非紧急静默: window={window.window_no}, "
                            f"node={node_type}/{node_id}, level={alert_level}"
                        )
                        return True, window
                    else:
                        logger.info(
                            f"紧急告警不被维护窗口静默: window={window.window_no}, "
                            f"node={node_type}/{node_id}, level={alert_level}"
                        )
                        return False, window

            return False, None

    # ---------- 批量状态刷新 ----------

    def refresh_all_window_status(self) -> int:
        """
        刷新所有维护窗口状态（定时任务调用）

        Returns:
            状态发生变化的窗口数量
        """
        now = datetime.now()
        changed_count = 0
        with get_db() as db:
            if db is None:
                return 0
            windows = db.query(MaintenanceWindow).filter(
                MaintenanceWindow.status.in_(['pending', 'active'])
            ).all()
            for w in windows:
                if self._refresh_status_if_needed(w, now):
                    changed_count += 1
            if changed_count > 0:
                db.commit()
                logger.info(f"已刷新 {changed_count} 个维护窗口状态")
        return changed_count
