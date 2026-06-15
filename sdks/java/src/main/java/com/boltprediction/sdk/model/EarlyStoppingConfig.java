package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 早停配置 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class EarlyStoppingConfig {

    @JsonProperty("enabled")
    private Boolean enabled;

    @JsonProperty("patience")
    private Integer patience;

    @JsonProperty("min_delta")
    private Double minDelta;

    @JsonProperty("mode")
    private String mode;

    public Boolean getEnabled() {
        return enabled;
    }

    public void setEnabled(Boolean enabled) {
        this.enabled = enabled;
    }

    public Integer getPatience() {
        return patience;
    }

    public void setPatience(Integer patience) {
        this.patience = patience;
    }

    public Double getMinDelta() {
        return minDelta;
    }

    public void setMinDelta(Double minDelta) {
        this.minDelta = minDelta;
    }

    public String getMode() {
        return mode;
    }

    public void setMode(String mode) {
        this.mode = mode;
    }

}