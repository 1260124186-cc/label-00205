package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** Focal Loss配置 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FocalLossConfig {

    @JsonProperty("enabled")
    private Boolean enabled;

    @JsonProperty("gamma")
    private Double gamma;

    @JsonProperty("alpha")
    private Object alpha;

    public Boolean getEnabled() {
        return enabled;
    }

    public void setEnabled(Boolean enabled) {
        this.enabled = enabled;
    }

    public Double getGamma() {
        return gamma;
    }

    public void setGamma(Double gamma) {
        this.gamma = gamma;
    }

    public Object getAlpha() {
        return alpha;
    }

    public void setAlpha(Object alpha) {
        this.alpha = alpha;
    }

}