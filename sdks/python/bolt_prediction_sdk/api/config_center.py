"""
ConfigCenter API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class ConfigCenterClient(BaseAPIClient):
    """ConfigCenter API 客户端"""

    async def get_config_center_api_v1_config_center_get(
        self
) -> ConfigCenterResponse:
        """
        获取所有配置中心数据

        获取预警策略、阈值、调度任务的所有配置
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/config/center",
        )

        return response

    async def update_warning_strategy_api_v1_config_warning_strategy_put(
        self,
        body: WarningStrategyConfigSchema
) -> WarningStrategyConfigSchema:
        """
        更新预警策略配置

        更新预警策略配置（策略类型、阈值等）
        """

        response = await self._request(
            method="PUT",
            path=f"/api/v1/api/v1/config/warning-strategy",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def update_thresholds_api_v1_config_thresholds_put(
        self,
        body: ThresholdConfigSchema
) -> ThresholdConfigSchema:
        """
        更新阈值配置

        更新风险阈值、预紧力阈值、偏差比例等
        """

        response = await self._request(
            method="PUT",
            path=f"/api/v1/api/v1/config/thresholds",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def list_scheduler_jobs_api_v1_config_scheduler_jobs_get(
        self
) -> List[ScheduledJobSchema]:
        """
        获取调度任务列表

        获取所有调度任务的配置和运行状态
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/config/scheduler/jobs",
        )

        return response

    async def update_scheduler_job_api_v1_config_scheduler_jobs_job_id_put(
        self,
        job_id: str,
        body: SchedulerJobUpdateRequest
) -> ScheduledJobSchema:
        """
        更新调度任务配置

        更新指定任务的 Cron 表达式或启用/禁用状态
        """

        response = await self._request(
            method="PUT",
            path=f"/api/v1/api/v1/config/scheduler/jobs/{job_id}",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def trigger_scheduler_job_api_v1_config_scheduler_jobs_job_id_trigger_post(
        self,
        job_id: str
) -> Dict[str, Any]:
        """
        手动触发调度任务

        立即执行指定的调度任务
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/config/scheduler/jobs/{job_id}/trigger",
        )

        return response
