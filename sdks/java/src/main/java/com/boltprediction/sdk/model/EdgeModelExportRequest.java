package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** EdgeModelExportRequest */
@JsonIgnoreProperties(ignoreUnknown = true)
public class EdgeModelExportRequest {

    @JsonProperty("model_type")
    private String modelType;

    @JsonProperty("node_id")
    private Object nodeId;

    @JsonProperty("export_format")
    private String exportFormat;

    @JsonProperty("version")
    private Object version;

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

    public String getExportFormat() {
        return exportFormat;
    }

    public void setExportFormat(String exportFormat) {
        this.exportFormat = exportFormat;
    }

    public Object getVersion() {
        return version;
    }

    public void setVersion(Object version) {
        this.version = version;
    }

}