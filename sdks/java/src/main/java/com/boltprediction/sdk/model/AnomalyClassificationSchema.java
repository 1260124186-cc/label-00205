package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 异常分类结果 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AnomalyClassificationSchema {

    @JsonProperty("anomaly_id")
    private Object anomalyId;

    @JsonProperty("sensor_id")
    private String sensorId;

    @JsonProperty("anomaly_value")
    private Double anomalyValue;

    @JsonProperty("anomaly_type")
    private String anomalyType;

    @JsonProperty("classification")
    private String classification;

    @JsonProperty("classification_confidence")
    private Double classificationConfidence;

    @JsonProperty("collection_subtype")
    private Object collectionSubtype;

    @JsonProperty("true_anomaly_subtype")
    private Object trueAnomalySubtype;

    @JsonProperty("evidence")
    private Map<String, Object> evidence;

    @JsonProperty("original_time")
    private Object originalTime;

    public Object getAnomalyId() {
        return anomalyId;
    }

    public void setAnomalyId(Object anomalyId) {
        this.anomalyId = anomalyId;
    }

    public String getSensorId() {
        return sensorId;
    }

    public void setSensorId(String sensorId) {
        this.sensorId = sensorId;
    }

    public Double getAnomalyValue() {
        return anomalyValue;
    }

    public void setAnomalyValue(Double anomalyValue) {
        this.anomalyValue = anomalyValue;
    }

    public String getAnomalyType() {
        return anomalyType;
    }

    public void setAnomalyType(String anomalyType) {
        this.anomalyType = anomalyType;
    }

    public String getClassification() {
        return classification;
    }

    public void setClassification(String classification) {
        this.classification = classification;
    }

    public Double getClassificationConfidence() {
        return classificationConfidence;
    }

    public void setClassificationConfidence(Double classificationConfidence) {
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

    public Map<String, Object> getEvidence() {
        return evidence;
    }

    public void setEvidence(Map<String, Object> evidence) {
        this.evidence = evidence;
    }

    public Object getOriginalTime() {
        return originalTime;
    }

    public void setOriginalTime(Object originalTime) {
        this.originalTime = originalTime;
    }

}