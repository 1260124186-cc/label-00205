package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 螺栓集成学习预测调试响应

Attributes:
    bolt_id: 螺栓ID
    prediction_source: 预测来源
    ensemble_method: 集成方法: hard / soft / weighted
    final_status: 最终状态
    final_status_code: 最终状态代码
    final_confidence: 最终置信度
    final_probs: 最终概率分布
    weights: 各预测器权重
    individual_results: 各子模型分项结果
    individual_probs: 各子模型概率分布
    model_version: 模型版本
    duration_ms: 预测耗时(ms)
    ema_accuracy: EMA准确率
    performance_history: 历史表现记录 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class BoltEnsemblePredictionResponse {

    @JsonProperty("bolt_id")
    private String boltId;

    @JsonProperty("prediction_source")
    private String predictionSource;

    @JsonProperty("ensemble_method")
    private String ensembleMethod;

    @JsonProperty("final_status")
    private String finalStatus;

    @JsonProperty("final_status_code")
    private Integer finalStatusCode;

    @JsonProperty("final_confidence")
    private Double finalConfidence;

    @JsonProperty("final_probs")
    private Object finalProbs;

    @JsonProperty("weights")
    private Map<String, Double> weights;

    @JsonProperty("individual_results")
    private List<Map<String, Object>> individualResults;

    @JsonProperty("individual_probs")
    private Map<String, Object> individualProbs;

    @JsonProperty("model_version")
    private String modelVersion;

    @JsonProperty("duration_ms")
    private Double durationMs;

    @JsonProperty("ema_accuracy")
    private Map<String, Double> emaAccuracy;

    @JsonProperty("performance_history")
    private Map<String, List<Double>> performanceHistory;

    public String getBoltId() {
        return boltId;
    }

    public void setBoltId(String boltId) {
        this.boltId = boltId;
    }

    public String getPredictionSource() {
        return predictionSource;
    }

    public void setPredictionSource(String predictionSource) {
        this.predictionSource = predictionSource;
    }

    public String getEnsembleMethod() {
        return ensembleMethod;
    }

    public void setEnsembleMethod(String ensembleMethod) {
        this.ensembleMethod = ensembleMethod;
    }

    public String getFinalStatus() {
        return finalStatus;
    }

    public void setFinalStatus(String finalStatus) {
        this.finalStatus = finalStatus;
    }

    public Integer getFinalStatusCode() {
        return finalStatusCode;
    }

    public void setFinalStatusCode(Integer finalStatusCode) {
        this.finalStatusCode = finalStatusCode;
    }

    public Double getFinalConfidence() {
        return finalConfidence;
    }

    public void setFinalConfidence(Double finalConfidence) {
        this.finalConfidence = finalConfidence;
    }

    public Object getFinalProbs() {
        return finalProbs;
    }

    public void setFinalProbs(Object finalProbs) {
        this.finalProbs = finalProbs;
    }

    public Map<String, Double> getWeights() {
        return weights;
    }

    public void setWeights(Map<String, Double> weights) {
        this.weights = weights;
    }

    public List<Map<String, Object>> getIndividualResults() {
        return individualResults;
    }

    public void setIndividualResults(List<Map<String, Object>> individualResults) {
        this.individualResults = individualResults;
    }

    public Map<String, Object> getIndividualProbs() {
        return individualProbs;
    }

    public void setIndividualProbs(Map<String, Object> individualProbs) {
        this.individualProbs = individualProbs;
    }

    public String getModelVersion() {
        return modelVersion;
    }

    public void setModelVersion(String modelVersion) {
        this.modelVersion = modelVersion;
    }

    public Double getDurationMs() {
        return durationMs;
    }

    public void setDurationMs(Double durationMs) {
        this.durationMs = durationMs;
    }

    public Map<String, Double> getEmaAccuracy() {
        return emaAccuracy;
    }

    public void setEmaAccuracy(Map<String, Double> emaAccuracy) {
        this.emaAccuracy = emaAccuracy;
    }

    public Map<String, List<Double>> getPerformanceHistory() {
        return performanceHistory;
    }

    public void setPerformanceHistory(Map<String, List<Double>> performanceHistory) {
        this.performanceHistory = performanceHistory;
    }

}