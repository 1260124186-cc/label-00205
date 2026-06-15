/** FederatedLearning API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class FederatedLearningClient extends BaseAPIClient {

  /**
   * 注册联邦学习客户端
   */
  async registerFederatedClientApiV1FederatedClientRegisterPost(
    body: Models.FederatedClientRegisterRequest
  ): Promise<Models.FederatedClientRegisterResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/federated/client/register`,
      params,
      body
    );
  }

  /**
   * 获取联邦学习服务器状态
   */
  async getFederatedServerStatusApiV1FederatedServerStatusGet(
  ): Promise<Models.FederatedServerStatusResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/federated/server/status`,
      params,
      undefined
    );
  }

  /**
   * 开始联邦学习轮次
   */
  async startFederatedRoundApiV1FederatedRoundStartPost(
    body: Models.FederatedRoundStartRequest
  ): Promise<Models.FederatedRoundStartResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/federated/round/start`,
      params,
      body
    );
  }

  /**
   * 获取当前轮次状态
   */
  async getFederatedRoundStatusApiV1FederatedRoundStatusGet(
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/federated/round/status`,
      params,
      undefined
    );
  }

  /**
   * 聚合并更新全局模型
   */
  async aggregateFederatedUpdatesApiV1FederatedRoundAggregatePost(
    body: Models.FederatedRoundAggregateRequest
  ): Promise<Models.FederatedRoundAggregateResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/federated/round/aggregate`,
      params,
      body
    );
  }

  /**
   * 获取全局模型历史
   */
  async getFederatedModelHistoryApiV1FederatedModelHistoryModelTypeNodeIdGet(
    modelType: string,
    nodeId: string
  ): Promise<Models.FederatedModelHistoryResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/federated/model/history/${modelType}/${nodeId}`,
      params,
      undefined
    );
  }

  /**
   * 下载全局模型
   */
  async downloadGlobalModelApiV1FederatedClientModelDownloadPost(
    body: Models.FederatedGlobalModelRequest
  ): Promise<Models.FederatedGlobalModelResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/federated/client/model/download`,
      params,
      body
    );
  }

  /**
   * 上传模型更新
   */
  async uploadModelUpdateApiV1FederatedClientUpdateUploadPost(
    body: Models.FederatedUpdateUploadRequest
  ): Promise<Models.FederatedUpdateUploadResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/federated/client/update/upload`,
      params,
      body
    );
  }

  /**
   * 分发最新全局模型
   */
  async distributeGlobalModelApiV1FederatedClientModelDistributeModelTypeNodeIdPost(
    modelType: string,
    nodeId: string
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/federated/client/model/distribute/${modelType}/${nodeId}`,
      params,
      undefined
    );
  }

  /**
   * 获取客户端状态
   */
  async getFederatedClientStatusApiV1FederatedClientStatusClientIdGet(
    clientId: string
  ): Promise<Models.FederatedClientStatusResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/federated/client/status/${clientId}`,
      params,
      undefined
    );
  }

  /**
   * 执行本地训练
   */
  async localTrainFederatedApiV1FederatedClientTrainLocalPost(
    body: Models.FederatedLocalTrainRequest
  ): Promise<Models.FederatedLocalTrainResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/federated/client/train/local`,
      params,
      body
    );
  }

  /**
   * 获取客户端模型更新（用于上传）
   */
  async getClientModelUpdateApiV1FederatedClientUpdateGetClientIdPost(
    clientId: string,
    applyPrivacy?: boolean
  ): Promise<any> {
    const params: Record<string, any> = {};
    if (applyPrivacy !== undefined) params['apply_privacy'] = applyPrivacy;

    return this._request(
      "POST",
      `/api/v1/api/v1/federated/client/update/get/${clientId}`,
      params,
      undefined
    );
  }

  /**
   * 配置隐私保护参数
   */
  async configurePrivacyApiV1FederatedConfigPrivacyPost(
    body: Models.FederatedPrivacyConfig,
    clientId: string
  ): Promise<any> {
    const params: Record<string, any> = {};
    if (clientId !== undefined) params['client_id'] = clientId;

    return this._request(
      "POST",
      `/api/v1/api/v1/federated/config/privacy`,
      params,
      body
    );
  }

  /**
   * 配置聚合器参数
   */
  async configureAggregatorApiV1FederatedConfigAggregatorPost(
    body: Models.FederatedAggregatorConfig
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/federated/config/aggregator`,
      params,
      body
    );
  }
}