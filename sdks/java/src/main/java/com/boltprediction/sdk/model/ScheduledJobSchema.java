package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 调度任务信息 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ScheduledJobSchema {

    @JsonProperty("id")
    private String id;

    @JsonProperty("name")
    private String name;

    @JsonProperty("enabled")
    private Boolean enabled;

    @JsonProperty("cron")
    private String cron;

    @JsonProperty("next_run")
    private Object nextRun;

    @JsonProperty("description")
    private Object description;

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public Boolean getEnabled() {
        return enabled;
    }

    public void setEnabled(Boolean enabled) {
        this.enabled = enabled;
    }

    public String getCron() {
        return cron;
    }

    public void setCron(String cron) {
        this.cron = cron;
    }

    public Object getNextRun() {
        return nextRun;
    }

    public void setNextRun(Object nextRun) {
        this.nextRun = nextRun;
    }

    public Object getDescription() {
        return description;
    }

    public void setDescription(Object description) {
        this.description = description;
    }

}