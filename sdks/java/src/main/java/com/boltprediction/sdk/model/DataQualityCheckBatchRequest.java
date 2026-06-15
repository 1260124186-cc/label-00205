package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 批量数据质量检查请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class DataQualityCheckBatchRequest {

    @JsonProperty("sensors_data")
    private Map<String, List<List<Object>>> sensorsData;

    public Map<String, List<List<Object>>> getSensorsData() {
        return sensorsData;
    }

    public void setSensorsData(Map<String, List<List<Object>>> sensorsData) {
        this.sensorsData = sensorsData;
    }

}