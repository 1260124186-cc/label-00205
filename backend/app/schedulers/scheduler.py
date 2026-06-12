"""
任务调度器模块

基于APScheduler实现定时任务调度。

主要任务:
1. 模型训练任务 - 每周执行
2. 预测任务 - 每30分钟执行
3. 月度预测任务 - 每月执行

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
from typing import Optional
from loguru import logger

from app.utils.config import config


class TaskScheduler:
    """
    任务调度器类
    
    管理所有定时任务的调度和执行。
    
    Attributes:
        scheduler: APScheduler调度器实例
        config: 调度器配置
        is_running: 调度器是否正在运行
    """
    
    def __init__(self):
        """
        初始化任务调度器
        """
        self.config = config.get('scheduler', {})
        self.is_running = False
        
        # 配置作业存储和执行器
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': ThreadPoolExecutor(10)
        }
        job_defaults = {
            'coalesce': True,  # 合并多个排队的作业
            'max_instances': 1  # 同一作业最多同时运行一个实例
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults
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
        
        # 添加任务
        self._add_jobs()
        
        # 启动调度器
        self.scheduler.start()
        self.is_running = True
        
        logger.info("任务调度器已启动")
    
    def stop(self) -> None:
        """
        停止调度器
        """
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("任务调度器已停止")
    
    def _add_jobs(self) -> None:
        """
        添加定时任务
        """
        # 训练任务
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
        
        # 预测任务
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
        
        # 月度预测任务
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

        # 告警升级任务（每5分钟检查一次）
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

        # 审计过期清理任务（每天执行一次）
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
    
    def _training_job(self) -> None:
        """
        模型训练任务
        """
        logger.info("开始执行模型训练任务")
        
        try:
            from app.services.training_service import TrainingService
            
            service = TrainingService()
            
            # 训练螺栓模型
            bolt_result = service.train_model('bolt', force_retrain=False)
            logger.info(f"螺栓模型训练完成: {bolt_result.get('message')}")
            
            # 训练法兰面模型
            flange_result = service.train_model('flange', force_retrain=False)
            logger.info(f"法兰面模型训练完成: {flange_result.get('message')}")
            
        except Exception as e:
            logger.error(f"模型训练任务失败: {e}")
    
    def _prediction_job(self) -> None:
        """
        预测任务
        """
        logger.info("开始执行预测任务")
        
        try:
            from app.services.prediction_service import PredictionService
            
            service = PredictionService()
            
            # 批量预测螺栓
            service.batch_predict_from_db('bolt')
            
            # 批量预测法兰面
            service.batch_predict_from_db('flange')
            
            logger.info("预测任务执行完成")
            
        except Exception as e:
            logger.error(f"预测任务失败: {e}")
    
    def _monthly_prediction_job(self) -> None:
        """
        月度预测任务
        """
        logger.info("开始执行月度预测任务")
        
        try:
            from app.services.prediction_service import PredictionService
            from app.services.training_service import TrainingService
            
            prediction_service = PredictionService()
            training_service = TrainingService()
            
            # 获取所有节点
            bolt_ids = training_service._get_all_bolt_ids()
            flange_ids = training_service._get_all_flange_ids()
            
            # 预测所有螺栓
            for bolt_id in bolt_ids:
                try:
                    prediction_service.forecast_monthly(
                        node_id=bolt_id,
                        node_type='bolt',
                        days=30
                    )
                except Exception as e:
                    logger.error(f"螺栓 {bolt_id} 月度预测失败: {e}")
            
            # 预测所有法兰面
            for flange_id in flange_ids:
                try:
                    prediction_service.forecast_monthly(
                        node_id=flange_id,
                        node_type='flange',
                        days=30
                    )
                except Exception as e:
                    logger.error(f"法兰面 {flange_id} 月度预测失败: {e}")
            
            logger.info("月度预测任务执行完成")
            
        except Exception as e:
            logger.error(f"月度预测任务失败: {e}")

    def _alert_upgrade_job(self) -> None:
        """
        告警自动升级任务

        每5分钟扫描一次，超时未处理的告警自动升级。
        默认30分钟未处理升级（可由告警规则单独配置）。
        """
        logger.info("开始执行告警升级任务")

        try:
            from app.services.alert import AlertService

            alert_service = AlertService()
            upgraded_count = alert_service.process_pending_upgrades()

            if upgraded_count > 0:
                logger.info(f"告警升级任务完成，共升级 {upgraded_count} 条告警")
            else:
                logger.info("告警升级任务完成，无需升级的告警")

        except Exception as e:
            logger.error(f"告警升级任务失败: {e}")

    def _audit_cleanup_job(self) -> None:
        """
        审计过期记录清理任务

        按配置的保留年限自动清理过期的审计快照记录。
        """
        logger.info("开始执行审计过期记录清理任务")

        try:
            from app.services.audit import AuditService

            audit_service = AuditService()
            cleaned_count = audit_service.cleanup_expired()

            if cleaned_count > 0:
                logger.info(f"审计清理任务完成，共清理 {cleaned_count} 条过期记录")
            else:
                logger.info("审计清理任务完成，无过期记录")

        except Exception as e:
            logger.error(f"审计清理任务失败: {e}")
    
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
    
    def run_job_now(self, job_id: str) -> bool:
        """
        立即执行指定任务
        """
        job = self.scheduler.get_job(job_id)
        if job:
            job.modify(next_run_time=datetime.now())
            return True
        return False


# 全局调度器实例
scheduler = TaskScheduler()
