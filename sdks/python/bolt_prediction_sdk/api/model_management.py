"""
ModelManagement API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class ModelManagementClient(BaseAPIClient):
    """ModelManagement API 客户端"""

    async def train_model_api_v1_model_train_post(
        self,
        body: TrainingRequest
) -> TrainingResponse:
        """
        训练模型

        训练或重新训练模型
        
        可以选择训练特定节点的模型或所有模型。
        训练任务在后台执行。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/model/train",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_model_info_api_v1_model_info_model_type_node_id_get(
        self,
        model_type: str,
        node_id: str
) -> ModelInfoResponse:
        """
        获取模型信息

        获取指定模型的信息
        
        包括训练状态、最后训练时间、验证准确率、版本信息等。
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/model/info/{model_type}/{node_id}",
        )

        return response

    async def train_model_enhanced_api_v1_model_train_enhanced_post(
        self,
        body: EnhancedTrainingRequest
) -> EnhancedTrainingResponse:
        """
        增强版训练模型（增量训练/学习率调度/类不平衡等）

        增强版训练接口
        
        支持：
        - 增量训练（冻结部分层 + 新数据 fine-tune）
        - 可配置早停机制
        - 可配置学习率调度（ReduceLROnPlateau/StepLR/Cosine）
        - 类别不平衡处理（加权损失/过采样）
        - Focal Loss
        - 人工标注数据覆盖
        
        训练任务在后台执行，通过 session_id 查询进度和结果。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/model/train/enhanced",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_training_status_endpoint_api_v1_model_train_status_session_id_get(
        self,
        session_id: str
) -> TrainingStatusResponse:
        """
        查询训练状态

        根据 session_id 查询训练任务的状态和进度
        
        状态: pending → running → completed/failed
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/model/train/status/{session_id}",
        )

        return response

    async def list_training_sessions_api_v1_model_train_sessions_get(
        self,
        model_type: Optional[Any] = None,
        status: Optional[Any] = None,
        limit: Optional[int] = None
) -> TrainingSessionListResponse:
        """
        列出训练会话历史

        列出训练会话记录
        
        可按模型类型和状态过滤，默认返回最近50条。
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/model/train/sessions",
            params={
                "model_type": model_type,
                "status": status,
                "limit": limit,
            },
        )

        return response

    async def list_model_versions_api_v1_model_versions_model_type_node_id_get(
        self,
        model_type: str,
        node_id: str
) -> ModelVersionListResponse:
        """
        列出模型版本历史

        列出指定模型的所有版本
        
        包括版本号、创建时间、训练指标、是否活动版本等。
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/model/versions/{model_type}/{node_id}",
        )

        return response

    async def activate_model_version_api_v1_model_activate_post(
        self,
        body: ModelVersionActivateRequest
) -> ModelVersionSchema:
        """
        激活指定模型版本

        激活指定的模型版本（切换活动版本）
        
        通过 model_type、node_id 和 version 切换当前活动版本。
        激活后，后续预测将使用该版本的模型。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/model/activate",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def rollback_model_version_api_v1_model_rollback_post(
        self,
        body: ModelVersionRollbackRequest
) -> ModelVersionSchema:
        """
        回滚模型版本

        回滚到指定版本（或上一个版本）
        
        如果指定了 version，则回滚到该版本；
        如果未指定 version，则回滚到上一个版本。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/model/rollback",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def cleanup_old_versions_api_v1_model_versions_model_type_node_id_cleanup_post(
        self,
        model_type: str,
        node_id: str
) -> Dict[str, Any]:
        """
        手动清理旧版本

        手动清理超过 max_versions 限制的旧版本
        
        保留最新的 N 个版本（N = max_versions），删除其余非活动版本。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/model/versions/{model_type}/{node_id}/cleanup",
        )

        return response

    async def list_import_files_api_v1_model_label_import_files_get(
        self
) -> LabelImportFileListResponse:
        """
        列出可导入的标注CSV文件

        列出导入目录中所有可导入的CSV文件
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/model/label/import/files",
        )

        return response

    async def import_labels_from_csv_api_v1_model_label_import_csv_post(
        self,
        body: LabelImportCsvRequest
) -> LabelImportResponse:
        """
        从CSV导入人工标注数据

        从CSV文件导入人工标注数据
        
        人工标注数据的标签优先级高于系统自动生成的规则标签。
        
        CSV要求:
        - 节点ID列（如 bolt_id、传感器id 等，自动检测）
        - 标签列（数字 0-4 或中文标签名: 正常/关注级预警/检查级预警/紧急级预警/故障）
        - 可选: 数据点列、时间戳列、标注人列
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/model/label/import/csv",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def import_labels_from_db_api_v1_model_label_import_db_post(
        self,
        body: LabelImportDbRequest
) -> LabelImportResponse:
        """
        从数据库表导入人工标注数据

        从现有数据库表导入人工标注数据
        
        指定源表名、ID字段和标签字段，可带WHERE条件。
        导入的标注会覆盖规则标签。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/model/label/import/db",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_model_versions_api_v1_model_versions_model_type_model_id_get(
        self,
        model_type: str,
        model_id: str
) -> ModelVersionListResponse:
        """
        获取模型版本列表

        获取指定模型的所有版本列表
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/model/versions/{model_type}/{model_id}",
        )

        return response

    async def get_active_model_version_api_v1_model_versions_model_type_model_id_active_get(
        self,
        model_type: str,
        model_id: str
) -> ModelVersionSchema:
        """
        获取当前活动版本

        获取当前激活的模型版本
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/model/versions/{model_type}/{model_id}/active",
        )

        return response

    async def activate_model_version_api_v1_model_versions_model_type_model_id_activate_post(
        self,
        model_type: str,
        model_id: str,
        body: ModelVersionActivateRequest
) -> ModelVersionSchema:
        """
        激活/回滚模型版本

        激活指定版本（用于回滚或切换版本）
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/model/versions/{model_type}/{model_id}/activate",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def compare_model_versions_api_v1_model_versions_model_type_model_id_compare_post(
        self,
        model_type: str,
        model_id: str,
        body: ModelVersionCompareRequest
) -> ModelVersionCompareResponse:
        """
        对比两个模型版本

        对比两个模型版本的指标差异
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/model/versions/{model_type}/{model_id}/compare",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def delete_model_version_api_v1_model_versions_model_type_model_id_version_delete(
        self,
        model_type: str,
        model_id: str,
        version: str
) -> Dict[str, Any]:
        """
        删除模型版本

        删除指定的模型版本（不能删除活动版本）
        """

        response = await self._request(
            method="DELETE",
            path=f"/api/v1/api/v1/model/versions/{model_type}/{model_id}/{version}",
        )

        return response

    async def get_training_status_api_v1_model_training_status_get(
        self
) -> TrainingStatusResponse:
        """
        获取训练状态

        获取当前训练状态和最近的训练会话
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/model/training/status",
        )

        return response

    async def list_training_sessions_api_v1_model_training_sessions_get(
        self,
        limit: Optional[int] = None
) -> TrainingSessionListResponse:
        """
        获取训练会话列表

        获取历史训练会话列表
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/model/training/sessions",
            params={
                "limit": limit,
            },
        )

        return response

    async def get_training_session_api_v1_model_training_sessions_session_id_get(
        self,
        session_id: str
) -> TrainingSessionSchema:
        """
        获取训练会话详情

        获取指定训练会话的详细信息，包含训练曲线数据
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/model/training/sessions/{session_id}",
        )

        return response

    async def list_all_models_api_v1_model_list_get(
        self
) -> Dict[str, Any]:
        """
        获取所有模型列表

        获取系统中所有的模型列表
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/model/list",
        )

        return response
