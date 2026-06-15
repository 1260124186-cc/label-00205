package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** CMMS同步日志响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class CmmsSyncLogResponse {

    @JsonProperty("id")
    private Integer id;

    @JsonProperty("config_id")
    private Object configId;

    @JsonProperty("sync_type")
    private Object syncType;

    @JsonProperty("sync_direction")
    private Object syncDirection;

    @JsonProperty("work_order_id")
    private Object workOrderId;

    @JsonProperty("external_id")
    private Object externalId;

    @JsonProperty("status")
    private Object status;

    @JsonProperty("error_message")
    private Object errorMessage;

    @JsonProperty("retry_count")
    private Object retryCount;

    @JsonProperty("sync_time")
    private Object syncTime;

    @JsonProperty("create_time")
    private OffsetDateTime createTime;

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public Object getConfigId() {
        return configId;
    }

    public void setConfigId(Object configId) {
        this.configId = configId;
    }

    public Object getSyncType() {
        return syncType;
    }

    public void setSyncType(Object syncType) {
        this.syncType = syncType;
    }

    public Object getSyncDirection() {
        return syncDirection;
    }

    public void setSyncDirection(Object syncDirection) {
        this.syncDirection = syncDirection;
    }

    public Object getWorkOrderId() {
        return workOrderId;
    }

    public void setWorkOrderId(Object workOrderId) {
        this.workOrderId = workOrderId;
    }

    public Object getExternalId() {
        return externalId;
    }

    public void setExternalId(Object externalId) {
        this.externalId = externalId;
    }

    public Object getStatus() {
        return status;
    }

    public void setStatus(Object status) {
        this.status = status;
    }

    public Object getErrorMessage() {
        return errorMessage;
    }

    public void setErrorMessage(Object errorMessage) {
        this.errorMessage = errorMessage;
    }

    public Object getRetryCount() {
        return retryCount;
    }

    public void setRetryCount(Object retryCount) {
        this.retryCount = retryCount;
    }

    public Object getSyncTime() {
        return syncTime;
    }

    public void setSyncTime(Object syncTime) {
        this.syncTime = syncTime;
    }

    public OffsetDateTime getCreateTime() {
        return createTime;
    }

    public void setCreateTime(OffsetDateTime createTime) {
        this.createTime = createTime;
    }

}