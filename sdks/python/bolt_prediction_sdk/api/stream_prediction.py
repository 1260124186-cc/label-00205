"""
StreamPrediction API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class StreamPredictionClient(BaseAPIClient):
    """StreamPrediction API 客户端"""

    async def stream_ingest_api_v1_stream_ingest_post(
        self,
        body: StreamDataIngestRequest
) -> StreamDataIngestResponse:
        """
        流式数据注入

        注入单条或微批次流数据
        
        数据进入滑动窗口，窗口满后自动触发预测。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/stream/ingest",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def stream_ingest_batch_api_v1_stream_ingest_batch_post(
        self,
        body: StreamBatchIngestRequest
) -> StreamBatchIngestResponse:
        """
        批量流式数据注入

        批量注入多条流数据
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/stream/ingest/batch",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_stream_window_api_v1_stream_window_bolt_id_get(
        self,
        bolt_id: str
) -> StreamWindowStatusResponse:
        """
        获取窗口状态

        获取指定螺栓的滑动窗口状态
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/stream/window/{bolt_id}",
        )

        return response

    async def clear_stream_window_api_v1_stream_window_bolt_id_delete(
        self,
        bolt_id: str
) -> Dict[str, Any]:
        """
        清空指定螺栓窗口

        清空指定螺栓的滑动窗口数据
        """

        response = await self._request(
            method="DELETE",
            path=f"/api/v1/api/v1/stream/window/{bolt_id}",
        )

        return response

    async def get_stream_engine_status_api_v1_stream_status_get(
        self
) -> StreamEngineStatusResponse:
        """
        获取流式预测引擎状态

        获取流式预测引擎的运行状态和统计信息
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/stream/status",
        )

        return response

    async def switch_prediction_mode_api_v1_stream_mode_post(
        self,
        body: StreamModeSwitchRequest
) -> StreamModeSwitchResponse:
        """
        切换预测模式

        切换预测模式：batch 或 stream
        
        - batch: 批处理模式，流式数据被忽略
        - stream: 流式模式，启用实时预测
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/stream/mode",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def start_stream_engine_api_v1_stream_start_post(
        self
) -> Dict[str, Any]:
        """
        启动流式预测引擎

        启动流式预测引擎
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/stream/start",
        )

        return response

    async def stop_stream_engine_api_v1_stream_stop_post(
        self
) -> Dict[str, Any]:
        """
        停止流式预测引擎

        停止流式预测引擎
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/stream/stop",
        )

        return response

    async def update_stream_config_api_v1_stream_config_post(
        self,
        body: StreamConfigUpdateRequest
) -> StreamConfigResponse:
        """
        更新流式预测配置

        动态更新流式预测配置
        
        支持更新：窗口大小、最大并发流数、每流速率限制
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/stream/config",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def clear_all_stream_windows_api_v1_stream_windows_delete(
        self
) -> Dict[str, Any]:
        """
        清空所有窗口

        清空所有螺栓的滑动窗口数据
        """

        response = await self._request(
            method="DELETE",
            path=f"/api/v1/api/v1/stream/windows",
        )

        return response
