"""
碳排与能效关联分析服务

建立预紧力劣化、泄漏率估算与能耗/碳排增量的简化关联模型。
所有模型系数可配置，强调趋势与优先级，不强制精确计量。

功能模块:
1. PreloadDegradationModel: 预紧力劣化模型（估算密封面压紧力衰减）
2. LeakageRateEstimator: 基于劣化程度的介质泄漏率估算
3. EnergyCarbonModel: 能耗增量与碳排增量简化模型
4. CarbonRiskRanker: 装置级月度碳排风险贡献排行
5. CarbonEnergyService: 对外服务门面
"""

import numpy as np
import json
import csv
import io
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from app.utils.config import config
from app.utils.database import get_db, BoltHealthHistory, FlangeHealthHistory, HealthRollupReport


class CarbonRiskLevel(Enum):
    """碳排风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EmissionScope(Enum):
    """排放范围"""
    SCOPE1 = "scope1"
    SCOPE2 = "scope2"
    SCOPE3 = "scope3"


@dataclass
class DegradationParams:
    """预紧力劣化模型参数（可配置）"""
    nominal_preload: float = 600.0
    min_effective_preload_ratio: float = 0.6
    relaxation_rate_per_month: float = 0.015
    temperature_acceleration_factor: float = 0.002
    vibration_acceleration_factor: float = 0.003
    cycle_acceleration_factor: float = 0.0001


@dataclass
class LeakageParams:
    """泄漏率估算模型参数（可配置）"""
    base_leakage_rate_m3_per_hour: float = 0.0
    critical_leakage_threshold: float = 0.05
    preload_leakage_sensitivity: float = 2.5
    seal_aging_factor_per_year: float = 0.08
    pressure_sensitivity: float = 1.2


@dataclass
class EnergyCarbonParams:
    """能耗与碳排增量模型参数（可配置）"""
    energy_per_leakage_unit: float = 8.5
    carbon_factor_electricity: float = 0.5839
    carbon_factor_natural_gas: float = 2.1622
    carbon_factor_steam: float = 0.11
    compressor_efficiency: float = 0.75
    recovery_rate: float = 0.0
    base_monthly_energy_kwh: float = 10000.0
    base_monthly_carbon_kg: float = 5839.0


@dataclass
class DegradationResult:
    """预紧力劣化分析结果"""
    current_preload_ratio: float
    effective_preload_ratio: float
    degradation_rate_per_month: float
    estimated_months_to_critical: Optional[float]
    degradation_trend: str
    contributing_factors: List[str]


@dataclass
class LeakageEstimate:
    """泄漏率估算结果"""
    estimated_leakage_rate: float
    leakage_level: str
    monthly_leakage_volume_m3: float
    annual_leakage_volume_m3: float
    trend_direction: str
    confidence_level: str


@dataclass
class EnergyCarbonImpact:
    """能耗与碳排增量估算结果"""
    monthly_energy_increment_kwh: float
    annual_energy_increment_kwh: float
    monthly_carbon_increment_kg: float
    annual_carbon_increment_kg: float
    energy_cost_increment_estimate: float
    scope: str
    primary_contributor: str


@dataclass
class CarbonRiskItem:
    """碳排风险排行单项"""
    node_id: str
    node_type: str
    node_name: str
    hi_score: float
    hi_level: str
    carbon_risk_score: float
    carbon_risk_level: str
    monthly_leakage_volume_m3: float
    monthly_carbon_increment_kg: float
    priority_score: float
    trend: str
    recommendations: List[str]


@dataclass
class HICarbonDualView:
    """HI 与碳排并列展示数据"""
    node_id: str
    node_type: str
    node_name: str
    hi_score: float
    hi_level: str
    hi_trend: str
    degradation_rate: float
    estimated_leakage_rate: float
    monthly_carbon_kg: float
    carbon_risk_level: str
    carbon_trend: str


@dataclass
class ESGReportFragment:
    """ESG 报表片段"""
    report_period: str
    generated_at: datetime
    summary: Dict[str, Any]
    top_risk_items: List[Dict[str, Any]]
    trend_analysis: Dict[str, Any]
    recommendations: List[str]
    methodology_note: str


class ModelConfigManager:
    """碳排模型配置管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        self.degradation = DegradationParams()
        self.leakage = LeakageParams()
        self.energy = EnergyCarbonParams()

        cfg = config.get('carbon_energy', {})

        deg_cfg = cfg.get('degradation', {})
        for k, v in deg_cfg.items():
            if hasattr(self.degradation, k):
                setattr(self.degradation, k, v)

        leak_cfg = cfg.get('leakage', {})
        for k, v in leak_cfg.items():
            if hasattr(self.leakage, k):
                setattr(self.leakage, k, v)

        eng_cfg = cfg.get('energy_carbon', {})
        for k, v in eng_cfg.items():
            if hasattr(self.energy, k):
                setattr(self.energy, k, v)

        try:
            with get_db() as db:
                for key in ['carbon_degradation_params', 'carbon_leakage_params', 'carbon_energy_params']:
                    try:
                        row = db.execute(
                            "SELECT config_value FROM sc_health_config WHERE config_key = :k",
                            {"k": key}
                        ).first()
                        if row and row[0]:
                            value = json.loads(row[0])
                            if key == 'carbon_degradation_params':
                                for k, v in value.items():
                                    if hasattr(self.degradation, k):
                                        setattr(self.degradation, k, v)
                            elif key == 'carbon_leakage_params':
                                for k, v in value.items():
                                    if hasattr(self.leakage, k):
                                        setattr(self.leakage, k, v)
                            elif key == 'carbon_energy_params':
                                for k, v in value.items():
                                    if hasattr(self.energy, k):
                                        setattr(self.energy, k, v)
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"从数据库加载碳排配置失败，使用默认配置: {e}")

    def reload(self):
        self._load_config()


