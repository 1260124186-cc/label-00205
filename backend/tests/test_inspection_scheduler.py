"""
智能复检周期排程模块单元测试

测试内容:
1. IntelligentScheduler - 智能排程算法引擎
2. ConflictDetector - 排程冲突检测器
3. ICSExporter - ICS日历文件导出器
4. InspectionScheduleService - 服务门面
"""

import pytest
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestIntelligentScheduler:
    """智能排程算法引擎测试"""

    def test_scheduler_initialization(self):
        """测试调度器初始化"""
        from app.services.inspection_scheduler import (
            IntelligentScheduler, ScheduleWeights
        )

        scheduler = IntelligentScheduler()

        assert scheduler is not None
        assert scheduler.weights is not None
        assert isinstance(scheduler.weights, ScheduleWeights)
        assert scheduler.weights.hi_weight > 0
        assert scheduler.weights.rul_weight > 0

    def test_calculate_next_inspection_basic(self):
        """测试基本排程计算"""
        from app.services.inspection_scheduler import (
            IntelligentScheduler, InspectionFactors, DeviceMasterData
        )

        scheduler = IntelligentScheduler()

        device_data = DeviceMasterData(
            node_id='FLANGE_001',
            node_type='flange',
            device_name='测试法兰面-001',
            legal_inspection_cycle_days=365,
            last_legal_inspection_date=datetime.now() - timedelta(days=180),
            team_id='TEAM_A',
            team_name='检验A班',
        )

        factors = InspectionFactors(
            hi_score=85.0,
            hi_level='good',
            rul_days=None,
            rul_confidence=None,
            recent_alert_count=0,
            recent_alert_levels=[],
            device_data=device_data,
            last_inspection_date=datetime.now() - timedelta(days=180),
            historical_inspection_count=5,
        )

        result = scheduler.calculate_next_inspection(factors)

        assert result is not None
        assert result.node_id == 'FLANGE_001'
        assert result.node_type == 'flange'
        assert result.next_inspection_date is not None
        assert result.next_inspection_date > datetime.now()
        assert 0 <= result.priority_score <= 100
        assert 0.3 <= result.confidence <= 0.98
        assert result.base_cycle_days == 365.0
        assert len(result.reasoning) > 0

    def test_calculate_next_inspection_critical_health(self):
        """测试危险健康度状态下的排程（应大幅提前）"""
        from app.services.inspection_scheduler import (
            IntelligentScheduler, InspectionFactors, DeviceMasterData, InspectionPriority
        )

        scheduler = IntelligentScheduler()

        device_data = DeviceMasterData(
            node_id='BOLT_CRITICAL',
            node_type='bolt',
            legal_inspection_cycle_days=180,
            last_legal_inspection_date=datetime.now() - timedelta(days=90),
            team_id='TEAM_A',
        )

        factors = InspectionFactors(
            hi_score=20.0,
            hi_level='critical',
            rul_days=15.0,
            rul_confidence=0.85,
            recent_alert_count=8,
            recent_alert_levels=[3, 4, 5, 3, 4, 5, 4, 3],
            device_data=device_data,
            last_inspection_date=datetime.now() - timedelta(days=90),
        )

        result = scheduler.calculate_next_inspection(factors)

        days_to_inspection = (result.next_inspection_date - datetime.now()).days

        assert result.priority in (InspectionPriority.URGENT, InspectionPriority.IMMEDIATE)
        assert result.hi_adjustment_days < 0
        assert result.rul_adjustment_days < 0
        assert result.alert_adjustment_days < 0
        assert days_to_inspection <= 30

    def test_hi_adjustment(self):
        """测试HI健康度对周期的调整"""
        from app.services.inspection_scheduler import IntelligentScheduler

        scheduler = IntelligentScheduler()

        base_cycle = 365.0

        excellent_adj = scheduler._calculate_hi_adjustment(95.0, 'excellent', base_cycle)
        poor_adj = scheduler._calculate_hi_adjustment(25.0, 'poor', base_cycle)

        assert excellent_adj > 0
        assert poor_adj < 0

    def test_rul_adjustment(self):
        """测试RUL剩余寿命对周期的调整"""
        from app.services.inspection_scheduler import IntelligentScheduler

        scheduler = IntelligentScheduler()

        base_cycle = 365.0

        no_rul_adj = scheduler._calculate_rul_adjustment(None, None, base_cycle)
        critical_rul_adj = scheduler._calculate_rul_adjustment(5.0, 0.9, base_cycle)

        assert no_rul_adj == 0.0
        assert critical_rul_adj < 0

    def test_alert_adjustment(self):
        """测试预警频率对周期的调整"""
        from app.services.inspection_scheduler import IntelligentScheduler

        scheduler = IntelligentScheduler()

        base_cycle = 365.0

        no_alert_adj = scheduler._calculate_alert_adjustment(0, [], base_cycle)
        high_alert_adj = scheduler._calculate_alert_adjustment(10, [4, 5, 4, 5, 4, 5, 4, 5, 4, 5], base_cycle)

        assert no_alert_adj > 0
        assert high_alert_adj < 0

    def test_priority_determination(self):
        """测试优先级确定逻辑"""
        from app.services.inspection_scheduler import (
            IntelligentScheduler, InspectionPriority
        )

        scheduler = IntelligentScheduler()

        routine_priority, _ = scheduler._determine_priority(90, 365, 0, 365, 200)
        immediate_priority, _ = scheduler._determine_priority(15, 5, 10, 30, 2)

        assert routine_priority == InspectionPriority.ROUTINE
        assert immediate_priority == InspectionPriority.IMMEDIATE


