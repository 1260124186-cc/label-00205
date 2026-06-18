"""
跨装置风险传播与聚合分析模型

基于组织树与历史共现故障，构建「装置关联图」：
- 同管线 (same_pipeline)
- 同振动源 (same_vibration_source)
- 同班次 (same_shift)
- 历史共故障 (co_fault)
- 物理邻接 (physical)

当装置A某法兰紧急预警时，评估关联装置B的螺栓风险上调系数。

功能:
1. 装置关联图构建与更新
2. 风险传播算法（带衰减的扩散模型）
3. 风险上调系数计算
4. 装置级风险热力矩阵生成
5. 传播路径高亮与追溯
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
from datetime import datetime
from collections import defaultdict, deque

from app.utils.config import config


class AssociationType(str, Enum):
    """关联类型枚举"""
    SAME_PIPELINE = "same_pipeline"
    SAME_VIBRATION_SOURCE = "same_vibration_source"
    SAME_SHIFT = "same_shift"
    CO_FAULT = "co_fault"
    PHYSICAL = "physical"
    COMPOSITE = "composite"


@dataclass
class AssociationWeightConfig:
    """关联权重配置"""
    same_pipeline: float = 0.30
    same_vibration_source: float = 0.25
    same_shift: float = 0.15
    co_fault: float = 0.20
    physical: float = 0.10

    def __post_init__(self):
        """初始化后自动归一化权重"""
        if not self.validate():
            self.normalize()

    def validate(self) -> bool:
        """验证权重总和为1.0"""
        total = (
            self.same_pipeline +
            self.same_vibration_source +
            self.same_shift +
            self.co_fault +
            self.physical
        )
        return abs(total - 1.0) < 1e-6

    def normalize(self) -> None:
        """归一化权重"""
        total = (
            self.same_pipeline +
            self.same_vibration_source +
            self.same_shift +
            self.co_fault +
            self.physical
        )
        if total > 0:
            self.same_pipeline /= total
            self.same_vibration_source /= total
            self.same_shift /= total
            self.co_fault /= total
            self.physical /= total


@dataclass
class DeviceAssociation:
    """装置关联关系"""
    source_device_id: str
    target_device_id: str
    composite_weight: float
    same_pipeline_weight: float = 0.0
    same_vibration_weight: float = 0.0
    same_shift_weight: float = 0.0
    co_fault_weight: float = 0.0
    physical_weight: float = 0.0
    co_fault_count: int = 0
    association_types: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def same_vibration_source_weight(self) -> float:
        """same_vibration_weight 的别名，保持API一致性"""
        return self.same_vibration_weight

    @property
    def total_association_weight(self) -> float:
        """总关联权重（即综合权重）"""
        return self.composite_weight

    def to_dict(self) -> Dict[str, Any]:
        return {
            'source_device_id': self.source_device_id,
            'target_device_id': self.target_device_id,
            'composite_weight': round(self.composite_weight, 4),
            'same_pipeline_weight': round(self.same_pipeline_weight, 4),
            'same_vibration_weight': round(self.same_vibration_weight, 4),
            'same_vibration_source_weight': round(self.same_vibration_weight, 4),
            'total_association_weight': round(self.composite_weight, 4),
            'same_shift_weight': round(self.same_shift_weight, 4),
            'co_fault_weight': round(self.co_fault_weight, 4),
            'physical_weight': round(self.physical_weight, 4),
            'co_fault_count': self.co_fault_count,
            'association_types': self.association_types,
            'metadata': self.metadata,
        }


@dataclass
class RiskUpregulationResult:
    """风险上调系数结果"""
    device_id: str
    device_name: str
    original_risk_score: float
    original_risk_level: str
    adjusted_risk_score: float
    adjusted_risk_level: str
    upregulation_coefficient: float
    propagation_path: List[str]
    propagation_depth: int
    contributing_factors: List[Dict[str, Any]]
    confidence: float
    total_association_weight: float = 0.0
    association_weights: Optional[Dict[str, float]] = None

    def __post_init__(self):
        """初始化后计算风险等级是否升级"""
        if self.association_weights is None:
            self.association_weights = {}

    @property
    def risk_level_upgraded(self) -> bool:
        """风险等级是否升级"""
        from app.models.risk_model import RiskLevel

        def get_level_index(level: str) -> int:
            level_map = {
                '高': 0,
                '中': 1,
                '低': 2,
                'high': 0,
                'medium': 1,
                'low': 2,
            }
            return level_map.get(level, 99)

        original_idx = get_level_index(self.original_risk_level)
        adjusted_idx = get_level_index(self.adjusted_risk_level)
        return adjusted_idx < original_idx

    def to_dict(self) -> Dict[str, Any]:
        return {
            'device_id': self.device_id,
            'device_name': self.device_name,
            'original_risk_score': round(self.original_risk_score, 2),
            'original_risk_level': self.original_risk_level,
            'adjusted_risk_score': round(self.adjusted_risk_score, 2),
            'adjusted_risk_level': self.adjusted_risk_level,
            'upregulation_coefficient': round(self.upregulation_coefficient, 4),
            'propagation_path': self.propagation_path,
            'propagation_depth': self.propagation_depth,
            'contributing_factors': self.contributing_factors,
            'confidence': round(self.confidence, 4),
            'total_association_weight': round(self.total_association_weight, 4),
            'association_weights': {
                k: round(v, 4) for k, v in self.association_weights.items()
            },
            'risk_level_upgraded': self.risk_level_upgraded,
        }


@dataclass
class RiskHeatmapMatrix:
    """装置级风险热力矩阵"""
    device_ids: List[str]
    device_names: List[str]
    risk_matrix: np.ndarray
    propagation_matrix: np.ndarray
    timestamp: str
    highlight_source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后计算属性"""
        self.highlight_mask = self._build_highlight_mask()
        self.cells = self._build_cells()
        self.min_risk_value = float(np.min(self.risk_matrix))
        self.max_risk_value = float(np.max(self.risk_matrix))

    @property
    def matrix(self) -> np.ndarray:
        """risk_matrix 的别名"""
        return self.risk_matrix

    @property
    def association_matrix(self) -> np.ndarray:
        """propagation_matrix 的别名"""
        return self.propagation_matrix

    def _build_highlight_mask(self) -> np.ndarray:
        """构建高亮掩码矩阵"""
        n = len(self.device_ids)
        mask = np.eye(n, dtype=bool)

        if self.highlight_source and self.highlight_source in self.device_ids:
            source_idx = self.device_ids.index(self.highlight_source)
            mask[source_idx, :] = True
            mask[:, source_idx] = True

        return mask

    def _build_cells(self) -> List[Dict[str, Any]]:
        """构建单元格列表"""
        cells = []
        n = len(self.device_ids)

        for i in range(n):
            for j in range(n):
                cells.append({
                    'row': i,
                    'col': j,
                    'row_device_id': self.device_ids[i],
                    'col_device_id': self.device_ids[j],
                    'row_device_name': self.device_names[i],
                    'col_device_name': self.device_names[j],
                    'risk_value': float(self.risk_matrix[i, j]),
                    'association_value': float(self.propagation_matrix[i, j]),
                    'is_highlighted': bool(self.highlight_mask[i, j]),
                    'is_diagonal': i == j,
                })

        return cells

    def to_dict(self) -> Dict[str, Any]:
        return {
            'device_ids': self.device_ids,
            'device_names': self.device_names,
            'risk_matrix': self.risk_matrix.tolist(),
            'propagation_matrix': self.propagation_matrix.tolist(),
            'matrix': self.risk_matrix.tolist(),
            'association_matrix': self.propagation_matrix.tolist(),
            'timestamp': self.timestamp,
            'highlight_source': self.highlight_source,
            'highlight_mask': self.highlight_mask.tolist(),
            'cells': self.cells,
            'min_risk_value': round(self.min_risk_value, 4),
            'max_risk_value': round(self.max_risk_value, 4),
            'metadata': self.metadata,
        }