class PreloadDegradationModel:
    """预紧力劣化模型

    估算密封面压紧力的衰减速率和到达临界阈值的时间。
    """

    def __init__(self):
        self.config_mgr = ModelConfigManager()

    def analyze(
        self,
        bolt_id: str,
        preload_history: List[float],
        timestamps: Optional[List[datetime]] = None,
        service_age_months: float = 0,
        avg_temperature: float = 25.0,
        avg_vibration: float = 0.0,
        pressure_cycles: int = 0,
    ) -> DegradationResult:
        params = self.config_mgr.degradation

        if len(preload_history) < 2:
            return DegradationResult(
                current_preload_ratio=1.0,
                effective_preload_ratio=1.0,
                degradation_rate_per_month=params.relaxation_rate_per_month,
                estimated_months_to_critical=None,
                degradation_trend="insufficient_data",
                contributing_factors=["历史数据不足"]
            )

        nominal = params.nominal_preload
        current_ratio = float(preload_history[-1] / nominal)
        current_ratio = float(np.clip(current_ratio, 0, 1.5))

        x = np.arange(len(preload_history))
        slope, _ = np.polyfit(x, preload_history, 1)
        slope_ratio = slope / nominal
        days_per_point = 1.0
        if timestamps and len(timestamps) >= 2:
            total_days = (timestamps[-1] - timestamps[0]).total_seconds() / 86400
            if total_days > 0:
                days_per_point = total_days / (len(preload_history) - 1)
        degradation_rate_month = abs(slope_ratio) * (30.0 / max(days_per_point, 0.1))

        temp_factor = max(0, avg_temperature - 40) * params.temperature_acceleration_factor
        vib_factor = avg_vibration * params.vibration_acceleration_factor
        cycle_factor = pressure_cycles * params.cycle_acceleration_factor
        degradation_rate_month += temp_factor + vib_factor + cycle_factor
        degradation_rate_month = float(max(degradation_rate_month, params.relaxation_rate_per_month * 0.5))

        effective_ratio = current_ratio * (1.0 - service_age_months * 0.002)
        effective_ratio = float(np.clip(effective_ratio, 0, 1.5))

        critical_ratio = params.min_effective_preload_ratio
        months_to_critical = None
        if effective_ratio > critical_ratio and degradation_rate_month > 0:
            months_to_critical = float((effective_ratio - critical_ratio) / degradation_rate_month)
            months_to_critical = float(max(0, months_to_critical))

        if slope_ratio < -0.005:
            trend = "accelerating_decline"
        elif slope_ratio < -0.001:
            trend = "gradual_decline"
        elif abs(slope_ratio) <= 0.001:
            trend = "stable"
        else:
            trend = "recovering"

        factors = []
        if degradation_rate_month > params.relaxation_rate_per_month * 1.5:
            factors.append("劣化速率高于正常值")
        if temp_factor > 0:
            factors.append(f"高温加速(+{temp_factor:.4f}/月)")
        if vib_factor > 0:
            factors.append(f"振动加速(+{vib_factor:.4f}/月)")
        if cycle_factor > 0:
            factors.append(f"压力循环加速(+{cycle_factor:.4f}/月)")
        if not factors:
            factors.append("劣化速率在正常范围")

        return DegradationResult(
            current_preload_ratio=current_ratio,
            effective_preload_ratio=effective_ratio,
            degradation_rate_per_month=degradation_rate_month,
            estimated_months_to_critical=months_to_critical,
            degradation_trend=trend,
            contributing_factors=factors
        )


