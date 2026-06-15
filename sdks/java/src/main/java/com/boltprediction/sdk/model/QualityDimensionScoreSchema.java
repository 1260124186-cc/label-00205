package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 维度评分 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class QualityDimensionScoreSchema {

    @JsonProperty("dimension")
    private String dimension;

    @JsonProperty("score")
    private Double score;

    @JsonProperty("weight")
    private Double weight;

    @JsonProperty("contributing_rules")
    private List<String> contributingRules;

    public String getDimension() {
        return dimension;
    }

    public void setDimension(String dimension) {
        this.dimension = dimension;
    }

    public Double getScore() {
        return score;
    }

    public void setScore(Double score) {
        this.score = score;
    }

    public Double getWeight() {
        return weight;
    }

    public void setWeight(Double weight) {
        this.weight = weight;
    }

    public List<String> getContributingRules() {
        return contributingRules;
    }

    public void setContributingRules(List<String> contributingRules) {
        this.contributingRules = contributingRules;
    }

}