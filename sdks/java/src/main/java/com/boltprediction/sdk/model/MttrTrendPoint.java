package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** MTTR趋势点 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class MttrTrendPoint {

    @JsonProperty("date")
    private String date;

    @JsonProperty("mttr_hours")
    private Object mttrHours;

    @JsonProperty("work_order_count")
    private Integer workOrderCount;

    public String getDate() {
        return date;
    }

    public void setDate(String date) {
        this.date = date;
    }

    public Object getMttrHours() {
        return mttrHours;
    }

    public void setMttrHours(Object mttrHours) {
        this.mttrHours = mttrHours;
    }

    public Integer getWorkOrderCount() {
        return workOrderCount;
    }

    public void setWorkOrderCount(Integer workOrderCount) {
        this.workOrderCount = workOrderCount;
    }

}