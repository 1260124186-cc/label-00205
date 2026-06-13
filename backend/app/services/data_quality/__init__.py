"""
数据质量治理平台模块

提供完整的数据质量治理功能：
1. 数据质量规则引擎：缺失率、重复、时间倒挂、越界、漂移检测
2. 质量评分系统：per sensor 质量评分
3. 低质量数据过滤：不参与训练/降低预测置信度
4. 质量报告日报：问题传感器排行、修复建议
5. 异常联动：与 sc_anomaly_data 联动，区分真异常与采集异常

使用示例:
    from app.services.data_quality import DataQualityEngine
    
    engine = DataQualityEngine()
    result = engine.evaluate_sensor_data(
        sensor_id='B001',
        values=preload_values,
        timestamps=timestamps
    )
"""

from app.services.data_quality.rules_engine import (
    DataQualityRule,
    MissingRateRule,
    DuplicateRule,
    TimeInversionRule,
    OutOfBoundsRule,
    DriftDetectionRule,
    RuleViolation,
    QualityCheckResult,
)
from app.services.data_quality.quality_scoring import (
    QualityScorer,
    SensorQualityScore,
    QualityDimensionScore,
)
from app.services.data_quality.filtering import (
    DataQualityFilter,
    FilteredDataResult,
)
from app.services.data_quality.anomaly_linker import (
    AnomalyLinker,
    AnomalyClassification,
    ClassifiedAnomaly,
)
from app.services.data_quality.report_service import (
    QualityReportService,
    DailyQualityReport,
    ProblemSensorRanking,
    RepairRecommendation,
)
from app.services.data_quality.engine import DataQualityEngine

__all__ = [
    'DataQualityRule',
    'MissingRateRule',
    'DuplicateRule',
    'TimeInversionRule',
    'OutOfBoundsRule',
    'DriftDetectionRule',
    'RuleViolation',
    'QualityCheckResult',
    'QualityScorer',
    'SensorQualityScore',
    'QualityDimensionScore',
    'DataQualityFilter',
    'FilteredDataResult',
    'AnomalyLinker',
    'AnomalyClassification',
    'ClassifiedAnomaly',
    'QualityReportService',
    'DailyQualityReport',
    'ProblemSensorRanking',
    'RepairRecommendation',
    'DataQualityEngine',
]
