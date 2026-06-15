package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** QuotaUpdateRequest */
@JsonIgnoreProperties(ignoreUnknown = true)
public class QuotaUpdateRequest {

    @JsonProperty("max_models")
    private Object maxModels;

    @JsonProperty("max_api_calls_per_day")
    private Object maxApiCallsPerDay;

    @JsonProperty("max_storage_mb")
    private Object maxStorageMb;

    @JsonProperty("max_users")
    private Object maxUsers;

    @JsonProperty("max_org_nodes")
    private Object maxOrgNodes;

    public Object getMaxModels() {
        return maxModels;
    }

    public void setMaxModels(Object maxModels) {
        this.maxModels = maxModels;
    }

    public Object getMaxApiCallsPerDay() {
        return maxApiCallsPerDay;
    }

    public void setMaxApiCallsPerDay(Object maxApiCallsPerDay) {
        this.maxApiCallsPerDay = maxApiCallsPerDay;
    }

    public Object getMaxStorageMb() {
        return maxStorageMb;
    }

    public void setMaxStorageMb(Object maxStorageMb) {
        this.maxStorageMb = maxStorageMb;
    }

    public Object getMaxUsers() {
        return maxUsers;
    }

    public void setMaxUsers(Object maxUsers) {
        this.maxUsers = maxUsers;
    }

    public Object getMaxOrgNodes() {
        return maxOrgNodes;
    }

    public void setMaxOrgNodes(Object maxOrgNodes) {
        this.maxOrgNodes = maxOrgNodes;
    }

}