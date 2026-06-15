package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 调度任务更新请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class SchedulerJobUpdateRequest {

    @JsonProperty("enabled")
    private Object enabled;

    @JsonProperty("cron")
    private Object cron;

    public Object getEnabled() {
        return enabled;
    }

    public void setEnabled(Object enabled) {
        this.enabled = enabled;
    }

    public Object getCron() {
        return cron;
    }

    public void setCron(Object cron) {
        this.cron = cron;
    }

}