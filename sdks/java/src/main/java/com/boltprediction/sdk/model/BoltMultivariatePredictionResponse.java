package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 螺栓多变量耦合预测响应

在标准螺栓预测响应基础上，新增：
- data_quality: 数据质量评估（含降级信息）
- channels_info: 实际使用的通道元数据
- temp_compensation: 温度耦合补偿详情
- feature_importance: 各通道特征重要性（可解释性） */
@JsonIgnoreProperties(ignoreUnknown = true)
public class BoltMultivariatePredictionResponse {

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

    @JsonProperty("input_dim_actual")
    private Integer inputDimActual;

    @JsonProperty("channels_info")
    private List<MultivariateChannelSchema> channelsInfo;

    @JsonProperty("data_quality")
    private DataQualityInfo dataQuality;

    @JsonProperty("temp_compensation")
    private Object tempCompensation;

    @JsonProperty("feature_importance")
    private Object featureImportance;

    @JsonProperty("sequence_length_used")
    private Integer sequenceLengthUsed;

    @JsonProperty("prediction_source")
    private String predictionSource;

    @JsonProperty("fault_detail")
    private Object faultDetail;

    @JsonProperty("shadow_version")
    private Object shadowVersion;

    @JsonProperty("shadow_result")
    private Object shadowResult;

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

    public Integer getInputDimActual() {
        return inputDimActual;
    }

    public void setInputDimActual(Integer inputDimActual) {
        this.inputDimActual = inputDimActual;
    }

    public List<MultivariateChannelSchema> getChannelsInfo() {
        return channelsInfo;
    }

    public void setChannelsInfo(List<MultivariateChannelSchema> channelsInfo) {
        this.channelsInfo = channelsInfo;
    }

    public DataQualityInfo getDataQuality() {
        return dataQuality;
    }

    public void setDataQuality(DataQualityInfo dataQuality) {
        this.dataQuality = dataQuality;
    }

    public Object getTempCompensation() {
        return tempCompensation;
    }

    public void setTempCompensation(Object tempCompensation) {
        this.tempCompensation = tempCompensation;
    }

    public Object getFeatureImportance() {
        return featureImportance;
    }

    public void setFeatureImportance(Object featureImportance) {
        this.featureImportance = featureImportance;
    }

    public Integer getSequenceLengthUsed() {
        return sequenceLengthUsed;
    }

    public void setSequenceLengthUsed(Integer sequenceLengthUsed) {
        this.sequenceLengthUsed = sequenceLengthUsed;
    }

    public String getPredictionSource() {
        return predictionSource;
    }

    public void setPredictionSource(String predictionSource) {
        this.predictionSource = predictionSource;
    }

    public Object getFaultDetail() {
        return faultDetail;
    }

    public void setFaultDetail(Object faultDetail) {
        this.faultDetail = faultDetail;
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

}