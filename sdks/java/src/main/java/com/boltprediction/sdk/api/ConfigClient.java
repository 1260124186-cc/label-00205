package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** Config API 客户端 */
public class ConfigClient extends BaseAPIClient {

    public ConfigClient(ApiClientConfig config) {
        super(config);
    }

    /** 查询当前生效策略 */
    public EffectiveStrategyResponse getStrategyConfigApiV1StrategyConfigGet(
            Object nodeType,
            Object nodeId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (nodeType != null) params.put("node_type", String.valueOf(nodeType));
        if (nodeId != null) params.put("node_id", String.valueOf(nodeId));

        return _request(
                "GET",
                "/api/v1/api/v1/strategy/config",
                params,
                null,
                EffectiveStrategyResponse.class
        );
    }

    /** 更新预警策略（立即生效） */
    public StrategyConfigItemResponse updateStrategyConfigApiV1StrategyConfigPost(
            StrategyConfigUpdateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/strategy/config",
                params,
                body,
                StrategyConfigItemResponse.class
        );
    }

    /** 列出策略配置（含历史版本） */
    public StrategyConfigListResponse listStrategyConfigsApiV1StrategyConfigListGet(
            Object scope,
            Object nodeType,
            Object nodeId,
            Object isActive,
            Integer limit
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (scope != null) params.put("scope", String.valueOf(scope));
        if (nodeType != null) params.put("node_type", String.valueOf(nodeType));
        if (nodeId != null) params.put("node_id", String.valueOf(nodeId));
        if (isActive != null) params.put("is_active", String.valueOf(isActive));
        if (limit != null) params.put("limit", String.valueOf(limit));

        return _request(
                "GET",
                "/api/v1/api/v1/strategy/config/list",
                params,
                null,
                StrategyConfigListResponse.class
        );
    }

    /** 回滚策略到历史版本 */
    public StrategyConfigItemResponse rollbackStrategyConfigApiV1StrategyConfigRollbackPost(
            StrategyRollbackRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/strategy/config/rollback",
                params,
                body,
                StrategyConfigItemResponse.class
        );
    }

    /** 查询策略变更审计日志 */
    public StrategyAuditLogListResponse getStrategyAuditLogsApiV1StrategyConfigAuditGet(
            Object scope,
            Object nodeType,
            Object nodeId,
            Object action,
            Object operatorId,
            Integer limit,
            Integer offset
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (scope != null) params.put("scope", String.valueOf(scope));
        if (nodeType != null) params.put("node_type", String.valueOf(nodeType));
        if (nodeId != null) params.put("node_id", String.valueOf(nodeId));
        if (action != null) params.put("action", String.valueOf(action));
        if (operatorId != null) params.put("operator_id", String.valueOf(operatorId));
        if (limit != null) params.put("limit", String.valueOf(limit));
        if (offset != null) params.put("offset", String.valueOf(offset));

        return _request(
                "GET",
                "/api/v1/api/v1/strategy/config/audit",
                params,
                null,
                StrategyAuditLogListResponse.class
        );
    }

    /** 删除节点级策略覆盖 */
    public Map<String, Object> deleteStrategyOverrideApiV1StrategyConfigOverrideDelete(
            StrategyNodeOverrideDeleteRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "DELETE",
                "/api/v1/api/v1/strategy/config/override",
                params,
                body,
                Map.class
        );
    }

}