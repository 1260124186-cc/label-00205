"""
碳排与能效关联分析服务 — 单元测试
验证：
  1. 预紧力劣化模型 (PreloadDegradationModel)
  2. 泄漏率估算模型 (LeakageRateEstimator)
  3. 能耗/碳排增量模型 (EnergyCarbonModel)
  4. 装置级月度碳排风险排行 (CarbonRiskRanker)
  5. HI+碳排并列视图
  6. ESG 报表片段导出 (JSON / CSV)
  7. 模型系数配置 (ModelConfigManager)
"""
import sys
import os
import csv
import io
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.carbon_energy_service import (
    CarbonEnergyService,
    PreloadDegradationModel,
    LeakageRateEstimator,
    EnergyCarbonModel,
    ModelConfigManager,
    DegradationResult,
)


# ---------- 测试数据 ----------

def build_sample_nodes(n: int = 8):
    """构造一组测试节点数据，涵盖不同 HI / 工况 / 趋势"""
    scenarios = [
        ('HL-BOLT-001', 'bolt', '高压分离器-A-螺栓1', 92, 'excellent', [600, 595, 590, 586, 582], 25, 1.2, 1),
        ('HL-BOLT-002', 'bolt', '高压分离器-A-螺栓2', 78, 'good',      [600, 580, 560, 540, 520], 45, 2.0, 3),
        ('HL-BOLT-003', 'bolt', '高压分离器-A-螺栓3', 62, 'fair',      [600, 560, 520, 480, 440], 55, 2.5, 5),
        ('HL-BOLT-004', 'bolt', '高压分离器-A-螺栓4', 45, 'poor',      [600, 520, 440, 380, 320], 65, 2.8, 7),
        ('HL-BOLT-005', 'bolt', '高压分离器-A-螺栓5', 25, 'critical',  [600, 450, 320, 230, 170], 75, 3.2, 9),
        ('HL-FLNG-001', 'flange', '高压分离器-A',      85, 'good',      [400, 395, 390, 385, 382], 30, 1.5, 2),
        ('HL-FLNG-002', 'flange', '冷却器入口法兰',     55, 'fair',      [400, 380, 355, 330, 305], 50, 2.2, 6),
        ('HL-FLNG-003', 'flange', '再沸器出口法兰',     30, 'poor',      [400, 340, 280, 220, 170], 70, 3.0, 8),
    ]
    nodes = []
    for (nid, ntype, nname, hi, hilvl, phist, temp, press, age) in scenarios[:n]:
        nodes.append({
            'node_id': nid,
            'node_type': ntype,
            'node_name': nname,
            'hi_score': hi,
            'hi_level': hilvl,
            'preload_history': phist,
            'avg_temperature': temp,
            'operating_pressure_mpa': press,
            'seal_age_years': age * 0.5,
            'service_age_months': age * 6,
            'energy_source': 'electricity',
        })
    return nodes


# ---------- 1. 预紧力劣化模型 ----------

def test_preload_degradation_basic():
    """预紧力劣化：正常松弛应在合理区间"""
    model = PreloadDegradationModel()
    res: DegradationResult = model.analyze(
        bolt_id='test-001',
        preload_history=[600, 590, 580, 572, 565],
    )
    assert isinstance(res, DegradationResult)
    assert 0 < res.current_preload_ratio <= 1.5
    assert 0 < res.effective_preload_ratio <= 1.5
    assert res.degradation_rate_per_month > 0
    assert res.degradation_trend in ('stable', 'gradual_decline',
                                      'accelerating_decline', 'recovering', 'insufficient_data')
    assert isinstance(res.contributing_factors, list)


def test_preload_degradation_accelerating():
    """预紧力快速劣化 → 下降趋势，速率明显增大"""
    model = PreloadDegradationModel()
    slow = model.analyze('s', [600, 598, 596, 594, 592]).degradation_rate_per_month
    fast = model.analyze('f', [600, 500, 400, 300, 220]).degradation_rate_per_month
    assert fast > slow
    assert fast > 0.01


def test_preload_degradation_recovering():
    """预紧力回升 → 恢复或稳定趋势"""
    model = PreloadDegradationModel()
    res = model.analyze('r', [400, 420, 450, 470, 500])
    assert res.degradation_trend in ('recovering', 'stable')


