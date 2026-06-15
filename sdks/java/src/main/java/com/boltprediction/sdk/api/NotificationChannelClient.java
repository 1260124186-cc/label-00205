package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** NotificationChannel API 客户端 */
public class NotificationChannelClient extends BaseAPIClient {

    public NotificationChannelClient(ApiClientConfig config) {
        super(config);
    }

    /** 查询通知渠道列表 */
    public List<NotificationChannelResponse> listNotificationChannelsApiV1NotificationChannelsGet(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/notification/channels",
                params,
                null,
                List.class
        );
    }

    /** 创建通知渠道 */
    public NotificationChannelResponse createNotificationChannelApiV1NotificationChannelsPost(
            NotificationChannelCreate body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/notification/channels",
                params,
                body,
                NotificationChannelResponse.class
        );
    }

    /** 更新通知渠道 */
    public NotificationChannelResponse updateNotificationChannelApiV1NotificationChannelsChannelIdPut(
            Integer channelId,
            NotificationChannelUpdate body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "PUT",
                "/api/v1/api/v1/notification/channels/" + channelId + "",
                params,
                body,
                NotificationChannelResponse.class
        );
    }

    /** 删除通知渠道 */
    public Map<String, Object> deleteNotificationChannelApiV1NotificationChannelsChannelIdDelete(
            Integer channelId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "DELETE",
                "/api/v1/api/v1/notification/channels/" + channelId + "",
                params,
                null,
                Map.class
        );
    }

    /** 查询通知发送日志 */
    public List<NotificationLogResponse> listNotificationLogsApiV1NotificationLogsGet(
            Object alertId,
            Object status,
            Integer limit
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (alertId != null) params.put("alert_id", String.valueOf(alertId));
        if (status != null) params.put("status", String.valueOf(status));
        if (limit != null) params.put("limit", String.valueOf(limit));

        return _request(
                "GET",
                "/api/v1/api/v1/notification/logs",
                params,
                null,
                List.class
        );
    }

}