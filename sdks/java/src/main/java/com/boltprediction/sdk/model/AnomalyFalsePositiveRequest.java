package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 标注误报请求

将异常标记为误报。 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AnomalyFalsePositiveRequest {

    @JsonProperty("anomaly_id")
    private Integer anomalyId;

    @JsonProperty("confirmed_by")
    private Object confirmedBy;

    @JsonProperty("confirm_note")
    private Object confirmNote;

    public Integer getAnomalyId() {
        return anomalyId;
    }

    public void setAnomalyId(Integer anomalyId) {
        this.anomalyId = anomalyId;
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