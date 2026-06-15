package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** AlertManagement API 客户端 */
public class AlertManagementClient extends BaseAPIClient {

    public AlertManagementClient(ApiClientConfig config) {
        super(config);
    }

    /** 查询告警规则列表 */
    public List<AlertRuleResponse> listAlertRulesApiV1AlertRulesGet(
            Object enabled,
            Object alertLevel
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (enabled != null) params.put("enabled", String.valueOf(enabled));
        if (alertLevel != null) params.put("alert_level", String.valueOf(alertLevel));

        return _request(
                "GET",
                "/api/v1/api/v1/alert/rules",
                params,
                null,
                List.class
        );
    }

    /** 创建告警规则 */
    public AlertRuleResponse createAlertRuleApiV1AlertRulesPost(
            AlertRuleCreate body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/alert/rules",
                params,
                body,
                AlertRuleResponse.class
        );
    }

    /** 更新告警规则 */
    public AlertRuleResponse updateAlertRuleApiV1AlertRulesRuleIdPut(
            Integer ruleId,
            AlertRuleUpdate body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "PUT",
                "/api/v1/api/v1/alert/rules/" + ruleId + "",
                params,
                body,
                AlertRuleResponse.class
        );
    }

    /** 删除告警规则 */
    public Map<String, Object> deleteAlertRuleApiV1AlertRulesRuleIdDelete(
            Integer ruleId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "DELETE",
                "/api/v1/api/v1/alert/rules/" + ruleId + "",
                params,
                null,
                Map.class
        );
    }

    /** 查询告警事件列表 */
    public AlertListResponse listAlertEventsApiV1AlertEventsGet(
            Object status,
            Object alertLevel,
            Object nodeType,
            Object nodeId,
            Integer limit,
            Integer offset
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (status != null) params.put("status", String.valueOf(status));
        if (alertLevel != null) params.put("alert_level", String.valueOf(alertLevel));
        if (nodeType != null) params.put("node_type", String.valueOf(nodeType));
        if (nodeId != null) params.put("node_id", String.valueOf(nodeId));
        if (limit != null) params.put("limit", String.valueOf(limit));
        if (offset != null) params.put("offset", String.valueOf(offset));

        return _request(
                "GET",
                "/api/v1/api/v1/alert/events",
                params,
                null,
                AlertListResponse.class
        );
    }

    /** 获取告警详情 */
    public AlertEventResponse getAlertEventApiV1AlertEventsAlertIdGet(
            Integer alertId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/alert/events/" + alertId + "",
                params,
                null,
                AlertEventResponse.class
        );
    }

    /** 处理告警 */
    public AlertEventResponse handleAlertEventApiV1AlertEventsAlertIdHandlePost(
            Integer alertId,
            AlertHandleRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/alert/events/" + alertId + "/handle",
                params,
                body,
                AlertEventResponse.class
        );
    }

    /** 手动触发告警升级检查 */
    public AlertUpgradeTriggerResponse triggerAlertUpgradeApiV1AlertUpgradeTriggerPost(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/alert/upgrade/trigger",
                params,
                null,
                AlertUpgradeTriggerResponse.class
        );
    }

}