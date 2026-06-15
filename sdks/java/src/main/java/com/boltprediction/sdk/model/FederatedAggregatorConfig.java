package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 聚合器配置 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FederatedAggregatorConfig {

    @JsonProperty("strategy")
    private String strategy;

    @JsonProperty("trim_ratio")
    private Double trimRatio;

    @JsonProperty("mu")
    private Double mu;

    @JsonProperty("server_learning_rate")
    private Double serverLearningRate;

    @JsonProperty("min_clients_per_round")
    private Integer minClientsPerRound;

    @JsonProperty("enable_outlier_detection")
    private Boolean enableOutlierDetection;

    public String getStrategy() {
        return strategy;
    }

    public void setStrategy(String strategy) {
        this.strategy = strategy;
    }

    public Double getTrimRatio() {
        return trimRatio;
    }

    public void setTrimRatio(Double trimRatio) {
        this.trimRatio = trimRatio;
    }

    public Double getMu() {
        return mu;
    }

    public void setMu(Double mu) {
        this.mu = mu;
    }

    public Double getServerLearningRate() {
        return serverLearningRate;
    }

    public void setServerLearningRate(Double serverLearningRate) {
        this.serverLearningRate = serverLearningRate;
    }

    public Integer getMinClientsPerRound() {
        return minClientsPerRound;
    }

    public void setMinClientsPerRound(Integer minClientsPerRound) {
        this.minClientsPerRound = minClientsPerRound;
    }

    public Boolean getEnableOutlierDetection() {
        return enableOutlierDetection;
    }

    public void setEnableOutlierDetection(Boolean enableOutlierDetection) {
        this.enableOutlierDetection = enableOutlierDetection;
    }

}