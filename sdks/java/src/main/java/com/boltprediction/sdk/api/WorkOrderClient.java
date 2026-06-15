package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** WorkOrder API 客户端 */
public class WorkOrderClient extends BaseAPIClient {

    public WorkOrderClient(ApiClientConfig config) {
        super(config);
    }

    /** 查询工单列表 */
    public WorkOrderListResponse listWorkOrdersApiV1WorkOrdersGet(
            Object status,
            Object priority,
            Object assigneeId,
            Object alertId,
            Object nodeType,
            Object nodeId,
            Integer limit,
            Integer offset
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (status != null) params.put("status", String.valueOf(status));
        if (priority != null) params.put("priority", String.valueOf(priority));
        if (assigneeId != null) params.put("assignee_id", String.valueOf(assigneeId));
        if (alertId != null) params.put("alert_id", String.valueOf(alertId));
        if (nodeType != null) params.put("node_type", String.valueOf(nodeType));
        if (nodeId != null) params.put("node_id", String.valueOf(nodeId));
        if (limit != null) params.put("limit", String.valueOf(limit));
        if (offset != null) params.put("offset", String.valueOf(offset));

        return _request(
                "GET",
                "/api/v1/api/v1/work-orders",
                params,
                null,
                WorkOrderListResponse.class
        );
    }

