"""
合规与检验标准检查引擎模块

包含:
- ComplianceInspectionService: 合规检验核心服务
  - 标准模板库管理（API 650, ASME PCC-1 等）
  - 按装置类型加载检查清单
  - 预测紧急预警时自动勾选必检项
  - 检验完成度评分
  - 未完成项阻止工单关闭
  - PDF 检验报告导出
"""

from app.services.compliance.compliance_inspection_service import ComplianceInspectionService

__all__ = [
    'ComplianceInspectionService',
]
