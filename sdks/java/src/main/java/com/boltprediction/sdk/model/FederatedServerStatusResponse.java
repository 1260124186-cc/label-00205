package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 联邦学习服务器状态响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FederatedServerStatusResponse {

    @JsonProperty("registered_clients")
    private Integer registeredClients;

    @JsonProperty("active_clients")
    private Integer activeClients;

    @JsonProperty("total_rounds")
    private Integer totalRounds;

    @JsonProperty("completed_rounds")
    private Integer completedRounds;

    @JsonProperty("failed_rounds")
    private Integer failedRounds;

    @JsonProperty("aggregation_strategy")
    private String aggregationStrategy;

    @JsonProperty("managed_models")
    private List<String> managedModels;

    @JsonProperty("current_round")
    private Object currentRound;

    public Integer getRegisteredClients() {
        return registeredClients;
    }

    public void setRegisteredClients(Integer registeredClients) {
        this.registeredClients = registeredClients;
    }

    public Integer getActiveClients() {
        return activeClients;
    }

    public void setActiveClients(Integer activeClients) {
        this.activeClients = activeClients;
    }

    public Integer getTotalRounds() {
        return totalRounds;
    }

    public void setTotalRounds(Integer totalRounds) {
        this.totalRounds = totalRounds;
    }

    public Integer getCompletedRounds() {
        return completedRounds;
    }

    public void setCompletedRounds(Integer completedRounds) {
        this.completedRounds = completedRounds;
    }

    public Integer getFailedRounds() {
        return failedRounds;
    }

    public void setFailedRounds(Integer failedRounds) {
        this.failedRounds = failedRounds;
    }

    public String getAggregationStrategy() {
        return aggregationStrategy;
    }

    public void setAggregationStrategy(String aggregationStrategy) {
        this.aggregationStrategy = aggregationStrategy;
    }

    public List<String> getManagedModels() {
        return managedModels;
    }

    public void setManagedModels(List<String> managedModels) {
        this.managedModels = managedModels;
    }

    public Object getCurrentRound() {
        return currentRound;
    }

    public void setCurrentRound(Object currentRound) {
        this.currentRound = currentRound;
    }

}