"""
数字孪生与健康度评分服务

实现健康度指数HI（0-100）的计算、法兰面级聚合、产线/装置级rollup报表，
以及基于历史HI序列的剩余使用寿命（RUL）预测。

功能模块:
1. HealthIndexCalculator: 健康度指数HI计算
2. FlangeHealthAggregator: 法兰面级健康度聚合
3. ProductionLineRollup: 产线/装置级健康度汇总
4. RULPredictor: 剩余使用寿命预测
5. DegradationModel: 劣化曲线模型
6. HealthService: 对外服务门面
"""

import numpy as np
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from app.utils.config import config
from app.utils.database import (
    get_db,
    BoltHealthHistory,
    FlangeHealthHistory,
    RULPrediction,
    HealthRollupReport,
    DegradationCurve,
    HealthConfig,
    AlertEvent,
    BoltData,
)


class HealthLevel(Enum):
    """健康等级枚举"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class HealthTrend(Enum):
    """健康趋势枚举"""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


class DegradationModelType(Enum):
    """劣化模型类型枚举"""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    POLYNOMIAL = "polynomial"


@dataclass
class HealthIndexFactor:
    """健康度因子"""
    factor_name: str
    factor_code: str
    score: float
    weight: float
    contribution: float
    description: str = ""


@dataclass
class HealthIndexResult:
    """健康度计算结果"""
    hi_score: float
    hi_level: str
    factors: List[HealthIndexFactor]
    preload_stability_score: float
    alert_frequency_score: float
    fault_history_score: float
    environmental_stress_score: float
    service_age_score: float
    trend: Optional[str] = None
    trend_rate: Optional[float] = None


@dataclass
class RULPredictionResult:
    """RUL预测结果"""
    node_id: str
    node_type: str
    current_hi: float
    rul_days: float
    rul_lower_bound: float
    rul_upper_bound: float
    rul_confidence: float
    failure_threshold: float
    warning_threshold: float
    days_to_warning: Optional[float]
    historical_hi: List[Dict[str, Any]]
    forecast_series: List[Dict[str, Any]]
    degradation_model: str
    model_params: Dict[str, Any]
    r_squared: Optional[float]


class HealthConfigManager:
    """健康度配置管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """加载配置"""
        self.weights = {
            'preload_stability': 0.30,
            'alert_frequency': 0.20,
            'fault_history': 0.20,
            'environmental_stress': 0.15,
            'service_age': 0.15,
        }

        self.thresholds = {
            'excellent': 90,
            'good': 70,
            'fair': 50,
            'poor': 30,
            'critical': 0,
        }

        self.aging_model = {
            'design_life_years': 15,
            'inflection_point_years': 8,
            'aging_rate': 0.05,
        }

        self.alert_thresholds = {
            'normal_count_days': 30,
            'warning_penalty_per_alert': 5,
            'max_penalty': 60,
        }

        self.environmental_factors = {
            'temp_normal_range': (10, 40),
            'temp_penalty_per_degree': 1.0,
            'vibration_penalty_factor': 0.5,
            'humidity_normal_range': (30, 80),
            'humidity_penalty_per_percent': 0.3,
        }

        try:
            with get_db() as db:
                for key in ['health_weights', 'health_thresholds', 'aging_model']:
                    config_record = db.query(HealthConfig).filter(
                        HealthConfig.config_key == key
                    ).first()
                    if config_record and config_record.config_value:
                        try:
                            value = json.loads(config_record.config_value)
                            if key == 'health_weights':
                                self.weights.update(value)
                            elif key == 'health_thresholds':
                                self.thresholds.update(value)
                            elif key == 'aging_model':
                                self.aging_model.update(value)
                        except Exception as e:
                            logger.warning(f"解析健康度配置 {key} 失败: {e}")
        except Exception as e:
            logger.warning(f"从数据库加载健康度配置失败，使用默认配置: {e}")

    def reload(self):
        """重新加载配置"""
        self._load_config()


