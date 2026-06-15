package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 模型版本列表响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ModelVersionListResponse {

    @JsonProperty("model_id")
    private String modelId;

    @JsonProperty("model_type")
    private String modelType;

    @JsonProperty("versions")
    private List<ModelVersionSchema> versions;

    public String getModelId() {
        return modelId;
    }

    public void setModelId(String modelId) {
        this.modelId = modelId;
    }

    public String getModelType() {
        return modelType;
    }

    public void setModelType(String modelType) {
        this.modelType = modelType;
    }

    public List<ModelVersionSchema> getVersions() {
        return versions;
    }

    public void setVersions(List<ModelVersionSchema> versions) {
        this.versions = versions;
    }

}