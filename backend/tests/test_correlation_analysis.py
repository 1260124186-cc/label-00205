"""
测试脚本：法兰面关联分析功能验证
验证 Granger 因果检验、因果图、领先螺栓识别、根因定位等功能
"""
import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.models.flange_attention import FlangeAttentionModel


def generate_test_bolt_data(n_bolts=6, n_samples=200, seed=42):
    """
    生成测试用的多螺栓数据
    模拟不均衡松动场景：bolt_0 最先松动，然后传播到其他螺栓
    """
    np.random.seed(seed)
    
    bolt_data = {}
    
    t = np.arange(n_samples)
    
    base_trend = 600 - 0.3 * t
    
    bolt_0_trend = base_trend - 20 * np.sin(t * 0.05)
    bolt_0_noise = np.random.normal(0, 5, n_samples)
    bolt_0 = bolt_0_trend + bolt_0_noise
    bolt_data['bolt_0'] = bolt_0
    
    for i in range(1, n_bolts):
        lag = i * 3
        lagged_trend = np.roll(bolt_0_trend, lag)
        lagged_trend[:lag] = bolt_0_trend[0]
        
        noise_amp = 5 + i * 0.5
        bolt_noise = np.random.normal(0, noise_amp, n_samples)
        
        offset = i * 10
        bolt_i = lagged_trend + offset + bolt_noise
        bolt_data[f'bolt_{i}'] = bolt_i
    
    bolt_data['bolt_3'] = 620 + np.random.normal(0, 3, n_samples)
    
    return bolt_data


def test_granger_causality():
    """测试 Granger 因果检验"""
    print("=" * 60)
    print("测试 1: Granger 因果检验")
    print("=" * 60)
    
    model = FlangeAttentionModel(flange_id='test-flange-001')
    bolt_data = generate_test_bolt_data(n_bolts=4, n_samples=200)
    
    f_stats, p_values = model.granger_causality_test(
        bolt_data=bolt_data,
        max_lag=5,
        significance_level=0.05
    )
    
    print(f"\nF统计量矩阵:")
    bolt_ids = list(bolt_data.keys())
    for i, src in enumerate(bolt_ids):
        row_str = f"  {src} ->: "
        for j, dst in enumerate(bolt_ids):
            if i == j:
                row_str += "   -   "
            else:
                row_str += f"{f_stats[i][j]:6.3f} "
        print(row_str)
    
    print(f"\nP值矩阵:")
    for i, src in enumerate(bolt_ids):
        row_str = f"  {src} ->: "
        for j, dst in enumerate(bolt_ids):
            if i == j:
                row_str += "   -   "
            else:
                row_str += f"{p_values[i][j]:6.4f} "
        print(row_str)
    
    print(f"\n显著因果关系 (p < 0.05):")
    for i, src in enumerate(bolt_ids):
        for j, dst in enumerate(bolt_ids):
            if i != j and p_values[i][j] < 0.05:
                print(f"  {src} -> {dst}: F={f_stats[i][j]:.3f}, p={p_values[i][j]:.4f}")
    
    print("\n✅ Granger 因果检验测试完成\n")
    return f_stats, p_values


def test_causal_graph():
    """测试因果图构建"""
    print("=" * 60)
    print("测试 2: 因果图构建")
    print("=" * 60)
    
    model = FlangeAttentionModel(n_bolts=4, input_size=1)
    bolt_data = generate_test_bolt_data(n_bolts=4, n_samples=200)
    
    causal_graph = model.build_causal_graph(
        bolt_data=bolt_data,
        max_lag=5,
        significance_level=0.05,
        min_correlation=0.3
    )
    
    print(f"\n因果图统计:")
    print(f"  节点数: {causal_graph['node_count']}")
    print(f"  边数: {causal_graph['edge_count']}")
    print(f"  边列表:")
    for edge in causal_graph['edges']:
        print(f"    {edge['source']} -> {edge['target']}: "
              f"相关={edge['correlation']:.3f}, "
              f"因果强度={edge['causal_strength']:.3f}, "
              f"最优滞后={edge['optimal_lag']}, "
              f"p值={edge['p_value']:.4f}")
    
    print(f"\n节点中心性:")
    for node in causal_graph['nodes']:
        print(f"  {node['bolt_id']}: "
              f"出度={node['out_degree']}, "
              f"入度={node['in_degree']}, "
              f"中介中心性={node['betweenness_centrality']:.3f}")
    
    print("\n✅ 因果图构建测试完成\n")
    return causal_graph


