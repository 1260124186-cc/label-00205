package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 隐私保护配置 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FederatedPrivacyConfig {

    @JsonProperty("mechanism")
    private String mechanism;

    @JsonProperty("epsilon")
    private Double epsilon;

    @JsonProperty("delta")
    private Double delta;

    @JsonProperty("noise_scale")
    private Double noiseScale;

    @JsonProperty("clip_norm")
    private Double clipNorm;

    @JsonProperty("num_parties")
    private Integer numParties;

    @JsonProperty("secret_share_threshold")
    private Integer secretShareThreshold;

    public String getMechanism() {
        return mechanism;
    }

    public void setMechanism(String mechanism) {
        this.mechanism = mechanism;
    }

    public Double getEpsilon() {
        return epsilon;
    }

    public void setEpsilon(Double epsilon) {
        this.epsilon = epsilon;
    }

    public Double getDelta() {
        return delta;
    }

    public void setDelta(Double delta) {
        this.delta = delta;
    }

    public Double getNoiseScale() {
        return noiseScale;
    }

    public void setNoiseScale(Double noiseScale) {
        this.noiseScale = noiseScale;
    }

    public Double getClipNorm() {
        return clipNorm;
    }

    public void setClipNorm(Double clipNorm) {
        this.clipNorm = clipNorm;
    }

    public Integer getNumParties() {
        return numParties;
    }

    public void setNumParties(Integer numParties) {
        this.numParties = numParties;
    }

    public Integer getSecretShareThreshold() {
        return secretShareThreshold;
    }

    public void setSecretShareThreshold(Integer secretShareThreshold) {
        this.secretShareThreshold = secretShareThreshold;
    }

}