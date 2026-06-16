"""
GeoJSON 热力图生成器

将风险数据转换为 GeoJSON 格式，支持 GIS 系统和前端可视化。
"""

import json
from typing import List, Dict, Optional, Any
from loguru import logger

from .graph_builder import GraphNode, PropagationGraph


class GeoJSONGenerator:
    """
    GeoJSON 格式生成器

    支持生成：
    1. 点要素热力图（每个装置/螺栓一个点）
    2. 线要素传播图（节点间的传播路径）
    3. 多边形区域（基于组织层级的区域聚合）
    """

    def __init__(
        self,
        risk_colors: Optional[Dict[str, str]] = None,
        default_lng: float = 116.4074,
        default_lat: float = 39.9042,
    ):
        """
        初始化 GeoJSON 生成器

        Args:
            risk_colors: 风险等级到颜色的映射
            default_lng: 默认经度（节点无位置时使用）
            default_lat: 默认纬度（节点无位置时使用）
        """
        self.risk_colors = risk_colors or {
            '高': '#ef4444',
            '中': '#f59e0b',
            '低': '#22c55e',
        }
        self.default_lng = default_lng
        self.default_lat = default_lat

        logger.info("GeoJSON生成器初始化完成")

    def generate_heatmap_geojson(
        self,
        nodes: List[GraphNode],
        value_field: str = "risk_score",
        include_edges: bool = False,
        edges: Optional[List] = None,
    ) -> Dict[str, Any]:
        """
        生成热力图 GeoJSON

        Args:
            nodes: 节点列表
            value_field: 用于热力值的字段名
            include_edges: 是否包含边要素
            edges: 边列表

        Returns:
            GeoJSON FeatureCollection
        """
        features = []

        for node in nodes:
            feature = self._node_to_point_feature(node, value_field)
            if feature:
                features.append(feature)

        if include_edges and edges:
            for edge in edges:
                line_feature = self._edge_to_line_feature(edge, nodes)
                if line_feature:
                    features.append(line_feature)

        geojson = {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "generated_at": self._current_timestamp(),
                "node_count": len(nodes),
                "value_field": value_field,
                "edge_count": len(edges) if edges else 0,
            }
        }

        logger.info(f"生成热力图GeoJSON，共 {len(features)} 个要素")
        return geojson

    def generate_propagation_geojson(
        self,
        graph: PropagationGraph,
    ) -> Dict[str, Any]:
        """
        生成传播图 GeoJSON

        包含节点和边，边的宽度/颜色表示传播权重。

        Args:
            graph: 传播图

        Returns:
            GeoJSON FeatureCollection
        """
        features = []

        for node in graph.nodes:
            feature = self._node_to_point_feature(node, "risk_score")
            if feature:
                features.append(feature)

        for edge in graph.edges:
            line_feature = self._edge_to_line_feature(edge, graph.nodes)
            if line_feature:
                features.append(line_feature)

        geojson = {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "generated_at": self._current_timestamp(),
                "node_count": graph.node_count,
                "edge_count": graph.edge_count,
                "graph_type": graph.graph_type,
                "timestamp": graph.timestamp,
            }
        }

        logger.info(f"生成传播图GeoJSON，共 {len(features)} 个要素")
        return geojson

    def generate_aggregated_geojson(
        self,
        nodes: List[GraphNode],
        aggregate_level: str = "unit",
    ) -> Dict[str, Any]:
        """
        生成聚合计的 GeoJSON

        按指定层级聚合风险数据，生成多边形或聚合点。

        Args:
            nodes: 节点列表
            aggregate_level: 聚合层级 (group/factory/unit/flange)

        Returns:
            GeoJSON FeatureCollection
        """
        aggregated = self._aggregate_by_level(nodes, aggregate_level)
        features = []

        for agg_id, agg_data in aggregated.items():
            feature = self._aggregated_to_feature(
                agg_id, agg_data, aggregate_level
            )
            if feature:
                features.append(feature)

        geojson = {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "generated_at": self._current_timestamp(),
                "aggregate_level": aggregate_level,
                "aggregate_count": len(aggregated),
            }
        }

        logger.info(f"生成聚合GeoJSON，共 {len(features)} 个聚合单元")
        return geojson

    def _node_to_point_feature(
        self,
        node: GraphNode,
        value_field: str,
    ) -> Optional[Dict[str, Any]]:
        """将节点转换为点要素"""
        lng, lat = self._get_node_coordinates(node)

        if lng is None or lat is None:
            return None

        value = getattr(node, value_field, node.risk_score)
        color = self.risk_colors.get(node.risk_level, '#888888')

        feature = {
            "type": "Feature",
            "id": node.id,
            "geometry": {
                "type": "Point",
                "coordinates": [lng, lat]
            },
            "properties": {
                "id": node.id,
                "name": node.name,
                "node_type": node.node_type,
                "level": node.level,
                "risk_score": node.risk_score,
                "risk_level": node.risk_level,
                "status_code": node.status_code,
                "status": node.status,
                "confidence": node.confidence,
                "parent_id": node.parent_id,
                "value": value,
                "color": color,
                "extra_info": node.extra_info,
            }
        }

        return feature

    def _edge_to_line_feature(
        self,
        edge,
        nodes: List[GraphNode],
    ) -> Optional[Dict[str, Any]]:
        """将边转换为线要素"""
        node_map = {n.id: n for n in nodes}

        source_node = node_map.get(edge.source)
        target_node = node_map.get(edge.target)

        if not source_node or not target_node:
            return None

        src_lng, src_lat = self._get_node_coordinates(source_node)
        tgt_lng, tgt_lat = self._get_node_coordinates(target_node)

        if src_lng is None or tgt_lng is None:
            return None

        feature = {
            "type": "Feature",
            "id": f"{edge.source}-{edge.target}",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [src_lng, src_lat],
                    [tgt_lng, tgt_lat]
                ]
            },
            "properties": {
                "source": edge.source,
                "target": edge.target,
                "weight": edge.weight,
                "weight_type": edge.weight_type,
                "co_fault_weight": edge.co_fault_weight,
                "physical_weight": edge.physical_weight,
                "granger_weight": edge.granger_weight,
                "co_fault_count": edge.co_fault_count,
                "width": self._weight_to_width(edge.weight),
                "opacity": self._weight_to_opacity(edge.weight),
            }
        }

        return feature

    def _aggregated_to_feature(
        self,
        agg_id: str,
        agg_data: Dict[str, Any],
        aggregate_level: str,
    ) -> Optional[Dict[str, Any]]:
        """将聚合数据转换为要素"""
        if 'center_lng' not in agg_data or 'center_lat' not in agg_data:
            return None

        feature = {
            "type": "Feature",
            "id": agg_id,
            "geometry": {
                "type": "Point",
                "coordinates": [agg_data['center_lng'], agg_data['center_lat']]
            },
            "properties": {
                "id": agg_id,
                "name": agg_data.get('name', agg_id),
                "aggregate_level": aggregate_level,
                "node_count": agg_data.get('node_count', 0),
                "avg_risk_score": agg_data.get('avg_risk_score', 0),
                "max_risk_score": agg_data.get('max_risk_score', 0),
                "min_risk_score": agg_data.get('min_risk_score', 0),
                "risk_distribution": agg_data.get('risk_distribution', {}),
                "color": self.risk_colors.get(
                    agg_data.get('dominant_risk_level', '中'),
                    '#888888'
                ),
            }
        }

        return feature

    def _aggregate_by_level(
        self,
        nodes: List[GraphNode],
        level: str,
    ) -> Dict[str, Dict[str, Any]]:
        """按层级聚合节点"""
        aggregates: Dict[str, Dict[str, Any]] = {}

        for node in nodes:
            if node.level < self._level_to_int(level):
                continue

            agg_id = self._get_ancestor_id(node, level)
            if not agg_id:
                continue

            if agg_id not in aggregates:
                aggregates[agg_id] = {
                    'name': '',
                    'nodes': [],
                    'risk_scores': [],
                    'lngs': [],
                    'lats': [],
                }

            aggregates[agg_id]['nodes'].append(node)
            aggregates[agg_id]['risk_scores'].append(node.risk_score)

            lng, lat = self._get_node_coordinates(node)
            if lng is not None and lat is not None:
                aggregates[agg_id]['lngs'].append(lng)
                aggregates[agg_id]['lats'].append(lat)

        for agg_id, data in aggregates.items():
            scores = data['risk_scores']
            if scores:
                data['avg_risk_score'] = sum(scores) / len(scores)
                data['max_risk_score'] = max(scores)
                data['min_risk_score'] = min(scores)
            else:
                data['avg_risk_score'] = 0
                data['max_risk_score'] = 0
                data['min_risk_score'] = 0

            if data['lngs'] and data['lats']:
                data['center_lng'] = sum(data['lngs']) / len(data['lngs'])
                data['center_lat'] = sum(data['lats']) / len(data['lats'])

            data['node_count'] = len(data['nodes'])
            data['risk_distribution'] = self._calculate_risk_distribution(
                data['nodes']
            )
            data['dominant_risk_level'] = self._get_dominant_risk_level(
                data['risk_distribution']
            )

            if data['nodes']:
                data['name'] = data['nodes'][0].name

        return aggregates

    def _get_node_coordinates(
        self, node: GraphNode
    ) -> tuple:
        """获取节点坐标"""
        if node.position:
            if 'longitude' in node.position and 'latitude' in node.position:
                return (
                    node.position['longitude'],
                    node.position['latitude']
                )
            if 'x' in node.position and 'y' in node.position:
                return (node.position['x'], node.position['y'])

        return (None, None)

    def _level_to_int(self, level: str) -> int:
        """层级字符串转整数"""
        level_map = {
            'group': 0,
            'factory': 1,
            'unit': 2,
            'flange': 3,
            'bolt': 4,
        }
        return level_map.get(level, 2)

    def _get_ancestor_id(self, node: GraphNode, level: str) -> Optional[str]:
        """获取指定层级的祖先节点ID"""
        target_level = self._level_to_int(level)
        if node.level == target_level:
            return node.id
        if node.level < target_level:
            return None

        return node.parent_id

    def _calculate_risk_distribution(
        self, nodes: List[GraphNode]
    ) -> Dict[str, int]:
        """计算风险分布"""
        distribution = {'高': 0, '中': 0, '低': 0}
        for node in nodes:
            if node.risk_level in distribution:
                distribution[node.risk_level] += 1
        return distribution

    def _get_dominant_risk_level(
        self, distribution: Dict[str, int]
    ) -> str:
        """获取主要风险等级"""
        if not distribution:
            return '中'
        return max(distribution.items(), key=lambda x: x[1])[0]

    def _weight_to_width(self, weight: float) -> float:
        """权重转线宽"""
        return max(0.5, weight * 8)

    def _weight_to_opacity(self, weight: float) -> float:
        """权重转不透明度"""
        return max(0.1, min(1.0, weight))

    def _current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()

    def to_echarts_graph(
        self,
        graph: PropagationGraph,
        layout: str = "force",
    ) -> Dict[str, Any]:
        """
        转换为 ECharts 图结构

        Args:
            graph: 传播图
            layout: 布局类型 force/circular/none

        Returns:
            ECharts graph 数据结构
        """
        echarts_nodes = []
        for node in graph.nodes:
            echarts_nodes.append({
                'id': node.id,
                'name': node.name,
                'value': node.risk_score,
                'category': node.node_type,
                'symbolSize': self._risk_score_to_size(node.risk_score),
                'itemStyle': {
                    'color': self.risk_colors.get(node.risk_level, '#888888')
                },
                'risk_level': node.risk_level,
                'status': node.status,
                'confidence': node.confidence,
                'level': node.level,
                'extra_info': node.extra_info,
            })

        echarts_links = []
        for edge in graph.edges:
            echarts_links.append({
                'source': edge.source,
                'target': edge.target,
                'value': edge.weight,
                'lineStyle': {
                    'width': self._weight_to_width(edge.weight),
                    'opacity': self._weight_to_opacity(edge.weight),
                },
                'weight_type': edge.weight_type,
                'co_fault_weight': edge.co_fault_weight,
                'physical_weight': edge.physical_weight,
                'granger_weight': edge.granger_weight,
            })

        categories = list(set(n['category'] for n in echarts_nodes))

        return {
            'nodes': echarts_nodes,
            'links': echarts_links,
            'categories': [{'name': cat} for cat in categories],
            'layout': layout,
            'metadata': {
                'node_count': graph.node_count,
                'edge_count': graph.edge_count,
                'graph_type': graph.graph_type,
                'timestamp': graph.timestamp,
            }
        }

    def _risk_score_to_size(self, risk_score: float) -> int:
        """风险评分转节点大小"""
        return int(10 + (10 - risk_score) * 4)
