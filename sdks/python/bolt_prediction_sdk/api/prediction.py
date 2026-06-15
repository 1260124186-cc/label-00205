"""
Prediction API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class PredictionClient(BaseAPIClient):
    """Prediction API 客户端"""

    async def predict_bolt_api_v1_predict_bolt_post(
        self,
        body: BoltPredictionRequest,
        validation_mode: Optional[str] = None,
        version: Optional[Any] = None,
        shadow_version: Optional[Any] = None
) -> BoltPredictionResponse:
        """
        螺栓状态预测

        预测单个螺栓的状态
        
        基于最近100条预紧力数据，预测螺栓当前状态。
        
        状态类别:
        - 0: 正常
        - 1: 关注级预警
        - 2: 检查级预警
        - 3: 紧急级预警
        - 4: 故障
        
        校验模式:
        - strict: 严格模式，数据不合规直接拒绝
        - lenient: 宽松模式，自动截断/填充数据
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/predict/bolt",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
            params={
                "validation_mode": validation_mode,
                "version": version,
                "shadow_version": shadow_version,
            },
        )

        return response

    async def predict_bolt_ensemble_api_v1_predict_bolt_ensemble_post(
        self,
        body: BoltEnsemblePredictionRequest,
        validation_mode: Optional[str] = None
) -> BoltEnsemblePredictionResponse:
        """
        螺栓集成学习预测调试

        螺栓集成学习预测调试接口
        
        返回各子模型分项结果与最终融合结论，用于调试和分析集成学习效果。
        
        支持配置:
        - method: 投票策略 (hard/soft/weighted)
        - weights: 自定义各预测器权重
        
        状态类别:
        - 0: 正常
        - 1: 关注级预警
        - 2: 检查级预警
        - 3: 紧急级预警
        - 4: 故障
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/predict/bolt/ensemble",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
            params={
                "validation_mode": validation_mode,
            },
        )

        return response

    async def predict_bolt_multivariate_api_v1_predict_bolt_multivariate_post(
        self,
        body: BoltMultivariatePredictionRequest,
        save_to_db: Optional[bool] = None
) -> BoltMultivariatePredictionResponse:
        """
        螺栓多变量耦合预测（温度/振动/扭矩等联合输入）

        螺栓多变量耦合预测接口
        
        支持温度、振动、扭矩、湿度、压力等多传感器数据与预紧力联合预测。
        内部使用跨通道 Attention 建模变量间的耦合关系。
        
        **两种数据输入方式（二选一）**：
        
        1. **分通道模式（推荐）**：
           - 使用 `channels` 字段传入各通道的时序数据
           - 各通道时间戳可以不同步，服务端自动对齐插值
           - 例：`{"preload": [[时间,值], ...], "temperature": [[时间,值], ...], ...}`
        
        2. **对齐数组模式**：
           - 使用 `aligned_data` + `aligned_channel_names`
           - 每行格式：[时间, 通道1值, 通道2值, ...]
           - 适用于各传感器已同步采集的场景
        
        **缺失降级策略**（可通过 enable_degradation 控制）：
        - 缺失通道数不严重：自动线性插值补全 → 标记为 `data_quality.level=partial`
        - 缺失严重（<50%完整度）且 `enable_degradation=True` → 自动降级为仅预紧力单变量预测 → 标记为 `data_quality.level=degraded`
        
        状态类别:
        - 0: 正常
        - 1: 关注级预警
        - 2: 检查级预警
        - 3: 紧急级预警
        - 4: 故障
        
        响应中新增多变量专属字段:
        - `data_quality`: 数据质量评估（full/partial/degraded，含插值点、降级信息）
        - `temp_compensation`: 温度耦合补偿详情（系数α、相关系数等）
        - `feature_importance`: 各通道对预测结果的重要性权重（可解释性）
        - `channels_info`: 实际参与计算的通道元数据（单位、描述）
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/predict/bolt/multivariate",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
            params={
                "save_to_db": save_to_db,
            },
        )

        return response

    async def predict_flange_api_v1_predict_flange_post(
        self,
        body: FlangePredictionRequest,
        validation_mode: Optional[str] = None,
        version: Optional[Any] = None,
        shadow_version: Optional[Any] = None
) -> FlangePredictionResponse:
        """
        法兰面状态预测

        预测法兰面的整体状态
        
        基于法兰面上所有螺栓的预紧力数据，预测法兰面状态。
        
        校验模式:
        - strict: 严格模式，数据不合规直接拒绝
        - lenient: 宽松模式，自动截断/填充数据
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/predict/flange",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
            params={
                "validation_mode": validation_mode,
                "version": version,
                "shadow_version": shadow_version,
            },
        )

        return response

    async def forecast_monthly_api_v1_forecast_monthly_post(
        self,
        body: MonthlyForecastRequest
) -> MonthlyForecastResponse:
        """
        月度趋势预测

        预测未来30天的状态趋势
        
        使用Prophet时间序列模型进行趋势预测。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/forecast/monthly",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def batch_predict_api_v1_predict_batch_post(
        self,
        node_type: str
) -> Dict[str, Any]:
        """
        批量预测

        从数据库读取数据并批量预测
        
        自动读取所有需要预测的节点数据并执行预测。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/predict/batch",
            params={
                "node_type": node_type,
            },
        )

        return response
