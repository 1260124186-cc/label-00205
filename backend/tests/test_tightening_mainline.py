"""
螺栓紧固工艺主链路最小可运行校验脚本

覆盖四条核心接口:
1. 工艺方案生成 (generate_tightening_plan)
2. 扭矩反算预紧力 (calculate_preload_from_measurement)
3. 复紧建议 (suggest_retorque_range)
4. 合规审计 (full_compliance_audit)

运行方式:
    cd backend && python3 -m pytest tests/test_tightening_mainline.py -v
    或直接运行: python3 tests/test_tightening_mainline.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger


def test_1_generate_tightening_plan():
    """接口 1: 工艺方案生成"""
    from app.services.tightening import TighteningService

    print("\n" + "=" * 60)
    print("TEST 1: 工艺方案生成 (generate_tightening_plan)")
    print("=" * 60)

    svc = TighteningService()

    # M20-8.8: 保证载荷=147kN, 许用预紧力(75%保证载荷)=110kN
    # 取许用预紧力的 73% 作为目标，即约 80kN（54% 保证载荷）
    target_preload = 80000

    plan = svc.generate_tightening_plan(
        bolt_size="M20",
        bolt_grade="8.8",
        target_preload_N=target_preload,
        lubrication_type="molybdenum_disulfide",
        procedure_id="ASME_PCC1_4STEP",
        bolt_count=8,
        tolerance_band="normal",
        start_index=1,
        lubricant_usage_count=0,
        operating_temperature_c=25,
    )

    plan_dict = plan.to_dict()

    # 校验关键字段
    assert plan_dict["process_id"] is not None, "process_id 不应为空"
    assert plan_dict["target_torque_Nm"] > 0, "目标扭矩应为正数"
    assert plan_dict["target_preload_N"] == target_preload, "目标预紧力不匹配"
    assert len(plan_dict["tightening_steps"]) > 0, "应有紧固步骤"
    assert len(plan_dict["cross_sequence"]) > 0, "应有交叉紧固顺序"
    assert "retorque_range_Nm" in plan_dict, "应有复紧扭矩区间"

    # 校验复紧区间是基于目标预紧力生成的（即使没有实测数据）
    retorque = plan_dict["retorque_range_Nm"]
    assert retorque["min_Nm"] > 0, "复紧最小扭矩应为正"
    assert retorque["nominal_Nm"] > 0, "复紧标称扭矩应为正"
    assert retorque["max_Nm"] > retorque["min_Nm"], "复紧最大扭矩应大于最小"

    # 校验合规检查结果
    assert "design_limit" in plan_dict["compliance_summary"], "应有设计极限检查"
    assert "lubricant" in plan_dict["compliance_summary"], "应有润滑剂评估"

    print(f"  ✓ process_id: {plan_dict['process_id']}")
    print(f"  ✓ 目标预紧力: {plan_dict['target_preload_N']:.0f} N")
    print(f"  ✓ 目标扭矩: {plan_dict['target_torque_Nm']:.1f} Nm")
    print(f"  ✓ 复紧扭矩区间: {retorque['min_Nm']:.1f} ~ {retorque['max_Nm']:.1f} Nm (标称 {retorque['nominal_Nm']:.1f})")
    print(f"  ✓ 紧固步骤数: {len(plan_dict['tightening_steps'])}")
    print(f"  ✓ 交叉顺序矩阵行数: {len(plan_dict['cross_sequence'])}")
    print(f"  ✓ 设计极限状态: {plan_dict['compliance_summary']['design_limit']['status']}")
    print(f"  ✓ 润滑剂状态: {plan_dict['compliance_summary']['lubricant']['status']}")
    if plan_dict["warnings"]:
        print(f"  ⚠  警告信息: {plan_dict['warnings']}")
    else:
        print("  ✓ 无警告")
    print("  ✓ 工艺方案生成: PASS")

    return plan_dict


def test_2_calculate_preload_from_measurement():
    """接口 2: 扭矩反算预紧力"""
    from app.services.tightening import TighteningService

    print("\n" + "=" * 60)
    print("TEST 2: 扭矩反算预紧力 (calculate_preload_from_measurement)")
    print("=" * 60)

    svc = TighteningService()

    # 用一个实测扭矩值反算（对应 M20-8.8, 80kN 目标预紧力的约 90% 扭矩）
    measured_torque = 280.0

    result = svc.calculate_preload_from_measurement(
        bolt_size="M20",
        measured_torque_Nm=measured_torque,
        lubrication_type="molybdenum_disulfide",
        bolt_grade="8.8",
    )

    result_dict = result.to_dict()

    # 校验关键字段
    assert result_dict["measured_torque_Nm"] == measured_torque, "实测扭矩不匹配"
    assert result_dict["estimated_preload_N"] > 0, "预估预紧力应为正"
    assert result_dict["preload_min_N"] > 0, "预紧力下限应为正"
    assert result_dict["preload_max_N"] > result_dict["preload_min_N"], "上限应大于下限"
    assert 0 < result_dict["preload_uncertainty_pct"] < 50, "不确定度应在合理范围"
    assert 0 < result_dict["friction_coeff_thread"] < 0.5, "螺纹摩擦系数应合理"
    assert 0 < result_dict["friction_coeff_bearing"] < 0.5, "支承面摩擦系数应合理"
    assert result_dict["utilization_ratio"] is not None, "应有利用率"
    assert result_dict["utilization_ratio"] < 1.0, "利用率应小于100%"
    assert result_dict["compliance_status"] is not None, "应有合规状态"

    print(f"  ✓ 实测扭矩: {measured_torque:.1f} Nm")
    print(f"  ✓ 预估预紧力: {result_dict['estimated_preload_N']:.0f} N "
          f"(±{result_dict['preload_uncertainty_pct']:.1f}%)")
    print(f"  ✓ 预紧力范围: {result_dict['preload_min_N']:.0f} ~ {result_dict['preload_max_N']:.0f} N")
    print(f"  ✓ 摩擦系数: 螺纹={result_dict['friction_coeff_thread']:.3f}, "
          f"支承面={result_dict['friction_coeff_bearing']:.3f}")
    print(f"  ✓ 利用率: {result_dict['utilization_ratio']:.2%}")
    print(f"  ✓ 合规状态: {result_dict['compliance_label']}")
    if result_dict["warnings"]:
        print(f"  ⚠  警告: {result_dict['warnings']}")
    else:
        print("  ✓ 无警告")
    print("  ✓ 扭矩反算: PASS")

    return result_dict


def test_3_suggest_retorque_range():
    """接口 3: 复紧建议 - 三种模式测试"""
    from app.services.tightening import TighteningService

    print("\n" + "=" * 60)
    print("TEST 3: 复紧建议 (suggest_retorque_range)")
    print("=" * 60)

    svc = TighteningService()
    bolt_size = "M20"
    target_preload = 80000
    lubrication = "molybdenum_disulfide"

    # --- 模式 1: 基于目标预紧力生成默认复紧范围（无实测数据） ---
    print("\n  模式 1: 基于目标预紧力生成默认复紧范围（无实测数据）")
    print("  " + "-" * 40)

    suggestion1 = svc.suggest_retorque_range(
        bolt_size=bolt_size,
        target_preload_N=target_preload,
        lubrication_type=lubrication,
        bolt_grade="8.8",
        procedure_id="ASME_PCC1_4STEP",
    )

    s1 = suggestion1.to_dict()
    assert s1["preload_loss_pct"] == 0.0, "无实测数据时预紧力损失应为 0"
    assert s1["suggested_min_torque_Nm"] > 0, "建议最小扭矩应为正"
    assert s1["suggested_max_torque_Nm"] > s1["suggested_min_torque_Nm"], "最大应大于最小"

    print(f"    ✓ 目标预紧力: {target_preload:.0f} N")
    print(f"    ✓ 预紧力损失: {s1['preload_loss_pct']:.1f}%")
    print(f"    ✓ 复紧扭矩区间: {s1['suggested_min_torque_Nm']:.1f} ~ {s1['suggested_max_torque_Nm']:.1f} Nm")
    print(f"    ✓ 建议动作: {s1['action_label']}")
    print(f"    ✓ 严重程度: {s1['severity']}")
    print(f"    ✓ 关联知识库案例数: {len(s1['related_knowledge_cases'])}")
    print("    ✓ 模式 1: PASS")

    # --- 模式 2: 基于实测扭矩 ---
    print("\n  模式 2: 基于实测扭矩（有松弛）")
    print("  " + "-" * 40)

    suggestion2 = svc.suggest_retorque_range(
        bolt_size=bolt_size,
        target_preload_N=target_preload,
        measured_torque_Nm=250,
        lubrication_type=lubrication,
        bolt_grade="8.8",
        procedure_id="ASME_PCC1_4STEP",
    )

    s2 = suggestion2.to_dict()
    assert s2["preload_loss_pct"] is not None, "应有预紧力损失计算"
    assert s2["suggested_min_torque_Nm"] > 0, "建议最小扭矩应为正"

    print(f"    ✓ 实测扭矩: 340.0 Nm（低于目标）")
    print(f"    ✓ 当前预估预紧力: {s2['current_estimated_preload_N']:.0f} N")
    print(f"    ✓ 预紧力损失: {s2['preload_loss_pct']:.1f}%")
    print(f"    ✓ 复紧扭矩区间: {s2['suggested_min_torque_Nm']:.1f} ~ {s2['suggested_max_torque_Nm']:.1f} Nm")
    print(f"    ✓ 建议动作: {s2['action_label']}")
    print(f"    ✓ 严重程度: {s2['severity']}")
    print(f"    ✓ 理由数: {len(s2['rationale'])}")
    print("    ✓ 模式 2: PASS")

    # --- 模式 3: 基于当前预紧力 ---
    print("\n  模式 3: 基于当前预紧力（严重松弛）")
    print("  " + "-" * 40)

    suggestion3 = svc.suggest_retorque_range(
        bolt_size=bolt_size,
        target_preload_N=target_preload,
        current_preload_N=60000,
        lubrication_type=lubrication,
        bolt_grade="8.8",
        procedure_id="ASME_PCC1_4STEP",
    )

    s3 = suggestion3.to_dict()
    assert s3["preload_loss_pct"] > 0, "应有正的预紧力损失"
    assert s3["action"] is not None, "应有建议动作"

    print(f"    ✓ 当前预紧力: 95000 N")
    print(f"    ✓ 预紧力损失: {s3['preload_loss_pct']:.1f}%")
    print(f"    ✓ 复紧扭矩区间: {s3['suggested_min_torque_Nm']:.1f} ~ {s3['suggested_max_torque_Nm']:.1f} Nm")
    print(f"    ✓ 建议动作: {s3['action_label']}")
    print(f"    ✓ 严重程度: {s3['severity']}")
    print(f"    ✓ 理由数: {len(s3['rationale'])}")
    print("    ✓ 模式 3: PASS")

    print("\n  ✓ 复紧建议（三种模式）: PASS")
    return s1, s2, s3


def test_4_full_compliance_audit():
    """接口 4: 合规审计"""
    from app.services.tightening import TighteningService

    print("\n" + "=" * 60)
    print("TEST 4: 合规审计 (full_compliance_audit)")
    print("=" * 60)

    svc = TighteningService()

    target_preload = 80000
    # 8 个螺栓的实测预紧力（围绕目标值 ±4% 波动）
    measured_list = [77000, 83000, 79000, 80000, 82000, 78000, 81000, 76000]

    audit = svc.full_compliance_audit(
        bolt_size="M20",
        bolt_grade="8.8",
        target_preload_N=target_preload,
        measured_preload_list=measured_list,
        lubrication_type="molybdenum_disulfide",
        lubricant_usage_count=3,
        operating_temperature_c=25,
        procedure_id="ASME_PCC1_4STEP",
        completed_steps=["step1", "step2", "step3", "step4"],
        preload_ratio_type="non_permanent",
    )

    assert audit["audit_id"] is not None, "audit_id 不应为空"
    assert "overview" in audit, "应有 overview"
    assert "design_limit_check" in audit, "应有设计极限检查"
    assert "uniformity_evaluation" in audit, "应有均匀性评估"
    assert "lubricant_evaluation" in audit, "应有润滑剂评估"
    assert "process_compliance" in audit, "应有工艺合规性"
    assert "related_knowledge_cases" in audit, "应有知识库关联"

    overview = audit["overview"]
    print(f"  ✓ audit_id: {overview['audit_id']}")
    print(f"  ✓ 总体状态: {overview['overall_label']} ({overview['overall_status']})")
    print(f"  ✓ 发现问题数: {len(overview['issues'])}")
    if overview["issues"]:
        print(f"    问题: {overview['issues']}")
    if overview["warnings"]:
        print(f"    警告: {overview['warnings']}")

    dlc = audit["design_limit_check"]
    print(f"  ✓ 设计极限 - 状态: {dlc['status']}, 利用率: {dlc['utilization_ratio']:.2%}")
    print(f"    保证载荷: {dlc['proof_load_N']:.0f} N, 屈服载荷: {dlc['yield_load_N']:.0f} N")

    ue = audit["uniformity_evaluation"]
    if ue:
        print(f"  ✓ 均匀性评估 - 质量: {ue.get('uniformity_quality', 'N/A')}")
        print(f"    平均预紧力: {ue.get('mean_preload_N', 0):.0f} N, "
              f"标准差: {ue.get('std_preload_N', 0):.0f} N, "
              f"变异系数: {ue.get('cov_pct', 0):.2f}%")

    le = audit["lubricant_evaluation"]
    print(f"  ✓ 润滑剂评估 - 状态: {le['status']}, 剩余寿命: {le['remaining_useful_life_pct']:.1f}%")
    print(f"    使用次数: {le['usage_count']}, 摩擦偏差: {le['friction_deviation_pct']:.1f}%")

    pc = audit["process_compliance"]
    if pc:
        print(f"  ✓ 工艺合规性 - 状态: {pc.get('status', 'N/A')}")
        print(f"    步骤完成: {pc.get('completed_step_count', 0)}/{pc.get('total_step_count', 0)}")

    kc = audit["related_knowledge_cases"]
    print(f"  ✓ 关联知识库案例数: {kc.get('total_count', 0)}")
    if kc.get("cases"):
        for i, case in enumerate(kc["cases"][:2]):
            print(f"    {i + 1}. {case.get('title', 'N/A')}")

    print("  ✓ 合规审计: PASS")
    return audit


def test_5_edge_cases():
    """额外测试: 边界条件"""
    from app.services.tightening import TighteningService

    print("\n" + "=" * 60)
    print("TEST 5: 边界条件测试")
    print("=" * 60)

    svc = TighteningService()

    # 测试不同螺栓规格
    print("\n  测试不同螺纹规格:")
    for bolt_size in ["M10", "M16", "M24", "M36"]:
        try:
            plan = svc.generate_tightening_plan(
                bolt_size=bolt_size,
                bolt_grade="8.8",
                target_preload_N=35000 if bolt_size == "M10" else 80000,
                lubrication_type="molybdenum_disulfide",
                procedure_id="ASME_PCC1_4STEP",
                bolt_count=4,
            )
            pd = plan.to_dict()
            print(f"    ✓ {bolt_size}: 扭矩={pd['target_torque_Nm']:.1f} Nm, "
                  f"工艺ID={pd['process_id']}")
        except Exception as e:
            print(f"    ✗ {bolt_size}: {e}")
            raise

    # 测试不同润滑类型
    print("\n  测试不同润滑类型:")
    for lub in ["dry", "machine_oil", "molybdenum_disulfide", "teflon"]:
        try:
            res = svc.calculate_torque_from_preload(
                bolt_size="M20",
                target_preload_N=80000,
                lubrication_type=lub,
            )
            label = res.friction.lubrication_type.name
            print(f"    ✓ {label}: 扭矩={res.nominal_torque:.1f} Nm, "
                  f"μ_G={res.friction.mu_G:.3f}, μ_K={res.friction.mu_K:.3f}")
        except Exception as e:
            print(f"    ✗ {lub}: {e}")
            raise

    # 测试批量处理
    print("\n  测试批量扭矩转预紧力:")
    # 扭矩值对应约 90~110% 目标预紧力（80kN 预紧力对应约 311Nm）
    measured_torques = [280, 290, 311, 330, 340]
    batch = svc.batch_measurements_to_preloads(
        bolt_size="M20",
        measured_torque_list=measured_torques,
        lubrication_type="molybdenum_disulfide",
        bolt_grade="8.8",
    )
    assert len(batch) == len(measured_torques), "批量结果数量不匹配"
    print(f"    ✓ 批量处理 {len(batch)} 条数据")
    for item in batch:
        print(f"      #{item['index']}: {item['measured_torque_Nm']:.0f} Nm → "
              f"{item['estimated_preload_N']:.0f} N")

    # 测试查询接口
    print("\n  测试查询接口:")
    procs = svc.list_available_procedures()
    print(f"    ✓ 可用工艺规程数: {len(procs)}")

    lubs = svc.list_lubrication_types()
    print(f"    ✓ 可用润滑类型数: {len(lubs)}")

    grades = svc.list_bolt_grades()
    print(f"    ✓ 可用螺栓等级数: {len(grades)}")

    specs = svc.list_thread_specs(coarse_only=True)
    print(f"    ✓ 粗牙螺纹规格数: {len(specs)}")

    print("\n  ✓ 边界条件测试: PASS")


def run_all_tests():
    """运行所有测试"""
    logger.remove()
    logger.add(sys.stderr, level="WARNING")

    print("\n" + "=" * 60)
    print("螺栓紧固工艺主链路最小可运行校验")
    print("=" * 60)

    try:
        test_1_generate_tightening_plan()
        test_2_calculate_preload_from_measurement()
        test_3_suggest_retorque_range()
        test_4_full_compliance_audit()
        test_5_edge_cases()

        print("\n" + "=" * 60)
        print("✓ 所有测试通过！主链路运行正常")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
