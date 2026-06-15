package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 配置中心整体响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ConfigCenterResponse {

    @JsonProperty("warning_strategy")
    private WarningStrategyConfigSchema warningStrategy;

    @JsonProperty("thresholds")
    private ThresholdConfigSchema thresholds;

    @JsonProperty("scheduled_jobs")
    private List<ScheduledJobSchema> scheduledJobs;

    @JsonProperty("updated_at")
    private OffsetDateTime updatedAt;

    public WarningStrategyConfigSchema getWarningStrategy() {
        return warningStrategy;
    }

    public void setWarningStrategy(WarningStrategyConfigSchema warningStrategy) {
        this.warningStrategy = warningStrategy;
    }

    public ThresholdConfigSchema getThresholds() {
        return thresholds;
    }

    public void setThresholds(ThresholdConfigSchema thresholds) {
        this.thresholds = thresholds;
    }

    public List<ScheduledJobSchema> getScheduledJobs() {
        return scheduledJobs;
    }

    public void setScheduledJobs(List<ScheduledJobSchema> scheduledJobs) {
        this.scheduledJobs = scheduledJobs;
    }

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(OffsetDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

}