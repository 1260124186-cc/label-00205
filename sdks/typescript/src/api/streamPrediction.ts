/** StreamPrediction API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class StreamPredictionClient extends BaseAPIClient {

  /**
   * 流式数据注入
   */
  async streamIngestApiV1StreamIngestPost(
    body: Models.StreamDataIngestRequest
  ): Promise<Models.StreamDataIngestResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/stream/ingest`,
      params,
      body
    );
  }

  /**
   * 批量流式数据注入
   */
  async streamIngestBatchApiV1StreamIngestBatchPost(
    body: Models.StreamBatchIngestRequest
  ): Promise<Models.StreamBatchIngestResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/stream/ingest/batch`,
      params,
      body
    );
  }

  /**
   * 获取窗口状态
   */
  async getStreamWindowApiV1StreamWindowBoltIdGet(
    boltId: string
  ): Promise<Models.StreamWindowStatusResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/stream/window/${boltId}`,
      params,
      undefined
    );
  }

  /**
   * 清空指定螺栓窗口
   */
  async clearStreamWindowApiV1StreamWindowBoltIdDelete(
    boltId: string
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "DELETE",
      `/api/v1/api/v1/stream/window/${boltId}`,
      params,
      undefined
    );
  }

  /**
   * 获取流式预测引擎状态
   */
  async getStreamEngineStatusApiV1StreamStatusGet(
  ): Promise<Models.StreamEngineStatusResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/stream/status`,
      params,
      undefined
    );
  }

  /**
   * 切换预测模式
   */
  async switchPredictionModeApiV1StreamModePost(
    body: Models.StreamModeSwitchRequest
  ): Promise<Models.StreamModeSwitchResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/stream/mode`,
      params,
      body
    );
  }

  /**
   * 启动流式预测引擎
   */
  async startStreamEngineApiV1StreamStartPost(
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/stream/start`,
      params,
      undefined
    );
  }

  /**
   * 停止流式预测引擎
   */
  async stopStreamEngineApiV1StreamStopPost(
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/stream/stop`,
      params,
      undefined
    );
  }

  /**
   * 更新流式预测配置
   */
  async updateStreamConfigApiV1StreamConfigPost(
    body: Models.StreamConfigUpdateRequest
  ): Promise<Models.StreamConfigResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/stream/config`,
      params,
      body
    );
  }

  /**
   * 清空所有窗口
   */
  async clearAllStreamWindowsApiV1StreamWindowsDelete(
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "DELETE",
      `/api/v1/api/v1/stream/windows`,
      params,
      undefined
    );
  }
}