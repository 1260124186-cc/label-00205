"""
Three.js场景JSON导出器

导出Three.js Object3D JSON格式场景。
可以直接被THREE.ObjectLoader加载使用。
"""

import json
from typing import List, Dict, Tuple, Any, Optional
import numpy as np

from .flange_model import MeshData
from .color_mapper import ColorMapper


class ThreeJSExporter:
    """
    Three.js场景导出器

    生成Three.js兼容的场景JSON格式。
    包含：
    - 几何体数据（BufferGeometry格式）
    - 材质数据（MeshStandardMaterial）
    - 场景层级结构
    - 交互控制配置（旋转、爆炸图参数）
    - 螺栓元数据（状态、HI、风险等）
    """

    def __init__(self):
        self.color_mapper = ColorMapper()

    def export_scene(
        self,
        meshes: List[MeshData],
        bolt_data: Optional[Dict[str, Dict[str, Any]]] = None,
        scene_config: Optional[Dict[str, Any]] = None,
        visualization_mode: str = "status",
    ) -> Dict[str, Any]:
        """
        导出Three.js场景

        Args:
            meshes: 网格数据列表
            bolt_data: 螺栓状态数据
            scene_config: 场景配置
            visualization_mode: 可视化模式 (status/hi/risk)

        Returns:
            Three.js场景JSON
        """
        geometries = []
        materials = []
        objects = []

        for mesh in meshes:
            is_bolt = mesh.user_data.get('type') == 'bolt'
            bolt_id = mesh.user_data.get('bolt_id', '')

            color = mesh.color
            if is_bolt and bolt_data and bolt_id in bolt_data:
                bolt_info = bolt_data[bolt_id]
                color = self.color_mapper.get_color(visualization_mode, bolt_info)
                color = self.color_mapper.rgb_to_normalized(color)

            geo_idx = len(geometries)
            geometries.append(self._create_geometry(mesh))

            mat_idx = len(materials)
            materials.append(self._create_material(mesh, color, is_bolt, bolt_id))

            objects.append(self._create_mesh_object(
                mesh, geo_idx, mat_idx, bolt_data.get(bolt_id) if bolt_data else None
            ))

        scene = {
            "metadata": {
                "version": 4.5,
                "type": "Object",
                "generator": "Bolt Flange Visualization Service",
            },
            "geometries": geometries,
            "materials": materials,
            "object": {
                "type": "Group",
                "name": "FlangeScene",
                "children": objects,
                "position": [0, 0, 0],
                "rotation": [0, 0, 0],
                "scale": [1, 1, 1],
                "visible": True,
                "userData": {
                    "visualizationMode": visualization_mode,
                    "boltCount": sum(1 for m in meshes if m.user_data.get('type') == 'bolt'),
                    "explosionConfig": {
                        "enabled": False,
                        "factor": 0.0,
                        "maxFactor": 1.0,
                        "direction": "radial"
                    },
                    "rotationConfig": {
                        "autoRotate": False,
                        "autoRotateSpeed": 2.0,
                        "enableDamping": True,
                        "dampingFactor": 0.05
                    }
                }
            },
        }

        if scene_config:
            scene["object"]["userData"].update(scene_config)

        return scene

    def export_to_json_string(
        self,
        meshes: List[MeshData],
        bolt_data: Optional[Dict[str, Dict[str, Any]]] = None,
        scene_config: Optional[Dict[str, Any]] = None,
        visualization_mode: str = "status",
    ) -> str:
        """导出为JSON字符串"""
        scene = self.export_scene(meshes, bolt_data, scene_config, visualization_mode)
        return json.dumps(scene, ensure_ascii=False)

    def _create_geometry(self, mesh: MeshData) -> Dict[str, Any]:
        """创建BufferGeometry"""
        vertices = []
        normals = []
        uvs = []

        for face in mesh.faces:
            for idx in face:
                if idx < len(mesh.vertices):
                    vertices.extend(mesh.vertices[idx])
                    if mesh.normals and idx < len(mesh.normals):
                        normals.extend(mesh.normals[idx])
                    if mesh.uvs and idx < len(mesh.uvs):
                        uvs.extend(mesh.uvs[idx])

        data = {
            "position": vertices,
        }
        if normals:
            data["normal"] = normals
        if uvs:
            data["uv"] = uvs

        return {
            "type": "BufferGeometry",
            "name": mesh.name,
            "data": {
                "attributes": {
                    "position": {
                        "itemSize": 3,
                        "type": "Float32Array",
                        "array": vertices,
                        "normalized": False
                    }
                }
            },
            "userData": mesh.user_data
        }

    def _create_material(
        self,
        mesh: MeshData,
        color: Tuple[float, float, float],
        is_bolt: bool,
        bolt_id: str
    ) -> Dict[str, Any]:
        """创建材质"""
        color_hex = int(color[0] * 255) * 65536 + int(color[1] * 255) * 256 + int(color[2] * 255)

        return {
            "type": "MeshStandardMaterial",
            "name": f"mat_{mesh.name}",
            "color": color_hex,
            "roughness": 0.7,
            "metalness": 0.3,
            "side": 2,
            "transparent": is_bolt and False,
            "opacity": 1.0,
            "userData": {
                "isBolt": is_bolt,
                "boltId": bolt_id,
                "originalColor": list(color)
            }
        }

    def _create_mesh_object(
        self,
        mesh: MeshData,
        geometry_idx: int,
        material_idx: int,
        bolt_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建Mesh对象"""
        user_data = dict(mesh.user_data)
        if bolt_data:
            user_data["boltData"] = bolt_data

        return {
            "type": "Mesh",
            "name": mesh.name,
            "geometry": geometry_idx,
            "material": material_idx,
            "position": [0, 0, 0],
            "rotation": [0, 0, 0],
            "scale": [1, 1, 1],
            "visible": True,
            "castShadow": True,
            "receiveShadow": True,
            "userData": user_data
        }

    def create_update_data(
        self,
        bolt_data: Dict[str, Dict[str, Any]],
        visualization_mode: str = "status"
    ) -> Dict[str, Any]:
        """
        创建增量更新数据（用于实时更新螺栓颜色）

        Args:
            bolt_data: 螺栓状态数据
            visualization_mode: 可视化模式

        Returns:
            更新数据
        """
        updates = {}
        for bolt_id, data in bolt_data.items():
            color = self.color_mapper.get_color(visualization_mode, data)
            color_norm = self.color_mapper.rgb_to_normalized(color)
            updates[bolt_id] = {
                "color": list(color_norm),
                "colorHex": self.color_mapper.rgb_to_hex(color),
                "data": data
            }

        return {
            "type": "bolt_status_update",
            "visualizationMode": visualization_mode,
            "timestamp": np.datetime64('now').astype(str),
            "updates": updates
        }
