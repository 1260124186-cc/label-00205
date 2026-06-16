"""
时间切片服务

生成过去 24 小时的风险演化时间切片数据，支持动画回放。
"""

import numpy as np
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from loguru import logger

from .graph_builder import PropagationGraph, GraphNode, GraphEdge


@dataclass
class TimeSlice:
    """时间切片"""
    timestamp: str
    slice_index: int
    nodes: List[Dict[str, Any]]
    edges: Optional[List[Dict[str, Any]]] = None
    stats: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'slice_index': self.slice_index,
            'nodes': self.nodes,
            'edges': self.edges,
            'stats': self.stats or {},
        }


@dataclass
class TimeSeriesResult:
    """时间序列结果"""
    time_slices: List[TimeSlice]
    total_slices: int
    time_range: Dict[str, str]
    interval_minutes: int
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'time_slices': [ts.to_dict() for ts in self.time_slices],
            'total_slices': self.total_slices,
            'time_range': self.time_range,
            'interval_minutes': self.interval_minutes,
            'metadata': self.metadata,
        }


class TimeSliceService:
    """
    时间切片服务

    生成历史风险演化的时间切片数据，支持：
    1. 固定间隔切片（如每小时一个切片）
    2. 事件驱动切片（风险突变时增加切片）
    3. 增量推送（与 WebSocket 配合）
    """

    def __init__(
        self,
        default_interval_minutes: int = 60,
        default_history_hours: int = 24,
    ):
        """
        初始化时间切片服务

        Args:
            default_interval_minutes: 默认时间间隔（分钟）
            default_history_hours: 默认历史时长（小时）
        """
        self.default_interval_minutes = default_interval_minutes
        self.default_history_hours = default_history_hours
        self._history_cache: Dict[str, List[Dict[str, Any]]] = {}

        logger.info(
            f"时间切片服务初始化完成: "
            f"间隔={default_interval_minutes}分钟, "
            f"历史={default_history_hours}小时"
        )

    def generate_time_slices(
        self,
        org_nodes: List[Dict[str, Any]],
        history_data: Dict[str, List[Dict[str, Any]]],
        interval_minutes: Optional[int] = None,
        history_hours: Optional[int] = None,
        include_edges: bool = False,
        graph_builder=None,
    ) -> TimeSeriesResult:
        """
        生成时间切片

        Args:
            org_nodes: 组织节点列表
            history_data: 历史数据 {node_id: [{timestamp, risk_score, ...}, ...]}
            interval_minutes: 时间间隔（分钟）
            history_hours: 历史时长（小时）
            include_edges: 是否包含边
            graph_builder: 图构建器（计算边时需要）

        Returns:
            TimeSeriesResult
        """
        if interval_minutes is None:
            interval_minutes = self.default_interval_minutes
        if history_hours is None:
            history_hours = self.default_history_hours

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=history_hours)

        slice_count = int(history_hours * 60 / interval_minutes) + 1
        time_slices = []

        for i in range(slice_count):
            slice_time = start_time + timedelta(minutes=i * interval_minutes)

            slice_nodes = self._compute_slice_nodes(
                org_nodes, history_data, slice_time
            )

            slice_edges = None
            if include_edges and graph_builder:
                slice_edges = self._compute_slice_edges(
                    slice_nodes, graph_builder, slice_time
                )

            stats = self._compute_slice_stats(slice_nodes)

            time_slice = TimeSlice(
                timestamp=slice_time.isoformat(),
                slice_index=i,
                nodes=slice_nodes,
                edges=slice_edges,
                stats=stats,
            )
            time_slices.append(time_slice)

        result = TimeSeriesResult(
            time_slices=time_slices,
            total_slices=len(time_slices),
            time_range={
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
            },
            interval_minutes=interval_minutes,
            metadata={
                'node_count': len(org_nodes),
                'include_edges': include_edges,
                'history_hours': history_hours,
            }
        )

        logger.info(
            f"生成时间切片完成: {len(time_slices)} 个切片, "
            f"间隔 {interval_minutes} 分钟, "
            f"覆盖 {history_hours} 小时"
        )
        return result

    def _compute_slice_nodes(
        self,
        org_nodes: List[Dict[str, Any]],
        history_data: Dict[str, List[Dict[str, Any]]],
        slice_time: datetime,
    ) -> List[Dict[str, Any]]:
        """计算某一时间切片的节点状态"""
        slice_nodes = []

        for org_node in org_nodes:
            node_id = str(org_node.get('id', org_node.get('node_code', '')))
            node_history = history_data.get(node_id, [])

            risk_score, confidence = self._interpolate_risk(
                node_history, slice_time
            )

            risk_level = self._score_to_level(risk_score)
            status_code = self._score_to_status_code(risk_score)
            status = self._code_to_status(status_code)

            node_data = {
                'id': node_id,
                'name': org_node.get('node_name', node_id),
                'node_type': org_node.get('node_type', ''),
                'level': org_node.get('level', 0),
                'risk_score': round(risk_score, 2),
                'risk_level': risk_level,
                'status_code': status_code,
                'status': status,
                'confidence': round(confidence, 4),
                'parent_id': (
                    str(org_node.get('parent_id'))
                    if org_node.get('parent_id') else None
                ),
            }
            slice_nodes.append(node_data)

        return slice_nodes

    def _compute_slice_edges(
        self,
        slice_nodes: List[Dict[str, Any]],
        graph_builder,
        slice_time: datetime,
    ) -> List[Dict[str, Any]]:
        """计算某一时间切片的边（简化版）"""
        edges = []
        node_ids = [n['id'] for n in slice_nodes]
        node_map = {n['id']: n for n in slice_nodes}

        for i in range(len(node_ids)):
            for j in range(i + 1, len(node_ids)):
                source = node_ids[i]
                target = node_ids[j]

                source_node = node_map[source]
                target_node = node_map[target]

                weight = self._calculate_edge_weight(
                    source_node, target_node, slice_time
                )

                if weight > 0:
                    edges.append({
                        'source': source,
                        'target': target,
                        'weight': round(weight, 4),
                        'weight_type': 'composite',
                    })

        return edges

    def _calculate_edge_weight(
        self,
        source_node: Dict[str, Any],
        target_node: Dict[str, Any],
        slice_time: datetime,
    ) -> float:
        """计算边权重（简化版）"""
        risk_correlation = 1.0 - abs(
            source_node['risk_score'] - target_node['risk_score']
        ) / 10.0

        same_parent = (
            source_node.get('parent_id')
            and source_node['parent_id'] == target_node.get('parent_id')
        )
        parent_bonus = 0.3 if same_parent else 0.0

        return min(1.0, risk_correlation * 0.7 + parent_bonus)

    def _interpolate_risk(
        self,
        history: List[Dict[str, Any]],
        target_time: datetime,
    ) -> tuple:
        """
        插值计算某一时间点的风险评分

        使用线性插值，如果目标时间在数据范围外则用最近值。
        """
        if not history:
            return 5.0, 0.3

        target_ts = target_time.timestamp()

        before = None
        after = None

        for record in history:
            record_time = self._parse_time(record.get('timestamp', ''))
            if record_time is None:
                continue

            record_ts = record_time.timestamp()

            if record_ts <= target_ts:
                before = (record_ts, record)
            else:
                after = (record_ts, record)
                break

        if before is None and after is None:
            return 5.0, 0.3

        if before is None:
            risk = after[1].get('risk_score', 5.0)
            confidence = after[1].get('confidence', 0.3)
            return float(risk), float(confidence)

        if after is None:
            risk = before[1].get('risk_score', 5.0)
            confidence = before[1].get('confidence', 0.3)
            return float(risk), float(confidence)

        before_ts, before_rec = before
        after_ts, after_rec = after

        if after_ts == before_ts:
            risk = before_rec.get('risk_score', 5.0)
            confidence = before_rec.get('confidence', 0.3)
            return float(risk), float(confidence)

        ratio = (target_ts - before_ts) / (after_ts - before_ts)

        before_risk = float(before_rec.get('risk_score', 5.0))
        after_risk = float(after_rec.get('risk_score', 5.0))
        interpolated_risk = before_risk + ratio * (after_risk - before_risk)

        before_conf = float(before_rec.get('confidence', 0.3))
        after_conf = float(after_rec.get('confidence', 0.3))
        interpolated_conf = before_conf + ratio * (after_conf - before_conf)

        return float(np.clip(interpolated_risk, 1, 10)), float(interpolated_conf)

    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """解析时间字符串"""
        if not time_str:
            return None

        try:
            return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            try:
                return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                return None

    def _compute_slice_stats(
        self, nodes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """计算切片统计信息"""
        if not nodes:
            return {}

        risk_scores = [n['risk_score'] for n in nodes]
        risk_levels = [n['risk_level'] for n in nodes]

        level_counts = {'高': 0, '中': 0, '低': 0}
        for level in risk_levels:
            if level in level_counts:
                level_counts[level] += 1

        return {
            'total_nodes': len(nodes),
            'avg_risk_score': round(sum(risk_scores) / len(risk_scores), 2),
            'max_risk_score': round(max(risk_scores), 2),
            'min_risk_score': round(min(risk_scores), 2),
            'high_risk_count': level_counts['高'],
            'medium_risk_count': level_counts['中'],
            'low_risk_count': level_counts['低'],
            'high_risk_ratio': round(level_counts['高'] / len(nodes), 4),
        }

    def _score_to_level(self, score: float) -> str:
        """风险评分转等级"""
        if score <= 3:
            return '高'
        elif score <= 7:
            return '中'
        else:
            return '低'

    def _score_to_status_code(self, score: float) -> int:
        """风险评分转状态码"""
        if score <= 2:
            return 4
        elif score <= 3.5:
            return 3
        elif score <= 5:
            return 2
        elif score <= 7:
            return 1
        else:
            return 0

    def _code_to_status(self, code: int) -> str:
        """状态码转状态描述"""
        status_map = {
            0: '正常',
            1: '关注级预警',
            2: '检查级预警',
            3: '紧急级预警',
            4: '故障',
        }
        return status_map.get(code, '未知')

    def generate_mock_history(
        self,
        org_nodes: List[Dict[str, Any]],
        history_hours: int = 24,
        interval_minutes: int = 30,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        生成模拟历史数据

        用于没有真实历史数据时的演示。

        Args:
            org_nodes: 组织节点列表
            history_hours: 历史时长（小时）
            interval_minutes: 数据点间隔（分钟）

        Returns:
            历史数据字典
        """
        history_data = {}
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=history_hours)
        point_count = int(history_hours * 60 / interval_minutes) + 1

        np.random.seed(42)

        for org_node in org_nodes:
            node_id = str(org_node.get('id', org_node.get('node_code', '')))
            node_history = []

            base_risk = np.random.uniform(2, 8)
            amplitude = np.random.uniform(0.5, 2)
            phase = np.random.uniform(0, 2 * np.pi)

            for i in range(point_count):
                point_time = start_time + timedelta(
                    minutes=i * interval_minutes
                )

                t = i / point_count * 2 * np.pi
                risk = base_risk + amplitude * np.sin(t + phase)
                risk += np.random.normal(0, 0.3)
                risk = float(np.clip(risk, 1, 10))

                confidence = float(np.random.uniform(0.5, 0.9))

                node_history.append({
                    'timestamp': point_time.isoformat(),
                    'risk_score': round(risk, 2),
                    'confidence': round(confidence, 4),
                })

            history_data[node_id] = node_history

        logger.info(f"生成模拟历史数据，共 {len(history_data)} 个节点")
        return history_data

    def get_incremental_updates(
        self,
        last_slice_index: int,
        time_series: TimeSeriesResult,
    ) -> List[Dict[str, Any]]:
        """
        获取增量更新

        用于 WebSocket 推送，只返回变化的节点。

        Args:
            last_slice_index: 上一个切片的索引
            time_series: 完整的时间序列结果

        Returns:
            增量更新列表
        """
        updates = []

        if last_slice_index >= len(time_series.time_slices) - 1:
            return updates

        current_slice = time_series.time_slices[last_slice_index]
        next_slice = time_series.time_slices[last_slice_index + 1]

        current_map = {n['id']: n for n in current_slice.nodes}

        for next_node in next_slice.nodes:
            node_id = next_node['id']
            current_node = current_map.get(node_id)

            if (current_node is None
                    or current_node['risk_score'] != next_node['risk_score']
                    or current_node['risk_level'] != next_node['risk_level']):
                updates.append({
                    'type': 'node_update',
                    'data': next_node,
                })

        return updates

    def detect_significant_changes(
        self,
        time_series: TimeSeriesResult,
        threshold: float = 2.0,
    ) -> List[Dict[str, Any]]:
        """
        检测显著变化点

        找出风险评分变化超过阈值的时间点。

        Args:
            time_series: 时间序列结果
            threshold: 变化阈值

        Returns:
            显著变化列表
        """
        changes = []

        for i in range(1, len(time_series.time_slices)):
            prev_slice = time_series.time_slices[i - 1]
            curr_slice = time_series.time_slices[i]

            prev_map = {n['id']: n for n in prev_slice.nodes}

            significant_changes = []
            for curr_node in curr_slice.nodes:
                prev_node = prev_map.get(curr_node['id'])
                if prev_node:
                    delta = abs(
                        curr_node['risk_score'] - prev_node['risk_score']
                    )
                    if delta >= threshold:
                        significant_changes.append({
                            'node_id': curr_node['id'],
                            'node_name': curr_node['name'],
                            'prev_risk': prev_node['risk_score'],
                            'curr_risk': curr_node['risk_score'],
                            'delta': delta,
                            'direction': (
                                'up' if curr_node['risk_score']
                                > prev_node['risk_score']
                                else 'down'
                            ),
                        })

            if significant_changes:
                changes.append({
                    'slice_index': i,
                    'timestamp': curr_slice.timestamp,
                    'change_count': len(significant_changes),
                    'changes': significant_changes,
                })

        return changes
