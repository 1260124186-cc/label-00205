package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 当前生效策略响应（含全局和节点覆盖） */
@JsonIgnoreProperties(ignoreUnknown = true)
public class EffectiveStrategyResponse {

    @JsonProperty("global_config")
    private StrategyConfigItemResponse globalConfig;

    @JsonProperty("node_overrides")
    private List<StrategyConfigItemResponse> nodeOverrides;

    @JsonProperty("effective")
    private StrategyConfigItemResponse effective;

    public StrategyConfigItemResponse getGlobalConfig() {
        return globalConfig;
    }

    public void setGlobalConfig(StrategyConfigItemResponse globalConfig) {
        this.globalConfig = globalConfig;
    }

    public List<StrategyConfigItemResponse> getNodeOverrides() {
        return nodeOverrides;
    }

    public void setNodeOverrides(List<StrategyConfigItemResponse> nodeOverrides) {
        this.nodeOverrides = nodeOverrides;
    }

    public StrategyConfigItemResponse getEffective() {
        return effective;
    }

    public void setEffective(StrategyConfigItemResponse effective) {
        this.effective = effective;
    }

}