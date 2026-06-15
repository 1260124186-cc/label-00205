package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 预警阈值配置 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ThresholdConfigSchema {

    @JsonProperty("high_risk_threshold")
    private Integer highRiskThreshold;

    @JsonProperty("medium_risk_threshold")
    private Integer mediumRiskThreshold;

    @JsonProperty("min_normal_preload")
    private Double minNormalPreload;

    @JsonProperty("max_normal_preload")
    private Double maxNormalPreload;

    @JsonProperty("warning_deviation")
    private Double warningDeviation;

    @JsonProperty("critical_deviation")
    private Double criticalDeviation;

    @JsonProperty("auto_create_work_order_level")
    private Integer autoCreateWorkOrderLevel;

    @JsonProperty("default_upgrade_minutes")
    private Integer defaultUpgradeMinutes;

    public Integer getHighRiskThreshold() {
        return highRiskThreshold;
    }

    public void setHighRiskThreshold(Integer highRiskThreshold) {
        this.highRiskThreshold = highRiskThreshold;
    }

    public Integer getMediumRiskThreshold() {
        return mediumRiskThreshold;
    }

    public void setMediumRiskThreshold(Integer mediumRiskThreshold) {
        this.mediumRiskThreshold = mediumRiskThreshold;
    }

    public Double getMinNormalPreload() {
        return minNormalPreload;
    }

    public void setMinNormalPreload(Double minNormalPreload) {
        this.minNormalPreload = minNormalPreload;
    }

    public Double getMaxNormalPreload() {
        return maxNormalPreload;
    }

    public void setMaxNormalPreload(Double maxNormalPreload) {
        this.maxNormalPreload = maxNormalPreload;
    }

    public Double getWarningDeviation() {
        return warningDeviation;
    }

    public void setWarningDeviation(Double warningDeviation) {
        this.warningDeviation = warningDeviation;
    }

    public Double getCriticalDeviation() {
        return criticalDeviation;
    }

    public void setCriticalDeviation(Double criticalDeviation) {
        this.criticalDeviation = criticalDeviation;
    }

    public Integer getAutoCreateWorkOrderLevel() {
        return autoCreateWorkOrderLevel;
    }

    public void setAutoCreateWorkOrderLevel(Integer autoCreateWorkOrderLevel) {
        this.autoCreateWorkOrderLevel = autoCreateWorkOrderLevel;
    }

    public Integer getDefaultUpgradeMinutes() {
        return defaultUpgradeMinutes;
    }

    public void setDefaultUpgradeMinutes(Integer defaultUpgradeMinutes) {
        this.defaultUpgradeMinutes = defaultUpgradeMinutes;
    }

}