class LeakageRateEstimator:
    """泄漏率估算器

    基于预紧力有效压紧比、密封老化、介质压力等估算泄漏率。
    不追求精确计量，用于趋势和优先级排序。
    """

    def __init__(self):
        self.config_mgr = ModelConfigManager()

    def estimate(
        self,
        degradation: DegradationResult,
        seal_age_years: float = 0,
        operating_pressure_mpa: float = 1.0,
        medium_type: str = "gas",
    ) -> LeakageEstimate:
        params = self.config_mgr.leakage

        eff_ratio = degradation.effective_preload_ratio
        critical = params.critical_leakage_threshold

        if eff_ratio >= 1.0:
            pressure_factor = 0
        elif eff_ratio > critical:
            normalized_gap = (1.0 - eff_ratio) / (1.0 - critical)
            pressure_factor = normalized_gap ** params.preload_leakage_sensitivity
        else:
            pressure_factor = 1.0 + (critical - eff_ratio) * 10

        aging_factor = 1.0 + seal_age_years * params.seal_aging_factor_per_year
        pressure_correction = 1.0 + max(0, operating_pressure_mpa - 1.0) * params.pressure_sensitivity

        if medium_type == "liquid":
            medium_correction = 0.3
        elif medium_type == "steam":
            medium_correction = 1.5
        else:
            medium_correction = 1.0

        base_rate = params.base_leakage_rate_m3_per_hour
        estimated_rate = (base_rate + 0.001) * pressure_factor * aging_factor * pressure_correction * medium_correction
        estimated_rate = float(max(estimated_rate, params.base_leakage_rate_m3_per_hour))

        if estimated_rate < 0.001:
            level = "negligible"
            confidence = "low"
        elif estimated_rate < 0.01:
            level = "minor"
            confidence = "medium"
        elif estimated_rate < 0.05:
            level = "moderate"
            confidence = "medium"
        elif estimated_rate < 0.2:
            level = "significant"
            confidence = "high"
        else:
            level = "critical"
            confidence = "high"

        monthly_volume = estimated_rate * 24 * 30
        annual_volume = monthly_volume * 12

        if degradation.degradation_trend in ["accelerating_decline", "gradual_decline"]:
            trend = "increasing"
        elif degradation.degradation_trend == "stable":
            trend = "stable"
        else:
            trend = "decreasing"

        return LeakageEstimate(
            estimated_leakage_rate=estimated_rate,
            leakage_level=level,
            monthly_leakage_volume_m3=monthly_volume,
            annual_leakage_volume_m3=annual_volume,
            trend_direction=trend,
            confidence_level=confidence
        )


class EnergyCarbonModel:
    """能耗增量与碳排增量简化模型

    将泄漏量转化为补充能耗（压缩机做功、加热能源等），
    再通过排放因子折算为碳排增量。
    """

    def __init__(self):
        self.config_mgr = ModelConfigManager()

    def calculate(
        self,
        leakage: LeakageEstimate,
        energy_source: str = "electricity",
        operating_hours_per_month: int = 720,
    ) -> EnergyCarbonImpact:
        params = self.config_mgr.energy

        leakage_m3_per_month = leakage.monthly_leakage_volume_m3
        effective_leakage = leakage_m3_per_month * (1.0 - params.recovery_rate)

        energy_kwh_per_m3 = params.energy_per_leakage_unit / max(params.compressor_efficiency, 0.1)
        monthly_energy = effective_leakage * energy_kwh_per_m3
        annual_energy = monthly_energy * 12

        if energy_source == "natural_gas":
            cf = params.carbon_factor_natural_gas
            scope = EmissionScope.SCOPE1.value
        elif energy_source == "steam":
            cf = params.carbon_factor_steam
            scope = EmissionScope.SCOPE2.value
        else:
            cf = params.carbon_factor_electricity
            scope = EmissionScope.SCOPE2.value

        monthly_carbon = monthly_energy * cf
        annual_carbon = annual_energy * cf

        electricity_price = 0.8
        energy_cost = monthly_energy * electricity_price

        contributor_map = {
            "negligible": "无显著贡献",
            "minor": "预紧力轻微劣化",
            "moderate": "预紧力劣化 + 密封老化",
            "significant": "压紧力不足 + 密封老化",
            "critical": "严重压紧力不足 + 多重因素"
        }
        primary = contributor_map.get(leakage.leakage_level, "多因素综合")

        return EnergyCarbonImpact(
            monthly_energy_increment_kwh=float(monthly_energy),
            annual_energy_increment_kwh=float(annual_energy),
            monthly_carbon_increment_kg=float(monthly_carbon),
            annual_carbon_increment_kg=float(annual_carbon),
            energy_cost_increment_estimate=float(energy_cost),
            scope=scope,
            primary_contributor=primary
        )


