package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 传播路径 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class PropagationPathSchema {

    @JsonProperty("path")
    private List<String> path;

    @JsonProperty("path_indices")
    private List<Integer> pathIndices;

    @JsonProperty("depth")
    private Integer depth;

    @JsonProperty("total_weight")
    private Double totalWeight;

    @JsonProperty("avg_weight")
    private Double avgWeight;

    public List<String> getPath() {
        return path;
    }

    public void setPath(List<String> path) {
        this.path = path;
    }

    public List<Integer> getPathIndices() {
        return pathIndices;
    }

    public void setPathIndices(List<Integer> pathIndices) {
        this.pathIndices = pathIndices;
    }

    public Integer getDepth() {
        return depth;
    }

    public void setDepth(Integer depth) {
        this.depth = depth;
    }

    public Double getTotalWeight() {
        return totalWeight;
    }

    public void setTotalWeight(Double totalWeight) {
        this.totalWeight = totalWeight;
    }

    public Double getAvgWeight() {
        return avgWeight;
    }

    public void setAvgWeight(Double avgWeight) {
        this.avgWeight = avgWeight;
    }

}