package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 模型训练请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TrainingRequest {

    @JsonProperty("model_type")
    private String modelType;

    @JsonProperty("node_id")
    private Object nodeId;

    @JsonProperty("force_retrain")
    private Boolean forceRetrain;

    public String getModelType() {
        return modelType;
    }

    public void setModelType(String modelType) {
        this.modelType = modelType;
    }

    public Object getNodeId() {
        return nodeId;
    }

    public void setNodeId(Object nodeId) {
        this.nodeId = nodeId;
    }

    public Boolean getForceRetrain() {
        return forceRetrain;
    }

    public void setForceRetrain(Boolean forceRetrain) {
        this.forceRetrain = forceRetrain;
    }

}