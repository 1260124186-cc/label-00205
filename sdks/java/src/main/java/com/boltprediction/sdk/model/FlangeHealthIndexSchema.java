package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 法兰面健康度指数（聚合） */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FlangeHealthIndexSchema {

    @JsonProperty("flange_id")
    private String flangeId;

    @JsonProperty("flange_name")
    private Object flangeName;

    @JsonProperty("hi_score")
    private Double hiScore;

    @JsonProperty("hi_level")
    private String hiLevel;

    @JsonProperty("worst_bolt_hi")
    private Double worstBoltHi;

    @JsonProperty("worst_bolt_id")
    private String worstBoltId;

    @JsonProperty("average_bolt_hi")
    private Double averageBoltHi;

    @JsonProperty("median_bolt_hi")
    private Double medianBoltHi;

    @JsonProperty("degradation_rate")
    private Double degradationRate;

    @JsonProperty("bolt_count")
    private Integer boltCount;

    @JsonProperty("healthy_bolt_count")
    private Integer healthyBoltCount;

    @JsonProperty("warning_bolt_count")
    private Integer warningBoltCount;

    @JsonProperty("critical_bolt_count")
    private Integer criticalBoltCount;

    @JsonProperty("bolts_health")
    private List<BoltHealthIndexSchema> boltsHealth;

    @JsonProperty("trend")
    private Object trend;

    @JsonProperty("calculate_time")
    private OffsetDateTime calculateTime;

    public String getFlangeId() {
        return flangeId;
    }

    public void setFlangeId(String flangeId) {
        this.flangeId = flangeId;
    }

    public Object getFlangeName() {
        return flangeName;
    }

    public void setFlangeName(Object flangeName) {
        this.flangeName = flangeName;
    }

    public Double getHiScore() {
        return hiScore;
    }

    public void setHiScore(Double hiScore) {
        this.hiScore = hiScore;
    }

    public String getHiLevel() {
        return hiLevel;
    }

    public void setHiLevel(String hiLevel) {
        this.hiLevel = hiLevel;
    }

    public Double getWorstBoltHi() {
        return worstBoltHi;
    }

    public void setWorstBoltHi(Double worstBoltHi) {
        this.worstBoltHi = worstBoltHi;
    }

    public String getWorstBoltId() {
        return worstBoltId;
    }

    public void setWorstBoltId(String worstBoltId) {
        this.worstBoltId = worstBoltId;
    }

    public Double getAverageBoltHi() {
        return averageBoltHi;
    }

    public void setAverageBoltHi(Double averageBoltHi) {
        this.averageBoltHi = averageBoltHi;
    }

    public Double getMedianBoltHi() {
        return medianBoltHi;
    }

    public void setMedianBoltHi(Double medianBoltHi) {
        this.medianBoltHi = medianBoltHi;
    }

    public Double getDegradationRate() {
        return degradationRate;
    }

    public void setDegradationRate(Double degradationRate) {
        this.degradationRate = degradationRate;
    }

    public Integer getBoltCount() {
        return boltCount;
    }

    public void setBoltCount(Integer boltCount) {
        this.boltCount = boltCount;
    }

    public Integer getHealthyBoltCount() {
        return healthyBoltCount;
    }

    public void setHealthyBoltCount(Integer healthyBoltCount) {
        this.healthyBoltCount = healthyBoltCount;
    }

    public Integer getWarningBoltCount() {
        return warningBoltCount;
    }

    public void setWarningBoltCount(Integer warningBoltCount) {
        this.warningBoltCount = warningBoltCount;
    }

    public Integer getCriticalBoltCount() {
        return criticalBoltCount;
    }

    public void setCriticalBoltCount(Integer criticalBoltCount) {
        this.criticalBoltCount = criticalBoltCount;
    }

    public List<BoltHealthIndexSchema> getBoltsHealth() {
        return boltsHealth;
    }

    public void setBoltsHealth(List<BoltHealthIndexSchema> boltsHealth) {
        this.boltsHealth = boltsHealth;
    }

    public Object getTrend() {
        return trend;
    }

    public void setTrend(Object trend) {
        this.trend = trend;
    }

    public OffsetDateTime getCalculateTime() {
        return calculateTime;
    }

    public void setCalculateTime(OffsetDateTime calculateTime) {
        this.calculateTime = calculateTime;
    }

}