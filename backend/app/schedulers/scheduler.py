"""
任务调度器模块

基于APScheduler实现定时任务调度。

主要任务:
1. 模型训练任务 - 每周执行
2. 预测任务 - 每30分钟执行（支持分片并行 + Leader选举）
3. 月度预测任务 - 每月执行
4. 告警升级任务 - 每5分钟执行
5. 审计清理任务 - 每天执行

新增功能:
- Leader选举: 大集群场景下避免重复执行预测任务
- 任务分片: 按bolt_id范围并行处理预测任务
- 执行日志: 记录每次任务的起止、节点数、成功/失败数、错误摘要

使用示例:
    from app.schedulers.scheduler import TaskScheduler

    scheduler = TaskScheduler()
    scheduler.start()
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, List, Any, Dict
from loguru import logger
import threading

from app.utils.config import config
from app.schedulers.scheduler_ext import enhanced_scheduler
from app.schedulers.leader_election import get_leader_election
from app.schedulers.job_execution import (
    job_execution_context,
    JobExecutionService,
    JobExecutionContext,
)
from app.schedulers.task_sharding import (
    get_sharded_task_executor,
    ShardedTaskExecutor,
)
from app.core.event_bus import event_bus, EventType, Event
from app.core.config_manager import config_manager

_task_lock = threading.Lock()
_running_jobs = set()


class TaskScheduler:
    """
    任务调度器类

    管理所有定时任务的调度和执行。

    Attributes:
        scheduler: APScheduler调度器实例
        config: 调度器配置
        is_running: 调度器是否正在运行
        leader_election: Leader选举器
        job_execution_service: 任务执行服务
        sharded_executor: 分片任务执行器
    """

    def __init__(self):
        """
        初始化任务调度器
        """
        self.config = config.get('scheduler', {})
        self.is_running = False

        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': ThreadPoolExecutor(10)
        }
        job_defaults = {
            'coalesce': True,
            'max_instances': 1,
        }

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults
        )

        self.leader_election = get_leader_election()
        self.job_execution_service = JobExecutionService()
        self.sharded_executor = get_sharded_task_executor()

        self.job_type_map = {
            'training_job': 'training',
            'prediction_job': 'prediction',
            'monthly_prediction_job': 'prediction',
            'alert_upgrade_job': 'alert',
            'audit_cleanup_job': 'maintenance',
            'association_graph_update_job': 'association_graph',
            'device_health_check_job': 'device_health',
        }

        self.leader_required = config.get('scheduler.leader_election.required', False)
        self.leader_jobs = config.get(
            'scheduler.leader_election.jobs',
            ['prediction_job', 'monthly_prediction_job']
        )

        self._job_ids = [
            'training_job',
            'prediction_job',
            'monthly_prediction_job',
            'alert_upgrade_job',
            'audit_cleanup_job',
            'association_graph_update_job',
            'device_health_check_job',
        ]

        event_bus.subscribe(
            EventType.SCHEDULER_CONFIG_CHANGED,
            self._on_config_changed,
            priority=10,
        )

        logger.info("任务调度器初始化完成")

    def start(self) -> None:
        """
        启动调度器
        """
        if not self.config.get('enabled', True):
            logger.info("调度器已禁用")
            return

        if self.is_running:
            logger.warning("调度器已在运行中")
            return

        self._add_jobs()

        self.scheduler.start()
        self.is_running = True

        enhanced_scheduler.start()

        logger.info("任务调度器已启动")

    def stop(self) -> None:
        """
        停止调度器
        """
        if self.is_running:
            self.leader_election.stop_all_heartbeats()
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("任务调度器已停止")

    def _add_jobs(self) -> None:
        """
        添加定时任务
        """
        training_config = self.config.get('training_job', {})
        if training_config.get('enabled', True):
            cron = training_config.get('cron', '0 2 * * 0')
            self.scheduler.add_job(
                self._training_job,
                CronTrigger.from_crontab(cron),
                id='training_job',
                name='模型训练任务',
                replace_existing=True
            )
            logger.info(f"训练任务已添加: {cron}")

        prediction_config = self.config.get('prediction_job', {})
        if prediction_config.get('enabled', True):
            cron = prediction_config.get('cron', '*/30 * * * *')
            self.scheduler.add_job(
                self._prediction_job,
                CronTrigger.from_crontab(cron),
                id='prediction_job',
                name='预测任务',
                replace_existing=True
            )
            logger.info(f"预测任务已添加: {cron}")

        monthly_config = self.config.get('monthly_prediction_job', {})
        if monthly_config.get('enabled', True):
            cron = monthly_config.get('cron', '0 3 1 * *')
            self.scheduler.add_job(
                self._monthly_prediction_job,
                CronTrigger.from_crontab(cron),
                id='monthly_prediction_job',
                name='月度预测任务',
                replace_existing=True
            )
            logger.info(f"月度预测任务已添加: {cron}")

        alert_upgrade_config = self.config.get('alert_upgrade_job', {})
        if alert_upgrade_config.get('enabled', True):
            cron = alert_upgrade_config.get('cron', '*/5 * * * *')
            self.scheduler.add_job(
                self._alert_upgrade_job,
                CronTrigger.from_crontab(cron),
                id='alert_upgrade_job',
                name='告警自动升级任务',
                replace_existing=True
            )
            logger.info(f"告警升级任务已添加: {cron}")

        audit_config = config.get('audit', {})
        if audit_config.get('auto_cleanup_enabled', True):
            cleanup_hours = audit_config.get('cleanup_interval_hours', 24)
            cron = f'0 4 */{max(1, cleanup_hours // 24)} * *'
            self.scheduler.add_job(
                self._audit_cleanup_job,
                CronTrigger.from_crontab(cron),
                id='audit_cleanup_job',
                name='审计过期记录清理任务',
                replace_existing=True
            )
            logger.info(f"审计清理任务已添加: {cron}")

        association_graph_config = self.config.get('association_graph_update_job', {})
        if association_graph_config.get('enabled', True):
            cron = association_graph_config.get('cron', '0 1 * * *')
            self.scheduler.add_job(
                self._association_graph_update_job,
                CronTrigger.from_crontab(cron),
                id='association_graph_update_job',
                name='装置关联图更新任务',
                replace_existing=True
            )
            logger.info(f"关联图更新任务已添加: {cron}")

        device_health_config = self.config.get('device_health_check_job', {})
        if device_health_config.get('enabled', True):
            cron = device_health_config.get('cron', '*/5 * * * *')
            self.scheduler.add_job(
                self._device_health_check_job,
                CronTrigger.from_crontab(cron),
                id='device_health_check_job',
                name='设备健康离线检查任务',
                replace_existing=True
            )
            logger.info(f"设备健康检查任务已添加: {cron}")

    def _acquire_leadership_if_needed(self, job_name: str) -> bool:
        """
        如果需要，获取Leader地位

        Args:
            job_name: 任务名称

        Returns:
            bool: 是否获得了Leader地位（或不需要Leader）
        """
        if not self.leader_required or job_name not in self.leader_jobs:
            return True

        with _task_lock:
            if job_name in _running_jobs:
                logger.warning(f"任务 {job_name} 已在运行中，跳过本次执行")
                return False

        success = self.leader_election.try_acquire_leadership(job_name)
        if not success:
            leader_info = self.leader_election.get_leader_info(job_name)
            leader_id = leader_info.get('leader_id', 'unknown') if leader_info else 'unknown'
            logger.info(f"任务 {job_name} 未获取到Leader地位，Leader节点: {leader_id}，跳过本次执行")
            return False

        with _task_lock:
            _running_jobs.add(job_name)

        logger.info(f"任务 {job_name} 获得Leader地位")
        return True

    def _release_leadership_if_needed(self, job_name: str) -> None:
        """
        如果需要，释放Leader地位

        Args:
            job_name: 任务名称
        """
        with _task_lock:
            _running_jobs.discard(job_name)

        if not self.leader_required or job_name not in self.leader_jobs:
            return

        self.leader_election.release_leadership(job_name)
        logger.info(f"任务 {job_name} 已释放Leader地位")

    def _training_job(self) -> None:
        """
        模型训练任务
        """
        job_name = 'training_job'
        logger.info("开始执行模型训练任务")

        try:
            with job_execution_context(
                job_name=job_name,
                job_type=self.job_type_map[job_name],
                trigger_type='scheduled',
                service=self.job_execution_service,
            ) as ctx:
                from app.services.training_service import TrainingService

                service = TrainingService()

                bolt_result = service.train_model('bolt', force_retrain=False)
                logger.info(f"螺栓模型训练完成: {bolt_result.get('message')}")
                ctx.record_success('bolt_model')

                flange_result = service.train_model('flange', force_retrain=False)
                logger.info(f"法兰面模型训练完成: {flange_result.get('message')}")
                ctx.record_success('flange_model')

        except Exception as e:
            logger.error(f"模型训练任务失败: {e}")

    def _prediction_job(
        self,
        num_shards: Optional[int] = None,
        log_id: Optional[int] = None,
    ) -> None:
        """
        预测任务（支持Leader选举和分片并行）

        Args:
            num_shards: 分片数，None则自动计算
            log_id: 已有的日志ID（手动触发时使用）
        """
        job_name = 'prediction_job'

        if not self._acquire_leadership_if_needed(job_name):
            return

        try:
            with job_execution_context(
                job_name=job_name,
                job_type=self.job_type_map[job_name],
                trigger_type='manual' if log_id else 'scheduled',
                service=self.job_execution_service,
                log_id=log_id,
            ) as ctx:
                logger.info("开始执行预测任务")

                from app.services.prediction_service import PredictionService
                from app.services.training_service import TrainingService
                from app.utils.database import get_db, BoltData
                from sqlalchemy import distinct

                service = PredictionService()
                training_service = TrainingService()

                try:
                    with get_db() as db:
                        bolt_ids = [str(r[0]) for r in db.query(distinct(BoltData.sensor_id)).all()]
                except Exception:
                    bolt_ids = training_service._get_all_bolt_ids()

                if not bolt_ids:
                    logger.info("没有可用的螺栓ID，跳过预测")
                    return

                logger.info(f"获取到 {len(bolt_ids)} 个螺栓ID，开始分片预测")

                def process_bolt(bolt_id: str) -> bool:
                    """处理单个螺栓预测"""
                    try:
                        service.batch_predict_from_db('bolt', specific_bolt_id=bolt_id)
                        return True
                    except Exception as e:
                        raise RuntimeError(f"螺栓 {bolt_id} 预测失败: {e}")

                default_shards = config.get('scheduler.sharding.default_num_shards', 4)
                num_shards = num_shards or default_shards

                result = self.sharded_executor.execute_sharded(
                    task_name=job_name,
                    task_type=self.job_type_map[job_name],
                    items=bolt_ids,
                    process_func=process_bolt,
                    num_shards=num_shards,
                    trigger_type='manual' if log_id else 'scheduled',
                    key_extractor=lambda x: str(x),
                )

                ctx.total_nodes = result.total_count
                ctx.success_count = result.success_count
                ctx.failed_count = result.failed_count
                ctx.skipped_count = result.skipped_count
                ctx.bolt_id_min = str(result.item_min) if result.item_min else None
                ctx.bolt_id_max = str(result.item_max) if result.item_max else None

                for i in range(result.error_summary.total_errors):
                    if i < len(result.error_summary.failed_node_ids):
                        node_id = result.error_summary.failed_node_ids[i]
                        err_type = list(result.error_summary.error_types.keys())[0] if result.error_summary.error_types else 'Exception'
                        ctx.record_failure(node_id, f"分片执行错误", err_type)

                logger.info(
                    f"螺栓预测任务完成: 总数={result.total_count}, "
                    f"成功={result.success_count}, 失败={result.failed_count}, "
                    f"跳过={result.skipped_count}"
                )

                logger.info("开始法兰面预测")
                try:
                    service.batch_predict_from_db('flange')
                    logger.info("法兰面预测完成")
                except Exception as e:
                    logger.error(f"法兰面预测失败: {e}")

                logger.info("预测任务执行完成")

        except Exception as e:
            logger.error(f"预测任务失败: {e}")
        finally:
            self._release_leadership_if_needed(job_name)

    def _monthly_prediction_job(self) -> None:
        """
        月度预测任务（支持Leader选举）
        """
        job_name = 'monthly_prediction_job'

        if not self._acquire_leadership_if_needed(job_name):
            return

        try:
            with job_execution_context(
                job_name=job_name,
                job_type=self.job_type_map[job_name],
                trigger_type='scheduled',
                service=self.job_execution_service,
            ) as ctx:
                logger.info("开始执行月度预测任务")

                from app.services.prediction_service import PredictionService
                from app.services.training_service import TrainingService

                prediction_service = PredictionService()
                training_service = TrainingService()

                bolt_ids = training_service._get_all_bolt_ids()
                flange_ids = training_service._get_all_flange_ids()

                total_nodes = len(bolt_ids) + len(flange_ids)
                ctx.total_nodes = total_nodes

                logger.info(f"待处理: 螺栓 {len(bolt_ids)} 个, 法兰面 {len(flange_ids)} 个")

                for bolt_id in bolt_ids:
                    try:
                        prediction_service.forecast_monthly(
                            node_id=bolt_id,
                            node_type='bolt',
                            days=30
                        )
                        ctx.record_success(str(bolt_id))
                    except Exception as e:
                        logger.error(f"螺栓 {bolt_id} 月度预测失败: {e}")
                        ctx.record_failure(str(bolt_id), str(e), type(e).__name__)

                for flange_id in flange_ids:
                    try:
                        prediction_service.forecast_monthly(
                            node_id=flange_id,
                            node_type='flange',
                            days=30
                        )
                        ctx.record_success(str(flange_id))
                    except Exception as e:
                        logger.error(f"法兰面 {flange_id} 月度预测失败: {e}")
                        ctx.record_failure(str(flange_id), str(e), type(e).__name__)

                logger.info(
                    f"月度预测任务完成: 总数={total_nodes}, "
                    f"成功={ctx.success_count}, 失败={ctx.failed_count}"
                )

        except Exception as e:
            logger.error(f"月度预测任务失败: {e}")
        finally:
            self._release_leadership_if_needed(job_name)

    def _alert_upgrade_job(self) -> None:
        """
        告警自动升级任务
        """
        job_name = 'alert_upgrade_job'
        logger.info("开始执行告警升级任务")

        try:
            with job_execution_context(
                job_name=job_name,
                job_type=self.job_type_map[job_name],
                trigger_type='scheduled',
                service=self.job_execution_service,
            ) as ctx:
                from app.services.alert import AlertService

                alert_service = AlertService()
                upgraded_count = alert_service.process_pending_upgrades()

                ctx.success_count = upgraded_count

                if upgraded_count > 0:
                    logger.info(f"告警升级任务完成，共升级 {upgraded_count} 条告警")
                else:
                    logger.info("告警升级任务完成，无需升级的告警")

        except Exception as e:
            logger.error(f"告警升级任务失败: {e}")

    def _audit_cleanup_job(self) -> None:
        """
        审计过期记录清理任务
        """
        job_name = 'audit_cleanup_job'
        logger.info("开始执行审计过期记录清理任务")

        try:
            with job_execution_context(
                job_name=job_name,
                job_type=self.job_type_map[job_name],
                trigger_type='scheduled',
                service=self.job_execution_service,
            ) as ctx:
                from app.services.audit import AuditService

                audit_service = AuditService()
                cleaned_count = audit_service.cleanup_expired()

                ctx.success_count = cleaned_count

                if cleaned_count > 0:
                    logger.info(f"审计清理任务完成，共清理 {cleaned_count} 条过期记录")
                else:
                    logger.info("审计清理任务完成，无过期记录")

        except Exception as e:
            logger.error(f"审计清理任务失败: {e}")

    def _association_graph_update_job(self) -> None:
        """
        装置关联图更新任务

        定期更新装置关联图，包括同管线、同振动源、同班次、共故障、物理邻接等关联权重。
        """
        job_name = 'association_graph_update_job'
        logger.info("开始执行装置关联图更新任务")

        try:
            with job_execution_context(
                job_name=job_name,
                job_type=self.job_type_map[job_name],
                trigger_type='scheduled',
                service=self.job_execution_service,
            ) as ctx:
                from app.services.risk_visualization import RiskPropagationService
                from app.utils.database import get_db
                from sqlalchemy import text

                propagation_service = RiskPropagationService()

                devices = []
                try:
                    with get_db() as db:
                        result = db.execute(text("""
                            SELECT
                                id,
                                node_code,
                                node_name,
                                node_type,
                                pipeline_id,
                                vibration_source,
                                shifts,
                                latitude,
                                longitude,
                                extra_info
                            FROM sc_org_nodes
                            WHERE node_type = 'unit'
                              AND status = 'active'
                        """))
                        for row in result:
                            device = {
                                'id': str(row[0]),
                                'device_id': str(row[0]),
                                'node_code': row[1],
                                'name': row[2] or str(row[0]),
                                'node_type': row[3],
                                'pipeline_id': row[4],
                                'vibration_source': row[5],
                                'shifts': self._parse_json_field(row[6], []),
                                'latitude': row[7],
                                'longitude': row[8],
                                'extra_info': self._parse_json_field(row[9], {}),
                            }
                            devices.append(device)
                except Exception as e:
                    logger.warning(f"从数据库读取装置信息失败，将使用内存缓存: {e}")

                co_fault_history = []
                try:
                    with get_db() as db:
                        result = db.execute(text("""
                            SELECT
                                GROUP_CONCAT(DISTINCT node_id ORDER BY node_id) as device_ids,
                                DATE_FORMAT(create_time, '%Y-%m-%d %H:00:00') as fault_time
                            FROM sci_abnormal_prediction
                            WHERE pw_type IN ('紧急级预警', '故障')
                              AND node_type = 'unit'
                              AND create_time >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                            GROUP BY fault_time
                            HAVING COUNT(DISTINCT node_id) >= 2
                            ORDER BY fault_time DESC
                            LIMIT 1000
                        """))
                        for row in result:
                            device_ids = row[0].split(',') if row[0] else []
                            if len(device_ids) >= 2:
                                co_fault_history.append({
                                    'device_ids': device_ids,
                                    'timestamp': row[1],
                                })
                except Exception as e:
                    logger.warning(f"从数据库读取共故障历史失败: {e}")

                update_result = propagation_service.update_association_graph(
                    devices=devices,
                    co_fault_history=co_fault_history,
                )

                ctx.total_nodes = update_result.get('device_count', 0)
                ctx.success_count = update_result.get('edge_count', 0)

                try:
                    self._save_associations_to_db(propagation_service)
                except Exception as e:
                    logger.error(f"保存关联关系到数据库失败: {e}")

                logger.info(
                    f"装置关联图更新任务完成: "
                    f"装置数={update_result.get('device_count', 0)}, "
                    f"边数={update_result.get('edge_count', 0)}, "
                    f"更新次数={update_result.get('update_count', 0)}"
                )

        except Exception as e:
            logger.error(f"装置关联图更新任务失败: {e}")

    def _device_health_check_job(self) -> None:
        """
        设备健康检查任务（离线检测）
        """
        job_name = 'device_health_check_job'
        logger.info("开始执行设备健康检查任务")

        try:
            with job_execution_context(
                job_name=job_name,
                job_type=self.job_type_map[job_name],
                trigger_type='scheduled',
                service=self.job_execution_service,
            ) as ctx:
                from app.services.device_health_service import get_device_health_service

                dh_service = get_device_health_service()
                offline_devices = dh_service.check_offline_devices()

                ctx.success_count = len(offline_devices)
                ctx.total_nodes = len(offline_devices)

                if offline_devices:
                    logger.info(
                        f"设备健康检查任务完成，检测到 {len(offline_devices)} 个离线设备"
                    )
                else:
                    logger.info("设备健康检查任务完成，无离线设备")

        except Exception as e:
            logger.error(f"设备健康检查任务失败: {e}")

    def _parse_json_field(self, value: Any, default: Any) -> Any:
        """解析JSON字段"""
        if not value:
            return default
        if isinstance(value, (dict, list)):
            return value
        try:
            import json
            return json.loads(value)
        except Exception:
            return default

    def _save_associations_to_db(self, propagation_service: RiskPropagationService) -> None:
        """保存关联关系到数据库"""
        from app.utils.database import get_db
        from sqlalchemy import text
        import json

        graph_data = propagation_service.get_association_graph_data()
        edges = graph_data.get('edges', [])

        with get_db() as db:
            for edge in edges:
                db.execute(text("""
                    INSERT INTO sc_device_associations
                    (tenant_id, device_a_id, device_b_id,
                     same_pipeline_weight, same_vibration_weight, same_shift_weight,
                     co_fault_weight, physical_weight, composite_weight,
                     association_types, co_fault_count, extra_info, status)
                    VALUES (:tenant_id, :device_a_id, :device_b_id,
                            :same_pipeline_weight, :same_vibration_weight, :same_shift_weight,
                            :co_fault_weight, :physical_weight, :composite_weight,
                            :association_types, :co_fault_count, :extra_info, 'active')
                    ON DUPLICATE KEY UPDATE
                        same_pipeline_weight = VALUES(same_pipeline_weight),
                        same_vibration_weight = VALUES(same_vibration_weight),
                        same_shift_weight = VALUES(same_shift_weight),
                        co_fault_weight = VALUES(co_fault_weight),
                        physical_weight = VALUES(physical_weight),
                        composite_weight = VALUES(composite_weight),
                        association_types = VALUES(association_types),
                        co_fault_count = VALUES(co_fault_count),
                        extra_info = VALUES(extra_info),
                        update_time = CURRENT_TIMESTAMP
                """), {
                    'tenant_id': 0,
                    'device_a_id': edge['source'],
                    'device_b_id': edge['target'],
                    'same_pipeline_weight': edge['weights']['same_pipeline'],
                    'same_vibration_weight': edge['weights']['same_vibration_source'],
                    'same_shift_weight': edge['weights']['same_shift'],
                    'co_fault_weight': edge['weights']['co_fault'],
                    'physical_weight': edge['weights']['physical'],
                    'composite_weight': edge['weight'],
                    'association_types': json.dumps(edge['association_types']),
                    'co_fault_count': edge.get('co_fault_count', 0),
                    'extra_info': json.dumps({}),
                })
            db.commit()

        logger.info(f"关联关系已保存到数据库，共 {len(edges)} 条")

    def get_jobs(self) -> list:
        """
        获取所有任务列表
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time,
                'trigger': str(job.trigger)
            })
        return jobs

    def run_job_now(
        self,
        job_id: str,
        num_shards: Optional[int] = None,
        log_id: Optional[int] = None,
    ) -> bool:
        """
        立即执行指定任务

        Args:
            job_id: 任务ID
            num_shards: 分片数（仅适用于prediction_job）
            log_id: 已有的日志ID

        Returns:
            bool: 是否成功触发
        """
        job = self.scheduler.get_job(job_id)
        if job:
            if job_id == 'prediction_job':
                self.scheduler.add_job(
                    func=self._prediction_job,
                    kwargs={'num_shards': num_shards, 'log_id': log_id},
                    id=f'{job_id}_manual_{datetime.now().strftime("%Y%m%d%H%M%S")}',
                    replace_existing=False,
                    misfire_grace_time=3600,
                )
            else:
                job.modify(next_run_time=datetime.now())
            return True
        return False

    def update_job_cron(self, job_id: str, cron: str) -> bool:
        """
        更新指定任务的 Cron 表达式
        """
        try:
            from apscheduler.triggers.cron import CronTrigger
            job = self.scheduler.get_job(job_id)
            if job:
                job.reschedule(CronTrigger.from_crontab(cron))
                return True
            return False
        except Exception as e:
            logger.error(f"更新任务Cron失败: {e}")
            return False

    def enable_job(self, job_id: str) -> bool:
        """
        启用指定任务
        """
        job = self.scheduler.get_job(job_id)
        if job:
            job.resume()
            return True
        return False

    def disable_job(self, job_id: str) -> bool:
        """
        禁用指定任务
        """
        job = self.scheduler.get_job(job_id)
        if job:
            job.pause()
            return True
        return False

    def is_job_enabled(self, job_id: str) -> Optional[bool]:
        """
        检查任务是否启用
        """
        job = self.scheduler.get_job(job_id)
        if job:
            return job.next_run_time is not None
        return None

    def _on_config_changed(self, event: Event) -> None:
        """
        调度配置变更事件回调（由事件总线触发）
        """
        try:
            changed_paths = event.data.get("changed_paths", [])
            version = event.data.get("version")
            logger.info(
                f"收到调度配置变更事件: version={version}, "
                f"changed_paths={changed_paths}"
            )
            self.reload_config(changed_paths=changed_paths)
        except Exception as e:
            logger.exception(f"处理调度配置变更事件失败: {e}")

    def reload_config(
        self,
        changed_paths: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        重新加载调度配置（热更新 cron 与 enabled 状态）

        Args:
            changed_paths: 变更的配置路径列表（可选，None则全量同步）

        Returns:
            {
                "updated_jobs": [job_id, ...],
                "failed_jobs": {job_id: reason},
                "added_jobs": [job_id, ...],
                "removed_jobs": [job_id, ...],
            }
        """
        result: Dict[str, Any] = {
            "updated_jobs": [],
            "failed_jobs": {},
            "added_jobs": [],
            "removed_jobs": [],
        }

        with _task_lock:
            self.config = config_manager.get('scheduler', {})

            self.leader_required = config_manager.get(
                'scheduler.leader_election.required', False
            )
            self.leader_jobs = config_manager.get(
                'scheduler.leader_election.jobs',
                ['prediction_job', 'monthly_prediction_job']
            )

            job_configs = {
                'training_job': (
                    self.config.get('training_job', {}),
                    self._training_job,
                ),
                'prediction_job': (
                    self.config.get('prediction_job', {}),
                    self._prediction_job,
                ),
                'monthly_prediction_job': (
                    self.config.get('monthly_prediction_job', {}),
                    self._monthly_prediction_job,
                ),
                'alert_upgrade_job': (
                    self.config.get('alert_upgrade_job', {}),
                    self._alert_upgrade_job,
                ),
                'audit_cleanup_job': (
                    self._get_audit_cleanup_config(),
                    self._audit_cleanup_job,
                ),
                'device_health_check_job': (
                    self.config.get('device_health_check_job', {}),
                    self._device_health_check_job,
                ),
            }

            for job_id, (job_cfg, job_func) in job_configs.items():
                try:
                    action = self._sync_job(job_id, job_cfg, job_func)
                    if action == 'updated':
                        result["updated_jobs"].append(job_id)
                    elif action == 'added':
                        result["added_jobs"].append(job_id)
                    elif action == 'removed':
                        result["removed_jobs"].append(job_id)
                except Exception as e:
                    result["failed_jobs"][job_id] = str(e)
                    logger.error(f"热更新任务 {job_id} 失败: {e}")

            if self.is_running and not self.scheduler.running:
                try:
                    self.scheduler.start()
                    logger.info("调度器已恢复运行")
                except Exception as e:
                    logger.warning(f"重启调度器失败（可能已在运行）: {e}")

            logger.info(
                f"调度配置热更新完成: updated={len(result['updated_jobs'])}, "
                f"added={len(result['added_jobs'])}, removed={len(result['removed_jobs'])}, "
                f"failed={len(result['failed_jobs'])}"
            )
            return result

    def _get_audit_cleanup_config(self) -> Dict[str, Any]:
        """获取审计清理任务的配置（兼容从 audit 根节读取）"""
        audit_cfg = config_manager.get('audit', {})
        cleanup_enabled = audit_cfg.get('auto_cleanup_enabled', True)
        cleanup_hours = audit_cfg.get('cleanup_interval_hours', 24)
        cron = f'0 4 */{max(1, cleanup_hours // 24)} * *'
        return {
            'enabled': cleanup_enabled,
            'cron': cron,
        }

    def _sync_job(
        self,
        job_id: str,
        job_cfg: Dict[str, Any],
        job_func: Any,
    ) -> Optional[str]:
        """
        同步单个任务的配置

        Returns:
            'updated' | 'added' | 'removed' | None（无变化）
        """
        from apscheduler.triggers.cron import CronTrigger

        enabled = job_cfg.get('enabled', True)
        cron = job_cfg.get('cron', '')
        job = self.scheduler.get_job(job_id)

        if not enabled:
            if job is not None:
                self.scheduler.remove_job(job_id)
                logger.info(f"任务已禁用并移除: {job_id}")
                return 'removed'
            return None

        if not cron:
            return None

        try:
            trigger = CronTrigger.from_crontab(cron)
        except Exception as e:
            raise ValueError(f"无效的 cron 表达式 '{cron}': {e}")

        if job is None:
            self.scheduler.add_job(
                job_func,
                trigger,
                id=job_id,
                name=f"{job_id} (热更新添加)",
                replace_existing=True,
            )
            logger.info(f"任务已添加: {job_id}, cron={cron}")
            return 'added'

        old_trigger_str = str(job.trigger)
        new_trigger_str = str(trigger)
        if old_trigger_str != new_trigger_str:
            job.reschedule(trigger)
            logger.info(f"任务 cron 已更新: {job_id}, {old_trigger_str} -> {new_trigger_str}")
            return 'updated'

        if job.next_run_time is None:
            job.resume()
            logger.info(f"任务已恢复: {job_id}")
            return 'updated'

        return None


# 全局调度器实例
scheduler = TaskScheduler()
