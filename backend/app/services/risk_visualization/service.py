"""
风险可视化主服务

整合图构建、GeoJSON生成、时间切片等功能，提供统一的服务接口。
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from loguru import logger

from .graph_builder import (
    PropagationGraphBuilder,
    PropagationGraph,
    EdgeWeightType,
)
from .geojson_generator import GeoJSONGenerator
from .time_slicer import TimeSliceService, TimeSeriesResult


class RiskVisualizationService:
    """
    风险可视化数据服务

    提供装置级风险热力图与传播可视化的数据服务能力。

    主要功能：
    1. 传播图构建（nodes/edges）
    2. GeoJSON 热力图数据
    3. 时间切片历史回放
    4. ECharts 图结构数据
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_components()
        return cls._instance

    def _init_components(self):
        """初始化组件"""
        self.graph_builder = PropagationGraphBuilder()
        self.geojson_generator = GeoJSONGenerator()
        self.time_slice_service = TimeSliceService()

        self._prediction_cache: Dict[str, Dict[str, Any]] = {}
        self._org_node_cache: List[Dict[str, Any]] = []

        logger.info("风险可视化服务初始化完成")

    def get_propagation_graph(
        self,
        org_nodes: List[Dict[str, Any]],
        prediction_data: Dict[str, Dict[str, Any]],
        graph_type: str = "composite",
        include_levels: Optional[List[str]] = None,
    ) -> PropagationGraph:
        """
        获取风险传播图

        Args:
            org_nodes: 组织节点列表
            prediction_data: 预测数据
            graph_type: 图类型
            include_levels: 包含的节点级别

        Returns:
            PropagationGraph
        """
        self._org_node_cache = org_nodes
        for node_id, data in prediction_data.items():
            self._prediction_cache[node_id] = data

        graph = self.graph_builder.build_graph(
            org_nodes=org_nodes,
            prediction_data=prediction_data,
            graph_type=graph_type,
            include_levels=include_levels,
        )

        return graph

    def get_heatmap_geojson(
        self,
        org_nodes: List[Dict[str, Any]],
        prediction_data: Dict[str, Dict[str, Any]],
        value_field: str = "risk_score",
        aggregate_level: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取热力图 GeoJSON

        Args:
            org_nodes: 组织节点列表
            prediction_data: 预测数据
            value_field: 值字段
            aggregate_level: 聚合层级

        Returns:
            GeoJSON FeatureCollection
        """
        graph = self.get_propagation_graph(
            org_nodes=org_nodes,
            prediction_data=prediction_data,
        )

        if aggregate_level:
            return self.geojson_generator.generate_aggregated_geojson(
                nodes=graph.nodes,
                aggregate_level=aggregate_level,
            )
        else:
            return self.geojson_generator.generate_heatmap_geojson(
                nodes=graph.nodes,
                value_field=value_field,
                include_edges=True,
                edges=graph.edges,
            )

    def get_echarts_graph(
        self,
        org_nodes: List[Dict[str, Any]],
        prediction_data: Dict[str, Dict[str, Any]],
        graph_type: str = "composite",
        layout: str = "force",
    ) -> Dict[str, Any]:
        """
        获取 ECharts 图结构数据

        Args:
            org_nodes: 组织节点列表
            prediction_data: 预测数据
            graph_type: 图类型
            layout: 布局类型

        Returns:
            ECharts graph 数据结构
        """
        graph = self.get_propagation_graph(
            org_nodes=org_nodes,
            prediction_data=prediction_data,
            graph_type=graph_type,
        )

        return self.geojson_generator.to_echarts_graph(graph, layout=layout)

    def get_time_series_slices(
        self,
        org_nodes: List[Dict[str, Any]],
        history_data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        interval_minutes: Optional[int] = None,
        history_hours: Optional[int] = None,
        include_edges: bool = False,
        use_mock: bool = False,
    ) -> TimeSeriesResult:
        """
        获取时间切片序列

        Args:
            org_nodes: 组织节点列表
            history_data: 历史数据
            interval_minutes: 时间间隔（分钟）
            history_hours: 历史时长（小时）
            include_edges: 是否包含边
            use_mock: 是否使用模拟数据

        Returns:
            TimeSeriesResult
        """
        if use_mock or history_data is None:
            history_data = self.time_slice_service.generate_mock_history(
                org_nodes=org_nodes,
                history_hours=history_hours or 24,
                interval_minutes=30,
            )

        result = self.time_slice_service.generate_time_slices(
            org_nodes=org_nodes,
            history_data=history_data,
            interval_minutes=interval_minutes,
            history_hours=history_hours,
            include_edges=include_edges,
            graph_builder=self.graph_builder if include_edges else None,
        )

        return result

    def get_time_slice_geojson(
        self,
        org_nodes: List[Dict[str, Any]],
        history_data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        slice_index: Optional[int] = None,
        timestamp: Optional[str] = None,
        use_mock: bool = False,
    ) -> Dict[str, Any]:
        """
        获取指定时间切片的 GeoJSON

        Args:
            org_nodes: 组织节点列表
            history_data: 历史数据
            slice_index: 切片索引
            timestamp: 时间戳
            use_mock: 是否使用模拟数据

        Returns:
            GeoJSON FeatureCollection
        """
        time_series = self.get_time_series_slices(
            org_nodes=org_nodes,
            history_data=history_data,
            include_edges=True,
            use_mock=use_mock,
        )

        if slice_index is not None:
            if 0 <= slice_index < len(time_series.time_slices):
                target_slice = time_series.time_slices[slice_index]
            else:
                target_slice = time_series.time_slices[-1]
        else:
            target_slice = time_series.time_slices[-1]

        features = []

        for node in target_slice.nodes:
            feature = self._node_dict_to_feature(node)
            if feature:
                features.append(feature)

        if target_slice.edges:
            for edge in target_slice.edges:
                line_feature = self._edge_dict_to_feature(
                    edge, target_slice.nodes
                )
                if line_feature:
                    features.append(line_feature)

        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "timestamp": target_slice.timestamp,
                "slice_index": target_slice.slice_index,
                "total_slices": time_series.total_slices,
                "stats": target_slice.stats,
            }
        }

    def get_propagation_paths(
        self,
        org_nodes: List[Dict[str, Any]],
        prediction_data: Dict[str, Dict[str, Any]],
        source_node: str,
        top_k: int = 10,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        获取风险传播路径

        Args:
            org_nodes: 组织节点列表
            prediction_data: 预测数据
            source_node: 源节点ID
            top_k: 返回前 k 条路径
            max_depth: 最大深度

        Returns:
            路径列表
        """
        graph = self.get_propagation_graph(
            org_nodes=org_nodes,
            prediction_data=prediction_data,
        )

        paths = self.graph_builder.get_top_propagation_paths(
            graph=graph,
            source_node=source_node,
            top_k=top_k,
            max_depth=max_depth,
        )

        return paths

    def get_risk_summary(
        self,
        org_nodes: List[Dict[str, Any]],
        prediction_data: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        获取风险汇总统计

        Args:
            org_nodes: 组织节点列表
            prediction_data: 预测数据

        Returns:
            风险汇总数据
        """
        graph = self.get_propagation_graph(
            org_nodes=org_nodes,
            prediction_data=prediction_data,
        )

        risk_scores = [n.risk_score for n in graph.nodes]
        risk_levels = [n.risk_level for n in graph.nodes]

        level_counts = {'高': 0, '中': 0, '低': 0}
        for level in risk_levels:
            if level in level_counts:
                level_counts[level] += 1

        high_risk_nodes = [
            n.to_dict() for n in graph.nodes
            if n.risk_level == '高'
        ]
        high_risk_nodes.sort(key=lambda x: x['risk_score'])

        return {
            'total_nodes': graph.node_count,
            'total_edges': graph.edge_count,
            'avg_risk_score': round(sum(risk_scores) / len(risk_scores), 2) if risk_scores else 0,
            'max_risk_score': max(risk_scores) if risk_scores else 0,
            'min_risk_score': min(risk_scores) if risk_scores else 0,
            'risk_distribution': level_counts,
            'high_risk_ratio': round(level_counts['高'] / len(risk_scores), 4) if risk_scores else 0,
            'high_risk_nodes': high_risk_nodes[:10],
            'timestamp': graph.timestamp,
        }

    def _node_dict_to_feature(
        self, node: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """节点字典转 GeoJSON 点要素"""
        position = node.get('position') or node.get('extra_info', {})

        lng = position.get('longitude') if position else None
        lat = position.get('latitude') if position else None

        if lng is None or lat is None:
            extra = node.get('extra_info', {})
            if isinstance(extra, dict):
                lng = extra.get('longitude')
                lat = extra.get('latitude')

        if lng is None or lat is None:
            return None

        risk_level = node.get('risk_level', '中')
        color = self.geojson_generator.risk_colors.get(risk_level, '#888888')

        return {
            "type": "Feature",
            "id": node.get('id'),
            "geometry": {
                "type": "Point",
                "coordinates": [float(lng), float(lat)]
            },
            "properties": {
                "id": node.get('id'),
                "name": node.get('name'),
                "node_type": node.get('node_type'),
                "level": node.get('level'),
                "risk_score": node.get('risk_score'),
                "risk_level": risk_level,
                "status_code": node.get('status_code'),
                "status": node.get('status'),
                "confidence": node.get('confidence'),
                "value": node.get('risk_score'),
                "color": color,
            }
        }

    def _edge_dict_to_feature(
        self, edge: Dict[str, Any], nodes: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """边字典转 GeoJSON 线要素"""
        node_map = {n['id']: n for n in nodes}

        source_node = node_map.get(edge.get('source', ''))
        target_node = node_map.get(edge.get('target', ''))

        if not source_node or not target_node:
            return None

        src_feat = self._node_dict_to_feature(source_node)
        tgt_feat = self._node_dict_to_feature(target_node)

        if not src_feat or not tgt_feat:
            return None

        return {
            "type": "Feature",
            "id": f"{edge['source']}-{edge['target']}",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    src_feat['geometry']['coordinates'],
                    tgt_feat['geometry']['coordinates']
                ]
            },
            "properties": {
                "source": edge['source'],
                "target": edge['target'],
                "weight": edge.get('weight', 0),
                "weight_type": edge.get('weight_type', 'composite'),
            }
        }

    def update_edge_weights_config(
        self,
        co_fault_weight: Optional[float] = None,
        physical_weight: Optional[float] = None,
        granger_weight: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        更新边权重配置

        Args:
            co_fault_weight: 共故障权重
            physical_weight: 物理邻接权重
            granger_weight: Granger 因果权重

        Returns:
            当前配置
        """
        if co_fault_weight is not None:
            self.graph_builder.co_fault_alpha = co_fault_weight
        if physical_weight is not None:
            self.graph_builder.physical_alpha = physical_weight
        if granger_weight is not None:
            self.graph_builder.granger_alpha = granger_weight

        return {
            'co_fault_weight': self.graph_builder.co_fault_alpha,
            'physical_weight': self.graph_builder.physical_alpha,
            'granger_weight': self.graph_builder.granger_alpha,
        }

    def update_co_fault_history(
        self, fault_events: List[Dict[str, Any]]
    ) -> None:
        """更新共故障历史"""
        self.graph_builder.update_co_fault_history(fault_events)

    def detect_significant_changes(
        self,
        org_nodes: List[Dict[str, Any]],
        history_data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        threshold: float = 2.0,
        use_mock: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        检测显著变化点

        Args:
            org_nodes: 组织节点列表
            history_data: 历史数据
            threshold: 变化阈值
            use_mock: 是否使用模拟数据

        Returns:
            显著变化列表
        """
        time_series = self.get_time_series_slices(
            org_nodes=org_nodes,
            history_data=history_data,
            use_mock=use_mock,
        )

        return self.time_slice_service.detect_significant_changes(
            time_series, threshold=threshold
        )

    # ============================================================
    # API 友好方法（支持 tenant_id，自动生成模拟数据）
    # ============================================================

    def _generate_mock_org_nodes(self, tenant_id: int) -> List[Dict[str, Any]]:
        """生成模拟组织节点数据"""
        import random

        random.seed(hash(tenant_id) % 10000)

        nodes = []
        factories = [
            {"id": "FA001", "name": "北京化工厂", "lng": 116.4074, "lat": 39.9042},
            {"id": "FA002", "name": "上海石化厂", "lng": 121.4737, "lat": 31.2304},
            {"id": "FA003", "name": "广州炼油厂", "lng": 113.2644, "lat": 23.1291},
        ]

        units = [
            "催化裂化装置", "加氢裂化装置", "常减压装置",
            "催化重整装置", "延迟焦化装置", "气体分馏装置",
        ]

        for factory in factories:
            nodes.append({
                "id": factory["id"],
                "name": factory["name"],
                "node_type": "factory",
                "level": 2,
                "parent_id": "G001",
                "position": {"longitude": factory["lng"], "latitude": factory["lat"]},
                "extra_info": {"longitude": factory["lng"], "latitude": factory["lat"]},
            })

            for i, unit_name in enumerate(units):
                unit_id = f"{factory['id']}-U{i+1:03d}"
                unit_lng = factory["lng"] + (random.random() - 0.5) * 0.05
                unit_lat = factory["lat"] + (random.random() - 0.5) * 0.05
                nodes.append({
                    "id": unit_id,
                    "name": f"{factory['name']}-{unit_name}",
                    "node_type": "unit",
                    "level": 3,
                    "parent_id": factory["id"],
                    "position": {"longitude": unit_lng, "latitude": unit_lat},
                    "extra_info": {"longitude": unit_lng, "latitude": unit_lat},
                })

                for j in range(3):
                    flange_id = f"{unit_id}-F{j+1:02d}"
                    flange_lng = unit_lng + (random.random() - 0.5) * 0.01
                    flange_lat = unit_lat + (random.random() - 0.5) * 0.01
                    nodes.append({
                        "id": flange_id,
                        "name": f"{unit_name}-法兰{j+1}",
                        "node_type": "flange",
                        "level": 4,
                        "parent_id": unit_id,
                        "position": {"longitude": flange_lng, "latitude": flange_lat},
                        "extra_info": {"longitude": flange_lng, "latitude": flange_lat},
                    })

        return nodes

    def _generate_mock_predictions(self, org_nodes: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """生成模拟预测数据"""
        import random

        predictions = {}
        for node in org_nodes:
            risk_score = round(random.uniform(1.0, 9.5), 1)
            if risk_score >= 8:
                risk_level = "高"
                status_code = 3
                status = "紧急级预警"
            elif risk_score >= 5:
                risk_level = "中"
                status_code = 2
                status = "检查级预警"
            elif risk_score >= 3:
                risk_level = "中"
                status_code = 1
                status = "关注级预警"
            else:
                risk_level = "低"
                status_code = 0
                status = "正常"

            predictions[node["id"]] = {
                "id": node["id"],
                "name": node["name"],
                "node_type": node["node_type"],
                "risk_score": risk_score,
                "risk_level": risk_level,
                "status_code": status_code,
                "status": status,
                "confidence": round(random.uniform(0.7, 0.98), 2),
            }

        return predictions

    def _ensure_mock_data(self, tenant_id: int):
        """确保有模拟数据可用"""
        if tenant_id not in self._prediction_cache or not self._org_node_cache:
            org_nodes = self._generate_mock_org_nodes(tenant_id)
            predictions = self._generate_mock_predictions(org_nodes)
            self._org_node_cache = org_nodes
            self._prediction_cache = predictions

    # ---------- API 方法 ----------

    def get_propagation_graph(
        self,
        tenant_id: int = None,
        graph_type: str = "composite",
        org_nodes: List[Dict[str, Any]] = None,
        prediction_data: Dict[str, Dict[str, Any]] = None,
        include_levels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        获取风险传播图（API 友好版本）

        Args:
            tenant_id: 租户ID（使用模拟数据时）
            graph_type: 图类型
            org_nodes: 组织节点列表（可选，有则使用）
            prediction_data: 预测数据（可选，有则使用）
            include_levels: 包含的节点级别

        Returns:
            传播图字典
        """
        if org_nodes is None or prediction_data is None:
            if tenant_id is None:
                raise ValueError("必须提供 tenant_id 或 org_nodes + prediction_data")
            self._ensure_mock_data(tenant_id)
            org_nodes = self._org_node_cache
            prediction_data = self._prediction_cache

        graph = self.graph_builder.build_graph(
            org_nodes=org_nodes,
            prediction_data=prediction_data,
            graph_type=graph_type,
            include_levels=include_levels,
        )

        return {
            "nodes": [n.to_dict() for n in graph.nodes],
            "edges": [e.to_dict() for e in graph.edges],
            "node_count": graph.node_count,
            "edge_count": graph.edge_count,
            "graph_type": graph.graph_type,
            "timestamp": graph.timestamp,
            "metadata": {},
        }

    def get_heatmap_geojson(
        self,
        tenant_id: int = None,
        node_type: str = "all",
        value_field: str = "risk_score",
        aggregate_level: Optional[str] = None,
        org_nodes: List[Dict[str, Any]] = None,
        prediction_data: Dict[str, Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        获取热力图 GeoJSON（API 友好版本）
        """
        if org_nodes is None or prediction_data is None:
            if tenant_id is None:
                raise ValueError("必须提供 tenant_id 或 org_nodes + prediction_data")
            self._ensure_mock_data(tenant_id)
            org_nodes = self._org_node_cache
            prediction_data = self._prediction_cache

        graph_result = self.get_propagation_graph(
            tenant_id=tenant_id,
            org_nodes=org_nodes,
            prediction_data=prediction_data,
        )

        from .graph_builder import PropagationGraph, GraphNode, GraphEdge

        nodes = [GraphNode.from_dict(n) for n in graph_result["nodes"]]
        edges = [GraphEdge.from_dict(e) for e in graph_result["edges"]]
        graph = PropagationGraph(
            nodes=nodes,
            edges=edges,
            node_count=graph_result["node_count"],
            edge_count=graph_result["edge_count"],
            graph_type=graph_result["graph_type"],
            timestamp=graph_result["timestamp"],
        )

        if aggregate_level:
            return self.geojson_generator.generate_aggregated_geojson(
                nodes=graph.nodes,
                aggregate_level=aggregate_level,
            )
        else:
            return self.geojson_generator.generate_heatmap_geojson(
                nodes=graph.nodes,
                value_field=value_field,
                include_edges=True,
                edges=graph.edges,
            )

    def get_echarts_graph(
        self,
        tenant_id: int = None,
        graph_type: str = "composite",
        layout: str = "force",
        org_nodes: List[Dict[str, Any]] = None,
        prediction_data: Dict[str, Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        获取 ECharts 图结构数据（API 友好版本）
        """
        if org_nodes is None or prediction_data is None:
            if tenant_id is None:
                raise ValueError("必须提供 tenant_id 或 org_nodes + prediction_data")
            self._ensure_mock_data(tenant_id)
            org_nodes = self._org_node_cache
            prediction_data = self._prediction_cache

        graph_result = self.get_propagation_graph(
            tenant_id=tenant_id,
            org_nodes=org_nodes,
            prediction_data=prediction_data,
            graph_type=graph_type,
        )

        from .graph_builder import PropagationGraph, GraphNode, GraphEdge

        nodes = [GraphNode.from_dict(n) for n in graph_result["nodes"]]
        edges = [GraphEdge.from_dict(e) for e in graph_result["edges"]]
        graph = PropagationGraph(
            nodes=nodes,
            edges=edges,
            node_count=graph_result["node_count"],
            edge_count=graph_result["edge_count"],
            graph_type=graph_result["graph_type"],
            timestamp=graph_result["timestamp"],
        )

        return self.geojson_generator.to_echarts_graph(graph, layout=layout)

    def get_time_series_slices(
        self,
        tenant_id: int = None,
        history_hours: int = 24,
        interval_minutes: int = 60,
        include_edges: bool = False,
        use_mock: bool = True,
        org_nodes: List[Dict[str, Any]] = None,
        history_data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        """
        获取时间切片序列（API 友好版本）
        """
        if org_nodes is None:
            if tenant_id is None:
                raise ValueError("必须提供 tenant_id 或 org_nodes")
            self._ensure_mock_data(tenant_id)
            org_nodes = self._org_node_cache

        if use_mock or history_data is None:
            history_data = self.time_slice_service.generate_mock_history(
                org_nodes=org_nodes,
                history_hours=history_hours,
                interval_minutes=interval_minutes,
            )

        result = self.time_slice_service.generate_time_slices(
            org_nodes=org_nodes,
            history_data=history_data,
            interval_minutes=interval_minutes,
            history_hours=history_hours,
            include_edges=include_edges,
            graph_builder=self.graph_builder if include_edges else None,
        )

        return {
            "time_slices": [s.to_dict() for s in result.time_slices],
            "total_slices": result.total_slices,
            "time_range": {
                "start": result.start_time,
                "end": result.end_time,
            },
            "interval_minutes": result.interval_minutes,
            "metadata": {},
        }

    def get_time_slice_geojson(
        self,
        tenant_id: int = None,
        slice_index: int = 0,
        history_hours: int = 24,
        interval_minutes: int = 60,
        use_mock: bool = True,
        org_nodes: List[Dict[str, Any]] = None,
        history_data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        """
        获取指定时间切片的 GeoJSON（API 友好版本）
        """
        time_series = self.get_time_series_slices(
            tenant_id=tenant_id,
            history_hours=history_hours,
            interval_minutes=interval_minutes,
            include_edges=True,
            use_mock=use_mock,
            org_nodes=org_nodes,
            history_data=history_data,
        )

        slices = time_series["time_slices"]
        if 0 <= slice_index < len(slices):
            target_slice = slices[slice_index]
        else:
            target_slice = slices[-1]

        features = []

        for node in target_slice["nodes"]:
            feature = self._node_dict_to_feature(node)
            if feature:
                features.append(feature)

        if target_slice.get("edges"):
            for edge in target_slice["edges"]:
                line_feature = self._edge_dict_to_feature(
                    edge, target_slice["nodes"]
                )
                if line_feature:
                    features.append(line_feature)

        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "timestamp": target_slice["timestamp"],
                "slice_index": target_slice["slice_index"],
                "total_slices": time_series["total_slices"],
                "stats": target_slice.get("stats", {}),
            }
        }

    def get_propagation_paths(
        self,
        tenant_id: int = None,
        source_node: str = "",
        top_k: int = 10,
        max_depth: int = 3,
        org_nodes: List[Dict[str, Any]] = None,
        prediction_data: Dict[str, Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        获取风险传播路径（API 友好版本）
        """
        if org_nodes is None or prediction_data is None:
            if tenant_id is None:
                raise ValueError("必须提供 tenant_id 或 org_nodes + prediction_data")
            self._ensure_mock_data(tenant_id)
            org_nodes = self._org_node_cache
            prediction_data = self._prediction_cache

        graph_result = self.get_propagation_graph(
            tenant_id=tenant_id,
            org_nodes=org_nodes,
            prediction_data=prediction_data,
        )

        from .graph_builder import PropagationGraph, GraphNode, GraphEdge

        nodes = [GraphNode.from_dict(n) for n in graph_result["nodes"]]
        edges = [GraphEdge.from_dict(e) for e in graph_result["edges"]]
        graph = PropagationGraph(
            nodes=nodes,
            edges=edges,
            node_count=graph_result["node_count"],
            edge_count=graph_result["edge_count"],
            graph_type=graph_result["graph_type"],
            timestamp=graph_result["timestamp"],
        )

        paths = self.graph_builder.get_top_propagation_paths(
            graph=graph,
            source_node=source_node,
            top_k=top_k,
            max_depth=max_depth,
        )

        return {
            "source_node": source_node,
            "total_paths": len(paths),
            "paths": paths,
        }

    def get_risk_summary(
        self,
        tenant_id: int = None,
        graph_type: str = "composite",
        org_nodes: List[Dict[str, Any]] = None,
        prediction_data: Dict[str, Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        获取风险汇总统计（API 友好版本）
        """
        graph_result = self.get_propagation_graph(
            tenant_id=tenant_id,
            graph_type=graph_type,
            org_nodes=org_nodes,
            prediction_data=prediction_data,
        )

        nodes = graph_result["nodes"]
        risk_scores = [n["risk_score"] for n in nodes]
        risk_levels = [n["risk_level"] for n in nodes]

        level_counts = {"高": 0, "中": 0, "低": 0}
        for level in risk_levels:
            if level in level_counts:
                level_counts[level] += 1

        high_risk_nodes = [
            n for n in nodes if n["risk_level"] == "高"
        ]
        high_risk_nodes.sort(key=lambda x: x["risk_score"], reverse=True)

        return {
            "total_nodes": graph_result["node_count"],
            "total_edges": graph_result["edge_count"],
            "avg_risk_score": round(sum(risk_scores) / len(risk_scores), 2) if risk_scores else 0,
            "max_risk_score": max(risk_scores) if risk_scores else 0,
            "min_risk_score": min(risk_scores) if risk_scores else 0,
            "risk_distribution": level_counts,
            "high_risk_ratio": round(level_counts["高"] / len(risk_scores), 4) if risk_scores else 0,
            "high_risk_nodes": high_risk_nodes[:10],
            "timestamp": graph_result["timestamp"],
        }

    def get_edge_weights_config(self, tenant_id: int = None) -> Dict[str, float]:
        """
        获取边权重配置（API 友好版本）
        """
        return {
            "co_fault_weight": self.graph_builder.co_fault_alpha,
            "physical_weight": self.graph_builder.physical_alpha,
            "granger_weight": self.graph_builder.granger_alpha,
        }

    def update_edge_weights_config(
        self,
        tenant_id: int = None,
        co_fault_weight: Optional[float] = None,
        physical_weight: Optional[float] = None,
        granger_weight: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        更新边权重配置（API 友好版本）
        """
        if co_fault_weight is not None:
            self.graph_builder.co_fault_alpha = co_fault_weight
        if physical_weight is not None:
            self.graph_builder.physical_alpha = physical_weight
        if granger_weight is not None:
            self.graph_builder.granger_alpha = granger_weight

        return {
            "co_fault_weight": self.graph_builder.co_fault_alpha,
            "physical_weight": self.graph_builder.physical_alpha,
            "granger_weight": self.graph_builder.granger_alpha,
        }

    def detect_significant_changes(
        self,
        tenant_id: int = None,
        threshold: float = 2.0,
        history_hours: int = 24,
        use_mock: bool = True,
        org_nodes: List[Dict[str, Any]] = None,
        history_data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        """
        检测显著变化点（API 友好版本）
        """
        time_series = self.get_time_series_slices(
            tenant_id=tenant_id,
            history_hours=history_hours,
            use_mock=use_mock,
            org_nodes=org_nodes,
            history_data=history_data,
        )

        slices = time_series["time_slices"]
        change_slices = []

        for i in range(1, len(slices)):
            prev_slice = slices[i - 1]
            curr_slice = slices[i]

            prev_map = {n["id"]: n for n in prev_slice["nodes"]}
            curr_map = {n["id"]: n for n in curr_slice["nodes"]}

            changes = []
            for node_id, curr_node in curr_map.items():
                prev_node = prev_map.get(node_id)
                if prev_node:
                    delta = curr_node["risk_score"] - prev_node["risk_score"]
                    if abs(delta) >= threshold:
                        changes.append({
                            "node_id": node_id,
                            "node_name": curr_node["name"],
                            "prev_risk": prev_node["risk_score"],
                            "curr_risk": curr_node["risk_score"],
                            "delta": delta,
                            "direction": "up" if delta > 0 else "down",
                        })

            if changes:
                change_slices.append({
                    "slice_index": i,
                    "timestamp": curr_slice["timestamp"],
                    "change_count": len(changes),
                    "changes": changes,
                })

        return {
            "total_slices": len(slices),
            "change_slices": len(change_slices),
            "threshold": threshold,
            "changes": change_slices,
        }