class TestConflictDetector:
    """排程冲突检测器测试"""

    def test_detector_initialization(self):
        """测试冲突检测器初始化"""
        from app.services.inspection_scheduler import ConflictDetector

        detector = ConflictDetector()

        assert detector is not None
        assert detector.default_daily_max_tasks > 0

    def test_team_capacity_registration(self):
        """测试班组产能注册"""
        from app.services.inspection_scheduler import ConflictDetector, TeamCapacity

        detector = ConflictDetector()

        capacity = TeamCapacity(
            team_id='TEAM_TEST',
            team_name='测试班组',
            daily_max_tasks=3,
            daily_max_hours=24.0,
            weekly_max_tasks=15,
            member_count=4,
        )

        detector.register_team_capacity(capacity)
        retrieved = detector.get_team_capacity('TEAM_TEST')

        assert retrieved.team_id == 'TEAM_TEST'
        assert retrieved.daily_max_tasks == 3

    def test_non_working_day_detection(self):
        """测试非工作日检测"""
        from app.services.inspection_scheduler import ConflictDetector, TeamCapacity

        detector = ConflictDetector()

        saturday = datetime(2026, 6, 20)
        assert saturday.weekday() == 5

        has_conflict, conflicts = detector.detect_conflicts(
            team_id='TEAM_WEEKEND',
            proposed_date=saturday,
            proposed_hours=4.0,
            existing_tasks=[],
        )

        assert has_conflict is True
        assert any(c.conflict_type == 'non_working_day' for c in conflicts)

    def test_batch_detect(self):
        """测试批量冲突检测"""
        from app.services.inspection_scheduler import (
            ConflictDetector, InspectionScheduleTask, ScheduleStatus
        )

        detector = ConflictDetector()

        base_date = datetime(2026, 6, 22, 9, 0, 0)
        tasks = []
        for i in range(5):
            tasks.append(InspectionScheduleTask(
                schedule_id=f'SCH_{i}',
                node_id=f'BOLT_{i}',
                node_type='bolt',
                device_name=f'测试螺栓{i}',
                scheduled_date=base_date,
                end_date=base_date + timedelta(hours=2),
                priority='routine',
                priority_score=20.0,
                status=ScheduleStatus.PLANNED.value,
                team_id='TEAM_BATCH',
                team_name='批量测试班组',
                assignee_id=f'USER_{i}',
                assignee_name=f'检验员{i}',
                inspection_type='routine',
                title=f'检验任务{i}',
                description='测试任务',
                estimated_hours=2.0,
                standard_codes=[],
                prerequisites=[],
                conflict_detected=False,
                conflict_details=[],
                calculation_result=None,
                work_order_id=None,
                cmms_external_id=None,
                extra_info={},
                create_time=datetime.now(),
                update_time=datetime.now(),
            ))

        results = detector.batch_detect(tasks)

        assert len(results) == len(tasks)
        for schedule_id, conflicts in results.items():
            assert isinstance(conflicts, list)


