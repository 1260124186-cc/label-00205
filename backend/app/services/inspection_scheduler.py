"""
智能复检周期排程服务模块

综合健康度指数(HI)、剩余使用寿命(RUL)、最近预警频率、设备主数据中的法定检验周期，
计算 next_inspection_date。支持排程冲突检测、ICS/日历订阅导出、CMMS 系统推送。

核心功能:
1. IntelligentScheduler: 智能排程算法引擎（综合多因素）
2. ConflictDetector: 排程冲突检测器（班组任务量上限）
3. ICSExporter: ICS 日历文件生成器
4. CMMSPusher: CMMS/EAM 系统推送器
5. InspectionScheduleService: 对外服务门面
"""

import json
import uuid
import hashlib
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import numpy as np
import httpx

from app.utils.config import config
from app.utils.database import (
    get_db,
    WorkOrder,
    AlertEvent,
    BoltHealthHistory,
    FlangeHealthHistory,
    RULPrediction,
)


class InspectionPriority(Enum):
    """检验优先级枚举"""
    ROUTINE = "routine"
    ATTENTION = "attention"
    URGENT = "urgent"
    IMMEDIATE = "immediate"


class ScheduleStatus(Enum):
    """排程状态枚举"""
    PLANNED = "planned"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    CONFLICT = "conflict"


@dataclass
class DeviceMasterData:
    """设备主数据（含法定检验周期）"""
    node_id: str
    node_type: str
    device_name: str = ""
    location: str = ""
    legal_inspection_cycle_days: int = 365
    last_legal_inspection_date: Optional[datetime] = None
    manufacturer: str = ""
    model: str = ""
    installation_date: Optional[datetime] = None
    team_id: Optional[str] = None
    team_name: Optional[str] = None
    extra_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InspectionFactors:
    """排程计算输入因子"""
    hi_score: float
    hi_level: str
    rul_days: Optional[float]
    rul_confidence: Optional[float]
    recent_alert_count: int
    recent_alert_levels: List[int]
    device_data: DeviceMasterData
    last_inspection_date: Optional[datetime]
    historical_inspection_count: int = 0


@dataclass
class ScheduleCalculationResult:
    """排程计算结果"""
    node_id: str
    node_type: str
    next_inspection_date: datetime
    priority: InspectionPriority
    priority_score: float
    confidence: float
    base_cycle_days: float
    hi_adjustment_days: float
    rul_adjustment_days: float
    alert_adjustment_days: float
    legal_constraint_applied: bool
    reasoning: str
    factor_breakdown: Dict[str, Any]


@dataclass
class InspectionScheduleTask:
    """检验排程任务"""
    schedule_id: str
    node_id: str
    node_type: str
    device_name: str
    scheduled_date: datetime
    end_date: datetime
    priority: str
    priority_score: float
    status: str
    team_id: Optional[str]
    team_name: Optional[str]
    assignee_id: Optional[str]
    assignee_name: Optional[str]
    inspection_type: str
    title: str
    description: str
    estimated_hours: float
    standard_codes: List[str]
    prerequisites: List[str]
    conflict_detected: bool
    conflict_details: List[str]
    calculation_result: Optional[Dict[str, Any]]
    work_order_id: Optional[int]
    cmms_external_id: Optional[str]
    extra_info: Dict[str, Any]
    create_time: datetime
    update_time: datetime


@dataclass
class TeamCapacity:
    """班组产能配置"""
    team_id: str
    team_name: str
    daily_max_tasks: int = 5
    daily_max_hours: float = 40.0
    weekly_max_tasks: int = 25
    member_count: int = 5
    working_days: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    holidays: List[str] = field(default_factory=list)
    special_schedules: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConflictInfo:
    """冲突信息"""
    conflict_type: str
    severity: str
    team_id: str
    team_name: str
    date: datetime
    current_tasks: int
    max_tasks: int
    current_hours: float
    max_hours: float
    description: str
    suggestions: List[str]


class ScheduleWeights:
    """排程算法权重配置"""

    def __init__(self):
        schedule_config = config.get('inspection_schedule', {})
        self.hi_weight = schedule_config.get('hi_weight', 0.35)
        self.rul_weight = schedule_config.get('rul_weight', 0.30)
        self.alert_weight = schedule_config.get('alert_weight', 0.20)
        self.legal_weight = schedule_config.get('legal_weight', 0.15)

        self.hi_thresholds = schedule_config.get('hi_thresholds', {
            'excellent': 90,
            'good': 70,
            'fair': 50,
            'poor': 30,
        })

        self.cycle_adj_ratios = schedule_config.get('cycle_adj_ratios', {
            'hi_excellent': 1.3,
            'hi_good': 1.1,
            'hi_fair': 1.0,
            'hi_poor': 0.6,
            'hi_critical': 0.3,
            'rul_warning': 0.5,
            'rul_critical': 0.2,
            'alert_high_freq': 0.7,
        })

        self.min_cycle_days = schedule_config.get('min_cycle_days', 7)
        self.max_cycle_days = schedule_config.get('max_cycle_days', 730)
        self.urgent_days_threshold = schedule_config.get('urgent_days_threshold', 30)
        self.immediate_days_threshold = schedule_config.get('immediate_days_threshold', 7)

        self.alert_window_days = schedule_config.get('alert_window_days', 30)
        self.high_alert_threshold = schedule_config.get('high_alert_threshold', 5)


