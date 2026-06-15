package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 异常联动结果 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AnomalyLinkResultSchema {

    @JsonProperty("sensor_id")
    private String sensorId;

    @JsonProperty("total_anomalies")
    private Integer totalAnomalies;

    @JsonProperty("true_anomalies")
    private Integer trueAnomalies;

    @JsonProperty("collection_anomalies")
    private Integer collectionAnomalies;

    @JsonProperty("uncertain_anomalies")
    private Integer uncertainAnomalies;

    @JsonProperty("mixed_anomalies")
    private Integer mixedAnomalies;

    @JsonProperty("classified_anomalies")
    private List<AnomalyClassificationSchema> classifiedAnomalies;

    public String getSensorId() {
        return sensorId;
    }

    public void setSensorId(String sensorId) {
        this.sensorId = sensorId;
    }

    public Integer getTotalAnomalies() {
        return totalAnomalies;
    }

    public void setTotalAnomalies(Integer totalAnomalies) {
        this.totalAnomalies = totalAnomalies;
    }

    public Integer getTrueAnomalies() {
        return trueAnomalies;
    }

    public void setTrueAnomalies(Integer trueAnomalies) {
        this.trueAnomalies = trueAnomalies;
    }

    public Integer getCollectionAnomalies() {
        return collectionAnomalies;
    }

    public void setCollectionAnomalies(Integer collectionAnomalies) {
        this.collectionAnomalies = collectionAnomalies;
    }

    public Integer getUncertainAnomalies() {
        return uncertainAnomalies;
    }

    public void setUncertainAnomalies(Integer uncertainAnomalies) {
        this.uncertainAnomalies = uncertainAnomalies;
    }

    public Integer getMixedAnomalies() {
        return mixedAnomalies;
    }

    public void setMixedAnomalies(Integer mixedAnomalies) {
        this.mixedAnomalies = mixedAnomalies;
    }

    public List<AnomalyClassificationSchema> getClassifiedAnomalies() {
        return classifiedAnomalies;
    }

    public void setClassifiedAnomalies(List<AnomalyClassificationSchema> classifiedAnomalies) {
        this.classifiedAnomalies = classifiedAnomalies;
    }

}