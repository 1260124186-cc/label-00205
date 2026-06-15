package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 案例响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class KnowledgeCaseResponse {

    @JsonProperty("id")
    private Integer id;

    @JsonProperty("case_no")
    private String caseNo;

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

    @JsonProperty("effectiveness_score")
    private Object effectivenessScore;

    @JsonProperty("status")
    private String status;

    @JsonProperty("version")
    private Integer version;

    @JsonProperty("tenant_id")
    private Object tenantId;

    @JsonProperty("creator_id")
    private Object creatorId;

    @JsonProperty("creator_name")
    private Object creatorName;

    @JsonProperty("reviewer_id")
    private Object reviewerId;

    @JsonProperty("reviewer_name")
    private Object reviewerName;

    @JsonProperty("review_time")
    private Object reviewTime;

    @JsonProperty("review_comment")
    private Object reviewComment;

    @JsonProperty("source_alert_id")
    private Object sourceAlertId;

    @JsonProperty("source_prediction_id")
    private Object sourcePredictionId;

    @JsonProperty("tags")
    private Object tags;

    @JsonProperty("similarity_score")
    private Object similarityScore;

    @JsonProperty("create_time")
    private OffsetDateTime createTime;

    @JsonProperty("update_time")
    private OffsetDateTime updateTime;

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public String getCaseNo() {
        return caseNo;
    }

    public void setCaseNo(String caseNo) {
        this.caseNo = caseNo;
    }

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

    public Object getEffectivenessScore() {
        return effectivenessScore;
    }

    public void setEffectivenessScore(Object effectivenessScore) {
        this.effectivenessScore = effectivenessScore;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Integer getVersion() {
        return version;
    }

    public void setVersion(Integer version) {
        this.version = version;
    }

    public Object getTenantId() {
        return tenantId;
    }

    public void setTenantId(Object tenantId) {
        this.tenantId = tenantId;
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

    public Object getReviewerId() {
        return reviewerId;
    }

    public void setReviewerId(Object reviewerId) {
        this.reviewerId = reviewerId;
    }

    public Object getReviewerName() {
        return reviewerName;
    }

    public void setReviewerName(Object reviewerName) {
        this.reviewerName = reviewerName;
    }

    public Object getReviewTime() {
        return reviewTime;
    }

    public void setReviewTime(Object reviewTime) {
        this.reviewTime = reviewTime;
    }

    public Object getReviewComment() {
        return reviewComment;
    }

    public void setReviewComment(Object reviewComment) {
        this.reviewComment = reviewComment;
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

    public Object getSimilarityScore() {
        return similarityScore;
    }

    public void setSimilarityScore(Object similarityScore) {
        this.similarityScore = similarityScore;
    }

    public OffsetDateTime getCreateTime() {
        return createTime;
    }

    public void setCreateTime(OffsetDateTime createTime) {
        this.createTime = createTime;
    }

    public OffsetDateTime getUpdateTime() {
        return updateTime;
    }

    public void setUpdateTime(OffsetDateTime updateTime) {
        this.updateTime = updateTime;
    }

}