@dataclass
class PropagationPath:
    """传播路径"""
    path: List[str]
    path_names: List[str]
    total_weight: float
    avg_weight: float
    depth: int
    risk_increase: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'path': self.path,
            'path_names': self.path_names,
            'total_weight': round(self.total_weight, 4),
            'avg_weight': round(self.avg_weight, 4),
            'depth': self.depth,
            'risk_increase': round(self.risk_increase, 4),
        }


class DeviceAssociationGraph:
    """
    装置关联图

    构建和管理装置间的关联关系，支持多种关联类型的权重计算。
    """

    def __init__(self, weight_config: Optional[AssociationWeightConfig] = None):
        """
        初始化装置关联图

        Args:
            weight_config: 关联权重配置
        """
        self.weight_config = weight_config or AssociationWeightConfig()

        if not self.weight_config.validate():
            logger.warning("关联权重总和不为1.0，将自动归一化")
            self._normalize_weights()

        self._adjacency: Dict[str, Dict[str, DeviceAssociation]] = defaultdict(dict)
        self._device_info: Dict[str, Dict[str, Any]] = {}
        self._pipeline_map: Dict[str, Set[str]] = defaultdict(set)
        self._vibration_map: Dict[str, Set[str]] = defaultdict(set)
        self._shift_map: Dict[str, Set[str]] = defaultdict(set)
        self._co_fault_history: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._max_co_fault_count: int = 1

        rp_config = config.get('risk_propagation', {})
        self.max_propagation_depth = rp_config.get('max_propagation_depth', 3)
        self.propagation_decay_factor = rp_config.get('propagation_decay_factor', 0.5)
        self.min_association_threshold = rp_config.get('min_association_threshold', 0.05)

        logger.info(
            f"装置关联图初始化完成: "
            f"同管线权重={self.weight_config.same_pipeline}, "
            f"同振动源权重={self.weight_config.same_vibration_source}, "
            f"同班次权重={self.weight_config.same_shift}"
        )

    @property
    def devices(self) -> Dict[str, Dict[str, Any]]:
        """返回所有装置信息（别名）"""
        return self._device_info

    @property
    def device_count(self) -> int:
        """装置数量"""
        return len(self._device_info)

    @property
    def associations(self) -> Dict[str, Dict[str, DeviceAssociation]]:
        """返回所有关联关系"""
        return self._adjacency

    @property
    def association_count(self) -> int:
        """关联边数量"""
        count = 0
        for dev_a, targets in self._adjacency.items():
            for dev_b, assoc in targets.items():
                if dev_a < dev_b:
                    count += 1
        return count

    def _normalize_weights(self) -> None:
        """归一化权重"""
        self.weight_config.normalize()

    def add_device(self, device_id: str, device_info: Dict[str, Any]) -> None:
        """
        添加装置节点

        Args:
            device_id: 装置ID
            device_info: 装置信息，包含 pipeline_id, vibration_source, shifts, position 等
        """
        self._device_info[device_id] = device_info

        pipeline_id = device_info.get('pipeline_id')
        if pipeline_id:
            self._pipeline_map[pipeline_id].add(device_id)

        vibration_source = device_info.get('vibration_source')
        if vibration_source:
            self._vibration_map[vibration_source].add(device_id)

        shifts = device_info.get('shifts', [])
        for shift in shifts:
            self._shift_map[shift].add(device_id)

        logger.debug(f"已添加装置: {device_id}")

    def update_associations(self) -> int:
        """
        更新所有装置间的关联关系

        Returns:
            int: 更新的关联关系数量
        """
        device_ids = list(self._device_info.keys())
        updated_count = 0

        for i, dev_a in enumerate(device_ids):
            for dev_b in device_ids[i + 1:]:
                association = self._calculate_association(dev_a, dev_b)
                if association.composite_weight >= self.min_association_threshold:
                    self._adjacency[dev_a][dev_b] = association
                    reverse_association = self._reverse_association(association)
                    self._adjacency[dev_b][dev_a] = reverse_association
                    updated_count += 1

        logger.info(f"装置关联图更新完成，共 {updated_count} 条关联关系")
        return updated_count

    def _calculate_association(
        self,
        dev_a: str,
        dev_b: str,
    ) -> DeviceAssociation:
        """
        计算两个装置间的关联关系

        Args:
            dev_a: 装置A ID
            dev_b: 装置B ID

        Returns:
            DeviceAssociation: 关联关系
        """
        info_a = self._device_info.get(dev_a, {})
        info_b = self._device_info.get(dev_b, {})

        association_types = []
        weights = {}

        same_pipeline_weight = self._calculate_same_pipeline_weight(info_a, info_b)
        weights['same_pipeline'] = same_pipeline_weight
        if same_pipeline_weight > 0:
            association_types.append(AssociationType.SAME_PIPELINE.value)

        same_vibration_weight = self._calculate_same_vibration_weight(info_a, info_b)
        weights['same_vibration'] = same_vibration_weight
        if same_vibration_weight > 0:
            association_types.append(AssociationType.SAME_VIBRATION_SOURCE.value)

        same_shift_weight = self._calculate_same_shift_weight(info_a, info_b)
        weights['same_shift'] = same_shift_weight
        if same_shift_weight > 0:
            association_types.append(AssociationType.SAME_SHIFT.value)

        co_fault_weight = self._calculate_co_fault_weight(dev_a, dev_b)
        weights['co_fault'] = co_fault_weight
        if co_fault_weight > 0:
            association_types.append(AssociationType.CO_FAULT.value)

        physical_weight = self._calculate_physical_weight(info_a, info_b)
        weights['physical'] = physical_weight
        if physical_weight > 0:
            association_types.append(AssociationType.PHYSICAL.value)

        composite_weight = (
            self.weight_config.same_pipeline * same_pipeline_weight +
            self.weight_config.same_vibration_source * same_vibration_weight +
            self.weight_config.same_shift * same_shift_weight +
            self.weight_config.co_fault * co_fault_weight +
            self.weight_config.physical * physical_weight
        )

        return DeviceAssociation(
            source_device_id=dev_a,
            target_device_id=dev_b,
            composite_weight=composite_weight,
            same_pipeline_weight=same_pipeline_weight,
            same_vibration_weight=same_vibration_weight,
            same_shift_weight=same_shift_weight,
            co_fault_weight=co_fault_weight,
            physical_weight=physical_weight,
            co_fault_count=self._co_fault_history.get(dev_a, {}).get(dev_b, 0),
            association_types=association_types,
            metadata={'weight_breakdown': weights},
        )

    def _calculate_same_pipeline_weight(
        self,
        info_a: Dict[str, Any],
        info_b: Dict[str, Any],
    ) -> float:
        """计算同管线权重"""
        pipeline_a = info_a.get('pipeline_id')
        pipeline_b = info_b.get('pipeline_id')

        if not pipeline_a or not pipeline_b:
            return 0.0

        if pipeline_a == pipeline_b:
            return 1.0

        return 0.0

    def _calculate_same_vibration_weight(
        self,
        info_a: Dict[str, Any],
        info_b: Dict[str, Any],
    ) -> float:
        """计算同振动源权重"""
        vib_a = info_a.get('vibration_source')
        vib_b = info_b.get('vibration_source')

        if not vib_a or not vib_b:
            return 0.0

        if isinstance(vib_a, list) or isinstance(vib_b, list):
            set_a = set(vib_a) if isinstance(vib_a, list) else {vib_a}
            set_b = set(vib_b) if isinstance(vib_b, list) else {vib_b}
            intersection = set_a & set_b
            union = set_a | set_b
            if not union:
                return 0.0
            return len(intersection) / len(union)

        if vib_a == vib_b:
            correlation = info_a.get('vibration_correlation', {})
            if isinstance(correlation, dict) and vib_b in correlation:
                return max(0.5, min(1.0, correlation[vib_b]))
            return 1.0

        return 0.0

    def _calculate_same_shift_weight(
        self,
        info_a: Dict[str, Any],
        info_b: Dict[str, Any],
    ) -> float:
        """计算同班次权重"""
        shifts_a = set(info_a.get('shifts', []))
        shifts_b = set(info_b.get('shifts', []))

        if not shifts_a or not shifts_b:
            return 0.0

        intersection = shifts_a & shifts_b
        union = shifts_a | shifts_b

        if not union:
            return 0.0

        jaccard = len(intersection) / len(union)
        return jaccard

    def _calculate_co_fault_weight(
        self,
        dev_a: str,
        dev_b: str,
    ) -> float:
        """计算历史共故障权重"""
        count = self._co_fault_history.get(dev_a, {}).get(dev_b, 0)
        if count == 0:
            return 0.0

        normalized = count / max(1, self._max_co_fault_count)
        return min(1.0, normalized)

    def _calculate_physical_weight(
        self,
        info_a: Dict[str, Any],
        info_b: Dict[str, Any],
    ) -> float:
        """计算物理邻接权重"""
        pos_a = info_a.get('position')
        pos_b = info_b.get('position')

        if not pos_a or not pos_b:
            lat_a = info_a.get('latitude')
            lon_a = info_a.get('longitude')
            lat_b = info_b.get('latitude')
            lon_b = info_b.get('longitude')

            if lat_a is not None and lon_a is not None and lat_b is not None and lon_b is not None:
                try:
                    dist_km = self._haversine_distance(lat_a, lon_a, lat_b, lon_b)
                    max_dist = 500.0
                    weight = max(0.0, 1.0 - dist_km / max_dist)
                    return weight
                except Exception:
                    pass

            parent_a = info_a.get('parent_id')
            parent_b = info_b.get('parent_id')
            if parent_a and parent_b and parent_a == parent_b:
                return 0.5
            return 0.0

        try:
            if 'x' in pos_a and 'x' in pos_b:
                dist = np.sqrt(
                    (pos_a.get('x', 0) - pos_b.get('x', 0)) ** 2 +
                    (pos_a.get('y', 0) - pos_b.get('y', 0)) ** 2 +
                    (pos_a.get('z', 0) - pos_b.get('z', 0)) ** 2
                )
                max_dist = 500.0
                weight = max(0.0, 1.0 - dist / max_dist)
                return weight
            elif 'longitude' in pos_a and 'longitude' in pos_b:
                dist_km = self._haversine_distance(
                    pos_a['latitude'], pos_a['longitude'],
                    pos_b['latitude'], pos_b['longitude']
                )
                max_dist = 500.0
                weight = max(0.0, 1.0 - dist_km / max_dist)
                return weight
            else:
                return 0.0
        except Exception:
            return 0.0

    def _haversine_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float,
    ) -> float:
        """计算球面距离（公里）"""
        R = 6371.0

        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        dlat = lat2_rad - lat1_rad
        dlon = np.radians(lon2 - lon1)

        a = (np.sin(dlat / 2) ** 2 +
             np.cos(lat1_rad) * np.cos(lat2_rad) *
             np.sin(dlon / 2) ** 2)
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

        return R * c

    def _reverse_association(self, assoc: DeviceAssociation) -> DeviceAssociation:
        """创建反向关联关系"""
        return DeviceAssociation(
            source_device_id=assoc.target_device_id,
            target_device_id=assoc.source_device_id,
            composite_weight=assoc.composite_weight,
            same_pipeline_weight=assoc.same_pipeline_weight,
            same_vibration_weight=assoc.same_vibration_weight,
            same_shift_weight=assoc.same_shift_weight,
            co_fault_weight=assoc.co_fault_weight,
            physical_weight=assoc.physical_weight,
            co_fault_count=assoc.co_fault_count,
            association_types=assoc.association_types,
            metadata=assoc.metadata,
        )

    def record_co_fault(
        self,
        device_ids: List[str],
        timestamp: Optional[str] = None,
    ) -> None:
        """
        记录共故障事件

        Args:
            device_ids: 同时发生故障的装置ID列表
            timestamp: 事件时间戳
        """
        for i, dev_a in enumerate(device_ids):
            for dev_b in device_ids[i + 1:]:
                self._co_fault_history[dev_a][dev_b] = (
                    self._co_fault_history[dev_a].get(dev_b, 0) + 1
                )
                self._co_fault_history[dev_b][dev_a] = (
                    self._co_fault_history[dev_b].get(dev_a, 0) + 1
                )
                count = self._co_fault_history[dev_a][dev_b]
                if count > self._max_co_fault_count:
                    self._max_co_fault_count = count

        logger.debug(f"记录共故障事件，涉及 {len(device_ids)} 个装置")

    def get_association(
        self,
        dev_a: str,
        dev_b: str,
    ) -> Optional[DeviceAssociation]:
        """获取两个装置间的关联关系"""
        return self._adjacency.get(dev_a, {}).get(dev_b)

    def get_connected_devices(
        self,
        device_id: str,
        min_weight: Optional[float] = None,
    ) -> List[Tuple[str, DeviceAssociation]]:
        """
        获取与指定装置关联的所有装置

        Args:
            device_id: 装置ID
            min_weight: 最小关联权重过滤

        Returns:
            List[Tuple[device_id, association]]
        """
        if min_weight is None:
            min_weight = self.min_association_threshold

        connections = []
        for target_id, assoc in self._adjacency.get(device_id, {}).items():
            if assoc.composite_weight >= min_weight:
                connections.append((target_id, assoc))

        connections.sort(key=lambda x: x[1].composite_weight, reverse=True)
        return connections

    def get_all_associations(self) -> List[DeviceAssociation]:
        """获取所有关联关系（去重）"""
        associations = []
        seen = set()

        for dev_a, targets in self._adjacency.items():
            for dev_b, assoc in targets.items():
                key = tuple(sorted([dev_a, dev_b]))
                if key not in seen:
                    seen.add(key)
                    associations.append(assoc)

        return associations

    def get_device_count(self) -> int:
        """获取装置数量"""
        return len(self._device_info)

    def get_association_count(self) -> int:
        """获取关联关系数量（去重后）"""
        return len(self.get_all_associations())


