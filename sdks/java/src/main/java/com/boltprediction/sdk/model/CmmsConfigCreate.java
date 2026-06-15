package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 创建CMMS配置请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class CmmsConfigCreate {

    @JsonProperty("system_name")
    private String systemName;

    @JsonProperty("system_type")
    private Object systemType;

    @JsonProperty("base_url")
    private Object baseUrl;

    @JsonProperty("auth_type")
    private Object authType;

    @JsonProperty("auth_config")
    private Object authConfig;

    @JsonProperty("work_order_sync")
    private Object workOrderSync;

    @JsonProperty("work_order_webhook_url")
    private Object workOrderWebhookUrl;

    @JsonProperty("work_order_push_url")
    private Object workOrderPushUrl;

    @JsonProperty("status_mapping")
    private Object statusMapping;

    @JsonProperty("priority_mapping")
    private Object priorityMapping;

    @JsonProperty("field_mapping")
    private Object fieldMapping;

    @JsonProperty("enabled")
    private Object enabled;

    @JsonProperty("sync_direction")
    private Object syncDirection;

    @JsonProperty("sync_interval")
    private Object syncInterval;

    @JsonProperty("tenant_id")
    private Object tenantId;

    @JsonProperty("extra_info")
    private Object extraInfo;

    public String getSystemName() {
        return systemName;
    }

    public void setSystemName(String systemName) {
        this.systemName = systemName;
    }

    public Object getSystemType() {
        return systemType;
    }

    public void setSystemType(Object systemType) {
        this.systemType = systemType;
    }

    public Object getBaseUrl() {
        return baseUrl;
    }

    public void setBaseUrl(Object baseUrl) {
        this.baseUrl = baseUrl;
    }

    public Object getAuthType() {
        return authType;
    }

    public void setAuthType(Object authType) {
        this.authType = authType;
    }

    public Object getAuthConfig() {
        return authConfig;
    }

    public void setAuthConfig(Object authConfig) {
        this.authConfig = authConfig;
    }

    public Object getWorkOrderSync() {
        return workOrderSync;
    }

    public void setWorkOrderSync(Object workOrderSync) {
        this.workOrderSync = workOrderSync;
    }

    public Object getWorkOrderWebhookUrl() {
        return workOrderWebhookUrl;
    }

    public void setWorkOrderWebhookUrl(Object workOrderWebhookUrl) {
        this.workOrderWebhookUrl = workOrderWebhookUrl;
    }

    public Object getWorkOrderPushUrl() {
        return workOrderPushUrl;
    }

    public void setWorkOrderPushUrl(Object workOrderPushUrl) {
        this.workOrderPushUrl = workOrderPushUrl;
    }

    public Object getStatusMapping() {
        return statusMapping;
    }

    public void setStatusMapping(Object statusMapping) {
        this.statusMapping = statusMapping;
    }

    public Object getPriorityMapping() {
        return priorityMapping;
    }

    public void setPriorityMapping(Object priorityMapping) {
        this.priorityMapping = priorityMapping;
    }

    public Object getFieldMapping() {
        return fieldMapping;
    }

    public void setFieldMapping(Object fieldMapping) {
        this.fieldMapping = fieldMapping;
    }

    public Object getEnabled() {
        return enabled;
    }

    public void setEnabled(Object enabled) {
        this.enabled = enabled;
    }

    public Object getSyncDirection() {
        return syncDirection;
    }

    public void setSyncDirection(Object syncDirection) {
        this.syncDirection = syncDirection;
    }

    public Object getSyncInterval() {
        return syncInterval;
    }

    public void setSyncInterval(Object syncInterval) {
        this.syncInterval = syncInterval;
    }

    public Object getTenantId() {
        return tenantId;
    }

    public void setTenantId(Object tenantId) {
        this.tenantId = tenantId;
    }

    public Object getExtraInfo() {
        return extraInfo;
    }

    public void setExtraInfo(Object extraInfo) {
        this.extraInfo = extraInfo;
    }

}