class IntelligentScheduler:
    """智能排程算法引擎"""

    def __init__(self):
        self.weights = ScheduleWeights()
        logger.info("智能排程算法引擎初始化完成")

    def calculate_next_inspection(
        self,
        factors: InspectionFactors,
        reference_date: Optional[datetime] = None,
    ) -> ScheduleCalculationResult:
        """
        综合多因素计算下次检验日期

        算法流程:
        1. 以法定检验周期为基础周期
        2. 根据 HI 健康度调整周期（健康好延长，差则缩短）
        3. 根据 RUL 剩余寿命调整（接近故障大幅提前）
        4. 根据近期预警频率调整（频繁预警则提前）
        5. 与法定周期下限进行约束比较
        6. 计算优先级和置信度

        Args:
            factors: 排程输入因子
            reference_date: 参考计算日期，默认当前时间

        Returns:
            ScheduleCalculationResult: 排程计算结果
        """
        reference_date = reference_date or datetime.now()

        device_data = factors.device_data
        last_inspection = factors.last_inspection_date or device_data.last_legal_inspection_date or reference_date

        base_cycle_days = float(device_data.legal_inspection_cycle_days)

        hi_adj_days = self._calculate_hi_adjustment(factors.hi_score, factors.hi_level, base_cycle_days)
        rul_adj_days = self._calculate_rul_adjustment(factors.rul_days, factors.rul_confidence, base_cycle_days)
        alert_adj_days = self._calculate_alert_adjustment(
            factors.recent_alert_count, factors.recent_alert_levels, base_cycle_days
        )

        weights = self.weights
        adjusted_cycle = (
            base_cycle_days
            + weights.hi_weight * hi_adj_days
            + weights.rul_weight * rul_adj_days
            + weights.alert_weight * alert_adj_days
        )

        adjusted_cycle = float(np.clip(
            adjusted_cycle,
            weights.min_cycle_days,
            weights.max_cycle_days,
        ))

        legal_deadline = self._calculate_legal_deadline(last_inspection, device_data.legal_inspection_cycle_days)
        preliminary_date = last_inspection + timedelta(days=adjusted_cycle)

        legal_constraint_applied = False
        if legal_deadline and preliminary_date > legal_deadline:
            final_date = legal_deadline
            legal_constraint_applied = True
        else:
            final_date = preliminary_date

        # RUL硬约束：检验必须在剩余寿命耗尽前完成（默认取RUL的70%作为安全裕度）
        if factors.rul_days is not None and factors.rul_days > 0:
            rul_confidence = factors.rul_confidence if factors.rul_confidence else 0.7
            safety_margin = 0.5 + 0.3 * rul_confidence  # 置信度越高，安全裕度越紧(0.5~0.8)
            rul_deadline = reference_date + timedelta(days=max(1, factors.rul_days * safety_margin))
            if final_date > rul_deadline:
                final_date = rul_deadline
                rul_adj_days = min(rul_adj_days, (rul_deadline - (last_inspection + timedelta(days=base_cycle_days))).days)

        if final_date < reference_date:
            final_date = reference_date + timedelta(days=1)

        priority, priority_score = self._determine_priority(
            factors.hi_score,
            factors.rul_days,
            factors.recent_alert_count,
            adjusted_cycle,
            (final_date - reference_date).days,
        )

        confidence = self._calculate_confidence(
            factors.hi_score,
            factors.rul_confidence,
            factors.recent_alert_count,
            factors.historical_inspection_count,
        )

        reasoning = self._generate_reasoning(
            factors,
            base_cycle_days,
            hi_adj_days,
            rul_adj_days,
            alert_adj_days,
            adjusted_cycle,
            legal_constraint_applied,
            priority,
            final_date,
        )

        factor_breakdown = {
            'base_cycle_days': base_cycle_days,
            'hi_score': factors.hi_score,
            'hi_level': factors.hi_level,
            'hi_adjustment_days': hi_adj_days,
            'rul_days': factors.rul_days,
            'rul_adjustment_days': rul_adj_days,
            'alert_count_30d': factors.recent_alert_count,
            'alert_adjustment_days': alert_adj_days,
            'weighted_cycle_days': adjusted_cycle,
            'legal_cycle_days': device_data.legal_inspection_cycle_days,
            'legal_constraint_applied': legal_constraint_applied,
        }

        return ScheduleCalculationResult(
            node_id=factors.device_data.node_id,
            node_type=factors.device_data.node_type,
            next_inspection_date=final_date,
            priority=priority,
            priority_score=priority_score,
            confidence=confidence,
            base_cycle_days=base_cycle_days,
            hi_adjustment_days=hi_adj_days,
            rul_adjustment_days=rul_adj_days,
            alert_adjustment_days=alert_adj_days,
            legal_constraint_applied=legal_constraint_applied,
            reasoning=reasoning,
            factor_breakdown=factor_breakdown,
        )

    def _calculate_hi_adjustment(
        self, hi_score: float, hi_level: str, base_cycle: float
    ) -> float:
        """根据 HI 健康度计算周期调整天数"""
        ratios = self.weights.cycle_adj_ratios
        thresholds = self.weights.hi_thresholds

        if hi_score >= thresholds['excellent']:
            ratio = ratios.get('hi_excellent', 1.3)
        elif hi_score >= thresholds['good']:
            ratio = ratios.get('hi_good', 1.1)
        elif hi_score >= thresholds['fair']:
            ratio = ratios.get('hi_fair', 1.0)
        elif hi_score >= thresholds['poor']:
            ratio = ratios.get('hi_poor', 0.6)
        else:
            ratio = ratios.get('hi_critical', 0.3)

        adjusted = base_cycle * ratio
        return adjusted - base_cycle

    def _calculate_rul_adjustment(
        self, rul_days: Optional[float], rul_confidence: Optional[float], base_cycle: float
    ) -> float:
        """根据 RUL 剩余使用寿命计算周期调整天数"""
        if rul_days is None or rul_days <= 0:
            return 0.0

        confidence_factor = rul_confidence if rul_confidence else 0.7
        ratios = self.weights.cycle_adj_ratios

        if rul_days <= self.weights.immediate_days_threshold:
            ratio = ratios.get('rul_critical', 0.2)
        elif rul_days <= self.weights.urgent_days_threshold:
            ratio = ratios.get('rul_warning', 0.5)
        elif rul_days <= base_cycle * 0.5:
            ratio = 0.7
        elif rul_days <= base_cycle:
            ratio = 0.9
        else:
            ratio = 1.05

        effective_ratio = 1.0 - confidence_factor * (1.0 - ratio)
        adjusted = base_cycle * effective_ratio
        return adjusted - base_cycle

    def _calculate_alert_adjustment(
        self, alert_count: int, alert_levels: List[int], base_cycle: float
    ) -> float:
        """根据近期预警频率计算周期调整天数"""
        if alert_count == 0:
            return base_cycle * 0.1

        ratios = self.weights.cycle_adj_ratios
        avg_level = float(np.mean(alert_levels)) if alert_levels else 1.0
        level_factor = (avg_level - 1.0) / 3.0
        level_factor = float(np.clip(level_factor, 0, 1))

        if alert_count >= self.weights.high_alert_threshold:
            base_ratio = ratios.get('alert_high_freq', 0.7)
        elif alert_count >= 3:
            base_ratio = 0.85
        elif alert_count >= 1:
            base_ratio = 0.95
        else:
            base_ratio = 1.0

        effective_ratio = base_ratio - level_factor * (1.0 - base_ratio) * 0.5
        adjusted = base_cycle * effective_ratio
        return adjusted - base_cycle

    def _calculate_legal_deadline(
        self, last_inspection: datetime, legal_cycle_days: int
    ) -> Optional[datetime]:
        """计算法定检验截止日期"""
        if last_inspection is None:
            return None
        return last_inspection + timedelta(days=legal_cycle_days)

    def _determine_priority(
        self,
        hi_score: float,
        rul_days: Optional[float],
        alert_count: int,
        adjusted_cycle: float,
        days_to_inspection: int,
    ) -> Tuple[InspectionPriority, float]:
        """确定检验优先级"""
        priority_score = 0.0

        if hi_score < 30:
            priority_score += 40
        elif hi_score < 50:
            priority_score += 25
        elif hi_score < 70:
            priority_score += 10
        else:
            priority_score += 0

        if rul_days is not None:
            if rul_days <= 7:
                priority_score += 35
            elif rul_days <= 30:
                priority_score += 20
            elif rul_days <= 90:
                priority_score += 10
            else:
                priority_score += 0

        if alert_count >= 10:
            priority_score += 25
        elif alert_count >= 5:
            priority_score += 15
        elif alert_count >= 2:
            priority_score += 8
        elif alert_count >= 1:
            priority_score += 3

        if days_to_inspection <= 3:
            priority_score += 20
        elif days_to_inspection <= 7:
            priority_score += 12
        elif days_to_inspection <= 14:
            priority_score += 6

        priority_score = float(np.clip(priority_score, 0, 100))

        if priority_score >= 70:
            priority = InspectionPriority.IMMEDIATE
        elif priority_score >= 50:
            priority = InspectionPriority.URGENT
        elif priority_score >= 25:
            priority = InspectionPriority.ATTENTION
        else:
            priority = InspectionPriority.ROUTINE

        return priority, priority_score

    def _calculate_confidence(
        self,
        hi_score: float,
        rul_confidence: Optional[float],
        alert_count: int,
        historical_count: int,
    ) -> float:
        """计算排程置信度"""
        conf = 0.5

        if rul_confidence is not None:
            conf += 0.3 * rul_confidence
        else:
            conf += 0.15

        if historical_count >= 10:
            conf += 0.1
        elif historical_count >= 3:
            conf += 0.05

        if alert_count > 0:
            conf += 0.05

        return float(np.clip(conf, 0.3, 0.98))

    def _generate_reasoning(
        self,
        factors: InspectionFactors,
        base_cycle: float,
        hi_adj: float,
        rul_adj: float,
        alert_adj: float,
        final_cycle: float,
        legal_applied: bool,
        priority: InspectionPriority,
        final_date: datetime,
    ) -> str:
        """生成排程决策解释文本"""
        parts = []

        parts.append(
            f"基础检验周期（法定）: {base_cycle:.0f}天，"
            f"上次检验: {factors.last_inspection_date.strftime('%Y-%m-%d') if factors.last_inspection_date else '无记录'}"
        )

        hi_level_cn = {
            'excellent': '优秀', 'good': '良好', 'fair': '一般',
            'poor': '较差', 'critical': '危险'
        }.get(factors.hi_level, factors.hi_level)
        parts.append(
            f"健康度HI: {factors.hi_score:.1f}({hi_level_cn})，"
            f"周期调整: {'缩短' if hi_adj < 0 else '延长'}{abs(hi_adj):.1f}天"
        )

        if factors.rul_days is not None:
            parts.append(
                f"预测RUL: {factors.rul_days:.1f}天，"
                f"周期调整: {'缩短' if rul_adj < 0 else '延长'}{abs(rul_adj):.1f}天"
            )
        else:
            parts.append("RUL数据不足，未参与调整")

        parts.append(
            f"近{self.weights.alert_window_days}天预警{factors.recent_alert_count}次，"
            f"周期调整: {'缩短' if alert_adj < 0 else '延长'}{abs(alert_adj):.1f}天"
        )

        if legal_applied:
            parts.append("已触发法定检验周期下限约束")

        priority_cn = {
            InspectionPriority.IMMEDIATE: '立即',
            InspectionPriority.URGENT: '紧急',
            InspectionPriority.ATTENTION: '关注',
            InspectionPriority.ROUTINE: '常规',
        }.get(priority, priority.value)

        parts.append(
            f"最终排程日期: {final_date.strftime('%Y-%m-%d')}，"
            f"优先级: {priority_cn}，"
            f"综合周期: {final_cycle:.1f}天"
        )

        return "；".join(parts)


