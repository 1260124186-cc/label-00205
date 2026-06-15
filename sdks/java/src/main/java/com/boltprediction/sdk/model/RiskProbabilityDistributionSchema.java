package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** RiskProbabilityDistributionSchema */
@JsonIgnoreProperties(ignoreUnknown = true)
public class RiskProbabilityDistributionSchema {

    @JsonProperty("p_high")
    private Double pHigh;

    @JsonProperty("p_medium")
    private Double pMedium;

    @JsonProperty("p_low")
    private Double pLow;

    public Double getPHigh() {
        return pHigh;
    }

    public void setPHigh(Double pHigh) {
        this.pHigh = pHigh;
    }

    public Double getPMedium() {
        return pMedium;
    }

    public void setPMedium(Double pMedium) {
        this.pMedium = pMedium;
    }

    public Double getPLow() {
        return pLow;
    }

    public void setPLow(Double pLow) {
        this.pLow = pLow;
    }

}