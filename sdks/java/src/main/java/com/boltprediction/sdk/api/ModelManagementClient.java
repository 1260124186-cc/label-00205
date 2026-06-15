package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** ModelManagement API 客户端 */
public class ModelManagementClient extends BaseAPIClient {

    public ModelManagementClient(ApiClientConfig config) {
        super(config);
    }

    /** 训练模型 */
    public TrainingResponse trainModelApiV1ModelTrainPost(
            TrainingRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/model/train",
                params,
                body,
                TrainingResponse.class
        );
    }

    /** 获取模型信息 */
    public ModelInfoResponse getModelInfoApiV1ModelInfoModelTypeNodeIdGet(
            String modelType,
            String nodeId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/model/info/" + modelType + "/" + nodeId + "",
                params,
                null,
                ModelInfoResponse.class
        );
    }

    /** 增强版训练模型（增量训练/学习率调度/类不平衡等） */
    public EnhancedTrainingResponse trainModelEnhancedApiV1ModelTrainEnhancedPost(
            EnhancedTrainingRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/model/train/enhanced",
                params,
                body,
                EnhancedTrainingResponse.class
        );
    }

    /** 查询训练状态 */
    public TrainingStatusResponse getTrainingStatusEndpointApiV1ModelTrainStatusSessionIdGet(
            String sessionId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/model/train/status/" + sessionId + "",
                params,
                null,
                TrainingStatusResponse.class
        );
    }

    /** 列出训练会话历史 */
    public TrainingSessionListResponse listTrainingSessionsApiV1ModelTrainSessionsGet(
            Object modelType,
            Object status,
            Integer limit
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (modelType != null) params.put("model_type", String.valueOf(modelType));
        if (status != null) params.put("status", String.valueOf(status));
        if (limit != null) params.put("limit", String.valueOf(limit));

        return _request(
                "GET",
                "/api/v1/api/v1/model/train/sessions",
                params,
                null,
                TrainingSessionListResponse.class
        );
    }

    /** 列出模型版本历史 */
    public ModelVersionListResponse listModelVersionsApiV1ModelVersionsModelTypeNodeIdGet(
            String modelType,
            String nodeId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/model/versions/" + modelType + "/" + nodeId + "",
                params,
                null,
                ModelVersionListResponse.class
        );
    }

    /** 激活指定模型版本 */
    public ModelVersionSchema activateModelVersionApiV1ModelActivatePost(
            ModelVersionActivateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/model/activate",
                params,
                body,
                ModelVersionSchema.class
        );
    }

    /** 回滚模型版本 */
    public ModelVersionSchema rollbackModelVersionApiV1ModelRollbackPost(
            ModelVersionRollbackRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/model/rollback",
                params,
                body,
                ModelVersionSchema.class
        );
    }

    /** 手动清理旧版本 */
    public Map<String, Object> cleanupOldVersionsApiV1ModelVersionsModelTypeNodeIdCleanupPost(
            String modelType,
            String nodeId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/model/versions/" + modelType + "/" + nodeId + "/cleanup",
                params,
                null,
                Map.class
        );
    }

    /** 列出可导入的标注CSV文件 */
    public LabelImportFileListResponse listImportFilesApiV1ModelLabelImportFilesGet(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/model/label/import/files",
                params,
                null,
                LabelImportFileListResponse.class
        );
    }

    /** 从CSV导入人工标注数据 */
    public LabelImportResponse importLabelsFromCsvApiV1ModelLabelImportCsvPost(
            LabelImportCsvRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/model/label/import/csv",
                params,
                body,
                LabelImportResponse.class
        );
    }

    /** 从数据库表导入人工标注数据 */
    public LabelImportResponse importLabelsFromDbApiV1ModelLabelImportDbPost(
            LabelImportDbRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/model/label/import/db",
                params,
                body,
                LabelImportResponse.class
        );
    }

    /** 获取模型版本列表 */
    public ModelVersionListResponse getModelVersionsApiV1ModelVersionsModelTypeModelIdGet(
            String modelType,
            String modelId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/model/versions/" + modelType + "/" + modelId + "",
                params,
                null,
                ModelVersionListResponse.class
        );
    }

    /** 获取当前活动版本 */
    public ModelVersionSchema getActiveModelVersionApiV1ModelVersionsModelTypeModelIdActiveGet(
            String modelType,
            String modelId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/model/versions/" + modelType + "/" + modelId + "/active",
                params,
                null,
                ModelVersionSchema.class
        );
    }

    /** 激活/回滚模型版本 */
    public ModelVersionSchema activateModelVersionApiV1ModelVersionsModelTypeModelIdActivatePost(
            String modelType,
            String modelId,
            ModelVersionActivateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/model/versions/" + modelType + "/" + modelId + "/activate",
                params,
                body,
                ModelVersionSchema.class
        );
    }

    /** 对比两个模型版本 */
    public ModelVersionCompareResponse compareModelVersionsApiV1ModelVersionsModelTypeModelIdComparePost(
            String modelType,
            String modelId,
            ModelVersionCompareRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/model/versions/" + modelType + "/" + modelId + "/compare",
                params,
                body,
                ModelVersionCompareResponse.class
        );
    }

    /** 删除模型版本 */
    public Map<String, Object> deleteModelVersionApiV1ModelVersionsModelTypeModelIdVersionDelete(
            String modelType,
            String modelId,
            String version
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "DELETE",
                "/api/v1/api/v1/model/versions/" + modelType + "/" + modelId + "/" + version + "",
                params,
                null,
                Map.class
        );
    }

    /** 获取训练状态 */
    public TrainingStatusResponse getTrainingStatusApiV1ModelTrainingStatusGet(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/model/training/status",
                params,
                null,
                TrainingStatusResponse.class
        );
    }

    /** 获取训练会话列表 */
    public TrainingSessionListResponse listTrainingSessionsApiV1ModelTrainingSessionsGet(
            Integer limit
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (limit != null) params.put("limit", String.valueOf(limit));

        return _request(
                "GET",
                "/api/v1/api/v1/model/training/sessions",
                params,
                null,
                TrainingSessionListResponse.class
        );
    }

    /** 获取训练会话详情 */
    public TrainingSessionSchema getTrainingSessionApiV1ModelTrainingSessionsSessionIdGet(
            String sessionId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/model/training/sessions/" + sessionId + "",
                params,
                null,
                TrainingSessionSchema.class
        );
    }

    /** 获取所有模型列表 */
    public Map<String, Object> listAllModelsApiV1ModelListGet(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/model/list",
                params,
                null,
                Map.class
        );
    }

}