package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 螺栓预测响应

Attributes:
    bolt_id: 螺栓ID
    status: 预测状态
    status_code: 状态代码
    confidence: 置信度
    risk_score: 风险评分
    risk_level: 风险等级
    diagnosis: 诊断结论
    recommendations: 推荐措施
    prediction_time: 预测时间
    model_version: 模型版本号
    shadow_version: Shadow模式版本号（如有）
    shadow_result: Shadow模式预测结果（如有） */
@JsonIgnoreProperties(ignoreUnknown = true)
public class BoltPredictionResponse {

    @JsonProperty("bolt_id")
    private String boltId;

    @JsonProperty("status")
    private String status;

    @JsonProperty("status_code")
    private Integer statusCode;

    @JsonProperty("confidence")
    private Double confidence;

    @JsonProperty("risk_score")
    private Double riskScore;

    @JsonProperty("risk_level")
    private String riskLevel;

    @JsonProperty("diagnosis")
    private String diagnosis;

    @JsonProperty("recommendations")
    private List<String> recommendations;

    @JsonProperty("prediction_time")
    private OffsetDateTime predictionTime;

    @JsonProperty("model_version")
    private Object modelVersion;

    @JsonProperty("shadow_version")
    private Object shadowVersion;

    @JsonProperty("shadow_result")
    private Object shadowResult;

    @JsonProperty("fault_detail")
    private Object faultDetail;

    @JsonProperty("prediction_source")
    private Object predictionSource;

    @JsonProperty("ensemble")
    private Object ensemble;

    public String getBoltId() {
        return boltId;
    }

    public void setBoltId(String boltId) {
        this.boltId = boltId;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Integer getStatusCode() {
        return statusCode;
    }

    public void setStatusCode(Integer statusCode) {
        this.statusCode = statusCode;
    }

    public Double getConfidence() {
        return confidence;
    }

    public void setConfidence(Double confidence) {
        this.confidence = confidence;
    }

    public Double getRiskScore() {
        return riskScore;
    }

    public void setRiskScore(Double riskScore) {
        this.riskScore = riskScore;
    }

    public String getRiskLevel() {
        return riskLevel;
    }

    public void setRiskLevel(String riskLevel) {
        this.riskLevel = riskLevel;
    }

    public String getDiagnosis() {
        return diagnosis;
    }

    public void setDiagnosis(String diagnosis) {
        this.diagnosis = diagnosis;
    }

    public List<String> getRecommendations() {
        return recommendations;
    }

    public void setRecommendations(List<String> recommendations) {
        this.recommendations = recommendations;
    }

    public OffsetDateTime getPredictionTime() {
        return predictionTime;
    }

    public void setPredictionTime(OffsetDateTime predictionTime) {
        this.predictionTime = predictionTime;
    }

    public Object getModelVersion() {
        return modelVersion;
    }

    public void setModelVersion(Object modelVersion) {
        this.modelVersion = modelVersion;
    }

    public Object getShadowVersion() {
        return shadowVersion;
    }

    public void setShadowVersion(Object shadowVersion) {
        this.shadowVersion = shadowVersion;
    }

    public Object getShadowResult() {
        return shadowResult;
    }

    public void setShadowResult(Object shadowResult) {
        this.shadowResult = shadowResult;
    }

    public Object getFaultDetail() {
        return faultDetail;
    }

    public void setFaultDetail(Object faultDetail) {
        this.faultDetail = faultDetail;
    }

    public Object getPredictionSource() {
        return predictionSource;
    }

    public void setPredictionSource(Object predictionSource) {
        this.predictionSource = predictionSource;
    }

    public Object getEnsemble() {
        return ensemble;
    }

    public void setEnsemble(Object ensemble) {
        this.ensemble = ensemble;
    }

}