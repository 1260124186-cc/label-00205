package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** FactorContributionSchema */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FactorContributionSchema {

    @JsonProperty("name")
    private String name;

    @JsonProperty("display_name")
    private String displayName;

    @JsonProperty("raw_score")
    private Double rawScore;

    @JsonProperty("weight")
    private Double weight;

    @JsonProperty("weighted_score")
    private Double weightedScore;

    @JsonProperty("contribution_ratio")
    private Double contributionRatio;

    @JsonProperty("direction")
    private String direction;

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getDisplayName() {
        return displayName;
    }

    public void setDisplayName(String displayName) {
        this.displayName = displayName;
    }

    public Double getRawScore() {
        return rawScore;
    }

    public void setRawScore(Double rawScore) {
        this.rawScore = rawScore;
    }

    public Double getWeight() {
        return weight;
    }

    public void setWeight(Double weight) {
        this.weight = weight;
    }

    public Double getWeightedScore() {
        return weightedScore;
    }

    public void setWeightedScore(Double weightedScore) {
        this.weightedScore = weightedScore;
    }

    public Double getContributionRatio() {
        return contributionRatio;
    }

    public void setContributionRatio(Double contributionRatio) {
        this.contributionRatio = contributionRatio;
    }

    public String getDirection() {
        return direction;
    }

    public void setDirection(String direction) {
        this.direction = direction;
    }

}