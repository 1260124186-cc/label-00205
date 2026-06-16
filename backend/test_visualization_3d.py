#!/usr/bin/env python3
"""
3D可视化服务快速验证脚本
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.visualization_3d import Visualization3DService
from app.services.visualization_3d.color_mapper import ColorMapper
from app.services.visualization_3d.bolt_mapper import BoltCoordinateMapper


def test_color_mapper():
    """测试颜色映射器"""
    print("=" * 60)
    print("测试 ColorMapper...")
    mapper = ColorMapper()

    # 测试状态颜色
    status_colors = {}
    for i in range(5):
        color = mapper.get_status_color(i)
        status_colors[i] = mapper.rgb_to_hex(color)
    print(f"  状态颜色: {status_colors}")

    # 测试HI颜色
    hi_colors = {}
    for hi in [0, 25, 50, 75, 100]:
        color = mapper.get_hi_color(hi)
        hi_colors[hi] = mapper.rgb_to_hex(color)
    print(f"  HI渐变色: {hi_colors}")

    # 测试风险颜色
    risk_colors = {}
    for level in ['low', 'medium', 'high', 'critical']:
        color = mapper.get_risk_color(level)
        risk_colors[level] = mapper.rgb_to_hex(color)
    print(f"  风险颜色: {risk_colors}")

    # 测试统一get_color接口
    test_data = {
        'status_code': 2,
        'hi_score': 75,
        'risk_level': 'high'
    }
    for mode in ['status', 'hi', 'risk']:
        color = mapper.get_color(mode, test_data)
        print(f"  get_color('{mode}'): {mapper.rgb_to_hex(color)}")

    print("  ✓ ColorMapper 测试通过")
    return True


def test_bolt_mapper():
    """测试螺栓坐标映射器"""
    print("=" * 60)
    print("测试 BoltCoordinateMapper...")
    mapper = BoltCoordinateMapper()

    # 测试环形分布生成
    bolt_ids = [f"B{i+1:03d}" for i in range(8)]
    mapper.generate_circular_pattern(bolt_ids, radius=100.0)

    coords = []
    for bid in bolt_ids:
        coord = mapper.get_bolt_coordinate(bid)
        if coord:
            coords.append({
                'bolt_id': coord.bolt_id,
                'x': round(coord.x, 2),
                'y': round(coord.y, 2),
                'z': round(coord.z, 2),
                'angle': round(coord.angle, 1) if coord.angle else None
            })

    print(f"  生成了 {len(coords)} 个螺栓坐标")
    print(f"  第一个螺栓: {coords[0]}")
    print(f"  最后一个螺栓: {coords[-1]}")

    # 测试爆炸图位置
    exploded = mapper.get_exploded_positions(explosion_factor=1.0)
    print(f"  爆炸图位置数量: {len(exploded)}")

    # 测试CSV解析
    csv_content = """bolt_id,x,y,z
