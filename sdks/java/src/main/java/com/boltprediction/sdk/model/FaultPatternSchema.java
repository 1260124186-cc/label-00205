package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 故障模式特征 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FaultPatternSchema {

    @JsonProperty("trend_slope")
    private Double trendSlope;

    @JsonProperty("volatility")
    private Double volatility;

    @JsonProperty("sudden_changes")
    private Integer suddenChanges;

    @JsonProperty("min_value")
    private Double minValue;

    @JsonProperty("max_value")
    private Double maxValue;

    @JsonProperty("mean_value")
    private Double meanValue;

    public Double getTrendSlope() {
        return trendSlope;
    }

    public void setTrendSlope(Double trendSlope) {
        this.trendSlope = trendSlope;
    }

    public Double getVolatility() {
        return volatility;
    }

    public void setVolatility(Double volatility) {
        this.volatility = volatility;
    }

    public Integer getSuddenChanges() {
        return suddenChanges;
    }

    public void setSuddenChanges(Integer suddenChanges) {
        this.suddenChanges = suddenChanges;
    }

    public Double getMinValue() {
        return minValue;
    }

    public void setMinValue(Double minValue) {
        this.minValue = minValue;
    }

    public Double getMaxValue() {
        return maxValue;
    }

    public void setMaxValue(Double maxValue) {
        this.maxValue = maxValue;
    }

    public Double getMeanValue() {
        return meanValue;
    }

    public void setMeanValue(Double meanValue) {
        this.meanValue = meanValue;
    }

}