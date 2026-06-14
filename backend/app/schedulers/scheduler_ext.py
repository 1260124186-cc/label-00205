"""
增强版任务调度器模块

扩展原有的调度器，增加以下功能：
1. Leader选举：大集群场景支持单实例Leader选举，避免重复预测
2. 任务分片：预测任务支持按 bolt_id 范围并行处理
3. 执行日志：记录每次任务起止、处理节点数、成功/失败数、错误摘要

使用示例:
    from app.schedulers.scheduler_ext import EnhancedTaskScheduler
    
    scheduler = EnhancedTaskScheduler()
    scheduler.start()
"""

import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

from app.schedulers.leader_election import leader_election
from app.schedulers.job_sharding import job_sharding, ShardInfo
from app.schedulers.job_logger import job_execution_logger
from app.utils.config import config


class EnhancedTaskScheduler:
    """
    增强版任务调度器

    在原有调度器基础上增加Leader选举、任务分片和执行日志功能。

    Attributes:
        enable_leader_election: 是否启用Leader选举
        enable_sharding: 是否启用任务分片
        shard_count: 分片数量
        max_parallel_shards: 最大并行分片数
        leader_election: Leader选举实例
        job_sharding: 任务分片实例
        job_logger: 任务日志实例
    """

    JOB_NAME_MAPPING = {
        'training_job': {'type': 'training', 'need_leader': True},
        'prediction_job': {'type': 'prediction', 'need_leader': True, 'enable_sharding': True},
        'monthly_prediction_job': {'type': 'monthly_prediction', 'need_leader': True, 'enable_sharding': True},
        'alert_upgrade_job': {'type': 'alert_upgrade', 'need_leader': False},
        'audit_cleanup_job': {'type': 'audit_cleanup', 'need_leader': False},
    }

    def __init__(self):
        """初始化增强版调度器"""
        scheduler_config = config.get('scheduler', {})
        self.enable_leader_election = scheduler_config.get('enable_leader_election', True)
        self.enable_sharding = scheduler_config.get('enable_sharding', True)
        self.shard_count = scheduler_config.get('shard_count', 4)
        self.max_parallel_shards = scheduler_config.get('max_parallel_shards', 4)

        self.leader_election = leader_election
        self.job_sharding = job_sharding
        self.job_logger = job_execution_logger

        self._shutdown = False

        logger.info(
            f"增强版调度器初始化完成: "
            f"Leader选举={'启用' if self.enable_leader_election else '禁用'}, "
            f"任务分片={'启用' if self.enable_sharding else '禁用'}, "
            f"分片数={self.shard_count}"
        )

    def _should_run_job(
        self,
        job_name: str,
        trigger_type: str = 'scheduled',
        manual_params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        执行任务包装器，包含Leader选举检查、日志记录、分片处理

        Args:
            job_name: 任务名称
            trigger_type: 触发类型 scheduled/manual
            manual_params: 手动触发参数

        Returns:
            bool: 是否成功执行
        """
        job_config = self.JOB_NAME_MAPPING.get(job_name, {})
        job_type = job_config.get('type', job_name)
        need_leader = job_config.get('need_leader', False)
        enable_sharding = job_config.get('enable_sharding', False)

        log_id = None
        try:
            if need_leader and self.enable_leader_election:
                if not self.leader_election.try_acquire_leadership(job_name):
                    logger.info(f"不是Leader，跳过任务: {job_name}")
                    return False

            log_id = self.job_logger.start_job(
                job_name=job_name,
                job_type=job_type,
                trigger_type=trigger_type,
            )

            if log_id is None:
                logger.warning(f"无法创建任务日志，继续执行: {job_name}")

            if enable_sharding and self.enable_sharding and job_type == 'prediction':
                success, total, success_count, fail_count = self._execute_sharded_prediction(
                    job_name=job_name,
                    job_type=job_type,
                    log_id=log_id,
                    manual_params=manual_params or {},
                )
            else:
                success, total, success_count, fail_count = self._execute_regular_job(
                    job_name=job_name,
                    job_type=job_type,
                    log_id=log_id,
                    manual_params=manual_params or {},
                )

            if log_id is not None:
                if success:
                    self.job_logger.complete_job(
                        log_id=log_id,
                        status='completed',
                        total_nodes=total,
                        success_count=success_count,
                        failed_count=fail_count,
                    )
                else:
                    self.job_logger.fail_job(
                        log_id=log_id,
                        error_message="任务执行失败",
                        total_nodes=total,
                        success_count=success_count,
                        failed_count=fail_count,
                    )

            return success

        except Exception as e:
            logger.error(f"任务执行异常: {job_name}, 错误: {e}")
            if log_id is not None:
                self.job_logger.fail_job(
                    log_id=log_id,
                    error_message=str(e),
                )
            return False
        finally:
            if need_leader and self.enable_leader_election:
                self.leader_election.release_leadership(job_name)

    def _execute_sharded_prediction(
        self,
        job_name: str,
        job_type: str,
        log_id: Optional[int],
        manual_params: Dict[str, Any],
    ) -> tuple[bool, int, int, int]:
        """
        执行分片预测任务

        Args:
            job_name: 任务名称
            job_type: 任务类型
            log_id: 日志ID
            manual_params: 手动参数

        Returns:
            tuple: (是否成功, 总节点数, 成功数, 失败数)
        """
        from app.services.prediction_service import PredictionService
        from app.services.training_service import TrainingService

        logger.info(f"开始执行分片预测任务: {job_name}")

        training_service = TrainingService()
        prediction_service = PredictionService()

        bolt_ids = training_service._get_all_bolt_ids()
        flange_ids = training_service._get_all_flange_ids()

        logger.info(f"获取到螺栓数: {len(bolt_ids)}, 法兰面数: {len(flange_ids)}")

        total_nodes = len(bolt_ids) + len(flange_ids)
        total_success = 0
        total_failed = 0
        error_details = {}

        shards = self.job_sharding.create_shards(
            bolt_ids=bolt_ids,
            shard_count=self.shard_count,
        )

        logger.info(f"任务分片完成，共{len(shards)}个分片")

        shard_results = []
        with ThreadPoolExecutor(max_workers=self.max_parallel_shards) as executor:
            future_to_shard = {}
            for shard in shards:
                future = executor.submit(
                    self._process_prediction_shard,
                    shard=shard,
                    job_name=job_name,
                    prediction_service=prediction_service,
                    flange_ids=flange_ids,
                    manual_params=manual_params,
                )
                future_to_shard[future] = shard

            for future in as_completed(future_to_shard):
                shard = future_to_shard[future]
                try:
                    result = future.result()
                    shard_results.append(result)
                except Exception as e:
                    logger.error(f"分片执行异常: 分片{shard.shard_index}, 错误: {e}")
                    shard_results.append({
                        'shard_index': shard.shard_index,
                        'success': False,
                        'total': shard.bolt_count,
                        'success_count': 0,
                        'fail_count': shard.bolt_count,
                        'error': str(e),
                    })

        for result in shard_results:
            total_success += result.get('success_count', 0)
            total_failed += result.get('fail_count', 0)
            if result.get('error'):
                error_details[f"shard_{result['shard_index']}"] = result['error']

        logger.info(
            f"分片预测任务完成: 总计{total_nodes}个节点, "
            f"成功{total_success}个, 失败{total_failed}个"
        )

        return True, total_nodes, total_success, total_failed

    def _process_prediction_shard(
        self,
        shard: ShardInfo,
        job_name: str,
        prediction_service: Any,
        flange_ids: List[str],
        manual_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        处理单个预测分片

        Args:
            shard: 分片信息
            job_name: 任务名称
            prediction_service: 预测服务
            flange_ids: 法兰面ID列表
            manual_params: 手动参数

        Returns:
            Dict[str, Any]: 处理结果
        """
        shard_log_id = self.job_logger.start_job(
            job_name=f"{job_name}_shard_{shard.shard_index}",
            job_type='prediction_shard',
            trigger_type=manual_params.get('trigger_type', 'scheduled'),
            shard_index=shard.shard_index,
            shard_total=shard.shard_total,
            bolt_id_min=str(shard.bolt_id_min) if shard.bolt_id_min is not None else None,
            bolt_id_max=str(shard.bolt_id_max) if shard.bolt_id_max is not None else None,
        )

        success_count = 0
        fail_count = 0
        error_messages = []

        try:
            logger.info(
                f"开始处理分片[{shard.shard_index}/{shard.shard_total}]: "
                f"bolt数={shard.bolt_count}, "
                f"范围=[{shard.bolt_id_min}, {shard.bolt_id_max}]"
            )

            for bolt_id in shard.bolt_ids:
                try:
                    data = self._fetch_bolt_data(bolt_id)
                    if data is not None and len(data) >= 10:
                        prediction_service.predict_bolt(
                            bolt_id=bolt_id,
                            data=data[:, 1].astype(float),
                            timestamps=data[:, 0].tolist(),
                            save_to_db=True,
                        )
                        success_count += 1
                    else:
                        fail_count += 1
                except Exception as e:
                    fail_count += 1
                    error_messages.append(f"bolt {bolt_id}: {str(e)}")

            if shard_log_id is not None:
                self.job_logger.complete_job(
                    log_id=shard_log_id,
                    status='completed',
                    total_nodes=shard.bolt_count,
                    success_count=success_count,
                    failed_count=fail_count,
                    error_summary={'error_count': len(error_messages)},
                    error_details=error_messages[:10] if error_messages else None,
                )

            return {
                'shard_index': shard.shard_index,
                'success': True,
                'total': shard.bolt_count,
                'success_count': success_count,
                'fail_count': fail_count,
            }

        except Exception as e:
            logger.error(f"分片处理失败: {shard.shard_index}, 错误: {e}")
            if shard_log_id is not None:
                self.job_logger.fail_job(
                    log_id=shard_log_id,
                    error_message=str(e),
                    total_nodes=shard.bolt_count,
                    success_count=success_count,
                    failed_count=shard.bolt_count - success_count,
                )
            return {
                'shard_index': shard.shard_index,
                'success': False,
                'total': shard.bolt_count,
                'success_count': success_count,
                'fail_count': shard.bolt_count - success_count,
                'error': str(e),
            }

    def _fetch_bolt_data(self, bolt_id: str) -> Optional[Any]:
        """
        获取螺栓数据

        Args:
            bolt_id: 螺栓ID

        Returns:
            Optional[np.ndarray]: 螺栓数据
        """
        try:
            from app.utils.database import get_bolt_recent_data
            data = get_bolt_recent_data(int(bolt_id), limit=100)
            if data and len(data) >= 10:
                import numpy as np
                result = []
                for d in data:
                    result.append([d.create_time.strftime('%Y-%m-%d %H:%M:%S'), d.ptf])
                return np.array(result)
            return None
        except Exception as e:
            logger.warning(f"获取螺栓数据失败: {bolt_id}, 错误: {e}")
            return None

    def _execute_regular_job(
        self,
        job_name: str,
        job_type: str,
        log_id: Optional[int],
        manual_params: Dict[str, Any],
    ) -> tuple[bool, int, int, int]:
        """
        执行普通任务（不分片）

        Args:
            job_name: 任务名称
            job_type: 任务类型
            log_id: 日志ID
            manual_params: 手动参数

        Returns:
            tuple: (是否成功, 总节点数, 成功数, 失败数)
        """
        logger.info(f"开始执行普通任务: {job_name}")

        try:
            if job_type == 'training':
                return self._execute_training_job(manual_params)
            elif job_type == 'monthly_prediction':
                return self._execute_monthly_prediction_job(manual_params)
            elif job_type == 'alert_upgrade':
                return self._execute_alert_upgrade_job(manual_params)
            elif job_type == 'audit_cleanup':
                return self._execute_audit_cleanup_job(manual_params)
            else:
                logger.warning(f"未知任务类型: {job_type}")
                return False, 0, 0, 0

        except Exception as e:
            logger.error(f"普通任务执行失败: {job_name}, 错误: {e}")
            return False, 0, 0, 0

    def _execute_training_job(self, manual_params: Dict[str, Any]) -> tuple[bool, int, int, int]:
        """执行训练任务"""
        from app.services.training_service import TrainingService

        service = TrainingService()
        force_retrain = manual_params.get('force_retrain', False)

        bolt_result = service.train_model('bolt', force_retrain=force_retrain)
        flange_result = service.train_model('flange', force_retrain=force_retrain)

        return True, 2, 2, 0

    def _execute_monthly_prediction_job(self, manual_params: Dict[str, Any]) -> tuple[bool, int, int, int]:
        """执行月度预测任务"""
        from app.services.prediction_service import PredictionService
        from app.services.training_service import TrainingService

        prediction_service = PredictionService()
        training_service = TrainingService()

        bolt_ids = training_service._get_all_bolt_ids()
        flange_ids = training_service._get_all_flange_ids()

        total = len(bolt_ids) + len(flange_ids)
        success = 0
        fail = 0

        for bolt_id in bolt_ids:
            try:
                prediction_service.forecast_monthly(
                    node_id=bolt_id,
                    node_type='bolt',
                    days=30,
                )
                success += 1
            except Exception as e:
                fail += 1
                logger.error(f"螺栓 {bolt_id} 月度预测失败: {e}")

        for flange_id in flange_ids:
            try:
                prediction_service.forecast_monthly(
                    node_id=flange_id,
                    node_type='flange',
                    days=30,
                )
                success += 1
            except Exception as e:
                fail += 1
                logger.error(f"法兰面 {flange_id} 月度预测失败: {e}")

        return True, total, success, fail

    def _execute_alert_upgrade_job(self, manual_params: Dict[str, Any]) -> tuple[bool, int, int, int]:
        """执行告警升级任务"""
        from app.services.alert import AlertService

        service = AlertService()
        upgraded_count = service.process_pending_upgrades()

        return True, upgraded_count, upgraded_count, 0

    def _execute_audit_cleanup_job(self, manual_params: Dict[str, Any]) -> tuple[bool, int, int, int]:
        """执行审计清理任务"""
        from app.services.audit import AuditService

        service = AuditService()
        cleaned_count = service.cleanup_expired()

        return True, cleaned_count, cleaned_count, 0

    def trigger_job(self, job_name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        手动触发任务

        Args:
            job_name: 任务名称
            params: 任务参数

        Returns:
            Dict[str, Any]: 触发结果
        """
        if job_name not in self.JOB_NAME_MAPPING:
            return {
                'success': False,
                'message': f'未知任务: {job_name}',
            }

        logger.info(f"手动触发任务: {job_name}")

        from threading import Thread

        def _run_in_background():
            self._should_run_job(
                job_name=job_name,
                trigger_type='manual',
                manual_params=params or {},
            )

        thread = Thread(target=_run_in_background, daemon=True)
        thread.start()

        return {
            'success': True,
            'message': f'任务 {job_name} 已触发执行',
            'job_name': job_name,
            'trigger_time': datetime.now().isoformat(),
        }

    def start(self) -> None:
        """启动增强功能（心跳线程等）"""
        logger.info("增强版调度器已启动，Leader选举将在任务执行时自动激活")

    def stop(self) -> None:
        """停止增强功能"""
        self._shutdown = True
        if self.enable_leader_election:
            for job_name in list(self.leader_election._heartbeat_threads.keys()):
                self.leader_election.release_leadership(job_name)
        logger.info("增强版调度器已停止")


enhanced_scheduler = EnhancedTaskScheduler()