def test_leading_bolts():
    """测试领先螺栓识别"""
    print("=" * 60)
    print("测试 3: 领先螺栓识别")
    print("=" * 60)
    
    model = FlangeAttentionModel(n_bolts=4, input_size=1)
    bolt_data = generate_test_bolt_data(n_bolts=4, n_samples=200)
    
    leading_bolts = model.identify_leading_bolts(
        bolt_data=bolt_data,
        max_lag=5
    )
    
    print(f"\n领先螺栓排行:")
    for i, bolt in enumerate(leading_bolts):
        print(f"  第{i+1}名: {bolt['bolt_id']} "
              f"(综合得分={bolt['composite_score']:.3f}, "
              f"出度得分={bolt['out_degree_score']:.3f}, "
              f"因果强度得分={bolt['causal_strength_score']:.3f}, "
              f"趋势领先得分={bolt['trend_lead_score']:.3f})")
    
    print("\n✅ 领先螺栓识别测试完成\n")
    return leading_bolts


def test_propagation_paths():
    """测试传播路径分析"""
    print("=" * 60)
    print("测试 4: 传播路径分析")
    print("=" * 60)
    
    model = FlangeAttentionModel(n_bolts=6, input_size=1)
    bolt_data = generate_test_bolt_data(n_bolts=6, n_samples=200)
    
    source_bolt = 'bolt_0'
    propagation_result = model.analyze_propagation_paths(
        bolt_data=bolt_data,
        source_bolt=source_bolt,
        max_depth=4
    )
    
    print(f"\n从 {source_bolt} 出发的传播路径:")
    print(f"  访问节点数: {propagation_result['visited_count']}")
    print(f"  路径数: {propagation_result['path_count']}")
    
    print(f"\n  主要传播路径:")
    for i, path in enumerate(propagation_result['paths'][:5]):
        path_str = " -> ".join(path['path'])
        print(f"    路径{i+1}: {path_str} (累计强度={path['total_strength']:.3f}, 深度={path['depth']})")
    
    print(f"\n  到达各节点的最短/最强路径:")
    for bid, path_info in propagation_result['node_paths'].items():
        if bid != source_bolt:
            path_str = " -> ".join(path_info['path'])
            print(f"    {bid}: {path_str} (强度={path_info['total_strength']:.3f})")
    
    print("\n✅ 传播路径分析测试完成\n")
    return propagation_result


def test_root_cause_analysis():
    """测试根因螺栓定位"""
    print("=" * 60)
    print("测试 5: 根因螺栓定位")
    print("=" * 60)
    
    model = FlangeAttentionModel(n_bolts=6, input_size=1)
    bolt_data = generate_test_bolt_data(n_bolts=6, n_samples=200)
    
    bolt_statuses = {
        'bolt_0': 2,
        'bolt_1': 2,
        'bolt_2': 1,
        'bolt_3': 0,
        'bolt_4': 1,
        'bolt_5': 2,
    }
    
    bolt_health_indices = {
        'bolt_0': 0.65,
        'bolt_1': 0.70,
        'bolt_2': 0.82,
        'bolt_3': 0.95,
        'bolt_4': 0.85,
        'bolt_5': 0.68,
    }
    
    root_cause_result = model.identify_root_cause_bolt(
        bolt_data=bolt_data,
        bolt_statuses=bolt_statuses,
        bolt_health_indices=bolt_health_indices
    )
    
    print(f"\n根因分析结果:")
    root_cause = root_cause_result['root_cause_bolt']
    print(f"  根因螺栓: {root_cause['bolt_id']}")
    print(f"  综合根因得分: {root_cause['root_cause_score']:.3f}")
    print(f"  出度得分: {root_cause['out_degree_score']:.3f}")
    print(f"  因果强度得分: {root_cause['causal_strength_score']:.3f}")
    print(f"  趋势领先得分: {root_cause['trend_lead_score']:.3f}")
    print(f"  健康状况得分: {root_cause['health_score']:.3f}")
    print(f"  传播距离得分: {root_cause['propagation_score']:.3f}")
    
    print(f"\n  所有螺栓根因得分排行:")
    for i, bolt in enumerate(root_cause_result['ranked_bolts']):
        marker = " ← 根因" if i == 0 else ""
        print(f"    第{i+1}名: {bolt['bolt_id']} (得分={bolt['root_cause_score']:.3f}){marker}")
    
    print(f"\n  多螺栓不均衡松动: {'是' if root_cause_result['is_unbalanced'] else '否'}")
    print(f"  异常螺栓数: {root_cause_result['abnormal_bolt_count']}")
    print(f"  健康螺栓数: {root_cause_result['healthy_bolt_count']}")
    
    print("\n✅ 根因螺栓定位测试完成\n")
    return root_cause_result


