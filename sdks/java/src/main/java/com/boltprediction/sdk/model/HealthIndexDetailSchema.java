package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 健康度指数详情 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class HealthIndexDetailSchema {

    @JsonProperty("hi_score")
    private Double hiScore;

    @JsonProperty("hi_level")
    private String hiLevel;

    @JsonProperty("factors")
    private List<HealthIndexFactorSchema> factors;

    @JsonProperty("preload_stability_score")
    private Double preloadStabilityScore;

    @JsonProperty("alert_frequency_score")
    private Double alertFrequencyScore;

    @JsonProperty("fault_history_score")
    private Double faultHistoryScore;

    @JsonProperty("environmental_stress_score")
    private Double environmentalStressScore;

    @JsonProperty("service_age_score")
    private Double serviceAgeScore;

    @JsonProperty("trend")
    private Object trend;

    @JsonProperty("trend_rate")
    private Object trendRate;

    @JsonProperty("calculate_time")
    private OffsetDateTime calculateTime;

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

    public List<HealthIndexFactorSchema> getFactors() {
        return factors;
    }

    public void setFactors(List<HealthIndexFactorSchema> factors) {
        this.factors = factors;
    }

    public Double getPreloadStabilityScore() {
        return preloadStabilityScore;
    }

    public void setPreloadStabilityScore(Double preloadStabilityScore) {
        this.preloadStabilityScore = preloadStabilityScore;
    }

    public Double getAlertFrequencyScore() {
        return alertFrequencyScore;
    }

    public void setAlertFrequencyScore(Double alertFrequencyScore) {
        this.alertFrequencyScore = alertFrequencyScore;
    }

    public Double getFaultHistoryScore() {
        return faultHistoryScore;
    }

    public void setFaultHistoryScore(Double faultHistoryScore) {
        this.faultHistoryScore = faultHistoryScore;
    }

    public Double getEnvironmentalStressScore() {
        return environmentalStressScore;
    }

    public void setEnvironmentalStressScore(Double environmentalStressScore) {
        this.environmentalStressScore = environmentalStressScore;
    }

    public Double getServiceAgeScore() {
        return serviceAgeScore;
    }

    public void setServiceAgeScore(Double serviceAgeScore) {
        this.serviceAgeScore = serviceAgeScore;
    }

    public Object getTrend() {
        return trend;
    }

    public void setTrend(Object trend) {
        this.trend = trend;
    }

    public Object getTrendRate() {
        return trendRate;
    }

    public void setTrendRate(Object trendRate) {
        this.trendRate = trendRate;
    }

    public OffsetDateTime getCalculateTime() {
        return calculateTime;
    }

    public void setCalculateTime(OffsetDateTime calculateTime) {
        this.calculateTime = calculateTime;
    }

}