class ConflictDetector:
    """排程冲突检测器"""

    def __init__(self):
        cd_config = config.get('conflict_detection', {})
        self.default_daily_max_tasks = cd_config.get('default_daily_max_tasks', 10)
        self.default_daily_max_hours = cd_config.get('default_daily_max_hours', 48.0)
        self.default_weekly_max_tasks = cd_config.get('default_weekly_max_tasks', 40)
        self.look_ahead_days = cd_config.get('look_ahead_days', 90)
        self.team_capacities: Dict[str, TeamCapacity] = {}
        logger.info("排程冲突检测器初始化完成")

    def register_team_capacity(self, capacity: TeamCapacity) -> None:
        """注册班组产能配置"""
        self.team_capacities[capacity.team_id] = capacity

    def get_team_capacity(self, team_id: str) -> TeamCapacity:
        """获取班组产能配置"""
        if team_id not in self.team_capacities:
            self.team_capacities[team_id] = TeamCapacity(
                team_id=team_id,
                team_name=f"班组_{team_id}",
                daily_max_tasks=self.default_daily_max_tasks,
                daily_max_hours=self.default_daily_max_hours,
                weekly_max_tasks=self.default_weekly_max_tasks,
            )
        return self.team_capacities[team_id]

    def _count_day_tasks(
        self,
        team_id: str,
        check_date: datetime,
        exclude_schedule_id: Optional[str] = None,
    ) -> Tuple[int, float]:
        """
        统计指定班组在指定日期的任务数和工时

        Args:
            team_id: 班组ID
            check_date: 检查日期
            exclude_schedule_id: 排除的排程ID（用于重新计算自身）

        Returns:
            (任务数, 总工时)
        """
        existing = self._load_tasks_for_date(team_id, check_date)
        day_start = check_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = 0
        hours = 0.0
        for t in existing:
            if exclude_schedule_id and hasattr(t, 'schedule_id') and t.schedule_id == exclude_schedule_id:
                continue
            t_start = t.scheduled_date if hasattr(t, 'scheduled_date') else (
                t.due_time if hasattr(t, 'due_time') else check_date
            )
            if day_start <= t_start < day_end:
                count += 1
                hours += float(getattr(t, 'estimated_hours', 4.0))
        return count, hours

    def _count_week_tasks(
        self,
        team_id: str,
        check_date: datetime,
    ) -> Tuple[int, float]:
        """
        统计指定班组在指定日期所在周的任务数和工时

        Returns:
            (本周任务数, 本周总工时)
        """
        weekday = check_date.weekday()
        week_start = (check_date - timedelta(days=weekday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        week_end = week_start + timedelta(days=7)
        total_count = 0
        total_hours = 0.0
        for i in range(7):
            d = week_start + timedelta(days=i)
            c, h = self._count_day_tasks(team_id, d)
            total_count += c
            total_hours += h
        return total_count, total_hours

    def detect_conflicts(
        self,
        team_id: str,
        proposed_date: datetime,
        proposed_hours: float = 4.0,
        existing_tasks: Optional[List[InspectionScheduleTask]] = None,
    ) -> Tuple[bool, List[ConflictInfo]]:
        """
        检测指定日期是否存在排程冲突

        Args:
            team_id: 班组ID
            proposed_date: 拟排程日期
            proposed_hours: 拟排程任务预估工时
            existing_tasks: 当日已有任务列表

        Returns:
            (是否有冲突, 冲突详情列表)
        """
        conflicts: List[ConflictInfo] = []
        capacity = self.get_team_capacity(team_id)

        if existing_tasks is None:
            existing_tasks = self._load_tasks_for_date(team_id, proposed_date)

        day_of_week = proposed_date.weekday()
        if day_of_week not in capacity.working_days:
            conflicts.append(ConflictInfo(
                conflict_type="non_working_day",
                severity="warning",
                team_id=team_id,
                team_name=capacity.team_name,
                date=proposed_date,
                current_tasks=len(existing_tasks),
                max_tasks=0,
                current_hours=sum(t.estimated_hours for t in existing_tasks),
                max_hours=0,
                description=f"{proposed_date.strftime('%Y-%m-%d')} 是非工作日（周{['一','二','三','四','五','六','日'][day_of_week]}）",
                suggestions=["建议调整至工作日", "如确需安排，请标记为加班任务"],
            ))
            return True, conflicts

        date_str = proposed_date.strftime('%Y-%m-%d')
        if date_str in capacity.holidays:
            conflicts.append(ConflictInfo(
                conflict_type="holiday",
                severity="warning",
                team_id=team_id,
                team_name=capacity.team_name,
                date=proposed_date,
                current_tasks=len(existing_tasks),
                max_tasks=0,
                current_hours=sum(t.estimated_hours for t in existing_tasks),
                max_hours=0,
                description=f"{date_str} 是节假日",
                suggestions=["建议调整至工作日", "如需安排需走加班审批流程"],
            ))
            return True, conflicts

        current_task_count = len(existing_tasks) + 1
        if current_task_count > capacity.daily_max_tasks:
            conflicts.append(ConflictInfo(
                conflict_type="daily_task_overflow",
                severity="error",
                team_id=team_id,
                team_name=capacity.team_name,
                date=proposed_date,
                current_tasks=current_task_count,
                max_tasks=capacity.daily_max_tasks,
                current_hours=sum(t.estimated_hours for t in existing_tasks) + proposed_hours,
                max_hours=capacity.daily_max_hours,
                description=(
                    f"日任务数超限：当前{current_task_count}个任务，"
                    f"上限{capacity.daily_max_tasks}个"
                ),
                suggestions=[
                    f"延期至次日（{self._find_next_available_date(team_id, proposed_date, proposed_hours)}）",
                    "拆分任务为多个子任务分散安排",
                    "协调其他班组支援",
                ],
            ))

        current_hours = sum(t.estimated_hours for t in existing_tasks) + proposed_hours
        if current_hours > capacity.daily_max_hours:
            conflicts.append(ConflictInfo(
                conflict_type="daily_hours_overflow",
                severity="error",
                team_id=team_id,
                team_name=capacity.team_name,
                date=proposed_date,
                current_tasks=current_task_count,
                max_tasks=capacity.daily_max_tasks,
                current_hours=current_hours,
                max_hours=capacity.daily_max_hours,
                description=(
                    f"日工时超限：当前{current_hours:.1f}小时，"
                    f"上限{capacity.daily_max_hours:.1f}小时"
                ),
                suggestions=[
                    f"延期至后续工时充足日期",
                    "减少任务预估工时或降低检验范围",
                    "协调其他班组分摊工作量",
                ],
            ))

        week_start = proposed_date - timedelta(days=day_of_week)
        week_tasks = self._count_weekly_tasks(team_id, week_start)
        if week_tasks + 1 > capacity.weekly_max_tasks:
            conflicts.append(ConflictInfo(
                conflict_type="weekly_task_overflow",
                severity="warning",
                team_id=team_id,
                team_name=capacity.team_name,
                date=proposed_date,
                current_tasks=week_tasks + 1,
                max_tasks=capacity.weekly_max_tasks,
                current_hours=current_hours,
                max_hours=capacity.daily_max_hours,
                description=(
                    f"本周任务数接近上限：已排{week_tasks}个，"
                    f"上限{capacity.weekly_max_tasks}个"
                ),
                suggestions=[
                    "考虑调整至下周",
                    "评估任务优先级，低优先级任务延后",
                ],
            ))

        has_conflicts = len(conflicts) > 0
        return has_conflicts, conflicts

    def batch_detect(
        self,
        schedule_tasks: List[InspectionScheduleTask],
    ) -> Dict[str, List[ConflictInfo]]:
        """批量检测多个排程任务的冲突"""
        results: Dict[str, List[ConflictInfo]] = {}
        team_date_tasks: Dict[Tuple[str, date], List[InspectionScheduleTask]] = {}

        for task in schedule_tasks:
            if not task.team_id:
                continue
            key = (task.team_id, task.scheduled_date.date())
            if key not in team_date_tasks:
                team_date_tasks[key] = []
            team_date_tasks[key].append(task)

        for task in schedule_tasks:
            if not task.team_id:
                results[task.schedule_id] = []
                continue
            key = (task.team_id, task.scheduled_date.date())
            other_tasks = [t for t in team_date_tasks[key] if t.schedule_id != task.schedule_id]
            has_conflict, conflicts = self.detect_conflicts(
                team_id=task.team_id,
                proposed_date=task.scheduled_date,
                proposed_hours=task.estimated_hours,
                existing_tasks=other_tasks,
            )
            results[task.schedule_id] = conflicts

        return results

    def _load_tasks_for_date(
        self, team_id: str, target_date: datetime
    ) -> List[InspectionScheduleTask]:
        """从数据库加载指定班组指定日期的任务（同时读WorkOrder和sc_inspection_schedules）"""
        tasks: List[InspectionScheduleTask] = []
        try:
            from app.utils.database import get_db, Base
            with get_db() as db:
                if db is None:
                    return tasks
                start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end = start + timedelta(days=1)

                # 1) 读WorkOrder表
                try:
                    wo_rows = db.query(WorkOrder).filter(
                        WorkOrder.assignee_id == str(team_id),
                        WorkOrder.due_time >= start,
                        WorkOrder.due_time < end,
                        WorkOrder.status.notin_(['closed', 'cancelled']),
                    ).all()
                    for row in wo_rows:
                        extra = {}
                        if row.extra_info:
                            try:
                                extra = json.loads(row.extra_info)
                            except (json.JSONDecodeError, TypeError):
                                pass
                        tasks.append(InspectionScheduleTask(
                            schedule_id=f"WO_{row.id}",
                            node_id=row.node_id or "",
                            node_type=row.node_type or "",
                            device_name="",
                            scheduled_date=row.due_time or start,
                            end_date=row.due_time or start,
                            priority=row.priority or "medium",
                            priority_score=0.0,
                            status=row.status or "open",
                            team_id=str(team_id),
                            team_name="",
                            assignee_id=row.assignee_id,
                            assignee_name=row.assignee_name,
                            inspection_type="work_order",
                            title=row.title or "",
                            description=row.description or "",
                            estimated_hours=float(extra.get('estimated_hours', 4.0)),
                            standard_codes=[],
                            prerequisites=[],
                            conflict_detected=False,
                            conflict_details=[],
                            calculation_result=None,
                            work_order_id=row.id,
                            cmms_external_id=None,
                            extra_info=extra,
                            create_time=row.create_time or datetime.now(),
                            update_time=row.update_time or datetime.now(),
                        ))
                except Exception as e:
                    logger.debug(f"读WorkOrder表失败(可接受): {e}")

                # 2) 读sc_inspection_schedules表（自身排程表）
                try:
                    sched_table = Base.classes.get('sc_inspection_schedules')
                    if sched_table is not None:
                        sched_rows = db.query(sched_table).filter(
                            sched_table.team_id == str(team_id),
                            sched_table.scheduled_date >= start,
                            sched_table.scheduled_date < end,
                            sched_table.status.notin_(['completed', 'cancelled']),
                        ).all()
                        for row in sched_rows:
                            try:
                                t = _row_to_schedule_task(row)
                                if t and t.schedule_id not in {x.schedule_id for x in tasks}:
                                    tasks.append(t)
                            except Exception as ie:
                                logger.debug(f"解析sc_inspection_schedules行失败(可接受): {ie}")
                except Exception as e:
                    logger.debug(f"读sc_inspection_schedules表失败(可接受): {e}")

        except Exception as e:
            logger.warning(f"加载班组任务失败(返回空列表): {e}")
        return tasks

    def _count_weekly_tasks(self, team_id: str, week_start: datetime) -> int:
        """统计本周任务数"""
        try:
            with get_db() as db:
                if db is None:
                    return 0
                week_end = week_start + timedelta(days=7)
                return db.query(WorkOrder).filter(
                    WorkOrder.assignee_id == str(team_id),
                    WorkOrder.due_time >= week_start,
                    WorkOrder.due_time < week_end,
                    WorkOrder.status.notin_(['closed', 'cancelled']),
                ).count()
        except Exception as e:
            logger.warning(f"统计周任务数失败: {e}")
            return 0

    def _find_next_available_date(
        self, team_id: str, from_date: datetime, required_hours: float = 4.0
    ) -> str:
        """查找下一个可用日期"""
        capacity = self.get_team_capacity(team_id)
        check_date = from_date + timedelta(days=1)
        for _ in range(30):
            day_of_week = check_date.weekday()
            date_str = check_date.strftime('%Y-%m-%d')
            if (day_of_week in capacity.working_days
                    and date_str not in capacity.holidays):
                existing = self._load_tasks_for_date(team_id, check_date)
                if (len(existing) < capacity.daily_max_tasks
                        and sum(t.estimated_hours for t in existing) + required_hours <= capacity.daily_max_hours):
                    return check_date.strftime('%Y-%m-%d')
            check_date += timedelta(days=1)
        return (from_date + timedelta(days=7)).strftime('%Y-%m-%d')


class ICSExporter:
    """ICS 日历文件导出器"""

    def __init__(self):
        ics_config = config.get('ics_export', {})
        self.default_duration_hours = ics_config.get('default_duration_hours', 4)
        self.organizer_email = ics_config.get('organizer_email', 'inspection@system.local')
        self.organizer_name = ics_config.get('organizer_name', '智能检验排程系统')
        self.default_reminder_minutes = ics_config.get('default_reminder_minutes', [1440, 60])
        self.product_id = ics_config.get('product_id', '-//Smart Inspection Scheduler//CN')
        logger.info("ICS日历导出器初始化完成")

    def export_single(
        self,
        task: InspectionScheduleTask,
        include_confidential_info: bool = False,
        include_alarms: bool = True,
        alarm_minutes_before: Optional[List[int]] = None,
    ) -> str:
        """
        导出单个排程任务为 ICS 格式

        Args:
            task: 排程任务
            include_confidential_info: 是否包含敏感信息（内部诊断数据等）
            include_alarms: 是否包含VALARM提醒
            alarm_minutes_before: 提前多少分钟提醒列表（None使用默认）

        Returns:
            ICS 格式字符串
        """
        return self._build_ics_content(
            [task], include_confidential_info,
            include_alarms=include_alarms,
            alarm_minutes_before=alarm_minutes_before,
        )

    def export_batch(
        self,
        tasks: List[InspectionScheduleTask],
        calendar_name: str = "检验排程",
        calendar_description: str = "",
        include_confidential_info: bool = False,
        include_alarms: bool = True,
        alarm_minutes_before: Optional[List[int]] = None,
    ) -> str:
        """批量导出排程任务为 ICS 格式"""
        return self._build_ics_content(
            tasks,
            include_confidential_info,
            calendar_name,
            calendar_description,
            include_alarms=include_alarms,
            alarm_minutes_before=alarm_minutes_before,
        )

    def generate_calendar_subscription_url(
        self,
        team_id: Optional[str] = None,
        priority_filter: Optional[List[str]] = None,
        days_ahead: int = 90,
        base_url: str = "",
        token: Optional[str] = None,
    ) -> str:
        """生成日历订阅链接（WebCal URL）"""
        params: List[str] = []
        if team_id:
            params.append(f"team_id={team_id}")
        if priority_filter:
            params.append(f"priorities={','.join(priority_filter)}")
        params.append(f"days={days_ahead}")
        if token is None:
            token = self._generate_subscription_token(team_id, priority_filter, days_ahead)
        params.append(f"token={token}")
        query_string = "&".join(params)
        webcal_base = base_url.replace('https://', 'webcal://').replace('http://', 'webcal://')
        return f"{webcal_base}/api/inspection-schedule/calendar/subscribe?{query_string}"

    def _build_ics_content(
        self,
        tasks: List[InspectionScheduleTask],
        include_confidential: bool,
        calendar_name: str = "检验排程",
        calendar_description: str = "",
        include_alarms: bool = True,
        alarm_minutes_before: Optional[List[int]] = None,
    ) -> str:
        """构建 ICS 文件内容"""
        lines: List[str] = []
        lines.append("BEGIN:VCALENDAR")
        lines.append("VERSION:2.0")
        lines.append("PRODID:" + self.product_id)
        lines.append("CALSCALE:GREGORIAN")
        lines.append("METHOD:PUBLISH")
        lines.append("X-WR-CALNAME:" + self._escape_ics_text(calendar_name))
        if calendar_description:
            lines.append("X-WR-CALDESC:" + self._escape_ics_text(calendar_description))
        lines.append("X-WR-TIMEZONE:Asia/Shanghai")

        for task in tasks:
            event_lines = self._build_vevent(
                task, include_confidential,
                include_alarms=include_alarms,
                alarm_minutes_before=alarm_minutes_before,
            )
            lines.extend(event_lines)

        lines.append("END:VCALENDAR")
        return "\r\n".join(lines)

    def _build_vevent(
        self,
        task: InspectionScheduleTask,
        include_confidential: bool,
        include_alarms: bool = True,
        alarm_minutes_before: Optional[List[int]] = None,
    ) -> List[str]:
        """构建单个 VEVENT 条目"""
        start_dt = task.scheduled_date
        end_dt = task.end_date or start_dt + timedelta(hours=self.default_duration_hours)

        uid = hashlib.md5(
            f"{task.schedule_id}_{start_dt.isoformat()}".encode()
        ).hexdigest() + "@inspection.local"

        lines: List[str] = []
        lines.append("BEGIN:VEVENT")
        lines.append("UID:" + uid)
        lines.append("DTSTAMP:" + datetime.now().strftime('%Y%m%dT%H%M%SZ'))
        lines.append("DTSTART:" + start_dt.strftime('%Y%m%dT%H%M%S'))
        lines.append("DTEND:" + end_dt.strftime('%Y%m%dT%H%M%S'))

        title_prefix_map = {
            'immediate': '[立即] ',
            'urgent': '[紧急] ',
            'attention': '[关注] ',
            'routine': '[常规] ',
        }
        prefix = title_prefix_map.get(task.priority.lower(), '')
        lines.append("SUMMARY:" + self._escape_ics_text(prefix + task.title))

        desc_parts = [task.description]
        desc_parts.append(f"优先级: {task.priority}")
        desc_parts.append(f"设备: {task.device_name} ({task.node_type}/{task.node_id})")
        if task.team_name:
            desc_parts.append(f"班组: {task.team_name}")
        if task.assignee_name:
            desc_parts.append(f"负责人: {task.assignee_name}")
        if task.standard_codes:
            desc_parts.append(f"检验标准: {', '.join(task.standard_codes)}")
        if task.prerequisites:
            desc_parts.append(f"前置条件: {'; '.join(task.prerequisites)}")
        desc_parts.append(f"预估工时: {task.estimated_hours:.1f}小时")

        if include_confidential and task.calculation_result:
            reasoning = task.calculation_result.get('reasoning', '')
            if reasoning:
                desc_parts.append(f"排程依据: {reasoning}")

        if task.conflict_detected and task.conflict_details:
            desc_parts.append(f"排程冲突: {'; '.join(task.conflict_details)}")

        lines.append("DESCRIPTION:" + self._escape_ics_text("\n".join(desc_parts)))

        if task.team_id:
            lines.append("ORGANIZER;CN=" + self._escape_ics_text(self.organizer_name)
                         + ":mailto:" + self.organizer_email)

        if task.status.lower() == 'completed':
            lines.append("STATUS:COMPLETED")
        elif task.status.lower() == 'cancelled':
            lines.append("STATUS:CANCELLED")
        elif task.status.lower() == 'in_progress':
            lines.append("STATUS:IN-PROCESS")
        elif task.conflict_detected:
            lines.append("STATUS:TENTATIVE")
        else:
            lines.append("STATUS:CONFIRMED")

        if include_alarms:
            reminder_minutes = alarm_minutes_before if alarm_minutes_before else self.default_reminder_minutes
            for minutes in reminder_minutes:
                lines.append("BEGIN:VALARM")
                lines.append("ACTION:DISPLAY")
                lines.append(f"DESCRIPTION:提醒: {task.title}")
                lines.append(f"TRIGGER:-PT{minutes}M")
                lines.append("END:VALARM")

        if task.work_order_id:
            lines.append("X-WORK-ORDER-ID:" + str(task.work_order_id))
        if task.cmms_external_id:
            lines.append("X-CMMS-EXTERNAL-ID:" + task.cmms_external_id)

        lines.append("CATEGORIES:INSPECTION," + task.priority.upper())
        lines.append("END:VEVENT")

        return lines

    def _escape_ics_text(self, text: str) -> str:
        """转义 ICS 文本特殊字符"""
        if not text:
            return ""
        result = (text
                  .replace("\\", "\\\\")
                  .replace(";", "\\;")
                  .replace(",", "\\,")
                  .replace("\n", "\\n")
                  .replace("\r", ""))
        if len(result) > 75:
            wrapped = []
            for i in range(0, len(result), 74):
                chunk = result[i:i + 74]
                wrapped.append("\t" + chunk if i > 0 else chunk)
            return "\r\n".join(wrapped)
        return result

    def _generate_subscription_token(
        self,
        team_id: Optional[str],
        priorities: Optional[List[str]],
        days: int,
    ) -> str:
        """生成订阅验证令牌"""
        secret = config.get('ics_export.subscription_secret', 'default-secret')
        raw = f"{team_id}|{','.join(priorities or [])}|{days}|{secret}|{datetime.now().strftime('%Y%m')}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


class CMMSPusher:
    """CMMS/EAM 系统推送器"""

    def __init__(self):
        from app.services.alert.cmms_service import CmmsService
        self._cmms_service = CmmsService()
        logger.info("CMMS推送器初始化完成")

    def push_schedule_to_cmms(
        self,
        schedule_task: InspectionScheduleTask,
        config_id: Optional[int] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        将排程任务推送到 CMMS 系统

        Args:
            schedule_task: 排程任务
            config_id: 指定 CMMS 配置 ID（None 则推送到所有启用配置）

        Returns:
            (是否成功, CMMS外部ID, 错误信息)
        """
        try:
            work_order_id = self._ensure_work_order(schedule_task)
            if work_order_id is None:
                return False, None, "创建关联工单失败"
            schedule_task.work_order_id = work_order_id

            success, log_id, external_id, error = self._cmms_service.sync_work_order(
                work_order_id=work_order_id,
                config_id=config_id,
                sync_type='inspection_schedule',
            )
            return success, external_id, error

        except Exception as e:
            logger.error(f"推送排程到CMMS失败: {e}")
            return False, None, str(e)

    def batch_push(
        self,
        schedule_tasks: List[InspectionScheduleTask],
        config_id: Optional[int] = None,
    ) -> Dict[str, Tuple[bool, Optional[str], Optional[str]]]:
        """批量推送排程任务到 CMMS"""
        results: Dict[str, Tuple[bool, Optional[str], Optional[str]]] = {}
        for task in schedule_tasks:
            results[task.schedule_id] = self.push_schedule_to_cmms(task, config_id)
        return results

    def _ensure_work_order(
        self, schedule_task: InspectionScheduleTask
    ) -> Optional[int]:
        """确保排程任务有关联工单，没有则创建"""
        if schedule_task.work_order_id:
            return schedule_task.work_order_id

        try:
            with get_db() as db:
                if db is None:
                    return None

                priority_map = {
                    'immediate': 'urgent',
                    'urgent': 'high',
                    'attention': 'medium',
                    'routine': 'low',
                }
                priority = priority_map.get(schedule_task.priority.lower(), 'medium')

                order_no = f"WO_INSP_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:4]}"

                extra_info = {
                    'schedule_id': schedule_task.schedule_id,
                    'inspection_type': schedule_task.inspection_type,
                    'standard_codes': schedule_task.standard_codes,
                    'prerequisites': schedule_task.prerequisites,
                    'estimated_hours': schedule_task.estimated_hours,
                    'calculation_result': schedule_task.calculation_result,
                    **schedule_task.extra_info,
                }

                wo = WorkOrder(
                    order_no=order_no,
                    title=schedule_task.title,
                    description=schedule_task.description,
                    priority=priority,
                    status='open',
                    node_type=schedule_task.node_type,
                    node_id=schedule_task.node_id,
                    alert_level=3 if priority in ('urgent', 'high') else 2,
                    risk_score=float(schedule_task.priority_score),
                    assignee_id=schedule_task.team_id,
                    assignee_name=schedule_task.team_name,
                    creator_id='system_scheduler',
                    creator_name='智能排程系统',
                    due_time=schedule_task.scheduled_date,
                    recommendations=json.dumps(schedule_task.prerequisites, ensure_ascii=False),
                    extra_info=json.dumps(extra_info, ensure_ascii=False),
                )
                db.add(wo)
                db.flush()
                wo_id = wo.id
                db.commit()
                logger.info(f"为排程任务创建工单: {order_no}, id={wo_id}")
                return wo_id

        except Exception as e:
            logger.error(f"创建关联工单失败: {e}")
            return None


class InspectionScheduleService:
    """智能检验排程服务门面类"""

    def __init__(self):
        self.scheduler = IntelligentScheduler()
        self.conflict_detector = ConflictDetector()
        self.ics_exporter = ICSExporter()
        self.cmms_pusher = CMMSPusher()
        self._ensure_tables()
        logger.info("智能检验排程服务初始化完成")

    # ---------- 核心排程功能 ----------

    def generate_schedule_for_device(
        self,
        device_data: DeviceMasterData,
        hi_score: float,
        hi_level: str,
        rul_days: Optional[float] = None,
        rul_confidence: Optional[float] = None,
        last_inspection_date: Optional[datetime] = None,
        reference_date: Optional[datetime] = None,
        check_conflict: bool = True,
        create_work_order: bool = False,
    ) -> InspectionScheduleTask:
        """
        为单个设备生成检验排程

        Args:
            device_data: 设备主数据
            hi_score: 健康度指数
            hi_level: 健康等级
            rul_days: 剩余使用寿命天数
            rul_confidence: RUL 置信度
            last_inspection_date: 上次检验日期
            reference_date: 参考计算日期
            check_conflict: 是否检测排程冲突
            create_work_order: 是否自动创建工单

        Returns:
            InspectionScheduleTask: 排程任务
        """
        alert_count, alert_levels = self._get_recent_alerts(
            device_data.node_id, device_data.node_type
        )

        factors = InspectionFactors(
            hi_score=hi_score,
            hi_level=hi_level,
            rul_days=rul_days,
            rul_confidence=rul_confidence,
            recent_alert_count=alert_count,
            recent_alert_levels=alert_levels,
            device_data=device_data,
            last_inspection_date=last_inspection_date,
            historical_inspection_count=self._get_historical_inspection_count(
                device_data.node_id, device_data.node_type
            ),
        )

        calc_result = self.scheduler.calculate_next_inspection(factors, reference_date)

        schedule_id = f"SCH{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}"

        estimated_hours = self._estimate_hours(calc_result.priority, device_data.node_type)
        end_date = calc_result.next_inspection_date + timedelta(hours=estimated_hours)

        task = InspectionScheduleTask(
            schedule_id=schedule_id,
            node_id=device_data.node_id,
            node_type=device_data.node_type,
            device_name=device_data.device_name or f"{device_data.node_type}_{device_data.node_id}",
            scheduled_date=calc_result.next_inspection_date,
            end_date=end_date,
            priority=calc_result.priority.value,
            priority_score=calc_result.priority_score,
            status=ScheduleStatus.PLANNED.value,
            team_id=device_data.team_id,
            team_name=device_data.team_name,
            assignee_id=None,
            assignee_name=None,
            inspection_type=self._determine_inspection_type(calc_result.priority),
            title=self._generate_title(calc_result.priority, device_data, device_data.node_type),
            description=calc_result.reasoning,
            estimated_hours=estimated_hours,
            standard_codes=self._determine_standard_codes(device_data.node_type, calc_result.priority),
            prerequisites=[],
            conflict_detected=False,
            conflict_details=[],
            calculation_result={
                'next_inspection_date': calc_result.next_inspection_date.isoformat(),
                'priority': calc_result.priority.value,
                'priority_score': calc_result.priority_score,
                'confidence': calc_result.confidence,
                'base_cycle_days': calc_result.base_cycle_days,
                'hi_adjustment_days': calc_result.hi_adjustment_days,
                'rul_adjustment_days': calc_result.rul_adjustment_days,
                'alert_adjustment_days': calc_result.alert_adjustment_days,
                'legal_constraint_applied': calc_result.legal_constraint_applied,
                'reasoning': calc_result.reasoning,
                'factor_breakdown': calc_result.factor_breakdown,
            },
            work_order_id=None,
            cmms_external_id=None,
            extra_info={
                'location': device_data.location,
                'manufacturer': device_data.manufacturer,
                'model': device_data.model,
                **device_data.extra_info,
            },
            create_time=datetime.now(),
            update_time=datetime.now(),
        )

        if check_conflict and task.team_id:
            has_conflict, conflicts = self.conflict_detector.detect_conflicts(
                team_id=task.team_id,
                proposed_date=task.scheduled_date,
                proposed_hours=task.estimated_hours,
            )
            task.conflict_detected = has_conflict
            task.conflict_details = [c.description for c in conflicts]
            if has_conflict:
                task.status = ScheduleStatus.CONFLICT.value
                task.extra_info['conflict_suggestions'] = [
                    s for c in conflicts for s in c.suggestions
                ]

        if create_work_order and not task.conflict_detected:
            try:
                success, external_id, _ = self.cmms_pusher.push_schedule_to_cmms(task)
                if success:
                    task.cmms_external_id = external_id
                    task.status = ScheduleStatus.CONFIRMED.value
            except Exception as e:
                logger.warning(f"创建工单失败: {e}")

        self._save_schedule_task(task)

        return task

    def batch_generate_schedules(
        self,
        device_list: List[Dict[str, Any]],
        check_conflict: bool = True,
        resolve_conflicts: bool = True,
    ) -> List[InspectionScheduleTask]:
        """
        批量为多个设备生成排程

        Args:
            device_list: 设备列表，每项含 device_data, hi_score, hi_level, rul_days 等
            check_conflict: 是否检测冲突
            resolve_conflicts: 是否自动尝试解决冲突

        Returns:
            排程任务列表
        """
        tasks: List[InspectionScheduleTask] = []
        for item in device_list:
            try:
                dd_raw = item.get('device_data', {})
                dd = DeviceMasterData(
                    node_id=dd_raw.get('node_id', ''),
                    node_type=dd_raw.get('node_type', 'bolt'),
                    device_name=dd_raw.get('device_name', ''),
                    location=dd_raw.get('location', ''),
                    legal_inspection_cycle_days=dd_raw.get('legal_inspection_cycle_days', 365),
                    last_legal_inspection_date=dd_raw.get('last_legal_inspection_date'),
                    manufacturer=dd_raw.get('manufacturer', ''),
                    model=dd_raw.get('model', ''),
                    installation_date=dd_raw.get('installation_date'),
                    team_id=dd_raw.get('team_id'),
                    team_name=dd_raw.get('team_name'),
                    extra_info=dd_raw.get('extra_info', {}),
                )
                task = self.generate_schedule_for_device(
                    device_data=dd,
                    hi_score=item.get('hi_score', 70.0),
                    hi_level=item.get('hi_level', 'good'),
                    rul_days=item.get('rul_days'),
                    rul_confidence=item.get('rul_confidence'),
                    last_inspection_date=item.get('last_inspection_date'),
                    check_conflict=False,
                    create_work_order=False,
                )
                tasks.append(task)
            except Exception as e:
                logger.error(f"批量生成排程 - 单设备失败: {e}")
                continue

        if check_conflict:
            conflict_results = self.conflict_detector.batch_detect(tasks)
            for task in tasks:
                conflicts = conflict_results.get(task.schedule_id, [])
                if conflicts:
                    task.conflict_detected = True
                    task.conflict_details = [c.description for c in conflicts]
                    task.status = ScheduleStatus.CONFLICT.value

            if resolve_conflicts:
                tasks = self._auto_resolve_conflicts(tasks)

        return tasks

    def auto_reschedule_after_conflict(
        self,
        schedule_task: InspectionScheduleTask,
        max_days_delay: int = 30,
    ) -> Optional[InspectionScheduleTask]:
        """
        冲突后自动重新排程

        Args:
            schedule_task: 原排程任务
            max_days_delay: 最大推迟天数

        Returns:
            重新排程后的任务，None表示无法解决
        """
        if not schedule_task.team_id:
            return None

        capacity = self.conflict_detector.get_team_capacity(schedule_task.team_id)
        check_date = schedule_task.scheduled_date + timedelta(days=1)

        for i in range(max_days_delay):
            day_of_week = check_date.weekday()
            date_str = check_date.strftime('%Y-%m-%d')
            if (day_of_week in capacity.working_days
                    and date_str not in capacity.holidays):
                has_conflict, _ = self.conflict_detector.detect_conflicts(
                    team_id=schedule_task.team_id,
                    proposed_date=check_date,
                    proposed_hours=schedule_task.estimated_hours,
                )
                if not has_conflict:
                    schedule_task.scheduled_date = check_date
                    schedule_task.end_date = check_date + timedelta(hours=schedule_task.estimated_hours)
                    schedule_task.conflict_detected = False
                    schedule_task.conflict_details = []
                    schedule_task.status = ScheduleStatus.CONFIRMED.value
                    schedule_task.update_time = datetime.now()
                    self._save_schedule_task(schedule_task)
                    logger.info(
                        f"自动重排成功: schedule_id={schedule_task.schedule_id}, "
                        f"原日期冲突，新日期={check_date.strftime('%Y-%m-%d')}"
                    )
                    return schedule_task
            check_date += timedelta(days=1)

        logger.warning(f"自动重排失败: schedule_id={schedule_task.schedule_id}, {max_days_delay}天内无可用日期")
        return None

    # ---------- 数据存取 ----------

    def list_schedules(
        self,
        team_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        node_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[InspectionScheduleTask], int]:
        """查询排程任务列表"""
        try:
            with get_db() as db:
                if db is None:
                    return [], 0
                self._ensure_schedule_table(db)
                from app.utils.database import Base
                table = Base.classes.get('sc_inspection_schedules')
                if table is None:
                    return [], 0
                query = db.query(table)
                if team_id:
                    query = query.filter(table.team_id == team_id)
                if status:
                    query = query.filter(table.status == status)
                if priority:
                    query = query.filter(table.priority == priority)
                if node_type:
                    query = query.filter(table.node_type == node_type)
                if start_date:
                    query = query.filter(table.scheduled_date >= start_date)
                if end_date:
                    query = query.filter(table.scheduled_date <= end_date)
                total = query.count()
                rows = query.order_by(
                    table.scheduled_date.asc(),
                    table.priority_score.desc(),
                ).offset(offset).limit(limit).all()
                return [self._row_to_task(r) for r in rows], total
        except Exception as e:
            logger.error(f"查询排程列表失败: {e}")
            return [], 0

    def get_schedule(self, schedule_id: str) -> Optional[InspectionScheduleTask]:
        """获取单个排程任务详情"""
        try:
            with get_db() as db:
                if db is None:
                    return None
                self._ensure_schedule_table(db)
                from app.utils.database import Base
                table = Base.classes.get('sc_inspection_schedules')
                if table is None:
                    return None
                row = db.query(table).filter(table.schedule_id == schedule_id).first()
                return self._row_to_task(row) if row else None
        except Exception as e:
            logger.error(f"获取排程详情失败: {e}")
            return None

    def update_schedule_status(
        self,
        schedule_id: str,
        status: str,
        assignee_id: Optional[str] = None,
        assignee_name: Optional[str] = None,
    ) -> Optional[InspectionScheduleTask]:
        """更新排程状态"""
        task = self.get_schedule(schedule_id)
        if not task:
            return None
        task.status = status
        if assignee_id:
            task.assignee_id = assignee_id
        if assignee_name:
            task.assignee_name = assignee_name
        task.update_time = datetime.now()
        self._save_schedule_task(task)
        return task

    # ---------- 导出与推送 ----------

    def export_to_ics(
        self,
        team_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        priorities: Optional[List[str]] = None,
        include_confidential: bool = False,
        include_alarms: bool = True,
        alarm_minutes_before: Optional[List[int]] = None,
        calendar_name: Optional[str] = None,
    ) -> str:
        """
        导出排程为 ICS 日历文件

        Args:
            team_id: 班组过滤
            start_date: 起始日期
            end_date: 结束日期
            priorities: 优先级过滤
            include_confidential: 是否包含内部诊断数据
            include_alarms: 是否包含VALARM提醒
            alarm_minutes_before: 提前提醒分钟列表
            calendar_name: 日历名称

        Returns:
            ICS 格式字符串
        """
        tasks, _ = self.list_schedules(
            team_id=team_id,
            start_date=start_date,
            end_date=end_date,
            limit=1000,
        )
        if priorities:
            tasks = [t for t in tasks if t.priority.lower() in [p.lower() for p in priorities]]
        return self.ics_exporter.export_batch(
            tasks=tasks,
            calendar_name=calendar_name or f"检验排程_{team_id or '全部班组'}",
            include_confidential_info=include_confidential,
            include_alarms=include_alarms,
            alarm_minutes_before=alarm_minutes_before,
        )

    def push_to_cmms(
        self,
        schedule_id: str,
        config_id: Optional[int] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """将单个排程推送到 CMMS"""
        task = self.get_schedule(schedule_id)
        if not task:
            return False, None, "排程不存在"
        success, external_id, error = self.cmms_pusher.push_schedule_to_cmms(task, config_id)
        if success and external_id:
            task.cmms_external_id = external_id
            task.status = ScheduleStatus.CONFIRMED.value
            task.update_time = datetime.now()
            self._save_schedule_task(task)
        return success, external_id, error

    # ---------- 内部辅助方法 ----------

    def _get_recent_alerts(
        self, node_id: str, node_type: str, window_days: Optional[int] = None
    ) -> Tuple[int, List[int]]:
        """获取近期预警统计"""
        window = window_days or self.scheduler.weights.alert_window_days
        try:
            with get_db() as db:
                if db is None:
                    return 0, []
                start_time = datetime.now() - timedelta(days=window)
                rows = db.query(AlertEvent).filter(
                    AlertEvent.node_type == node_type,
                    AlertEvent.node_id == str(node_id),
                    AlertEvent.create_time >= start_time,
                    AlertEvent.status != 'ignored',
                ).all()
                levels = [r.alert_level or 1 for r in rows]
                return len(rows), levels
        except Exception as e:
            logger.warning(f"获取近期预警失败: {e}")
            return 0, []

    def _get_historical_inspection_count(
        self, node_id: str, node_type: str
    ) -> int:
        """获取历史检验次数"""
        try:
            with get_db() as db:
                if db is None:
                    return 0
                return db.query(WorkOrder).filter(
                    WorkOrder.node_type == node_type,
                    WorkOrder.node_id == str(node_id),
                    WorkOrder.status.in_(['resolved', 'closed', 'retested']),
                ).count()
        except Exception as e:
            logger.warning(f"获取历史检验次数失败: {e}")
            return 0

    def _estimate_hours(
        self, priority: InspectionPriority, node_type: str
    ) -> float:
        """预估检验工时"""
        base_hours = {'bolt': 1.0, 'flange': 2.0}.get(node_type, 2.0)
        multiplier = {
            InspectionPriority.IMMEDIATE: 2.5,
            InspectionPriority.URGENT: 2.0,
            InspectionPriority.ATTENTION: 1.5,
            InspectionPriority.ROUTINE: 1.0,
        }.get(priority, 1.0)
        return round(base_hours * multiplier, 1)

    def _determine_inspection_type(self, priority: InspectionPriority) -> str:
        """确定检验类型"""
        return {
            InspectionPriority.IMMEDIATE: 'special_emergency',
            InspectionPriority.URGENT: 'special',
            InspectionPriority.ATTENTION: 'enhanced',
            InspectionPriority.ROUTINE: 'routine',
        }.get(priority, 'routine')

    def _generate_title(
        self, priority: InspectionPriority, device: DeviceMasterData, node_type: str
    ) -> str:
        """生成检验任务标题"""
        prefix_map = {
            InspectionPriority.IMMEDIATE: '【立即检验】',
            InspectionPriority.URGENT: '【紧急检验】',
            InspectionPriority.ATTENTION: '【加强检验】',
            InspectionPriority.ROUTINE: '【常规检验】',
        }
        type_cn = {'bolt': '螺栓', 'flange': '法兰面'}.get(node_type, node_type)
        prefix = prefix_map.get(priority, '')
        name = device.device_name or f"{type_cn}-{device.node_id}"
        return f"{prefix}{name}{type_cn}检验"

    def _determine_standard_codes(
        self, node_type: str, priority: InspectionPriority
    ) -> List[str]:
        """确定适用检验标准"""
        base = {
            'bolt': ['API650', 'ASME_PCC1'],
            'flange': ['API650', 'ASME_PCC1', 'GB150'],
        }.get(node_type, ['API650'])
        if priority in (InspectionPriority.URGENT, InspectionPriority.IMMEDIATE):
            base.append('ASME_PCC1')
        return list(dict.fromkeys(base))

    def _auto_resolve_conflicts(
        self, tasks: List[InspectionScheduleTask]
    ) -> List[InspectionScheduleTask]:
        """自动解决冲突（按优先级，低优先级延后）"""
        priority_order = {
            'immediate': 0,
            'urgent': 1,
            'attention': 2,
            'routine': 3,
        }
        sorted_tasks = sorted(
            tasks,
            key=lambda t: (priority_order.get(t.priority.lower(), 99), -t.priority_score)
        )
        team_date_load: Dict[Tuple[str, date], List[InspectionScheduleTask]] = {}
        resolved: List[InspectionScheduleTask] = []

        for task in sorted_tasks:
            if not task.team_id or not task.conflict_detected:
                resolved.append(task)
                if task.team_id:
                    key = (task.team_id, task.scheduled_date.date())
                    team_date_load.setdefault(key, []).append(task)
                continue
            new_task = self.auto_reschedule_after_conflict(task)
            resolved.append(new_task if new_task else task)

        return resolved

    def _save_schedule_task(self, task: InspectionScheduleTask) -> None:
        """持久化排程任务到数据库"""
        try:
            with get_db() as db:
                if db is None:
                    return
                self._ensure_schedule_table(db)
                from app.utils.database import Base
                table = Base.classes.get('sc_inspection_schedules')
                if table is None:
                    return
                existing = db.query(table).filter(table.schedule_id == task.schedule_id).first()
                data = {
                    'schedule_id': task.schedule_id,
                    'node_id': task.node_id,
                    'node_type': task.node_type,
                    'device_name': task.device_name,
                    'scheduled_date': task.scheduled_date,
                    'end_date': task.end_date,
                    'priority': task.priority,
                    'priority_score': task.priority_score,
                    'status': task.status,
                    'team_id': task.team_id,
                    'team_name': task.team_name,
                    'assignee_id': task.assignee_id,
                    'assignee_name': task.assignee_name,
                    'inspection_type': task.inspection_type,
                    'title': task.title,
                    'description': task.description,
                    'estimated_hours': task.estimated_hours,
                    'standard_codes': json.dumps(task.standard_codes, ensure_ascii=False) if task.standard_codes else None,
                    'prerequisites': json.dumps(task.prerequisites, ensure_ascii=False) if task.prerequisites else None,
                    'conflict_detected': task.conflict_detected,
                    'conflict_details': json.dumps(task.conflict_details, ensure_ascii=False) if task.conflict_details else None,
                    'calculation_result': json.dumps(task.calculation_result, ensure_ascii=False) if task.calculation_result else None,
                    'work_order_id': task.work_order_id,
                    'cmms_external_id': task.cmms_external_id,
                    'extra_info': json.dumps(task.extra_info, ensure_ascii=False) if task.extra_info else None,
                    'update_time': task.update_time,
                }
                if existing:
                    for k, v in data.items():
                        if v is not None:
                            setattr(existing, k, v)
                else:
                    data['create_time'] = task.create_time
                    db.add(table(**data))
                db.commit()
        except Exception as e:
            logger.error(f"保存排程任务失败: {e}")

    def _row_to_task(self, row) -> InspectionScheduleTask:
        """将数据库行转换为任务对象"""
        try:
            standard_codes = json.loads(row.standard_codes) if row.standard_codes else []
        except (json.JSONDecodeError, TypeError):
            standard_codes = []
        try:
            prerequisites = json.loads(row.prerequisites) if row.prerequisites else []
        except (json.JSONDecodeError, TypeError):
            prerequisites = []
        try:
            conflict_details = json.loads(row.conflict_details) if row.conflict_details else []
        except (json.JSONDecodeError, TypeError):
            conflict_details = []
        try:
            calculation_result = json.loads(row.calculation_result) if row.calculation_result else None
        except (json.JSONDecodeError, TypeError):
            calculation_result = None
        try:
            extra_info = json.loads(row.extra_info) if row.extra_info else {}
        except (json.JSONDecodeError, TypeError):
            extra_info = {}

        return InspectionScheduleTask(
            schedule_id=row.schedule_id,
            node_id=row.node_id,
            node_type=row.node_type,
            device_name=row.device_name or "",
            scheduled_date=row.scheduled_date,
            end_date=row.end_date,
            priority=row.priority,
            priority_score=float(row.priority_score or 0.0),
            status=row.status,
            team_id=row.team_id,
            team_name=row.team_name,
            assignee_id=row.assignee_id,
            assignee_name=row.assignee_name,
            inspection_type=row.inspection_type or 'routine',
            title=row.title or "",
            description=row.description or "",
            estimated_hours=float(row.estimated_hours or 4.0),
            standard_codes=standard_codes,
            prerequisites=prerequisites,
            conflict_detected=bool(row.conflict_detected),
            conflict_details=conflict_details,
            calculation_result=calculation_result,
            work_order_id=row.work_order_id,
            cmms_external_id=row.cmms_external_id,
            extra_info=extra_info,
            create_time=row.create_time or datetime.now(),
            update_time=row.update_time or datetime.now(),
        )

    def _ensure_tables(self) -> None:
        """确保所有必要的数据库表存在"""
        try:
            with get_db() as db:
                if db:
                    self._ensure_schedule_table(db)
        except Exception as e:
            logger.warning(f"确保数据表存在失败: {e}")

    def _ensure_schedule_table(self, db) -> None:
        """确保排程表存在"""
        try:
            db.execute("SELECT 1 FROM sc_inspection_schedules LIMIT 1")
        except Exception:
            try:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS sc_inspection_schedules (
                        id BIGINT PRIMARY KEY AUTO_INCREMENT,
                        schedule_id VARCHAR(64) NOT NULL UNIQUE,
                        node_id VARCHAR(100),
                        node_type VARCHAR(20),
                        device_name VARCHAR(200),
                        scheduled_date DATETIME,
                        end_date DATETIME,
                        priority VARCHAR(20),
                        priority_score FLOAT,
                        status VARCHAR(20),
                        team_id VARCHAR(50),
                        team_name VARCHAR(100),
                        assignee_id VARCHAR(50),
                        assignee_name VARCHAR(100),
                        inspection_type VARCHAR(50),
                        title VARCHAR(500),
                        description TEXT,
                        estimated_hours FLOAT,
                        standard_codes TEXT,
                        prerequisites TEXT,
                        conflict_detected BOOLEAN DEFAULT FALSE,
                        conflict_details TEXT,
                        calculation_result TEXT,
                        work_order_id BIGINT,
                        cmms_external_id VARCHAR(100),
                        extra_info TEXT,
                        create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                        update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_schedule_id (schedule_id),
                        INDEX idx_team_date (team_id, scheduled_date),
                        INDEX idx_status (status),
                        INDEX idx_priority (priority),
                        INDEX idx_node (node_type, node_id),
                        INDEX idx_scheduled_date (scheduled_date),
                        INDEX idx_work_order (work_order_id)
                    )
                """)
                db.commit()
                logger.info("排程表 sc_inspection_schedules 创建成功")
            except Exception as e2:
                logger.warning(f"创建排程表失败: {e2}")


# ---------- 模块级辅助函数（供ConflictDetector等跨类调用） ----------

def _row_to_schedule_task(row) -> Optional[InspectionScheduleTask]:
    """将sc_inspection_schedules表行转换为InspectionScheduleTask对象（模块级辅助）"""
    try:
        def _safe_json(val):
            if not val:
                return None if False else []  # 占位，下面覆盖
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return None

        def _safe_json_list(val):
            r = _safe_json(val)
            return r if isinstance(r, list) else []

        def _safe_json_dict(val):
            r = _safe_json(val)
            return r if isinstance(r, dict) else {}

        standard_codes = _safe_json_list(getattr(row, 'standard_codes', None))
        prerequisites = _safe_json_list(getattr(row, 'prerequisites', None))
        conflict_details = _safe_json_list(getattr(row, 'conflict_details', None))
        calculation_result = _safe_json_dict(getattr(row, 'calculation_result', None)) or None
        extra_info = _safe_json_dict(getattr(row, 'extra_info', None))

        return InspectionScheduleTask(
            schedule_id=getattr(row, 'schedule_id', ''),
            node_id=getattr(row, 'node_id', '') or '',
            node_type=getattr(row, 'node_type', '') or '',
            device_name=getattr(row, 'device_name', '') or '',
            scheduled_date=getattr(row, 'scheduled_date', datetime.now()),
            end_date=getattr(row, 'end_date', None) or (getattr(row, 'scheduled_date', datetime.now()) + timedelta(hours=4)),
            priority=getattr(row, 'priority', 'routine') or 'routine',
            priority_score=float(getattr(row, 'priority_score', 0) or 0),
            status=getattr(row, 'status', 'planned') or 'planned',
            team_id=getattr(row, 'team_id', None),
            team_name=getattr(row, 'team_name', None),
            assignee_id=getattr(row, 'assignee_id', None),
            assignee_name=getattr(row, 'assignee_name', None),
            inspection_type=getattr(row, 'inspection_type', 'routine') or 'routine',
            title=getattr(row, 'title', '') or '',
            description=getattr(row, 'description', '') or '',
            estimated_hours=float(getattr(row, 'estimated_hours', 4.0) or 4.0),
            standard_codes=standard_codes,
            prerequisites=prerequisites,
            conflict_detected=bool(getattr(row, 'conflict_detected', False)),
            conflict_details=conflict_details,
            calculation_result=calculation_result,
            work_order_id=getattr(row, 'work_order_id', None),
            cmms_external_id=getattr(row, 'cmms_external_id', None),
            extra_info=extra_info,
            create_time=getattr(row, 'create_time', None) or datetime.now(),
            update_time=getattr(row, 'update_time', None) or datetime.now(),
        )
    except Exception as e:
        logger.debug(f"转换排程行失败(可接受): {e}")
        return None
