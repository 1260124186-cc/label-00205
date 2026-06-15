package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 处置步骤 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TreatmentStepSchema {

    @JsonProperty("step_order")
    private Integer stepOrder;

    @JsonProperty("action")
    private String action;

    @JsonProperty("description")
    private Object description;

    @JsonProperty("tools")
    private Object tools;

    @JsonProperty("duration_minutes")
    private Object durationMinutes;

    @JsonProperty("safety_notes")
    private Object safetyNotes;

    public Integer getStepOrder() {
        return stepOrder;
    }

    public void setStepOrder(Integer stepOrder) {
        this.stepOrder = stepOrder;
    }

    public String getAction() {
        return action;
    }

    public void setAction(String action) {
        this.action = action;
    }

    public Object getDescription() {
        return description;
    }

    public void setDescription(Object description) {
        this.description = description;
    }

    public Object getTools() {
        return tools;
    }

    public void setTools(Object tools) {
        this.tools = tools;
    }

    public Object getDurationMinutes() {
        return durationMinutes;
    }

    public void setDurationMinutes(Object durationMinutes) {
        this.durationMinutes = durationMinutes;
    }

    public Object getSafetyNotes() {
        return safetyNotes;
    }

    public void setSafetyNotes(Object safetyNotes) {
        this.safetyNotes = safetyNotes;
    }

}