class RiskPropagator:
    """
    风险传播分析器

    基于装置关联图，实现风险传播和上调系数计算。
    """

    def __init__(self, association_graph: DeviceAssociationGraph):
        """
        初始化风险传播分析器

        Args:
            association_graph: 装置关联图
        """
        self.graph = association_graph

        rp_config = config.get('risk_propagation', {})
        self.max_propagation_depth = rp_config.get('max_propagation_depth', 3)
        self.propagation_decay = rp_config.get('propagation_decay_factor', 0.5)
        self.emergency_risk_threshold = rp_config.get('emergency_risk_threshold', 3.0)
        self.risk_increase_cap = rp_config.get('risk_increase_cap', 2.0)
        self.min_risk_increase = rp_config.get('min_risk_increase', 0.05)

        logger.info(
            f"风险传播分析器初始化完成: "
            f"最大传播深度={self.max_propagation_depth}, "
            f"传播衰减因子={self.propagation_decay}"
        )

    def calculate_risk_propagation(
        self,
        source_device_id: str,
        source_flange_id: str,
        current_risk_scores: Dict[str, float],
        source_risk_score: Optional[float] = None,
    ) -> Dict[str, RiskUpregulationResult]:
        """
        计算风险传播影响

        当装置A某法兰紧急预警时，评估关联装置B的螺栓风险上调系数。

        Args:
            source_device_id: 源装置ID（发生紧急预警的装置）
            source_flange_id: 源法兰ID（发生紧急预警的法兰）
            current_risk_scores: 当前各装置的风险评分 {device_id: risk_score}
            source_risk_score: 源装置的风险评分（如不提供则从 current_risk_scores 获取）

        Returns:
            Dict[device_id, RiskUpregulationResult]: 各关联装置的风险上调结果
        """
        if source_risk_score is None:
            source_risk_score = current_risk_scores.get(source_device_id, 5.0)

        if source_risk_score > self.emergency_risk_threshold:
            logger.warning(
                f"源装置 {source_device_id} 风险评分 {source_risk_score} "
                f"未达到紧急预警阈值 {self.emergency_risk_threshold}"
            )

        propagation_effects = self._propagate_risk(
            source_device_id,
            source_risk_score,
        )

        results = {}
        device_names = {
            dev_id: info.get('name', dev_id)
            for dev_id, info in self.graph._device_info.items()
        }

        for device_id, (path, depth, accumulated_weight) in propagation_effects.items():
            if device_id == source_device_id:
                continue

            original_score = current_risk_scores.get(device_id, 5.0)

            upregulation_coeff = self._calculate_upregulation_coefficient(
                source_risk_score,
                accumulated_weight,
                depth,
            )

            adjusted_score = original_score / upregulation_coeff
            adjusted_score = max(1.0, adjusted_score)

            original_level = self._risk_level(original_score)
            adjusted_level = self._risk_level(adjusted_score)

            contributing_factors = self._get_contributing_factors(
                source_device_id,
                device_id,
                path,
            )

            confidence = self._calculate_propagation_confidence(
                accumulated_weight,
                depth,
            )

            path_names = [device_names.get(pid, pid) for pid in path]

            assoc = self.graph.get_association(source_device_id, device_id)
            association_weights = {}
            total_association_weight = 0.0
            if assoc:
                association_weights = {
                    'same_pipeline': assoc.same_pipeline_weight,
                    'same_vibration': assoc.same_vibration_weight,
                    'same_shift': assoc.same_shift_weight,
                    'co_fault': assoc.co_fault_weight,
                    'physical': assoc.physical_weight,
                }
                total_association_weight = assoc.composite_weight

            results[device_id] = RiskUpregulationResult(
                device_id=device_id,
                device_name=device_names.get(device_id, device_id),
                original_risk_score=original_score,
                original_risk_level=original_level,
                adjusted_risk_score=adjusted_score,
                adjusted_risk_level=adjusted_level,
                upregulation_coefficient=upregulation_coeff,
                propagation_path=path_names,
                propagation_depth=depth,
                contributing_factors=contributing_factors,
                confidence=confidence,
                total_association_weight=total_association_weight,
                association_weights=association_weights,
            )

        logger.info(
            f"风险传播计算完成，源装置: {source_device_id}, "
            f"影响装置数: {len(results)}"
        )
        return results

    def _propagate_risk(
        self,
        source_device_id: str,
        source_risk_score: float,
    ) -> Dict[str, Tuple[List[str], int, float]]:
        """
        使用BFS进行风险传播

        Args:
            source_device_id: 源装置ID
            source_risk_score: 源风险评分

        Returns:
            Dict[device_id, (path, depth, accumulated_weight)]
        """
        results: Dict[str, Tuple[List[str], int, float]] = {}
        visited: Set[str] = set()
        queue: deque = deque()

        risk_severity = max(0.0, (10.0 - source_risk_score) / 10.0)

        queue.append((source_device_id, [source_device_id], 0, 1.0))
        visited.add(source_device_id)

        while queue:
            current_id, path, depth, current_weight = queue.popleft()

            if depth > 0:
                results[current_id] = (path, depth, current_weight)

            if depth >= self.max_propagation_depth:
                continue

            connections = self.graph.get_connected_devices(current_id)

            for neighbor_id, assoc in connections:
                if neighbor_id in visited:
                    continue

                decay = self.propagation_decay ** depth
                edge_contribution = assoc.composite_weight * risk_severity * decay
                new_weight = current_weight * (1 + edge_contribution)

                visited.add(neighbor_id)
                new_path = path + [neighbor_id]
                queue.append((neighbor_id, new_path, depth + 1, new_weight))

        return results

    def _calculate_upregulation_coefficient(
        self,
        source_risk_score: float,
        accumulated_weight: float,
        depth: int,
    ) -> float:
        """
        计算风险上调系数

        Args:
            source_risk_score: 源风险评分（越低风险越高）
            accumulated_weight: 累积传播权重
            depth: 传播深度

        Returns:
            float: 上调系数 (>= 1.0，表示风险需要乘以的倍数)
        """
        risk_factor = max(0.0, (self.emergency_risk_threshold - source_risk_score) / self.emergency_risk_threshold)
        depth_decay = self.propagation_decay ** max(0, depth - 1)

        base_coeff = 1.0 + (risk_factor * accumulated_weight * depth_decay * self.risk_increase_cap)

        coeff = max(self.min_risk_increase, min(1.0 + self.risk_increase_cap, base_coeff))

        return coeff

    def _get_contributing_factors(
        self,
        source_id: str,
        target_id: str,
        path: List[str],
    ) -> List[Dict[str, Any]]:
        """
        获取传播路径上的贡献因子

        Args:
            source_id: 源装置ID
            target_id: 目标装置ID
            path: 传播路径

        Returns:
            List of factor dicts
        """
        factors = []

        for i in range(len(path) - 1):
            from_id = path[i]
            to_id = path[i + 1]

            assoc = self.graph.get_association(from_id, to_id)
            if assoc:
                factors.append({
                    'from_device': from_id,
                    'to_device': to_id,
                    'association_types': assoc.association_types,
                    'composite_weight': round(assoc.composite_weight, 4),
                    'weight_breakdown': {
                        'same_pipeline': round(assoc.same_pipeline_weight, 4),
                        'same_vibration': round(assoc.same_vibration_weight, 4),
                        'same_shift': round(assoc.same_shift_weight, 4),
                        'co_fault': round(assoc.co_fault_weight, 4),
                        'physical': round(assoc.physical_weight, 4),
                    },
                })

        return factors

    def _calculate_propagation_confidence(
        self,
        accumulated_weight: float,
        depth: int,
    ) -> float:
        """
        计算传播置信度

        Args:
            accumulated_weight: 累积权重
            depth: 传播深度

        Returns:
            float: 置信度 (0-1)
        """
        weight_confidence = min(1.0, (accumulated_weight - 1.0) * 2)
        depth_penalty = self.propagation_decay ** max(0, depth - 1)

        confidence = weight_confidence * depth_penalty
        return float(np.clip(confidence, 0.0, 1.0))

    def _risk_level(self, score: float) -> str:
        """根据风险评分确定风险等级"""
        if score <= 3.0:
            return "高"
        elif score <= 7.0:
            return "中"
        else:
            return "低"

    def build_risk_heatmap_matrix(
        self,
        device_ids: List[str],
        risk_scores: Dict[str, float],
        highlight_source: Optional[str] = None,
    ) -> RiskHeatmapMatrix:
        """
        构建装置级风险热力矩阵

        Args:
            device_ids: 装置ID列表（用于确定矩阵顺序）
            risk_scores: 各装置的风险评分
            highlight_source: 高亮的源装置ID（用于传播矩阵）

        Returns:
            RiskHeatmapMatrix: 风险热力矩阵
        """
        n = len(device_ids)
        device_id_to_idx = {dev_id: i for i, dev_id in enumerate(device_ids)}

        risk_matrix = np.zeros((n, n))
        propagation_matrix = np.zeros((n, n))

        for i, dev_a in enumerate(device_ids):
            for j, dev_b in enumerate(device_ids):
                if i == j:
                    risk_matrix[i, j] = 0.0
                    propagation_matrix[i, j] = 0.0
                else:
                    assoc = self.graph.get_association(dev_a, dev_b)
                    if assoc:
                        risk_matrix[i, j] = (
                            risk_scores.get(dev_a, 5.0) *
                            risk_scores.get(dev_b, 5.0) / 10.0
                        )
                        propagation_matrix[i, j] = assoc.composite_weight
                    else:
                        risk_matrix[i, j] = 0.0
                        propagation_matrix[i, j] = 0.0

        if highlight_source and highlight_source in device_id_to_idx:
            source_idx = device_id_to_idx[highlight_source]
            propagation_effects = self._propagate_risk(
                highlight_source,
                risk_scores.get(highlight_source, 5.0),
            )

            for dev_id, (path, depth, weight) in propagation_effects.items():
                if dev_id in device_id_to_idx:
                    target_idx = device_id_to_idx[dev_id]
                    propagation_matrix[source_idx, target_idx] = max(
                        propagation_matrix[source_idx, target_idx],
                        min(1.0, weight - 1.0 + 0.5)
                    )

        device_names = [
            self.graph._device_info.get(dev_id, {}).get('name', dev_id)
            for dev_id in device_ids
        ]

        return RiskHeatmapMatrix(
            device_ids=device_ids,
            device_names=device_names,
            risk_matrix=risk_matrix,
            propagation_matrix=propagation_matrix,
            timestamp=datetime.now().isoformat(),
            highlight_source=highlight_source,
            metadata={
                'highlight_source': highlight_source,
                'matrix_size': n,
            },
        )

    def find_propagation_paths(
        self,
        source_device_id: str,
        target_device_id: Optional[str] = None,
        top_k: int = 10,
        max_depth: Optional[int] = None,
        current_risk_scores: Optional[Dict[str, float]] = None,
    ) -> List[PropagationPath]:
        """
        查找风险传播路径

        Args:
            source_device_id: 源装置ID
            target_device_id: 目标装置ID（None则返回所有可达路径）
            top_k: 返回前k条路径
            max_depth: 最大深度
            current_risk_scores: 当前风险评分（用于计算风险增量）

        Returns:
            List[PropagationPath]: 传播路径列表
        """
        if max_depth is None:
            max_depth = self.max_propagation_depth

        if current_risk_scores is None:
            current_risk_scores = {}

        all_paths: List[PropagationPath] = []
        visited: Set[str] = set()
        device_names = {
            dev_id: info.get('name', dev_id)
            for dev_id, info in self.graph._device_info.items()
        }

        def dfs(
            current_id: str,
            path: List[str],
            total_weight: float,
            depth: int,
        ):
            if depth > max_depth:
                return

            if current_id in visited:
                return

            visited.add(current_id)

            if len(path) > 1:
                if target_device_id is None or current_id == target_device_id:
                    source_risk = current_risk_scores.get(source_device_id, 5.0)
                    target_risk = current_risk_scores.get(current_id, 5.0)
                    risk_increase = (total_weight - 1.0) * max(0, (10 - source_risk) / 10)

                    all_paths.append(PropagationPath(
                        path=list(path),
                        path_names=[device_names.get(pid, pid) for pid in path],
                        total_weight=total_weight,
                        avg_weight=total_weight / (len(path) - 1),
                        depth=len(path) - 1,
                        risk_increase=risk_increase,
                    ))

                    if target_device_id is not None and current_id == target_device_id:
                        visited.remove(current_id)
                        return

            connections = self.graph.get_connected_devices(current_id)
            connections.sort(key=lambda x: x[1].composite_weight, reverse=True)

            for neighbor_id, assoc in connections[:10]:
                if neighbor_id not in visited:
                    path.append(neighbor_id)
                    new_weight = total_weight * (1 + assoc.composite_weight * self.propagation_decay ** depth)
                    dfs(neighbor_id, path, new_weight, depth + 1)
                    path.pop()

            visited.remove(current_id)

        source_risk = current_risk_scores.get(source_device_id, 5.0)
        dfs(source_device_id, [source_device_id], 1.0, 0)

        all_paths.sort(key=lambda p: p.risk_increase, reverse=True)

        return all_paths[:top_k]

    def get_propagation_summary(
        self,
        source_device_id: str,
        current_risk_scores: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        获取风险传播汇总信息

        Args:
            source_device_id: 源装置ID
            current_risk_scores: 当前风险评分

        Returns:
            Dict: 汇总信息
        """
        propagation_results = self.calculate_risk_propagation(
            source_device_id=source_device_id,
            source_flange_id="",
            current_risk_scores=current_risk_scores,
        )

        affected_high = 0
        affected_medium = 0
        affected_low = 0
        max_increase = 0.0
        total_increase = 0.0

        level_upgrades = []

        for result in propagation_results.values():
            if result.upregulation_coefficient > max_increase:
                max_increase = result.upregulation_coefficient
            total_increase += result.upregulation_coefficient

            if result.adjusted_risk_level == "高":
                affected_high += 1
            elif result.adjusted_risk_level == "中":
                affected_medium += 1
            else:
                affected_low += 1

            if result.original_risk_level != result.adjusted_risk_level:
                level_upgrades.append({
                    'device_id': result.device_id,
                    'device_name': result.device_name,
                    'from_level': result.original_risk_level,
                    'to_level': result.adjusted_risk_level,
                    'increase_coeff': round(result.upregulation_coefficient, 4),
                })

        sorted_results = sorted(
            propagation_results.values(),
            key=lambda x: x.upregulation_coefficient,
            reverse=True,
        )

        return {
            'source_device_id': source_device_id,
            'source_device_name': self.graph._device_info.get(source_device_id, {}).get('name', source_device_id),
            'total_affected_devices': len(propagation_results),
            'affected_device_count': len(propagation_results),
            'affected_by_level': {
                'high': affected_high,
                'medium': affected_medium,
                'low': affected_low,
            },
            'max_risk_increase': round(max_increase, 4),
            'avg_risk_increase': round(total_increase / max(1, len(propagation_results)), 4),
            'level_upgrades': level_upgrades,
            'level_upgraded_devices': level_upgrades,
            'top_affected_devices': [r.to_dict() for r in sorted_results[:10]],
            'timestamp': datetime.now().isoformat(),
        }
