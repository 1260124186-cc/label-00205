"""
Scheduler API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class SchedulerClient(BaseAPIClient):
    """Scheduler API 客户端"""

    async def trigger_scheduler_job_by_name_api_v1_scheduler_trigger_job_name_post(
        self,
        job_name: str,
        require_leader: Optional[bool] = None,
        num_shards: Optional[Any] = None
) -> SchedulerTriggerResponse:
        """
        手动触发调度任务（按任务名称）

        按任务名称手动触发调度任务。
        
        支持的任务名称:
        - training_job: 模型训练
        - prediction_job: 预测任务（支持分片）
        - monthly_prediction_job: 月度预测
        - alert_upgrade_job: 告警升级
        - audit_cleanup_job: 审计清理
        
        Args:
            job_name: 任务名称
            require_leader: 是否需要Leader节点才能执行
            num_shards: 分片数（仅适用于prediction_job）
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/scheduler/trigger/{job_name}",
            params={
                "require_leader": require_leader,
                "num_shards": num_shards,
            },
        )

        return response

    async def get_job_execution_logs_api_v1_scheduler_logs_get(
        self,
        job_name: Optional[Any] = None,
        job_type: Optional[Any] = None,
        status: Optional[Any] = None,
        trigger_type: Optional[Any] = None,
        start_time_from: Optional[Any] = None,
        start_time_to: Optional[Any] = None,
        instance_id: Optional[Any] = None,
        has_errors: Optional[Any] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None
) -> JobExecutionLogListResponse:
        """
        查询任务执行日志列表

        查询任务执行日志列表
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/scheduler/logs",
            params={
                "job_name": job_name,
                "job_type": job_type,
                "status": status,
                "trigger_type": trigger_type,
                "start_time_from": start_time_from,
                "start_time_to": start_time_to,
                "instance_id": instance_id,
                "has_errors": has_errors,
                "page": page,
                "page_size": page_size,
            },
        )

        return response

    async def get_job_execution_log_detail_api_v1_scheduler_logs_log_id_get(
        self,
        log_id: int
) -> JobExecutionLogSchema:
        """
        获取任务执行日志详情

        获取单条任务执行日志详情
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/scheduler/logs/{log_id}",
        )

        return response

    async def get_leader_status_api_v1_scheduler_leader_job_key_get(
        self,
        job_key: str
) -> LeaderStatusSchema:
        """
        获取Leader选举状态

        获取指定任务的Leader选举状态
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/scheduler/leader/{job_key}",
        )

        return response