B001,100,0,0
B002,70.7,70.7,0
B003,0,100,0
B004,-70.7,70.7,0
"""
    csv_coords = mapper.load_from_csv(csv_content)
    print(f"  CSV解析: {len(csv_coords)} 个坐标")

    # 测试JSON解析
    json_content = json.dumps([
        {"bolt_id": "B001", "x": 100, "y": 0, "z": 0},
        {"bolt_id": "B002", "x": 0, "y": 100, "z": 0},
    ])
    json_coords = mapper.load_from_json(json_content)
    print(f"  JSON解析: {len(json_coords)} 个坐标")

    print("  ✓ BoltCoordinateMapper 测试通过")
    return True


def test_visualization_service():
    """测试完整的3D可视化服务"""
    print("=" * 60)
    print("测试 Visualization3DService...")
    service = Visualization3DService()

    # 准备螺栓数据
    bolt_data = {
        "B001": {"status_code": 0, "hi_score": 95.0, "risk_level": "low"},
        "B002": {"status_code": 1, "hi_score": 75.0, "risk_level": "medium"},
        "B003": {"status_code": 2, "hi_score": 55.0, "risk_level": "medium"},
        "B004": {"status_code": 0, "hi_score": 90.0, "risk_level": "low"},
        "B005": {"status_code": 3, "hi_score": 30.0, "risk_level": "high"},
        "B006": {"status_code": 0, "hi_score": 88.0, "risk_level": "low"},
        "B007": {"status_code": 1, "hi_score": 70.0, "risk_level": "medium"},
        "B008": {"status_code": 4, "hi_score": 10.0, "risk_level": "critical"},
    }

    # 创建场景
    print("  创建法兰3D场景...")
    scene = service.create_flange_scene(
        flange_id="test_flange_001",
        bolt_count=8,
        bolt_data=bolt_data,
        visualization_mode="status"
    )
    print(f"  场景ID: {scene['flange_id']}")
    print(f"  螺栓数量: {len(scene['bolt_ids'])}")
    print(f"  可视化模式: {scene['visualization_mode']}")
    print(f"  网格数量: {len(scene['meshes'])}")

    # 测试场景信息
    info = service.get_scene_info("test_flange_001")
    print(f"  场景信息获取: {info is not None}")

    # 测试场景列表
    scenes = service.list_scenes()
    print(f"  场景列表: {scenes}")

    # 测试glTF导出
    print("  导出glTF格式...")
    gltf = service.export_gltf("test_flange_001")
    print(f"    glTF asset: {gltf.get('asset', {})}")
    print(f"    节点数量: {len(gltf.get('nodes', []))}")
    print(f"    网格数量: {len(gltf.get('meshes', []))}")
    print(f"    材质数量: {len(gltf.get('materials', []))}")
    print(f"    ✓ glTF导出成功")

    # 测试Three.js导出
    print("  导出Three.js格式...")
    threejs = service.export_threejs("test_flange_001")
    print(f"    对象类型: {threejs.get('object', {}).get('type')}")
    print(f"    子对象数: {len(threejs.get('object', {}).get('children', []))}")
    vis_mode = threejs.get('object', {}).get('userData', {}).get('visualizationMode')
    print(f"    可视化模式: {vis_mode}")
    print(f"    ✓ Three.js导出成功")

    # 测试Unity导出
    print("  导出Unity数据包...")
    unity = service.export_unity("test_flange_001")
    package_info = unity.get('packageInfo', {})
    print(f"    包名称: {package_info.get('name')}")
    print(f"    法兰ID: {package_info.get('flangeId')}")
    print(f"    可视化模式: {package_info.get('visualizationMode')}")
    print(f"    网格分类数: {len(unity.get('meshes', {}))}")
    print(f"    螺栓列表数: {len(unity.get('bolts', []))}")
    print(f"    ✓ Unity导出成功")

    # 测试导出所有格式
    print("  导出所有格式...")
    all_formats = service.export_all_formats("test_flange_001")
    print(f"    格式数量: {len(all_formats)}")
    print(f"    格式列表: {list(all_formats.keys())}")
    print(f"    ✓ 全部导出成功")

    # 测试增量更新
    print("  测试螺栓状态增量更新...")
    update_data = {
        "B001": {"status_code": 2, "hi_score": 60.0, "risk_level": "high"}
    }
    updated = service.update_bolt_status("test_flange_001", update_data, visualization_mode="hi")
    print(f"    更新后模式: {updated['visualization_mode']}")
    print(f"    B001新HI: {updated['bolt_data']['B001'].get('hi_score')}")
    print(f"    ✓ 增量更新成功")

    # 测试爆炸图
    print("  测试爆炸图位置...")
    explosion = service.get_explosion_positions("test_flange_001", explosion_factor=1.0)
    print(f"    爆炸位置数: {len(explosion)}")
    print(f"    ✓ 爆炸图计算成功")

    # 测试清除场景
    service.clear_scene("test_flange_001")
    remaining = service.list_scenes()
    print(f"  清除后剩余场景数: {len(remaining)}")

    print("  ✓ Visualization3DService 测试通过")
    return True


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("3D 数字孪生可视化服务验证")
    print("=" * 60)

    all_passed = True

    try:
        test_color_mapper()
    except Exception as e:
        print(f"  ✗ ColorMapper 测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    try:
        test_bolt_mapper()
    except Exception as e:
        print(f"  ✗ BoltCoordinateMapper 测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    try:
        test_visualization_service()
    except Exception as e:
        print(f"  ✗ Visualization3DService 测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ 所有测试通过！")
    else:
        print("✗ 部分测试失败")
    print("=" * 60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
