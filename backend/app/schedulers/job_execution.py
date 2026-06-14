"""
任务执行日志与编排模块

负责任务执行的日志记录、错误摘要统计、任务上下文管理。

主要功能:
1. JobExecutionRepository: 任务执行日志的数据库操作
2. JobExecutionService: 任务执行日志的业务逻辑
3. JobExecutionContext: 任务执行上下文管理器（with语法）
4. ErrorSummary: 错误摘要统计工具

使用示例:
    from app.schedulers.job_execution import JobExecutionService, job_execution_context
    
    service = JobExecutionService()
    
    with job_execution_context(
        job_name='prediction_job',
        job_type='prediction',
        trigger_type='scheduled'
    ) as ctx:
        # 执行任务
        for bolt_id in bolt_ids:
            try:
                predict(bolt_id)
                ctx.record_success()
            except Exception as e:
                ctx.record_failure(bolt_id, str(e), type(e).__name__)
"""

import json
import uuid
import socket
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import Dict, List, Optional, Any, Tuple, Generator
from collections import defaultdict
from dataclasses import dataclass, field
from loguru import logger

from app.utils.database import get_db, JobExecutionLog
from app.utils.config import config


@dataclass
class ErrorSummary:
    """
    错误摘要统计

    统计任务执行过程中的各类错误，用于生成错误摘要。
    """
    total_errors: int = 0
    error_types: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    error_messages: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    failed_node_ids: List[str] = field(default_factory=list)

    def add_error(self, node_id: str, error_type: str, error_message: str, max_messages_per_type: int = 10) -> None:
        """
        添加一条错误记录

        Args:
            node_id: 节点ID
            error_type: 错误类型（异常类名）
            error_message: 错误信息
            max_messages_per_type: 每种错误类型最多保存的消息数
        """
        self.total_errors += 1
        self.error_types[error_type] += 1
        self.failed_node_ids.append(node_id)

        if len(self.error_messages[error_type]) < max_messages_per_type:
            self.error_messages[error_type].append(error_message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于JSON序列化"""
        return {
            'total_errors': self.total_errors,
            'error_types': dict(self.error_types),
            'error_samples': {
                err_type: msgs[:5]
                for err_type, msgs in self.error_messages.items()
            },
            'failed_node_ids': self.failed_node_ids[:20],
            'failed_node_count': len(self.failed_node_ids),
        }

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def is_empty(self) -> bool:
        """是否没有错误"""
        return self.total_errors == 0


class JobExecutionRepository:
    """
    任务执行日志数据仓库

    封装所有与任务执行日志相关的数据库操作。
    """

    def create_log(
        self,
        job_name: str,
        job_type: str,
        trigger_type: str = 'scheduled',
        instance_id: Optional[str] = None,
        tenant_id: Optional[int] = None,
        shard_index: Optional[int] = None,
        shard_total: Optional[int] = None,
    ) -> int:
        """
        创建任务执行日志记录（开始执行）

        Args:
            job_name: 任务名称
            job_type: 任务类型
            trigger_type: 触发类型
            instance_id: 执行实例ID
            tenant_id: 租户ID
            shard_index: 分片索引
            shard_total: 总分片数

        Returns:
            int: 创建的日志记录ID
        """
        with get_db() as db:
            if db is None:
                logger.warning("数据库不可用，跳过任务日志创建")
                return 0

            log = JobExecutionLog(
                job_name=job_name,
                job_type=job_type,
                trigger_type=trigger_type,
                status='running',
                start_time=datetime.now(),
                instance_id=instance_id or get_instance_id(),
                tenant_id=tenant_id,
                shard_index=shard_index,
                shard_total=shard_total,
            )
            db.add(log)
            db.flush()
            return log.id

    def update_log(
        self,
        log_id: int,
        status: str,
        total_nodes: int = 0,
        success_count: int = 0,
        failed_count: int = 0,
        skipped_count: int = 0,
        bolt_id_min: Optional[str] = None,
        bolt_id_max: Optional[str] = None,
        error_summary: Optional[str] = None,
        error_details: Optional[str] = None,
    ) -> None:
        """
        更新任务执行日志记录

        Args:
            log_id: 日志记录ID
            status: 状态: running/completed/failed/skipped
            total_nodes: 处理节点总数
            success_count: 成功节点数
            failed_count: 失败节点数
            skipped_count: 跳过节点数
            bolt_id_min: 处理的最小bolt_id
            bolt_id_max: 处理的最大bolt_id
            error_summary: 错误摘要（JSON）
            error_details: 错误详情（JSON）
        """
        with get_db() as db:
            if db is None or log_id == 0:
                logger.warning("数据库不可用或log_id无效，跳过任务日志更新")
                return

            log = db.query(JobExecutionLog).filter(JobExecutionLog.id == log_id).first()
            if not log:
                logger.warning(f"任务日志不存在: {log_id}")
                return

            end_time = datetime.now()
            duration = (end_time - log.start_time).total_seconds() if log.start_time else 0

            log.status = status
            log.end_time = end_time
            log.duration_seconds = int(duration)
            log.total_nodes = total_nodes
            log.success_count = success_count
            log.failed_count = failed_count
            log.skipped_count = skipped_count
            log.bolt_id_min = bolt_id_min
            log.bolt_id_max = bolt_id_max
            log.error_summary = error_summary
            log.error_details = error_details

    def mark_skipped(
        self,
        log_id: int,
        reason: str,
    ) -> None:
        """
        标记任务为跳过（如未获得Leader锁）

        Args:
            log_id: 日志记录ID
            reason: 跳过原因
        """
        self.update_log(
            log_id=log_id,
            status='skipped',
            error_summary=json.dumps({'reason': reason}, ensure_ascii=False),
        )

    def get_recent_logs(
        self,
        job_name: Optional[str] = None,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        获取最近的任务执行日志

        Args:
            job_name: 任务名称过滤
            job_type: 任务类型过滤
            status: 状态过滤
            limit: 返回数量

        Returns:
            List[Dict]: 日志列表
        """
        with get_db() as db:
            if db is None:
                return []

            query = db.query(JobExecutionLog)

            if job_name:
                query = query.filter(JobExecutionLog.job_name == job_name)
            if job_type:
                query = query.filter(JobExecutionLog.job_type == job_type)
            if status:
                query = query.filter(JobExecutionLog.status == status)

            logs = query.order_by(JobExecutionLog.start_time.desc()).limit(limit).all()

            return [self._log_to_dict(log) for log in logs]

    def get_log_by_id(self, log_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取任务执行日志

        Args:
            log_id: 日志ID

        Returns:
            Dict: 日志详情
        """
        with get_db() as db:
            if db is None:
                return None

            log = db.query(JobExecutionLog).filter(JobExecutionLog.id == log_id).first()
            if not log:
                return None

            return self._log_to_dict(log)

    def _log_to_dict(self, log: JobExecutionLog) -> Dict[str, Any]:
        """将ORM对象转换为字典"""
        data = {
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
                data['error_summary'] = json.loads(log.error_summary)
            except Exception:
                data['error_summary'] = log.error_summary

        if log.error_details:
            try:
                data['error_details'] = json.loads(log.error_details)
            except Exception:
                data['error_details'] = log.error_details

        return data


class JobExecutionService:
    """
    任务执行服务

    提供任务执行日志的高层业务操作。
    """

    def __init__(self):
        self.repository = JobExecutionRepository()

    def start_execution(
        self,
        job_name: str,
        job_type: str,
        trigger_type: str = 'scheduled',
        shard_index: Optional[int] = None,
        shard_total: Optional[int] = None,
    ) -> int:
        """
        开始任务执行，创建日志记录

        Args:
            job_name: 任务名称
            job_type: 任务类型
            trigger_type: 触发类型
            shard_index: 分片索引
            shard_total: 总分片数

        Returns:
            int: 日志ID
        """
        return self.repository.create_log(
            job_name=job_name,
            job_type=job_type,
            trigger_type=trigger_type,
            shard_index=shard_index,
            shard_total=shard_total,
        )

    def complete_execution(
        self,
        log_id: int,
        total_nodes: int,
        success_count: int,
        failed_count: int,
        skipped_count: int = 0,
        bolt_id_min: Optional[str] = None,
        bolt_id_max: Optional[str] = None,
        error_summary: Optional[ErrorSummary] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        完成任务执行，更新日志记录

        Args:
            log_id: 日志ID
            total_nodes: 总节点数
            success_count: 成功节点数
            failed_count: 失败节点数
            skipped_count: 跳过节点数
            bolt_id_min: 最小bolt_id
            bolt_id_max: 最大bolt_id
            error_summary: 错误摘要对象
            error_details: 错误详情字典
        """
        status = 'completed' if failed_count == 0 else 'failed'

        summary_json = None
        if error_summary and not error_summary.is_empty():
            summary_json = error_summary.to_json()

        details_json = None
        if error_details:
            details_json = json.dumps(error_details, ensure_ascii=False)

        self.repository.update_log(
            log_id=log_id,
            status=status,
            total_nodes=total_nodes,
            success_count=success_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            bolt_id_min=bolt_id_min,
            bolt_id_max=bolt_id_max,
            error_summary=summary_json,
            error_details=details_json,
        )

    def fail_execution(
        self,
        log_id: int,
        error_type: str,
        error_message: str,
        total_nodes: int = 0,
    ) -> None:
        """
        标记任务执行失败

        Args:
            log_id: 日志ID
            error_type: 错误类型
            error_message: 错误信息
            total_nodes: 已处理的节点数
        """
        error_summary = ErrorSummary()
        error_summary.add_error('__task__', error_type, error_message)

        self.repository.update_log(
            log_id=log_id,
            status='failed',
            total_nodes=total_nodes,
            error_summary=error_summary.to_json(),
        )

    def skip_execution(self, log_id: int, reason: str) -> None:
        """
        标记任务跳过

        Args:
            log_id: 日志ID
            reason: 跳过原因
        """
        self.repository.mark_skipped(log_id, reason)

    def get_recent_logs(
        self,
        job_name: Optional[str] = None,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """获取最近的任务执行日志"""
        return self.repository.get_recent_logs(job_name, job_type, status, limit)

    def get_log_by_id(self, log_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取任务执行日志"""
        return self.repository.get_log_by_id(log_id)


class JobExecutionContext:
    """
    任务执行上下文管理器

    使用with语法自动管理任务执行日志的创建和更新。
    """

    def __init__(
        self,
        job_name: str,
        job_type: str,
        trigger_type: str = 'scheduled',
        service: Optional[JobExecutionService] = None,
        shard_index: Optional[int] = None,
        shard_total: Optional[int] = None,
    ):
        self.job_name = job_name
        self.job_type = job_type
        self.trigger_type = trigger_type
        self.service = service or JobExecutionService()
        self.shard_index = shard_index
        self.shard_total = shard_total

        self.log_id: int = 0
        self.start_time: Optional[datetime] = None
        self.total_nodes: int = 0
        self.success_count: int = 0
        self.failed_count: int = 0
        self.skipped_count: int = 0
        self.bolt_id_min: Optional[str] = None
        self.bolt_id_max: Optional[str] = None
        self.error_summary = ErrorSummary()
        self.node_ids_processed: List[str] = []

    def __enter__(self) -> 'JobExecutionContext':
        self.log_id = self.service.start_execution(
            job_name=self.job_name,
            job_type=self.job_type,
            trigger_type=self.trigger_type,
            shard_index=self.shard_index,
            shard_total=self.shard_total,
        )
        self.start_time = datetime.now()
        logger.info(
            f"任务开始执行: {self.job_name}, log_id={self.log_id}, "
            f"trigger={self.trigger_type}, "
            f"shard={self.shard_index}/{self.shard_total}"
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            logger.error(f"任务执行异常: {self.job_name}, error={exc_val}")
            if self.log_id > 0:
                self.service.fail_execution(
                    log_id=self.log_id,
                    error_type=exc_type.__name__,
                    error_message=str(exc_val),
                    total_nodes=self.total_nodes,
                )
            return False

        if self.log_id > 0:
            self.service.complete_execution(
                log_id=self.log_id,
                total_nodes=self.total_nodes,
                success_count=self.success_count,
                failed_count=self.failed_count,
                skipped_count=self.skipped_count,
                bolt_id_min=self.bolt_id_min,
                bolt_id_max=self.bolt_id_max,
                error_summary=self.error_summary,
            )

        duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        logger.info(
            f"任务执行完成: {self.job_name}, "
            f"total={self.total_nodes}, success={self.success_count}, "
            f"failed={self.failed_count}, skipped={self.skipped_count}, "
            f"duration={duration:.1f}s"
        )
        return True

    def record_node(self, node_id: str) -> None:
        """记录处理的节点ID，用于统计bolt_id范围"""
        self.total_nodes += 1
        self.node_ids_processed.append(node_id)

        if self.bolt_id_min is None or node_id < self.bolt_id_min:
            self.bolt_id_min = node_id
        if self.bolt_id_max is None or node_id > self.bolt_id_max:
            self.bolt_id_max = node_id

    def record_success(self, node_id: Optional[str] = None) -> None:
        """记录成功处理的节点"""
        if node_id:
            self.record_node(node_id)
        self.success_count += 1

    def record_failure(
        self,
        node_id: str,
        error_message: str,
        error_type: str = 'Exception',
    ) -> None:
        """
        记录失败的节点

        Args:
            node_id: 节点ID
            error_message: 错误信息
            error_type: 错误类型
        """
        self.record_node(node_id)
        self.failed_count += 1
        self.error_summary.add_error(node_id, error_type, error_message)

    def record_skipped(self, node_id: str, reason: str = 'skipped') -> None:
        """记录跳过的节点"""
        self.record_node(node_id)
        self.skipped_count += 1


@contextmanager
def job_execution_context(
    job_name: str,
    job_type: str,
    trigger_type: str = 'scheduled',
    service: Optional[JobExecutionService] = None,
    shard_index: Optional[int] = None,
    shard_total: Optional[int] = None,
) -> Generator[JobExecutionContext, None, None]:
    """
    任务执行上下文管理器的便捷函数

    Args:
        job_name: 任务名称
        job_type: 任务类型
        trigger_type: 触发类型
        service: 任务执行服务实例
        shard_index: 分片索引
        shard_total: 总分片数

    Yields:
        JobExecutionContext: 任务执行上下文

    Example:
        with job_execution_context('prediction_job', 'prediction') as ctx:
            for bolt_id in bolt_ids:
                try:
                    predict(bolt_id)
                    ctx.record_success(bolt_id)
                except Exception as e:
                    ctx.record_failure(bolt_id, str(e), type(e).__name__)
    """
    ctx = JobExecutionContext(
        job_name=job_name,
        job_type=job_type,
        trigger_type=trigger_type,
        service=service,
        shard_index=shard_index,
        shard_total=shard_total,
    )
    try:
        yield ctx.__enter__()
    except Exception:
        ctx.__exit__(*__import__('sys').exc_info())
        raise
    else:
        ctx.__exit__(None, None, None)


_instance_id: Optional[str] = None


def get_instance_id() -> str:
    """
    获取当前实例的唯一标识符

    用于集群环境下区分不同的执行实例。
    格式: hostname-pid-uuid_prefix
    """
    global _instance_id
    if _instance_id is None:
        hostname = socket.gethostname()
        pid = __import__('os').getpid()
        short_uuid = str(uuid.uuid4())[:8]
        _instance_id = f"{hostname}-{pid}-{short_uuid}"
    return _instance_id
