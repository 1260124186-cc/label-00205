package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 通知日志响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class NotificationLogResponse {

    @JsonProperty("id")
    private Integer id;

    @JsonProperty("alert_id")
    private Object alertId;

    @JsonProperty("channel_type")
    private Object channelType;

    @JsonProperty("subscriber_id")
    private Object subscriberId;

    @JsonProperty("subscriber_name")
    private Object subscriberName;

    @JsonProperty("target")
    private Object target;

    @JsonProperty("title")
    private Object title;

    @JsonProperty("content")
    private Object content;

    @JsonProperty("status")
    private String status;

    @JsonProperty("error_message")
    private Object errorMessage;

    @JsonProperty("retry_count")
    private Integer retryCount;

    @JsonProperty("send_time")
    private OffsetDateTime sendTime;

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public Object getAlertId() {
        return alertId;
    }

    public void setAlertId(Object alertId) {
        this.alertId = alertId;
    }

    public Object getChannelType() {
        return channelType;
    }

    public void setChannelType(Object channelType) {
        this.channelType = channelType;
    }

    public Object getSubscriberId() {
        return subscriberId;
    }

    public void setSubscriberId(Object subscriberId) {
        this.subscriberId = subscriberId;
    }

    public Object getSubscriberName() {
        return subscriberName;
    }

    public void setSubscriberName(Object subscriberName) {
        this.subscriberName = subscriberName;
    }

    public Object getTarget() {
        return target;
    }

    public void setTarget(Object target) {
        this.target = target;
    }

    public Object getTitle() {
        return title;
    }

    public void setTitle(Object title) {
        this.title = title;
    }

    public Object getContent() {
        return content;
    }

    public void setContent(Object content) {
        this.content = content;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Object getErrorMessage() {
        return errorMessage;
    }

    public void setErrorMessage(Object errorMessage) {
        this.errorMessage = errorMessage;
    }

    public Integer getRetryCount() {
        return retryCount;
    }

    public void setRetryCount(Integer retryCount) {
        this.retryCount = retryCount;
    }

    public OffsetDateTime getSendTime() {
        return sendTime;
    }

    public void setSendTime(OffsetDateTime sendTime) {
        this.sendTime = sendTime;
    }

}