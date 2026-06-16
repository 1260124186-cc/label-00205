"""
备件库存与 RUL 联动服务模块

负责实现螺栓型号与备件SKU映射、RUL阈值触发备件需求、
库存查询、缺货工单升级、装置需求汇总等核心功能。

主要功能:
- get_sku_for_bolt: 根据螺栓型号获取对应SKU
- check_inventory: 查询备件库存
- generate_demand_from_rul: 根据RUL预测生成备件需求
- upgrade_work_order_priority: 缺货时升级工单优先级
- generate_device_summary: 生成装置级备件需求汇总
"""

import json
import math
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from loguru import logger

from app.utils.database import (
    get_db,
    BoltSkuMapping,
    SparePartInventory,
    SparePartDemand,
    SparePartDemandSummary,
    RULPrediction,
    WorkOrder,
    OrganizationNode,
)
from app.utils.config import config
from app.services.alert.work_order_service import WorkOrderService


DEFAULT_RUL_THRESHOLD_DAYS = 30
URGENT_RUL_THRESHOLD_DAYS = 14
CRITICAL_RUL_THRESHOLD_DAYS = 7

RUL_URGENCY_MAP = {
    'critical': CRITICAL_RUL_THRESHOLD_DAYS,
    'urgent': URGENT_RUL_THRESHOLD_DAYS,
    'normal': DEFAULT_RUL_THRESHOLD_DAYS,
}


