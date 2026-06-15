package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** MTTR趋势响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class MttrTrendResponse {

    @JsonProperty("trend")
    private List<MttrTrendPoint> trend;

    @JsonProperty("overall_mttr_hours")
    private Object overallMttrHours;

    public List<MttrTrendPoint> getTrend() {
        return trend;
    }

    public void setTrend(List<MttrTrendPoint> trend) {
        this.trend = trend;
    }

    public Object getOverallMttrHours() {
        return overallMttrHours;
    }

    public void setOverallMttrHours(Object overallMttrHours) {
        this.overallMttrHours = overallMttrHours;
    }

}