class HealthIndexCalculator:
    """健康度指数HI计算器"""

    def __init__(self):
        self.config_manager = HealthConfigManager()

    def calculate_bolt_health(
        self,
        bolt_id: str,
        preload_data: np.ndarray,
        timestamps: Optional[List[datetime]] = None,
        working_condition: Optional[Dict[str, Any]] = None,
        nominal_preload: Optional[float] = None,
        service_age_years: float = 0,
        flange_id: Optional[str] = None,
    ) -> HealthIndexResult:
        """
        计算螺栓健康度指数HI

        Args:
            bolt_id: 螺栓ID
            preload_data: 预紧力时序数据
            timestamps: 时间戳列表
            working_condition: 工况信息
            nominal_preload: 额定预紧力
            service_age_years: 使用年限（年）
            flange_id: 法兰面ID

        Returns:
            HealthIndexResult: 健康度计算结果
        """
        if nominal_preload is None:
            nominal_preload = config.get('preload.nominal', 600)

        preload_stability_score = self._calculate_preload_stability(
            preload_data, nominal_preload
        )

        alert_frequency_score = self._calculate_alert_frequency(
            bolt_id, 'bolt'
        )

        fault_history_score = self._calculate_fault_history(
            bolt_id, 'bolt'
        )

        environmental_stress_score = self._calculate_environmental_stress(
            working_condition
        )

        service_age_score = self._calculate_service_age(
            service_age_years
        )

        weights = self.config_manager.weights

        factors = [
            HealthIndexFactor(
                factor_name='预紧力稳定性',
                factor_code='preload_stability',
                score=preload_stability_score,
                weight=weights['preload_stability'],
                contribution=preload_stability_score * weights['preload_stability'],
                description='基于预紧力波动范围、偏差率、趋势稳定性计算'
            ),
            HealthIndexFactor(
                factor_name='预警频率',
                factor_code='alert_frequency',
                score=alert_frequency_score,
                weight=weights['alert_frequency'],
                contribution=alert_frequency_score * weights['alert_frequency'],
                description='基于最近30天内的告警次数计算'
            ),
            HealthIndexFactor(
                factor_name='故障历史',
                factor_code='fault_history',
                score=fault_history_score,
                weight=weights['fault_history'],
                contribution=fault_history_score * weights['fault_history'],
                description='基于历史故障记录和维护情况计算'
            ),
            HealthIndexFactor(
                factor_name='环境应力',
                factor_code='environmental_stress',
                score=environmental_stress_score,
                weight=weights['environmental_stress'],
                contribution=environmental_stress_score * weights['environmental_stress'],
                description='基于温度、湿度、振动等环境因素计算'
            ),
            HealthIndexFactor(
                factor_name='使用年限',
                factor_code='service_age',
                score=service_age_score,
                weight=weights['service_age'],
                contribution=service_age_score * weights['service_age'],
                description='基于设计寿命和使用年限的S型老化曲线计算'
            ),
        ]

        hi_score = sum(f.contribution for f in factors)
        hi_score = float(np.clip(hi_score, 0, 100))

        hi_level = self._determine_health_level(hi_score)

        trend, trend_rate = self._calculate_trend(bolt_id, 'bolt', hi_score)

        return HealthIndexResult(
            hi_score=hi_score,
            hi_level=hi_level,
            factors=factors,
            preload_stability_score=preload_stability_score,
            alert_frequency_score=alert_frequency_score,
            fault_history_score=fault_history_score,
            environmental_stress_score=environmental_stress_score,
            service_age_score=service_age_score,
            trend=trend,
            trend_rate=trend_rate,
        )

    def _calculate_preload_stability(
        self,
        preload_data: np.ndarray,
        nominal_preload: float,
    ) -> float:
        """
        计算预紧力稳定性得分（0-100）

        考虑因素：
        1. 均值偏离额定值的程度
        2. 波动性（变异系数）
        3. 趋势稳定性
        4. 极端值比例
        """
        if len(preload_data) == 0:
            return 50.0

        mean_val = np.mean(preload_data)
        std_val = np.std(preload_data)
        cv = std_val / (mean_val + 1e-6)

        deviation_score = self._calculate_deviation_score(mean_val, nominal_preload)
        volatility_score = self._calculate_volatility_score(cv)
        trend_score = self._calculate_data_trend_score(preload_data)
        extreme_score = self._calculate_extreme_value_score(preload_data, nominal_preload)

        stability_score = (
            0.35 * deviation_score +
            0.30 * volatility_score +
            0.20 * trend_score +
            0.15 * extreme_score
        )

        return float(np.clip(stability_score, 0, 100))

    def _calculate_deviation_score(self, mean_val: float, nominal: float) -> float:
        """计算偏离得分"""
        deviation = abs(mean_val - nominal) / nominal
        if deviation <= 0.05:
            return 100.0
        elif deviation <= 0.10:
            return 80.0 - (deviation - 0.05) * 400
        elif deviation <= 0.20:
            return 60.0 - (deviation - 0.10) * 300
        else:
            return max(0, 30.0 - (deviation - 0.20) * 200)

    def _calculate_volatility_score(self, cv: float) -> float:
        """计算波动性得分"""
        if cv <= 0.02:
            return 100.0
        elif cv <= 0.05:
            return 85.0 - (cv - 0.02) * 500
        elif cv <= 0.10:
            return 70.0 - (cv - 0.05) * 400
        else:
            return max(0, 50.0 - (cv - 0.10) * 300)

    def _calculate_data_trend_score(self, data: np.ndarray) -> float:
        """计算数据趋势稳定性得分"""
        if len(data) < 5:
            return 70.0

        x = np.arange(len(data))
        slope, _ = np.polyfit(x, data, 1)
        mean_val = np.mean(data)
        slope_rate = abs(slope) / (mean_val + 1e-6)

        if slope_rate <= 0.001:
            return 100.0
        elif slope_rate <= 0.005:
            return 85.0 - (slope_rate - 0.001) * 3750
        elif slope_rate <= 0.01:
            return 70.0 - (slope_rate - 0.005) * 3000
        else:
            return max(0, 55.0 - (slope_rate - 0.01) * 2000)

    def _calculate_extreme_value_score(self, data: np.ndarray, nominal: float) -> float:
        """计算极端值得分"""
        low_threshold = nominal * 0.7
        high_threshold = nominal * 1.3

        extreme_count = np.sum((data < low_threshold) | (data > high_threshold))
        extreme_ratio = extreme_count / len(data)

        if extreme_ratio <= 0.01:
            return 100.0
        elif extreme_ratio <= 0.05:
            return 90.0 - (extreme_ratio - 0.01) * 500
        elif extreme_ratio <= 0.10:
            return 70.0 - (extreme_ratio - 0.05) * 400
        else:
            return max(0, 50.0 - (extreme_ratio - 0.10) * 300)

    def _calculate_alert_frequency(self, node_id: str, node_type: str) -> float:
        """
        计算预警频率得分（0-100）

        基于最近30天内的告警次数，告警次数越多得分越低。
        """
        try:
            alert_thresholds = self.config_manager.alert_thresholds
            days = alert_thresholds['normal_count_days']
            penalty_per_alert = alert_thresholds['warning_penalty_per_alert']
            max_penalty = alert_thresholds['max_penalty']

            with get_db() as db:
                start_time = datetime.now() - timedelta(days=days)
                alert_count = db.query(AlertEvent).filter(
                    AlertEvent.node_type == node_type,
                    AlertEvent.node_id == str(node_id),
                    AlertEvent.create_time >= start_time,
                    AlertEvent.status != 'ignored'
                ).count()

            base_score = 100.0
            penalty = min(alert_count * penalty_per_alert, max_penalty)
            score = base_score - penalty

            return float(np.clip(score, 0, 100))

        except Exception as e:
            logger.warning(f"计算预警频率得分失败: {e}")
            return 80.0

    def _calculate_fault_history(self, node_id: str, node_type: str) -> float:
        """
        计算故障历史得分（0-100）

        考虑因素：
        1. 历史故障次数
        2. 故障严重程度
        3. 距上次故障的时间
        4. 维护记录
        """
        try:
            with get_db() as db:
                fault_count = db.query(AlertEvent).filter(
                    AlertEvent.node_type == node_type,
                    AlertEvent.node_id == str(node_id),
                    AlertEvent.alert_level >= 3,
                    AlertEvent.status == 'resolved'
                ).count()

                recent_fault = db.query(AlertEvent).filter(
                    AlertEvent.node_type == node_type,
                    AlertEvent.node_id == str(node_id),
                    AlertEvent.alert_level >= 3,
                    AlertEvent.status == 'resolved'
                ).order_by(AlertEvent.resolve_time.desc()).first()

            if fault_count == 0:
                return 100.0

            base_score = 100.0
            base_score -= fault_count * 10

            if recent_fault and recent_fault.resolve_time:
                days_since_fault = (datetime.now() - recent_fault.resolve_time).days
                if days_since_fault < 30:
                    base_score -= 20
                elif days_since_fault < 90:
                    base_score -= 10

            return float(np.clip(base_score, 0, 100))

        except Exception as e:
            logger.warning(f"计算故障历史得分失败: {e}")
            return 70.0

    def _calculate_environmental_stress(self, working_condition: Optional[Dict[str, Any]]) -> float:
        """
        计算环境应力得分（0-100）

        考虑因素：
        1. 温度是否在正常范围
        2. 湿度是否在正常范围
        3. 振动水平
        4. 负载状况
        """
        if working_condition is None:
            return 85.0

        env_factors = self.config_manager.environmental_factors
        score = 100.0

        temperature = working_condition.get('temperature')
        if temperature is not None:
            temp_min, temp_max = env_factors['temp_normal_range']
            if temperature < temp_min:
                score -= (temp_min - temperature) * env_factors['temp_penalty_per_degree']
            elif temperature > temp_max:
                score -= (temperature - temp_max) * env_factors['temp_penalty_per_degree']

        humidity = working_condition.get('humidity')
        if humidity is not None:
            hum_min, hum_max = env_factors['humidity_normal_range']
            if humidity < hum_min:
                score -= (hum_min - humidity) * env_factors['humidity_penalty_per_percent']
            elif humidity > hum_max:
                score -= (humidity - hum_max) * env_factors['humidity_penalty_per_percent']

        vibration = working_condition.get('vibration')
        if vibration is not None and vibration > 0:
            score -= vibration * env_factors['vibration_penalty_factor']

        load_condition = working_condition.get('load_condition')
        if load_condition == 'overload':
            score -= 20
        elif load_condition == 'heavy':
            score -= 10

        return float(np.clip(score, 0, 100))

    def _calculate_service_age(self, service_age_years: float) -> float:
        """
        计算使用年限得分（0-100）

        使用S型老化曲线模型：
        - 前半段老化缓慢
        - 到达拐点后老化加速
        - 接近设计寿命时老化再次减缓
        """
        aging_model = self.config_manager.aging_model
        design_life = aging_model['design_life_years']
        inflection_point = aging_model['inflection_point_years']
        aging_rate = aging_model['aging_rate']

        if service_age_years <= 0:
            return 100.0

        if service_age_years >= design_life:
            return 10.0

        normalized_age = service_age_years / design_life
        normalized_inflection = inflection_point / design_life

        if normalized_age <= normalized_inflection:
            k = aging_rate * 2
            score = 100.0 * (1 - k * normalized_age)
        else:
            remaining_age = normalized_age - normalized_inflection
            remaining_ratio = remaining_age / (1 - normalized_inflection)
            k = aging_rate * 3
            score = 100.0 * (1 - k * normalized_inflection) * (1 - remaining_ratio * 0.9)

        return float(np.clip(score, 0, 100))

    def _determine_health_level(self, hi_score: float) -> str:
        """根据HI分数确定健康等级"""
        thresholds = self.config_manager.thresholds

        if hi_score >= thresholds['excellent']:
            return HealthLevel.EXCELLENT.value
        elif hi_score >= thresholds['good']:
            return HealthLevel.GOOD.value
        elif hi_score >= thresholds['fair']:
            return HealthLevel.FAIR.value
        elif hi_score >= thresholds['poor']:
            return HealthLevel.POOR.value
        else:
            return HealthLevel.CRITICAL.value

    def _calculate_trend(
        self,
        node_id: str,
        node_type: str,
        current_hi: float,
    ) -> Tuple[Optional[str], Optional[float]]:
        """计算健康趋势"""
        try:
            with get_db() as db:
                if node_type == 'bolt':
                    history = db.query(BoltHealthHistory).filter(
                        BoltHealthHistory.bolt_id == str(node_id)
                    ).order_by(BoltHealthHistory.create_time.desc()).limit(5).all()
                else:
                    history = db.query(FlangeHealthHistory).filter(
                        FlangeHealthHistory.flange_id == str(node_id)
                    ).order_by(FlangeHealthHistory.create_time.desc()).limit(5).all()

            if len(history) < 2:
                return None, None

            historical_scores = [h.hi_score for h in reversed(history)]
            historical_scores.append(current_hi)

            x = np.arange(len(historical_scores))
            slope, _ = np.polyfit(x, historical_scores, 1)

            if slope > 0.5:
                trend = HealthTrend.IMPROVING.value
            elif slope < -0.5:
                trend = HealthTrend.DECLINING.value
            else:
                trend = HealthTrend.STABLE.value

            return trend, float(slope)

        except Exception as e:
            logger.warning(f"计算健康趋势失败: {e}")
            return None, None


