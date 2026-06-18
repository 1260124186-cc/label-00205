"""
跨装置风险传播与聚合分析 - 单元测试

测试内容:
1. 装置关联图构建
2. 关联权重计算（同管线、同振动源、同班次、共故障、物理邻接）
3. 风险传播算法（BFS带深度衰减）
4. 风险上调系数计算
5. 风险热力矩阵构建
6. 传播路径查找
7. 服务层集成测试
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDeviceAssociationGraph:
    """装置关联图测试"""

    def setup_method(self):
        """初始化测试数据"""
        from app.models.risk_propagation import (
            DeviceAssociationGraph,
            AssociationWeightConfig,
        )

        self.weight_config = AssociationWeightConfig()
        self.graph = DeviceAssociationGraph(weight_config=self.weight_config)

        # 添加测试装置
        self.devices = [
            {
                'device_id': 'unit_001',
                'name': '装置A',
                'pipeline_id': 'PL_001',
                'vibration_source': 'VS_001',
                'shifts': ['day', 'night'],
                'latitude': 30.0,
                'longitude': 120.0,
            },
            {
                'device_id': 'unit_002',
                'name': '装置B',
                'pipeline_id': 'PL_001',
                'vibration_source': 'VS_001',
                'shifts': ['day'],
                'latitude': 30.01,
                'longitude': 120.01,
            },
            {
                'device_id': 'unit_003',
                'name': '装置C',
                'pipeline_id': 'PL_002',
                'vibration_source': 'VS_002',
                'shifts': ['night'],
                'latitude': 31.0,
                'longitude': 121.0,
            },
            {
                'device_id': 'unit_004',
                'name': '装置D',
                'pipeline_id': 'PL_002',
                'vibration_source': 'VS_002',
                'shifts': ['day', 'night'],
                'latitude': 31.01,
                'longitude': 121.01,
            },
        ]

        for device in self.devices:
            self.graph.add_device(device['device_id'], device)

    def test_add_device(self):
        """测试添加装置节点"""
        assert len(self.graph.devices) == 4
        assert 'unit_001' in self.graph.devices
        assert self.graph.devices['unit_001']['name'] == '装置A'

    def test_same_pipeline_association(self):
        """测试同管线关联权重计算"""
        edge_count = self.graph.update_associations()

        assoc = self.graph.get_association('unit_001', 'unit_002')
        assert assoc is not None
        assert assoc.same_pipeline_weight == 1.0
        assert 'same_pipeline' in assoc.association_types

        assoc = self.graph.get_association('unit_001', 'unit_003')
        assert assoc is not None
        assert assoc.same_pipeline_weight == 0.0

    def test_same_vibration_source_association(self):
        """测试同振动源关联权重计算"""
        self.graph.update_associations()

        assoc = self.graph.get_association('unit_001', 'unit_002')
        assert assoc.same_vibration_source_weight == 1.0
        assert 'same_vibration_source' in assoc.association_types

        assoc = self.graph.get_association('unit_001', 'unit_003')
        assert assoc.same_vibration_source_weight == 0.0

    def test_same_shift_association(self):
        """测试同班次关联权重计算（Jaccard相似度）"""
        self.graph.update_associations()

        # unit_001: ['day', 'night'], unit_002: ['day']
        # Jaccard = 1/2 = 0.5
        assoc = self.graph.get_association('unit_001', 'unit_002')
        assert abs(assoc.same_shift_weight - 0.5) < 0.01
        assert 'same_shift' in assoc.association_types

        # unit_001: ['day', 'night'], unit_003: ['night']
        # Jaccard = 1/2 = 0.5
        assoc = self.graph.get_association('unit_001', 'unit_003')
        assert abs(assoc.same_shift_weight - 0.5) < 0.01

        # unit_001: ['day', 'night'], unit_004: ['day', 'night']
        # Jaccard = 2/2 = 1.0
        assoc = self.graph.get_association('unit_001', 'unit_004')
        assert abs(assoc.same_shift_weight - 1.0) < 0.01

    def test_physical_association(self):
        """测试物理邻接关联权重计算（距离衰减）"""
        self.graph.update_associations()

        # unit_001和unit_002距离很近（约1.57公里），权重应该较高
        assoc_1_2 = self.graph.get_association('unit_001', 'unit_002')
        # unit_001和unit_003距离很远（约157公里），权重应该很低
        assoc_1_3 = self.graph.get_association('unit_001', 'unit_003')

        assert assoc_1_2.physical_weight > assoc_1_3.physical_weight
        assert assoc_1_2.physical_weight > 0.0
        assert 'physical' in assoc_1_2.association_types

    def test_co_fault_association(self):
        """测试共故障关联权重计算"""
        # 记录共故障事件
        self.graph.record_co_fault(['unit_001', 'unit_002', 'unit_003'])
        self.graph.record_co_fault(['unit_001', 'unit_002'])

        self.graph.update_associations()

        # unit_001和unit_002共故障2次，权重应该较高
        assoc_1_2 = self.graph.get_association('unit_001', 'unit_002')
        # unit_001和unit_003共故障1次，权重应该较低
        assoc_1_3 = self.graph.get_association('unit_001', 'unit_003')
        # unit_002和unit_004没有共故障，权重为0
        assoc_2_4 = self.graph.get_association('unit_002', 'unit_004')

        assert assoc_1_2.co_fault_weight > assoc_1_3.co_fault_weight
        assert assoc_2_4.co_fault_weight == 0.0
        assert 'co_fault' in assoc_1_2.association_types

    def test_composite_weight(self):
        """测试综合权重计算"""
        self.graph.record_co_fault(['unit_001', 'unit_002'])
        edge_count = self.graph.update_associations()

        # 4个装置应该有 4*3/2 = 6 条边
        assert edge_count == 6

        # unit_001和unit_002有多个关联维度，综合权重应该最高
        assoc_1_2 = self.graph.get_association('unit_001', 'unit_002')
        assoc_1_3 = self.graph.get_association('unit_001', 'unit_003')

        assert assoc_1_2.composite_weight > assoc_1_3.composite_weight
        assert 0.0 <= assoc_1_2.composite_weight <= 1.0

    def test_weight_normalization(self):
        """测试权重配置自动归一化"""
        from app.models.risk_propagation import AssociationWeightConfig

        # 权重总和不等于1.0，应该自动归一化
        config = AssociationWeightConfig(
            same_pipeline=3.0,
            same_vibration_source=2.5,
            same_shift=0.5,
            co_fault=2.0,
            physical=1.0,
        )

        total = (config.same_pipeline + config.same_vibration_source +
                 config.same_shift + config.co_fault + config.physical)

        # 归一化后总和应该约等于1.0
        assert abs(total - 1.0) < 0.01

    def test_get_connected_devices(self):
        """测试获取关联装置列表"""
        self.graph.record_co_fault(['unit_001', 'unit_002'])
        self.graph.update_associations()

        # 获取所有关联装置
        connected = self.graph.get_connected_devices('unit_001')
        assert len(connected) == 3

        # 使用权重过滤
        connected_filtered = self.graph.get_connected_devices('unit_001', min_weight=0.5)
        assert len(connected_filtered) <= 3

        # 验证按权重降序排列
        weights = [assoc.composite_weight for _, assoc in connected]
        assert weights == sorted(weights, reverse=True)


class TestRiskPropagator:
    """风险传播分析器测试"""

    def setup_method(self):
        """初始化测试数据"""
        from app.models.risk_propagation import (
            DeviceAssociationGraph,
            RiskPropagator,
            AssociationWeightConfig,
        )

        self.weight_config = AssociationWeightConfig()
        self.graph = DeviceAssociationGraph(weight_config=self.weight_config)
        self.propagator = RiskPropagator(association_graph=self.graph)

        # 添加测试装置（链式结构：A-B-C-D）
        devices = [
            {
                'device_id': 'unit_001',
                'name': '装置A',
                'pipeline_id': 'PL_001',
                'vibration_source': 'VS_001',
                'shifts': ['day'],
                'latitude': 30.0,
                'longitude': 120.0,
            },
            {
                'device_id': 'unit_002',
                'name': '装置B',
                'pipeline_id': 'PL_001',
                'vibration_source': 'VS_001',
                'shifts': ['day'],
                'latitude': 30.001,
                'longitude': 120.001,
            },
            {
                'device_id': 'unit_003',
                'name': '装置C',
                'pipeline_id': 'PL_001',
                'vibration_source': 'VS_001',
                'shifts': ['day'],
                'latitude': 30.002,
                'longitude': 120.002,
            },
            {
                'device_id': 'unit_004',
                'name': '装置D',
                'pipeline_id': 'PL_001',
                'vibration_source': 'VS_001',
                'shifts': ['day'],
                'latitude': 30.003,
                'longitude': 120.003,
            },
        ]

        for device in devices:
            self.graph.add_device(device['device_id'], device)

        # 记录共故障，增强关联
        self.graph.record_co_fault(['unit_001', 'unit_002'])
        self.graph.record_co_fault(['unit_002', 'unit_003'])
        self.graph.record_co_fault(['unit_003', 'unit_004'])

        self.graph.update_associations()

        # 初始风险评分（1-10，值越低风险越高）
        self.risk_scores = {
            'unit_001': 8.0,
            'unit_002': 7.0,
            'unit_003': 6.0,
            'unit_004': 5.0,
        }

    def test_risk_propagation_basic(self):
        """测试基本风险传播计算"""
        result = self.propagator.calculate_risk_propagation(
            source_device_id='unit_001',
            source_flange_id='flange_001',
            current_risk_scores=self.risk_scores,
            source_risk_score=2.0,  # 紧急预警
        )

        # 源装置本身不应包含在结果中
        assert 'unit_001' not in result

        # 其他装置都应该有风险上调结果
        assert 'unit_002' in result
        assert 'unit_003' in result
        assert 'unit_004' in result

        # 验证上调系数大于1.0（表示风险被上调）
        for device_id, upreg_result in result.items():
            assert upreg_result.upregulation_coefficient >= 1.0
            assert upreg_result.adjusted_risk_score <= upreg_result.original_risk_score

    def test_propagation_depth_decay(self):
        """测试传播深度衰减"""
        result = self.propagator.calculate_risk_propagation(
            source_device_id='unit_001',
            source_flange_id='flange_001',
            current_risk_scores=self.risk_scores,
            source_risk_score=2.0,
        )

        # 距离越远，上调系数应该越小
        coef_2 = result['unit_002'].upregulation_coefficient  # 深度1
        coef_3 = result['unit_003'].upregulation_coefficient  # 深度2
        coef_4 = result['unit_004'].upregulation_coefficient  # 深度3

        assert coef_2 >= coef_3 >= coef_4

    def test_risk_level_upgrade(self):
        """测试风险等级升级判断"""
        # 中风险阈值是4-7，高风险是1-3
        # unit_004原始风险评分是5.0（中风险），如果传播后降到3.0以下，则升级为高风险
        result = self.propagator.calculate_risk_propagation(
            source_device_id='unit_001',
            source_flange_id='flange_001',
            current_risk_scores=self.risk_scores,
            source_risk_score=1.0,  # 最高级风险
        )

        # 至少有一个装置的风险等级应该被升级
        has_upgrade = any(
            r.risk_level_upgraded for r in result.values()
        )
        assert has_upgrade

    def test_propagation_summary(self):
        """测试传播汇总信息"""
        result = self.propagator.calculate_risk_propagation(
            source_device_id='unit_001',
            source_flange_id='flange_001',
            current_risk_scores=self.risk_scores,
            source_risk_score=2.0,
        )

        summary = self.propagator.get_propagation_summary(
            source_device_id='unit_001',
            current_risk_scores=self.risk_scores,
        )

        assert 'affected_device_count' in summary
        assert 'level_upgraded_devices' in summary
        assert summary['affected_device_count'] == 3
        assert isinstance(summary['level_upgraded_devices'], list)

    def test_risk_heatmap_matrix(self):
        """测试风险热力矩阵构建"""
        device_ids = ['unit_001', 'unit_002', 'unit_003', 'unit_004']

        heatmap = self.propagator.build_risk_heatmap_matrix(
            device_ids=device_ids,
            risk_scores=self.risk_scores,
            highlight_source='unit_001',
        )

        # 验证矩阵维度
        assert len(heatmap.matrix) == 4
        assert len(heatmap.matrix[0]) == 4
        assert len(heatmap.association_matrix) == 4
        assert len(heatmap.association_matrix[0]) == 4

        # 验证高亮掩码
        assert heatmap.highlight_source == 'unit_001'
        assert len(heatmap.highlight_mask) == 4

        # 验证对角线为0（不包含自身）
        for i in range(4):
            assert heatmap.matrix[i][i] == 0.0

    def test_propagation_paths(self):
        """测试传播路径查找"""
        paths = self.propagator.find_propagation_paths(
            source_device_id='unit_001',
            target_device_id='unit_004',
            top_k=5,
            max_depth=4,
        )

        assert len(paths) > 0

        # 验证路径从源到目标
        for path in paths:
            assert path.path[0] == 'unit_001'
            assert path.path[-1] == 'unit_004'
            assert len(path.path) >= 2
            assert path.depth == len(path.path) - 1
            assert path.total_weight > 0.0

    def test_all_propagation_paths(self):
        """测试不指定目标时查找所有高权重路径"""
        paths = self.propagator.find_propagation_paths(
            source_device_id='unit_001',
            top_k=10,
            max_depth=3,
        )

        assert len(paths) > 0
        assert len(paths) <= 10

        for path in paths:
            assert path.path[0] == 'unit_001'
            assert path.depth <= 3

    def test_source_risk_severity(self):
        """测试源风险严重性对传播强度的影响"""
        # 源风险低（评分高）
        result_low = self.propagator.calculate_risk_propagation(
            source_device_id='unit_001',
            source_flange_id='flange_001',
            current_risk_scores=self.risk_scores,
            source_risk_score=8.0,  # 低风险
        )

        # 源风险高（评分低）
        result_high = self.propagator.calculate_risk_propagation(
            source_device_id='unit_001',
            source_flange_id='flange_001',
            current_risk_scores=self.risk_scores,
            source_risk_score=1.0,  # 高风险
        )

        # 高风险源应该导致更高的上调系数
        coef_high = result_high['unit_002'].upregulation_coefficient
        coef_low = result_low['unit_002'].upregulation_coefficient

        assert coef_high >= coef_low


class TestRiskPropagationService:
    """风险传播服务层测试"""

    def setup_method(self):
        """初始化测试数据"""
        from app.services.risk_visualization import RiskPropagationService

        self.service = RiskPropagationService()

        self.test_devices = [
            {
                'id': 'unit_001',
                'name': '装置A',
                'pipeline_id': 'PL_001',
                'vibration_source': 'VS_001',
                'shifts': ['day', 'night'],
                'latitude': 30.0,
                'longitude': 120.0,
            },
            {
                'id': 'unit_002',
                'name': '装置B',
                'pipeline_id': 'PL_001',
                'vibration_source': 'VS_001',
                'shifts': ['day'],
                'latitude': 30.01,
                'longitude': 120.01,
            },
            {
                'id': 'unit_003',
                'name': '装置C',
                'pipeline_id': 'PL_002',
                'vibration_source': 'VS_002',
                'shifts': ['night'],
                'latitude': 30.02,
                'longitude': 120.02,
            },
        ]

        self.co_fault_history = [
            {
                'device_ids': ['unit_001', 'unit_002'],
                'timestamp': '2024-01-01 10:00:00',
            },
        ]

    def test_update_association_graph(self):
        """测试更新关联图"""
        result = self.service.update_association_graph(
            devices=self.test_devices,
            co_fault_history=self.co_fault_history,
        )

        assert result['device_count'] == 3
        assert result['edge_count'] == 3
        assert 'last_update_time' in result
        assert 'weight_config' in result

    def test_calculate_risk_propagation(self):
        """测试风险传播计算服务"""
        # 先更新关联图
        self.service.update_association_graph(
            devices=self.test_devices,
            co_fault_history=self.co_fault_history,
        )

        risk_scores = {
            'unit_001': 8.0,
            'unit_002': 7.0,
            'unit_003': 6.0,
        }

        result = self.service.calculate_risk_propagation(
            source_device_id='unit_001',
            source_flange_id='flange_001',
            current_risk_scores=risk_scores,
            source_risk_score=2.0,
        )

        assert result['source_device_id'] == 'unit_001'
        assert result['source_flange_id'] == 'flange_001'
        assert 'results' in result
        assert 'summary' in result
        assert len(result['results']) == 2  # unit_002和unit_003

    def test_get_risk_heatmap_matrix(self):
        """测试获取风险热力矩阵"""
        self.service.update_association_graph(devices=self.test_devices)

        risk_scores = {
            'unit_001': 8.0,
            'unit_002': 7.0,
            'unit_003': 6.0,
        }

        result = self.service.get_risk_heatmap_matrix(
            device_ids=['unit_001', 'unit_002', 'unit_003'],
            risk_scores=risk_scores,
            highlight_source='unit_001',
        )

        assert 'device_ids' in result
        assert 'matrix' in result
        assert 'highlight_source' in result
        assert result['highlight_source'] == 'unit_001'
        assert len(result['matrix']) == 3

    def test_get_propagation_paths(self):
        """测试获取传播路径"""
        self.service.update_association_graph(
            devices=self.test_devices,
            co_fault_history=self.co_fault_history,
        )

        paths = self.service.get_propagation_paths(
            source_device_id='unit_001',
            target_device_id='unit_003',
            top_k=5,
        )

        assert isinstance(paths, list)
        assert len(paths) > 0

        for path in paths:
            assert 'path' in path
            assert 'total_weight' in path
            assert path['path'][0] == 'unit_001'
            assert path['path'][-1] == 'unit_003'

    def test_get_association_graph_data(self):
        """测试获取关联图数据"""
        self.service.update_association_graph(devices=self.test_devices)

        data = self.service.get_association_graph_data()

        assert 'nodes' in data
        assert 'edges' in data
        assert data['node_count'] == 3
        assert data['edge_count'] == 3

    def test_get_device_associations(self):
        """测试获取装置关联列表"""
        self.service.update_association_graph(
            devices=self.test_devices,
            co_fault_history=self.co_fault_history,
        )

        associations = self.service.get_device_associations(
            device_id='unit_001',
            min_weight=0.1,
        )

        assert isinstance(associations, list)
        assert len(associations) == 2

        for assoc in associations:
            assert 'device_id' in assoc
            assert 'composite_weight' in assoc
            assert 'weights' in assoc

    def test_record_co_fault_event(self):
        """测试记录共故障事件"""
        self.service.update_association_graph(devices=self.test_devices)

        # 记录前的关联
        before = self.service.get_device_associations(device_id='unit_003')
        before_weight = next(
            (a['composite_weight'] for a in before if a['device_id'] == 'unit_001'),
            0.0
        )

        # 记录共故障事件
        self.service.record_co_fault_event(
            device_ids=['unit_001', 'unit_003'],
            timestamp=datetime.now().isoformat(),
        )

        # 记录后的关联（权重应该增加）
        after = self.service.get_device_associations(device_id='unit_003')
        after_weight = next(
            (a['composite_weight'] for a in after if a['device_id'] == 'unit_001'),
            0.0
        )

        assert after_weight >= before_weight

    def test_get_statistics(self):
        """测试获取统计信息"""
        self.service.update_association_graph(devices=self.test_devices)

        stats = self.service.get_statistics()

        assert stats['device_count'] == 3
        assert stats['edge_count'] == 3
        assert 'update_count' in stats
        assert 'last_update_time' in stats
        assert 'weight_config' in stats


class TestPropagationGraphBuilderExtensions:
    """图构建器扩展功能测试"""

    def test_same_pipeline_weight_calculation(self):
        """测试同管线权重计算"""
        from app.services.risk_visualization import PropagationGraphBuilder

        builder = PropagationGraphBuilder()

        org_nodes = [
            {
                'id': 'unit_001',
                'node_name': '装置A',
                'node_type': 'unit',
                'extra_info': {
                    'pipeline_id': 'PL_001',
                },
            },
            {
                'id': 'unit_002',
                'node_name': '装置B',
                'node_type': 'unit',
                'extra_info': {
                    'pipeline_id': 'PL_001',
                },
            },
            {
                'id': 'unit_003',
                'node_name': '装置C',
                'node_type': 'unit',
                'extra_info': {
                    'pipeline_id': 'PL_002',
                },
            },
        ]

        prediction_data = {
            'unit_001': {'risk_score': 5.0, 'risk_level': '中'},
            'unit_002': {'risk_score': 5.0, 'risk_level': '中'},
            'unit_003': {'risk_score': 5.0, 'risk_level': '中'},
        }

        graph = builder.build_graph(
            org_nodes=org_nodes,
            prediction_data=prediction_data,
            graph_type='composite',
            include_levels=['unit'],
        )

        # 检查同管线权重
        for edge in graph.edges:
            if (edge.source == 'unit_001' and edge.target == 'unit_002') or \
               (edge.source == 'unit_002' and edge.target == 'unit_001'):
                assert edge.same_pipeline_weight == 1.0
                assert 'same_pipeline' in edge.association_types
            if (edge.source == 'unit_001' and edge.target == 'unit_003') or \
               (edge.source == 'unit_003' and edge.target == 'unit_001'):
                assert edge.same_pipeline_weight == 0.0

    def test_same_vibration_weight_calculation(self):
        """测试同振动源权重计算"""
        from app.services.risk_visualization import PropagationGraphBuilder

        builder = PropagationGraphBuilder()

        org_nodes = [
            {
                'id': 'unit_001',
                'node_name': '装置A',
                'node_type': 'unit',
                'extra_info': {
                    'vibration_source': 'VS_001',
                },
            },
            {
                'id': 'unit_002',
                'node_name': '装置B',
                'node_type': 'unit',
                'extra_info': {
                    'vibration_source': 'VS_001',
                },
            },
            {
                'id': 'unit_003',
                'node_name': '装置C',
                'node_type': 'unit',
                'extra_info': {
                    'vibration_source': 'VS_002',
                },
            },
        ]

        prediction_data = {
            'unit_001': {'risk_score': 5.0, 'risk_level': '中'},
            'unit_002': {'risk_score': 5.0, 'risk_level': '中'},
            'unit_003': {'risk_score': 5.0, 'risk_level': '中'},
        }

        graph = builder.build_graph(
            org_nodes=org_nodes,
            prediction_data=prediction_data,
            graph_type='composite',
            include_levels=['unit'],
        )

        for edge in graph.edges:
            if (edge.source == 'unit_001' and edge.target == 'unit_002') or \
               (edge.source == 'unit_002' and edge.target == 'unit_001'):
                assert edge.same_vibration_weight == 1.0
                assert 'same_vibration' in edge.association_types

    def test_same_shift_weight_calculation(self):
        """测试同班次权重计算（Jaccard相似度）"""
        from app.services.risk_visualization import PropagationGraphBuilder

        builder = PropagationGraphBuilder()

        org_nodes = [
            {
                'id': 'unit_001',
                'node_name': '装置A',
                'node_type': 'unit',
                'extra_info': {
                    'shifts': ['day', 'night'],
                },
            },
            {
                'id': 'unit_002',
                'node_name': '装置B',
                'node_type': 'unit',
                'extra_info': {
                    'shifts': ['day'],
                },
            },
            {
                'id': 'unit_003',
                'node_name': '装置C',
                'node_type': 'unit',
                'extra_info': {
                    'shifts': ['night'],
                },
            },
        ]

        prediction_data = {
            'unit_001': {'risk_score': 5.0, 'risk_level': '中'},
            'unit_002': {'risk_score': 5.0, 'risk_level': '中'},
            'unit_003': {'risk_score': 5.0, 'risk_level': '中'},
        }

        graph = builder.build_graph(
            org_nodes=org_nodes,
            prediction_data=prediction_data,
            graph_type='composite',
            include_levels=['unit'],
        )

        for edge in graph.edges:
            if (edge.source == 'unit_001' and edge.target == 'unit_002') or \
               (edge.source == 'unit_002' and edge.target == 'unit_001'):
                # Jaccard相似度: |{day}| / |{day, night}| = 1/2 = 0.5
                assert abs(edge.same_shift_weight - 0.5) < 0.01
                assert 'same_shift' in edge.association_types


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
