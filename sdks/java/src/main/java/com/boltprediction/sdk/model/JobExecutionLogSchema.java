package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 任务执行日志 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class JobExecutionLogSchema {

    @JsonProperty("id")
    private Integer id;

    @JsonProperty("job_name")
    private String jobName;

    @JsonProperty("job_type")
    private String jobType;

    @JsonProperty("trigger_type")
    private String triggerType;

    @JsonProperty("status")
    private String status;

    @JsonProperty("start_time")
    private OffsetDateTime startTime;

    @JsonProperty("end_time")
    private Object endTime;

    @JsonProperty("duration_seconds")
    private Object durationSeconds;

    @JsonProperty("total_nodes")
    private Integer totalNodes;

    @JsonProperty("success_count")
    private Integer successCount;

    @JsonProperty("failed_count")
    private Integer failedCount;

    @JsonProperty("skipped_count")
    private Integer skippedCount;

    @JsonProperty("shard_index")
    private Object shardIndex;

    @JsonProperty("shard_total")
    private Object shardTotal;

    @JsonProperty("bolt_id_min")
    private Object boltIdMin;

    @JsonProperty("bolt_id_max")
    private Object boltIdMax;

    @JsonProperty("instance_id")
    private Object instanceId;

    @JsonProperty("error_summary")
    private Object errorSummary;

    @JsonProperty("error_details")
    private Object errorDetails;

    @JsonProperty("create_time")
    private OffsetDateTime createTime;

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public String getJobName() {
        return jobName;
    }

    public void setJobName(String jobName) {
        this.jobName = jobName;
    }

    public String getJobType() {
        return jobType;
    }

    public void setJobType(String jobType) {
        this.jobType = jobType;
    }

    public String getTriggerType() {
        return triggerType;
    }

    public void setTriggerType(String triggerType) {
        this.triggerType = triggerType;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public OffsetDateTime getStartTime() {
        return startTime;
    }

    public void setStartTime(OffsetDateTime startTime) {
        this.startTime = startTime;
    }

    public Object getEndTime() {
        return endTime;
    }

    public void setEndTime(Object endTime) {
        this.endTime = endTime;
    }

    public Object getDurationSeconds() {
        return durationSeconds;
    }

    public void setDurationSeconds(Object durationSeconds) {
        this.durationSeconds = durationSeconds;
    }

    public Integer getTotalNodes() {
        return totalNodes;
    }

    public void setTotalNodes(Integer totalNodes) {
        this.totalNodes = totalNodes;
    }

    public Integer getSuccessCount() {
        return successCount;
    }

    public void setSuccessCount(Integer successCount) {
        this.successCount = successCount;
    }

    public Integer getFailedCount() {
        return failedCount;
    }

    public void setFailedCount(Integer failedCount) {
        this.failedCount = failedCount;
    }

    public Integer getSkippedCount() {
        return skippedCount;
    }

    public void setSkippedCount(Integer skippedCount) {
        this.skippedCount = skippedCount;
    }

    public Object getShardIndex() {
        return shardIndex;
    }

    public void setShardIndex(Object shardIndex) {
        this.shardIndex = shardIndex;
    }

    public Object getShardTotal() {
        return shardTotal;
    }

    public void setShardTotal(Object shardTotal) {
        this.shardTotal = shardTotal;
    }

    public Object getBoltIdMin() {
        return boltIdMin;
    }

    public void setBoltIdMin(Object boltIdMin) {
        this.boltIdMin = boltIdMin;
    }

    public Object getBoltIdMax() {
        return boltIdMax;
    }

    public void setBoltIdMax(Object boltIdMax) {
        this.boltIdMax = boltIdMax;
    }

    public Object getInstanceId() {
        return instanceId;
    }

    public void setInstanceId(Object instanceId) {
        this.instanceId = instanceId;
    }

    public Object getErrorSummary() {
        return errorSummary;
    }

    public void setErrorSummary(Object errorSummary) {
        this.errorSummary = errorSummary;
    }

    public Object getErrorDetails() {
        return errorDetails;
    }

    public void setErrorDetails(Object errorDetails) {
        this.errorDetails = errorDetails;
    }

    public OffsetDateTime getCreateTime() {
        return createTime;
    }

    public void setCreateTime(OffsetDateTime createTime) {
        this.createTime = createTime;
    }

}