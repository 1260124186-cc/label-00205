package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** CMMS同步请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class CmmsSyncRequest {

    @JsonProperty("config_id")
    private Integer configId;

    @JsonProperty("sync_type")
    private String syncType;

    @JsonProperty("work_order_id")
    private Object workOrderId;

    public Integer getConfigId() {
        return configId;
    }

    public void setConfigId(Integer configId) {
        this.configId = configId;
    }

    public String getSyncType() {
        return syncType;
    }

    public void setSyncType(String syncType) {
        this.syncType = syncType;
    }

    public Object getWorkOrderId() {
        return workOrderId;
    }

    public void setWorkOrderId(Object workOrderId) {
        this.workOrderId = workOrderId;
    }

}