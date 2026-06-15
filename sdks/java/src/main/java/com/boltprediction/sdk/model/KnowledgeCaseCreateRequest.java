package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 创建案例请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class KnowledgeCaseCreateRequest {

    @JsonProperty("case_title")
    private String caseTitle;

    @JsonProperty("node_type")
    private Object nodeType;

    @JsonProperty("node_id")
    private Object nodeId;

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

    @JsonProperty("source_alert_id")
    private Object sourceAlertId;

    @JsonProperty("source_prediction_id")
    private Object sourcePredictionId;

    @JsonProperty("tags")
    private Object tags;

    @JsonProperty("creator_id")
    private Object creatorId;

    @JsonProperty("creator_name")
    private Object creatorName;

    @JsonProperty("tenant_id")
    private Object tenantId;

    @JsonProperty("submit_for_review")
    private Boolean submitForReview;

    public String getCaseTitle() {
        return caseTitle;
    }

    public void setCaseTitle(String caseTitle) {
        this.caseTitle = caseTitle;
    }

    public Object getNodeType() {
        return nodeType;
    }

    public void setNodeType(Object nodeType) {
        this.nodeType = nodeType;
    }

    public Object getNodeId() {
        return nodeId;
    }

    public void setNodeId(Object nodeId) {
        this.nodeId = nodeId;
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

    public Object getSourceAlertId() {
        return sourceAlertId;
    }

    public void setSourceAlertId(Object sourceAlertId) {
        this.sourceAlertId = sourceAlertId;
    }

    public Object getSourcePredictionId() {
        return sourcePredictionId;
    }

    public void setSourcePredictionId(Object sourcePredictionId) {
        this.sourcePredictionId = sourcePredictionId;
    }

    public Object getTags() {
        return tags;
    }

    public void setTags(Object tags) {
        this.tags = tags;
    }

    public Object getCreatorId() {
        return creatorId;
    }

    public void setCreatorId(Object creatorId) {
        this.creatorId = creatorId;
    }

    public Object getCreatorName() {
        return creatorName;
    }

    public void setCreatorName(Object creatorName) {
        this.creatorName = creatorName;
    }

    public Object getTenantId() {
        return tenantId;
    }

    public void setTenantId(Object tenantId) {
        this.tenantId = tenantId;
    }

    public Boolean getSubmitForReview() {
        return submitForReview;
    }

    public void setSubmitForReview(Boolean submitForReview) {
        this.submitForReview = submitForReview;
    }

}