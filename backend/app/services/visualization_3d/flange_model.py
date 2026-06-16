"""
法兰3D模型生成器

程序化生成法兰的3D几何模型，包括：
- 法兰盘主体（圆柱/圆环）
- 螺栓孔
- 管道连接部分
- 螺栓mesh

生成的模型数据可用于导出glTF、Three.js场景或Unity数据包。
"""

from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
import numpy as np


@dataclass
class MeshData:
    """网格数据"""
    name: str
    vertices: List[List[float]] = field(default_factory=list)
    normals: List[List[float]] = field(default_factory=list)
    uvs: List[List[float]] = field(default_factory=list)
    faces: List[List[int]] = field(default_factory=list)
    color: Tuple[float, float, float] = (0.8, 0.8, 0.8)
    material: str = "default"
    user_data: Dict[str, Any] = field(default_factory=dict)


class FlangeModelGenerator:
    """
    法兰3D模型生成器

    程序化生成法兰的各个组件mesh。
    支持自定义尺寸参数，生成的网格数据可直接用于导出。
    """

    def __init__(self):
        self.flange_outer_radius: float = 150.0
        self.flange_inner_radius: float = 80.0
        self.flange_thickness: float = 30.0
        self.bolt_hole_radius: float = 12.0
        self.bolt_radius: float = 10.0
        self.bolt_height: float = 25.0
        self.bolt_pcd_radius: float = 120.0
        self.pipe_radius: float = 75.0
        self.pipe_length: float = 100.0
        self.segments: int = 48
        self.bolt_segments: int = 16

    def set_parameters(
        self,
        flange_outer_radius: Optional[float] = None,
        flange_inner_radius: Optional[float] = None,
        flange_thickness: Optional[float] = None,
        bolt_hole_radius: Optional[float] = None,
        bolt_radius: Optional[float] = None,
        bolt_height: Optional[float] = None,
        bolt_pcd_radius: Optional[float] = None,
        pipe_radius: Optional[float] = None,
        pipe_length: Optional[float] = None,
        segments: Optional[int] = None,
    ):
        """设置法兰模型参数"""
        if flange_outer_radius is not None:
            self.flange_outer_radius = flange_outer_radius
        if flange_inner_radius is not None:
            self.flange_inner_radius = flange_inner_radius
        if flange_thickness is not None:
            self.flange_thickness = flange_thickness
        if bolt_hole_radius is not None:
            self.bolt_hole_radius = bolt_hole_radius
        if bolt_radius is not None:
            self.bolt_radius = bolt_radius
        if bolt_height is not None:
            self.bolt_height = bolt_height
        if bolt_pcd_radius is not None:
            self.bolt_pcd_radius = bolt_pcd_radius
        if pipe_radius is not None:
            self.pipe_radius = pipe_radius
        if pipe_length is not None:
            self.pipe_length = pipe_length
        if segments is not None:
            self.segments = segments

    def generate_flange_body(self) -> MeshData:
        """生成法兰盘主体（带内孔的圆柱）"""
        mesh = MeshData(name="flange_body", color=(0.75, 0.75, 0.78))
        self._add_torus_cylinder(
            mesh,
            self.flange_inner_radius,
            self.flange_outer_radius,
            self.flange_thickness,
            self.segments
        )
        return mesh

    def generate_pipe(self) -> MeshData:
        """生成连接管道"""
        mesh = MeshData(name="pipe", color=(0.7, 0.72, 0.75))
        self._add_cylinder(
            mesh,
            self.pipe_radius,
            self.pipe_length,
            self.segments,
            z_offset=-self.pipe_length
        )
        return mesh

    def generate_bolt(self, bolt_id: str, x: float, y: float, z: float) -> MeshData:
        """
        生成单个螺栓mesh

        Args:
            bolt_id: 螺栓ID
            x, y, z: 螺栓位置

        Returns:
            螺栓网格数据
        """
        mesh = MeshData(
            name=f"bolt_{bolt_id}",
            color=(0.6, 0.6, 0.65),
            user_data={"bolt_id": bolt_id, "type": "bolt"}
        )

        head_height = self.bolt_height * 0.4
        shank_height = self.bolt_height * 0.6
        head_radius = self.bolt_radius * 1.3

        # 螺栓头（六角形近似为圆柱）
        self._add_cylinder(
            mesh,
            head_radius,
            head_height,
            self.bolt_segments,
            x_offset=x,
            y_offset=y,
            z_offset=z + shank_height
        )

        # 螺栓杆
        self._add_cylinder(
            mesh,
            self.bolt_radius,
            shank_height,
            self.bolt_segments,
            x_offset=x,
            y_offset=y,
            z_offset=z
        )

        return mesh

    def generate_all_bolts(self, bolt_positions: Dict[str, Tuple[float, float, float]]) -> List[MeshData]:
        """
        生成所有螺栓mesh

        Args:
            bolt_positions: 螺栓ID到位置的映射

        Returns:
            螺栓网格列表
        """
        bolts = []
        for bolt_id, (x, y, z) in bolt_positions.items():
            bolt_mesh = self.generate_bolt(bolt_id, x, y, z)
            bolts.append(bolt_mesh)
        return bolts

    def generate_bolt_holes(self, bolt_count: int) -> List[Tuple[float, float, float]]:
        """
        生成螺栓孔位置

        Args:
            bolt_count: 螺栓数量

        Returns:
            螺栓孔位置列表
        """
        positions = []
        for i in range(bolt_count):
            angle = 2 * np.pi * i / bolt_count
            x = self.bolt_pcd_radius * np.cos(angle)
            y = self.bolt_pcd_radius * np.sin(angle)
            z = 0.0
            positions.append((x, y, z))
        return positions

    def generate_complete_flange(
        self,
        bolt_ids: Optional[List[str]] = None,
        bolt_count: int = 8
    ) -> Dict[str, Any]:
        """
        生成完整的法兰模型（含所有螺栓）

        Args:
            bolt_ids: 螺栓ID列表（可选，为空则自动生成）
            bolt_count: 螺栓数量（bolt_ids为空时使用）

        Returns:
            完整模型数据字典
        """
        if bolt_ids is None:
            bolt_ids = [f"B{i+1:03d}" for i in range(bolt_count)]
        else:
            bolt_count = len(bolt_ids)

        hole_positions = self.generate_bolt_holes(bolt_count)
        bolt_positions = {
            bolt_id: (pos[0], pos[1], self.flange_thickness / 2)
            for bolt_id, pos in zip(bolt_ids, hole_positions)
        }

        flange_body = self.generate_flange_body()
        pipe = self.generate_pipe()
        bolts = self.generate_all_bolts(bolt_positions)

        return {
            'flange_body': flange_body,
            'pipe': pipe,
            'bolts': bolts,
            'bolt_positions': bolt_positions,
            'bolt_ids': bolt_ids,
            'parameters': {
                'flange_outer_radius': self.flange_outer_radius,
                'flange_inner_radius': self.flange_inner_radius,
                'flange_thickness': self.flange_thickness,
                'bolt_pcd_radius': self.bolt_pcd_radius,
                'bolt_radius': self.bolt_radius,
                'bolt_count': bolt_count,
            }
        }

    def _add_cylinder(
        self,
        mesh: MeshData,
        radius: float,
        height: float,
        segments: int,
        x_offset: float = 0.0,
        y_offset: float = 0.0,
        z_offset: float = 0.0
    ):
        """添加圆柱网格"""
        base_idx = len(mesh.vertices)

        # 底面圆心
        mesh.vertices.append([x_offset, y_offset, z_offset])
        mesh.normals.append([0, 0, -1])
        mesh.uvs.append([0.5, 0.5])

        # 顶面圆心
        mesh.vertices.append([x_offset, y_offset, z_offset + height])
        mesh.normals.append([0, 0, 1])
        mesh.uvs.append([0.5, 0.5])

        # 侧面顶点
        for i in range(segments):
            angle = 2 * np.pi * i / segments
            cos_a = np.cos(angle)
            sin_a = np.sin(angle)

            # 底侧面顶点
            mesh.vertices.append([
                x_offset + radius * cos_a,
                y_offset + radius * sin_a,
                z_offset
            ])
            mesh.normals.append([cos_a, sin_a, 0])
            mesh.uvs.append([i / segments, 0])

            # 顶侧面顶点
            mesh.vertices.append([
                x_offset + radius * cos_a,
                y_offset + radius * sin_a,
                z_offset + height
            ])
            mesh.normals.append([cos_a, sin_a, 0])
            mesh.uvs.append([i / segments, 1])

        # 底面
        for i in range(segments):
            next_i = (i + 1) % segments
            mesh.faces.append([0, base_idx + 2 + next_i * 2, base_idx + 2 + i * 2])

        # 顶面
        for i in range(segments):
            next_i = (i + 1) % segments
            mesh.faces.append([1, base_idx + 2 + i * 2 + 1, base_idx + 2 + next_i * 2 + 1])

        # 侧面
        for i in range(segments):
            next_i = (i + 1) % segments
            bottom_curr = base_idx + 2 + i * 2
            bottom_next = base_idx + 2 + next_i * 2
            top_curr = bottom_curr + 1
            top_next = bottom_next + 1
            mesh.faces.append([bottom_curr, bottom_next, top_next])
            mesh.faces.append([bottom_curr, top_next, top_curr])

    def _add_torus_cylinder(
        self,
        mesh: MeshData,
        inner_radius: float,
        outer_radius: float,
        height: float,
        segments: int
    ):
        """添加环形圆柱（带内孔的圆盘）"""
        base_idx = len(mesh.vertices)

        # 生成顶点
        for i in range(segments):
            angle = 2 * np.pi * i / segments
            cos_a = np.cos(angle)
            sin_a = np.sin(angle)

            # 底部内圈
            mesh.vertices.append([inner_radius * cos_a, inner_radius * sin_a, 0])
            mesh.normals.append([0, 0, -1])
            mesh.uvs.append([0.2 + 0.3 * cos_a, 0.2 + 0.3 * sin_a])

            # 底部外圈
            mesh.vertices.append([outer_radius * cos_a, outer_radius * sin_a, 0])
            mesh.normals.append([0, 0, -1])
            mesh.uvs.append([0.5 + 0.5 * cos_a, 0.5 + 0.5 * sin_a])

            # 顶部内圈
            mesh.vertices.append([inner_radius * cos_a, inner_radius * sin_a, height])
            mesh.normals.append([0, 0, 1])
            mesh.uvs.append([0.2 + 0.3 * cos_a, 0.2 + 0.3 * sin_a])

            # 顶部外圈
            mesh.vertices.append([outer_radius * cos_a, outer_radius * sin_a, height])
            mesh.normals.append([0, 0, 1])
            mesh.uvs.append([0.5 + 0.5 * cos_a, 0.5 + 0.5 * sin_a])

        # 底面
        for i in range(segments):
            next_i = (i + 1) % segments
            inner_curr = base_idx + i * 4
            inner_next = base_idx + next_i * 4
            outer_curr = inner_curr + 1
            outer_next = inner_next + 1
            mesh.faces.append([inner_curr, outer_curr, outer_next])
            mesh.faces.append([inner_curr, outer_next, inner_next])

        # 顶面
        for i in range(segments):
            next_i = (i + 1) % segments
            inner_curr = base_idx + i * 4 + 2
            inner_next = base_idx + next_i * 4 + 2
            outer_curr = inner_curr + 1
            outer_next = inner_next + 1
            mesh.faces.append([inner_curr, outer_next, outer_curr])
            mesh.faces.append([inner_curr, inner_next, outer_next])

        # 外侧面
        for i in range(segments):
            next_i = (i + 1) % segments
            bottom_curr = base_idx + i * 4 + 1
            bottom_next = base_idx + next_i * 4 + 1
            top_curr = bottom_curr + 2
            top_next = bottom_next + 2
            mesh.faces.append([bottom_curr, bottom_next, top_next])
            mesh.faces.append([bottom_curr, top_next, top_curr])

        # 内侧面
        for i in range(segments):
            next_i = (i + 1) % segments
            bottom_curr = base_idx + i * 4
            bottom_next = base_idx + next_i * 4
            top_curr = bottom_curr + 2
            top_next = bottom_next + 2
            mesh.faces.append([bottom_curr, top_next, bottom_next])
            mesh.faces.append([bottom_curr, top_curr, top_next])

    def compute_bolt_positions_from_pcd(
        self,
        bolt_ids: List[str],
        pcd_radius: Optional[float] = None,
        start_angle_deg: float = 0.0
    ) -> Dict[str, Tuple[float, float, float]]:
        """
        根据节圆直径计算螺栓位置

        Args:
            bolt_ids: 螺栓ID列表
            pcd_radius: 节圆半径，默认使用bolt_pcd_radius
            start_angle_deg: 起始角度

        Returns:
            螺栓ID到位置的映射
        """
        if pcd_radius is None:
            pcd_radius = self.bolt_pcd_radius

        positions = {}
        n = len(bolt_ids)
        start_rad = np.radians(start_angle_deg)

        for i, bolt_id in enumerate(bolt_ids):
            angle = start_rad + 2 * np.pi * i / n
            x = pcd_radius * np.cos(angle)
            y = pcd_radius * np.sin(angle)
            z = self.flange_thickness / 2
            positions[bolt_id] = (x, y, z)

        return positions
