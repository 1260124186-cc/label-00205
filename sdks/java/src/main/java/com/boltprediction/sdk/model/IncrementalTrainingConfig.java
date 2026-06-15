package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 增量训练配置 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class IncrementalTrainingConfig {

    @JsonProperty("enabled")
    private Boolean enabled;

    @JsonProperty("freeze_layers")
    private Object freezeLayers;

    @JsonProperty("base_model_version")
    private Object baseModelVersion;

    public Boolean getEnabled() {
        return enabled;
    }

    public void setEnabled(Boolean enabled) {
        this.enabled = enabled;
    }

    public Object getFreezeLayers() {
        return freezeLayers;
    }

    public void setFreezeLayers(Object freezeLayers) {
        this.freezeLayers = freezeLayers;
    }

    public Object getBaseModelVersion() {
        return baseModelVersion;
    }

    public void setBaseModelVersion(Object baseModelVersion) {
        this.baseModelVersion = baseModelVersion;
    }

}