def test_root_cause_measures():
    """测试根因推荐措施生成"""
    print("=" * 60)
    print("测试 6: 根因推荐措施生成")
    print("=" * 60)
    
    model = FlangeAttentionModel(n_bolts=6, input_size=1)
    bolt_data = generate_test_bolt_data(n_bolts=6, n_samples=200)
    
    bolt_statuses = {
        'bolt_0': 2,
        'bolt_1': 2,
        'bolt_2': 1,
        'bolt_3': 0,
        'bolt_4': 1,
        'bolt_5': 2,
    }
    
    bolt_health_indices = {
        'bolt_0': 0.65,
        'bolt_1': 0.70,
        'bolt_2': 0.82,
        'bolt_3': 0.95,
        'bolt_4': 0.85,
        'bolt_5': 0.68,
    }
    
    root_cause_result = model.identify_root_cause_bolt(
        bolt_data=bolt_data,
        bolt_statuses=bolt_statuses,
        bolt_health_indices=bolt_health_indices
    )
    
    measures = model.generate_root_cause_measures(
        root_cause_result=root_cause_result,
        flange_id='FL-001'
    )
    
    print(f"\n根因分析推荐措施:")
    print(f"  {measures}")
    
    print("\n✅ 根因推荐措施生成测试完成\n")
    return measures


def test_comprehensive_analysis():
    """测试综合关联分析"""
    print("=" * 60)
    print("测试 7: 综合关联分析（一键调用）")
    print("=" * 60)
    
    model = FlangeAttentionModel(n_bolts=6, input_size=1)
    bolt_data = generate_test_bolt_data(n_bolts=6, n_samples=200)
    
    bolt_ids = list(bolt_data.keys())
    bolt_statuses = {
        'bolt_0': 2,
        'bolt_1': 2,
        'bolt_2': 1,
        'bolt_3': 0,
        'bolt_4': 1,
        'bolt_5': 2,
    }
    bolt_health_indices = {
        'bolt_0': 0.65,
        'bolt_1': 0.70,
        'bolt_2': 0.82,
        'bolt_3': 0.95,
        'bolt_4': 0.85,
        'bolt_5': 0.68,
    }
    
    result = model.comprehensive_correlation_analysis(
        bolt_data=bolt_data,
        bolt_ids=bolt_ids,
        bolt_statuses=bolt_statuses,
        bolt_health_indices=bolt_health_indices,
        max_lag=5,
        significance_level=0.05,
        min_correlation=0.3
    )
    
    print(f"\n综合分析结果摘要:")
    print(f"  correlation_matrix: {len(result['correlation_matrix'])}x{len(result['correlation_matrix'][0])} 矩阵")
    print(f"  causal_graph: {result['causal_graph']['node_count']} 节点, {result['causal_graph']['edge_count']} 边")
    print(f"  leading_bolts: {len(result['leading_bolts'])} 个领先螺栓")
    print(f"  propagation_paths: {result['propagation_paths']['path_count']} 条传播路径")
    print(f"  root_cause_bolt: {result['root_cause_analysis']['root_cause_bolt']['bolt_id']}")
    print(f"  root_cause_measures: {'已生成' if result['root_cause_measures'] else '无'}")
    
    print(f"\n返回字段: {list(result.keys())}")
    
    print("\n✅ 综合关联分析测试完成\n")
    return result


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("法兰面关联分析功能验证")
    print("=" * 60 + "\n")
    
    try:
        test_granger_causality()
        test_causal_graph()
        test_leading_bolts()
        test_propagation_paths()
        test_root_cause_analysis()
        test_root_cause_measures()
        test_comprehensive_analysis()
        
        print("=" * 60)
        print("🎉 所有测试通过！")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
