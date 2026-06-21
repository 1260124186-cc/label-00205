"""
节点级动态阈值系统 - API请求和响应模型定义

使用Pydantic定义阈值管理API的输入输出数据结构。

包含:
- 节点阈值创建/更新/响应
- 生效阈值解析响应
- 阈值审计日志
- 阈值批量导入
"""

from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class ThresholdParametersSchema(BaseModel):
    """阈值参数（动态键值，不同threshold_type有不同的参数集合）"""
    pass


class NodeThresholdCreateRequest(BaseModel):
    """创建节点阈值请求"""
    node_type: str = Field(..., description="节点类型 bolt/flange")
    node_id: str = Field(..., description="节点ID")
    scope: str = Field('node', description="作用域 global/flange/node")
    source: str = Field('design', description="来源: design/statistical/manual")
    threshold_type: str = Field(..., description="阈值类型: preload/risk/health_index/confidence")
    parameters: Dict[str, Any] = Field(..., description="阈值参数 JSON")
    description: Optional[str] = Field(None, description="变更说明")
    design_value: Optional[float] = Field(None, description="设计值（source=design时）")
    deviation_ratio: Optional[float] = Field(None, description="偏差比例（source=design时）")
    statistical_mean: Optional[float] = Field(None, description="统计均值（source=statistical时）")
    statistical_std: Optional[float] = Field(None, description="统计标准差（source=statistical时）")
    statistical_sample_count: Optional[int] = Field(None, description="统计样本数")
    statistical_window_days: Optional[int] = Field(None, description="统计窗口天数")
    operator_id: Optional[str] = Field(None, description="操作人ID")
    operator_name: Optional[str] = Field(None, description="操作人姓名")


class NodeThresholdUpdateRequest(BaseModel):
    """更新节点阈值请求"""
    parameters: Optional[Dict[str, Any]] = Field(None, description="阈值参数 JSON")
    source: Optional[str] = Field(None, description="来源: design/statistical/manual")
    description: Optional[str] = Field(None, description="变更说明")
    design_value: Optional[float] = Field(None, description="设计值")
    deviation_ratio: Optional[float] = Field(None, description="偏差比例")
    statistical_mean: Optional[float] = Field(None, description="统计均值")
    statistical_std: Optional[float] = Field(None, description="统计标准差")
    statistical_sample_count: Optional[int] = Field(None, description="统计样本数")
    statistical_window_days: Optional[int] = Field(None, description="统计窗口天数")
    operator_id: Optional[str] = Field(None, description="操作人ID")
    operator_name: Optional[str] = Field(None, description="操作人姓名")


class NodeThresholdResponse(BaseModel):
    """节点阈值响应"""
    id: int
    node_type: str
    node_id: str
    scope: str
    source: str
    threshold_type: str
    parameters: Dict[str, Any]
    version: int
    is_active: bool = True
    description: Optional[str] = None
    design_value: Optional[float] = None
    deviation_ratio: Optional[float] = None
    statistical_mean: Optional[float] = None
    statistical_std: Optional[float] = None
    statistical_sample_count: Optional[int] = None
    statistical_window_days: Optional[int] = None
    operator_id: Optional[str] = None
    operator_name: Optional[str] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class EffectiveThresholdResponse(BaseModel):
    """当前生效阈值响应（含优先级解析链）"""
    node_type: str
    node_id: str
    threshold_type: str
    effective: NodeThresholdResponse
    resolution_chain: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="解析链: [{scope, node_type, node_id, version, matched: bool}, ...]"
    )


class NodeThresholdListResponse(BaseModel):
    """阈值列表响应"""
    total: int
    items: List[NodeThresholdResponse]


class ThresholdAuditLogResponse(BaseModel):
    """阈值审计日志响应"""
    id: int
    threshold_id: int
    node_type: str
    node_id: str
    scope: str
    threshold_type: str
    source: str
    action: str
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    version_before: Optional[int] = None
    version_after: Optional[int] = None
    change_summary: Optional[str] = None
    operator_id: Optional[str] = None
    operator_name: Optional[str] = None
    create_time: Optional[datetime] = None


class ThresholdAuditLogListResponse(BaseModel):
    """阈值审计日志列表响应"""
    total: int
    items: List[ThresholdAuditLogResponse]


class ThresholdBatchImportItem(BaseModel):
    """批量导入阈值条目"""
    node_type: str = Field(..., description="节点类型 bolt/flange")
    node_id: str = Field(..., description="节点ID")
    scope: str = Field('node', description="作用域 global/flange/node")
    source: str = Field('design', description="来源: design/statistical/manual")
    threshold_type: str = Field(..., description="阈值类型")
    parameters: Dict[str, Any] = Field(..., description="阈值参数 JSON")
    description: Optional[str] = None
    design_value: Optional[float] = None
    deviation_ratio: Optional[float] = None
    statistical_mean: Optional[float] = None
    statistical_std: Optional[float] = None
    statistical_sample_count: Optional[int] = None
    statistical_window_days: Optional[int] = None


class ThresholdBatchImportRequest(BaseModel):
    """阈值批量导入请求"""
    items: List[ThresholdBatchImportItem] = Field(..., min_length=1, description="阈值条目列表")
    operator_id: Optional[str] = Field(None, description="操作人ID")
    operator_name: Optional[str] = Field(None, description="操作人姓名")


class ThresholdBatchImportResultSchema(BaseModel):
    """批量导入结果"""
    total: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    error_details: Optional[List[Dict[str, Any]]] = None


class ThresholdBatchImportResponse(BaseModel):
    """批量导入响应"""
    status: str
    message: str
    result: Optional[ThresholdBatchImportResultSchema] = None
