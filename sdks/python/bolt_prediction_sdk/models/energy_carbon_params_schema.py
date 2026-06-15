"""
EnergyCarbonParamsSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EnergyCarbonParamsSchema(SDKBaseModel):
    """能耗与碳排增量模型参数"""

    energy_per_leakage_unit: Optional[float] = Field(description="单位泄漏能耗 (kWh/m³)", default=8.5)
    carbon_factor_electricity: Optional[float] = Field(description="电力排放因子 (kgCO₂e/kWh)", default=0.5839)
    carbon_factor_natural_gas: Optional[float] = Field(description="天然气排放因子 (kgCO₂e/kWh)", default=2.1622)
    carbon_factor_steam: Optional[float] = Field(description="蒸汽排放因子 (kgCO₂e/kWh)", default=0.11)
    compressor_efficiency: Optional[float] = Field(description="压缩机效率 0-1", default=0.75)
    recovery_rate: Optional[float] = Field(description="泄漏回收率 0-1", default=0.0)
    base_monthly_energy_kwh: Optional[float] = Field(description="基准月度能耗 (kWh)", default=10000.0)
    base_monthly_carbon_kg: Optional[float] = Field(description="基准月度碳排 (kgCO₂e)", default=5839.0)
