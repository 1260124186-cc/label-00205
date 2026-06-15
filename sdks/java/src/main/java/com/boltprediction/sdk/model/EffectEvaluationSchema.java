package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 效果评估 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class EffectEvaluationSchema {

    @JsonProperty("overall_rating")
    private Object overallRating;

    @JsonProperty("effectiveness_score")
    private Object effectivenessScore;

    @JsonProperty("fault_resolved")
    private Object faultResolved;

    @JsonProperty("recurrence_within_days")
    private Object recurrenceWithinDays;

    @JsonProperty("actual_cost")
    private Object actualCost;

    @JsonProperty("actual_duration_minutes")
    private Object actualDurationMinutes;

    @JsonProperty("side_effects")
    private Object sideEffects;

    @JsonProperty("improvement_metrics")
    private Object improvementMetrics;

    @JsonProperty("notes")
    private Object notes;

    public Object getOverallRating() {
        return overallRating;
    }

    public void setOverallRating(Object overallRating) {
        this.overallRating = overallRating;
    }

    public Object getEffectivenessScore() {
        return effectivenessScore;
    }

    public void setEffectivenessScore(Object effectivenessScore) {
        this.effectivenessScore = effectivenessScore;
    }

    public Object getFaultResolved() {
        return faultResolved;
    }

    public void setFaultResolved(Object faultResolved) {
        this.faultResolved = faultResolved;
    }

    public Object getRecurrenceWithinDays() {
        return recurrenceWithinDays;
    }

    public void setRecurrenceWithinDays(Object recurrenceWithinDays) {
        this.recurrenceWithinDays = recurrenceWithinDays;
    }

    public Object getActualCost() {
        return actualCost;
    }

    public void setActualCost(Object actualCost) {
        this.actualCost = actualCost;
    }

    public Object getActualDurationMinutes() {
        return actualDurationMinutes;
    }

    public void setActualDurationMinutes(Object actualDurationMinutes) {
        this.actualDurationMinutes = actualDurationMinutes;
    }

    public Object getSideEffects() {
        return sideEffects;
    }

    public void setSideEffects(Object sideEffects) {
        this.sideEffects = sideEffects;
    }

    public Object getImprovementMetrics() {
        return improvementMetrics;
    }

    public void setImprovementMetrics(Object improvementMetrics) {
        this.improvementMetrics = improvementMetrics;
    }

    public Object getNotes() {
        return notes;
    }

    public void setNotes(Object notes) {
        this.notes = notes;
    }

}