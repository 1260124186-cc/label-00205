package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 异常统计响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AnomalyStatisticsResponse {

    @JsonProperty("total_count")
    private Integer totalCount;

    @JsonProperty("confirmed_count")
    private Integer confirmedCount;

    @JsonProperty("unconfirmed_count")
    private Integer unconfirmedCount;

    @JsonProperty("false_positive_count")
    private Integer falsePositiveCount;

    @JsonProperty("true_anomaly_count")
    private Integer trueAnomalyCount;

    @JsonProperty("false_positive_rate")
    private Double falsePositiveRate;

    @JsonProperty("type_distribution")
    private Object typeDistribution;

    @JsonProperty("classification_distribution")
    private Object classificationDistribution;

    @JsonProperty("time_range")
    private Object timeRange;

    public Integer getTotalCount() {
        return totalCount;
    }

    public void setTotalCount(Integer totalCount) {
        this.totalCount = totalCount;
    }

    public Integer getConfirmedCount() {
        return confirmedCount;
    }

    public void setConfirmedCount(Integer confirmedCount) {
        this.confirmedCount = confirmedCount;
    }

    public Integer getUnconfirmedCount() {
        return unconfirmedCount;
    }

    public void setUnconfirmedCount(Integer unconfirmedCount) {
        this.unconfirmedCount = unconfirmedCount;
    }

    public Integer getFalsePositiveCount() {
        return falsePositiveCount;
    }

    public void setFalsePositiveCount(Integer falsePositiveCount) {
        this.falsePositiveCount = falsePositiveCount;
    }

    public Integer getTrueAnomalyCount() {
        return trueAnomalyCount;
    }

    public void setTrueAnomalyCount(Integer trueAnomalyCount) {
        this.trueAnomalyCount = trueAnomalyCount;
    }

    public Double getFalsePositiveRate() {
        return falsePositiveRate;
    }

    public void setFalsePositiveRate(Double falsePositiveRate) {
        this.falsePositiveRate = falsePositiveRate;
    }

    public Object getTypeDistribution() {
        return typeDistribution;
    }

    public void setTypeDistribution(Object typeDistribution) {
        this.typeDistribution = typeDistribution;
    }

    public Object getClassificationDistribution() {
        return classificationDistribution;
    }

    public void setClassificationDistribution(Object classificationDistribution) {
        this.classificationDistribution = classificationDistribution;
    }

    public Object getTimeRange() {
        return timeRange;
    }

    public void setTimeRange(Object timeRange) {
        this.timeRange = timeRange;
    }

}