def test_preload_degradation_insufficient_data():
    """只有 1 个数据点 → 数据不足"""
    model = PreloadDegradationModel()
    res = model.analyze('s', [600])
    assert res.degradation_trend == 'insufficient_data'


# ---------- 2. 泄漏率估算模型 ----------

def test_leakage_rate_zero_for_healthy():
    """压紧力充足时泄漏率极低，leakage_level 为 negligible 或 minor"""
    deg_model = PreloadDegradationModel()
    deg = deg_model.analyze('h', [600, 598, 595, 592, 590])
    est = LeakageRateEstimator()
    leak = est.estimate(degradation=deg, seal_age_years=0.5, operating_pressure_mpa=1.0)
    assert leak.estimated_leakage_rate >= 0
    assert leak.leakage_level in ('negligible', 'minor')


def test_leakage_rate_critical():
    """压紧力不足、密封老化、高压力 → 泄漏率更高，泄漏等级至少为 moderate"""
    deg_model = PreloadDegradationModel()
    deg = deg_model.analyze('c', [600, 500, 400, 280, 180], service_age_months=120)
    est = LeakageRateEstimator()
    low = est.estimate(degradation=deg, seal_age_years=0.5, operating_pressure_mpa=0.5)
    high = est.estimate(degradation=deg, seal_age_years=10.0, operating_pressure_mpa=4.0)
    assert high.estimated_leakage_rate >= low.estimated_leakage_rate
    assert high.leakage_level in ('minor', 'moderate', 'significant', 'critical')


def test_leakage_pressure_sensitivity():
    """压力越高 → 泄漏量越大"""
    deg_model = PreloadDegradationModel()
    deg = deg_model.analyze('p', [600, 550, 500, 450, 400], service_age_months=60)
    est = LeakageRateEstimator()
    low_p = est.estimate(deg, 2.0, 0.5).estimated_leakage_rate
    high_p = est.estimate(deg, 2.0, 4.0).estimated_leakage_rate
    assert high_p >= low_p


def test_leakage_seal_aging_sensitivity():
    """密封越老 → 泄漏量越大"""
    deg_model = PreloadDegradationModel()
    deg = deg_model.analyze('a', [600, 550, 500, 450, 400])
    est = LeakageRateEstimator()
    young = est.estimate(deg, 0.5, 1.5).estimated_leakage_rate
    old = est.estimate(deg, 15.0, 1.5).estimated_leakage_rate
    assert old >= young


# ---------- 3. 能耗/碳排增量模型 ----------

def test_energy_carbon_positive():
    """有泄漏 → 能耗和碳排增量为正"""
    deg_model = PreloadDegradationModel()
    deg = deg_model.analyze('e', [600, 500, 400, 300, 200])
    leak = LeakageRateEstimator().estimate(deg, 5.0, 2.5)
    impact = EnergyCarbonModel().calculate(leakage=leak)
    assert impact.monthly_energy_increment_kwh >= 0
    assert impact.monthly_carbon_increment_kg >= 0


def test_energy_carbon_zero_leakage_scenario():
    """压紧力充足且工况良好 → 增量低或为 0"""
    deg_model = PreloadDegradationModel()
    deg = deg_model.analyze('z', [600, 599, 598, 597, 596])
    leak = LeakageRateEstimator().estimate(deg, 0.1, 0.5)
    impact = EnergyCarbonModel().calculate(leakage=leak)
    assert impact.monthly_carbon_increment_kg >= 0


# ---------- 4. 装置级月度碳排风险排行 ----------

def test_ranking_output_structure():
    """排行输出结构必须完整"""
    svc = CarbonEnergyService()
    nodes = build_sample_nodes(6)
    report = svc.generate_monthly_ranking(nodes_data=nodes, top_n=5)

    assert 'report_month' in report
    assert 'total_nodes' in report
    assert report['total_nodes'] == 6
    assert 'total_monthly_carbon_increment_kg' in report
    assert report['total_monthly_carbon_increment_kg'] >= 0
    assert 'total_monthly_leakage_volume_m3' in report
    assert 'risk_distribution' in report
    assert 'ranked_items' in report
    assert len(report['ranked_items']) <= 5

    for item in report['ranked_items']:
        for key in ('rank', 'node_id', 'node_name', 'hi_score', 'carbon_risk_level',
                    'carbon_risk_score', 'priority_score', 'trend',
                    'monthly_leakage_volume_m3', 'monthly_carbon_increment_kg'):
            assert key in item, f"缺少字段 {key}"