class TestICSExporter:
    """ICS日历导出器测试"""

    def test_exporter_initialization(self):
        """测试ICS导出器初始化"""
        from app.services.inspection_scheduler import ICSExporter

        exporter = ICSExporter()

        assert exporter is not None
        assert exporter.default_duration_hours > 0

    def test_single_task_export(self):
        """测试单任务ICS导出"""
        from app.services.inspection_scheduler import (
            ICSExporter, InspectionScheduleTask
        )

        exporter = ICSExporter()

        scheduled_date = datetime(2026, 7, 15, 9, 0, 0)
        task = InspectionScheduleTask(
            schedule_id='SCH_ICS_TEST',
            node_id='BOLT_001',
            node_type='bolt',
            device_name='测试螺栓-ICS',
            scheduled_date=scheduled_date,
            end_date=scheduled_date + timedelta(hours=4),
            priority='urgent',
            priority_score=65.0,
            status='planned',
            team_id='TEAM_A',
            team_name='检验A班',
            assignee_id='USER_A',
            assignee_name='检验员甲',
            inspection_type='special',
            title='【紧急检验】测试螺栓检验',
            description='测试ICS导出功能',
            estimated_hours=4.0,
            standard_codes=['API650'],
            prerequisites=['设备停机', '安全确认'],
            conflict_detected=False,
            conflict_details=[],
            calculation_result=None,
            work_order_id=None,
            cmms_external_id=None,
            extra_info={},
            create_time=datetime.now(),
            update_time=datetime.now(),
        )

        ics_content = exporter.export_single(task, include_alarms=False)

        assert 'BEGIN:VCALENDAR' in ics_content
        assert 'END:VCALENDAR' in ics_content
        assert 'BEGIN:VEVENT' in ics_content
        assert 'END:VEVENT' in ics_content
        assert 'SUMMARY:' in ics_content
        assert 'DTSTART:' in ics_content

    def test_batch_export(self):
        """测试批量ICS导出"""
        from app.services.inspection_scheduler import (
            ICSExporter, InspectionScheduleTask
        )

        exporter = ICSExporter()

        tasks = []
        for i in range(3):
            d = datetime(2026, 7, 20 + i, 9, 0, 0)
            tasks.append(InspectionScheduleTask(
                schedule_id=f'SCH_BATCH_{i}',
                node_id=f'BOLT_{i}',
                node_type='bolt',
                device_name=f'螺栓{i}',
                scheduled_date=d,
                end_date=d + timedelta(hours=2),
                priority='routine',
                priority_score=20.0,
                status='planned',
                team_id='TEAM_A',
                team_name='检验A班',
                assignee_id=f'USER_{i}',
                assignee_name=f'检验员{i}',
                inspection_type='routine',
                title=f'常规检验{i}',
                description='批量测试',
                estimated_hours=2.0,
                standard_codes=[],
                prerequisites=[],
                conflict_detected=False,
                conflict_details=[],
                calculation_result=None,
                work_order_id=None,
                cmms_external_id=None,
                extra_info={},
                create_time=datetime.now(),
                update_time=datetime.now(),
            ))

        ics_content = exporter.export_batch(tasks, calendar_name="测试日历")

        assert 'BEGIN:VCALENDAR' in ics_content
        assert ics_content.count('BEGIN:VEVENT') == 3
        assert 'X-WR-CALNAME:测试日历' in ics_content

    def test_subscription_token_generation(self):
        """测试日历订阅令牌生成"""
        from app.services.inspection_scheduler import ICSExporter

        exporter = ICSExporter()

        url = exporter.generate_calendar_subscription_url(
            team_id='TEAM_A',
            priority_filter=['urgent', 'immediate'],
            days_ahead=60,
            base_url='https://example.com',
        )

        assert 'webcal://' in url
        assert 'token=' in url
        assert 'team_id=TEAM_A' in url
        assert 'days=60' in url


class TestInspectionScheduleService:
    """智能检验排程服务门面测试"""

    def test_service_initialization(self):
        """测试服务初始化"""
        from app.services.inspection_scheduler import (
            InspectionScheduleService, IntelligentScheduler,
            ConflictDetector, ICSExporter
        )

        service = InspectionScheduleService()

        assert service is not None
        assert isinstance(service.scheduler, IntelligentScheduler)
        assert isinstance(service.conflict_detector, ConflictDetector)
        assert isinstance(service.ics_exporter, ICSExporter)

    def test_estimate_hours(self):
        """测试工时估算"""
        from app.services.inspection_scheduler import (
            InspectionScheduleService, InspectionPriority
        )

        service = InspectionScheduleService()

        bolt_routine_hours = service._estimate_hours(InspectionPriority.ROUTINE, 'bolt')
        flange_urgent_hours = service._estimate_hours(InspectionPriority.URGENT, 'flange')

        assert bolt_routine_hours > 0
        assert flange_urgent_hours >= bolt_routine_hours

    def test_determine_inspection_type(self):
        """测试检验类型确定"""
        from app.services.inspection_scheduler import (
            InspectionScheduleService, InspectionPriority
        )

        service = InspectionScheduleService()

        assert service._determine_inspection_type(InspectionPriority.ROUTINE) == 'routine'
        assert service._determine_inspection_type(InspectionPriority.IMMEDIATE) == 'special_emergency'

    def test_generate_title(self):
        """测试任务标题生成"""
        from app.services.inspection_scheduler import (
            InspectionScheduleService, InspectionPriority, DeviceMasterData
        )

        service = InspectionScheduleService()

        device = DeviceMasterData(
            node_id='B001',
            node_type='bolt',
            device_name='高压管道螺栓',
        )

        title = service._generate_title(InspectionPriority.URGENT, device, 'bolt')

        assert '紧急检验' in title
        assert '高压管道螺栓' in title
