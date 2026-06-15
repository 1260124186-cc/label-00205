package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 案例相似度检索请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class CaseSimilaritySearchRequest {

    @JsonProperty("node_type")
    private Object nodeType;

    @JsonProperty("node_id")
    private Object nodeId;

    @JsonProperty("fault_type")
    private Object faultType;

    @JsonProperty("fault_level")
    private Object faultLevel;

    @JsonProperty("sensor_data")
    private Object sensorData;

    @JsonProperty("sensor_features")
    private Object sensorFeatures;

    @JsonProperty("feature_vector")
    private Object featureVector;

    @JsonProperty("tags")
    private Object tags;

    @JsonProperty("top_k")
    private Integer topK;

    @JsonProperty("min_similarity")
    private Double minSimilarity;

    @JsonProperty("only_approved")
    private Boolean onlyApproved;

    @JsonProperty("tenant_id")
    private Object tenantId;

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

    public Object getFeatureVector() {
        return featureVector;
    }

    public void setFeatureVector(Object featureVector) {
        this.featureVector = featureVector;
    }

    public Object getTags() {
        return tags;
    }

    public void setTags(Object tags) {
        this.tags = tags;
    }

    public Integer getTopK() {
        return topK;
    }

    public void setTopK(Integer topK) {
        this.topK = topK;
    }

    public Double getMinSimilarity() {
        return minSimilarity;
    }

    public void setMinSimilarity(Double minSimilarity) {
        this.minSimilarity = minSimilarity;
    }

    public Boolean getOnlyApproved() {
        return onlyApproved;
    }

    public void setOnlyApproved(Boolean onlyApproved) {
        this.onlyApproved = onlyApproved;
    }

    public Object getTenantId() {
        return tenantId;
    }

    public void setTenantId(Object tenantId) {
        this.tenantId = tenantId;
    }

}