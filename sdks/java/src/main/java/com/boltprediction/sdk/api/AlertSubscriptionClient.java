package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** AlertSubscription API 客户端 */
public class AlertSubscriptionClient extends BaseAPIClient {

    public AlertSubscriptionClient(ApiClientConfig config) {
        super(config);
    }

    /** 查询订阅列表 */
    public List<AlertSubscriptionResponse> listAlertSubscriptionsApiV1AlertSubscriptionsGet(
            Object subscriberType,
            Object subscriberId,
            Object enabled
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (subscriberType != null) params.put("subscriber_type", String.valueOf(subscriberType));
        if (subscriberId != null) params.put("subscriber_id", String.valueOf(subscriberId));
        if (enabled != null) params.put("enabled", String.valueOf(enabled));

        return _request(
                "GET",
                "/api/v1/api/v1/alert/subscriptions",
                params,
                null,
                List.class
        );
    }

    /** 创建订阅 */
    public AlertSubscriptionResponse createAlertSubscriptionApiV1AlertSubscriptionsPost(
            AlertSubscriptionCreate body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/alert/subscriptions",
                params,
                body,
                AlertSubscriptionResponse.class
        );
    }

    /** 获取订阅详情 */
    public AlertSubscriptionResponse getAlertSubscriptionApiV1AlertSubscriptionsSubIdGet(
            Integer subId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/alert/subscriptions/" + subId + "",
                params,
                null,
                AlertSubscriptionResponse.class
        );
    }

    /** 更新订阅 */
    public AlertSubscriptionResponse updateAlertSubscriptionApiV1AlertSubscriptionsSubIdPut(
            Integer subId,
            AlertSubscriptionUpdate body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "PUT",
                "/api/v1/api/v1/alert/subscriptions/" + subId + "",
                params,
                body,
                AlertSubscriptionResponse.class
        );
    }

    /** 删除订阅 */
    public Map<String, Object> deleteAlertSubscriptionApiV1AlertSubscriptionsSubIdDelete(
            Integer subId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "DELETE",
                "/api/v1/api/v1/alert/subscriptions/" + subId + "",
                params,
                null,
                Map.class
        );
    }

}