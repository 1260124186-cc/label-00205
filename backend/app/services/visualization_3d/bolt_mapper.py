"""
螺栓坐标映射模块

解析螺栓坐标映射表，将螺栓ID映射到3D空间坐标。
支持两种输入方式：
1. 2D展开图 + 螺栓坐标映射表（2D坐标转3D）
2. 直接3D坐标映射表
"""

import csv
import json
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import numpy as np
from io import StringIO


@dataclass
class BoltCoordinate:
    """螺栓坐标数据类"""
    bolt_id: str
    x: float
    y: float
    z: float
    angle: float = 0.0
    radius: float = 0.0
    position_index: int = 0


class BoltCoordinateMapper:
    """
    螺栓坐标映射器

    功能：
    1. 解析螺栓坐标映射表（CSV/JSON）
    2. 2D展开图坐标转换为3D环形坐标
    3. 按角度排序螺栓
    4. 计算螺栓在法兰面上的3D位置
    """

    def __init__(self):
        self.bolt_coordinates: Dict[str, BoltCoordinate] = {}
        self.bolt_order: List[str] = []
        self.flange_radius: float = 0.0
        self.bolt_count: int = 0

    def load_from_csv(self, csv_content: str) -> List[BoltCoordinate]:
        """
        从CSV内容加载螺栓坐标映射表

        CSV格式（2D展开图）：
        bolt_id,position_index,angle_deg,radius_mm
        B001,0,0,100
        B002,1,45,100

        或3D坐标：
        bolt_id,x,y,z
        B001,100,0,50
        """
        reader = csv.DictReader(StringIO(csv_content))
        coordinates = []

        for row in reader:
            bolt_id = row.get('bolt_id') or row.get('螺栓id', '')
            if not bolt_id:
                continue

            if 'x' in row and 'y' in row and 'z' in row:
                coord = BoltCoordinate(
                    bolt_id=bolt_id,
                    x=float(row['x']),
                    y=float(row['y']),
                    z=float(row['z']),
                    position_index=int(row.get('position_index', len(coordinates))),
                )
            elif 'angle_deg' in row or 'angle' in row:
                angle_deg = float(row.get('angle_deg', row.get('angle', 0)))
                radius = float(row.get('radius_mm', row.get('radius', 100)))
                angle_rad = np.radians(angle_deg)
                z_offset = float(row.get('z_offset', row.get('z', 0)))
                coord = BoltCoordinate(
                    bolt_id=bolt_id,
                    x=radius * np.cos(angle_rad),
                    y=radius * np.sin(angle_rad),
                    z=z_offset,
                    angle=angle_deg,
                    radius=radius,
                    position_index=int(row.get('position_index', len(coordinates))),
                )
            else:
                continue

            coordinates.append(coord)

        self._update_internal_data(coordinates)
        return coordinates

    def load_from_json(self, json_content: str) -> List[BoltCoordinate]:
        """
        从JSON内容加载螺栓坐标映射表

        JSON格式：
        [
            {"bolt_id": "B001", "x": 100, "y": 0, "z": 50},
            ...
        ]
        或
        {
            "flange_radius": 100,
            "bolts": [
                {"bolt_id": "B001", "angle_deg": 0, "radius": 90},
                ...
            ]
        }
        """
        data = json.loads(json_content)
        coordinates = []

        if isinstance(data, dict) and 'bolts' in data:
            self.flange_radius = float(data.get('flange_radius', 0))
            bolt_list = data['bolts']
        elif isinstance(data, list):
            bolt_list = data
        else:
            bolt_list = []

        for i, bolt_data in enumerate(bolt_list):
            bolt_id = bolt_data.get('bolt_id', '')
            if not bolt_id:
                continue

            if 'x' in bolt_data and 'y' in bolt_data and 'z' in bolt_data:
                coord = BoltCoordinate(
                    bolt_id=bolt_id,
                    x=float(bolt_data['x']),
                    y=float(bolt_data['y']),
                    z=float(bolt_data['z']),
                    position_index=bolt_data.get('position_index', i),
                )
            elif 'angle_deg' in bolt_data or 'angle' in bolt_data:
                angle_deg = float(bolt_data.get('angle_deg', bolt_data.get('angle', 0)))
                radius = float(bolt_data.get('radius', self.flange_radius * 0.9))
                angle_rad = np.radians(angle_deg)
                z_offset = float(bolt_data.get('z_offset', bolt_data.get('z', 0)))
                coord = BoltCoordinate(
                    bolt_id=bolt_id,
                    x=radius * np.cos(angle_rad),
                    y=radius * np.sin(angle_rad),
                    z=z_offset,
                    angle=angle_deg,
                    radius=radius,
                    position_index=bolt_data.get('position_index', i),
                )
            else:
                continue

            coordinates.append(coord)

        self._update_internal_data(coordinates)
        return coordinates

    def generate_circular_pattern(
        self,
        bolt_ids: List[str],
        radius: float,
        start_angle_deg: float = 0.0,
        z_offset: float = 0.0
    ) -> List[BoltCoordinate]:
        """
        生成环形均匀分布的螺栓坐标

        Args:
            bolt_ids: 螺栓ID列表
            radius: 分布半径
            start_angle_deg: 起始角度（度）
            z_offset: Z轴偏移

        Returns:
            螺栓坐标列表
        """
        coordinates = []
        n = len(bolt_ids)

        for i, bolt_id in enumerate(bolt_ids):
            angle_deg = start_angle_deg + (360.0 / n) * i
            angle_rad = np.radians(angle_deg)
            coord = BoltCoordinate(
                bolt_id=bolt_id,
                x=radius * np.cos(angle_rad),
                y=radius * np.sin(angle_rad),
                z=z_offset,
                angle=angle_deg,
                radius=radius,
                position_index=i,
            )
            coordinates.append(coord)

        self.flange_radius = radius
        self._update_internal_data(coordinates)
        return coordinates

    def _update_internal_data(self, coordinates: List[BoltCoordinate]):
        """更新内部数据结构"""
        self.bolt_coordinates = {c.bolt_id: c for c in coordinates}
        self.bolt_order = [c.bolt_id for c in coordinates]
        self.bolt_count = len(coordinates)

        if coordinates:
            max_radius = max(c.radius for c in coordinates)
            if max_radius > 0:
                self.flange_radius = max_radius
            else:
                self.flange_radius = max(
                    np.sqrt(c.x**2 + c.y**2) for c in coordinates
                )

    def get_bolt_coordinate(self, bolt_id: str) -> Optional[BoltCoordinate]:
        """获取指定螺栓的坐标"""
        return self.bolt_coordinates.get(bolt_id)

    def get_all_coordinates(self) -> List[BoltCoordinate]:
        """获取所有螺栓坐标"""
        return list(self.bolt_coordinates.values())

    def get_bolt_ids(self) -> List[str]:
        """获取所有螺栓ID"""
        return self.bolt_order.copy()

    def get_exploded_positions(
        self,
        explosion_factor: float = 1.0
    ) -> Dict[str, Tuple[float, float, float]]:
        """
        获取爆炸图位置

        Args:
            explosion_factor: 爆炸因子 (0=原始位置, 1=完全爆炸)

        Returns:
            螺栓ID到爆炸位置的映射
        """
        positions = {}
        for bolt_id, coord in self.bolt_coordinates.items():
            direction = np.array([coord.x, coord.y, 0.0])
            norm = np.linalg.norm(direction)
            if norm > 0:
                direction = direction / norm
            offset = direction * 20 * explosion_factor
            positions[bolt_id] = (
                coord.x + offset[0],
                coord.y + offset[1],
                coord.z + 30 * explosion_factor
            )
        return positions

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'flange_radius': self.flange_radius,
            'bolt_count': self.bolt_count,
            'bolts': [
                {
                    'bolt_id': c.bolt_id,
                    'x': c.x,
                    'y': c.y,
                    'z': c.z,
                    'angle': c.angle,
                    'radius': c.radius,
                    'position_index': c.position_index,
                }
                for c in self.bolt_coordinates.values()
            ]
        }
