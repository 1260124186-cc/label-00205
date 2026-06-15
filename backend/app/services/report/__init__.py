"""
报告服务模块

提供智能诊断报告生成服务，包括：
- 单次预测的智能诊断报告
- 周报/月报生成
- LLM集成与降级支持
"""

from app.services.report.diagnosis_report_service import (
    DiagnosisReportService,
    ReportType,
    get_diagnosis_report_service,
)

__all__ = [
    'DiagnosisReportService',
    'ReportType',
    'get_diagnosis_report_service',
]
