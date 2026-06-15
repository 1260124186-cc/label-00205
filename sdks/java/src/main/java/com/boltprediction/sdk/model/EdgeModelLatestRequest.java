package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** EdgeModelLatestRequest */
@JsonIgnoreProperties(ignoreUnknown = true)
public class EdgeModelLatestRequest {

    @JsonProperty("model_type")
    private String modelType;

    @JsonProperty("node_id")
    private Object nodeId;

    @JsonProperty("edge_device_id")
    private Object edgeDeviceId;

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

    public Object getEdgeDeviceId() {
        return edgeDeviceId;
    }

    public void setEdgeDeviceId(Object edgeDeviceId) {
        this.edgeDeviceId = edgeDeviceId;
    }

}