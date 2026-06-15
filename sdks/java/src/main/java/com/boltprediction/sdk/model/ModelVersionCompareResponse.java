package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 模型版本对比响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ModelVersionCompareResponse {

    @JsonProperty("model_id")
    private String modelId;

    @JsonProperty("version1")
    private String version1;

    @JsonProperty("version2")
    private String version2;

    @JsonProperty("metrics_comparison")
    private Map<String, Object> metricsComparison;

    @JsonProperty("config_diff")
    private Map<String, Object> configDiff;

    public String getModelId() {
        return modelId;
    }

    public void setModelId(String modelId) {
        this.modelId = modelId;
    }

    public String getVersion1() {
        return version1;
    }

    public void setVersion1(String version1) {
        this.version1 = version1;
    }

    public String getVersion2() {
        return version2;
    }

    public void setVersion2(String version2) {
        this.version2 = version2;
    }

    public Map<String, Object> getMetricsComparison() {
        return metricsComparison;
    }

    public void setMetricsComparison(Map<String, Object> metricsComparison) {
        this.metricsComparison = metricsComparison;
    }

    public Map<String, Object> getConfigDiff() {
        return configDiff;
    }

    public void setConfigDiff(Map<String, Object> configDiff) {
        this.configDiff = configDiff;
    }

}