package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 调度任务触发响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class SchedulerTriggerResponse {

    @JsonProperty("job_name")
    private String jobName;

    @JsonProperty("status")
    private String status;

    @JsonProperty("message")
    private String message;

    @JsonProperty("log_id")
    private Object logId;

    @JsonProperty("is_leader")
    private Object isLeader;

    public String getJobName() {
        return jobName;
    }

    public void setJobName(String jobName) {
        this.jobName = jobName;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public Object getLogId() {
        return logId;
    }

    public void setLogId(Object logId) {
        this.logId = logId;
    }

    public Object getIsLeader() {
        return isLeader;
    }

    public void setIsLeader(Object isLeader) {
        this.isLeader = isLeader;
    }

}