class FlangeHealthAggregator:
    """法兰面健康度聚合器"""

    def __init__(self):
        self.hi_calculator = HealthIndexCalculator()

    def aggregate_flange_health(
        self,
        flange_id: str,
        bolts_health: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        聚合法兰面下所有螺栓的健康度

        Args:
            flange_id: 法兰面ID
            bolts_health: 螺栓健康度列表，每个元素包含bolt_id和健康度信息

        Returns:
            法兰面聚合健康度结果
        """
        if not bolts_health:
            raise ValueError("螺栓健康度列表不能为空")

        hi_scores = [b['hi_score'] for b in bolts_health]

        worst_idx = int(np.argmin(hi_scores))
        worst_bolt_hi = hi_scores[worst_idx]
        worst_bolt_id = bolts_health[worst_idx]['bolt_id']

        average_hi = float(np.mean(hi_scores))
        median_hi = float(np.median(hi_scores))

        degradation_rate = self._calculate_flange_degradation_rate(flange_id, hi_scores)

        healthy_count = sum(1 for s in hi_scores if s >= 70)
        warning_count = sum(1 for s in hi_scores if 50 <= s < 70)
        critical_count = sum(1 for s in hi_scores if s < 50)

        weights = [0.5, 0.3, 0.2]
        flange_hi = (
            weights[0] * worst_bolt_hi +
            weights[1] * average_hi +
            weights[2] * median_hi
        )
        flange_hi = float(np.clip(flange_hi, 0, 100))

        hi_level = self.hi_calculator._determine_health_level(flange_hi)

        trend = self._determine_flange_trend(flange_id, flange_hi)

        return {
            'flange_id': flange_id,
            'hi_score': flange_hi,
            'hi_level': hi_level,
            'worst_bolt_hi': worst_bolt_hi,
            'worst_bolt_id': worst_bolt_id,
            'average_bolt_hi': average_hi,
            'median_bolt_hi': median_hi,
            'degradation_rate': degradation_rate,
            'bolt_count': len(bolts_health),
            'healthy_bolt_count': healthy_count,
            'warning_bolt_count': warning_count,
            'critical_bolt_count': critical_count,
            'trend': trend,
        }

    def _calculate_flange_degradation_rate(
        self,
        flange_id: str,
        current_scores: List[float],
    ) -> float:
        """计算法兰面劣化速率（HI/天）"""
        try:
            with get_db() as db:
                history = db.query(FlangeHealthHistory).filter(
                    FlangeHealthHistory.flange_id == flange_id
                ).order_by(FlangeHealthHistory.create_time.desc()).limit(10).all()

            if len(history) < 2:
                current_avg = np.mean(current_scores)
                return float((100 - current_avg) / 365)

            hi_values = [h.hi_score for h in reversed(history)]
            current_avg = np.mean(current_scores)
            hi_values.append(current_avg)

            days = [(h.create_time - history[-1].create_time).total_seconds() / 86400 for h in reversed(history)]
            days.append(days[-1] + 1 if days else 0)

            if len(days) >= 2:
                slope, _ = np.polyfit(days, hi_values, 1)
                return float(slope)

            return 0.0

        except Exception as e:
            logger.warning(f"计算法兰面劣化速率失败: {e}")
            return 0.0

    def _determine_flange_trend(self, flange_id: str, current_hi: float) -> Optional[str]:
        """判断法兰面健康趋势"""
        trend, _ = self.hi_calculator._calculate_trend(flange_id, 'flange', current_hi)
        return trend


class ProductionLineRollup:
    """产线/装置级健康度汇总"""

    def __init__(self):
        pass

    def generate_rollup_report(
        self,
        line_id: str,
        line_name: str,
        line_type: str,
        flanges_health: List[Dict[str, Any]],
        report_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        生成产线/装置级健康度汇总报表

        Args:
            line_id: 产线/装置ID
            line_name: 产线/装置名称
            line_type: 产线类型
            flanges_health: 法兰面健康度列表
            report_date: 报告日期

        Returns:
            产线/装置级汇总报表数据
        """
        if not flanges_health:
            raise ValueError("法兰面健康度列表不能为空")

        report_date = report_date or datetime.now()

        flange_hi_scores = [f['hi_score'] for f in flanges_health]
        bolt_counts = [f.get('bolt_count', 0) for f in flanges_health]
        healthy_bolt_counts = [f.get('healthy_bolt_count', 0) for f in flanges_health]
        warning_bolt_counts = [f.get('warning_bolt_count', 0) for f in flanges_health]
        critical_bolt_counts = [f.get('critical_bolt_count', 0) for f in flanges_health]
        degradation_rates = [f.get('degradation_rate', 0) for f in flanges_health]

        overall_hi = float(np.average(
            flange_hi_scores,
            weights=bolt_counts if sum(bolt_counts) > 0 else None
        ))
        overall_hi = float(np.clip(overall_hi, 0, 100))

        overall_level = self._determine_health_level(overall_hi)

        worst_idx = int(np.argmin(flange_hi_scores))
        worst_flange_hi = flange_hi_scores[worst_idx]
        worst_flange_id = flanges_health[worst_idx]['flange_id']

        healthy_flange_count = sum(1 for s in flange_hi_scores if s >= 70)
        warning_flange_count = sum(1 for s in flange_hi_scores if 50 <= s < 70)
        critical_flange_count = sum(1 for s in flange_hi_scores if s < 50)

        avg_degradation_rate = float(np.mean(degradation_rates))

        risk_summary = self._generate_risk_summary(
            flanges_health,
            overall_hi,
            overall_level,
        )

        maintenance_priorities = self._generate_maintenance_priorities(flanges_health)

        return {
            'line_id': line_id,
            'line_name': line_name,
            'line_type': line_type,
            'overall_hi': overall_hi,
            'overall_level': overall_level,
            'total_flange_count': len(flanges_health),
            'total_bolt_count': sum(bolt_counts),
            'healthy_flange_count': healthy_flange_count,
            'warning_flange_count': warning_flange_count,
            'critical_flange_count': critical_flange_count,
            'healthy_bolt_count': sum(healthy_bolt_counts),
            'warning_bolt_count': sum(warning_bolt_counts),
            'critical_bolt_count': sum(critical_bolt_counts),
            'worst_flange_hi': worst_flange_hi,
            'worst_flange_id': worst_flange_id,
            'average_degradation_rate': avg_degradation_rate,
            'flanges_health': flanges_health,
            'risk_summary': risk_summary,
            'maintenance_priorities': maintenance_priorities,
            'report_date': report_date,
            'generate_time': datetime.now(),
        }

    def _determine_health_level(self, hi_score: float) -> str:
        """确定健康等级"""
        if hi_score >= 90:
            return HealthLevel.EXCELLENT.value
        elif hi_score >= 70:
            return HealthLevel.GOOD.value
        elif hi_score >= 50:
            return HealthLevel.FAIR.value
        elif hi_score >= 30:
            return HealthLevel.POOR.value
        else:
            return HealthLevel.CRITICAL.value

    def _generate_risk_summary(
        self,
        flanges_health: List[Dict[str, Any]],
        overall_hi: float,
        overall_level: str,
    ) -> Dict[str, Any]:
        """生成风险汇总"""
        critical_flanges = [f for f in flanges_health if f['hi_score'] < 50]
        warning_flanges = [f for f in flanges_health if 50 <= f['hi_score'] < 70]

        risk_level = 'low'
        if len(critical_flanges) > 0:
            risk_level = 'high'
        elif len(warning_flanges) > 0:
            risk_level = 'medium'

        avg_degradation = float(np.mean([f.get('degradation_rate', 0) for f in flanges_health]))
        accelerating_count = sum(1 for f in flanges_health if f.get('degradation_rate', 0) < -0.1)

        return {
            'overall_risk_level': risk_level,
            'overall_hi': overall_hi,
            'overall_level': overall_level,
            'critical_flange_count': len(critical_flanges),
            'warning_flange_count': len(warning_flanges),
            'average_degradation_rate': avg_degradation,
            'accelerating_degradation_count': accelerating_count,
            'recommended_inspection_count': len(critical_flanges) + len(warning_flanges),
            'summary_text': self._generate_risk_summary_text(
                risk_level, len(critical_flanges), len(warning_flanges), overall_hi
            ),
        }

    def _generate_risk_summary_text(
        self,
        risk_level: str,
        critical_count: int,
        warning_count: int,
        overall_hi: float,
    ) -> str:
        """生成风险摘要文本"""
        if risk_level == 'low':
            return f"整体健康状况良好（HI: {overall_hi:.1f}），无重大风险。建议按计划进行常规维护。"
        elif risk_level == 'medium':
            return f"存在 {warning_count} 个预警法兰面，整体健康度一般（HI: {overall_hi:.1f}）。建议近期安排预防性维护。"
        else:
            return f"存在 {critical_count} 个危险法兰面和 {warning_count} 个预警法兰面，整体健康度较低（HI: {overall_hi:.1f}）。建议立即安排检查和维修。"

    def _generate_maintenance_priorities(
        self,
        flanges_health: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """生成维护优先级排序"""
        priority_list = []

        for flange in flanges_health:
            hi_score = flange['hi_score']
            degradation_rate = flange.get('degradation_rate', 0)

            priority_score = hi_score + degradation_rate * 10

            if hi_score < 50:
                priority = 'urgent'
            elif hi_score < 70:
                priority = 'high'
            elif degradation_rate < -0.05:
                priority = 'medium'
            else:
                priority = 'low'

            critical_bolts = flange.get('critical_bolt_count', 0)
            warning_bolts = flange.get('warning_bolt_count', 0)

            priority_list.append({
                'flange_id': flange['flange_id'],
                'flange_name': flange.get('flange_name', ''),
                'hi_score': hi_score,
                'hi_level': flange['hi_level'],
                'priority': priority,
                'priority_score': priority_score,
                'degradation_rate': degradation_rate,
                'critical_bolt_count': critical_bolts,
                'warning_bolt_count': warning_bolts,
                'worst_bolt_id': flange.get('worst_bolt_id', ''),
                'recommended_action': self._get_maintenance_action(priority, hi_score),
            })

        priority_list.sort(key=lambda x: x['priority_score'])

        for i, item in enumerate(priority_list):
            item['rank'] = i + 1

        return priority_list

    def _get_maintenance_action(self, priority: str, hi_score: float) -> str:
        """获取维护建议"""
        if priority == 'urgent':
            return "立即停机检查，更换问题螺栓，全面检测法兰面密封性能"
        elif priority == 'high':
            return "近期安排检修，紧固或更换预警螺栓，分析劣化原因"
        elif priority == 'medium':
            return "提高监测频率，制定预防性维护计划，关注劣化趋势"
        else:
            return "按常规计划维护，保持日常监测"


class RULPredictor:
    """剩余使用寿命预测器"""

    def predict_rul(
        self,
        node_id: str,
        node_type: str,
        forecast_days: int = 180,
        failure_threshold: float = 30,
        warning_threshold: float = 50,
        model_type: Optional[str] = None,
        use_history_days: int = 90,
    ) -> RULPredictionResult:
        """
        预测剩余使用寿命（RUL）

        Args:
            node_id: 节点ID
            node_type: 节点类型 bolt/flange
            forecast_days: 预测天数
            failure_threshold: 故障阈值HI
            warning_threshold: 预警阈值HI
            model_type: 劣化模型类型，None则自动选择
            use_history_days: 使用多少天历史数据

        Returns:
            RUL预测结果
        """
        historical_hi = self._get_historical_hi(node_id, node_type, use_history_days)

        if len(historical_hi) < 3:
            raise ValueError("历史数据不足，无法进行RUL预测，至少需要3条历史记录")

        if model_type is None:
            best_model, best_r2 = self._select_best_model(historical_hi)
            model_type = best_model
        else:
            best_r2 = None

        hi_values = [h['hi_score'] for h in historical_hi]
        time_days = [h['days_since_start'] for h in historical_hi]

        model_params, predicted_series = self._fit_and_predict(
            time_days, hi_values, forecast_days, model_type
        )

        current_hi = hi_values[-1]

        rul_days = self._calculate_rul(
            predicted_series, failure_threshold, len(time_days)
        )

        rul_lower, rul_upper, confidence = self._calculate_rul_bounds(
            predicted_series, failure_threshold, len(time_days), model_type, len(historical_hi)
        )

        days_to_warning = self._calculate_days_to_threshold(
            predicted_series, warning_threshold, len(time_days)
        )

        forecast_result = []
        start_date = historical_hi[-1]['date']
        for i, pred in enumerate(predicted_series):
            forecast_date = start_date + timedelta(days=i)
            is_prediction = i >= len(time_days)
            forecast_result.append({
                'date': forecast_date,
                'predicted_hi': pred['value'],
                'lower_bound': pred.get('lower', pred['value'] - 5),
                'upper_bound': pred.get('upper', pred['value'] + 5),
                'is_prediction': is_prediction,
            })

        return RULPredictionResult(
            node_id=node_id,
            node_type=node_type,
            current_hi=current_hi,
            rul_days=rul_days,
            rul_lower_bound=rul_lower,
            rul_upper_bound=rul_upper,
            rul_confidence=confidence,
            failure_threshold=failure_threshold,
            warning_threshold=warning_threshold,
            days_to_warning=days_to_warning,
            historical_hi=historical_hi,
            forecast_series=forecast_result,
            degradation_model=model_type,
            model_params=model_params,
            r_squared=best_r2,
        )

    def _get_historical_hi(
        self,
        node_id: str,
        node_type: str,
        use_history_days: int,
    ) -> List[Dict[str, Any]]:
        """获取历史HI数据"""
        try:
            with get_db() as db:
                start_time = datetime.now() - timedelta(days=use_history_days)

                if node_type == 'bolt':
                    history = db.query(BoltHealthHistory).filter(
                        BoltHealthHistory.bolt_id == str(node_id),
                        BoltHealthHistory.create_time >= start_time
                    ).order_by(BoltHealthHistory.create_time.asc()).all()
                else:
                    history = db.query(FlangeHealthHistory).filter(
                        FlangeHealthHistory.flange_id == str(node_id),
                        FlangeHealthHistory.create_time >= start_time
                    ).order_by(FlangeHealthHistory.create_time.asc()).all()

            if not history:
                return []

            start_date = history[0].create_time
            result = []
            for h in history:
                days_since_start = (h.create_time - start_date).total_seconds() / 86400
                result.append({
                    'date': h.create_time,
                    'hi_score': h.hi_score,
                    'hi_level': h.hi_level,
                    'days_since_start': days_since_start,
                })

            return result

        except Exception as e:
            logger.warning(f"获取历史HI数据失败: {e}")
            return []

    def _select_best_model(
        self,
        historical_hi: List[Dict[str, Any]],
    ) -> Tuple[str, Optional[float]]:
        """自动选择最优劣化模型"""
        if len(historical_hi) < 5:
            return DegradationModelType.LINEAR.value, None

        hi_values = [h['hi_score'] for h in historical_hi]
        time_days = [h['days_since_start'] for h in historical_hi]

        r2_scores = {}
        for model_enum in DegradationModelType:
            try:
                params, _ = self._fit_model(time_days, hi_values, model_enum.value)
                r2 = self._calculate_r_squared(time_days, hi_values, params, model_enum.value)
                r2_scores[model_enum.value] = r2
            except Exception:
                continue

        if not r2_scores:
            return DegradationModelType.LINEAR.value, None

        best_model = max(r2_scores.keys(), key=lambda k: r2_scores[k])
        return best_model, r2_scores[best_model]

    def _fit_model(
        self,
        x: List[float],
        y: List[float],
        model_type: str,
    ) -> Tuple[Dict[str, Any], np.ndarray]:
        """拟合劣化模型"""
        x_arr = np.array(x)
        y_arr = np.array(y)

        if model_type == DegradationModelType.LINEAR.value:
            slope, intercept = np.polyfit(x_arr, y_arr, 1)
            params = {'slope': float(slope), 'intercept': float(intercept)}
            fitted = slope * x_arr + intercept
            return params, fitted

        elif model_type == DegradationModelType.EXPONENTIAL.value:
            y_log = np.log(np.clip(y_arr, 1, None))
            slope, intercept = np.polyfit(x_arr, y_log, 1)
            params = {
                'a': float(np.exp(intercept)),
                'b': float(slope),
            }
            fitted = params['a'] * np.exp(params['b'] * x_arr)
            return params, fitted

        elif model_type == DegradationModelType.POLYNOMIAL.value:
            coeffs = np.polyfit(x_arr, y_arr, 2)
            params = {
                'a': float(coeffs[0]),
                'b': float(coeffs[1]),
                'c': float(coeffs[2]),
            }
            fitted = params['a'] * x_arr ** 2 + params['b'] * x_arr + params['c']
            return params, fitted

        else:
            raise ValueError(f"未知的模型类型: {model_type}")

    def _fit_and_predict(
        self,
        x: List[float],
        y: List[float],
        forecast_days: int,
        model_type: str,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """拟合模型并生成预测序列"""
        params, fitted = self._fit_model(x, y, model_type)

        x_last = x[-1]
        future_x = np.linspace(0, x_last + forecast_days, len(x) + forecast_days)

        if model_type == DegradationModelType.LINEAR.value:
            predicted_values = params['slope'] * future_x + params['intercept']
        elif model_type == DegradationModelType.EXPONENTIAL.value:
            predicted_values = params['a'] * np.exp(params['b'] * future_x)
        else:
            predicted_values = params['a'] * future_x ** 2 + params['b'] * future_x + params['c']

        residuals = np.array(y) - fitted
        std_error = float(np.std(residuals)) if len(residuals) > 1 else 5.0

        result = []
        for i, val in enumerate(predicted_values):
            day_num = future_x[i]
            uncertainty = std_error * (1 + (day_num - x_last) / max(forecast_days, 1))
            result.append({
                'day': day_num,
                'value': float(np.clip(val, 0, 100)),
                'lower': float(np.clip(val - uncertainty * 1.96, 0, 100)),
                'upper': float(np.clip(val + uncertainty * 1.96, 0, 100)),
            })

        return params, result

    def _calculate_r_squared(
        self,
        x: List[float],
        y: List[float],
        params: Dict[str, Any],
        model_type: str,
    ) -> float:
        """计算R²拟合优度"""
        x_arr = np.array(x)
        y_arr = np.array(y)

        if model_type == DegradationModelType.LINEAR.value:
            y_pred = params['slope'] * x_arr + params['intercept']
        elif model_type == DegradationModelType.EXPONENTIAL.value:
            y_pred = params['a'] * np.exp(params['b'] * x_arr)
        else:
            y_pred = params['a'] * x_arr ** 2 + params['b'] * x_arr + params['c']

        ss_res = np.sum((y_arr - y_pred) ** 2)
        ss_tot = np.sum((y_arr - np.mean(y_arr)) ** 2)

        if ss_tot == 0:
            return 1.0

        return float(1 - ss_res / ss_tot)

    def _calculate_rul(
        self,
        predicted_series: List[Dict[str, Any]],
        threshold: float,
        history_length: int,
    ) -> float:
        """计算RUL（剩余使用寿命）"""
        for i in range(history_length, len(predicted_series)):
            if predicted_series[i]['value'] <= threshold:
                return float(predicted_series[i]['day'] - predicted_series[history_length - 1]['day'])

        return float(len(predicted_series) - history_length)

    def _calculate_rul_bounds(
        self,
        predicted_series: List[Dict[str, Any]],
        threshold: float,
        history_length: int,
        model_type: str,
        data_points: int,
    ) -> Tuple[float, float, float]:
        """计算RUL置信区间和置信度"""
        rul_lower = None
        rul_upper = None

        for i in range(history_length, len(predicted_series)):
            if predicted_series[i]['upper'] <= threshold and rul_upper is None:
                rul_upper = float(predicted_series[i]['day'] - predicted_series[history_length - 1]['day'])
            if predicted_series[i]['lower'] <= threshold and rul_lower is None:
                rul_lower = float(predicted_series[i]['day'] - predicted_series[history_length - 1]['day'])
                break

        if rul_lower is None:
            rul_lower = float(len(predicted_series) - history_length)
        if rul_upper is None:
            rul_upper = float(len(predicted_series) - history_length) * 1.5

        base_confidence = 0.7
        data_factor = min(data_points / 30, 1.0) * 0.2
        model_factor = 0.1 if model_type != DegradationModelType.LINEAR.value else 0
        confidence = float(np.clip(base_confidence + data_factor + model_factor, 0.5, 0.95))

        return rul_lower, rul_upper, confidence

    def _calculate_days_to_threshold(
        self,
        predicted_series: List[Dict[str, Any]],
        threshold: float,
        history_length: int,
    ) -> Optional[float]:
        """计算到达预警阈值的天数"""
        current_hi = predicted_series[history_length - 1]['value']
        if current_hi <= threshold:
            return 0.0

        for i in range(history_length, len(predicted_series)):
            if predicted_series[i]['value'] <= threshold:
                return float(predicted_series[i]['day'] - predicted_series[history_length - 1]['day'])

        return None


class HealthService:
    """健康度评分服务门面类"""

    def __init__(self):
        self.hi_calculator = HealthIndexCalculator()
        self.flange_aggregator = FlangeHealthAggregator()
        self.line_rollup = ProductionLineRollup()
        self.rul_predictor = RULPredictor()

    def calculate_bolt_health(
        self,
        bolt_id: str,
        data: List[List[Any]],
        working_condition: Optional[Dict[str, Any]] = None,
        nominal_preload: Optional[float] = None,
        service_age_years: float = 0,
        flange_id: Optional[str] = None,
        save_to_db: bool = True,
    ) -> Dict[str, Any]:
        """
        计算螺栓健康度

        Args:
            bolt_id: 螺栓ID
            data: 预紧力时序数据 [[时间, 预紧力], ...]
            working_condition: 工况信息
            nominal_preload: 额定预紧力
            service_age_years: 使用年限
            flange_id: 法兰面ID
            save_to_db: 是否保存到数据库

        Returns:
            健康度计算结果
        """
        timestamps = []
        values = []
        for item in data:
            if len(item) >= 2:
                timestamps.append(item[0])
                values.append(float(item[1]))

        if not values:
            raise ValueError("预紧力数据为空")

        preload_data = np.array(values)
        current_preload = float(preload_data[-1])
        preload_deviation = None
        if nominal_preload:
            preload_deviation = (current_preload - nominal_preload) / nominal_preload * 100

        result = self.hi_calculator.calculate_bolt_health(
            bolt_id=bolt_id,
            preload_data=preload_data,
            timestamps=None,
            working_condition=working_condition,
            nominal_preload=nominal_preload,
            service_age_years=service_age_years,
            flange_id=flange_id,
        )

        result_dict = {
            'bolt_id': bolt_id,
            'hi_score': result.hi_score,
            'hi_level': result.hi_level,
            'factors': [
                {
                    'factor_name': f.factor_name,
                    'factor_code': f.factor_code,
                    'score': f.score,
                    'weight': f.weight,
                    'contribution': f.contribution,
                    'description': f.description,
                }
                for f in result.factors
            ],
            'preload_stability_score': result.preload_stability_score,
            'alert_frequency_score': result.alert_frequency_score,
            'fault_history_score': result.fault_history_score,
            'environmental_stress_score': result.environmental_stress_score,
            'service_age_score': result.service_age_score,
            'trend': result.trend,
            'trend_rate': result.trend_rate,
            'current_preload': current_preload,
            'nominal_preload': nominal_preload,
            'preload_deviation': preload_deviation,
            'calculate_time': datetime.now(),
        }

        if save_to_db:
            self._save_bolt_health(bolt_id, flange_id, result_dict, working_condition)

        return result_dict

    def calculate_flange_health(
        self,
        flange_id: str,
        bolts_data: List[Dict[str, Any]],
        working_condition: Optional[Dict[str, Any]] = None,
        save_to_db: bool = True,
    ) -> Dict[str, Any]:
        """
        计算法兰面健康度

        Args:
            flange_id: 法兰面ID
            bolts_data: 螺栓数据列表 [{bolt_id, data, service_age_years, nominal_preload}, ...]
            working_condition: 工况信息
            save_to_db: 是否保存到数据库

        Returns:
            法兰面健康度聚合结果
        """
        bolts_health = []
        for bolt_data in bolts_data:
            bolt_health = self.calculate_bolt_health(
                bolt_id=bolt_data['bolt_id'],
                data=bolt_data['data'],
                working_condition=working_condition,
                nominal_preload=bolt_data.get('nominal_preload'),
                service_age_years=bolt_data.get('service_age_years', 0),
                flange_id=flange_id,
                save_to_db=save_to_db,
            )
            bolts_health.append(bolt_health)

        flange_result = self.flange_aggregator.aggregate_flange_health(
            flange_id=flange_id,
            bolts_health=bolts_health,
        )

        flange_result['bolts_health'] = bolts_health
        flange_result['calculate_time'] = datetime.now()

        if save_to_db:
            self._save_flange_health(flange_id, flange_result)

        return flange_result

    def generate_rollup_report(
        self,
        line_id: str,
        line_name: str,
        line_type: str,
        flanges_data: List[Dict[str, Any]],
        report_date: Optional[datetime] = None,
        include_details: bool = True,
        save_to_db: bool = True,
    ) -> Dict[str, Any]:
        """
        生成产线/装置级健康度汇总报表

        Args:
            line_id: 产线/装置ID
            line_name: 产线/装置名称
            line_type: 产线类型
            flanges_data: 法兰面数据列表 [{flange_id, bolts_data, working_condition}, ...]
            report_date: 报告日期
            include_details: 是否包含详细数据
            save_to_db: 是否保存到数据库

        Returns:
            产线/装置级汇总报表
        """
        flanges_health = []
        for flange_data in flanges_data:
            flange_health = self.calculate_flange_health(
                flange_id=flange_data['flange_id'],
                bolts_data=flange_data['bolts_data'],
                working_condition=flange_data.get('working_condition'),
                save_to_db=save_to_db,
            )
            if not include_details:
                flange_health.pop('bolts_health', None)
            flanges_health.append(flange_health)

        report = self.line_rollup.generate_rollup_report(
            line_id=line_id,
            line_name=line_name,
            line_type=line_type,
            flanges_health=flanges_health,
            report_date=report_date,
        )

        if save_to_db:
            self._save_rollup_report(report)

        return report

    def predict_rul(
        self,
        node_id: str,
        node_type: str,
        forecast_days: int = 180,
        failure_threshold: float = 30,
        warning_threshold: float = 50,
        model_type: Optional[str] = None,
        use_history_days: int = 90,
        save_to_db: bool = True,
    ) -> Dict[str, Any]:
        """
        预测剩余使用寿命

        Args:
            node_id: 节点ID
            node_type: 节点类型 bolt/flange
            forecast_days: 预测天数
            failure_threshold: 故障阈值
            warning_threshold: 预警阈值
            model_type: 模型类型
            use_history_days: 使用历史数据天数
            save_to_db: 是否保存到数据库

        Returns:
            RUL预测结果
        """
        result = self.rul_predictor.predict_rul(
            node_id=node_id,
            node_type=node_type,
            forecast_days=forecast_days,
            failure_threshold=failure_threshold,
            warning_threshold=warning_threshold,
            model_type=model_type,
            use_history_days=use_history_days,
        )

        result_dict = {
            'node_id': result.node_id,
            'node_type': result.node_type,
            'current_hi': result.current_hi,
            'rul_days': result.rul_days,
            'rul_lower_bound': result.rul_lower_bound,
            'rul_upper_bound': result.rul_upper_bound,
            'rul_confidence': result.rul_confidence,
            'failure_threshold': result.failure_threshold,
            'warning_threshold': result.warning_threshold,
            'days_to_warning': result.days_to_warning,
            'historical_hi': result.historical_hi,
            'forecast_series': [
                {
                    'date': f['date'],
                    'predicted_hi': f['predicted_hi'],
                    'lower_bound': f['lower_bound'],
                    'upper_bound': f['upper_bound'],
                    'is_prediction': f['is_prediction'],
                }
                for f in result.forecast_series
            ],
            'degradation_model': result.degradation_model,
            'model_params': result.model_params,
            'r_squared': result.r_squared,
            'prediction_date': result.prediction_date if hasattr(result, 'prediction_date') else datetime.now(),
        }

        if save_to_db:
            self._save_rul_prediction(result_dict)

        return result_dict

    def get_health_history(
        self,
        node_id: str,
        node_type: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        查询健康度历史

        Args:
            node_id: 节点ID
            node_type: 节点类型 bolt/flange
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制

        Returns:
            健康度历史数据
        """
        try:
            with get_db() as db:
                query = None
                if node_type == 'bolt':
                    query = db.query(BoltHealthHistory).filter(
                        BoltHealthHistory.bolt_id == str(node_id)
                    )
                else:
                    query = db.query(FlangeHealthHistory).filter(
                        FlangeHealthHistory.flange_id == str(node_id)
                    )

                if start_time:
                    query = query.filter(BoltHealthHistory.create_time >= start_time if node_type == 'bolt' else FlangeHealthHistory.create_time >= start_time)
                if end_time:
                    query = query.filter(BoltHealthHistory.create_time <= end_time if node_type == 'bolt' else FlangeHealthHistory.create_time <= end_time)

                query = query.order_by(
                    (BoltHealthHistory.create_time if node_type == 'bolt' else FlangeHealthHistory.create_time).desc()
                ).limit(limit)

                history = query.all()

            history_list = []
            for h in reversed(history):
                item = {
                    'id': h.id,
                    'hi_score': h.hi_score,
                    'hi_level': h.hi_level,
                    'preload_stability_score': getattr(h, 'preload_stability_score', None),
                    'alert_frequency_score': getattr(h, 'alert_frequency_score', None),
                    'fault_history_score': getattr(h, 'fault_history_score', None),
                    'environmental_stress_score': getattr(h, 'environmental_stress_score', None),
                    'service_age_score': getattr(h, 'service_age_score', None),
                    'trend': getattr(h, 'trend', None),
                    'create_time': h.create_time,
                }
                history_list.append(item)

            trend_analysis = self._analyze_history_trend(history_list)

            return {
                'node_id': node_id,
                'node_type': node_type,
                'total': len(history_list),
                'history': history_list,
                'trend_analysis': trend_analysis,
            }

        except Exception as e:
            logger.error(f"查询健康度历史失败: {e}")
            raise

    def _analyze_history_trend(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析历史趋势"""
        if len(history) < 2:
            return {'available': False, 'message': '数据不足，无法分析趋势'}

        hi_scores = [h['hi_score'] for h in history]
        x = np.arange(len(hi_scores))
        slope, intercept = np.polyfit(x, hi_scores, 1)

        recent_avg = np.mean(hi_scores[-3:]) if len(hi_scores) >= 3 else hi_scores[-1]
        earlier_avg = np.mean(hi_scores[:3]) if len(hi_scores) >= 3 else hi_scores[0]

        if slope > 0.3:
            trend = 'improving'
        elif slope < -0.3:
            trend = 'declining'
        else:
            trend = 'stable'

        return {
            'available': True,
            'trend': trend,
            'slope': float(slope),
            'intercept': float(intercept),
            'min_score': float(min(hi_scores)),
            'max_score': float(max(hi_scores)),
            'avg_score': float(np.mean(hi_scores)),
            'recent_avg': float(recent_avg),
            'earlier_avg': float(earlier_avg),
            'change_percent': float((recent_avg - earlier_avg) / max(earlier_avg, 1) * 100),
        }

    def _save_bolt_health(
        self,
        bolt_id: str,
        flange_id: Optional[str],
        result: Dict[str, Any],
        working_condition: Optional[Dict[str, Any]],
    ):
        """保存螺栓健康度到数据库"""
        try:
            with get_db() as db:
                record = BoltHealthHistory(
                    bolt_id=str(bolt_id),
                    flange_id=str(flange_id) if flange_id else None,
                    hi_score=result['hi_score'],
                    hi_level=result['hi_level'],
                    preload_stability_score=result['preload_stability_score'],
                    alert_frequency_score=result['alert_frequency_score'],
                    fault_history_score=result['fault_history_score'],
                    environmental_stress_score=result['environmental_stress_score'],
                    service_age_score=result['service_age_score'],
                    factors_detail=json.dumps(result['factors'], ensure_ascii=False),
                    trend=result.get('trend'),
                    trend_rate=result.get('trend_rate'),
                    current_preload=result.get('current_preload'),
                    nominal_preload=result.get('nominal_preload'),
                    preload_deviation=result.get('preload_deviation'),
                    working_condition=json.dumps(working_condition, ensure_ascii=False) if working_condition else None,
                    create_time=datetime.now(),
                )
                db.add(record)
                db.commit()
        except Exception as e:
            logger.warning(f"保存螺栓健康度失败: {e}")
            db.rollback() if 'db' in locals() else None

    def _save_flange_health(
        self,
        flange_id: str,
        result: Dict[str, Any],
    ):
        """保存法兰面健康度到数据库"""
        try:
            with get_db() as db:
                bolts_summary = []
                for bolt in result.get('bolts_health', []):
                    bolts_summary.append({
                        'bolt_id': bolt['bolt_id'],
                        'hi_score': bolt['hi_score'],
                        'hi_level': bolt['hi_level'],
                    })

                record = FlangeHealthHistory(
                    flange_id=str(flange_id),
                    hi_score=result['hi_score'],
                    hi_level=result['hi_level'],
                    worst_bolt_hi=result['worst_bolt_hi'],
                    worst_bolt_id=result['worst_bolt_id'],
                    average_bolt_hi=result['average_bolt_hi'],
                    median_bolt_hi=result['median_bolt_hi'],
                    degradation_rate=result['degradation_rate'],
                    bolt_count=result['bolt_count'],
                    healthy_bolt_count=result['healthy_bolt_count'],
                    warning_bolt_count=result['warning_bolt_count'],
                    critical_bolt_count=result['critical_bolt_count'],
                    bolts_summary=json.dumps(bolts_summary, ensure_ascii=False),
                    trend=result.get('trend'),
                    create_time=datetime.now(),
                )
                db.add(record)
                db.commit()
        except Exception as e:
            logger.warning(f"保存法兰面健康度失败: {e}")
            db.rollback() if 'db' in locals() else None

    def _save_rul_prediction(self, result: Dict[str, Any]):
        """保存RUL预测结果到数据库"""
        try:
            with get_db() as db:
                record = RULPrediction(
                    node_id=str(result['node_id']),
                    node_type=result['node_type'],
                    current_hi=result['current_hi'],
                    rul_days=result['rul_days'],
                    rul_lower_bound=result['rul_lower_bound'],
                    rul_upper_bound=result['rul_upper_bound'],
                    rul_confidence=result['rul_confidence'],
                    failure_threshold=result['failure_threshold'],
                    warning_threshold=result['warning_threshold'],
                    days_to_warning=result.get('days_to_warning'),
                    historical_hi=json.dumps(result['historical_hi'], default=str, ensure_ascii=False),
                    forecast_series=json.dumps(result['forecast_series'], default=str, ensure_ascii=False),
                    degradation_model=result['degradation_model'],
                    model_params=json.dumps(result['model_params'], ensure_ascii=False),
                    model_r_squared=result.get('r_squared'),
                    prediction_date=result.get('prediction_date', datetime.now()),
                    create_time=datetime.now(),
                )
                db.add(record)
                db.commit()
        except Exception as e:
            logger.warning(f"保存RUL预测结果失败: {e}")
            db.rollback() if 'db' in locals() else None

    def _save_rollup_report(self, report: Dict[str, Any]):
        """保存汇总报表到数据库"""
        try:
            with get_db() as db:
                import uuid
                report_no = f"HR{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:8].upper()}"

                flanges_summary = []
                for flange in report.get('flanges_health', []):
                    flanges_summary.append({
                        'flange_id': flange.get('flange_id'),
                        'hi_score': flange.get('hi_score'),
                        'hi_level': flange.get('hi_level'),
                        'worst_bolt_hi': flange.get('worst_bolt_hi'),
                        'worst_bolt_id': flange.get('worst_bolt_id'),
                        'average_bolt_hi': flange.get('average_bolt_hi'),
                        'degradation_rate': flange.get('degradation_rate'),
                        'bolt_count': flange.get('bolt_count'),
                        'healthy_bolt_count': flange.get('healthy_bolt_count'),
                        'warning_bolt_count': flange.get('warning_bolt_count'),
                        'critical_bolt_count': flange.get('critical_bolt_count'),
                    })

                record = HealthRollupReport(
                    report_no=report_no,
                    line_id=str(report.get('line_id')),
                    line_name=report.get('line_name'),
                    line_type=report.get('line_type'),
                    overall_hi=report.get('overall_hi'),
                    overall_level=report.get('overall_level'),
                    total_flange_count=report.get('total_flange_count'),
                    total_bolt_count=report.get('total_bolt_count'),
                    healthy_flange_count=report.get('healthy_flange_count'),
                    warning_flange_count=report.get('warning_flange_count'),
                    critical_flange_count=report.get('critical_flange_count'),
                    healthy_bolt_count=report.get('healthy_bolt_count'),
                    warning_bolt_count=report.get('warning_bolt_count'),
                    critical_bolt_count=report.get('critical_bolt_count'),
                    worst_flange_hi=report.get('worst_flange_hi'),
                    worst_flange_id=report.get('worst_flange_id'),
                    average_degradation_rate=report.get('average_degradation_rate'),
                    flanges_summary=json.dumps(flanges_summary, ensure_ascii=False),
                    risk_summary=json.dumps(report.get('risk_summary', {}), ensure_ascii=False),
                    maintenance_priorities=json.dumps(report.get('maintenance_priorities', []), ensure_ascii=False),
                    report_date=report.get('report_date', datetime.now()),
                    create_time=datetime.now(),
                )
                db.add(record)
                db.commit()
        except Exception as e:
            logger.warning(f"保存汇总报表失败: {e}")
            db.rollback() if 'db' in locals() else None

    def _save_degradation_curve(
        self,
        node_id: str,
        node_type: str,
        curve_data: List[Dict[str, Any]],
        degradation_rate: float,
        acceleration_rate: float,
        model_type: str,
        model_params: Dict[str, Any],
        r_squared: Optional[float] = None,
    ):
        """保存劣化曲线数据到数据库"""
        try:
            with get_db() as db:
                record = DegradationCurve(
                    node_id=str(node_id),
                    node_type=node_type,
                    curve_data=json.dumps(curve_data, default=str, ensure_ascii=False),
                    degradation_rate=degradation_rate,
                    acceleration_rate=acceleration_rate,
                    model_type=model_type,
                    model_params=json.dumps(model_params, ensure_ascii=False),
                    r_squared=r_squared,
                    create_time=datetime.now(),
                )
                db.add(record)
                db.commit()
        except Exception as e:
            logger.warning(f"保存劣化曲线失败: {e}")
            db.rollback() if 'db' in locals() else None