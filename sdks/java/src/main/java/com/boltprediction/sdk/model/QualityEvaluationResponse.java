package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 质量评估完整响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class QualityEvaluationResponse {

    @JsonProperty("sensor_id")
    private String sensorId;

    @JsonProperty("quality_check")
    private QualityCheckResultSchema qualityCheck;

    @JsonProperty("quality_score")
    private SensorQualityScoreSchema qualityScore;

    @JsonProperty("filter_result")
    private FilteredDataResultSchema filterResult;

    @JsonProperty("anomaly_classification")
    private Object anomalyClassification;

    @JsonProperty("evaluate_time")
    private OffsetDateTime evaluateTime;

    public String getSensorId() {
        return sensorId;
    }

    public void setSensorId(String sensorId) {
        this.sensorId = sensorId;
    }

    public QualityCheckResultSchema getQualityCheck() {
        return qualityCheck;
    }

    public void setQualityCheck(QualityCheckResultSchema qualityCheck) {
        this.qualityCheck = qualityCheck;
    }

    public SensorQualityScoreSchema getQualityScore() {
        return qualityScore;
    }

    public void setQualityScore(SensorQualityScoreSchema qualityScore) {
        this.qualityScore = qualityScore;
    }

    public FilteredDataResultSchema getFilterResult() {
        return filterResult;
    }

    public void setFilterResult(FilteredDataResultSchema filterResult) {
        this.filterResult = filterResult;
    }

    public Object getAnomalyClassification() {
        return anomalyClassification;
    }

    public void setAnomalyClassification(Object anomalyClassification) {
        this.anomalyClassification = anomalyClassification;
    }

    public OffsetDateTime getEvaluateTime() {
        return evaluateTime;
    }

    public void setEvaluateTime(OffsetDateTime evaluateTime) {
        this.evaluateTime = evaluateTime;
    }

}