class CarbonRiskRanker:
    """装置级月度碳排风险贡献排行"""

    def __init__(self):
        self.degradation_model = PreloadDegradationModel()
        self.leakage_estimator = LeakageRateEstimator()
        self.energy_carbon_model = EnergyCarbonModel()

    def analyze_node(
        self,
        node_id: str,
        node_type: str,
        node_name: str,
        hi_score: float,
        hi_level: str,
        preload_history: List[float],
        timestamps: Optional[List[datetime]] = None,
        service_age_months: float = 0,
        avg_temperature: float = 25.0,
        seal_age_years: float = 0,
        operating_pressure_mpa: float = 1.0,
        energy_source: str = "electricity",
    ) -> CarbonRiskItem:
        degradation = self.degradation_model.analyze(
            bolt_id=node_id,
            preload_history=preload_history,
            timestamps=timestamps,
            service_age_months=service_age_months,
            avg_temperature=avg_temperature,
        )
        leakage = self.leakage_estimator.estimate(
            degradation=degradation,
            seal_age_years=seal_age_years,
            operating_pressure_mpa=operating_pressure_mpa,
        )
        carbon = self.energy_carbon_model.calculate(
            leakage=leakage,
            energy_source=energy_source,
        )

        hi_component = (100.0 - hi_score) * 0.4
        leakage_component = min(leakage.estimated_leakage_rate * 500, 40.0)
        trend_component = 0.0
        if degradation.degradation_trend == "accelerating_decline":
            trend_component = 15.0
        elif degradation.degradation_trend == "gradual_decline":
            trend_component = 5.0
        elif degradation.degradation_trend == "recovering":
            trend_component = -5.0

        carbon_risk_score = float(np.clip(hi_component + leakage_component + trend_component, 0, 100))

        if carbon_risk_score >= 75:
            cr_level = CarbonRiskLevel.CRITICAL.value
        elif carbon_risk_score >= 50:
            cr_level = CarbonRiskLevel.HIGH.value
        elif carbon_risk_score >= 25:
            cr_level = CarbonRiskLevel.MEDIUM.value
        else:
            cr_level = CarbonRiskLevel.LOW.value

        recs = self._generate_recommendations(
            hi_score, carbon_risk_score, leakage, degradation
        )

        priority = carbon_risk_score + (100.0 - hi_score) * 0.5

        return CarbonRiskItem(
            node_id=node_id,
            node_type=node_type,
            node_name=node_name,
            hi_score=hi_score,
            hi_level=hi_level,
            carbon_risk_score=carbon_risk_score,
            carbon_risk_level=cr_level,
            monthly_leakage_volume_m3=leakage.monthly_leakage_volume_m3,
            monthly_carbon_increment_kg=carbon.monthly_carbon_increment_kg,
            priority_score=priority,
            trend=degradation.degradation_trend,
            recommendations=recs
        )

    def rank_devices(
        self,
        items: List[CarbonRiskItem],
        top_n: Optional[int] = None,
    ) -> List[CarbonRiskItem]:
        ranked = sorted(items, key=lambda x: x.priority_score, reverse=True)
        if top_n:
            ranked = ranked[:top_n]
        for i, item in enumerate(ranked):
            setattr(item, 'rank', i + 1)
        return ranked

    def _generate_recommendations(
        self,
        hi_score: float,
        carbon_risk: float,
        leakage: LeakageEstimate,
        degradation: DegradationResult,
    ) -> List[str]:
        recs = []

        if carbon_risk >= 75:
            recs.append("立即安排紧固或更换密封件，降低泄漏")
            recs.append("纳入本月ESG重点整改清单")
        elif carbon_risk >= 50:
            recs.append("近期安排检修，评估密封性能")
            recs.append("列入月度碳排减排计划")
        elif carbon_risk >= 25:
            recs.append("提高监测频率，关注劣化趋势")
            recs.append("纳入预防性维护计划")
        else:
            recs.append("保持常规监测，暂无显著碳排风险")

        if degradation.estimated_months_to_critical and degradation.estimated_months_to_critical < 6:
            recs.append(f"预计{degradation.estimated_months_to_critical:.1f}个月后达到临界压紧力")

        if leakage.trend_direction == "increasing":
            recs.append("泄漏呈上升趋势，建议提前干预")

        return recs


