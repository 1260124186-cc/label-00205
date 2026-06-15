/** EdgeComputing API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class EdgeComputingClient extends BaseAPIClient {

  /**
   * 注册边缘设备
   */
  async registerEdgeDeviceApiV1EdgeDeviceRegisterPost(
    body: Models.EdgeDeviceRegisterRequest
  ): Promise<Models.EdgeDeviceRegisterResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/edge/device/register`,
      params,
      body
    );
  }

  /**
   * 边缘设备心跳
   */
  async edgeDeviceHeartbeatApiV1EdgeDeviceHeartbeatPost(
    body: Models.EdgeDeviceHeartbeatRequest
  ): Promise<Models.EdgeDeviceHeartbeatResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/edge/device/heartbeat`,
      params,
      body
    );
  }

  /**
   * 获取最新模型版本信息
   */
  async getEdgeModelLatestApiV1EdgeModelLatestPost(
    body: Models.EdgeModelLatestRequest
  ): Promise<Models.EdgeModelLatestResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/edge/model/latest`,
      params,
      body
    );
  }

  /**
   * 下载模型包
   */
  async downloadEdgeModelApiV1EdgeModelDownloadVersionGet(
    version: string,
    modelType?: string,
    nodeId?: any,
    format?: string
  ): Promise<any> {
    const params: Record<string, any> = {};
    if (modelType !== undefined) params['model_type'] = modelType;
    if (nodeId !== undefined) params['node_id'] = nodeId;
    if (format !== undefined) params['format'] = format;

    return this._request(
      "GET",
      `/api/v1/api/v1/edge/model/download/${version}`,
      params,
      undefined
    );
  }

  /**
   * 导出边缘模型包
   */
  async exportEdgeModelApiV1EdgeModelExportPost(
    body: Models.EdgeModelExportRequest
  ): Promise<Models.EdgeModelExportResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/edge/model/export`,
      params,
      body
    );
  }

  /**
   * 批量上报边缘预测结果
   */
  async uploadEdgePredictionsApiV1EdgePredictionsUploadPost(
    body: Models.EdgePredictionUploadRequest
  ): Promise<Models.EdgePredictionUploadResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/edge/predictions/upload`,
      params,
      body
    );
  }

  /**
   * 获取所有边缘设备状态
   */
  async listEdgeDevicesApiV1EdgeDeviceStatusGet(
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/edge/device/status`,
      params,
      undefined
    );
  }
}