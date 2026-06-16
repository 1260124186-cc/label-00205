"""
3D可视化服务主类

整合法兰模型生成、螺栓坐标映射、颜色映射和多格式导出功能。
提供统一的API接口供外部调用。
"""

from typing import List, Dict, Tuple, Optional, Any
from loguru import logger

from .color_mapper import ColorMapper, VisualizationMode
from .bolt_mapper import BoltCoordinateMapper
from .flange_model import FlangeModelGenerator, MeshData
from .gltf_exporter import GLTFExporter
from .threejs_exporter import ThreeJSExporter
from .unity_exporter import UnityExporter


class Visualization3DService:
    """
    3D数字孪生可视化服务

    核心功能：
    1. 法兰3D模型生成（程序化建模）
    2. 螺栓坐标映射（支持2D展开图+坐标表、3D坐标表、环形自动分布）
    3. 状态/健康度/风险颜色映射
    4. 多格式导出：glTF、Three.js场景JSON、Unity数据包
    5. 爆炸图、旋转等交互配置
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_components()
        return cls._instance

    def _init_components(self):
        """初始化组件"""
        self.color_mapper = ColorMapper()
        self.bolt_mapper = BoltCoordinateMapper()
        self.model_generator = FlangeModelGenerator()
        self.gltf_exporter = GLTFExporter()
        self.threejs_exporter = ThreeJSExporter()
        self.unity_exporter = UnityExporter()
        self._scenes: Dict[str, Dict[str, Any]] = {}

    def create_flange_scene(
        self,
        flange_id: str,
        bolt_ids: Optional[List[str]] = None,
        bolt_count: int = 8,
        bolt_data: Optional[Dict[str, Dict[str, Any]]] = None,
        bolt_coordinate_csv: Optional[str] = None,
        bolt_coordinate_json: Optional[str] = None,
        flange_params: Optional[Dict[str, Any]] = None,
        visualization_mode: str = "status",
    ) -> Dict[str, Any]:
        """
        创建法兰3D场景

        Args:
            flange_id: 法兰ID
            bolt_ids: 螺栓ID列表
            bolt_count: 螺栓数量（bolt_ids为空时使用）
            bolt_data: 螺栓状态数据 {bolt_id: {status_code, hi_score, risk_level, ...}}
            bolt_coordinate_csv: 螺栓坐标映射表CSV内容
            bolt_coordinate_json: 螺栓坐标映射表JSON内容
            flange_params: 法兰模型参数
            visualization_mode: 可视化模式 (status/hi/risk)

        Returns:
            场景数据字典
        """
        logger.info(f"创建法兰3D场景: {flange_id}, 模式: {visualization_mode}")

        # 设置法兰参数
        if flange_params:
            self.model_generator.set_parameters(**flange_params)

        # 加载螺栓坐标
        if bolt_coordinate_csv:
            coords = self.bolt_mapper.load_from_csv(bolt_coordinate_csv)
            bolt_ids = [c.bolt_id for c in coords]
        elif bolt_coordinate_json:
            coords = self.bolt_mapper.load_from_json(bolt_coordinate_json)
            bolt_ids = [c.bolt_id for c in coords]
        elif bolt_ids:
            self.bolt_mapper.generate_circular_pattern(
                bolt_ids,
                self.model_generator.bolt_pcd_radius
            )
        else:
            bolt_ids = [f"B{i+1:03d}" for i in range(bolt_count)]
            self.bolt_mapper.generate_circular_pattern(
                bolt_ids,
                self.model_generator.bolt_pcd_radius
            )

        # 生成模型
        bolt_positions = {}
        for bolt_id in bolt_ids:
            coord = self.bolt_mapper.get_bolt_coordinate(bolt_id)
            if coord:
                bolt_positions[bolt_id] = (coord.x, coord.y, coord.z)

        flange_body = self.model_generator.generate_flange_body()
        pipe = self.model_generator.generate_pipe()
        bolts = self.model_generator.generate_all_bolts(bolt_positions)

        all_meshes = [flange_body, pipe] + bolts

        # 准备螺栓状态数据
        status_data = {}
        for bolt_id in bolt_ids:
            data = bolt_data.get(bolt_id, {}) if bolt_data else {}
            color = self.color_mapper.get_color(visualization_mode, data)
            status_data[bolt_id] = {
                **data,
                'color_rgb': self.color_mapper.rgb_to_normalized(color),
                'color_hex': self.color_mapper.rgb_to_hex(color),
            }

        scene_data = {
            'flange_id': flange_id,
            'visualization_mode': visualization_mode,
            'meshes': all_meshes,
            'bolt_ids': bolt_ids,
            'bolt_data': status_data,
            'bolt_positions': bolt_positions,
            'flange_params': {
                'flange_outer_radius': self.model_generator.flange_outer_radius,
                'flange_inner_radius': self.model_generator.flange_inner_radius,
                'flange_thickness': self.model_generator.flange_thickness,
                'bolt_pcd_radius': self.model_generator.bolt_pcd_radius,
                'bolt_radius': self.model_generator.bolt_radius,
                'bolt_count': len(bolt_ids),
            }
        }

        self._scenes[flange_id] = scene_data
        return scene_data

    def export_gltf(
        self,
        flange_id: str,
        scene_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        导出glTF格式

        Args:
            flange_id: 法兰ID
            scene_data: 场景数据（可选，为空则从缓存获取）

        Returns:
            glTF数据
        """
        if scene_data is None:
            scene_data = self._scenes.get(flange_id)
            if scene_data is None:
                raise ValueError(f"场景 {flange_id} 不存在，请先调用 create_flange_scene")

        return self.gltf_exporter.export(
            scene_data['meshes'],
            scene_name=f"Flange_{flange_id}",
            bolt_status_data=scene_data['bolt_data']
        )

    def export_threejs(
        self,
        flange_id: str,
        scene_data: Optional[Dict[str, Any]] = None,
        scene_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        导出Three.js场景JSON

        Args:
            flange_id: 法兰ID
            scene_data: 场景数据（可选）
            scene_config: 场景配置（可选）

        Returns:
            Three.js场景数据
        """
        if scene_data is None:
            scene_data = self._scenes.get(flange_id)
            if scene_data is None:
                raise ValueError(f"场景 {flange_id} 不存在，请先调用 create_flange_scene")

        return self.threejs_exporter.export_scene(
            scene_data['meshes'],
            bolt_data=scene_data['bolt_data'],
            scene_config=scene_config,
            visualization_mode=scene_data['visualization_mode']
        )

    def export_unity(
        self,
        flange_id: str,
        scene_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        导出Unity数据包

        Args:
            flange_id: 法兰ID
            scene_data: 场景数据（可选）

        Returns:
            Unity数据包
        """
        if scene_data is None:
            scene_data = self._scenes.get(flange_id)
            if scene_data is None:
                raise ValueError(f"场景 {flange_id} 不存在，请先调用 create_flange_scene")

        return self.unity_exporter.export_package(
            scene_data['meshes'],
            bolt_data=scene_data['bolt_data'],
            flange_id=flange_id,
            visualization_mode=scene_data['visualization_mode']
        )

    def export_all_formats(
        self,
        flange_id: str,
        scene_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        导出所有格式

        Args:
            flange_id: 法兰ID
            scene_data: 场景数据（可选）

        Returns:
            包含所有格式的字典
        """
        return {
            'gltf': self.export_gltf(flange_id, scene_data),
            'threejs': self.export_threejs(flange_id, scene_data),
            'unity': self.export_unity(flange_id, scene_data),
        }

    def update_bolt_status(
        self,
        flange_id: str,
        bolt_data: Dict[str, Dict[str, Any]],
        visualization_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        更新螺栓状态（增量更新）

        Args:
            flange_id: 法兰ID
            bolt_data: 螺栓状态数据
            visualization_mode: 可视化模式（可选，不填则使用原模式）

        Returns:
            更新后的场景数据
        """
        scene_data = self._scenes.get(flange_id)
        if scene_data is None:
            raise ValueError(f"场景 {flange_id} 不存在，请先调用 create_flange_scene")

        if visualization_mode:
            scene_data['visualization_mode'] = visualization_mode

        mode = scene_data['visualization_mode']

        for bolt_id, data in bolt_data.items():
            if bolt_id in scene_data['bolt_data']:
                scene_data['bolt_data'][bolt_id].update(data)
            else:
                scene_data['bolt_data'][bolt_id] = data

            color = self.color_mapper.get_color(mode, scene_data['bolt_data'][bolt_id])
            scene_data['bolt_data'][bolt_id]['color_rgb'] = self.color_mapper.rgb_to_normalized(color)
            scene_data['bolt_data'][bolt_id]['color_hex'] = self.color_mapper.rgb_to_hex(color)

        self._scenes[flange_id] = scene_data
        return scene_data

    def get_explosion_positions(
        self,
        flange_id: str,
        explosion_factor: float = 1.0
    ) -> Dict[str, Tuple[float, float, float]]:
        """
        获取爆炸图位置

        Args:
            flange_id: 法兰ID
            explosion_factor: 爆炸因子 (0-1)

        Returns:
            螺栓ID到爆炸位置的映射
        """
        return self.bolt_mapper.get_exploded_positions(explosion_factor)

    def get_scene_info(self, flange_id: str) -> Optional[Dict[str, Any]]:
        """获取场景信息"""
        scene = self._scenes.get(flange_id)
        if not scene:
            return None
        return {
            'flange_id': scene['flange_id'],
            'visualization_mode': scene['visualization_mode'],
            'bolt_count': len(scene['bolt_ids']),
            'bolt_ids': scene['bolt_ids'],
            'flange_params': scene['flange_params'],
        }

    def list_scenes(self) -> List[str]:
        """列出所有场景"""
        return list(self._scenes.keys())

    def clear_scene(self, flange_id: str):
        """清除场景缓存"""
        if flange_id in self._scenes:
            del self._scenes[flange_id]

    def clear_all_scenes(self):
        """清除所有场景缓存"""
        self._scenes.clear()