class CarbonEnergyService:
    """碳排与能效分析服务门面类"""

    def __init__(self):
        self.ranker = CarbonRiskRanker()
        self.degradation_model = PreloadDegradationModel()
        self.leakage_estimator = LeakageRateEstimator()
        self.energy_carbon_model = EnergyCarbonModel()
        self.config_mgr = ModelConfigManager()

    def analyze_single_node(
        self,
        node_id: str,
        node_type: str,
        node_name: str,
        preload_history: List[float],
        hi_score: float,
        hi_level: str,
        timestamps: Optional[List[datetime]] = None,
        service_age_months: float = 0,
        avg_temperature: float = 25.0,
        seal_age_years: float = 0,
        operating_pressure_mpa: float = 1.0,
        energy_source: str = "electricity",
    ) -> Dict[str, Any]:
        """分析单个节点的碳排与能效影响"""
        item = self.ranker.analyze_node(
            node_id=node_id,
            node_type=node_type,
            node_name=node_name,
            hi_score=hi_score,
            hi_level=hi_level,
            preload_history=preload_history,
            timestamps=timestamps,
            service_age_months=service_age_months,
            avg_temperature=avg_temperature,
            seal_age_years=seal_age_years,
            operating_pressure_mpa=operating_pressure_mpa,
            energy_source=energy_source,
        )
        return self._risk_item_to_dict(item)

    def generate_monthly_ranking(
        self,
        nodes_data: List[Dict[str, Any]],
        top_n: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        生成装置级月度碳排风险贡献排行

        Args:
            nodes_data: 节点数据列表，每个节点包含:
                node_id, node_type, node_name, hi_score, hi_level,
                preload_history, timestamps(可选), service_age_months(可选),
                avg_temperature(可选), seal_age_years(可选),
                operating_pressure_mpa(可选), energy_source(可选)
            top_n: 只返回前 N 项，None 表示返回全部

        Returns:
            包含排名统计与详情的字典
        """
        items: List[CarbonRiskItem] = []
        for nd in nodes_data:
            try:
                item = self.ranker.analyze_node(
                    node_id=nd['node_id'],
                    node_type=nd.get('node_type', 'bolt'),
                    node_name=nd.get('node_name', nd['node_id']),
                    hi_score=nd.get('hi_score', 70.0),
                    hi_level=nd.get('hi_level', 'fair'),
                    preload_history=nd.get('preload_history', [600.0, 595.0]),
                    timestamps=nd.get('timestamps'),
                    service_age_months=nd.get('service_age_months', 0),
                    avg_temperature=nd.get('avg_temperature', 25.0),
                    seal_age_years=nd.get('seal_age_years', 0),
                    operating_pressure_mpa=nd.get('operating_pressure_mpa', 1.0),
                    energy_source=nd.get('energy_source', 'electricity'),
                )
                items.append(item)
            except Exception as e:
                logger.warning(f"分析节点 {nd.get('node_id')} 失败: {e}")
                continue

        ranked = self.ranker.rank_devices(items, top_n=top_n)

        total_monthly_carbon = sum(i.monthly_carbon_increment_kg for i in items)
        total_monthly_leakage = sum(i.monthly_leakage_volume_m3 for i in items)
        critical_count = sum(1 for i in items if i.carbon_risk_level == CarbonRiskLevel.CRITICAL.value)
        high_count = sum(1 for i in items if i.carbon_risk_level == CarbonRiskLevel.HIGH.value)
        medium_count = sum(1 for i in items if i.carbon_risk_level == CarbonRiskLevel.MEDIUM.value)
        low_count = sum(1 for i in items if i.carbon_risk_level == CarbonRiskLevel.LOW.value)

        return {
            'report_month': datetime.now().strftime("%Y-%m"),
            'total_nodes': len(items),
            'total_monthly_carbon_increment_kg': float(total_monthly_carbon),
            'total_monthly_leakage_volume_m3': float(total_monthly_leakage),
            'risk_distribution': {
                'critical': critical_count,
                'high': high_count,
                'medium': medium_count,
                'low': low_count,
            },
            'ranked_items': [self._risk_item_to_dict(i) for i in ranked],
            'generated_at': datetime.now(),
        }

    def generate_hi_carbon_dual_view(
        self,
        nodes_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        生成 HI 与碳排并列展示数据

        每个节点同时展示:
        - HI 分数、等级、趋势
        - 劣化速率
        - 估算泄漏率
        - 月度碳排增量、碳排风险等级、趋势
        """
        dual_items: List[HICarbonDualView] = []

        for nd in nodes_data:
            try:
                degradation = self.degradation_model.analyze(
                    bolt_id=nd['node_id'],
                    preload_history=nd.get('preload_history', [600.0, 595.0]),
                    timestamps=nd.get('timestamps'),
                    service_age_months=nd.get('service_age_months', 0),
                    avg_temperature=nd.get('avg_temperature', 25.0),
                )
                leakage = self.leakage_estimator.estimate(
                    degradation=degradation,
                    seal_age_years=nd.get('seal_age_years', 0),
                    operating_pressure_mpa=nd.get('operating_pressure_mpa', 1.0),
                )
                carbon = self.energy_carbon_model.calculate(leakage=leakage)

                cr_score = (100.0 - nd.get('hi_score', 70.0)) * 0.4 + min(leakage.estimated_leakage_rate * 500, 40.0)
                cr_score = float(np.clip(cr_score, 0, 100))
                if cr_score >= 75:
                    cr_level = CarbonRiskLevel.CRITICAL.value
                elif cr_score >= 50:
                    cr_level = CarbonRiskLevel.HIGH.value
                elif cr_score >= 25:
                    cr_level = CarbonRiskLevel.MEDIUM.value
                else:
                    cr_level = CarbonRiskLevel.LOW.value

                dual_items.append(HICarbonDualView(
                    node_id=nd['node_id'],
                    node_type=nd.get('node_type', 'bolt'),
                    node_name=nd.get('node_name', nd['node_id']),
                    hi_score=nd.get('hi_score', 70.0),
                    hi_level=nd.get('hi_level', 'fair'),
                    hi_trend=nd.get('hi_trend', 'stable'),
                    degradation_rate=degradation.degradation_rate_per_month,
                    estimated_leakage_rate=leakage.estimated_leakage_rate,
                    monthly_carbon_kg=carbon.monthly_carbon_increment_kg,
                    carbon_risk_level=cr_level,
                    carbon_trend=leakage.trend_direction,
                ))
            except Exception as e:
                logger.warning(f"HI/碳排并列视图节点 {nd.get('node_id')} 生成失败: {e}")
                continue

        sorted_dual = sorted(dual_items, key=lambda x: x.monthly_carbon_kg, reverse=True)

        return {
            'report_month': datetime.now().strftime("%Y-%m"),
            'total_nodes': len(sorted_dual),
            'items': [self._dual_item_to_dict(d) for d in sorted_dual],
            'generated_at': datetime.now(),
        }

    def generate_esg_report_fragment(
        self,
        ranking_data: Dict[str, Any],
        include_methodology: bool = True,
    ) -> ESGReportFragment:
        """
        生成 ESG 报表片段

        输出适用于企业 ESG 报告 / 温室气体排放清单的片段内容，
        不强制精确计量，强调趋势与优先级。
        """
        items = ranking_data.get('ranked_items', [])
        top5 = items[:5]

        total_carbon = ranking_data.get('total_monthly_carbon_increment_kg', 0)
        total_leakage = ranking_data.get('total_monthly_leakage_volume_m3', 0)
        dist = ranking_data.get('risk_distribution', {})
        total_nodes = ranking_data.get('total_nodes', 0)

        if total_nodes > 0:
            avg_carbon_per_node = total_carbon / total_nodes
        else:
            avg_carbon_per_node = 0

        if total_carbon > 1000:
            severity = "高"
        elif total_carbon > 300:
            severity = "中"
        else:
            severity = "低"

        top_carbon_contribution = 0.0
        if total_carbon > 0:
            top_carbon_contribution = sum(
                i.get('monthly_carbon_increment_kg', 0) for i in top5
            ) / total_carbon

        summary = {
            'reporting_period': ranking_data.get('report_month', datetime.now().strftime("%Y-%m")),
            'total_devices_analyzed': total_nodes,
            'estimated_monthly_carbon_increment_kg': round(total_carbon, 2),
            'estimated_monthly_carbon_increment_tons': round(total_carbon / 1000, 4),
            'estimated_monthly_leakage_m3': round(total_leakage, 4),
            'average_carbon_per_device_kg': round(avg_carbon_per_node, 2),
            'carbon_risk_severity': severity,
            'top5_contribution_ratio': round(top_carbon_contribution, 4),
            'risk_distribution': dist,
        }

        trend = {
            'overall_trend': self._assess_overall_trend(items),
            'improving_count': sum(1 for i in items if i.get('trend') == 'recovering'),
            'stable_count': sum(1 for i in items if i.get('trend') == 'stable'),
            'declining_count': sum(1 for i in items if i.get('trend') in ['gradual_decline', 'accelerating_decline']),
            'key_observation': self._generate_trend_observation(items, total_carbon),
        }

        recommendations = []
        if dist.get('critical', 0) > 0:
            recommendations.append(f"优先处理 {dist['critical']} 个碳排高风险装置")
        if dist.get('high', 0) > 0:
            recommendations.append(f"对 {dist['high']} 个高风险装置安排月度检修")
        if top_carbon_contribution > 0.6:
            recommendations.append(f"前5名贡献 {top_carbon_contribution:.0%} 碳排增量，建议重点治理")
        recommendations.append("建立密封件全生命周期碳排台账")
        recommendations.append("将碳排风险纳入预防性维护决策指标")

        methodology = (
            "本报告片段采用简化关联模型进行估算，不用于精确计量和合规申报。"
            "方法: (1) 基于预紧力时序与工况因子估算压紧力劣化速率; "
            "(2) 通过有效压紧比、密封老化、介质压力估算泄漏率趋势; "
            "(3) 将泄漏量折算为压缩机补充能耗并通过排放因子(电力0.5839kgCO₂e/kWh等)换算碳排增量。"
            "所有系数可配置，建议用于趋势分析与优先级排序。"
        ) if include_methodology else ""

        return ESGReportFragment(
            report_period=summary['reporting_period'],
            generated_at=datetime.now(),
            summary=summary,
            top_risk_items=[self._esg_item(i) for i in top5],
            trend_analysis=trend,
            recommendations=recommendations,
            methodology_note=methodology,
        )

    def export_esg_csv(self, fragment: ESGReportFragment) -> str:
        """将 ESG 报表片段导出为 CSV 字符串"""
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["# ESG 碳排风险报表片段"])
        writer.writerow(["# 报告期", fragment.report_period])
        writer.writerow(["# 生成时间", fragment.generated_at.isoformat()])
        writer.writerow([])

        writer.writerow(["=== 汇总数据 ==="])
        for k, v in fragment.summary.items():
            writer.writerow([k, v])
        writer.writerow([])

        writer.writerow(["=== 碳排风险 TOP5 装置 ==="])
        writer.writerow([
            "排名", "节点ID", "节点类型", "节点名称",
            "HI分数", "HI等级", "碳排风险分数", "碳排风险等级",
            "月度泄漏量(m3)", "月度碳排增量(kgCO₂e)", "趋势",
        ])
        for idx, it in enumerate(fragment.top_risk_items, 1):
            writer.writerow([
                idx,
                it.get('node_id', ''),
                it.get('node_type', ''),
                it.get('node_name', ''),
                it.get('hi_score', ''),
                it.get('hi_level', ''),
                it.get('carbon_risk_score', ''),
                it.get('carbon_risk_level', ''),
                round(it.get('monthly_leakage_volume_m3', 0), 4),
                round(it.get('monthly_carbon_increment_kg', 0), 2),
                it.get('trend', ''),
            ])
        writer.writerow([])

        writer.writerow(["=== 趋势分析 ==="])
        for k, v in fragment.trend_analysis.items():
            writer.writerow([k, v])
        writer.writerow([])

        writer.writerow(["=== 建议措施 ==="])
        for r in fragment.recommendations:
            writer.writerow([r])
        writer.writerow([])

        if fragment.methodology_note:
            writer.writerow(["=== 方法学说明 ==="])
            writer.writerow([fragment.methodology_note])

        return output.getvalue()

    def get_model_config(self) -> Dict[str, Any]:
        """获取当前生效的模型系数配置"""
        return {
            'degradation': {
                'nominal_preload': self.config_mgr.degradation.nominal_preload,
                'min_effective_preload_ratio': self.config_mgr.degradation.min_effective_preload_ratio,
                'relaxation_rate_per_month': self.config_mgr.degradation.relaxation_rate_per_month,
                'temperature_acceleration_factor': self.config_mgr.degradation.temperature_acceleration_factor,
                'vibration_acceleration_factor': self.config_mgr.degradation.vibration_acceleration_factor,
                'cycle_acceleration_factor': self.config_mgr.degradation.cycle_acceleration_factor,
            },
            'leakage': {
                'base_leakage_rate_m3_per_hour': self.config_mgr.leakage.base_leakage_rate_m3_per_hour,
                'critical_leakage_threshold': self.config_mgr.leakage.critical_leakage_threshold,
                'preload_leakage_sensitivity': self.config_mgr.leakage.preload_leakage_sensitivity,
                'seal_aging_factor_per_year': self.config_mgr.leakage.seal_aging_factor_per_year,
                'pressure_sensitivity': self.config_mgr.leakage.pressure_sensitivity,
            },
            'energy_carbon': {
                'energy_per_leakage_unit': self.config_mgr.energy.energy_per_leakage_unit,
                'carbon_factor_electricity': self.config_mgr.energy.carbon_factor_electricity,
                'carbon_factor_natural_gas': self.config_mgr.energy.carbon_factor_natural_gas,
                'carbon_factor_steam': self.config_mgr.energy.carbon_factor_steam,
                'compressor_efficiency': self.config_mgr.energy.compressor_efficiency,
                'recovery_rate': self.config_mgr.energy.recovery_rate,
                'base_monthly_energy_kwh': self.config_mgr.energy.base_monthly_energy_kwh,
                'base_monthly_carbon_kg': self.config_mgr.energy.base_monthly_carbon_kg,
            },
        }

    # ==================== 内部辅助方法 ====================

    def _risk_item_to_dict(self, item: CarbonRiskItem) -> Dict[str, Any]:
        return {
            'rank': getattr(item, 'rank', None),
            'node_id': item.node_id,
            'node_type': item.node_type,
            'node_name': item.node_name,
            'hi_score': item.hi_score,
            'hi_level': item.hi_level,
            'carbon_risk_score': round(item.carbon_risk_score, 2),
            'carbon_risk_level': item.carbon_risk_level,
            'monthly_leakage_volume_m3': round(item.monthly_leakage_volume_m3, 4),
            'monthly_carbon_increment_kg': round(item.monthly_carbon_increment_kg, 2),
            'priority_score': round(item.priority_score, 2),
            'trend': item.trend,
            'recommendations': item.recommendations,
        }

    def _dual_item_to_dict(self, d: HICarbonDualView) -> Dict[str, Any]:
        return {
            'node_id': d.node_id,
            'node_type': d.node_type,
            'node_name': d.node_name,
            'hi_score': round(d.hi_score, 2),
            'hi_level': d.hi_level,
            'hi_trend': d.hi_trend,
            'degradation_rate_per_month': round(d.degradation_rate, 5),
            'estimated_leakage_rate_m3_hour': round(d.estimated_leakage_rate, 5),
            'monthly_carbon_increment_kg': round(d.monthly_carbon_kg, 2),
            'carbon_risk_level': d.carbon_risk_level,
            'carbon_trend': d.carbon_trend,
        }

    def _esg_item(self, it: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'node_id': it.get('node_id', ''),
            'node_type': it.get('node_type', ''),
            'node_name': it.get('node_name', ''),
            'hi_score': it.get('hi_score', 0),
            'hi_level': it.get('hi_level', ''),
            'carbon_risk_score': it.get('carbon_risk_score', 0),
            'carbon_risk_level': it.get('carbon_risk_level', ''),
            'monthly_leakage_volume_m3': it.get('monthly_leakage_volume_m3', 0),
            'monthly_carbon_increment_kg': it.get('monthly_carbon_increment_kg', 0),
            'trend': it.get('trend', ''),
            'recommendations': it.get('recommendations', []),
        }

    def _assess_overall_trend(self, items: List[Dict[str, Any]]) -> str:
        if not items:
            return "insufficient_data"
        declining = sum(1 for i in items if i.get('trend') in ['gradual_decline', 'accelerating_decline'])
        recovering = sum(1 for i in items if i.get('trend') == 'recovering')
        if declining / len(items) > 0.5:
            return "deteriorating"
        elif recovering / len(items) > 0.3:
            return "improving"
        else:
            return "stable"

    def _generate_trend_observation(self, items: List[Dict[str, Any]], total_carbon: float) -> str:
        if not items:
            return "样本量不足"
        declining = sum(1 for i in items if i.get('trend') in ['gradual_decline', 'accelerating_decline'])
        ratio = declining / len(items)
        if ratio > 0.5:
            return f"{ratio:.0%} 的装置呈劣化趋势，月度碳排增量合计约 {total_carbon:.1f}kgCO₂e，建议集中治理"
        elif ratio > 0.2:
            return f"{ratio:.0%} 的装置呈劣化趋势，建议加强巡检并针对性维护"
        else:
            return "整体状况稳定，维持常规监测和预防性维护节奏"