    /** 手动创建工单 */
    public WorkOrderResponse createWorkOrderApiV1WorkOrdersPost(
            WorkOrderCreate body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/work-orders",
                params,
                body,
                WorkOrderResponse.class
        );
    }

    /** 获取工单详情 */
    public WorkOrderResponse getWorkOrderApiV1WorkOrdersWorkOrderIdGet(
            Integer workOrderId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/work-orders/" + workOrderId + "",
                params,
                null,
                WorkOrderResponse.class
        );
    }

    /** 更新工单信息 */
    public WorkOrderResponse updateWorkOrderApiV1WorkOrdersWorkOrderIdPut(
            Integer workOrderId,
            WorkOrderUpdate body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "PUT",
                "/api/v1/api/v1/work-orders/" + workOrderId + "",
                params,
                body,
                WorkOrderResponse.class
        );
    }

    /** 指派工单 */
    public WorkOrderResponse assignWorkOrderApiV1WorkOrdersWorkOrderIdAssignPost(
            Integer workOrderId,
            WorkOrderAssignRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/work-orders/" + workOrderId + "/assign",
                params,
                body,
                WorkOrderResponse.class
        );
    }

    /** 更新工单状态 */
    public WorkOrderResponse updateWorkOrderStatusApiV1WorkOrdersWorkOrderIdStatusPost(
            Integer workOrderId,
            WorkOrderStatusUpdateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/work-orders/" + workOrderId + "/status",
                params,
                body,
                WorkOrderResponse.class
        );
    }

    /** 解决工单 */
    public WorkOrderResponse resolveWorkOrderApiV1WorkOrdersWorkOrderIdResolvePost(
            Integer workOrderId,
            WorkOrderResolveRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/work-orders/" + workOrderId + "/resolve",
                params,
                body,
                WorkOrderResponse.class
        );
    }

    /** 查询工单处置记录列表 */
    public DisposalRecordListResponse listWorkOrderDisposalsApiV1WorkOrdersWorkOrderIdDisposalsGet(
            Integer workOrderId,
            Object disposalType,
            Integer limit,
            Integer offset
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (disposalType != null) params.put("disposal_type", String.valueOf(disposalType));
        if (limit != null) params.put("limit", String.valueOf(limit));
        if (offset != null) params.put("offset", String.valueOf(offset));

        return _request(
                "GET",
                "/api/v1/api/v1/work-orders/" + workOrderId + "/disposals",
                params,
                null,
                DisposalRecordListResponse.class
        );
    }

    /** 创建处置记录 */
    public DisposalRecordResponse createDisposalRecordApiV1WorkOrdersDisposalsPost(
            DisposalRecordCreate body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/work-orders/disposals",
                params,
                body,
                DisposalRecordResponse.class
        );
    }

    /** 获取处置记录详情 */
    public DisposalRecordResponse getDisposalRecordApiV1WorkOrdersDisposalsRecordIdGet(
            Integer recordId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/work-orders/disposals/" + recordId + "",
                params,
                null,
                DisposalRecordResponse.class
        );
    }

    /** 更新处置记录 */
    public DisposalRecordResponse updateDisposalRecordApiV1WorkOrdersDisposalsRecordIdPut(
            Integer recordId,
            DisposalRecordUpdate body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "PUT",
                "/api/v1/api/v1/work-orders/disposals/" + recordId + "",
                params,
                body,
                DisposalRecordResponse.class
        );
    }

    /** 删除处置记录 */
    public Map<String, Object> deleteDisposalRecordApiV1WorkOrdersDisposalsRecordIdDelete(
            Integer recordId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "DELETE",
                "/api/v1/api/v1/work-orders/disposals/" + recordId + "",
                params,
                null,
                Map.class
        );
    }

    /** 查询工单复测记录列表 */
    public RetestRecordListResponse listWorkOrderRetestsApiV1WorkOrdersWorkOrderIdRetestsGet(
            Integer workOrderId,
            Object retestResult,
            Integer limit,
            Integer offset
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (retestResult != null) params.put("retest_result", String.valueOf(retestResult));
        if (limit != null) params.put("limit", String.valueOf(limit));
        if (offset != null) params.put("offset", String.valueOf(offset));

        return _request(
                "GET",
                "/api/v1/api/v1/work-orders/" + workOrderId + "/retests",
                params,
                null,
                RetestRecordListResponse.class
        );
    }

    /** 创建复测记录 */
    public RetestRecordResponse createRetestRecordApiV1WorkOrdersRetestsPost(
            RetestRecordCreate body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/work-orders/retests",
                params,
                body,
                RetestRecordResponse.class
        );
    }

    /** 获取复测记录详情 */
    public RetestRecordResponse getRetestRecordApiV1WorkOrdersRetestsRecordIdGet(
            Integer recordId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/work-orders/retests/" + recordId + "",
                params,
                null,
                RetestRecordResponse.class
        );
    }

    /** 更新复测记录 */
    public RetestRecordResponse updateRetestRecordApiV1WorkOrdersRetestsRecordIdPut(
            Integer recordId,
            RetestRecordUpdate body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "PUT",
                "/api/v1/api/v1/work-orders/retests/" + recordId + "",
                params,
                body,
                RetestRecordResponse.class
        );
    }

    /** 触发复测后再预测 */
    public PredictionCompareResponse triggerRetestRepredictApiV1WorkOrdersRetestsRecordIdRepredictPost(
            Integer recordId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/work-orders/retests/" + recordId + "/repredict",
                params,
                null,
                PredictionCompareResponse.class
        );
    }

    /** 查询工单预测对比列表 */
    public PredictionCompareListResponse listWorkOrderPredictionComparesApiV1WorkOrdersWorkOrderIdPredictionComparesGet(
            Integer workOrderId,
            Object isFalsePositive,
            Object isRecurring,
            Object riskChange,
            Integer limit,
            Integer offset
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (isFalsePositive != null) params.put("is_false_positive", String.valueOf(isFalsePositive));
        if (isRecurring != null) params.put("is_recurring", String.valueOf(isRecurring));
        if (riskChange != null) params.put("risk_change", String.valueOf(riskChange));
        if (limit != null) params.put("limit", String.valueOf(limit));
        if (offset != null) params.put("offset", String.valueOf(offset));

        return _request(
                "GET",
                "/api/v1/api/v1/work-orders/" + workOrderId + "/prediction-compares",
                params,
                null,
                PredictionCompareListResponse.class
        );
    }

    /** 获取预测对比详情 */
    public PredictionCompareResponse getPredictionCompareApiV1WorkOrdersPredictionComparesCompareIdGet(
            Integer compareId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/work-orders/prediction-compares/" + compareId + "",
                params,
                null,
                PredictionCompareResponse.class
        );
    }

}