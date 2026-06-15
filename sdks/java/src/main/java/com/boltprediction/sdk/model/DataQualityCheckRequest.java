package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 数据质量检查请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class DataQualityCheckRequest {

    @JsonProperty("sensor_id")
    private String sensorId;

    @JsonProperty("data")
    private List<List<Object>> data;

    @JsonProperty("include_anomaly_classification")
    private Boolean includeAnomalyClassification;

    public String getSensorId() {
        return sensorId;
    }

    public void setSensorId(String sensorId) {
        this.sensorId = sensorId;
    }

    public List<List<Object>> getData() {
        return data;
    }

    public void setData(List<List<Object>> data) {
        this.data = data;
    }

    public Boolean getIncludeAnomalyClassification() {
        return includeAnomalyClassification;
    }

    public void setIncludeAnomalyClassification(Boolean includeAnomalyClassification) {
        this.includeAnomalyClassification = includeAnomalyClassification;
    }

}