package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 聚合模型更新请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FederatedRoundAggregateRequest {

    @JsonProperty("model_type")
    private String modelType;

    @JsonProperty("node_id")
    private String nodeId;

    public String getModelType() {
        return modelType;
    }

    public void setModelType(String modelType) {
        this.modelType = modelType;
    }

    public String getNodeId() {
        return nodeId;
    }

    public void setNodeId(String nodeId) {
        this.nodeId = nodeId;
    }

}