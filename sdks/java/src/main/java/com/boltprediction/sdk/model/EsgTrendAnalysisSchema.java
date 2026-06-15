package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** ESG趋势分析 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class EsgTrendAnalysisSchema {

    @JsonProperty("overall_trend")
    private String overallTrend;

    @JsonProperty("improving_count")
    private Integer improvingCount;

    @JsonProperty("stable_count")
    private Integer stableCount;

    @JsonProperty("declining_count")
    private Integer decliningCount;

    @JsonProperty("key_observation")
    private String keyObservation;

    public String getOverallTrend() {
        return overallTrend;
    }

    public void setOverallTrend(String overallTrend) {
        this.overallTrend = overallTrend;
    }

    public Integer getImprovingCount() {
        return improvingCount;
    }

    public void setImprovingCount(Integer improvingCount) {
        this.improvingCount = improvingCount;
    }

    public Integer getStableCount() {
        return stableCount;
    }

    public void setStableCount(Integer stableCount) {
        this.stableCount = stableCount;
    }

    public Integer getDecliningCount() {
        return decliningCount;
    }

    public void setDecliningCount(Integer decliningCount) {
        this.decliningCount = decliningCount;
    }

    public String getKeyObservation() {
        return keyObservation;
    }

    public void setKeyObservation(String keyObservation) {
        this.keyObservation = keyObservation;
    }

}