"""
RiskAssessment API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class RiskAssessmentClient(BaseAPIClient):
    """RiskAssessment API 客户端"""

    async def assess_risk_api_v1_risk_assess_post(
        self,
        body: RiskAssessmentRequest,
        validation_mode: Optional[str] = None
) -> RiskAssessmentResponse:
        """
        风险评估

        评估节点（螺栓或法兰面）的风险
        
        返回风险评分(1-10)、风险等级(低/中/高)、概率分布P(高/中/低)和各因子贡献度。
        
        校验模式:
        - strict: 严格模式，数据不合规直接拒绝
        - lenient: 宽松模式，自动截断/填充数据
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/risk/assess",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
            params={
                "validation_mode": validation_mode,
            },
        )

        return response

    async def assess_risk_explain_api_v1_risk_assess_explain_post(
        self,
        body: RiskAssessExplainRequest,
        validation_mode: Optional[str] = None
) -> RiskAssessExplainResponse:
        """
        风险评估可解释性分析

        风险评估可解释性分析（类似 SHAP）
        
        返回各因子对风险评分的贡献度，包含：
        - 概率分布 P(高/中/低)
        - 各因子贡献度（原始评分、权重、加权评分、贡献占比、方向）
        - 基准值与总贡献偏移
        - 可读性总结
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/risk/assess/explain",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
            params={
                "validation_mode": validation_mode,
            },
        )

        return response

    async def update_risk_calibration_api_v1_risk_calibration_post(
        self,
        body: RiskCalibrationUpdateRequest
) -> RiskCalibrationResponse:
        """
        更新节点级风险校准配置

        更新节点级风险模型校准（权重/阈值覆盖）
        
        - 设置后该节点使用自定义权重和阈值
        - 不设置则使用全局配置
        - 支持版本管理与回滚
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/risk/calibration",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_risk_calibration_api_v1_risk_calibration_get(
        self,
        node_type: str,
        node_id: str
) -> RiskCalibrationResponse:
        """
        查询节点级风险校准配置

        查询节点级风险模型校准配置
        
        返回该节点生效的权重和阈值配置（含节点级覆盖）。
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/risk/calibration",
            params={
                "node_type": node_type,
                "node_id": node_id,
            },
        )

        return response
