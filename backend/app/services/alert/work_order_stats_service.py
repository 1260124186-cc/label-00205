"""
工单统计指标服务模块

负责计算和提供工单相关统计指标：MTTR、误报率、重复故障率等。

主要功能:
- calculate_work_order_stats: 计算工单统计指标
- calculate_mttr: 计算平均修复时间 MTTR
- calculate_false_positive_rate: 计算误报率
- calculate_recurrence_rate: 计算重复故障率
- get_mttr_trend: 获取 MTTR 趋势
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from loguru import logger
from sqlalchemy import func, and_

from app.utils.database import (
    get_db,
    WorkOrder,
    WorkOrderPredictionCompare,
    WorkOrderRetestRecord,
)


class WorkOrderStatsService:
    """
    工单统计指标服务类
    """

    CLOSED_STATUSES = ('closed', 'resolved', 'retested')

    def __init__(self):
        logger.info("工单统计服务初始化完成")

    def calculate_stats(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        node_type: str = None,
        priority: str = None,
    ) -> Dict[str, Any]:
        """
        计算工单统计指标

        Args:
            start_time: 统计开始时间
            end_time: 统计结束时间
            node_type: 节点类型
            priority: 优先级

        Returns:
            统计指标字典
        """
        with get_db() as db:
            if db is None:
                return {}

            query = db.query(WorkOrder)

            if start_time:
                query = query.filter(WorkOrder.create_time >= start_time)
            if end_time:
                query = query.filter(WorkOrder.create_time <= end_time)
            if node_type:
                query = query.filter(WorkOrder.node_type == node_type)
            if priority:
                query = query.filter(WorkOrder.priority == priority)

            total_work_orders = query.count()

            status_distribution = {}
            for status in ['pending_assignment', 'open', 'assigned', 'in_progress',
                           'retested', 'resolved', 'closed']:
                count = query.filter(WorkOrder.status == status).count()
                if count > 0:
                    status_distribution[status] = count

            priority_distribution = {}
            for prio in ['low', 'medium', 'high', 'urgent']:
                count = query.filter(WorkOrder.priority == prio).count()
                if count > 0:
                    priority_distribution[prio] = count

            open_work_orders = query.filter(
                WorkOrder.status.in_(['open', 'pending_assignment', 'assigned'])
            ).count()

            in_progress_work_orders = query.filter(
                WorkOrder.status == 'in_progress'
            ).count()

            closed_query = query.filter(
                WorkOrder.status.in_(self.CLOSED_STATUSES)
            )
            closed_work_orders = closed_query.count()

            mttr_hours = self._calculate_mttr(db, start_time, end_time, node_type, priority)

            avg_resolve_hours = mttr_hours

            on_time_completion_rate = self._calculate_on_time_rate(
                db, start_time, end_time, node_type, priority
            )

            false_positive_count, false_positive_rate = self._calculate_false_positive_rate(
                db, start_time, end_time, node_type
            )

            recurrence_count, recurrence_rate = self._calculate_recurrence_rate(
                db, start_time, end_time, node_type
            )

            result = {
                'total_work_orders': total_work_orders,
                'closed_work_orders': closed_work_orders,
                'open_work_orders': open_work_orders,
                'in_progress_work_orders': in_progress_work_orders,
                'mttr_hours': mttr_hours,
                'mttr_minutes': mttr_hours * 60 if mttr_hours is not None else None,
                'false_positive_rate': false_positive_rate,
                'false_positive_count': false_positive_count,
                'recurrence_rate': recurrence_rate,
                'recurrence_count': recurrence_count,
                'avg_resolve_hours': avg_resolve_hours,
                'on_time_completion_rate': on_time_completion_rate,
                'priority_distribution': priority_distribution,
                'status_distribution': status_distribution,
                'time_range': {
                    'start_time': start_time.isoformat() if start_time else None,
                    'end_time': end_time.isoformat() if end_time else None,
                },
            }

            logger.info(
                f"工单统计计算完成: 总工单={total_work_orders}, "
                f"已关闭={closed_work_orders}, MTTR={mttr_hours}h, "
                f"误报率={false_positive_rate}, 重复故障率={recurrence_rate}"
            )

            return result

    def _calculate_mttr(
        self, db,
        start_time: datetime = None,
        end_time: datetime = None,
        node_type: str = None,
        priority: str = None,
    ) -> Optional[float]:
        """
        计算平均修复时间 MTTR (Mean Time To Repair)

        MTTR = 总修复时间 / 已修复工单数

        Args:
            db: 数据库会话
            start_time: 开始时间
            end_time: 结束时间
            node_type: 节点类型
            priority: 优先级

        Returns:
            MTTR 小时数
        """
        try:
            query = db.query(WorkOrder).filter(
                WorkOrder.status.in_(self.CLOSED_STATUSES),
                WorkOrder.resolve_time.isnot(None),
            )

            if start_time:
                query = query.filter(WorkOrder.create_time >= start_time)
            if end_time:
                query = query.filter(WorkOrder.create_time <= end_time)
            if node_type:
                query = query.filter(WorkOrder.node_type == node_type)
            if priority:
                query = query.filter(WorkOrder.priority == priority)

            resolved_orders = query.all()

            if not resolved_orders:
                return None

            total_duration_hours = 0.0
            count = 0

            for wo in resolved_orders:
                if wo.create_time and wo.resolve_time:
                    duration = wo.resolve_time - wo.create_time
                    total_duration_hours += duration.total_seconds() / 3600.0
                    count += 1

            if count == 0:
                return None

            return round(total_duration_hours / count, 2)

        except Exception as e:
            logger.error(f"计算MTTR失败: {e}")
            return None

    def _calculate_false_positive_rate(
        self, db,
        start_time: datetime = None,
        end_time: datetime = None,
        node_type: str = None,
    ) -> tuple[int, Optional[float]]:
        """
        计算误报率

        误报率 = 误报工单数 / 已复测工单数

        Args:
            db: 数据库会话
            start_time: 开始时间
            end_time: 结束时间
            node_type: 节点类型

        Returns:
            (误报数量, 误报率)
        """
        try:
            compare_query = db.query(WorkOrderPredictionCompare)

            if start_time:
                compare_query = compare_query.filter(
                    WorkOrderPredictionCompare.create_time >= start_time
                )
            if end_time:
                compare_query = compare_query.filter(
                    WorkOrderPredictionCompare.create_time <= end_time
                )

            if node_type:
                compare_query = compare_query.join(
                    WorkOrder,
                    WorkOrderPredictionCompare.work_order_id == WorkOrder.id
                ).filter(WorkOrder.node_type == node_type)

            total_compared = compare_query.count()

            if total_compared == 0:
                return 0, None

            false_positive_query = compare_query.filter(
                WorkOrderPredictionCompare.is_false_positive == True
            )
            false_positive_count = false_positive_query.count()

            false_positive_rate = round(false_positive_count / total_compared, 4)

            return false_positive_count, false_positive_rate

        except Exception as e:
            logger.error(f"计算误报率失败: {e}")
            return 0, None

    def _calculate_recurrence_rate(
        self, db,
        start_time: datetime = None,
        end_time: datetime = None,
        node_type: str = None,
    ) -> tuple[int, Optional[float]]:
        """
        计算重复故障率

        重复故障率 = 重复故障工单数 / 总工单数

        Args:
            db: 数据库会话
            start_time: 开始时间
            end_time: 结束时间
            node_type: 节点类型

        Returns:
            (重复故障数量, 重复故障率)
        """
        try:
            compare_query = db.query(WorkOrderPredictionCompare)

            if start_time:
                compare_query = compare_query.filter(
                    WorkOrderPredictionCompare.create_time >= start_time
                )
            if end_time:
                compare_query = compare_query.filter(
                    WorkOrderPredictionCompare.create_time <= end_time
                )

            if node_type:
                compare_query = compare_query.join(
                    WorkOrder,
                    WorkOrderPredictionCompare.work_order_id == WorkOrder.id
                ).filter(WorkOrder.node_type == node_type)

            total_compared = compare_query.count()

            if total_compared == 0:
                return 0, None

            recurring_query = compare_query.filter(
                WorkOrderPredictionCompare.is_recurring == True
            )
            recurrence_count = recurring_query.count()

            recurrence_rate = round(recurrence_count / total_compared, 4)

            return recurrence_count, recurrence_rate

        except Exception as e:
            logger.error(f"计算重复故障率失败: {e}")
            return 0, None

    def _calculate_on_time_rate(
        self, db,
        start_time: datetime = None,
        end_time: datetime = None,
        node_type: str = None,
        priority: str = None,
    ) -> Optional[float]:
        """
        计算按时完成率

        按时完成率 = 截止时间前完成的工单数 / 已完成工单数

        Args:
            db: 数据库会话
            start_time: 开始时间
            end_time: 结束时间
            node_type: 节点类型
            priority: 优先级

        Returns:
            按时完成率
        """
        try:
            query = db.query(WorkOrder).filter(
                WorkOrder.status.in_(self.CLOSED_STATUSES),
                WorkOrder.resolve_time.isnot(None),
                WorkOrder.due_time.isnot(None),
            )

            if start_time:
                query = query.filter(WorkOrder.create_time >= start_time)
            if end_time:
                query = query.filter(WorkOrder.create_time <= end_time)
            if node_type:
                query = query.filter(WorkOrder.node_type == node_type)
            if priority:
                query = query.filter(WorkOrder.priority == priority)

            total = query.count()

            if total == 0:
                return None

            on_time_count = query.filter(
                WorkOrder.resolve_time <= WorkOrder.due_time
            ).count()

            return round(on_time_count / total, 4)

        except Exception as e:
            logger.error(f"计算按时完成率失败: {e}")
            return None

    def get_mttr_trend(
        self,
        days: int = 30,
        node_type: str = None,
        priority: str = None,
    ) -> Dict[str, Any]:
        """
        获取 MTTR 趋势（按天）

        Args:
            days: 统计天数
            node_type: 节点类型
            priority: 优先级

        Returns:
            MTTR 趋势数据
        """
        with get_db() as db:
            if db is None:
                return {'trend': [], 'overall_mttr_hours': None}

            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)

            trend = []
            total_mttr_sum = 0.0
            total_days_with_data = 0

            for i in range(days):
                day_start = start_time + timedelta(days=i)
                day_end = day_start + timedelta(days=1)
                date_str = day_start.strftime('%Y-%m-%d')

                day_mttr = self._calculate_daily_mttr(
                    db, day_start, day_end, node_type, priority
                )

                day_query = db.query(WorkOrder).filter(
                    WorkOrder.status.in_(self.CLOSED_STATUSES),
                    WorkOrder.resolve_time >= day_start,
                    WorkOrder.resolve_time < day_end,
                )
                if node_type:
                    day_query = day_query.filter(WorkOrder.node_type == node_type)
                if priority:
                    day_query = day_query.filter(WorkOrder.priority == priority)
                day_count = day_query.count()

                trend.append({
                    'date': date_str,
                    'mttr_hours': day_mttr,
                    'work_order_count': day_count,
                })

                if day_mttr is not None and day_count > 0:
                    total_mttr_sum += day_mttr
                    total_days_with_data += 1

            overall_mttr = (
                round(total_mttr_sum / total_days_with_data, 2)
                if total_days_with_data > 0
                else None
            )

            return {
                'trend': trend,
                'overall_mttr_hours': overall_mttr,
            }

    def _calculate_daily_mttr(
        self, db,
        day_start: datetime,
        day_end: datetime,
        node_type: str = None,
        priority: str = None,
    ) -> Optional[float]:
        """
        计算单日 MTTR

        Args:
            db: 数据库会话
            day_start: 当天开始时间
            day_end: 当天结束时间
            node_type: 节点类型
            priority: 优先级

        Returns:
            单日 MTTR 小时数
        """
        try:
            query = db.query(WorkOrder).filter(
                WorkOrder.status.in_(self.CLOSED_STATUSES),
                WorkOrder.resolve_time >= day_start,
                WorkOrder.resolve_time < day_end,
            )

            if node_type:
                query = query.filter(WorkOrder.node_type == node_type)
            if priority:
                query = query.filter(WorkOrder.priority == priority)

            resolved_orders = query.all()

            if not resolved_orders:
                return None

            total_duration = 0.0
            count = 0

            for wo in resolved_orders:
                if wo.create_time and wo.resolve_time:
                    duration = wo.resolve_time - wo.create_time
                    total_duration += duration.total_seconds() / 3600.0
                    count += 1

            if count == 0:
                return None

            return round(total_duration / count, 2)

        except Exception as e:
            logger.error(f"计算单日MTTR失败: {e}")
            return None

    def get_false_positive_trend(
        self,
        days: int = 30,
        node_type: str = None,
    ) -> List[Dict[str, Any]]:
        """
        获取误报率趋势

        Args:
            days: 统计天数
            node_type: 节点类型

        Returns:
            误报率趋势列表
        """
        with get_db() as db:
            if db is None:
                return []

            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            trend = []

            for i in range(days):
                day_start = start_time + timedelta(days=i)
                day_end = day_start + timedelta(days=1)
                date_str = day_start.strftime('%Y-%m-%d')

                fp_count, fp_rate = self._calculate_daily_false_positive(
                    db, day_start, day_end, node_type
                )

                trend.append({
                    'date': date_str,
                    'false_positive_count': fp_count,
                    'false_positive_rate': fp_rate,
                })

            return trend

    def _calculate_daily_false_positive(
        self, db,
        day_start: datetime,
        day_end: datetime,
        node_type: str = None,
    ) -> tuple[int, Optional[float]]:
        """
        计算单日误报率
        """
        try:
            query = db.query(WorkOrderPredictionCompare).filter(
                WorkOrderPredictionCompare.create_time >= day_start,
                WorkOrderPredictionCompare.create_time < day_end,
            )

            if node_type:
                query = query.join(
                    WorkOrder,
                    WorkOrderPredictionCompare.work_order_id == WorkOrder.id
                ).filter(WorkOrder.node_type == node_type)

            total = query.count()
            if total == 0:
                return 0, None

            fp_count = query.filter(
                WorkOrderPredictionCompare.is_false_positive == True
            ).count()

            return fp_count, round(fp_count / total, 4)

        except Exception as e:
            logger.error(f"计算单日误报率失败: {e}")
            return 0, None
