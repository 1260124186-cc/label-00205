"""
传播图构建器

构建装置级风险传播图，包含节点和边的定义、边权重计算。

边权重来源：
1. 历史共故障权重（co_fault）：基于历史故障数据的共现频率
2. 物理邻接权重（physical）：基于组织结构/地理位置的相邻关系
3. Granger因果权重（granger）：基于时间序列的格兰杰因果检验
"""

import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class EdgeWeightType(str, Enum):
    """边权重类型"""
    CO_FAULT = "co_fault"
    PHYSICAL = "physical"
    GRANGER = "granger"
    COMPOSITE = "composite"


@dataclass
class GraphNode:
    """图节点"""
    id: str
    name: str
    node_type: str
    level: int
    risk_score: float
    risk_level: str
    status_code: int
    status: str
    confidence: float
    parent_id: Optional[str] = None
    position: Optional[Dict[str, float]] = None
    extra_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'node_type': self.node_type,
            'level': self.level,
            'risk_score': self.risk_score,
            'risk_level': self.risk_level,
            'status_code': self.status_code,
            'status': self.status,
            'confidence': self.confidence,
            'parent_id': self.parent_id,
            'position': self.position,
            'extra_info': self.extra_info,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GraphNode':
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            node_type=data.get('node_type', ''),
            level=data.get('level', 0),
            risk_score=data.get('risk_score', 0.0),
            risk_level=data.get('risk_level', '低'),
            status_code=data.get('status_code', 0),
            status=data.get('status', '正常'),
            confidence=data.get('confidence', 0.0),
            parent_id=data.get('parent_id'),
            position=data.get('position'),
            extra_info=data.get('extra_info', {}),
        )


@dataclass
class GraphEdge:
    """图边"""
    source: str
    target: str
    weight: float
    weight_type: str
    co_fault_weight: float = 0.0
    physical_weight: float = 0.0
    granger_weight: float = 0.0
    granger_p_value: Optional[float] = None
    granger_lag: Optional[int] = None
    co_fault_count: int = 0
    extra_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'source': self.source,
            'target': self.target,
            'weight': self.weight,
            'weight_type': self.weight_type,
            'co_fault_weight': self.co_fault_weight,
            'physical_weight': self.physical_weight,
            'granger_weight': self.granger_weight,
            'granger_p_value': self.granger_p_value,
            'granger_lag': self.granger_lag,
            'co_fault_count': self.co_fault_count,
            'extra_info': self.extra_info,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GraphEdge':
        return cls(
            source=data.get('source', ''),
            target=data.get('target', ''),
            weight=data.get('weight', 0.0),
            weight_type=data.get('weight_type', 'composite'),
            co_fault_weight=data.get('co_fault_weight', 0.0),
            physical_weight=data.get('physical_weight', 0.0),
            granger_weight=data.get('granger_weight', 0.0),
            granger_p_value=data.get('granger_p_value'),
            granger_lag=data.get('granger_lag'),
            co_fault_count=data.get('co_fault_count', 0),
            extra_info=data.get('extra_info', {}),
        )


