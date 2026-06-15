package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** QuotaResponse */
@JsonIgnoreProperties(ignoreUnknown = true)
public class QuotaResponse {

    @JsonProperty("tenant_id")
    private Integer tenantId;

    @JsonProperty("max_models")
    private Integer maxModels;

    @JsonProperty("max_api_calls_per_day")
    private Integer maxApiCallsPerDay;

    @JsonProperty("max_storage_mb")
    private Integer maxStorageMb;

    @JsonProperty("max_users")
    private Integer maxUsers;

    @JsonProperty("max_org_nodes")
    private Integer maxOrgNodes;

    @JsonProperty("current_model_count")
    private Integer currentModelCount;

    @JsonProperty("current_api_calls_today")
    private Integer currentApiCallsToday;

    @JsonProperty("current_storage_mb")
    private Double currentStorageMb;

    @JsonProperty("current_user_count")
    private Integer currentUserCount;

    @JsonProperty("current_org_node_count")
    private Integer currentOrgNodeCount;

    @JsonProperty("create_time")
    private OffsetDateTime createTime;

    @JsonProperty("update_time")
    private OffsetDateTime updateTime;

    public Integer getTenantId() {
        return tenantId;
    }

    public void setTenantId(Integer tenantId) {
        this.tenantId = tenantId;
    }

    public Integer getMaxModels() {
        return maxModels;
    }

    public void setMaxModels(Integer maxModels) {
        this.maxModels = maxModels;
    }

    public Integer getMaxApiCallsPerDay() {
        return maxApiCallsPerDay;
    }

    public void setMaxApiCallsPerDay(Integer maxApiCallsPerDay) {
        this.maxApiCallsPerDay = maxApiCallsPerDay;
    }

    public Integer getMaxStorageMb() {
        return maxStorageMb;
    }

    public void setMaxStorageMb(Integer maxStorageMb) {
        this.maxStorageMb = maxStorageMb;
    }

    public Integer getMaxUsers() {
        return maxUsers;
    }

    public void setMaxUsers(Integer maxUsers) {
        this.maxUsers = maxUsers;
    }

    public Integer getMaxOrgNodes() {
        return maxOrgNodes;
    }

    public void setMaxOrgNodes(Integer maxOrgNodes) {
        this.maxOrgNodes = maxOrgNodes;
    }

    public Integer getCurrentModelCount() {
        return currentModelCount;
    }

    public void setCurrentModelCount(Integer currentModelCount) {
        this.currentModelCount = currentModelCount;
    }

    public Integer getCurrentApiCallsToday() {
        return currentApiCallsToday;
    }

    public void setCurrentApiCallsToday(Integer currentApiCallsToday) {
        this.currentApiCallsToday = currentApiCallsToday;
    }

    public Double getCurrentStorageMb() {
        return currentStorageMb;
    }

    public void setCurrentStorageMb(Double currentStorageMb) {
        this.currentStorageMb = currentStorageMb;
    }

    public Integer getCurrentUserCount() {
        return currentUserCount;
    }

    public void setCurrentUserCount(Integer currentUserCount) {
        this.currentUserCount = currentUserCount;
    }

    public Integer getCurrentOrgNodeCount() {
        return currentOrgNodeCount;
    }

    public void setCurrentOrgNodeCount(Integer currentOrgNodeCount) {
        this.currentOrgNodeCount = currentOrgNodeCount;
    }

    public OffsetDateTime getCreateTime() {
        return createTime;
    }

    public void setCreateTime(OffsetDateTime createTime) {
        this.createTime = createTime;
    }

    public OffsetDateTime getUpdateTime() {
        return updateTime;
    }

    public void setUpdateTime(OffsetDateTime updateTime) {
        this.updateTime = updateTime;
    }

}