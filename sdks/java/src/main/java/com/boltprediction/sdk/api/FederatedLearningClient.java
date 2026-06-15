package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** FederatedLearning API 客户端 */
public class FederatedLearningClient extends BaseAPIClient {

    public FederatedLearningClient(ApiClientConfig config) {
        super(config);
    }

    /** 注册联邦学习客户端 */
    public FederatedClientRegisterResponse registerFederatedClientApiV1FederatedClientRegisterPost(
            FederatedClientRegisterRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/federated/client/register",
                params,
                body,
                FederatedClientRegisterResponse.class
        );
    }

    /** 获取联邦学习服务器状态 */
    public FederatedServerStatusResponse getFederatedServerStatusApiV1FederatedServerStatusGet(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/federated/server/status",
                params,
                null,
                FederatedServerStatusResponse.class
        );
    }

    /** 开始联邦学习轮次 */
    public FederatedRoundStartResponse startFederatedRoundApiV1FederatedRoundStartPost(
            FederatedRoundStartRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/federated/round/start",
                params,
                body,
                FederatedRoundStartResponse.class
        );
    }

    /** 获取当前轮次状态 */
    public Map<String, Object> getFederatedRoundStatusApiV1FederatedRoundStatusGet(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/federated/round/status",
                params,
                null,
                Map.class
        );
    }

    /** 聚合并更新全局模型 */
    public FederatedRoundAggregateResponse aggregateFederatedUpdatesApiV1FederatedRoundAggregatePost(
            FederatedRoundAggregateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/federated/round/aggregate",
                params,
                body,
                FederatedRoundAggregateResponse.class
        );
    }

    /** 获取全局模型历史 */
    public FederatedModelHistoryResponse getFederatedModelHistoryApiV1FederatedModelHistoryModelTypeNodeIdGet(
            String modelType,
            String nodeId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/federated/model/history/" + modelType + "/" + nodeId + "",
                params,
                null,
                FederatedModelHistoryResponse.class
        );
    }

    /** 下载全局模型 */
    public FederatedGlobalModelResponse downloadGlobalModelApiV1FederatedClientModelDownloadPost(
            FederatedGlobalModelRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/federated/client/model/download",
                params,
                body,
                FederatedGlobalModelResponse.class
        );
    }

    /** 上传模型更新 */
    public FederatedUpdateUploadResponse uploadModelUpdateApiV1FederatedClientUpdateUploadPost(
            FederatedUpdateUploadRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/federated/client/update/upload",
                params,
                body,
                FederatedUpdateUploadResponse.class
        );
    }

    /** 分发最新全局模型 */
    public Map<String, Object> distributeGlobalModelApiV1FederatedClientModelDistributeModelTypeNodeIdPost(
            String modelType,
            String nodeId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/federated/client/model/distribute/" + modelType + "/" + nodeId + "",
                params,
                null,
                Map.class
        );
    }

    /** 获取客户端状态 */
    public FederatedClientStatusResponse getFederatedClientStatusApiV1FederatedClientStatusClientIdGet(
            String clientId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/federated/client/status/" + clientId + "",
                params,
                null,
                FederatedClientStatusResponse.class
        );
    }

    /** 执行本地训练 */
    public FederatedLocalTrainResponse localTrainFederatedApiV1FederatedClientTrainLocalPost(
            FederatedLocalTrainRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/federated/client/train/local",
                params,
                body,
                FederatedLocalTrainResponse.class
        );
    }

    /** 获取客户端模型更新（用于上传） */
    public Map<String, Object> getClientModelUpdateApiV1FederatedClientUpdateGetClientIdPost(
            String clientId,
            Boolean applyPrivacy
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (applyPrivacy != null) params.put("apply_privacy", String.valueOf(applyPrivacy));

        return _request(
                "POST",
                "/api/v1/api/v1/federated/client/update/get/" + clientId + "",
                params,
                null,
                Map.class
        );
    }

    /** 配置隐私保护参数 */
    public Map<String, Object> configurePrivacyApiV1FederatedConfigPrivacyPost(
            FederatedPrivacyConfig body,
            String clientId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (clientId != null) params.put("client_id", String.valueOf(clientId));

        return _request(
                "POST",
                "/api/v1/api/v1/federated/config/privacy",
                params,
                body,
                Map.class
        );
    }

    /** 配置聚合器参数 */
    public Map<String, Object> configureAggregatorApiV1FederatedConfigAggregatorPost(
            FederatedAggregatorConfig body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/federated/config/aggregator",
                params,
                body,
                Map.class
        );
    }

}