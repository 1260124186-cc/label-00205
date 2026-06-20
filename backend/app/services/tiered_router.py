"""
时序数据冷热分层路由层
======================
高层业务路由，根据使用场景自动选择数据存储层级：

业务场景                | 读取层级               | 说明
----------------------- | --------------------- | ---------------------------------
模型训练 (Training)     | hot_only              | 只读取热数据，保证训练速度
实时预测 (Prediction)   | hot_only              | 只读取最近数据，低延迟优先
历史分析 (Analysis)     | hot_warm              | 热+温数据，可按需懒加载冷数据
合规审计 (Compliance)   | all                   | 热+温+冷，完整数据范围
报表查询 (Reporting)    | hot_warm              | 默认热+温，可配置

核心职责：
1. 根据业务场景设定默认读取层级
2. 时间范围超过阈值时自动提示/触发懒加载
3. 统一冷热数据合并与后处理
4. 路由决策审计（便于分析数据访问模式）
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd
import numpy as np
from loguru import logger

from .archive_service import ArchiveService, LazyLoadResult
from .cold_storage import ColdStorageFactory, StorageConfig
from ..utils.database import SessionLocal, get_db, TenantRetentionPolicy


# ============================================================
# 枚举与数据类定义
# ============================================================

class ReadTier(str, Enum):
    """读取数据层级"""
    HOT_ONLY = "hot_only"          # 仅热数据（MySQL）
    HOT_WARM = "hot_warm"          # 热 + 温数据（MySQL + 快速冷存）
    ALL = "all"                    # 全部层级，含深度冷存
    AUTO = "auto"                  # 根据时间范围自动选择

class BusinessScenario(str, Enum):
    """业务场景枚举"""
    TRAINING = "training"              # 模型训练
    PREDICTION = "prediction"          # 实时预测
    ANALYSIS = "analysis"              # 历史分析
    COMPLIANCE = "compliance"          # 合规审计
    REPORTING = "reporting"            # 报表查询
    VISUALIZATION = "visualization"    # 可视化展示
    DATA_EXPORT = "data_export"        # 数据导出
    CUSTOM = "custom"                  # 自定义

# 场景 -> 默认读取层级 映射
SCENARIO_DEFAULT_TIER: Dict[BusinessScenario, ReadTier] = {
    BusinessScenario.TRAINING: ReadTier.HOT_ONLY,
    BusinessScenario.PREDICTION: ReadTier.HOT_ONLY,
    BusinessScenario.ANALYSIS: ReadTier.HOT_WARM,
    BusinessScenario.COMPLIANCE: ReadTier.ALL,
    BusinessScenario.REPORTING: ReadTier.HOT_WARM,
    BusinessScenario.VISUALIZATION: ReadTier.HOT_WARM,
    BusinessScenario.DATA_EXPORT: ReadTier.ALL,
    BusinessScenario.CUSTOM: ReadTier.AUTO,
}

# 场景 -> user_type 映射（用于懒加载审计）
SCENARIO_USER_TYPE: Dict[BusinessScenario, str] = {
    BusinessScenario.TRAINING: "training",
    BusinessScenario.PREDICTION: "prediction",
    BusinessScenario.ANALYSIS: "analysis",
    BusinessScenario.COMPLIANCE: "compliance",
    BusinessScenario.REPORTING: "reporting",
    BusinessScenario.VISUALIZATION: "visualization",
    BusinessScenario.DATA_EXPORT: "data_export",
    BusinessScenario.CUSTOM: "api",
}


@dataclass
class TieredQueryRequest:
    """分层查询请求"""
    tenant_id: int
    table_name: str
    start_time: datetime
    end_time: datetime
    sensor_ids: Optional[List[Any]] = None
    columns: Optional[List[str]] = None
    scenario: BusinessScenario = BusinessScenario.ANALYSIS
    read_tier: ReadTier = ReadTier.AUTO              # AUTO 表示使用场景默认值
    async_load: bool = False                          # 冷数据异步加载（返回请求ID）
    load_priority: str = "normal"                    # low/normal/high/urgent
    restore_to_hot: bool = False                     # 加载后回迁到热库（加速后续访问）
    auto_upgrade_tier: bool = True                   # 时间范围超阈值时自动升级读取层级
    user_id: Optional[str] = None
    api_endpoint: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TieredQueryResponse:
    """分层查询响应"""
    success: bool
    dataframe: Optional[pd.DataFrame] = None
    scenario: BusinessScenario = BusinessScenario.ANALYSIS
    effective_tier: ReadTier = ReadTier.HOT_ONLY      # 实际生效的读取层级
    hot_rows: int = 0
    cold_rows: int = 0
    total_rows: int = 0
    cold_files_read: int = 0
    cold_bytes_loaded: int = 0
    duration_seconds: float = 0.0
    lazy_load_request_id: Optional[str] = None         # 异步加载时返回
    lazy_load_status: str = "not_needed"               # not_needed / pending / loading / completed / failed
    tier_upgraded: bool = False                         # 是否发生了层级升级
    tier_upgrade_reason: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# 冷热路由主类
# ============================================================

class TieredTimeSeriesRouter:
    """
    冷热分层时序数据路由器

    使用方式：
    ```python
    router = TieredTimeSeriesRouter()
    result = router.query(TieredQueryRequest(
        tenant_id=1,
        table_name="sc_bolt_data",
        start_time=..., end_time=...,
        sensor_ids=[1001],
        scenario=BusinessScenario.ANALYSIS,
    ))
    ```
    """

    def __init__(self, archive_service: Optional[ArchiveService] = None,
                 storage_config: Optional[Dict[str, Any]] = None):
        """
        Args:
            archive_service: 归档服务实例（None 则自动创建）
            storage_config: 冷存储配置（archive_service 为 None 时使用）
        """
        self._external_service = archive_service is not None
        self._archive_service = archive_service
        self._storage_config = storage_config

    @property
    def archive_service(self) -> ArchiveService:
        if self._archive_service is None:
            self._archive_service = ArchiveService(
                db=SessionLocal(),
                storage_config=self._storage_config,
            )
        return self._archive_service

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._external_service and self._archive_service is not None:
            try:
                self._archive_service.__exit__(exc_type, exc_val, exc_tb)
            except Exception:
                pass

    # ============================================================
    # 层级决策逻辑
    # ============================================================

    def _resolve_tier(self, req: TieredQueryRequest,
                       policy: TenantRetentionPolicy) -> Tuple[ReadTier, bool, Optional[str]]:
        """
        根据请求、策略和场景决定实际读取层级

        Returns:
            (effective_tier, tier_upgraded, upgrade_reason)
        """
        # 1. 手动指定了非 AUTO 层级，直接使用
        if req.read_tier != ReadTier.AUTO:
            return req.read_tier, False, None

        # 2. 使用场景默认层级
        scenario_tier = SCENARIO_DEFAULT_TIER.get(req.scenario, ReadTier.HOT_WARM)

        if not req.auto_upgrade_tier:
            return scenario_tier, False, None

        # 3. 检查是否需要自动升级层级（根据时间范围跨度）
        hot_days = policy.hot_retention_days or 90
        cold_days = policy.cold_retention_days or 365
        time_span_days = (req.end_time - req.start_time).total_seconds() / 86400.0
        now = datetime.now()
        oldest_requested = req.start_time
        hot_cutoff = now - timedelta(days=hot_days)

        upgraded = False
        reason = None

        if scenario_tier == ReadTier.HOT_ONLY:
            # 请求的起始时间早于热数据阈值，需要升级
            if oldest_requested < hot_cutoff:
                upgraded = True
                warm_cutoff = now - timedelta(days=cold_days)
                if oldest_requested < warm_cutoff:
                    scenario_tier = ReadTier.ALL
                    reason = (f"查询起始时间({oldest_requested.strftime('%Y-%m-%d')}) "
                              f"早于冷数据阈值({cold_days}天前)，自动升级至 ALL 层级")
                else:
                    scenario_tier = ReadTier.HOT_WARM
                    reason = (f"查询起始时间({oldest_requested.strftime('%Y-%m-%d')}) "
                              f"早于热数据阈值({hot_days}天前)，自动升级至 HOT_WARM 层级")

        elif scenario_tier == ReadTier.HOT_WARM:
            warm_cutoff = now - timedelta(days=cold_days)
            if oldest_requested < warm_cutoff:
                upgraded = True
                scenario_tier = ReadTier.ALL
                reason = (f"查询起始时间({oldest_requested.strftime('%Y-%m-%d')}) "
                          f"早于冷数据阈值({cold_days}天前)，自动升级至 ALL 层级")

        return scenario_tier, upgraded, reason

    @staticmethod
    def _map_tier_to_read_tier_param(tier: ReadTier) -> str:
        """将 ReadTier 枚举映射为 archive_service.read_tier 参数值"""
        mapping = {
            ReadTier.HOT_ONLY: "hot_only",
            ReadTier.HOT_WARM: "hot_warm",
            ReadTier.ALL: "all",
            ReadTier.AUTO: "hot_warm",  # 默认降级
        }
        return mapping.get(tier, "hot_only")

    # ============================================================
    # 主查询入口
    # ============================================================

    def query(self, req: TieredQueryRequest) -> TieredQueryResponse:
        """
        执行分层时序查询（主入口）

        Args:
            req: 查询请求

        Returns:
            TieredQueryResponse
        """
        overall_start = datetime.now()
        response = TieredQueryResponse(
            success=True,
            scenario=req.scenario,
        )
        warnings: List[str] = []

        try:
            # 1. 获取保留策略
            policy = self.archive_service.get_retention_policy(req.tenant_id)

            # 2. 计算实际读取层级
            effective_tier, tier_upgraded, upgrade_reason = self._resolve_tier(req, policy)
            response.effective_tier = effective_tier
            response.tier_upgraded = tier_upgraded
            response.tier_upgrade_reason = upgrade_reason
            if upgrade_reason:
                warnings.append(upgrade_reason)

            # 3. 检查懒加载是否启用
            read_tier_param = self._map_tier_to_read_tier_param(effective_tier)
            if read_tier_param != "hot_only" and not policy.lazy_load_enabled:
                warnings.append("租户未启用冷数据懒加载，仅读取热数据")
                read_tier_param = "hot_only"
                response.effective_tier = ReadTier.HOT_ONLY

            # 4. 调用 ArchiveService 执行分层查询
            user_type = SCENARIO_USER_TYPE.get(req.scenario, "api")
            lazy_result: LazyLoadResult = self.archive_service.query_tiered(
                tenant_id=req.tenant_id,
                table_name=req.table_name,
                start_time=req.start_time,
                end_time=req.end_time,
                sensor_ids=req.sensor_ids,
                columns=req.columns,
                read_tier=read_tier_param,
                policy=policy,
                user_id=req.user_id,
                api_endpoint=req.api_endpoint,
                user_type=user_type,
                async_mode=req.async_load,
                priority=req.load_priority,
                restore_to_hot=req.restore_to_hot,
                request_params={
                    "scenario": req.scenario.value,
                    "requested_tier": req.read_tier.value,
                    "effective_tier": response.effective_tier.value,
                    **req.extra,
                },
            )

            # 5. 映射结果
            response.hot_rows = lazy_result.hot_rows
            response.cold_rows = lazy_result.cold_rows
            response.total_rows = lazy_result.total_rows
            response.cold_files_read = lazy_result.files_read
            response.cold_bytes_loaded = lazy_result.bytes_loaded
            response.duration_seconds = lazy_result.duration_seconds
            response.dataframe = lazy_result.dataframe
            response.lazy_load_request_id = lazy_result.request_id
            response.lazy_load_status = lazy_result.status

            if not lazy_result.success:
                response.success = False
                response.error_message = lazy_result.error_message
            elif lazy_result.status == "pending" and req.async_load:
                warnings.append(f"冷数据异步加载中，请求ID: {lazy_result.request_id}。"
                                f"已返回热数据部分({lazy_result.hot_rows}行)。"
                                f"后续可通过 /archive/load/{lazy_result.request_id} 状态查询。")

            # 6. 统计信息
            hot_cutoff_days = policy.hot_retention_days or 90
            response.statistics = {
                "retention_policy_type": policy.policy_type,
                "hot_retention_days": hot_cutoff_days,
                "cold_retention_days": policy.cold_retention_days,
                "compliance_retention_years": policy.compliance_retention_years,
                "query_span_days": round((req.end_time - req.start_time).total_seconds() / 86400.0, 2),
                "effective_read_tier": response.effective_tier.value,
                "data_source_breakdown": {
                    "hot_mysql_rows": lazy_result.hot_rows,
                    "cold_storage_rows": lazy_result.cold_rows,
                    "cold_files_read": lazy_result.files_read,
                    "cold_bytes_mb": round(lazy_result.bytes_loaded / 1024 / 1024, 3),
                },
            }

            # 7. 总耗时
            response.duration_seconds = (datetime.now() - overall_start).total_seconds()
            response.warnings = warnings

        except Exception as e:
            logger.error(f"分层路由查询失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            response.success = False
            response.error_message = str(e)[:1000]
            response.duration_seconds = (datetime.now() - overall_start).total_seconds()

        return response

    # ============================================================
    # 便捷方法：按业务场景
    # ============================================================

    def query_for_training(self, tenant_id: int, table_name: str,
                            start_time: datetime, end_time: datetime,
                            sensor_ids: Optional[List[Any]] = None,
                            columns: Optional[List[str]] = None,
                            **kwargs) -> TieredQueryResponse:
        """
        模型训练场景查询：默认仅读取热数据（保证速度）

        典型用于：模型重训练、增量训练、超参搜索等。
        如需全量训练，请手动指定 read_tier=ALL。
        """
        req = TieredQueryRequest(
            tenant_id=tenant_id,
            table_name=table_name,
            start_time=start_time,
            end_time=end_time,
            sensor_ids=sensor_ids,
            columns=columns,
            scenario=BusinessScenario.TRAINING,
            read_tier=ReadTier.AUTO,   # 按场景默认（HOT_ONLY）
            auto_upgrade_tier=False,   # 训练不自动升级，避免意外加载冷数据导致训练缓慢
            **kwargs,
        )
        return self.query(req)

    def query_for_prediction(self, tenant_id: int, table_name: str,
                              start_time: datetime, end_time: datetime,
                              sensor_ids: Optional[List[Any]] = None,
                              columns: Optional[List[str]] = None,
                              lookback_days: int = 30,
                              **kwargs) -> TieredQueryResponse:
        """
        实时预测场景查询：默认仅读取热数据（低延迟优先）

        Args:
            lookback_days: 预测所需的回溯天数，用于安全检查
        """
        # 如果请求起始时间早于回溯所需额外提醒
        warnings = kwargs.pop("warnings", None)

        req = TieredQueryRequest(
            tenant_id=tenant_id,
            table_name=table_name,
            start_time=start_time,
            end_time=end_time,
            sensor_ids=sensor_ids,
            columns=columns,
            scenario=BusinessScenario.PREDICTION,
            read_tier=ReadTier.AUTO,   # 按场景默认（HOT_ONLY）
            auto_upgrade_tier=False,   # 预测不升级，延迟优先
            **kwargs,
        )
        return self.query(req)

    def query_for_analysis(self, tenant_id: int, table_name: str,
                            start_time: datetime, end_time: datetime,
                            sensor_ids: Optional[List[Any]] = None,
                            columns: Optional[List[str]] = None,
                            async_load: bool = True,
                            load_priority: str = "normal",
                            **kwargs) -> TieredQueryResponse:
        """
        历史分析场景查询：热+温数据，冷数据可异步懒加载

        典型用于：趋势分析、异常回溯、健康度历史查询等。
        """
        req = TieredQueryRequest(
            tenant_id=tenant_id,
            table_name=table_name,
            start_time=start_time,
            end_time=end_time,
            sensor_ids=sensor_ids,
            columns=columns,
            scenario=BusinessScenario.ANALYSIS,
            read_tier=ReadTier.AUTO,
            auto_upgrade_tier=True,    # 分析允许自动升级
            async_load=async_load,
            load_priority=load_priority,
            **kwargs,
        )
        return self.query(req)

    def query_for_compliance(self, tenant_id: int, table_name: str,
                              start_time: datetime, end_time: datetime,
                              sensor_ids: Optional[List[Any]] = None,
                              columns: Optional[List[str]] = None,
                              **kwargs) -> TieredQueryResponse:
        """
        合规审计场景查询：全层级完整数据

        典型用于：合规审计、事故追溯、法规查询等，必须完整。
        默认同步加载（不异步），因为合规场景通常需要完整结果。
        """
        req = TieredQueryRequest(
            tenant_id=tenant_id,
            table_name=table_name,
            start_time=start_time,
            end_time=end_time,
            sensor_ids=sensor_ids,
            columns=columns,
            scenario=BusinessScenario.COMPLIANCE,
            read_tier=ReadTier.ALL,     # 强制全部层级
            async_load=False,           # 合规场景同步返回
            load_priority="high",
            **kwargs,
        )
        return self.query(req)

    def query_for_reporting(self, tenant_id: int, table_name: str,
                             start_time: datetime, end_time: datetime,
                             sensor_ids: Optional[List[Any]] = None,
                             columns: Optional[List[str]] = None,
                             **kwargs) -> TieredQueryResponse:
        """
        报表查询场景：热+温数据，可配置
        """
        req = TieredQueryRequest(
            tenant_id=tenant_id,
            table_name=table_name,
            start_time=start_time,
            end_time=end_time,
            sensor_ids=sensor_ids,
            columns=columns,
            scenario=BusinessScenario.REPORTING,
            read_tier=ReadTier.AUTO,
            auto_upgrade_tier=True,
            async_load=kwargs.pop("async_load", True),
            **kwargs,
        )
        return self.query(req)

    # ============================================================
    # 辅助：时间范围建议
    # ============================================================

    def suggest_time_range(self, tenant_id: int,
                            scenario: BusinessScenario,
                            requested_start: Optional[datetime] = None,
                            requested_end: Optional[datetime] = None
                            ) -> Dict[str, Any]:
        """
        根据场景和策略建议合理的查询时间范围

        Returns:
            包含建议、策略信息、警告等
        """
        policy = self.archive_service.get_retention_policy(tenant_id)
        hot_days = policy.hot_retention_days or 90
        cold_days = policy.cold_retention_days or 365
        now = datetime.now()

        scenario_default_span = {
            BusinessScenario.TRAINING: hot_days,
            BusinessScenario.PREDICTION: min(30, hot_days),
            BusinessScenario.ANALYSIS: cold_days,
            BusinessScenario.COMPLIANCE: policy.cold_retention_days or (policy.compliance_retention_years or 7) * 365,
            BusinessScenario.REPORTING: cold_days,
            BusinessScenario.VISUALIZATION: cold_days,
            BusinessScenario.DATA_EXPORT: policy.cold_retention_days or 365,
            BusinessScenario.CUSTOM: cold_days,
        }
        default_span = scenario_default_span.get(scenario, hot_days)

        suggested_end = requested_end or now
        suggested_start = requested_start or (suggested_end - timedelta(days=default_span))

        hot_cutoff = now - timedelta(days=hot_days)
        warm_cutoff = now - timedelta(days=cold_days)

        # 判断请求起始时间落在哪个层级
        if suggested_start >= hot_cutoff:
            tier_needed = ReadTier.HOT_ONLY
            tier_description = "仅热数据"
        elif suggested_start >= warm_cutoff:
            tier_needed = ReadTier.HOT_WARM
            tier_description = "热+温数据"
        else:
            tier_needed = ReadTier.ALL
            tier_description = "含冷数据，可能触发懒加载"

        return {
            "scenario": scenario.value,
            "policy": {
                "type": policy.policy_type,
                "hot_retention_days": hot_days,
                "cold_retention_days": cold_days,
                "compliance_years": policy.compliance_retention_years,
                "lazy_load_enabled": policy.lazy_load_enabled,
            },
            "suggested_range": {
                "start": suggested_start.isoformat(),
                "end": suggested_end.isoformat(),
                "span_days": round((suggested_end - suggested_start).total_seconds() / 86400.0, 2),
            },
            "tier_required": {
                "tier": tier_needed.value,
                "description": tier_description,
                "hot_cutoff": hot_cutoff.isoformat(),
                "warm_cutoff": warm_cutoff.isoformat(),
            },
            "warnings": [
            ] if suggested_start >= warm_cutoff or policy.lazy_load_enabled else [
                f"请求起始时间({suggested_start.strftime('%Y-%m-%d')})超出温数据范围，"
                f"但租户未启用懒加载，部分数据将无法访问。"
            ],
        }
