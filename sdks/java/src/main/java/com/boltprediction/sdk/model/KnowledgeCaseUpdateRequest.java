package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 更新案例请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class KnowledgeCaseUpdateRequest {

    @JsonProperty("case_title")
    private Object caseTitle;

    @JsonProperty("fault_type")
    private Object faultType;

    @JsonProperty("fault_level")
    private Object faultLevel;

    @JsonProperty("working_condition")
    private Object workingCondition;

    @JsonProperty("sensor_data")
    private Object sensorData;

    @JsonProperty("sensor_features")
    private Object sensorFeatures;

    @JsonProperty("diagnosis")
    private Object diagnosis;

    @JsonProperty("root_cause")
    private Object rootCause;

    @JsonProperty("treatment_plan")
    private Object treatmentPlan;

    @JsonProperty("effect_evaluation")
    private Object effectEvaluation;

    @JsonProperty("tags")
    private Object tags;

    @JsonProperty("change_summary")
    private Object changeSummary;

    @JsonProperty("submit_for_review")
    private Boolean submitForReview;

    @JsonProperty("operator_id")
    private Object operatorId;

    @JsonProperty("operator_name")
    private Object operatorName;

    public Object getCaseTitle() {
        return caseTitle;
    }

    public void setCaseTitle(Object caseTitle) {
        this.caseTitle = caseTitle;
    }

    public Object getFaultType() {
        return faultType;
    }

    public void setFaultType(Object faultType) {
        this.faultType = faultType;
    }

    public Object getFaultLevel() {
        return faultLevel;
    }

    public void setFaultLevel(Object faultLevel) {
        this.faultLevel = faultLevel;
    }

    public Object getWorkingCondition() {
        return workingCondition;
    }

    public void setWorkingCondition(Object workingCondition) {
        this.workingCondition = workingCondition;
    }

    public Object getSensorData() {
        return sensorData;
    }

    public void setSensorData(Object sensorData) {
        this.sensorData = sensorData;
    }

    public Object getSensorFeatures() {
        return sensorFeatures;
    }

    public void setSensorFeatures(Object sensorFeatures) {
        this.sensorFeatures = sensorFeatures;
    }

    public Object getDiagnosis() {
        return diagnosis;
    }

    public void setDiagnosis(Object diagnosis) {
        this.diagnosis = diagnosis;
    }

    public Object getRootCause() {
        return rootCause;
    }

    public void setRootCause(Object rootCause) {
        this.rootCause = rootCause;
    }

    public Object getTreatmentPlan() {
        return treatmentPlan;
    }

    public void setTreatmentPlan(Object treatmentPlan) {
        this.treatmentPlan = treatmentPlan;
    }

    public Object getEffectEvaluation() {
        return effectEvaluation;
    }

    public void setEffectEvaluation(Object effectEvaluation) {
        this.effectEvaluation = effectEvaluation;
    }

    public Object getTags() {
        return tags;
    }

    public void setTags(Object tags) {
        this.tags = tags;
    }

    public Object getChangeSummary() {
        return changeSummary;
    }

    public void setChangeSummary(Object changeSummary) {
        this.changeSummary = changeSummary;
    }

    public Boolean getSubmitForReview() {
        return submitForReview;
    }

    public void setSubmitForReview(Boolean submitForReview) {
        this.submitForReview = submitForReview;
    }

    public Object getOperatorId() {
        return operatorId;
    }

    public void setOperatorId(Object operatorId) {
        this.operatorId = operatorId;
    }

    public Object getOperatorName() {
        return operatorName;
    }

    public void setOperatorName(Object operatorName) {
        this.operatorName = operatorName;
    }

}