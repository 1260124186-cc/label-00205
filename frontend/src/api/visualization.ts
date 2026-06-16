/**
 * 3D可视化API
 *
 * 提供法兰3D场景的创建、导出、状态更新等API接口。
 */

import axios from 'axios';

export interface BoltCoordinate {
  bolt_id: string;
  x: number;
  y: number;
  z: number;
  angle?: number;
  radius?: number;
  position_index?: number;
}

export interface BoltStatusData {
  bolt_id: string;
  status_code?: number;
  status?: string;
  hi_score?: number;
  hi_level?: string;
  risk_level?: string;
  risk_score?: number;
  confidence?: number;
  diagnosis?: string;
  recommendations?: string[];
}

export interface Flange3DCreateRequest {
  flange_id: string;
  bolt_ids?: string[];
  bolt_count?: number;
  bolt_data?: BoltStatusData[];
  bolt_coordinate_csv?: string;
  bolt_coordinate_json?: string;
  visualization_mode?: 'status' | 'hi' | 'risk';
  flange_params?: Record<string, any>;
}

export interface Flange3DSceneInfo {
  flange_id: string;
  visualization_mode: string;
  bolt_count: number;
  bolt_ids: string[];
  flange_params: Record<string, any>;
  bolt_coordinates: BoltCoordinate[];
}

export interface Flange3DExportResponse {
  flange_id: string;
  format: string;
  visualization_mode: string;
  export_time: string;
  data: Record<string, any>;
}

export interface Flange3DUpdateResponse {
  flange_id: string;
  updated_count: number;
  visualization_mode: string;
  bolt_updates: Array<{
    bolt_id: string;
    color_hex: string;
    data: BoltStatusData;
  }>;
  update_time: string;
}

export interface Flange3DExplosionResponse {
  flange_id: string;
  explosion_factor: number;
  bolt_positions: Record<string, number[]>;
}

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

export const visualization3dApi = {
  createScene: async (request: Flange3DCreateRequest): Promise<Flange3DSceneInfo> => {
    const response = await apiClient.post('/visualization/3d/scene', request);
    return response.data;
  },

  getSceneInfo: async (flangeId: string): Promise<Flange3DSceneInfo> => {
    const response = await apiClient.get(`/visualization/3d/scene/${flangeId}`);
    return response.data;
  },

  listScenes: async (): Promise<{ total: number; scenes: string[] }> => {
    const response = await apiClient.get('/visualization/3d/scenes');
    return response.data;
  },

  exportScene: async (
    flangeId: string,
    format: 'gltf' | 'threejs' | 'unity' | 'all' = 'threejs',
    visualizationMode?: string
  ): Promise<Flange3DExportResponse> => {
    const response = await apiClient.get(`/visualization/3d/export/${flangeId}`, {
      params: {
        format,
        visualization_mode: visualizationMode,
      },
    });
    return response.data;
  },

  updateBoltStatus: async (
    flangeId: string,
    boltData: BoltStatusData[],
    visualizationMode?: string
  ): Promise<Flange3DUpdateResponse> => {
    const response = await apiClient.post('/visualization/3d/update', {
      flange_id: flangeId,
      bolt_data: boltData,
      visualization_mode: visualizationMode,
    });
    return response.data;
  },

  getExplosionPositions: async (
    flangeId: string,
    explosionFactor: number = 1.0
  ): Promise<Flange3DExplosionResponse> => {
    const response = await apiClient.get(`/visualization/3d/explosion/${flangeId}`, {
      params: { explosion_factor: explosionFactor },
    });
    return response.data;
  },

  deleteScene: async (flangeId: string): Promise<{ status: string; message: string }> => {
    const response = await apiClient.delete(`/visualization/3d/scene/${flangeId}`);
    return response.data;
  },
};

export default visualization3dApi;
