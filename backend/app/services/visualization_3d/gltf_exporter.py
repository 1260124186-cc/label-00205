"""
glTF格式导出器

将3D场景导出为glTF 2.0格式（JSON-based）。
glTF是Khronos Group定义的3D模型格式，被广泛支持（Three.js、Unity、Unreal等）。
"""

import json
from typing import List, Dict, Tuple, Any, Optional
import numpy as np

from .flange_model import MeshData


class GLTFExporter:
    """
    glTF格式导出器

    生成符合glTF 2.0规范的JSON文件。
    支持：
    - 多个mesh
    - 顶点颜色（通过COLOR_0属性）
    - 基础材质
    - 节点层级
    """

    def __init__(self):
        self._buffer_views = []
        self._accessors = []
        self._meshes = []
        self._nodes = []
        self._materials = []
        self._binary_data = bytearray()

    def export(
        self,
        meshes: List[MeshData],
        scene_name: str = "Scene",
        bolt_status_data: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        导出glTF场景

        Args:
            meshes: 网格数据列表
            scene_name: 场景名称
            bolt_status_data: 螺栓状态数据，用于设置顶点颜色

        Returns:
            glTF JSON数据
        """
        self._reset()

        self._create_materials(meshes, bolt_status_data)

        scene_node_indices = []
        for i, mesh in enumerate(meshes):
            node_idx = self._add_mesh_node(mesh, i, bolt_status_data)
            scene_node_indices.append(node_idx)

        gltf = {
            "asset": {
                "version": "2.0",
                "generator": "Bolt Flange Visualization Service",
                "copyright": "Digital Twin Visualization"
            },
            "scene": 0,
            "scenes": [
                {
                    "name": scene_name,
                    "nodes": scene_node_indices
                }
            ],
            "nodes": self._nodes,
            "meshes": self._meshes,
            "materials": self._materials,
            "buffers": [
                {
                    "uri": "data:application/octet-stream;base64,",
                    "byteLength": len(self._binary_data)
                }
            ],
            "bufferViews": self._buffer_views,
            "accessors": self._accessors,
        }

        return gltf

    def export_to_json_string(
        self,
        meshes: List[MeshData],
        scene_name: str = "Scene",
        bolt_status_data: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> str:
        """导出为JSON字符串"""
        gltf_data = self.export(meshes, scene_name, bolt_status_data)
        return json.dumps(gltf_data, ensure_ascii=False)

    def _reset(self):
        """重置内部状态"""
        self._buffer_views = []
        self._accessors = []
        self._meshes = []
        self._nodes = []
        self._materials = []
        self._binary_data = bytearray()

    def _create_materials(
        self,
        meshes: List[MeshData],
        bolt_status_data: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        """创建材质"""
        for i, mesh in enumerate(meshes):
            color = mesh.color
            if bolt_status_data and mesh.user_data.get('type') == 'bolt':
                bolt_id = mesh.user_data.get('bolt_id', '')
                status = bolt_status_data.get(bolt_id, {})
                color = self._get_status_color(status, color)

            material = {
                "name": f"material_{i}",
                "pbrMetallicRoughness": {
                    "baseColorFactor": [color[0], color[1], color[2], 1.0],
                    "metallicFactor": 0.3,
                    "roughnessFactor": 0.7
                },
                "doubleSided": True
            }
            self._materials.append(material)

    def _get_status_color(
        self,
        status_data: Dict[str, Any],
        default_color: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        """根据状态数据获取颜色"""
        if 'color_rgb' in status_data:
            return status_data['color_rgb']
        if 'status_code' in status_data:
            colors = [
                (0.3, 0.69, 0.31),
                (1.0, 0.76, 0.03),
                (1.0, 0.6, 0.0),
                (0.96, 0.26, 0.21),
                (0.61, 0.15, 0.69)
            ]
            idx = min(status_data['status_code'], len(colors) - 1)
            return colors[idx]
        return default_color

    def _add_mesh_node(
        self,
        mesh: MeshData,
        material_index: int,
        bolt_status_data: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> int:
        """添加网格节点"""
        mesh_idx = len(self._meshes)
        node_idx = len(self._nodes)

        self._add_mesh_geometry(mesh, material_index, bolt_status_data)

        node = {
            "name": mesh.name,
            "mesh": mesh_idx,
            "translation": [0, 0, 0],
            "rotation": [0, 0, 0, 1],
            "scale": [1, 1, 1]
        }
        if mesh.user_data:
            node["extras"] = mesh.user_data

        self._nodes.append(node)
        return node_idx

    def _add_mesh_geometry(
        self,
        mesh: MeshData,
        material_index: int,
        bolt_status_data: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        """添加网格几何体"""
        vertices = np.array(mesh.vertices, dtype=np.float32)
        normals = np.array(mesh.normals, dtype=np.float32) if mesh.normals else None
        uvs = np.array(mesh.uvs, dtype=np.float32) if mesh.uvs else None
        faces = np.array(mesh.faces, dtype=np.uint16)

        # 顶点位置
        pos_buf_offset = len(self._binary_data)
        pos_data = vertices.flatten().tobytes()
        self._binary_data.extend(pos_data)
        pos_buf_view_idx = len(self._buffer_views)
        self._buffer_views.append({
            "buffer": 0,
            "byteOffset": pos_buf_offset,
            "byteLength": len(pos_data),
            "target": 34962
        })

        min_pos = vertices.min(axis=0).tolist()
        max_pos = vertices.max(axis=0).tolist()
        pos_accessor_idx = len(self._accessors)
        self._accessors.append({
            "bufferView": pos_buf_view_idx,
            "componentType": 5126,
            "count": len(vertices),
            "type": "VEC3",
            "min": min_pos,
            "max": max_pos
        })

        # 法线
        normal_accessor_idx = None
        if normals is not None and len(normals) > 0:
            norm_buf_offset = len(self._binary_data)
            norm_data = normals.flatten().tobytes()
            self._binary_data.extend(norm_data)
            norm_buf_view_idx = len(self._buffer_views)
            self._buffer_views.append({
                "buffer": 0,
                "byteOffset": norm_buf_offset,
                "byteLength": len(norm_data),
                "target": 34962
            })
            normal_accessor_idx = len(self._accessors)
            self._accessors.append({
                "bufferView": norm_buf_view_idx,
                "componentType": 5126,
                "count": len(normals),
                "type": "VEC3"
            })

        # 纹理坐标
        tex_coord_accessor_idx = None
        if uvs is not None and len(uvs) > 0:
            uv_buf_offset = len(self._binary_data)
            uv_data = uvs.flatten().tobytes()
            self._binary_data.extend(uv_data)
            uv_buf_view_idx = len(self._buffer_views)
            self._buffer_views.append({
                "buffer": 0,
                "byteOffset": uv_buf_offset,
                "byteLength": len(uv_data),
                "target": 34962
            })
            tex_coord_accessor_idx = len(self._accessors)
            self._accessors.append({
                "bufferView": uv_buf_view_idx,
                "componentType": 5126,
                "count": len(uvs),
                "type": "VEC2"
            })

        # 索引
        idx_buf_offset = len(self._binary_data)
        idx_data = faces.flatten().tobytes()
        self._binary_data.extend(idx_data)
        idx_buf_view_idx = len(self._buffer_views)
        self._buffer_views.append({
            "buffer": 0,
            "byteOffset": idx_buf_offset,
            "byteLength": len(idx_data),
            "target": 34963
        })

        idx_count = len(faces.flatten())
        idx_accessor_idx = len(self._accessors)
        self._accessors.append({
            "bufferView": idx_buf_view_idx,
            "componentType": 5123,
            "count": idx_count,
            "type": "SCALAR",
            "min": [int(faces.min())],
            "max": [int(faces.max())]
        })

        # 构建mesh primitive
        primitive = {
            "attributes": {
                "POSITION": pos_accessor_idx,
            },
            "indices": idx_accessor_idx,
            "material": material_index,
            "mode": 4
        }

        if normal_accessor_idx is not None:
            primitive["attributes"]["NORMAL"] = normal_accessor_idx
        if tex_coord_accessor_idx is not None:
            primitive["attributes"]["TEXCOORD_0"] = tex_coord_accessor_idx

        mesh_data = {
            "name": mesh.name,
            "primitives": [primitive]
        }

        self._meshes.append(mesh_data)
