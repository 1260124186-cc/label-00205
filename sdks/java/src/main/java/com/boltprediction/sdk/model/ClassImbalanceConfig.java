package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 类别不平衡处理配置 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ClassImbalanceConfig {

    @JsonProperty("strategy")
    private String strategy;

    @JsonProperty("oversampling_ratio")
    private Object oversamplingRatio;

    public String getStrategy() {
        return strategy;
    }

    public void setStrategy(String strategy) {
        this.strategy = strategy;
    }

    public Object getOversamplingRatio() {
        return oversamplingRatio;
    }

    public void setOversamplingRatio(Object oversamplingRatio) {
        this.oversamplingRatio = oversamplingRatio;
    }

}