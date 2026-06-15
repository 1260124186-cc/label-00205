package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** StreamPrediction API 客户端 */
public class StreamPredictionClient extends BaseAPIClient {

    public StreamPredictionClient(ApiClientConfig config) {
        super(config);
    }

    /** 流式数据注入 */
    public StreamDataIngestResponse streamIngestApiV1StreamIngestPost(
            StreamDataIngestRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/stream/ingest",
                params,
                body,
                StreamDataIngestResponse.class
        );
    }

    /** 批量流式数据注入 */
    public StreamBatchIngestResponse streamIngestBatchApiV1StreamIngestBatchPost(
            StreamBatchIngestRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/stream/ingest/batch",
                params,
                body,
                StreamBatchIngestResponse.class
        );
    }

    /** 获取窗口状态 */
    public StreamWindowStatusResponse getStreamWindowApiV1StreamWindowBoltIdGet(
            String boltId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/stream/window/" + boltId + "",
                params,
                null,
                StreamWindowStatusResponse.class
        );
    }

    /** 清空指定螺栓窗口 */
    public Map<String, Object> clearStreamWindowApiV1StreamWindowBoltIdDelete(
            String boltId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "DELETE",
                "/api/v1/api/v1/stream/window/" + boltId + "",
                params,
                null,
                Map.class
        );
    }

    /** 获取流式预测引擎状态 */
    public StreamEngineStatusResponse getStreamEngineStatusApiV1StreamStatusGet(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/stream/status",
                params,
                null,
                StreamEngineStatusResponse.class
        );
    }

    /** 切换预测模式 */
    public StreamModeSwitchResponse switchPredictionModeApiV1StreamModePost(
            StreamModeSwitchRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/stream/mode",
                params,
                body,
                StreamModeSwitchResponse.class
        );
    }

    /** 启动流式预测引擎 */
    public Map<String, Object> startStreamEngineApiV1StreamStartPost(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/stream/start",
                params,
                null,
                Map.class
        );
    }

    /** 停止流式预测引擎 */
    public Map<String, Object> stopStreamEngineApiV1StreamStopPost(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/stream/stop",
                params,
                null,
                Map.class
        );
    }

    /** 更新流式预测配置 */
    public StreamConfigResponse updateStreamConfigApiV1StreamConfigPost(
            StreamConfigUpdateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/stream/config",
                params,
                body,
                StreamConfigResponse.class
        );
    }

    /** 清空所有窗口 */
    public Map<String, Object> clearAllStreamWindowsApiV1StreamWindowsDelete(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "DELETE",
                "/api/v1/api/v1/stream/windows",
                params,
                null,
                Map.class
        );
    }

}