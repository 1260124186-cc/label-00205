"""
FederatedLearning API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class FederatedLearningClient(BaseAPIClient):
    """FederatedLearning API 客户端"""

    async def register_federated_client_api_v1_federated_client_register_post(
        self,
        body: FederatedClientRegisterRequest
) -> FederatedClientRegisterResponse:
        """
        注册联邦学习客户端

        注册联邦学习客户端（厂区）
        
        各厂区在参与联邦学习前需要先注册。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/federated/client/register",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_federated_server_status_api_v1_federated_server_status_get(
        self
) -> FederatedServerStatusResponse:
        """
        获取联邦学习服务器状态

        获取联邦学习服务器的整体状态
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/federated/server/status",
        )

        return response

    async def start_federated_round_api_v1_federated_round_start_post(
        self,
        body: FederatedRoundStartRequest
) -> FederatedRoundStartResponse:
        """
        开始联邦学习轮次

        开始新的联邦学习轮次
        
        由中心服务器启动，指定要训练的模型和参与的客户端。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/federated/round/start",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_federated_round_status_api_v1_federated_round_status_get(
        self
) -> Dict[str, Any]:
        """
        获取当前轮次状态

        获取当前进行中的联邦学习轮次状态
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/federated/round/status",
        )

        return response

    async def aggregate_federated_updates_api_v1_federated_round_aggregate_post(
        self,
        body: FederatedRoundAggregateRequest
) -> FederatedRoundAggregateResponse:
        """
        聚合并更新全局模型

        聚合各客户端的模型更新，生成新的全局模型
        
        在收集到足够的客户端更新后调用此接口。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/federated/round/aggregate",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_federated_model_history_api_v1_federated_model_history_model_type_node_id_get(
        self,
        model_type: str,
        node_id: str
) -> FederatedModelHistoryResponse:
        """
        获取全局模型历史

        获取全局模型的版本历史和性能指标
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/federated/model/history/{model_type}/{node_id}",
        )

        return response

    async def download_global_model_api_v1_federated_client_model_download_post(
        self,
        body: FederatedGlobalModelRequest
) -> FederatedGlobalModelResponse:
        """
        下载全局模型

        客户端下载全局模型
        
        各厂区在本地训练前下载最新的全局模型。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/federated/client/model/download",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def upload_model_update_api_v1_federated_client_update_upload_post(
        self,
        body: FederatedUpdateUploadRequest
) -> FederatedUpdateUploadResponse:
        """
        上传模型更新

        客户端上传本地训练后的模型更新
        
        可以上传完整权重、梯度或权重差异。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/federated/client/update/upload",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def distribute_global_model_api_v1_federated_client_model_distribute_model_type_node_id_post(
        self,
        model_type: str,
        node_id: str
) -> Dict[str, Any]:
        """
        分发最新全局模型

        分发最新聚合后的全局模型给所有客户端
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/federated/client/model/distribute/{model_type}/{node_id}",
        )

        return response

    async def get_federated_client_status_api_v1_federated_client_status_client_id_get(
        self,
        client_id: str
) -> FederatedClientStatusResponse:
        """
        获取客户端状态

        获取指定客户端的状态
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/federated/client/status/{client_id}",
        )

        return response

    async def local_train_federated_api_v1_federated_client_train_local_post(
        self,
        body: FederatedLocalTrainRequest
) -> FederatedLocalTrainResponse:
        """
        执行本地训练

        在客户端执行本地训练
        
        支持全量训练和本地微调（两层架构的第二层）。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/federated/client/train/local",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_client_model_update_api_v1_federated_client_update_get_client_id_post(
        self,
        client_id: str,
        apply_privacy: Optional[bool] = None
) -> Dict[str, Any]:
        """
        获取客户端模型更新（用于上传）

        获取客户端的模型更新，准备上传到服务器
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/federated/client/update/get/{client_id}",
            params={
                "apply_privacy": apply_privacy,
            },
        )

        return response

    async def configure_privacy_api_v1_federated_config_privacy_post(
        self,
        body: FederatedPrivacyConfig,
        client_id: str
) -> Dict[str, Any]:
        """
        配置隐私保护参数

        配置客户端的隐私保护参数
        
        支持差分隐私、安全聚合等机制。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/federated/config/privacy",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
            params={
                "client_id": client_id,
            },
        )

        return response

    async def configure_aggregator_api_v1_federated_config_aggregator_post(
        self,
        body: FederatedAggregatorConfig
) -> Dict[str, Any]:
        """
        配置聚合器参数

        配置服务器端的聚合器参数
        
        支持FedAvg、加权平均、中位数、修剪均值等聚合策略。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/federated/config/aggregator",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response
