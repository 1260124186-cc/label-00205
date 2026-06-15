package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 异常对预警等级影响分析响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AnomalyWarningImpactResponse {

    @JsonProperty("sensor_id")
    private String sensorId;

    @JsonProperty("should_upgrade")
    private Boolean shouldUpgrade;

    @JsonProperty("original_level")
    private Integer originalLevel;

    @JsonProperty("upgraded_level")
    private Integer upgradedLevel;

    @JsonProperty("anomaly_count")
    private Integer anomalyCount;

    @JsonProperty("threshold")
    private Integer threshold;

    @JsonProperty("window_minutes")
    private Integer windowMinutes;

    public String getSensorId() {
        return sensorId;
    }

    public void setSensorId(String sensorId) {
        this.sensorId = sensorId;
    }

    public Boolean getShouldUpgrade() {
        return shouldUpgrade;
    }

    public void setShouldUpgrade(Boolean shouldUpgrade) {
        this.shouldUpgrade = shouldUpgrade;
    }

    public Integer getOriginalLevel() {
        return originalLevel;
    }

    public void setOriginalLevel(Integer originalLevel) {
        this.originalLevel = originalLevel;
    }

    public Integer getUpgradedLevel() {
        return upgradedLevel;
    }

    public void setUpgradedLevel(Integer upgradedLevel) {
        this.upgradedLevel = upgradedLevel;
    }

    public Integer getAnomalyCount() {
        return anomalyCount;
    }

    public void setAnomalyCount(Integer anomalyCount) {
        this.anomalyCount = anomalyCount;
    }

    public Integer getThreshold() {
        return threshold;
    }

    public void setThreshold(Integer threshold) {
        this.threshold = threshold;
    }

    public Integer getWindowMinutes() {
        return windowMinutes;
    }

    public void setWindowMinutes(Integer windowMinutes) {
        this.windowMinutes = windowMinutes;
    }

}