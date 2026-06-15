package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** RUL预测点 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class RulPredictionPointSchema {

    @JsonProperty("date")
    private OffsetDateTime date;

    @JsonProperty("predicted_hi")
    private Double predictedHi;

    @JsonProperty("lower_bound")
    private Double lowerBound;

    @JsonProperty("upper_bound")
    private Double upperBound;

    public OffsetDateTime getDate() {
        return date;
    }

    public void setDate(OffsetDateTime date) {
        this.date = date;
    }

    public Double getPredictedHi() {
        return predictedHi;
    }

    public void setPredictedHi(Double predictedHi) {
        this.predictedHi = predictedHi;
    }

    public Double getLowerBound() {
        return lowerBound;
    }

    public void setLowerBound(Double lowerBound) {
        this.lowerBound = lowerBound;
    }

    public Double getUpperBound() {
        return upperBound;
    }

    public void setUpperBound(Double upperBound) {
        this.upperBound = upperBound;
    }

}