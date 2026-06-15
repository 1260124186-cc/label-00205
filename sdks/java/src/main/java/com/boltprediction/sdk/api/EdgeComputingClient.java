package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** EdgeComputing API 客户端 */
public class EdgeComputingClient extends BaseAPIClient {

    public EdgeComputingClient(ApiClientConfig config) {
        super(config);
    }

    /** 注册边缘设备 */
    public EdgeDeviceRegisterResponse registerEdgeDeviceApiV1EdgeDeviceRegisterPost(
            EdgeDeviceRegisterRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/edge/device/register",
                params,
                body,
                EdgeDeviceRegisterResponse.class
        );
    }

    /** 边缘设备心跳 */
    public EdgeDeviceHeartbeatResponse edgeDeviceHeartbeatApiV1EdgeDeviceHeartbeatPost(
            EdgeDeviceHeartbeatRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/edge/device/heartbeat",
                params,
                body,
                EdgeDeviceHeartbeatResponse.class
        );
    }

    /** 获取最新模型版本信息 */
    public EdgeModelLatestResponse getEdgeModelLatestApiV1EdgeModelLatestPost(
            EdgeModelLatestRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/edge/model/latest",
                params,
                body,
                EdgeModelLatestResponse.class
        );
    }

    /** 下载模型包 */
    public Map<String, Object> downloadEdgeModelApiV1EdgeModelDownloadVersionGet(
            String version,
            String modelType,
            Object nodeId,
            String format
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (modelType != null) params.put("model_type", String.valueOf(modelType));
        if (nodeId != null) params.put("node_id", String.valueOf(nodeId));
        if (format != null) params.put("format", String.valueOf(format));

        return _request(
                "GET",
                "/api/v1/api/v1/edge/model/download/" + version + "",
                params,
                null,
                Map.class
        );
    }

    /** 导出边缘模型包 */
    public EdgeModelExportResponse exportEdgeModelApiV1EdgeModelExportPost(
            EdgeModelExportRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/edge/model/export",
                params,
                body,
                EdgeModelExportResponse.class
        );
    }

    /** 批量上报边缘预测结果 */
    public EdgePredictionUploadResponse uploadEdgePredictionsApiV1EdgePredictionsUploadPost(
            EdgePredictionUploadRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/edge/predictions/upload",
                params,
                body,
                EdgePredictionUploadResponse.class
        );
    }

    /** 获取所有边缘设备状态 */
    public Map<String, Object> listEdgeDevicesApiV1EdgeDeviceStatusGet(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/edge/device/status",
                params,
                null,
                Map.class
        );
    }

}