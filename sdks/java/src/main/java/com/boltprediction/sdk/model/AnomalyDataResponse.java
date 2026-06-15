package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 异常数据响应模型

对应 sc_anomaly_data 表的完整字段，
包含异常信息、分类、确认标注等。 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AnomalyDataResponse {

    @JsonProperty("id")
    private Integer id;

    @JsonProperty("sensor_id")
    private String sensorId;

    @JsonProperty("anomaly_value")
    private Object anomalyValue;

    @JsonProperty("anomaly_type")
    private Object anomalyType;

    @JsonProperty("anomaly_score")
    private Object anomalyScore;

    @JsonProperty("original_time")
    private Object originalTime;

    @JsonProperty("details")
    private Object details;

    @JsonProperty("classification")
    private Object classification;

    @JsonProperty("classification_confidence")
    private Object classificationConfidence;

    @JsonProperty("collection_subtype")
    private Object collectionSubtype;

    @JsonProperty("true_anomaly_subtype")
    private Object trueAnomalySubtype;

    @JsonProperty("classification_evidence")
    private Object classificationEvidence;

    @JsonProperty("is_confirmed")
    private Boolean isConfirmed;

    @JsonProperty("is_false_positive")
    private Boolean isFalsePositive;

    @JsonProperty("confirmed_by")
    private Object confirmedBy;

    @JsonProperty("confirmed_time")
    private Object confirmedTime;

    @JsonProperty("confirm_note")
    private Object confirmNote;

    @JsonProperty("tenant_id")
    private Object tenantId;

    @JsonProperty("create_time")
    private Object createTime;

    @JsonProperty("update_time")
    private Object updateTime;

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public String getSensorId() {
        return sensorId;
    }

    public void setSensorId(String sensorId) {
        this.sensorId = sensorId;
    }

    public Object getAnomalyValue() {
        return anomalyValue;
    }

    public void setAnomalyValue(Object anomalyValue) {
        this.anomalyValue = anomalyValue;
    }

    public Object getAnomalyType() {
        return anomalyType;
    }

    public void setAnomalyType(Object anomalyType) {
        this.anomalyType = anomalyType;
    }

    public Object getAnomalyScore() {
        return anomalyScore;
    }

    public void setAnomalyScore(Object anomalyScore) {
        this.anomalyScore = anomalyScore;
    }

    public Object getOriginalTime() {
        return originalTime;
    }

    public void setOriginalTime(Object originalTime) {
        this.originalTime = originalTime;
    }

    public Object getDetails() {
        return details;
    }

    public void setDetails(Object details) {
        this.details = details;
    }

    public Object getClassification() {
        return classification;
    }

    public void setClassification(Object classification) {
        this.classification = classification;
    }

    public Object getClassificationConfidence() {
        return classificationConfidence;
    }

    public void setClassificationConfidence(Object classificationConfidence) {
        this.classificationConfidence = classificationConfidence;
    }

    public Object getCollectionSubtype() {
        return collectionSubtype;
    }

    public void setCollectionSubtype(Object collectionSubtype) {
        this.collectionSubtype = collectionSubtype;
    }

    public Object getTrueAnomalySubtype() {
        return trueAnomalySubtype;
    }

    public void setTrueAnomalySubtype(Object trueAnomalySubtype) {
        this.trueAnomalySubtype = trueAnomalySubtype;
    }

    public Object getClassificationEvidence() {
        return classificationEvidence;
    }

    public void setClassificationEvidence(Object classificationEvidence) {
        this.classificationEvidence = classificationEvidence;
    }

    public Boolean getIsConfirmed() {
        return isConfirmed;
    }

    public void setIsConfirmed(Boolean isConfirmed) {
        this.isConfirmed = isConfirmed;
    }

    public Boolean getIsFalsePositive() {
        return isFalsePositive;
    }

    public void setIsFalsePositive(Boolean isFalsePositive) {
        this.isFalsePositive = isFalsePositive;
    }

    public Object getConfirmedBy() {
        return confirmedBy;
    }

    public void setConfirmedBy(Object confirmedBy) {
        this.confirmedBy = confirmedBy;
    }

    public Object getConfirmedTime() {
        return confirmedTime;
    }

    public void setConfirmedTime(Object confirmedTime) {
        this.confirmedTime = confirmedTime;
    }

    public Object getConfirmNote() {
        return confirmNote;
    }

    public void setConfirmNote(Object confirmNote) {
        this.confirmNote = confirmNote;
    }

    public Object getTenantId() {
        return tenantId;
    }

    public void setTenantId(Object tenantId) {
        this.tenantId = tenantId;
    }

    public Object getCreateTime() {
        return createTime;
    }

    public void setCreateTime(Object createTime) {
        this.createTime = createTime;
    }

    public Object getUpdateTime() {
        return updateTime;
    }

    public void setUpdateTime(Object updateTime) {
        this.updateTime = updateTime;
    }

}