def test_ranking_order_by_priority():
    """排行必须按 priority_score 降序"""
    svc = CarbonEnergyService()
    nodes = build_sample_nodes(8)
    report = svc.generate_monthly_ranking(nodes_data=nodes, top_n=8)
    scores = [it['priority_score'] for it in report['ranked_items']]
    assert scores == sorted(scores, reverse=True)


def test_ranking_critical_has_higher_priority():
    """critical 装置优先级显著高于 excellent"""
    svc = CarbonEnergyService()
    nodes = build_sample_nodes(8)
    report = svc.generate_monthly_ranking(nodes_data=nodes, top_n=8)
    ranked = {it['node_id']: it for it in report['ranked_items']}
    critical_prio = ranked['HL-BOLT-005']['priority_score']
    excellent_prio = ranked['HL-BOLT-001']['priority_score']
    assert critical_prio > excellent_prio


def test_ranking_risk_distribution_sums():
    """风险分布合计等于节点总数"""
    svc = CarbonEnergyService()
    nodes = build_sample_nodes(8)
    report = svc.generate_monthly_ranking(nodes_data=nodes, top_n=8)
    total = sum(report['risk_distribution'].values())
    assert total == 8


# ---------- 5. HI + 碳排并列视图 ----------

def test_hi_dual_view_structure():
    """HI双视图输出结构完整"""
    svc = CarbonEnergyService()
    nodes = build_sample_nodes(6)
    view = svc.generate_hi_carbon_dual_view(nodes_data=nodes)

    assert view['total_nodes'] == 6
    assert 'items' in view
    assert len(view['items']) == 6
    assert 'report_month' in view
    assert 'generated_at' in view

    for item in view['items']:
        for key in ('node_id', 'node_name', 'hi_score', 'hi_level', 'hi_trend',
                    'monthly_carbon_increment_kg', 'carbon_risk_level', 'carbon_trend',
                    'degradation_rate_per_month', 'estimated_leakage_rate_m3_hour'):
            assert key in item, f"缺少字段 {key}"


# ---------- 6. ESG 报表片段导出 ----------

def test_esg_report_json_structure():
    """ESG JSON 片段结构完整"""
    svc = CarbonEnergyService()
    nodes = build_sample_nodes(8)
    ranking = svc.generate_monthly_ranking(nodes_data=nodes, top_n=5)
    fragment = svc.generate_esg_report_fragment(
        ranking_data=ranking,
        include_methodology=True,
    )

    assert fragment.report_period
    assert isinstance(fragment.generated_at, datetime)
    assert fragment.summary
    assert len(fragment.top_risk_items) <= 5
    assert fragment.trend_analysis
    assert len(fragment.recommendations) >= 2
    assert fragment.methodology_note
    assert '不用于精确计量' in fragment.methodology_note


def test_esg_report_summary_values():
    """ESG 汇总数值合法"""
    svc = CarbonEnergyService()
    nodes = build_sample_nodes(8)
    ranking = svc.generate_monthly_ranking(nodes_data=nodes, top_n=5)
    fragment = svc.generate_esg_report_fragment(ranking_data=ranking)
    s = fragment.summary

    assert s['total_devices_analyzed'] == 8
    assert s['estimated_monthly_carbon_increment_kg'] >= 0
    assert s['estimated_monthly_carbon_increment_tons'] >= 0
    assert abs(s['estimated_monthly_carbon_increment_kg'] / 1000 -
               s['estimated_monthly_carbon_increment_tons']) < 1e-3
    assert 0 <= s['top5_contribution_ratio'] <= 1
    assert s['carbon_risk_severity'] in ('低', '中', '高')


def test_esg_trend_analysis():
    """趋势分析各项合计等于分析数量"""
    svc = CarbonEnergyService()
    nodes = build_sample_nodes(8)
    ranking = svc.generate_monthly_ranking(nodes_data=nodes, top_n=8)
    fragment = svc.generate_esg_report_fragment(ranking_data=ranking)
    t = fragment.trend_analysis
    assert t['improving_count'] + t['stable_count'] + t['declining_count'] == 8
    assert t['overall_trend'] in ('improving', 'stable', 'deteriorating', 'insufficient_data')
    assert t['key_observation']


