"""
Unity数据包导出器

导出Unity可用的数据包格式，包括：
- 预制体配置数据（Prefab config）
- ScriptableObject 数据
- 螺栓状态数据
- 材质颜色配置

可用于Unity Addressables或直接加载。
"""

import json
import base64
from typing import List, Dict, Tuple, Any, Optional
from dataclasses import dataclass, asdict
import numpy as np

from .flange_model import MeshData
from .color_mapper import ColorMapper


@dataclass
class UnityMeshData:
    """Unity网格数据"""
    name: str
    vertices: List[List[float]]
    normals: List[List[float]]
    uvs: List[List[float]]
    triangles: List[int]
    colors: Optional[List[List[float]]] = None


@dataclass
class UnityBoltData:
    """Unity螺栓数据"""
    boltId: str
    position: List[float]
    rotation: List[float]
    scale: List[float]
    statusCode: int
    statusName: str
    hiScore: float
    riskLevel: str
    riskScore: float
    colorHex: str
    colorRgb: List[float]


class UnityExporter:
    """
    Unity数据包导出器

    生成Unity可直接使用的数据包。
    支持：
    - 网格数据（可用于MeshFilter）
    - 螺栓状态数据（可用于ScriptableObject）
    - 材质颜色配置
    - 场景层级配置
    """

    def __init__(self):
        self.color_mapper = ColorMapper()

    def export_package(
        self,
        meshes: List[MeshData],
        bolt_data: Optional[Dict[str, Dict[str, Any]]] = None,
        flange_id: str = "flange_001",
        visualization_mode: str = "status",
    ) -> Dict[str, Any]:
        """
        导出完整的Unity数据包

        Args:
            meshes: 网格数据列表
            bolt_data: 螺栓数据
            flange_id: 法兰ID
            visualization_mode: 可视化模式

        Returns:
            Unity数据包
        """
        bolt_meshes = [m for m in meshes if m.user_data.get('type') == 'bolt']
        other_meshes = [m for m in meshes if m.user_data.get('type') != 'bolt']

        bolt_list = []
        for mesh in bolt_meshes:
            bolt_id = mesh.user_data.get('bolt_id', '')
            bolt_info = bolt_data.get(bolt_id, {}) if bolt_data else {}

            color = self.color_mapper.get_color(visualization_mode, bolt_info or {'status_code': 0})
            color_norm = self.color_mapper.rgb_to_normalized(color)

            bolt_list.append(UnityBoltData(
                boltId=bolt_id,
                position=[0, 0, 0],
                rotation=[0, 0, 0, 1],
                scale=[1, 1, 1],
                statusCode=bolt_info.get('status_code', 0),
                statusName=bolt_info.get('status', '正常'),
                hiScore=bolt_info.get('hi_score', 100.0),
                riskLevel=bolt_info.get('risk_level', 'low'),
                riskScore=bolt_info.get('risk_score', 1.0),
                colorHex=self.color_mapper.rgb_to_hex(color),
                colorRgb=list(color_norm)
            ))

        package = {
            "packageInfo": {
                "name": f"FlangeDigitalTwin_{flange_id}",
                "version": "1.0.0",
                "type": "digital_twin_flange",
                "flangeId": flange_id,
                "visualizationMode": visualization_mode,
                "generator": "Bolt Flange Visualization Service",
            },
            "meshes": {
                "flangeBody": self._convert_mesh(next((m for m in other_meshes if 'body' in m.name), other_meshes[0]) if other_meshes else None),
                "pipe": self._convert_mesh(next((m for m in other_meshes if 'pipe' in m.name), None)),
                "boltPrefab": self._convert_mesh(bolt_meshes[0]) if bolt_meshes else None,
            },
            "bolts": [asdict(b) for b in bolt_list],
            "materials": {
                "flangeMaterial": {
                    "type": "Standard",
                    "color": "#BFBFC7",
                    "metallic": 0.3,
                    "smoothness": 0.5,
                },
                "boltMaterial": {
                    "type": "Standard",
                    "color": "#9999A6",
                    "metallic": 0.5,
                    "smoothness": 0.4,
                    "enableVertexColor": True,
                }
            },
            "sceneConfig": {
                "flangePosition": [0, 0, 0],
                "flangeRotation": [0, 0, 0],
                "boltCount": len(bolt_list),
                "explosionEnabled": False,
                "explosionFactor": 0.0,
                "rotationEnabled": True,
                "autoRotate": False,
            },
            "interactionConfig": {
                "rotateSpeed": 1.0,
                "zoomSpeed": 1.0,
                "panSpeed": 1.0,
                "explosionSpeed": 1.0,
                "minZoom": 0.5,
                "maxZoom": 10.0,
            },
            "statusColorMap": {
                "0": {"name": "正常", "color": "#4CAF50"},
                "1": {"name": "关注级预警", "color": "#FFC107"},
                "2": {"name": "检查级预警", "color": "#FF9800"},
                "3": {"name": "紧急级预警", "color": "#F44336"},
                "4": {"name": "故障", "color": "#9C27B0"},
            },
            "healthColorGradient": {
                "stops": [
                    {"position": 0.0, "color": "#F44336"},
                    {"position": 0.3, "color": "#FF9800"},
                    {"position": 0.5, "color": "#FFC107"},
                    {"position": 0.7, "color": "#8BC34A"},
                    {"position": 1.0, "color": "#4CAF50"},
                ]
            }
        }

        return package

    def export_to_json_string(
        self,
        meshes: List[MeshData],
        bolt_data: Optional[Dict[str, Dict[str, Any]]] = None,
        flange_id: str = "flange_001",
        visualization_mode: str = "status",
    ) -> str:
        """导出为JSON字符串"""
        package = self.export_package(meshes, bolt_data, flange_id, visualization_mode)
        return json.dumps(package, ensure_ascii=False)

    def export_scriptable_object(
        self,
        bolt_data: Dict[str, Dict[str, Any]],
        flange_id: str = "flange_001"
    ) -> Dict[str, Any]:
        """
        导出ScriptableObject格式数据（Unity专用）

        生成类似Unity ScriptableObject的YAML/JSON格式数据。
        """
        bolts = []
        for bolt_id, data in bolt_data.items():
            status_color = self.color_mapper.get_status_color(data.get('status_code', 0))
            hi_color = self.color_mapper.get_hi_color(data.get('hi_score', 100))

            bolts.append({
                "boltId": bolt_id,
                "statusCode": data.get('status_code', 0),
                "statusName": data.get('status', '正常'),
                "confidence": data.get('confidence', 0.0),
                "hiScore": data.get('hi_score', 100.0),
                "hiLevel": data.get('hi_level', 'excellent'),
                "riskLevel": data.get('risk_level', 'low'),
                "riskScore": data.get('risk_score', 1.0),
                "statusColor": {
                    "r": status_color[0] / 255.0,
                    "g": status_color[1] / 255.0,
                    "b": status_color[2] / 255.0,
                    "a": 1.0
                },
                "healthColor": {
                    "r": hi_color[0] / 255.0,
                    "g": hi_color[1] / 255.0,
                    "b": hi_color[2] / 255.0,
                    "a": 1.0
                },
                "diagnosis": data.get('diagnosis', ''),
                "recommendations": data.get('recommendations', []),
            })

        return {
            "m_ObjectHideFlags": 0,
            "m_CorrespondingSourceObject": {"fileID": 0},
            "m_PrefabInstance": {"fileID": 0},
            "m_PrefabAsset": {"fileID": 0},
            "m_EditorClassIdentifier": "FlangeBoltData",
            "flangeId": flange_id,
            "bolts": bolts,
            "boltCount": len(bolts),
        }

    def _convert_mesh(self, mesh: Optional[MeshData]) -> Optional[Dict[str, Any]]:
        """转换为Unity网格格式"""
        if mesh is None:
            return None

        triangles = []
        for face in mesh.faces:
            triangles.extend(face)

        return {
            "name": mesh.name,
            "vertexCount": len(mesh.vertices),
            "vertices": mesh.vertices,
            "normals": mesh.normals if mesh.normals else [],
            "uvs": mesh.uvs if mesh.uvs else [],
            "triangles": triangles,
            "subMeshCount": 1,
            "bounds": self._calculate_bounds(mesh.vertices),
            "userData": mesh.user_data
        }

    def _calculate_bounds(self, vertices: List[List[float]]) -> Dict[str, Any]:
        """计算包围盒"""
        if not vertices:
            return {"center": [0, 0, 0], "size": [0, 0, 0]}

        verts = np.array(vertices)
        min_v = verts.min(axis=0)
        max_v = verts.max(axis=0)
        center = (min_v + max_v) / 2
        size = max_v - min_v

        return {
            "center": center.tolist(),
            "size": size.tolist(),
            "min": min_v.tolist(),
            "max": max_v.tolist(),
        }

    def create_bolt_update_payload(
        self,
        bolt_data: Dict[str, Dict[str, Any]],
        visualization_mode: str = "status"
    ) -> Dict[str, Any]:
        """
        创建螺栓状态更新payload（Unity实时更新用）

        Args:
            bolt_data: 螺栓状态数据
            visualization_mode: 可视化模式

        Returns:
            更新payload
        """
        updates = []
        for bolt_id, data in bolt_data.items():
            color = self.color_mapper.get_color(visualization_mode, data)
            updates.append({
                "boltId": bolt_id,
                "statusCode": data.get('status_code', 0),
                "hiScore": data.get('hi_score', 100),
                "riskLevel": data.get('risk_level', 'low'),
                "color": {
                    "r": color[0] / 255.0,
                    "g": color[1] / 255.0,
                    "b": color[2] / 255.0,
                    "a": 1.0
                },
                "data": data
            })

        return {
            "type": "bolt_status_update",
            "visualizationMode": visualization_mode,
            "timestamp": np.datetime64('now').astype(str),
            "updates": updates
        }
