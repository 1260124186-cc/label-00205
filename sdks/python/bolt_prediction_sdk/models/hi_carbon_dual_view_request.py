"""
HICarbonDualViewRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class HiCarbonDualViewRequest(SDKBaseModel):
    """HI rollup 与碳排并列展示请求"""

    nodes: List[Dict[str, Any]] = Field(description="节点数据列表，每项包含: node_id, node_type(可选), node_name(可选), hi_score, hi_level, hi_trend(可选), preload_history, timestamps(可选), service_age_months(可选), avg_temperature(可选), seal_age_years(可选), operating_pressure_mpa(可选)")