@dataclass
class PropagationGraph:
    """传播图"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    node_count: int
    edge_count: int
    graph_type: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'nodes': [n.to_dict() for n in self.nodes],
            'edges': [e.to_dict() for e in self.edges],
            'node_count': self.node_count,
            'edge_count': self.edge_count,
            'graph_type': self.graph_type,
            'timestamp': self.timestamp,
            'metadata': self.metadata,
        }


class PropagationGraphBuilder:
    """
    传播图构建器

    从组织树和预测数据构建风险传播图，计算多种边权重。
    """

    def __init__(
        self,
        co_fault_weight: float = 0.4,
        physical_weight: float = 0.3,
        granger_weight: float = 0.3,
        max_granger_lag: int = 5,
        granger_significance: float = 0.05,
    ):
        """
        初始化图构建器

        Args:
            co_fault_weight: 共故障权重在综合权重中的占比
            physical_weight: 物理邻接权重在综合权重中的占比
            granger_weight: Granger因果权重在综合权重中的占比
            max_granger_lag: Granger因果检验的最大滞后阶数
            granger_significance: Granger因果检验的显著性水平
        """
        self.co_fault_alpha = co_fault_weight
        self.physical_alpha = physical_weight
        self.granger_alpha = granger_weight
        self.max_granger_lag = max_granger_lag
        self.granger_significance = granger_significance

        self._co_fault_history: Dict[str, Dict[str, int]] = {}
        self._physical_adjacency: Dict[str, List[str]] = {}

        logger.info(
            f"传播图构建器初始化完成: "
            f"co_fault={co_fault_weight}, "
            f"physical={physical_weight}, "
            f"granger={granger_weight}"
        )

    def build_graph(
        self,
        org_nodes: List[Dict[str, Any]],
        prediction_data: Dict[str, Dict[str, Any]],
        graph_type: str = "composite",
        include_levels: Optional[List[str]] = None,
    ) -> PropagationGraph:
        """
        构建传播图

        Args:
            org_nodes: 组织树节点列表
            prediction_data: 预测数据字典 {node_id: {risk_score, risk_level, ...}}
            graph_type: 图类型: bolt/flange/unit/composite
            include_levels: 包含的节点级别，None 表示全部

        Returns:
            PropagationGraph
        """
        from datetime import datetime

        nodes = self._build_nodes(org_nodes, prediction_data, include_levels)
        edges = self._build_edges(nodes, graph_type)

        return PropagationGraph(
            nodes=nodes,
            edges=edges,
            node_count=len(nodes),
            edge_count=len(edges),
            graph_type=graph_type,
            timestamp=datetime.now().isoformat(),
            metadata={
                'weight_coefficients': {
                    'co_fault': self.co_fault_alpha,
                    'physical': self.physical_alpha,
                    'granger': self.granger_alpha,
                }
            }
        )

    def _build_nodes(
        self,
        org_nodes: List[Dict[str, Any]],
        prediction_data: Dict[str, Dict[str, Any]],
        include_levels: Optional[List[str]] = None,
    ) -> List[GraphNode]:
        """构建节点列表"""
        nodes = []

        for org_node in org_nodes:
            node_type = org_node.get('node_type', '')
            node_id = str(org_node.get('id', org_node.get('node_code', '')))

            if include_levels and node_type not in include_levels:
                continue

            pred = prediction_data.get(node_id, {})

            risk_score = pred.get('risk_score', 5.0)
            risk_level = pred.get('risk_level', '中')
            status_code = pred.get('status_code', 0)
            status = pred.get('status', '正常')
            confidence = pred.get('confidence', 0.5)

            position = None
            extra_info = org_node.get('extra_info') or {}
            if 'longitude' in extra_info and 'latitude' in extra_info:
                position = {
                    'longitude': float(extra_info['longitude']),
                    'latitude': float(extra_info['latitude']),
                }
            elif 'x' in extra_info and 'y' in extra_info:
                position = {
                    'x': float(extra_info['x']),
                    'y': float(extra_info['y']),
                }

            node = GraphNode(
                id=node_id,
                name=org_node.get('node_name', node_id),
                node_type=node_type,
                level=org_node.get('level', 0),
                risk_score=float(risk_score),
                risk_level=risk_level,
                status_code=int(status_code),
                status=status,
                confidence=float(confidence),
                parent_id=str(org_node.get('parent_id')) if org_node.get('parent_id') else None,
                position=position,
                extra_info={
                    'sort_order': org_node.get('sort_order', 0),
                    'node_code': org_node.get('node_code', ''),
                    **extra_info,
                }
            )
            nodes.append(node)

        logger.info(f"构建节点完成，共 {len(nodes)} 个节点")
        return nodes

    def _build_edges(
        self,
        nodes: List[GraphNode],
        graph_type: str,
    ) -> List[GraphEdge]:
        """构建边列表"""
        edges = []
        node_ids = {n.id for n in nodes}
        node_map = {n.id: n for n in nodes}

        for i, source_node in enumerate(nodes):
            for target_node in nodes[i + 1:]:
                if source_node.id == target_node.id:
                    continue

                co_fault_w = self._calculate_co_fault_weight(
                    source_node.id, target_node.id
                )
                physical_w = self._calculate_physical_weight(
                    source_node, target_node
                )
                granger_w, p_value, lag = self._calculate_granger_weight(
                    source_node.id, target_node.id
                )

                composite_w = self._composite_weight(
                    co_fault_w, physical_w, granger_w
                )

                if composite_w <= 0:
                    continue

                edge = GraphEdge(
                    source=source_node.id,
                    target=target_node.id,
                    weight=composite_w,
                    weight_type=graph_type,
                    co_fault_weight=co_fault_w,
                    physical_weight=physical_w,
                    granger_weight=granger_w,
                    granger_p_value=p_value,
                    granger_lag=lag,
                    co_fault_count=self._get_co_fault_count(
                        source_node.id, target_node.id
                    ),
                )
                edges.append(edge)

        edges.sort(key=lambda e: e.weight, reverse=True)
        logger.info(f"构建边完成，共 {len(edges)} 条边")
        return edges

    def _calculate_co_fault_weight(
        self, node_a: str, node_b: str
    ) -> float:
        """
        计算历史共故障权重

        基于历史故障数据中两节点同时发生故障的频率。
        """
        count = self._get_co_fault_count(node_a, node_b)
        if count == 0:
            return 0.0

        max_count = max(
            (
                v
                for n in self._co_fault_history.values()
                for v in n.values()
            ),
            default=1
        )
        return min(1.0, count / max(1, max_count))

    def _get_co_fault_count(self, node_a: str, node_b: str) -> int:
        """获取共故障次数"""
        a_history = self._co_fault_history.get(node_a, {})
        b_history = self._co_fault_history.get(node_b, {})
        return max(a_history.get(node_b, 0), b_history.get(node_a, 0))

    def _calculate_physical_weight(
        self, node_a: GraphNode, node_b: GraphNode
    ) -> float:
        """
        计算物理邻接权重

        基于组织结构和位置信息计算邻接程度：
        1. 同父节点 → 权重高
        2. 同一层级且位置接近 → 权重中
        3. 跨层级 → 权重低
        """
        weight = 0.0

        if node_a.parent_id and node_a.parent_id == node_b.parent_id:
            weight += 0.6

        if node_a.level == node_b.level:
            weight += 0.2

        if node_a.position and node_b.position:
            pos_a = node_a.position
            pos_b = node_b.position
            if 'longitude' in pos_a and 'latitude' in pos_a:
                dist = self._haversine_distance(
                    pos_a['latitude'], pos_a['longitude'],
                    pos_b['latitude'], pos_b['longitude'],
                )
                if dist < 100:
                    weight += 0.2 * max(0, 1 - dist / 100)
            elif 'x' in pos_a and 'y' in pos_a:
                dist = np.sqrt(
                    (pos_a['x'] - pos_b['x']) ** 2 +
                    (pos_a['y'] - pos_b['y']) ** 2
                )
                if dist < 1000:
                    weight += 0.2 * max(0, 1 - dist / 1000)

        return min(1.0, weight)

    def _haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """计算两点间的球面距离（公里）"""
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

    def _calculate_granger_weight(
        self, node_a: str, node_b: str
    ) -> Tuple[float, Optional[float], Optional[int]]:
        """
        计算 Granger 因果权重

        基于时间序列数据进行格兰杰因果检验。
        此处提供框架，实际计算需要时间序列数据。
        """
        return 0.0, None, None

    def compute_granger_from_timeseries(
        self,
        series_a: np.ndarray,
        series_b: np.ndarray,
        max_lag: Optional[int] = None,
    ) -> Tuple[float, float, int]:
        """
        从时间序列计算 Granger 因果

        Args:
            series_a: 序列 A
            series_b: 序列 B
            max_lag: 最大滞后阶数

        Returns:
            (weight, p_value, best_lag)
        """
        if max_lag is None:
            max_lag = self.max_granger_lag

        try:
            from statsmodels.tsa.stattools import grangercausalitytests

            data = np.column_stack([series_a, series_b])

            results = grangercausalitytests(
                data, maxlag=max_lag, verbose=False
            )

            best_p = 1.0
            best_lag = 0

            for lag, result in results.items():
                f_test = result[0].get('ssr_ftest', None)
                if f_test is not None:
                    p_value = f_test[1]
                    if p_value < best_p:
                        best_p = p_value
                        best_lag = lag

            if best_p < self.granger_significance:
                weight = 1.0 - best_p
            else:
                weight = 0.0

            return float(weight), float(best_p), int(best_lag)

        except ImportError:
            logger.warning("statsmodels 未安装，Granger 因果检验不可用")
            corr = np.corrcoef(series_a, series_b)[0, 1]
            return float(max(0, abs(corr))), None, None
        except Exception as e:
            logger.warning(f"Granger 因果检验失败: {e}")
            return 0.0, None, None

    def _composite_weight(
        self,
        co_fault: float,
        physical: float,
        granger: float,
    ) -> float:
        """计算综合权重"""
        total_alpha = (
            self.co_fault_alpha +
            self.physical_alpha +
            self.granger_alpha
        )
        if total_alpha <= 0:
            return 0.0

        composite = (
            self.co_fault_alpha * co_fault +
            self.physical_alpha * physical +
            self.granger_alpha * granger
        ) / total_alpha

        return float(composite)

    def update_co_fault_history(
        self,
        fault_events: List[Dict[str, Any]],
    ) -> None:
        """
        更新共故障历史数据

        Args:
            fault_events: 故障事件列表，每个事件包含 node_id 和 timestamp
        """
        from collections import defaultdict

        time_windows = defaultdict(list)
        for event in fault_events:
            node_id = str(event.get('node_id', ''))
            ts = event.get('timestamp', '')
            time_windows[ts[:13]].append(node_id)

        for time_key, nodes in time_windows.items():
            for i, n1 in enumerate(nodes):
                for n2 in nodes[i + 1:]:
                    if n1 not in self._co_fault_history:
                        self._co_fault_history[n1] = {}
                    if n2 not in self._co_fault_history:
                        self._co_fault_history[n2] = {}
                    self._co_fault_history[n1][n2] = (
                        self._co_fault_history[n1].get(n2, 0) + 1
                    )
                    self._co_fault_history[n2][n1] = (
                        self._co_fault_history[n2].get(n1, 0) + 1
                    )

        logger.info(f"共故障历史数据已更新，涉及 {len(self._co_fault_history)} 个节点")

    def update_physical_adjacency(
        self,
        adjacency_map: Dict[str, List[str]],
    ) -> None:
        """
        更新物理邻接关系

        Args:
            adjacency_map: 邻接映射 {node_id: [neighbor_ids]}
        """
        self._physical_adjacency.update(adjacency_map)
        logger.info(f"物理邻接关系已更新，涉及 {len(adjacency_map)} 个节点")

    def get_top_propagation_paths(
        self,
        graph: PropagationGraph,
        source_node: str,
        top_k: int = 10,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        获取从源节点出发的 top-k 传播路径

        Args:
            graph: 传播图
            source_node: 源节点ID
            top_k: 返回前 k 条路径
            max_depth: 最大路径深度

        Returns:
            路径列表
        """
        adjacency = {}
        for edge in graph.edges:
            if edge.source not in adjacency:
                adjacency[edge.source] = []
            if edge.target not in adjacency:
                adjacency[edge.target] = []
            adjacency[edge.source].append((edge.target, edge.weight))
            adjacency[edge.target].append((edge.source, edge.weight))

        paths = []
        visited = set()

        def dfs(current: str, path: List[str], total_weight: float, depth: int):
            if depth > max_depth:
                return
            if current in visited:
                return

            visited.add(current)

            if len(path) > 1:
                paths.append({
                    'path': list(path),
                    'total_weight': total_weight,
                    'avg_weight': total_weight / (len(path) - 1),
                    'depth': len(path) - 1,
                })

            neighbors = adjacency.get(current, [])
            neighbors.sort(key=lambda x: x[1], reverse=True)

            for neighbor, weight in neighbors[:5]:
                if neighbor not in visited:
                    path.append(neighbor)
                    dfs(neighbor, path, total_weight + weight, depth + 1)
                    path.pop()

            visited.remove(current)

        dfs(source_node, [source_node], 0.0, 0)

        paths.sort(key=lambda p: p['total_weight'], reverse=True)
        return paths[:top_k]
