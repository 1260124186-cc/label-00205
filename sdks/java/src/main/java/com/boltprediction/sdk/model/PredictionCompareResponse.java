package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 预测对比响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class PredictionCompareResponse {

    @JsonProperty("id")
    private Integer id;

    @JsonProperty("work_order_id")
    private Integer workOrderId;

    @JsonProperty("retest_id")
    private Object retestId;

    @JsonProperty("original_prediction_id")
    private Object originalPredictionId;

    @JsonProperty("retest_prediction_id")
    private Object retestPredictionId;

    @JsonProperty("original_status")
    private Object originalStatus;

    @JsonProperty("retest_status")
    private Object retestStatus;

    @JsonProperty("original_risk_score")
    private Object originalRiskScore;

    @JsonProperty("retest_risk_score")
    private Object retestRiskScore;

    @JsonProperty("original_confidence")
    private Object originalConfidence;

    @JsonProperty("retest_confidence")
    private Object retestConfidence;

    @JsonProperty("risk_change")
    private Object riskChange;

    @JsonProperty("risk_delta")
    private Object riskDelta;

    @JsonProperty("status_match")
    private Object statusMatch;

    @JsonProperty("is_false_positive")
    private Object isFalsePositive;

    @JsonProperty("is_recurring")
    private Object isRecurring;

    @JsonProperty("comparison_detail")
    private Object comparisonDetail;

    @JsonProperty("create_time")
    private OffsetDateTime createTime;

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public Integer getWorkOrderId() {
        return workOrderId;
    }

    public void setWorkOrderId(Integer workOrderId) {
        this.workOrderId = workOrderId;
    }

    public Object getRetestId() {
        return retestId;
    }

    public void setRetestId(Object retestId) {
        this.retestId = retestId;
    }

    public Object getOriginalPredictionId() {
        return originalPredictionId;
    }

    public void setOriginalPredictionId(Object originalPredictionId) {
        this.originalPredictionId = originalPredictionId;
    }

    public Object getRetestPredictionId() {
        return retestPredictionId;
    }

    public void setRetestPredictionId(Object retestPredictionId) {
        this.retestPredictionId = retestPredictionId;
    }

    public Object getOriginalStatus() {
        return originalStatus;
    }

    public void setOriginalStatus(Object originalStatus) {
        this.originalStatus = originalStatus;
    }

    public Object getRetestStatus() {
        return retestStatus;
    }

    public void setRetestStatus(Object retestStatus) {
        this.retestStatus = retestStatus;
    }

    public Object getOriginalRiskScore() {
        return originalRiskScore;
    }

    public void setOriginalRiskScore(Object originalRiskScore) {
        this.originalRiskScore = originalRiskScore;
    }

    public Object getRetestRiskScore() {
        return retestRiskScore;
    }

    public void setRetestRiskScore(Object retestRiskScore) {
        this.retestRiskScore = retestRiskScore;
    }

    public Object getOriginalConfidence() {
        return originalConfidence;
    }

    public void setOriginalConfidence(Object originalConfidence) {
        this.originalConfidence = originalConfidence;
    }

    public Object getRetestConfidence() {
        return retestConfidence;
    }

    public void setRetestConfidence(Object retestConfidence) {
        this.retestConfidence = retestConfidence;
    }

    public Object getRiskChange() {
        return riskChange;
    }

    public void setRiskChange(Object riskChange) {
        this.riskChange = riskChange;
    }

    public Object getRiskDelta() {
        return riskDelta;
    }

    public void setRiskDelta(Object riskDelta) {
        this.riskDelta = riskDelta;
    }

    public Object getStatusMatch() {
        return statusMatch;
    }

    public void setStatusMatch(Object statusMatch) {
        this.statusMatch = statusMatch;
    }

    public Object getIsFalsePositive() {
        return isFalsePositive;
    }

    public void setIsFalsePositive(Object isFalsePositive) {
        this.isFalsePositive = isFalsePositive;
    }

    public Object getIsRecurring() {
        return isRecurring;
    }

    public void setIsRecurring(Object isRecurring) {
        this.isRecurring = isRecurring;
    }

    public Object getComparisonDetail() {
        return comparisonDetail;
    }

    public void setComparisonDetail(Object comparisonDetail) {
        this.comparisonDetail = comparisonDetail;
    }

    public OffsetDateTime getCreateTime() {
        return createTime;
    }

    public void setCreateTime(OffsetDateTime createTime) {
        this.createTime = createTime;
    }

}