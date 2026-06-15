"""
EdgeComputing API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class EdgeComputingClient(BaseAPIClient):
    """EdgeComputing API 客户端"""

    async def register_edge_device_api_v1_edge_device_register_post(
        self,
        body: EdgeDeviceRegisterRequest
) -> EdgeDeviceRegisterResponse:
        """
        注册边缘设备
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/edge/device/register",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def edge_device_heartbeat_api_v1_edge_device_heartbeat_post(
        self,
        body: EdgeDeviceHeartbeatRequest
) -> EdgeDeviceHeartbeatResponse:
        """
        边缘设备心跳
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/edge/device/heartbeat",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_edge_model_latest_api_v1_edge_model_latest_post(
        self,
        body: EdgeModelLatestRequest
) -> EdgeModelLatestResponse:
        """
        获取最新模型版本信息
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/edge/model/latest",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def download_edge_model_api_v1_edge_model_download_version_get(
        self,
        version: str,
        model_type: Optional[str] = None,
        node_id: Optional[Any] = None,
        format: Optional[str] = None
) -> Dict[str, Any]:
        """
        下载模型包
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/edge/model/download/{version}",
            params={
                "model_type": model_type,
                "node_id": node_id,
                "format": format,
            },
        )

        return response

    async def export_edge_model_api_v1_edge_model_export_post(
        self,
        body: EdgeModelExportRequest
) -> EdgeModelExportResponse:
        """
        导出边缘模型包
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/edge/model/export",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def upload_edge_predictions_api_v1_edge_predictions_upload_post(
        self,
        body: EdgePredictionUploadRequest
) -> EdgePredictionUploadResponse:
        """
        批量上报边缘预测结果
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/edge/predictions/upload",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def list_edge_devices_api_v1_edge_device_status_get(
        self
) -> Dict[str, Any]:
        """
        获取所有边缘设备状态
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/edge/device/status",
        )

        return response