class SparePartService:
    """
    备件库存与 RUL 联动服务类
    """

    def __init__(self):
        sp_config = config.get('spare_parts', {})
        self.default_rul_threshold = sp_config.get(
            'default_rul_threshold_days', DEFAULT_RUL_THRESHOLD_DAYS
        )
        self.urgent_rul_threshold = sp_config.get(
            'urgent_rul_threshold_days', URGENT_RUL_THRESHOLD_DAYS
        )
        self.critical_rul_threshold = sp_config.get(
            'critical_rul_threshold_days', CRITICAL_RUL_THRESHOLD_DAYS
        )
        self.default_warehouse = sp_config.get(
            'default_warehouse', 'main'
        )
        self.auto_upgrade_priority = sp_config.get(
            'auto_upgrade_priority', True
        )
        logger.info("备件库存与RUL联动服务初始化完成")

    # ============== 螺栓型号-SKU映射 ==============

    def get_sku_for_bolt(
        self,
        bolt_model: str,
        tenant_id: int = None,
    ) -> Optional[BoltSkuMapping]:
        """
        根据螺栓型号获取对应备件SKU

        Args:
            bolt_model: 螺栓型号
            tenant_id: 租户ID

        Returns:
            BoltSkuMapping: SKU映射对象，不存在则返回None
        """
        with get_db() as db:
            if db is None:
                return None

            query = db.query(BoltSkuMapping).filter(
                BoltSkuMapping.bolt_model == bolt_model,
                BoltSkuMapping.is_active == True,
            )
            if tenant_id:
                query = query.filter(
                    (BoltSkuMapping.tenant_id == tenant_id) |
                    (BoltSkuMapping.tenant_id.is_(None))
                )

            return query.first()

    def list_sku_mappings(
        self,
        bolt_model: str = None,
        sku_code: str = None,
        is_active: bool = None,
        tenant_id: int = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[BoltSkuMapping]:
        """
        查询螺栓-SKU映射列表

        Args:
            bolt_model: 螺栓型号（模糊匹配）
            sku_code: SKU编码（精确匹配）
            is_active: 是否启用
            tenant_id: 租户ID
            limit: 分页限制
            offset: 分页偏移

        Returns:
            List[BoltSkuMapping]: 映射列表
        """
        with get_db() as db:
            if db is None:
                return []

            query = db.query(BoltSkuMapping)

            if bolt_model:
                query = query.filter(
                    BoltSkuMapping.bolt_model.like(f'%{bolt_model}%')
                )
            if sku_code:
                query = query.filter(BoltSkuMapping.sku_code == sku_code)
            if is_active is not None:
                query = query.filter(BoltSkuMapping.is_active == is_active)
            if tenant_id:
                query = query.filter(
                    (BoltSkuMapping.tenant_id == tenant_id) |
                    (BoltSkuMapping.tenant_id.is_(None))
                )

            return query.order_by(
                BoltSkuMapping.update_time.desc()
            ).offset(offset).limit(limit).all()

    def create_sku_mapping(
        self,
        bolt_model: str,
        sku_code: str,
        sku_name: str,
        bolt_spec: str = None,
        material: str = None,
        standard: str = None,
        diameter: float = None,
        length: float = None,
        grade: str = None,
        unit: str = '个',
        unit_price: float = None,
        supplier: str = None,
        manufacturer: str = None,
        lead_time_days: int = 7,
        min_order_qty: int = 1,
        description: str = None,
        tenant_id: int = None,
    ) -> Optional[BoltSkuMapping]:
        """
        创建螺栓-SKU映射

        Returns:
            BoltSkuMapping: 创建的映射对象
        """
        with get_db() as db:
            if db is None:
                return None

            existing = db.query(BoltSkuMapping).filter(
                BoltSkuMapping.sku_code == sku_code
            ).first()
            if existing:
                logger.warning(f"SKU编码已存在: {sku_code}")
                return existing

            mapping = BoltSkuMapping(
                bolt_model=bolt_model,
                bolt_spec=bolt_spec,
                material=material,
                standard=standard,
                diameter=diameter,
                length=length,
                grade=grade,
                sku_code=sku_code,
                sku_name=sku_name,
                unit=unit,
                unit_price=unit_price,
                supplier=supplier,
                manufacturer=manufacturer,
                lead_time_days=lead_time_days,
                min_order_qty=min_order_qty,
                is_active=True,
                description=description,
                tenant_id=tenant_id,
            )

            db.add(mapping)
            db.commit()

            logger.info(
                f"螺栓-SKU映射已创建: {bolt_model} -> {sku_code}"
            )

            return db.query(BoltSkuMapping).filter(
                BoltSkuMapping.id == mapping.id
            ).first()

    # ============== 库存查询 ==============

    def check_inventory(
        self,
        sku_code: str,
        warehouse_code: str = None,
        tenant_id: int = None,
    ) -> Optional[SparePartInventory]:
        """
        查询备件库存

        Args:
            sku_code: 备件SKU编码
            warehouse_code: 仓库编码，默认使用配置的默认仓库
            tenant_id: 租户ID

        Returns:
            SparePartInventory: 库存对象，不存在则返回None
        """
        with get_db() as db:
            if db is None:
                return None

            warehouse = warehouse_code or self.default_warehouse

            query = db.query(SparePartInventory).filter(
                SparePartInventory.sku_code == sku_code,
                SparePartInventory.warehouse_code == warehouse,
            )
            if tenant_id:
                query = query.filter(
                    (SparePartInventory.tenant_id == tenant_id) |
                    (SparePartInventory.tenant_id.is_(None))
                )

            return query.first()

    def list_inventory(
        self,
        sku_code: str = None,
        warehouse_code: str = None,
        stock_status: str = None,
        abc_category: str = None,
        tenant_id: int = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SparePartInventory]:
        """
        查询库存列表

        Args:
            sku_code: SKU编码（模糊匹配）
            warehouse_code: 仓库编码
            stock_status: 库存状态 in_stock/low_stock/out_of_stock
            abc_category: ABC分类
            tenant_id: 租户ID
            limit: 分页限制
            offset: 分页偏移

        Returns:
            List[SparePartInventory]: 库存列表
        """
        with get_db() as db:
            if db is None:
                return []

            query = db.query(SparePartInventory)

            if sku_code:
                query = query.filter(
                    SparePartInventory.sku_code.like(f'%{sku_code}%')
                )
            if warehouse_code:
                query = query.filter(
                    SparePartInventory.warehouse_code == warehouse_code
                )
            if abc_category:
                query = query.filter(
                    SparePartInventory.abc_category == abc_category
                )
            if tenant_id:
                query = query.filter(
                    (SparePartInventory.tenant_id == tenant_id) |
                    (SparePartInventory.tenant_id.is_(None))
                )

            if stock_status == 'out_of_stock':
                query = query.filter(SparePartInventory.quantity_available == 0)
            elif stock_status == 'low_stock':
                query = query.filter(
                    SparePartInventory.quantity_available > 0,
                    SparePartInventory.quantity_available <= SparePartInventory.safety_stock
                )
            elif stock_status == 'in_stock':
                query = query.filter(
                    SparePartInventory.quantity_available > SparePartInventory.safety_stock
                )

            return query.order_by(
                SparePartInventory.update_time.desc()
            ).offset(offset).limit(limit).all()

    def check_stock_availability(
        self,
        sku_code: str,
        required_quantity: int,
        warehouse_code: str = None,
    ) -> Dict[str, Any]:
        """
        检查库存可用性

        Args:
            sku_code: SKU编码
            required_quantity: 需求数量
            warehouse_code: 仓库编码

        Returns:
            Dict: 包含以下字段的字典
                - is_available: 是否可用
                - stock_status: 库存状态 in_stock/partial/out_of_stock
                - available_quantity: 可用数量
                - shortage_quantity: 短缺数量
                - inventory: 库存对象
        """
        inventory = self.check_inventory(sku_code, warehouse_code)

        if inventory is None:
            return {
                'is_available': False,
                'stock_status': 'out_of_stock',
                'available_quantity': 0,
                'shortage_quantity': required_quantity,
                'inventory': None,
            }

        available = inventory.quantity_available
        shortage = max(0, required_quantity - available)

        if available >= required_quantity:
            status = 'in_stock'
            is_available = True
        elif available > 0:
            status = 'partial'
            is_available = False
        else:
            status = 'out_of_stock'
            is_available = False

        return {
            'is_available': is_available,
            'stock_status': status,
            'available_quantity': available,
            'shortage_quantity': shortage,
            'inventory': inventory,
        }

    # ============== RUL联动生成备件需求 ==============

    def _determine_urgency(
        self,
        rul_days: float,
    ) -> Tuple[str, int]:
        """
        根据RUL天数确定紧急程度和优先级

        Args:
            rul_days: 剩余使用寿命天数

        Returns:
            Tuple[str, int]: (紧急程度, 优先级)
        """
        if rul_days <= self.critical_rul_threshold:
            return 'critical', 1
        elif rul_days <= self.urgent_rul_threshold:
            return 'urgent', 2
        elif rul_days <= self.default_rul_threshold:
            return 'normal', 3
        else:
            return 'normal', 4

    def _get_device_info(
        self,
        node_type: str,
        node_id: str,
        tenant_id: int = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        获取节点所属的装置信息

        Args:
            node_type: 节点类型 bolt/flange
            node_id: 节点ID

        Returns:
            Tuple[Optional[str], Optional[str]]: (装置ID, 装置名称)
        """
        try:
            with get_db() as db:
                if db is None:
                    return None, None

                org_node = db.query(OrganizationNode).filter(
                    OrganizationNode.node_type == node_type,
                    OrganizationNode.node_code == str(node_id),
                ).first()

                if org_node and org_node.path:
                    path_parts = [p for p in org_node.path.split('/') if p]
                    if len(path_parts) >= 3:
                        device_id = path_parts[2]
                        device_node = db.query(OrganizationNode).filter(
                            OrganizationNode.id == int(device_id)
                        ).first()
                        if device_node:
                            return str(device_node.id), device_node.node_name

        except Exception as e:
            logger.warning(f"获取装置信息失败: {e}")

        return None, None

    def _generate_demand_no(self, db) -> str:
        """生成唯一需求单号"""
        now = datetime.now()
        prefix = now.strftime('SPD%Y%m%d%H%M%S')
        for i in range(100):
            candidate = f"{prefix}{i:02d}"
            exists = db.query(SparePartDemand).filter(
                SparePartDemand.demand_no == candidate
            ).first()
            if not exists:
                return candidate
        raise RuntimeError("生成需求单号失败")

    def generate_demand_from_rul(
        self,
        rul_prediction: RULPrediction,
        bolt_model: str,
        required_quantity: int = 1,
        tenant_id: int = None,
        auto_check_stock: bool = True,
        auto_create_work_order: bool = True,
    ) -> Optional[SparePartDemand]:
        """
        根据RUL预测生成备件需求建议

        Args:
            rul_prediction: RUL预测对象
            bolt_model: 螺栓型号
            required_quantity: 需求数量
            tenant_id: 租户ID
            auto_check_stock: 是否自动检查库存
            auto_create_work_order: 是否自动创建工单

        Returns:
            SparePartDemand: 创建的需求单
        """
        sku_mapping = self.get_sku_for_bolt(bolt_model, tenant_id)
        if not sku_mapping:
            logger.warning(
                f"未找到螺栓型号 {bolt_model} 对应的SKU映射"
            )
            return None

        urgency, priority = self._determine_urgency(rul_prediction.rul_days)

        device_id, device_name = self._get_device_info(
            rul_prediction.node_type,
            rul_prediction.node_id,
            tenant_id,
        )

        estimated_failure_date = None
        if rul_prediction.rul_days and rul_prediction.prediction_date:
            estimated_failure_date = (
                rul_prediction.prediction_date +
                timedelta(days=rul_prediction.rul_days)
            )

        required_date = estimated_failure_date
        if required_date and sku_mapping.lead_time_days:
            required_date = required_date - timedelta(
                days=sku_mapping.lead_time_days
            )

        with get_db() as db:
            if db is None:
                return None

            existing = db.query(SparePartDemand).filter(
                SparePartDemand.source_type == 'rul',
                SparePartDemand.source_id == str(rul_prediction.id),
                SparePartDemand.sku_code == sku_mapping.sku_code,
                SparePartDemand.status.in_(['pending', 'approved']),
            ).first()

            if existing:
                logger.info(
                    f"已存在针对RUL {rul_prediction.id} 的需求单: {existing.demand_no}"
                )
                return existing

            demand = SparePartDemand(
                demand_no=self._generate_demand_no(db),
                source_type='rul',
                source_id=str(rul_prediction.id),
                node_type=rul_prediction.node_type,
                node_id=rul_prediction.node_id,
                bolt_model=bolt_model,
                sku_code=sku_mapping.sku_code,
                sku_name=sku_mapping.sku_name,
                required_quantity=required_quantity,
                urgency=urgency,
                priority=priority,
                rul_days=rul_prediction.rul_days,
                rul_threshold=self.default_rul_threshold,
                estimated_failure_date=estimated_failure_date,
                required_date=required_date,
                status='pending',
                device_id=device_id,
                device_name=device_name,
                tenant_id=tenant_id,
            )

            if auto_check_stock:
                stock_check = self.check_stock_availability(
                    sku_mapping.sku_code
                )
                demand.stock_status = stock_check['stock_status']
                demand.available_quantity = stock_check['available_quantity']
                demand.shortage_quantity = stock_check['shortage_quantity']

            db.add(demand)
            db.flush()
            demand_id = demand.id
            db.commit()

            logger.info(
                f"备件需求单已创建: {demand.demand_no}, "
                f"螺栓型号={bolt_model}, SKU={sku_mapping.sku_code}, "
                f"RUL={rul_prediction.rul_days:.1f}天, 紧急程度={urgency}"
            )

            if auto_create_work_order and demand.stock_status == 'out_of_stock':
                try:
                    wo_id = self._create_work_order_for_shortage(demand, rul_prediction)
                    if wo_id:
                        demand.work_order_id = wo_id
                        db.commit()
                except Exception as e:
                    logger.error(f"创建缺货工单失败: {e}")

            if (self.auto_upgrade_priority and
                demand.stock_status == 'out_of_stock' and
                demand.work_order_id):
                try:
                    self.upgrade_work_order_priority(demand.work_order_id)
                    demand.work_order_priority_upgraded = True
                    db.commit()
                except Exception as e:
                    logger.error(f"升级工单优先级失败: {e}")

            return db.query(SparePartDemand).filter(
                SparePartDemand.id == demand_id
            ).first()

    def _create_work_order_for_shortage(
        self,
        demand: SparePartDemand,
        rul_prediction: RULPrediction,
    ) -> Optional[int]:
        """
        为缺货创建工单

        Args:
            demand: 备件需求单
            rul_prediction: RUL预测

        Returns:
            int: 创建的工单ID
        """
        wo_service = WorkOrderService()

        node_label = '螺栓' if demand.node_type == 'bolt' else '法兰面'
        urgency_label = {
            'critical': '特急',
            'urgent': '紧急',
            'normal': '普通',
        }.get(demand.urgency, '普通')

        title = (
            f"[{urgency_label}]备件缺货 - {node_label}{demand.node_id} "
            f"RUL={demand.rul_days:.0f}天"
        )

        description = (
            f"备件缺货告警\n"
            f"节点类型: {node_label}\n"
            f"节点ID: {demand.node_id}\n"
            f"螺栓型号: {demand.bolt_model}\n"
            f"备件SKU: {demand.sku_code} - {demand.sku_name}\n"
            f"需求数量: {demand.required_quantity}\n"
            f"可用库存: {demand.available_quantity}\n"
            f"短缺数量: {demand.shortage_quantity}\n"
            f"RUL剩余: {demand.rul_days:.1f}天\n"
            f"预计故障日期: {demand.estimated_failure_date}\n"
            f"建议需求日期: {demand.required_date}\n"
            f"装置: {demand.device_name or '未知'}\n"
            f"需求单号: {demand.demand_no}"
        )

        priority_map = {
            'critical': 'urgent',
            'urgent': 'high',
            'normal': 'medium',
        }
        priority = priority_map.get(demand.urgency, 'medium')

        alert_level_map = {
            'critical': 4,
            'urgent': 3,
            'normal': 2,
        }
        alert_level = alert_level_map.get(demand.urgency, 2)

        due_hours_map = {
            'critical': 4,
            'urgent': 24,
            'normal': 48,
        }

        work_order = wo_service.create_manual_work_order(
            title=title,
            description=description,
            priority=priority,
            node_type=demand.node_type,
            node_id=demand.node_id,
            alert_level=alert_level,
            risk_score=100 - (demand.rul_days or 0) * 2,
            due_hours=due_hours_map.get(demand.urgency, 48),
            recommendations=[
                f"紧急采购备件: {demand.sku_name} ({demand.sku_code})",
                f"预计需要 {demand.required_quantity} 个",
                f"请在 {demand.required_date} 前完成采购",
            ],
            extra_info={
                'source': 'spare_part_shortage',
                'demand_id': demand.id,
                'demand_no': demand.demand_no,
                'sku_code': demand.sku_code,
                'shortage_quantity': demand.shortage_quantity,
                'rul_days': demand.rul_days,
                'estimated_failure_date': demand.estimated_failure_date.isoformat() if demand.estimated_failure_date else None,
            },
        )

        if work_order:
            logger.info(
                f"缺货工单已创建: {work_order.order_no}, "
                f"优先级={priority}"
            )
            return work_order.id

        return None

    def upgrade_work_order_priority(
        self,
        work_order_id: int,
        operator_id: str = 'system',
        operator_name: str = '系统自动',
    ) -> Optional[WorkOrder]:
        """
        缺货时升级工单优先级

        Args:
            work_order_id: 工单ID
            operator_id: 操作人ID
            operator_name: 操作人姓名

        Returns:
            WorkOrder: 更新后的工单
        """
        with get_db() as db:
            if db is None:
                return None

            work_order = db.query(WorkOrder).filter(
                WorkOrder.id == work_order_id
            ).first()

            if not work_order:
                logger.warning(f"工单不存在: {work_order_id}")
                return None

            priority_order = ['low', 'medium', 'high', 'urgent']
            current_idx = priority_order.index(work_order.priority)
            if current_idx < len(priority_order) - 1:
                new_priority = priority_order[current_idx + 1]
                old_priority = work_order.priority
                work_order.priority = new_priority

                due_hours_map = {
                    'low': 72,
                    'medium': 48,
                    'high': 24,
                    'urgent': 4,
                }
                new_due_hours = due_hours_map.get(new_priority, 48)
                work_order.due_time = datetime.now() + timedelta(hours=new_due_hours)

                extra_info = {}
                if work_order.extra_info:
                    try:
                        extra_info = json.loads(work_order.extra_info)
                    except (json.JSONDecodeError, TypeError):
                        pass

                upgrade_history = extra_info.get('priority_upgrade_history', [])
                upgrade_history.append({
                    'from_priority': old_priority,
                    'to_priority': new_priority,
                    'reason': '备件缺货自动升级',
                    'operator_id': operator_id,
                    'operator_name': operator_name,
                    'time': datetime.now().isoformat(),
                })
                extra_info['priority_upgrade_history'] = upgrade_history
                work_order.extra_info = json.dumps(extra_info, ensure_ascii=False)

                if work_order.resolve_note:
                    work_order.resolve_note += (
                        f"\n---\n[{operator_name}] {datetime.now().isoformat()}\n"
                        f"因备件缺货，优先级从 {old_priority} 升级为 {new_priority}"
                    )
                else:
                    work_order.resolve_note = (
                        f"[{operator_name}] {datetime.now().isoformat()}\n"
                        f"因备件缺货，优先级从 {old_priority} 升级为 {new_priority}"
                    )

                db.commit()
                logger.info(
                    f"工单 {work_order.order_no} 优先级已从 {old_priority} "
                    f"升级为 {new_priority}"
                )

                return db.query(WorkOrder).filter(
                    WorkOrder.id == work_order_id
                ).first()
            else:
                logger.info(
                    f"工单 {work_order.order_no} 已是最高优先级 {work_order.priority}"
                )
                return work_order

    # ============== 批量装置需求汇总 ==============

    def generate_device_summary(
        self,
        device_id: str,
        period_start: datetime = None,
        period_end: datetime = None,
        period: str = 'monthly',
        tenant_id: int = None,
        operator_id: str = None,
        operator_name: str = None,
    ) -> Optional[SparePartDemandSummary]:
        """
        生成装置级备件需求汇总报表

        Args:
            device_id: 装置ID
            period_start: 统计周期开始
            period_end: 统计周期结束
            period: 汇总周期 weekly/monthly/quarterly/custom
            tenant_id: 租户ID
            operator_id: 操作人ID
            operator_name: 操作人姓名

        Returns:
            SparePartDemandSummary: 汇总报表
        """
        now = datetime.now()
        if period_end is None:
            period_end = now
        if period_start is None:
            if period == 'weekly':
                period_start = now - timedelta(days=7)
            elif period == 'quarterly':
                period_start = now - timedelta(days=90)
            else:
                period_start = now - timedelta(days=30)

        device_name = None
        try:
            with get_db() as db:
                if db and device_id.isdigit():
                    device_node = db.query(OrganizationNode).filter(
                        OrganizationNode.id == int(device_id)
                    ).first()
                    if device_node:
                        device_name = device_node.node_name
        except Exception as e:
            logger.warning(f"获取装置名称失败: {e}")

        with get_db() as db:
            if db is None:
                return None

            demands_query = db.query(SparePartDemand).filter(
                SparePartDemand.device_id == device_id,
                SparePartDemand.create_time >= period_start,
                SparePartDemand.create_time <= period_end,
                SparePartDemand.status.in_(['pending', 'approved']),
            )
            if tenant_id:
                demands_query = demands_query.filter(
                    SparePartDemand.tenant_id == tenant_id
                )

            demands = demands_query.all()

            if not demands:
                logger.info(
                    f"装置 {device_id} 在指定周期内无备件需求"
                )
                return None

            total_demand_count = len(demands)
            total_quantity = sum(d.required_quantity for d in demands)
            urgent_count = sum(1 for d in demands if d.urgency == 'urgent')
            critical_count = sum(1 for d in demands if d.urgency == 'critical')
            out_of_stock_count = sum(
                1 for d in demands if d.stock_status == 'out_of_stock'
            )
            partial_stock_count = sum(
                1 for d in demands if d.stock_status == 'partial'
            )
            in_stock_count = sum(
                1 for d in demands if d.stock_status == 'in_stock'
            )

            affected_nodes = set()
            demand_details = []
            stock_analysis_items = {}
            total_value = 0.0

            for d in demands:
                node_key = f"{d.node_type}:{d.node_id}"
                affected_nodes.add(node_key)

                detail = {
                    'demand_id': d.id,
                    'demand_no': d.demand_no,
                    'node_type': d.node_type,
                    'node_id': d.node_id,
                    'bolt_model': d.bolt_model,
                    'sku_code': d.sku_code,
                    'sku_name': d.sku_name,
                    'required_quantity': d.required_quantity,
                    'urgency': d.urgency,
                    'priority': d.priority,
                    'rul_days': d.rul_days,
                    'estimated_failure_date': d.estimated_failure_date.isoformat() if d.estimated_failure_date else None,
                    'stock_status': d.stock_status,
                    'available_quantity': d.available_quantity,
                    'shortage_quantity': d.shortage_quantity,
                    'work_order_id': d.work_order_id,
                }
                demand_details.append(detail)

                if d.sku_code not in stock_analysis_items:
                    sku_mapping = db.query(BoltSkuMapping).filter(
                        BoltSkuMapping.sku_code == d.sku_code
                    ).first()
                    unit_price = sku_mapping.unit_price if sku_mapping else 0
                    stock_analysis_items[d.sku_code] = {
                        'sku_code': d.sku_code,
                        'sku_name': d.sku_name,
                        'total_required': 0,
                        'total_shortage': 0,
                        'unit_price': unit_price,
                        'stock_status': 'unknown',
                    }

                item = stock_analysis_items[d.sku_code]
                item['total_required'] += d.required_quantity
                item['total_shortage'] += d.shortage_quantity or 0
                item['stock_status'] = d.stock_status

                if item['unit_price']:
                    total_value += d.required_quantity * item['unit_price']

            recommendations = self._generate_purchase_recommendations(
                stock_analysis_items,
                period_start,
                period_end,
            )

            summary_no = self._generate_summary_no(db)

            summary = SparePartDemandSummary(
                summary_no=summary_no,
                device_id=device_id,
                device_name=device_name or device_id,
                summary_period=period,
                period_start=period_start,
                period_end=period_end,
                total_demand_count=total_demand_count,
                total_quantity=total_quantity,
                total_estimated_value=round(total_value, 2),
                urgent_count=urgent_count,
                critical_count=critical_count,
                out_of_stock_count=out_of_stock_count,
                partial_stock_count=partial_stock_count,
                in_stock_count=in_stock_count,
                affected_node_count=len(affected_nodes),
                demand_details=json.dumps(demand_details, ensure_ascii=False),
                stock_analysis=json.dumps(
                    list(stock_analysis_items.values()), ensure_ascii=False
                ),
                recommendations=json.dumps(recommendations, ensure_ascii=False),
                status='draft',
                generated_by=operator_id,
                generated_name=operator_name,
                tenant_id=tenant_id,
            )

            db.add(summary)
            db.flush()
            summary_id = summary.id
            db.commit()

            logger.info(
                f"装置备件需求汇总报表已生成: {summary_no}, "
                f"装置={device_name or device_id}, "
                f"需求项数={total_demand_count}, "
                f"总数量={total_quantity}"
            )

            return db.query(SparePartDemandSummary).filter(
                SparePartDemandSummary.id == summary_id
            ).first()

    def _generate_summary_no(self, db) -> str:
        """生成唯一汇总报表编号"""
        now = datetime.now()
        prefix = now.strftime('SPS%Y%m%d%H%M%S')
        for i in range(100):
            candidate = f"{prefix}{i:02d}"
            exists = db.query(SparePartDemandSummary).filter(
                SparePartDemandSummary.summary_no == candidate
            ).first()
            if not exists:
                return candidate
        raise RuntimeError("生成汇总报表编号失败")

    def _generate_purchase_recommendations(
        self,
        stock_analysis: Dict[str, Dict[str, Any]],
        period_start: datetime,
        period_end: datetime,
    ) -> List[Dict[str, Any]]:
        """
        生成采购建议

        Args:
            stock_analysis: 库存分析字典
            period_start: 统计周期开始
            period_end: 统计周期结束

        Returns:
            List[Dict]: 采购建议列表
        """
        recommendations = []
        period_days = max(1, (period_end - period_start).days)

        for sku_code, item in stock_analysis.items():
            if item['total_shortage'] <= 0:
                continue

            avg_daily_demand = item['total_required'] / period_days
            lead_time_days = 7

            try:
                with get_db() as db:
                    if db:
                        sku_mapping = db.query(BoltSkuMapping).filter(
                            BoltSkuMapping.sku_code == sku_code
                        ).first()
                        if sku_mapping:
                            lead_time_days = sku_mapping.lead_time_days or 7
            except Exception:
                pass

            safety_stock = math.ceil(avg_daily_demand * lead_time_days * 0.5)
            reorder_qty = max(
                item['total_shortage'],
                math.ceil(avg_daily_demand * lead_time_days) + safety_stock,
            )

            urgency = 'critical' if item['stock_status'] == 'out_of_stock' else 'normal'

            recommendations.append({
                'sku_code': sku_code,
                'sku_name': item['sku_name'],
                'recommended_qty': reorder_qty,
                'shortage_qty': item['total_shortage'],
                'avg_daily_demand': round(avg_daily_demand, 2),
                'lead_time_days': lead_time_days,
                'safety_stock': safety_stock,
                'estimated_cost': round(
                    reorder_qty * (item['unit_price'] or 0), 2
                ),
                'urgency': urgency,
                'unit_price': item['unit_price'],
            })

        return sorted(
            recommendations,
            key=lambda x: (x['urgency'] == 'critical', x['shortage_qty']),
            reverse=True,
        )

    # ============== 需求单管理 ==============

    def list_demands(
        self,
        device_id: str = None,
        sku_code: str = None,
        urgency: str = None,
        stock_status: str = None,
        status: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        tenant_id: int = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SparePartDemand]:
        """
        查询备件需求列表

        Args:
            device_id: 装置ID
            sku_code: SKU编码
            urgency: 紧急程度
            stock_status: 库存状态
            status: 需求单状态
            start_date: 开始日期
            end_date: 结束日期
            tenant_id: 租户ID
            limit: 分页限制
            offset: 分页偏移

        Returns:
            List[SparePartDemand]: 需求列表
        """
        with get_db() as db:
            if db is None:
                return []

            query = db.query(SparePartDemand)

            if device_id:
                query = query.filter(SparePartDemand.device_id == device_id)
            if sku_code:
                query = query.filter(SparePartDemand.sku_code == sku_code)
            if urgency:
                query = query.filter(SparePartDemand.urgency == urgency)
            if stock_status:
                query = query.filter(SparePartDemand.stock_status == stock_status)
            if status:
                query = query.filter(SparePartDemand.status == status)
            if start_date:
                query = query.filter(SparePartDemand.create_time >= start_date)
            if end_date:
                query = query.filter(SparePartDemand.create_time <= end_date)
            if tenant_id:
                query = query.filter(SparePartDemand.tenant_id == tenant_id)

            return query.order_by(
                SparePartDemand.priority.asc(),
                SparePartDemand.create_time.desc(),
            ).offset(offset).limit(limit).all()

    def approve_demand(
        self,
        demand_id: int,
        approver_id: str,
        approver_name: str,
        remarks: str = None,
    ) -> Optional[SparePartDemand]:
        """
        审批备件需求

        Args:
            demand_id: 需求单ID
            approver_id: 审批人ID
            approver_name: 审批人姓名
            remarks: 审批备注

        Returns:
            SparePartDemand: 更新后的需求单
        """
        with get_db() as db:
            if db is None:
                return None

            demand = db.query(SparePartDemand).filter(
                SparePartDemand.id == demand_id
            ).first()

            if not demand:
                logger.warning(f"需求单不存在: {demand_id}")
                return None

            demand.status = 'approved'
            demand.approved_by = approver_id
            demand.approved_name = approver_name
            demand.approved_time = datetime.now()
            if remarks:
                demand.remarks = remarks

            db.commit()
            logger.info(
                f"需求单 {demand.demand_no} 已通过审批"
            )

            return db.query(SparePartDemand).filter(
                SparePartDemand.id == demand_id
            ).first()

    def fulfill_demand(
        self,
        demand_id: int,
        operator_id: str = None,
        operator_name: str = None,
    ) -> Optional[SparePartDemand]:
        """
        完成备件需求（出库）

        Args:
            demand_id: 需求单ID
            operator_id: 操作人ID
            operator_name: 操作人姓名

        Returns:
            SparePartDemand: 更新后的需求单
        """
        with get_db() as db:
            if db is None:
                return None

            demand = db.query(SparePartDemand).filter(
                SparePartDemand.id == demand_id
            ).first()

            if not demand:
                logger.warning(f"需求单不存在: {demand_id}")
                return None

            inventory = db.query(SparePartInventory).filter(
                SparePartInventory.sku_code == demand.sku_code,
                SparePartInventory.warehouse_code == self.default_warehouse,
            ).first()

            if inventory and inventory.quantity_available >= demand.required_quantity:
                inventory.quantity_on_hand -= demand.required_quantity
                inventory.quantity_available -= demand.required_quantity
                inventory.last_issue_date = datetime.now()
                inventory.total_value = (
                    inventory.quantity_on_hand * (inventory.unit_price or 0)
                )

            demand.status = 'fulfilled'
            demand.fulfilled_time = datetime.now()

            db.commit()
            logger.info(
                f"需求单 {demand.demand_no} 已完成，出库 {demand.required_quantity} 个 {demand.sku_code}"
            )

            return db.query(SparePartDemand).filter(
                SparePartDemand.id == demand_id
            ).first()

    # ============== 批量RUL扫描 ==============

    def scan_rul_and_generate_demands(
        self,
        rul_threshold_days: float = None,
        tenant_id: int = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        扫描RUL预测结果，批量生成备件需求

        Args:
            rul_threshold_days: RUL阈值（天），默认使用配置值
            tenant_id: 租户ID
            limit: 最大处理数量

        Returns:
            Dict: 处理结果统计
        """
        threshold = rul_threshold_days or self.default_rul_threshold

        with get_db() as db:
            if db is None:
                return {'success': False, 'error': '数据库不可用'}

            rul_predictions = db.query(RULPrediction).filter(
                RULPrediction.rul_days <= threshold,
            ).order_by(
                RULPrediction.rul_days.asc()
            ).limit(limit).all()

            results = {
                'total_scanned': len(rul_predictions),
                'demands_created': 0,
                'demands_existed': 0,
                'failed': 0,
                'work_orders_created': 0,
                'priorities_upgraded': 0,
                'details': [],
            }

            for rul_pred in rul_predictions:
                try:
                    bolt_model = self._infer_bolt_model(rul_pred)
                    if not bolt_model:
                        results['failed'] += 1
                        results['details'].append({
                            'node_id': rul_pred.node_id,
                            'error': '无法推断螺栓型号',
                        })
                        continue

                    demand = self.generate_demand_from_rul(
                        rul_pred,
                        bolt_model,
                        tenant_id=tenant_id,
                    )

                    if demand:
                        if demand.create_time == datetime.now().replace(
                            microsecond=0
                        ):
                            results['demands_created'] += 1
                        else:
                            results['demands_existed'] += 1

                        if demand.work_order_id:
                            results['work_orders_created'] += 1
                        if demand.work_order_priority_upgraded:
                            results['priorities_upgraded'] += 1

                        results['details'].append({
                            'node_id': rul_pred.node_id,
                            'rul_days': rul_pred.rul_days,
                            'demand_no': demand.demand_no,
                            'status': 'created' if demand.create_time == datetime.now().replace(microsecond=0) else 'existed',
                        })
                    else:
                        results['failed'] += 1
                        results['details'].append({
                            'node_id': rul_pred.node_id,
                            'error': '创建需求单失败',
                        })

                except Exception as e:
                    logger.error(f"处理RUL {rul_pred.id} 失败: {e}")
                    results['failed'] += 1
                    results['details'].append({
                        'node_id': rul_pred.node_id,
                        'error': str(e),
                    })

            logger.info(
                f"RUL扫描完成: 扫描{results['total_scanned']}条, "
                f"新建需求{results['demands_created']}条, "
                f"已有需求{results['demands_existed']}条, "
                f"失败{results['failed']}条"
            )

            return results

    def _infer_bolt_model(self, rul_pred: RULPrediction) -> Optional[str]:
        """
        从RUL预测记录推断螺栓型号

        Args:
            rul_pred: RUL预测对象

        Returns:
            str: 螺栓型号，推断失败返回None
        """
        try:
            with get_db() as db:
                if db is None:
                    return None

                if rul_pred.node_type == 'bolt':
                    bolt_data = db.query(BoltSkuMapping).filter(
                        BoltSkuMapping.bolt_model.like(f'%{rul_pred.node_id}%'),
                        BoltSkuMapping.is_active == True,
                    ).first()
                    if bolt_data:
                        return bolt_data.bolt_model

                default_model = config.get(
                    f'spare_parts.default_bolt_model.{rul_pred.node_id}',
                    None
                )
                if default_model:
                    return default_model

                return config.get('spare_parts.default_bolt_model', 'M24-10.9')

        except Exception as e:
            logger.warning(f"推断螺栓型号失败: {e}")
            return config.get('spare_parts.default_bolt_model', 'M24-10.9')
