/** ModelManagement API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class ModelManagementClient extends BaseAPIClient {

  /**
   * 训练模型
   */
  async trainModelApiV1ModelTrainPost(
    body: Models.TrainingRequest
  ): Promise<Models.TrainingResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/model/train`,
      params,
      body
    );
  }

  /**
   * 获取模型信息
   */
  async getModelInfoApiV1ModelInfoModelTypeNodeIdGet(
    modelType: string,
    nodeId: string
  ): Promise<Models.ModelInfoResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/model/info/${modelType}/${nodeId}`,
      params,
      undefined
    );
  }

  /**
   * 增强版训练模型（增量训练/学习率调度/类不平衡等）
   */
  async trainModelEnhancedApiV1ModelTrainEnhancedPost(
    body: Models.EnhancedTrainingRequest
  ): Promise<Models.EnhancedTrainingResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/model/train/enhanced`,
      params,
      body
    );
  }

  /**
   * 查询训练状态
   */
  async getTrainingStatusEndpointApiV1ModelTrainStatusSessionIdGet(
    sessionId: string
  ): Promise<Models.TrainingStatusResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/model/train/status/${sessionId}`,
      params,
      undefined
    );
  }

  /**
   * 列出训练会话历史
   */
  async listTrainingSessionsApiV1ModelTrainSessionsGet(
    modelType?: any,
    status?: any,
    limit?: number
  ): Promise<Models.TrainingSessionListResponse> {
    const params: Record<string, any> = {};
    if (modelType !== undefined) params['model_type'] = modelType;
    if (status !== undefined) params['status'] = status;
    if (limit !== undefined) params['limit'] = limit;

    return this._request(
      "GET",
      `/api/v1/api/v1/model/train/sessions`,
      params,
      undefined
    );
  }

  /**
   * 列出模型版本历史
   */
  async listModelVersionsApiV1ModelVersionsModelTypeNodeIdGet(
    modelType: string,
    nodeId: string
  ): Promise<Models.ModelVersionListResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/model/versions/${modelType}/${nodeId}`,
      params,
      undefined
    );
  }

  /**
   * 激活指定模型版本
   */
  async activateModelVersionApiV1ModelActivatePost(
    body: Models.ModelVersionActivateRequest
  ): Promise<Models.ModelVersionSchema> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/model/activate`,
      params,
      body
    );
  }

  /**
   * 回滚模型版本
   */
  async rollbackModelVersionApiV1ModelRollbackPost(
    body: Models.ModelVersionRollbackRequest
  ): Promise<Models.ModelVersionSchema> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/model/rollback`,
      params,
      body
    );
  }

  /**
   * 手动清理旧版本
   */
  async cleanupOldVersionsApiV1ModelVersionsModelTypeNodeIdCleanupPost(
    modelType: string,
    nodeId: string
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/model/versions/${modelType}/${nodeId}/cleanup`,
      params,
      undefined
    );
  }

  /**
   * 列出可导入的标注CSV文件
   */
  async listImportFilesApiV1ModelLabelImportFilesGet(
  ): Promise<Models.LabelImportFileListResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/model/label/import/files`,
      params,
      undefined
    );
  }

  /**
   * 从CSV导入人工标注数据
   */
  async importLabelsFromCsvApiV1ModelLabelImportCsvPost(
    body: Models.LabelImportCsvRequest
  ): Promise<Models.LabelImportResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/model/label/import/csv`,
      params,
      body
    );
  }

  /**
   * 从数据库表导入人工标注数据
   */
  async importLabelsFromDbApiV1ModelLabelImportDbPost(
    body: Models.LabelImportDbRequest
  ): Promise<Models.LabelImportResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/model/label/import/db`,
      params,
      body
    );
  }

  /**
   * 获取模型版本列表
   */
  async getModelVersionsApiV1ModelVersionsModelTypeModelIdGet(
    modelType: string,
    modelId: string
  ): Promise<Models.ModelVersionListResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/model/versions/${modelType}/${modelId}`,
      params,
      undefined
    );
  }

  /**
   * 获取当前活动版本
   */
  async getActiveModelVersionApiV1ModelVersionsModelTypeModelIdActiveGet(
    modelType: string,
    modelId: string
  ): Promise<Models.ModelVersionSchema> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/model/versions/${modelType}/${modelId}/active`,
      params,
      undefined
    );
  }

  /**
   * 激活/回滚模型版本
   */
  async activateModelVersionApiV1ModelVersionsModelTypeModelIdActivatePost(
    modelType: string,
    modelId: string,
    body: Models.ModelVersionActivateRequest
  ): Promise<Models.ModelVersionSchema> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/model/versions/${modelType}/${modelId}/activate`,
      params,
      body
    );
  }

  /**
   * 对比两个模型版本
   */
  async compareModelVersionsApiV1ModelVersionsModelTypeModelIdComparePost(
    modelType: string,
    modelId: string,
    body: Models.ModelVersionCompareRequest
  ): Promise<Models.ModelVersionCompareResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/model/versions/${modelType}/${modelId}/compare`,
      params,
      body
    );
  }

  /**
   * 删除模型版本
   */
  async deleteModelVersionApiV1ModelVersionsModelTypeModelIdVersionDelete(
    modelType: string,
    modelId: string,
    version: string
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "DELETE",
      `/api/v1/api/v1/model/versions/${modelType}/${modelId}/${version}`,
      params,
      undefined
    );
  }

  /**
   * 获取训练状态
   */
  async getTrainingStatusApiV1ModelTrainingStatusGet(
  ): Promise<Models.TrainingStatusResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/model/training/status`,
      params,
      undefined
    );
  }

  /**
   * 获取训练会话列表
   */
  async listTrainingSessionsApiV1ModelTrainingSessionsGet(
    limit?: number
  ): Promise<Models.TrainingSessionListResponse> {
    const params: Record<string, any> = {};
    if (limit !== undefined) params['limit'] = limit;

    return this._request(
      "GET",
      `/api/v1/api/v1/model/training/sessions`,
      params,
      undefined
    );
  }

  /**
   * 获取训练会话详情
   */
  async getTrainingSessionApiV1ModelTrainingSessionsSessionIdGet(
    sessionId: string
  ): Promise<Models.TrainingSessionSchema> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/model/training/sessions/${sessionId}`,
      params,
      undefined
    );
  }

  /**
   * 获取所有模型列表
   */
  async listAllModelsApiV1ModelListGet(
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/model/list`,
      params,
      undefined
    );
  }
}