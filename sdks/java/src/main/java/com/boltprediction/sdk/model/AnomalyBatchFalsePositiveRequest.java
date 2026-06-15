package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 批量标注误报请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AnomalyBatchFalsePositiveRequest {

    @JsonProperty("anomaly_ids")
    private List<Integer> anomalyIds;

    @JsonProperty("confirmed_by")
    private Object confirmedBy;

    @JsonProperty("confirm_note")
    private Object confirmNote;

    public List<Integer> getAnomalyIds() {
        return anomalyIds;
    }

    public void setAnomalyIds(List<Integer> anomalyIds) {
        this.anomalyIds = anomalyIds;
    }

    public Object getConfirmedBy() {
        return confirmedBy;
    }

    public void setConfirmedBy(Object confirmedBy) {
        this.confirmedBy = confirmedBy;
    }

    public Object getConfirmNote() {
        return confirmNote;
    }

    public void setConfirmNote(Object confirmNote) {
        this.confirmNote = confirmNote;
    }

}