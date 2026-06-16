"""
采购周期与安全库存优化服务模块

负责实现基于需求预测和采购周期的安全库存计算、
经济订货批量(EOQ)计算、再订货点(ROP)计算等功能。

主要功能:
- calculate_safety_stock: 计算安全库存量
- calculate_eoq: 计算经济订货批量
- calculate_reorder_point: 计算再订货点
- calculate_abc_category: 计算ABC分类
- generate_purchase_plan: 生成采购计划建议
"""

import math
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from loguru import logger

from app.utils.database import (
    get_db,
    BoltSkuMapping,
    SparePartInventory,
    SparePartDemand,
    SparePartStockTransaction,
    PurchaseCycleConfig,
    RULPrediction,
)
from app.utils.config import config


Z_SCORE_TABLE = {
    0.90: 1.28,
    0.95: 1.65,
    0.98: 2.05,
    0.99: 2.33,
    0.999: 3.09,
}


class PurchaseOptimizer:
    """
    采购周期与安全库存优化服务类
    """

    def __init__(self):
        opt_config = config.get('purchase_optimizer', {})
        self.default_service_level = opt_config.get(
            'default_service_level', 0.95
        )
        self.default_order_cost = opt_config.get(
            'default_order_cost', 100.0
        )
        self.default_holding_cost_rate = opt_config.get(
            'default_holding_cost_rate', 0.15
        )
        self.default_lead_time_days = opt_config.get(
            'default_lead_time_days', 7
        )
        self.default_safety_stock_days = opt_config.get(
            'default_safety_stock_days', 7
        )
        self.demand_history_days = opt_config.get(
            'demand_history_days', 90
        )
        logger.info("采购优化服务初始化完成")

    # ============== 基础计算方法 ==============

    def get_z_score(self, service_level: float) -> float:
        """
        根据服务水平获取Z分数（正态分布分位数）

        Args:
            service_level: 服务水平 0-1

        Returns:
            float: Z分数
        """
        if service_level <= 0:
            service_level = 0.9
        elif service_level >= 1:
            service_level = 0.999

        for sl, z in sorted(Z_SCORE_TABLE.items()):
            if service_level <= sl:
                return z

        return Z_SCORE_TABLE[0.999]

    def calculate_demand_statistics(
        self,
        sku_code: str,
        history_days: int = None,
    ) -> Dict[str, Any]:
        """
        计算需求统计数据

        Args:
            sku_code: SKU编码
            history_days: 历史天数，默认使用配置值

        Returns:
            Dict: 统计结果
                - avg_daily_demand: 平均日需求量
                - max_daily_demand: 最大日需求量
                - min_daily_demand: 最小日需求量
                - std_daily_demand: 日需求标准差
                - demand_variability: 需求变异系数
                - total_demand: 总需求量
                - days_with_data: 有数据的天数
                - daily_demands: 每日需求量列表
        """
        days = history_days or self.demand_history_days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        with get_db() as db:
            if db is None:
                return {
                    'avg_daily_demand': 0,
                    'max_daily_demand': 0,
                    'min_daily_demand': 0,
                    'std_daily_demand': 0,
                    'demand_variability': 0,
                    'total_demand': 0,
                    'days_with_data': 0,
                    'daily_demands': [],
                }

            transactions = db.query(SparePartStockTransaction).filter(
                SparePartStockTransaction.sku_code == sku_code,
                SparePartStockTransaction.transaction_type == 'issue',
                SparePartStockTransaction.create_time >= start_date,
                SparePartStockTransaction.create_time <= end_date,
            ).all()

            demands = db.query(SparePartDemand).filter(
                SparePartDemand.sku_code == sku_code,
                SparePartDemand.status == 'fulfilled',
                SparePartDemand.create_time >= start_date,
                SparePartDemand.create_time <= end_date,
            ).all()

            daily_demands: Dict[str, int] = {}

            for trans in transactions:
                date_key = trans.create_time.strftime('%Y-%m-%d')
                qty = abs(trans.quantity)
                daily_demands[date_key] = daily_demands.get(date_key, 0) + qty

            for demand in demands:
                date_key = demand.fulfilled_time.strftime('%Y-%m-%d') if demand.fulfilled_time else demand.create_time.strftime('%Y-%m-%d')
                daily_demands[date_key] = daily_demands.get(date_key, 0) + demand.required_quantity

            if not daily_demands:
                rul_demands = db.query(RULPrediction).filter(
                    RULPrediction.rul_days <= 30,
                ).all()
                estimated_daily = len(rul_demands) / max(1, days) * 0.5

                return {
                    'avg_daily_demand': estimated_daily,
                    'max_daily_demand': estimated_daily * 2,
                    'min_daily_demand': 0,
                    'std_daily_demand': estimated_daily * 0.3,
                    'demand_variability': 0.3,
                    'total_demand': estimated_daily * days,
                    'days_with_data': 0,
                    'daily_demands': [],
                    'is_estimated': True,
                }

            values = list(daily_demands.values())
            n = len(values)
            total = sum(values)
            mean = total / n
            max_val = max(values)
            min_val = min(values)

            if n > 1:
                variance = sum((x - mean) ** 2 for x in values) / (n - 1)
                std_dev = math.sqrt(variance)
            else:
                std_dev = mean * 0.2

            variability = std_dev / mean if mean > 0 else 0

            return {
                'avg_daily_demand': round(mean, 4),
                'max_daily_demand': max_val,
                'min_daily_demand': min_val,
                'std_daily_demand': round(std_dev, 4),
                'demand_variability': round(variability, 4),
                'total_demand': total,
                'days_with_data': n,
                'daily_demands': [
                    {'date': k, 'quantity': v}
                    for k, v in sorted(daily_demands.items())
                ],
                'is_estimated': False,
            }

    def calculate_lead_time_statistics(
        self,
        sku_code: str,
    ) -> Dict[str, Any]:
        """
        计算采购提前期统计数据

        Args:
            sku_code: SKU编码

        Returns:
            Dict: 统计结果
                - avg_lead_time_days: 平均提前期(天)
                - max_lead_time_days: 最大提前期(天)
                - min_lead_time_days: 最小提前期(天)
                - std_lead_time_days: 提前期标准差
                - lead_time_variability: 提前期变异系数
                - lead_time_samples: 提前期样本
        """
        with get_db() as db:
            if db is None:
                return {
                    'avg_lead_time_days': self.default_lead_time_days,
                    'max_lead_time_days': self.default_lead_time_days,
                    'min_lead_time_days': self.default_lead_time_days,
                    'std_lead_time_days': 0,
                    'lead_time_variability': 0,
                    'lead_time_samples': [],
                    'is_default': True,
                }

            sku_mapping = db.query(BoltSkuMapping).filter(
                BoltSkuMapping.sku_code == sku_code
            ).first()

            if sku_mapping and sku_mapping.lead_time_days:
                return {
                    'avg_lead_time_days': sku_mapping.lead_time_days,
                    'max_lead_time_days': sku_mapping.lead_time_days + 2,
                    'min_lead_time_days': max(1, sku_mapping.lead_time_days - 1),
                    'std_lead_time_days': 1.0,
                    'lead_time_variability': 1.0 / sku_mapping.lead_time_days,
                    'lead_time_samples': [sku_mapping.lead_time_days],
                    'is_default': False,
                }

            return {
                'avg_lead_time_days': self.default_lead_time_days,
                'max_lead_time_days': self.default_lead_time_days,
                'min_lead_time_days': self.default_lead_time_days,
                'std_lead_time_days': 0,
                'lead_time_variability': 0,
                'lead_time_samples': [],
                'is_default': True,
            }

    def calculate_safety_stock(
        self,
        avg_daily_demand: float,
        std_daily_demand: float,
        avg_lead_time_days: float,
        std_lead_time_days: float = 0,
        service_level: float = None,
        safety_stock_days: int = None,
    ) -> Dict[str, Any]:
        """
        计算安全库存量

        安全库存公式（考虑需求和提前期的不确定性）：
        SS = Z * sqrt(σ_d² * L + σ_L² * d_avg²)

        其中：
        - Z: 服务水平对应的Z分数
        - σ_d: 日需求标准差
        - L: 平均提前期(天)
        - σ_L: 提前期标准差
        - d_avg: 平均日需求量

        Args:
            avg_daily_demand: 平均日需求量
            std_daily_demand: 日需求标准差
            avg_lead_time_days: 平均提前期(天)
            std_lead_time_days: 提前期标准差
            service_level: 服务水平 0-1，默认使用配置值
            safety_stock_days: 安全库存天数（简化计算方式）

        Returns:
            Dict: 计算结果
                - safety_stock_qty: 安全库存量
                - service_level: 服务水平
                - z_score: Z分数
                - calculation_method: 计算方法
                - formula: 计算公式说明
                - components: 计算组成部分
        """
        sl = service_level or self.default_service_level
        z_score = self.get_z_score(sl)

        if safety_stock_days:
            ss_qty = math.ceil(avg_daily_demand * safety_stock_days)
            method = 'days_coverage'
            formula = f'SS = 平均日需求 × 安全库存天数 = {avg_daily_demand} × {safety_stock_days}'
            components = {
                'avg_daily_demand': avg_daily_demand,
                'safety_stock_days': safety_stock_days,
            }
        else:
            demand_variance_during_lead = (
                std_daily_demand ** 2 * avg_lead_time_days
            )
            lead_time_variance_effect = (
                std_lead_time_days ** 2 * avg_daily_demand ** 2
            )
            total_std = math.sqrt(
                demand_variance_during_lead + lead_time_variance_effect
            )
            ss_qty = math.ceil(z_score * total_std)

            method = 'statistical'
            formula = (
                f'SS = Z × √(σ_d²×L + σ_L²×d_avg²) '
                f'= {z_score} × √({std_daily_demand:.4f}²×{avg_lead_time_days} + '
                f'{std_lead_time_days:.4f}²×{avg_daily_demand}²)'
            )
            components = {
                'z_score': z_score,
                'std_daily_demand': std_daily_demand,
                'avg_lead_time_days': avg_lead_time_days,
                'std_lead_time_days': std_lead_time_days,
                'avg_daily_demand': avg_daily_demand,
                'demand_variance_during_lead': demand_variance_during_lead,
                'lead_time_variance_effect': lead_time_variance_effect,
                'total_std': total_std,
            }

        return {
            'safety_stock_qty': max(0, ss_qty),
            'service_level': sl,
            'z_score': z_score,
            'calculation_method': method,
            'formula': formula,
            'components': components,
        }

    def calculate_eoq(
        self,
        annual_demand: float,
        order_cost: float = None,
        unit_price: float = None,
        holding_cost_rate: float = None,
    ) -> Dict[str, Any]:
        """
        计算经济订货批量(EOQ)

        EOQ公式：
        EOQ = √(2DS / H)

        其中：
        - D: 年需求量
        - S: 单次订货成本
        - H: 单位年持有成本 = 单价 × 持有成本率

        Args:
            annual_demand: 年需求量
            order_cost: 单次订货成本，默认使用配置值
            unit_price: 单价，默认从SKU映射获取
            holding_cost_rate: 年持有成本率，默认使用配置值

        Returns:
            Dict: 计算结果
                - eoq_qty: 经济订货批量
                - annual_ordering_cost: 年订货成本
                - annual_holding_cost: 年持有成本
                - total_cost: 总成本(订货+持有)
                - optimal_orders_per_year: 每年最佳订货次数
                - optimal_order_interval_days: 最佳订货间隔(天)
                - formula: 计算公式说明
        """
        s = order_cost or self.default_order_cost
        hcr = holding_cost_rate or self.default_holding_cost_rate

        h = unit_price * hcr if unit_price else 100 * hcr

        if annual_demand <= 0 or s <= 0 or h <= 0:
            return {
                'eoq_qty': 0,
                'annual_ordering_cost': 0,
                'annual_holding_cost': 0,
                'total_cost': 0,
                'optimal_orders_per_year': 0,
                'optimal_order_interval_days': 0,
                'formula': '',
                'is_estimated': False,
            }

        eoq = math.sqrt(2 * annual_demand * s / h)
        eoq_qty = math.ceil(eoq)

        annual_ordering_cost = (annual_demand / eoq_qty) * s if eoq_qty > 0 else 0
        annual_holding_cost = (eoq_qty / 2) * h
        total_cost = annual_ordering_cost + annual_holding_cost

        optimal_orders_per_year = annual_demand / eoq_qty if eoq_qty > 0 else 0
        optimal_order_interval_days = (
            365 / optimal_orders_per_year if optimal_orders_per_year > 0 else 0
        )

        formula = (
            f'EOQ = √(2DS/H) = √(2×{annual_demand:.0f}×{s:.2f}/{h:.2f}) '
            f'= {eoq:.2f} ≈ {eoq_qty}'
        )

        return {
            'eoq_qty': eoq_qty,
            'annual_ordering_cost': round(annual_ordering_cost, 2),
            'annual_holding_cost': round(annual_holding_cost, 2),
            'total_cost': round(total_cost, 2),
            'optimal_orders_per_year': round(optimal_orders_per_year, 2),
            'optimal_order_interval_days': round(optimal_order_interval_days, 1),
            'formula': formula,
            'is_estimated': unit_price is None,
        }

    def calculate_reorder_point(
        self,
        avg_daily_demand: float,
        avg_lead_time_days: float,
        safety_stock_qty: int,
    ) -> Dict[str, Any]:
        """
        计算再订货点(ROP)

        ROP公式：
        ROP = 平均日需求 × 平均提前期 + 安全库存
            = d_avg × L + SS

        Args:
            avg_daily_demand: 平均日需求量
            avg_lead_time_days: 平均提前期(天)
            safety_stock_qty: 安全库存量

        Returns:
            Dict: 计算结果
                - reorder_point_qty: 再订货点数量
                - lead_time_demand: 提前期需求量
                - safety_stock_qty: 安全库存量
                - formula: 计算公式说明
        """
        lead_time_demand = avg_daily_demand * avg_lead_time_days
        rop_qty = math.ceil(lead_time_demand + safety_stock_qty)

        formula = (
            f'ROP = 平均日需求 × 提前期 + 安全库存 '
            f'= {avg_daily_demand} × {avg_lead_time_days} + {safety_stock_qty} '
            f'= {lead_time_demand:.2f} + {safety_stock_qty} = {rop_qty}'
        )

        return {
            'reorder_point_qty': max(0, rop_qty),
            'lead_time_demand': round(lead_time_demand, 2),
            'safety_stock_qty': safety_stock_qty,
            'formula': formula,
        }

    def calculate_abc_category(
        self,
        sku_code: str,
        unit_price: float = None,
        annual_demand_value: float = None,
    ) -> Dict[str, Any]:
        """
        计算ABC分类

        ABC分类规则（基于年使用价值）：
        - A类：前20%的SKU，占80%的年使用价值
        - B类：中间30%的SKU，占15%的年使用价值
        - C类：后50%的SKU，占5%的年使用价值

        Args:
            sku_code: SKU编码
            unit_price: 单价
            annual_demand_value: 年需求价值（如果已计算）

        Returns:
            Dict: 计算结果
                - abc_category: ABC分类 A/B/C
                - annual_demand_qty: 年需求量
                - annual_demand_value: 年需求价值
                - unit_price: 单价
                - percentile: 百分位排名
        """
        with get_db() as db:
            if db is None:
                return {
                    'abc_category': 'C',
                    'annual_demand_qty': 0,
                    'annual_demand_value': 0,
                    'unit_price': unit_price,
                    'percentile': 50,
                }

            if unit_price is None:
                sku_mapping = db.query(BoltSkuMapping).filter(
                    BoltSkuMapping.sku_code == sku_code
                ).first()
                unit_price = sku_mapping.unit_price if sku_mapping else 0

            if annual_demand_value is None:
                demand_stats = self.calculate_demand_statistics(sku_code)
                annual_qty = demand_stats['avg_daily_demand'] * 365
                annual_value = annual_qty * (unit_price or 0)
            else:
                annual_qty = annual_demand_value / unit_price if unit_price else 0
                annual_value = annual_demand_value

            all_skus = db.query(BoltSkuMapping).filter(
                BoltSkuMapping.is_active == True
            ).all()

            if len(all_skus) <= 1:
                category = 'A'
                percentile = 90
            else:
                sku_values = []
                for sku in all_skus:
                    ds = self.calculate_demand_statistics(sku.sku_code, 30)
                    annual_qty_sku = ds['avg_daily_demand'] * 365
                    annual_val_sku = annual_qty_sku * (sku.unit_price or 0)
                    sku_values.append((sku.sku_code, annual_val_sku))

                sku_values.sort(key=lambda x: x[1], reverse=True)

                rank = next(
                    (i for i, (code, _) in enumerate(sku_values) if code == sku_code),
                    len(sku_values) - 1
                )
                percentile = (1 - rank / len(sku_values)) * 100

                if percentile >= 80:
                    category = 'A'
                elif percentile >= 30:
                    category = 'B'
                else:
                    category = 'C'

            return {
                'abc_category': category,
                'annual_demand_qty': round(annual_qty, 2),
                'annual_demand_value': round(annual_value, 2),
                'unit_price': unit_price,
                'percentile': round(percentile, 1),
            }

    # ============== 综合分析方法 ==============

    def analyze_sku(
        self,
        sku_code: str,
        service_level: float = None,
        safety_stock_days: int = None,
    ) -> Dict[str, Any]:
        """
        综合分析单个SKU的采购策略

        Args:
            sku_code: SKU编码
            service_level: 服务水平
            safety_stock_days: 安全库存天数

        Returns:
            Dict: 综合分析结果
                - sku_code: SKU编码
                - sku_name: SKU名称
                - unit_price: 单价
                - demand_statistics: 需求统计
                - lead_time_statistics: 提前期统计
                - safety_stock: 安全库存计算
                - eoq: 经济订货批量计算
                - reorder_point: 再订货点计算
                - abc_category: ABC分类
                - recommendations: 优化建议
        """
        with get_db() as db:
            if db is None:
                return {'error': '数据库不可用'}

            sku_mapping = db.query(BoltSkuMapping).filter(
                BoltSkuMapping.sku_code == sku_code
            ).first()

            if not sku_mapping:
                return {'error': f'SKU不存在: {sku_code}'}

            unit_price = sku_mapping.unit_price
            sku_name = sku_mapping.sku_name

            demand_stats = self.calculate_demand_statistics(sku_code)
            lead_time_stats = self.calculate_lead_time_statistics(sku_code)

            avg_daily = demand_stats['avg_daily_demand']
            std_daily = demand_stats['std_daily_demand']
            avg_lt = lead_time_stats['avg_lead_time_days']
            std_lt = lead_time_stats.get('std_lead_time_days', 0)

            safety_stock = self.calculate_safety_stock(
                avg_daily_demand=avg_daily,
                std_daily_demand=std_daily,
                avg_lead_time_days=avg_lt,
                std_lead_time_days=std_lt,
                service_level=service_level,
                safety_stock_days=safety_stock_days,
            )

            annual_demand = avg_daily * 365
            eoq = self.calculate_eoq(
                annual_demand=annual_demand,
                unit_price=unit_price,
            )

            rop = self.calculate_reorder_point(
                avg_daily_demand=avg_daily,
                avg_lead_time_days=avg_lt,
                safety_stock_qty=safety_stock['safety_stock_qty'],
            )

            abc = self.calculate_abc_category(
                sku_code,
                unit_price=unit_price,
            )

            inventory = db.query(SparePartInventory).filter(
                SparePartInventory.sku_code == sku_code
            ).first()

            recommendations = self._generate_recommendations(
                sku_code=sku_code,
                inventory=inventory,
                safety_stock=safety_stock,
                eoq=eoq,
                rop=rop,
                abc=abc,
                demand_stats=demand_stats,
            )

            return {
                'sku_code': sku_code,
                'sku_name': sku_name,
                'unit_price': unit_price,
                'demand_statistics': demand_stats,
                'lead_time_statistics': lead_time_stats,
                'safety_stock': safety_stock,
                'eoq': eoq,
                'reorder_point': rop,
                'abc_category': abc,
                'recommendations': recommendations,
            }

    def _generate_recommendations(
        self,
        sku_code: str,
        inventory: Optional[SparePartInventory],
        safety_stock: Dict[str, Any],
        eoq: Dict[str, Any],
        rop: Dict[str, Any],
        abc: Dict[str, Any],
        demand_stats: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        生成优化建议列表
        """
        recommendations = []

        if inventory is None:
            recommendations.append({
                'type': 'urgent',
                'priority': 1,
                'title': '库存记录缺失',
                'description': f'SKU {sku_code} 没有库存记录，建议立即建立库存档案',
                'action': 'create_inventory_record',
            })
            return recommendations

        if inventory.quantity_available < safety_stock['safety_stock_qty']:
            deficit = safety_stock['safety_stock_qty'] - inventory.quantity_available
            recommendations.append({
                'type': 'warning',
                'priority': 2,
                'title': '安全库存不足',
                'description': (
                    f'当前可用库存 {inventory.quantity_available} 低于安全库存 '
                    f'{safety_stock["safety_stock_qty"]}，短缺 {deficit} 个'
                ),
                'action': 'replenish_safety_stock',
                'suggested_qty': max(eoq['eoq_qty'], deficit),
            })

        if inventory.quantity_available <= rop['reorder_point_qty']:
            recommendations.append({
                'type': 'info',
                'priority': 3,
                'title': '已达到再订货点',
                'description': (
                    f'当前库存 {inventory.quantity_available} 已达到再订货点 '
                    f'{rop["reorder_point_qty"]}，建议启动采购流程'
                ),
                'action': 'create_purchase_order',
                'suggested_qty': eoq['eoq_qty'],
            })

        if abc['abc_category'] == 'A':
            recommendations.append({
                'type': 'info',
                'priority': 4,
                'title': 'A类物资管理建议',
                'description': (
                    f'该SKU属于A类物资（占年使用价值前20%），'
                    f'建议缩短盘点周期，提高服务水平，加强库存监控'
                ),
                'action': 'enhance_inventory_management',
            })

        if demand_stats.get('is_estimated', False):
            recommendations.append({
                'type': 'info',
                'priority': 5,
                'title': '需求数据不足',
                'description': (
                    '历史需求数据不足，当前使用估算值。建议积累更多数据后重新计算。'
                ),
                'action': 'collect_more_data',
            })

        if demand_stats['demand_variability'] > 0.5:
            recommendations.append({
                'type': 'warning',
                'priority': 6,
                'title': '需求波动较大',
                'description': (
                    f'需求变异系数 {demand_stats["demand_variability"]:.2f} > 0.5，'
                    f'建议适当增加安全库存或建立灵活的补货机制'
                ),
                'action': 'increase_safety_stock',
                'suggested_increase': int(safety_stock['safety_stock_qty'] * 0.2),
            })

        return recommendations

    # ============== 配置管理 ==============

    def save_config(
        self,
        sku_code: str,
        service_level: float = None,
        safety_stock_days: int = None,
        lead_time_days: int = None,
        review_period_days: int = None,
        min_order_qty: int = None,
        max_order_qty: int = None,
        order_cost: float = None,
        holding_cost_rate: float = None,
        description: str = None,
        tenant_id: int = None,
    ) -> Optional[PurchaseCycleConfig]:
        """
        保存采购周期配置

        Args:
            sku_code: SKU编码
            service_level: 服务水平
            safety_stock_days: 安全库存天数
            lead_time_days: 提前期(天)
            review_period_days: 盘点周期(天)
            min_order_qty: 最小订货量
            max_order_qty: 最大订货量
            order_cost: 单次订货成本
            holding_cost_rate: 持有成本率
            description: 备注
            tenant_id: 租户ID

        Returns:
            PurchaseCycleConfig: 保存的配置对象
        """
        analysis = self.analyze_sku(
            sku_code,
            service_level=service_level,
            safety_stock_days=safety_stock_days,
        )

        if 'error' in analysis:
            logger.error(f"分析SKU失败: {analysis['error']}")
            return None

        with get_db() as db:
            if db is None:
                return None

            demand_stats = analysis['demand_statistics']
            ss = analysis['safety_stock']
            eoq = analysis['eoq']
            rop = analysis['reorder_point']
            abc = analysis['abc_category']

            config_record = db.query(PurchaseCycleConfig).filter(
                PurchaseCycleConfig.sku_code == sku_code
            ).first()

            if config_record:
                config_record.service_level = service_level or config_record.service_level
                config_record.safety_stock_days = safety_stock_days or config_record.safety_stock_days
                config_record.lead_time_days = lead_time_days or config_record.lead_time_days
                config_record.review_period_days = review_period_days or config_record.review_period_days
                config_record.min_order_qty = min_order_qty or config_record.min_order_qty
                config_record.max_order_qty = max_order_qty or config_record.max_order_qty
                config_record.order_cost = order_cost or config_record.order_cost
                config_record.holding_cost_rate = holding_cost_rate or config_record.holding_cost_rate
                config_record.description = description or config_record.description
            else:
                config_record = PurchaseCycleConfig(
                    sku_code=sku_code,
                    sku_name=analysis['sku_name'],
                    abc_category=abc['abc_category'],
                    lead_time_days=lead_time_days or self.default_lead_time_days,
                    review_period_days=review_period_days or 30,
                    avg_daily_consumption=demand_stats['avg_daily_demand'],
                    max_daily_consumption=demand_stats['max_daily_demand'],
                    safety_stock_days=safety_stock_days or self.default_safety_stock_days,
                    calculated_safety_stock=ss['safety_stock_qty'],
                    reorder_point=rop['reorder_point_qty'],
                    economic_order_qty=eoq['eoq_qty'],
                    min_order_qty=min_order_qty or 1,
                    max_order_qty=max_order_qty,
                    order_cost=order_cost or self.default_order_cost,
                    holding_cost_rate=holding_cost_rate or self.default_holding_cost_rate,
                    unit_price=analysis['unit_price'],
                    service_level=service_level or self.default_service_level,
                    demand_variability=demand_stats['demand_variability'],
                    lead_time_variability=analysis['lead_time_statistics'].get('lead_time_variability', 0),
                    is_active=True,
                    description=description,
                    tenant_id=tenant_id,
                )
                db.add(config_record)

            config_record.avg_daily_consumption = demand_stats['avg_daily_demand']
            config_record.max_daily_consumption = demand_stats['max_daily_demand']
            config_record.calculated_safety_stock = ss['safety_stock_qty']
            config_record.reorder_point = rop['reorder_point_qty']
            config_record.economic_order_qty = eoq['eoq_qty']
            config_record.demand_variability = demand_stats['demand_variability']
            config_record.abc_category = abc['abc_category']
            config_record.extra_info = json.dumps({
                'safety_stock_calculation': ss,
                'eoq_calculation': eoq,
                'rop_calculation': rop,
                'abc_analysis': abc,
            }, ensure_ascii=False)

            db.commit()

            logger.info(
                f"采购周期配置已保存: {sku_code}, "
                f"安全库存={ss['safety_stock_qty']}, "
                f"再订货点={rop['reorder_point_qty']}, "
                f"EOQ={eoq['eoq_qty']}"
            )

            return db.query(PurchaseCycleConfig).filter(
                PurchaseCycleConfig.sku_code == sku_code
            ).first()

    def generate_purchase_plan(
        self,
        device_id: str = None,
        include_rul_demand: bool = True,
        tenant_id: int = None,
    ) -> Dict[str, Any]:
        """
        生成综合采购计划

        Args:
            device_id: 装置ID，None表示全部
            include_rul_demand: 是否包含基于RUL的预测需求
            tenant_id: 租户ID

        Returns:
            Dict: 采购计划
                - plan_id: 计划编号
                - generated_time: 生成时间
                - device_id: 装置ID
                - total_items: 采购项总数
                - total_estimated_cost: 预估总成本
                - items: 采购项列表
                - summary: 汇总信息
        """
        with get_db() as db:
            if db is None:
                return {'error': '数据库不可用'}

            query = db.query(SparePartInventory)
            if tenant_id:
                query = query.filter(
                    (SparePartInventory.tenant_id == tenant_id) |
                    (SparePartInventory.tenant_id.is_(None))
                )
            inventories = query.all()

            plan_items = []
            total_cost = 0.0

            for inv in inventories:
                analysis = self.analyze_sku(inv.sku_code)
                if 'error' in analysis:
                    continue

                ss = analysis['safety_stock']
                eoq = analysis['eoq']
                rop = analysis['reorder_point']
                abc = analysis['abc_category']

                current_stock = inv.quantity_available
                demand_during_lead = rop['lead_time_demand']

                additional_demand = 0
                if include_rul_demand:
                    rul_demands = db.query(SparePartDemand).filter(
                        SparePartDemand.sku_code == inv.sku_code,
                        SparePartDemand.status.in_(['pending', 'approved']),
                    )
                    if device_id:
                        rul_demands = rul_demands.filter(
                            SparePartDemand.device_id == device_id
                        )
                    additional_demand = sum(
                        d.shortage_quantity or d.required_quantity
                        for d in rul_demands.all()
                    )

                total_required = (
                    ss['safety_stock_qty'] +
                    demand_during_lead +
                    additional_demand
                )
                deficit = max(0, total_required - current_stock)

                if deficit <= 0:
                    continue

                order_qty = max(
                    eoq['eoq_qty'],
                    deficit,
                    analysis.get('demand_statistics', {}).get('avg_daily_demand', 0) * 30,
                )

                if abc['abc_category'] == 'A':
                    service_level = 0.99
                elif abc['abc_category'] == 'B':
                    service_level = 0.95
                else:
                    service_level = 0.90

                urgency = 'normal'
                if current_stock < ss['safety_stock_qty'] * 0.5:
                    urgency = 'critical'
                elif current_stock < ss['safety_stock_qty']:
                    urgency = 'urgent'

                estimated_cost = order_qty * (analysis.get('unit_price', 0) or 0)
                total_cost += estimated_cost

                plan_items.append({
                    'sku_code': inv.sku_code,
                    'sku_name': analysis['sku_name'],
                    'abc_category': abc['abc_category'],
                    'current_stock': current_stock,
                    'safety_stock': ss['safety_stock_qty'],
                    'reorder_point': rop['reorder_point_qty'],
                    'lead_time_demand': demand_during_lead,
                    'additional_rul_demand': additional_demand,
                    'total_required': total_required,
                    'deficit': deficit,
                    'recommended_order_qty': int(order_qty),
                    'eoq_qty': eoq['eoq_qty'],
                    'unit_price': analysis.get('unit_price'),
                    'estimated_cost': round(estimated_cost, 2),
                    'urgency': urgency,
                    'service_level': service_level,
                    'lead_time_days': analysis['lead_time_statistics']['avg_lead_time_days'],
                    'expected_delivery_date': (
                        datetime.now() +
                        timedelta(days=analysis['lead_time_statistics']['avg_lead_time_days'])
                    ).isoformat(),
                    'recommendations': [
                        r['title'] for r in analysis.get('recommendations', [])
                        if r['type'] in ['warning', 'urgent']
                    ],
                })

            plan_items.sort(
                key=lambda x: (
                    x['urgency'] == 'critical',
                    x['urgency'] == 'urgent',
                    x['abc_category'] == 'A',
                    -x['deficit'],
                ),
                reverse=True,
            )

            plan_id = f"PP{datetime.now().strftime('%Y%m%d%H%M%S')}"

            summary = {
                'critical_items': sum(1 for i in plan_items if i['urgency'] == 'critical'),
                'urgent_items': sum(1 for i in plan_items if i['urgency'] == 'urgent'),
                'normal_items': sum(1 for i in plan_items if i['urgency'] == 'normal'),
                'a_class_items': sum(1 for i in plan_items if i['abc_category'] == 'A'),
                'b_class_items': sum(1 for i in plan_items if i['abc_category'] == 'B'),
                'c_class_items': sum(1 for i in plan_items if i['abc_category'] == 'C'),
                'total_deficit_qty': sum(i['deficit'] for i in plan_items),
                'total_recommended_qty': sum(i['recommended_order_qty'] for i in plan_items),
            }

            return {
                'plan_id': plan_id,
                'generated_time': datetime.now().isoformat(),
                'device_id': device_id,
                'include_rul_demand': include_rul_demand,
                'total_items': len(plan_items),
                'total_estimated_cost': round(total_cost, 2),
                'items': plan_items,
                'summary': summary,
            }

    def list_configs(
        self,
        sku_code: str = None,
        abc_category: str = None,
        is_active: bool = None,
        tenant_id: int = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PurchaseCycleConfig]:
        """
        查询采购周期配置列表

        Args:
            sku_code: SKU编码（精确匹配）
            abc_category: ABC分类
            is_active: 是否启用
            tenant_id: 租户ID
            limit: 分页限制
            offset: 分页偏移

        Returns:
            List[PurchaseCycleConfig]: 配置列表
        """
        with get_db() as db:
            if db is None:
                return []

            query = db.query(PurchaseCycleConfig)

            if sku_code:
                query = query.filter(PurchaseCycleConfig.sku_code == sku_code)
            if abc_category:
                query = query.filter(PurchaseCycleConfig.abc_category == abc_category)
            if is_active is not None:
                query = query.filter(PurchaseCycleConfig.is_active == is_active)
            if tenant_id:
                query = query.filter(
                    (PurchaseCycleConfig.tenant_id == tenant_id) |
                    (PurchaseCycleConfig.tenant_id.is_(None))
                )

            return query.order_by(
                PurchaseCycleConfig.update_time.desc()
            ).offset(offset).limit(limit).all()