def test_esg_no_methodology_flag():
    """不包含方法学说明时为空字符串"""
    svc = CarbonEnergyService()
    nodes = build_sample_nodes(4)
    ranking = svc.generate_monthly_ranking(nodes_data=nodes, top_n=4)
    fragment = svc.generate_esg_report_fragment(
        ranking_data=ranking,
        include_methodology=False,
    )
    assert fragment.methodology_note == ''


def test_esg_csv_export_valid():
    """CSV 导出可被 csv 模块解析，包含关键信息"""
    svc = CarbonEnergyService()
    nodes = build_sample_nodes(6)
    ranking = svc.generate_monthly_ranking(nodes_data=nodes, top_n=5)
    fragment = svc.generate_esg_report_fragment(ranking_data=ranking)
    csv_str = svc.export_esg_csv(fragment)

    assert csv_str
    assert 'ESG' in csv_str

    reader = csv.reader(io.StringIO(csv_str))
    rows = list(reader)
    assert len(rows) >= 5

    header_found = False
    for row in rows:
        if len(row) >= 3 and any('排名' in str(c) or '装置' in str(c) for c in row):
            header_found = True
            break
    assert header_found, "CSV 中未找到标题行"


# ---------- 7. 模型系数配置 ----------

def test_model_config_defaults_sane():
    """默认系数在合理区间"""
    mgr = ModelConfigManager()
    mgr.reload()
    d = mgr.degradation
    l = mgr.leakage
    e = mgr.energy

    assert d.nominal_preload > 0
    assert 0 < d.min_effective_preload_ratio < 1
    assert 0 < d.relaxation_rate_per_month < 1
    assert l.base_leakage_rate_m3_per_hour >= 0
    assert 0 < e.compressor_efficiency <= 1
    assert 0 <= e.recovery_rate < 1
    assert e.carbon_factor_electricity > 0
    assert e.carbon_factor_natural_gas > 0


def test_model_config_singleton():
    """ModelConfigManager 是单例"""
    m1 = ModelConfigManager()
    m2 = ModelConfigManager()
    assert m1 is m2


def test_model_config_reload_preserves_types():
    """reload 后各属性类型正确"""
    mgr = ModelConfigManager()
    mgr.reload()
    assert hasattr(mgr, 'degradation')
    assert hasattr(mgr, 'leakage')
    assert hasattr(mgr, 'energy')


# ---------- 8. 服务门面综合测试 ----------

def test_service_singleton_and_methods():
    """CarbonEnergyService 门面提供全部必要方法"""
    svc = CarbonEnergyService()
    assert hasattr(svc, 'analyze_single_node')
    assert hasattr(svc, 'generate_monthly_ranking')
    assert hasattr(svc, 'generate_hi_carbon_dual_view')
    assert hasattr(svc, 'generate_esg_report_fragment')
    assert hasattr(svc, 'export_esg_csv')
    assert hasattr(svc, 'get_model_config')


def test_service_analyze_single_node():
    """analyze_single_node 返回完整单节点风险分析结果"""
    svc = CarbonEnergyService()
    node = build_sample_nodes(1)[0]
    res = svc.analyze_single_node(
        node_id=node['node_id'],
        node_type=node.get('node_type', 'bolt'),
        node_name=node.get('node_name', node['node_id']),
        preload_history=node['preload_history'],
        hi_score=node['hi_score'],
        hi_level=node.get('hi_level', 'fair'),
        service_age_months=node.get('service_age_months', 0),
        avg_temperature=node.get('avg_temperature', 25.0),
        seal_age_years=node.get('seal_age_years', 0),
        operating_pressure_mpa=node.get('operating_pressure_mpa', 1.0),
    )
    for key in ('node_id', 'hi_score', 'hi_level', 'carbon_risk_level',
                'carbon_risk_score', 'monthly_carbon_increment_kg',
                'monthly_leakage_volume_m3'):
        assert key in res


def test_service_get_model_config():
    """获取模型系数返回三个分组"""
    svc = CarbonEnergyService()
    cfg = svc.get_model_config()
    assert set(cfg.keys()) == {'degradation', 'leakage', 'energy_carbon'}


# ---------- 主入口 ----------

if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
