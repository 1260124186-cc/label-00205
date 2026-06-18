"""
风险传播分析服务

整合装置关联图构建、风险传播计算、热力矩阵生成、传播路径追溯等功能，
提供统一的服务接口供API层调用。
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from loguru import logger

from app.models.risk_propagation import (
    DeviceAssociationGraph,
    RiskPropagator,
    AssociationWeightConfig,
    RiskUpregulationResult,
    RiskHeatmapMatrix,
    PropagationPath,
)
from app.models.risk_model import RiskLevel


class RiskPropagationService:
    """
    风险传播分析服务

    提供跨装置风险传播与聚合分析的核心服务能力。
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_components()
        return cls._instance

    def _init_components(self):
        """初始化组件"""
        self.weight_config = AssociationWeightConfig()
        self.association_graph = DeviceAssociationGraph(weight_config=self.weight_config)
        self.propagator = RiskPropagator(association_graph=self.association_graph)

        self._last_update_time: Optional[datetime] = None
        self._update_count: int = 0

        logger.info("风险传播分析服务初始化完成")

    def update_association_graph(
        self,
        devices: List[Dict[str, Any]],
        co_fault_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        更新装置关联图

        Args:
            devices: 装置列表，每个装置包含 id、name、pipeline_id、vibration_source、
                    shifts、location 等信息
            co_fault_history: 共故障历史记录，每个记录包含 device_ids 和 timestamp

        Returns:
            更新结果统计
        """
        for device in devices:
            device_id = str(device.get('id', device.get('device_id', '')))
            if not device_id:
                continue

            device_info = {
                'name': device.get('name', device_id),
                'pipeline_id': device.get('pipeline_id'),
                'vibration_source': device.get('vibration_source'),
                'shifts': device.get('shifts', []),
                'latitude': device.get('latitude'),
                'longitude': device.get('longitude'),
                'x': device.get('x'),
                'y': device.get('y'),
                'extra': device.get('extra_info', {}),
            }
            self.association_graph.add_device(device_id, device_info)

        if co_fault_history:
            for record in co_fault_history:
                device_ids = record.get('device_ids', [])
                timestamp = record.get('timestamp')
                if device_ids:
                    self.association_graph.record_co_fault(
                        [str(d) for d in device_ids],
                        timestamp
                    )

        edge_count = self.association_graph.update_associations()

        self._last_update_time = datetime.now()
        self._update_count += 1

        result = {
            'device_count': len(self.association_graph.devices),
            'edge_count': edge_count,
            'update_count': self._update_count,
            'last_update_time': self._last_update_time.isoformat(),
            'weight_config': self.weight_config.__dict__,
        }

        logger.info(
            f"装置关联图更新完成: 装置数={result['device_count']}, "
            f"边数={result['edge_count']}, 更新次数={result['update_count']}"
        )

        return result

    def calculate_risk_propagation(
        self,
        source_device_id: str,
        source_flange_id: str,
        current_risk_scores: Dict[str, float],
        source_risk_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        计算风险传播

        当源装置某法兰发生紧急预警时，评估关联装置的螺栓风险上调系数。

        Args:
            source_device_id: 源装置ID
            source_flange_id: 源法兰ID
            current_risk_scores: 当前各装置风险评分字典 {device_id: risk_score}
            source_risk_score: 源装置风险评分，如不提供则从 current_risk_scores 获取

        Returns:
            风险传播结果，包含各关联装置的风险上调系数
        """
        source_device_id = str(source_device_id)
        source_flange_id = str(source_flange_id)

        if source_risk_score is None:
            source_risk_score = current_risk_scores.get(source_device_id, 3.0)

        propagation_results = self.propagator.calculate_risk_propagation(
            source_device_id=source_device_id,
            source_flange_id=source_flange_id,
            current_risk_scores=current_risk_scores,
            source_risk_score=source_risk_score,
        )

        summary = self.propagator.get_propagation_summary(
            source_device_id=source_device_id,
            current_risk_scores=current_risk_scores,
        )

        result = {
            'source_device_id': source_device_id,
            'source_flange_id': source_flange_id,
            'source_risk_score': source_risk_score,
            'propagation_time': datetime.now().isoformat(),
            'results': {
                device_id: result.to_dict()
                for device_id, result in propagation_results.items()
            },
            'summary': summary,
        }

        logger.info(
            f"风险传播计算完成: 源装置={source_device_id}, "
            f"影响装置数={summary.get('affected_device_count', 0)}"
        )

        return result

    def get_risk_heatmap_matrix(
        self,
        device_ids: Optional[List[str]] = None,
        risk_scores: Optional[Dict[str, float]] = None,
        highlight_source: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取装置级风险热力矩阵

        Args:
            device_ids: 装置ID列表，如不提供则使用所有装置
            risk_scores: 风险评分字典
            highlight_source: 高亮的源装置ID

        Returns:
            风险热力矩阵数据，可直接用于大屏展示
        """
        if device_ids is None:
            device_ids = list(self.association_graph.devices.keys())

        if risk_scores is None:
            risk_scores = {
                device_id: 5.0
                for device_id in device_ids
            }

        heatmap = self.propagator.build_risk_heatmap_matrix(
            device_ids=device_ids,
            risk_scores=risk_scores,
            highlight_source=highlight_source,
        )

        return heatmap.to_dict()

    def get_propagation_paths(
        self,
        source_device_id: str,
        target_device_id: Optional[str] = None,
        top_k: int = 10,
        max_depth: Optional[int] = None,
        current_risk_scores: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取传播路径

        查找从源装置出发的高权重传播路径，用于大屏传播路径高亮展示。

        Args:
            source_device_id: 源装置ID
            target_device_id: 目标装置ID，如不提供则返回所有高权重路径
            top_k: 返回前K条路径
            max_depth: 最大传播深度
            current_risk_scores: 当前风险评分

        Returns:
            传播路径列表
        """
        source_device_id = str(source_device_id)
        if target_device_id:
            target_device_id = str(target_device_id)

        paths = self.propagator.find_propagation_paths(
            source_device_id=source_device_id,
            target_device_id=target_device_id,
            top_k=top_k,
            max_depth=max_depth,
            current_risk_scores=current_risk_scores,
        )

        result = [path.to_dict() for path in paths]

        logger.info(
            f"传播路径查询完成: 源装置={source_device_id}, "
            f"目标装置={target_device_id or 'ALL'}, 路径数={len(result)}"
        )

        return result

    def get_association_graph_data(self) -> Dict[str, Any]:
        """
        获取关联图数据（用于图可视化）

        Returns:
            关联图的 nodes 和 edges 数据
        """
        nodes = []
        for device_id, device_info in self.association_graph.devices.items():
            nodes.append({
                'id': device_id,
                'name': device_info.get('name', device_id),
                'data': device_info,
            })

        edges = []
        seen = set()
        for dev_a, targets in self.association_graph.associations.items():
            for dev_b, association in targets.items():
                edge_key = tuple(sorted([dev_a, dev_b]))
                if edge_key in seen:
                    continue
                seen.add(edge_key)
                edges.append({
                    'source': dev_a,
                    'target': dev_b,
                    'weight': association.composite_weight,
                    'association_types': association.association_types,
                    'weights': {
                        'same_pipeline': association.same_pipeline_weight,
                        'same_vibration_source': association.same_vibration_source_weight,
                        'same_shift': association.same_shift_weight,
                    'co_fault': association.co_fault_weight,
                    'physical': association.physical_weight,
                },
            })

        result = {
            'nodes': nodes,
            'edges': edges,
            'node_count': len(nodes),
            'edge_count': len(edges),
            'last_update_time': self._last_update_time.isoformat() if self._last_update_time else None,
            'weight_config': self.weight_config.__dict__,
        }

        return result

    def get_device_associations(
        self,
        device_id: str,
        min_weight: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取指定装置的关联装置列表

        Args:
            device_id: 装置ID
            min_weight: 最小关联权重过滤

        Returns:
            关联装置列表
        """
        device_id = str(device_id)
        associations = self.association_graph.get_connected_devices(
            device_id=device_id,
            min_weight=min_weight,
        )

        result = []
        for connected_device_id, association in associations:
            result.append({
                'device_id': connected_device_id,
                'device_name': self.association_graph.devices.get(
                    connected_device_id, {}
                ).get('name', connected_device_id),
                'composite_weight': association.composite_weight,
                'association_types': association.association_types,
                'weights': {
                    'same_pipeline': association.same_pipeline_weight,
                    'same_vibration_source': association.same_vibration_source_weight,
                    'same_shift': association.same_shift_weight,
                    'co_fault': association.co_fault_weight,
                    'physical': association.physical_weight,
                },
            })

        return result

    def record_co_fault_event(
        self,
        device_ids: List[str],
        timestamp: Optional[str] = None,
    ) -> None:
        """
        记录共故障事件

        当多个装置同时发生故障时，调用此方法更新共故障关联权重。

        Args:
            device_ids: 同时发生故障的装置ID列表
            timestamp: 故障时间戳
        """
        device_ids = [str(d) for d in device_ids]
        self.association_graph.record_co_fault(device_ids, timestamp)
        self.association_graph.update_associations()

        logger.info(
            f"共故障事件已记录: 装置数={len(device_ids)}, "
            f"装置列表={device_ids}"
        )

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取服务统计信息

        Returns:
            统计信息字典
        """
        return {
            'device_count': len(self.association_graph.devices),
            'edge_count': len(self.association_graph.associations),
            'update_count': self._update_count,
            'last_update_time': self._last_update_time.isoformat() if self._last_update_time else None,
            'weight_config': self.weight_config.__dict__,
        }
