package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** WorkOrderStats API 客户端 */
public class WorkOrderStatsClient extends BaseAPIClient {

    public WorkOrderStatsClient(ApiClientConfig config) {
        super(config);
    }

    /** 工单统计指标概览 */
    public WorkOrderStatsResponse getWorkOrderStatsApiV1WorkOrdersStatsSummaryGet(
            Object startTime,
            Object endTime,
            Object nodeType,
            Object priority
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (startTime != null) params.put("start_time", String.valueOf(startTime));
        if (endTime != null) params.put("end_time", String.valueOf(endTime));
        if (nodeType != null) params.put("node_type", String.valueOf(nodeType));
        if (priority != null) params.put("priority", String.valueOf(priority));

        return _request(
                "GET",
                "/api/v1/api/v1/work-orders/stats/summary",
                params,
                null,
                WorkOrderStatsResponse.class
        );
    }

    /** MTTR趋势 */
    public MttrTrendResponse getMttrTrendApiV1WorkOrdersStatsMttrTrendGet(
            Integer days,
            Object nodeType,
            Object priority
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (days != null) params.put("days", String.valueOf(days));
        if (nodeType != null) params.put("node_type", String.valueOf(nodeType));
        if (priority != null) params.put("priority", String.valueOf(priority));

        return _request(
                "GET",
                "/api/v1/api/v1/work-orders/stats/mttr-trend",
                params,
                null,
                MttrTrendResponse.class
        );
    }

}