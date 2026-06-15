package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 增强版模型训练请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class EnhancedTrainingRequest {

    @JsonProperty("model_type")
    private String modelType;

    @JsonProperty("node_id")
    private Object nodeId;

    @JsonProperty("force_retrain")
    private Boolean forceRetrain;

    @JsonProperty("data_source")
    private String dataSource;

    @JsonProperty("is_incremental")
    private Boolean isIncremental;

    @JsonProperty("base_model_version")
    private Object baseModelVersion;

    @JsonProperty("freeze_layers")
    private Object freezeLayers;

    @JsonProperty("training_config")
    private Object trainingConfig;

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

    public String getDataSource() {
        return dataSource;
    }

    public void setDataSource(String dataSource) {
        this.dataSource = dataSource;
    }

    public Boolean getIsIncremental() {
        return isIncremental;
    }

    public void setIsIncremental(Boolean isIncremental) {
        this.isIncremental = isIncremental;
    }

    public Object getBaseModelVersion() {
        return baseModelVersion;
    }

    public void setBaseModelVersion(Object baseModelVersion) {
        this.baseModelVersion = baseModelVersion;
    }

    public Object getFreezeLayers() {
        return freezeLayers;
    }

    public void setFreezeLayers(Object freezeLayers) {
        this.freezeLayers = freezeLayers;
    }

    public Object getTrainingConfig() {
        return trainingConfig;
    }

    public void setTrainingConfig(Object trainingConfig) {
        this.trainingConfig = trainingConfig;
    }

}