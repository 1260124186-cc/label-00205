package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 预警策略配置 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class WarningStrategyConfigSchema {

    @JsonProperty("strategy_type")
    private Integer strategyType;

    @JsonProperty("strategy_1_confidence_threshold")
    private Double strategy1ConfidenceThreshold;

    @JsonProperty("strategy_1_false_positive_threshold")
    private Double strategy1FalsePositiveThreshold;

    @JsonProperty("strategy_2_confidence_threshold")
    private Double strategy2ConfidenceThreshold;

    @JsonProperty("strategy_2_false_negative_threshold")
    private Double strategy2FalseNegativeThreshold;

    public Integer getStrategyType() {
        return strategyType;
    }

    public void setStrategyType(Integer strategyType) {
        this.strategyType = strategyType;
    }

    public Double getStrategy1ConfidenceThreshold() {
        return strategy1ConfidenceThreshold;
    }

    public void setStrategy1ConfidenceThreshold(Double strategy1ConfidenceThreshold) {
        this.strategy1ConfidenceThreshold = strategy1ConfidenceThreshold;
    }

    public Double getStrategy1FalsePositiveThreshold() {
        return strategy1FalsePositiveThreshold;
    }

    public void setStrategy1FalsePositiveThreshold(Double strategy1FalsePositiveThreshold) {
        this.strategy1FalsePositiveThreshold = strategy1FalsePositiveThreshold;
    }

    public Double getStrategy2ConfidenceThreshold() {
        return strategy2ConfidenceThreshold;
    }

    public void setStrategy2ConfidenceThreshold(Double strategy2ConfidenceThreshold) {
        this.strategy2ConfidenceThreshold = strategy2ConfidenceThreshold;
    }

    public Double getStrategy2FalseNegativeThreshold() {
        return strategy2FalseNegativeThreshold;
    }

    public void setStrategy2FalseNegativeThreshold(Double strategy2FalseNegativeThreshold) {
        this.strategy2FalseNegativeThreshold = strategy2FalseNegativeThreshold;
    }

}