"""
任务执行日志模块

负责记录每次任务执行的详细信息，包括任务起止、处理节点数、成功/失败数、错误摘要等。

主要功能:
1. 创建任务执行日志记录
2. 更新任务执行状态和统计信息
3. 查询历史执行记录
4. 错误摘要聚合

使用示例:
    from app.schedulers.job_logger import JobExecutionLogger
    
    logger = JobExecutionLogger()
    log_id = logger.start_job(
        job_name='prediction_job',
        job_type='prediction',
        trigger_type='scheduled'
    )
    # 执行任务...
    logger.complete_job(
        log_id=log_id,
        success_count=100,
        failed_count=2,
        error_summary={'error_type': 'count'
    )
"""

import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from loguru import logger

from app.utils.database import get_db, JobExecutionLog
from app.schedulers.leader_election import leader_election


class JobExecutionLogger:
    """
    任务执行日志类

    负责记录任务执行的完整生命周期日志。
    """

    def __init__(self):
        """初始化任务执行日志器"""
        self.instance_id = leader_election.instance_id
        logger.info(f"任务执行日志器初始化完成，实例ID: {self.instance_id}")

    def start_job(
        self,
        job_name: str,
        job_type: str,
        trigger_type: str = 'scheduled',
        shard_index: Optional[int] = None,
        shard_total: Optional[int] = None,
        bolt_id_min: Optional[str] = None,
        bolt_id_max: Optional[str] = None,
        extra_info: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[int] = None,
    ) -> Optional[int]:
        """
        记录任务开始

        Args:
            job_name: 任务名称
            job_type: 任务类型
            trigger_type: 触发类型 scheduled/manual
            shard_index: 分片索引
            shard_total: 总分片数
            bolt_id_min: 处理的最小bolt_id
            bolt_id_max: 处理的最大bolt_id
            extra_info: 扩展信息
            tenant_id: 租户ID

        Returns:
            Optional[int]: 日志记录ID，如果创建失败返回None
        """
        try:
            with get_db() as db:
                if db is None:
                    logger.warning(f"数据库不可用，无法记录任务开始: {job_name}")
                    return None

                log_entry = JobExecutionLog(
                    job_name=job_name,
                    job_type=job_type,
                    trigger_type=trigger_type,
                    status='running',
                    start_time=datetime.now(),
                    instance_id=self.instance_id,
                    shard_index=shard_index,
                    shard_total=shard_total,
                    bolt_id_min=bolt_id_min,
                    bolt_id_max=bolt_id_max,
                    extra_info=json.dumps(extra_info, ensure_ascii=False) if extra_info else None,
                    tenant_id=tenant_id,
                )

                db.add(log_entry)
                db.commit()
                db.refresh(log_entry)

                logger.info(
                    f"任务开始: {job_name}[{job_type}] 触发类型: {trigger_type} "
                    f"日志ID: {log_entry.id}"
                )

                return log_entry.id

        except Exception as e:
            logger.error(f"记录任务开始失败: {job_name}, 错误: {e}")
            return None

    def update_progress(
        self,
        log_id: int,
        total_nodes: Optional[int] = None,
        success_count: Optional[int] = None,
        failed_count: Optional[int] = None,
        skipped_count: Optional[int] = None,
        extra_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        更新任务进度

        Args:
            log_id: 日志ID
            total_nodes: 总节点数
            success_count: 成功数
            failed_count: 失败数
            skipped_count: 跳过数
            extra_info: 扩展信息

        Returns:
            bool: 是否更新成功
        """
        try:
            with get_db() as db:
                if db is None:
                    return False

                log_entry = db.query(JobExecutionLog).filter(
                    JobExecutionLog.id == log_id
                ).first()

                if log_entry is None:
                    logger.warning(f"任务日志不存在: {log_id}")
                    return False

                update_data = {}
                if total_nodes is not None:
                    update_data['total_nodes'] = total_nodes
                if success_count is not None:
                    update_data['success_count'] = success_count
                if failed_count is not None:
                    update_data['failed_count'] = failed_count
                if skipped_count is not None:
                    update_data['skipped_count'] = skipped_count
                if extra_info is not None:
                    current_extra = {}
                    if log_entry.extra_info:
                        try:
                            current_extra = json.loads(log_entry.extra_info)
                        except Exception:
                            current_extra = {}
                    current_extra.update(extra_info)
                    update_data['extra_info'] = json.dumps(current_extra, ensure_ascii=False)

                if update_data:
                    db.query(JobExecutionLog).filter(
                        JobExecutionLog.id == log_id
                    ).update(update_data)
                    db.commit()

                logger.debug(
                    f"任务进度更新: {log_id}, "
                    f"total={total_nodes}, "
                    f"success={success_count}, "
                    f"failed={failed_count}"
                )

                return True

        except Exception as e:
            logger.error(f"更新任务进度失败: {log_id}, 错误: {e}")
            return False

    def complete_job(
        self,
        log_id: int,
        status: str = 'completed',
        total_nodes: Optional[int] = None,
        success_count: Optional[int] = None,
        failed_count: Optional[int] = None,
        skipped_count: Optional[int] = None,
        error_summary: Optional[Dict[str, Any]] = None,
        error_details: Optional[Dict[str, Any]] = None,
        extra_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        标记任务完成

        Args:
            log_id: 日志ID
            status: 完成状态 completed/failed/skipped
            total_nodes: 总节点数
            success_count: 成功数
            failed_count: 失败数
            skipped_count: 跳过数
            error_summary: 错误摘要
            error_details: 错误详情
            extra_info: 扩展信息

        Returns:
            bool: 是否更新成功
        """
        try:
            with get_db() as db:
                if db is None:
                    return False

                log_entry = db.query(JobExecutionLog).filter(
                    JobExecutionLog.id == log_id
                ).first()

                if log_entry is None:
                    logger.warning(f"任务日志不存在: {log_id}")
                    return False

                end_time = datetime.now()
                duration = None
                if log_entry.start_time:
                    duration = int((end_time - log_entry.start_time).total_seconds())

                update_data = {
                    'status': status,
                    'end_time': end_time,
                    'duration_seconds': duration,
                }

                if total_nodes is not None:
                    update_data['total_nodes'] = total_nodes
                if success_count is not None:
                    update_data['success_count'] = success_count
                if failed_count is not None:
                    update_data['failed_count'] = failed_count
                if skipped_count is not None:
                    update_data['skipped_count'] = skipped_count
                if error_summary is not None:
                    update_data['error_summary'] = json.dumps(error_summary, ensure_ascii=False)
                if error_details is not None:
                    update_data['error_details'] = json.dumps(error_details, ensure_ascii=False)
                if extra_info is not None:
                    current_extra = {}
                    if log_entry.extra_info:
                        try:
                            current_extra = json.loads(log_entry.extra_info)
                        except Exception:
                            current_extra = {}
                    current_extra.update(extra_info)
                    update_data['extra_info'] = json.dumps(current_extra, ensure_ascii=False)

                db.query(JobExecutionLog).filter(
                    JobExecutionLog.id == log_id
                ).update(update_data)
                db.commit()

                logger.info(
                    f"任务完成: {log_entry.job_name}[{log_entry.job_type}] "
                    f"状态: {status}, 时长: {duration}秒, "
                    f"成功: {success_count or 0}, 失败: {failed_count or 0}"
                )

                return True

        except Exception as e:
            logger.error(f"标记任务完成失败: {log_id}, 错误: {e}")
            return False

    def fail_job(
        self,
        log_id: int,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
        total_nodes: Optional[int] = None,
        success_count: Optional[int] = None,
        failed_count: Optional[int] = None,
    ) -> bool:
        """
        标记任务失败（快捷方法）

        Args:
            log_id: 日志ID
            error_message: 错误信息
            error_details: 错误详情
            total_nodes: 总节点数
            success_count: 成功数
            failed_count: 失败数

        Returns:
            bool: 是否更新成功
        """
        error_summary = {
            'error_type': type(error_message).__name__ if isinstance(error_message, Exception) else 'Unknown',
            'error_message': str(error_message),
        }

        return self.complete_job(
            log_id=log_id,
            status='failed',
            total_nodes=total_nodes,
            success_count=success_count,
            failed_count=failed_count,
            error_summary=error_summary,
            error_details=error_details,
        )

    def get_recent_logs(
        self,
        job_name: Optional[str] = None,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        查询最近的任务执行日志

        Args:
            job_name: 任务名称（可选）
            job_type: 任务类型（可选）
            status: 状态（可选）
            limit: 返回数量限制

        Returns:
            List[Dict[str, Any]]: 日志列表
        """
        try:
            with get_db() as db:
                if db is None:
                    return []

                query = db.query(JobExecutionLog).order_by(
                    JobExecutionLog.start_time.desc()
                )

                if job_name:
                    query = query.filter(JobExecutionLog.job_name == job_name)
                if job_type:
                    query = query.filter(JobExecutionLog.job_type == job_type)
                if status:
                    query = query.filter(JobExecutionLog.status == status)

                logs = query.limit(limit).all()

                result = []
                for log in logs:
                    log_dict = {
                        'id': log.id,
                        'job_name': log.job_name,
                        'job_type': log.job_type,
                        'trigger_type': log.trigger_type,
                        'status': log.status,
                        'start_time': log.start_time,
                        'end_time': log.end_time,
                        'duration_seconds': log.duration_seconds,
                        'total_nodes': log.total_nodes,
                        'success_count': log.success_count,
                        'failed_count': log.failed_count,
                        'skipped_count': log.skipped_count,
                        'shard_index': log.shard_index,
                        'shard_total': log.shard_total,
                        'bolt_id_min': log.bolt_id_min,
                        'bolt_id_max': log.bolt_id_max,
                        'instance_id': log.instance_id,
                        'tenant_id': log.tenant_id,
                        'create_time': log.create_time,
                    }
                    if log.error_summary:
                        try:
                            log_dict['error_summary'] = json.loads(log.error_summary)
                        except Exception:
                            log_dict['error_summary'] = log.error_summary
                    if log.extra_info:
                        try:
                            log_dict['extra_info'] = json.loads(log.extra_info)
                        except Exception:
                            log_dict['extra_info'] = None
                    result.append(log_dict)

                return result

        except Exception as e:
            logger.error(f"查询任务日志失败: {e}")
            return []

    def get_job_statistics(
        self,
        job_name: str,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        获取任务统计信息

        Args:
            job_name: 任务名称
            days: 统计天数

        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            from datetime import timedelta

            with get_db() as db:
                if db is None:
                    return {}

                start_date = datetime.now() - timedelta(days=days)

                logs = db.query(JobExecutionLog).filter(
                    JobExecutionLog.job_name == job_name,
                    JobExecutionLog.start_time >= start_date,
                ).all()

                total_executions = len(logs)
                completed = sum(1 for log in logs if log.status == 'completed')
                failed = sum(1 for log in logs if log.status == 'failed')
                total_success = sum(log.success_count or 0 for log in logs)
                total_failed = sum(log.failed_count or 0 for log in logs)
                total_duration = sum(log.duration_seconds or 0 for log in logs)

                avg_duration = total_duration / total_executions if total_executions > 0 else 0

                return {
                    'job_name': job_name,
                    'period_days': days,
                    'total_executions': total_executions,
                    'completed_count': completed,
                    'failed_count': failed,
                    'success_rate': (completed / total_executions * 100) if total_executions > 0 else 0,
                    'total_nodes_processed': total_success + total_failed,
                    'total_success': total_success,
                    'total_failed': total_failed,
                    'avg_duration_seconds': avg_duration,
                    'total_duration_seconds': total_duration,
                }

        except Exception as e:
            logger.error(f"获取任务统计失败: {e}")
            return {}


job_execution_logger = JobExecutionLogger()
