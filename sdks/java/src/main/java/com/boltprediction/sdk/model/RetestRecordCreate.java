package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 创建复测记录请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class RetestRecordCreate {

    @JsonProperty("work_order_id")
    private Integer workOrderId;

    @JsonProperty("retest_time")
    private Object retestTime;

    @JsonProperty("retester_id")
    private Object retesterId;

    @JsonProperty("retester_name")
    private Object retesterName;

    @JsonProperty("retest_result")
    private String retestResult;

    @JsonProperty("measured_value")
    private Object measuredValue;

    @JsonProperty("data_points")
    private Object dataPoints;

    @JsonProperty("before_risk_score")
    private Object beforeRiskScore;

    @JsonProperty("after_risk_score")
    private Object afterRiskScore;

    @JsonProperty("status_after_retest")
    private Object statusAfterRetest;

    @JsonProperty("confidence")
    private Object confidence;

    @JsonProperty("retest_notes")
    private Object retestNotes;

    @JsonProperty("photos")
    private Object photos;

    @JsonProperty("extra_info")
    private Object extraInfo;

    @JsonProperty("auto_repredict")
    private Object autoRepredict;

    public Integer getWorkOrderId() {
        return workOrderId;
    }

    public void setWorkOrderId(Integer workOrderId) {
        this.workOrderId = workOrderId;
    }

    public Object getRetestTime() {
        return retestTime;
    }

    public void setRetestTime(Object retestTime) {
        this.retestTime = retestTime;
    }

    public Object getRetesterId() {
        return retesterId;
    }

    public void setRetesterId(Object retesterId) {
        this.retesterId = retesterId;
    }

    public Object getRetesterName() {
        return retesterName;
    }

    public void setRetesterName(Object retesterName) {
        this.retesterName = retesterName;
    }

    public String getRetestResult() {
        return retestResult;
    }

    public void setRetestResult(String retestResult) {
        this.retestResult = retestResult;
    }

    public Object getMeasuredValue() {
        return measuredValue;
    }

    public void setMeasuredValue(Object measuredValue) {
        this.measuredValue = measuredValue;
    }

    public Object getDataPoints() {
        return dataPoints;
    }

    public void setDataPoints(Object dataPoints) {
        this.dataPoints = dataPoints;
    }

    public Object getBeforeRiskScore() {
        return beforeRiskScore;
    }

    public void setBeforeRiskScore(Object beforeRiskScore) {
        this.beforeRiskScore = beforeRiskScore;
    }

    public Object getAfterRiskScore() {
        return afterRiskScore;
    }

    public void setAfterRiskScore(Object afterRiskScore) {
        this.afterRiskScore = afterRiskScore;
    }

    public Object getStatusAfterRetest() {
        return statusAfterRetest;
    }

    public void setStatusAfterRetest(Object statusAfterRetest) {
        this.statusAfterRetest = statusAfterRetest;
    }

    public Object getConfidence() {
        return confidence;
    }

    public void setConfidence(Object confidence) {
        this.confidence = confidence;
    }

    public Object getRetestNotes() {
        return retestNotes;
    }

    public void setRetestNotes(Object retestNotes) {
        this.retestNotes = retestNotes;
    }

    public Object getPhotos() {
        return photos;
    }

    public void setPhotos(Object photos) {
        this.photos = photos;
    }

    public Object getExtraInfo() {
        return extraInfo;
    }

    public void setExtraInfo(Object extraInfo) {
        this.extraInfo = extraInfo;
    }

    public Object getAutoRepredict() {
        return autoRepredict;
    }

    public void setAutoRepredict(Object autoRepredict) {
        this.autoRepredict = autoRepredict;
    }

}