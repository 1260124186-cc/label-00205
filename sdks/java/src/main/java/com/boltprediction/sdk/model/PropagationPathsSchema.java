package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 传播路径分析结果 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class PropagationPathsSchema {

    @JsonProperty("source_bolt")
    private String sourceBolt;

    @JsonProperty("source_idx")
    private Integer sourceIdx;

    @JsonProperty("paths")
    private List<PropagationPathSchema> paths;

    @JsonProperty("total_path_count")
    private Integer totalPathCount;

    @JsonProperty("reachable_bolts")
    private List<String> reachableBolts;

    @JsonProperty("propagation_distance")
    private Map<String, Object> propagationDistance;

    @JsonProperty("max_depth")
    private Integer maxDepth;

    public String getSourceBolt() {
        return sourceBolt;
    }

    public void setSourceBolt(String sourceBolt) {
        this.sourceBolt = sourceBolt;
    }

    public Integer getSourceIdx() {
        return sourceIdx;
    }

    public void setSourceIdx(Integer sourceIdx) {
        this.sourceIdx = sourceIdx;
    }

    public List<PropagationPathSchema> getPaths() {
        return paths;
    }

    public void setPaths(List<PropagationPathSchema> paths) {
        this.paths = paths;
    }

    public Integer getTotalPathCount() {
        return totalPathCount;
    }

    public void setTotalPathCount(Integer totalPathCount) {
        this.totalPathCount = totalPathCount;
    }

    public List<String> getReachableBolts() {
        return reachableBolts;
    }

    public void setReachableBolts(List<String> reachableBolts) {
        this.reachableBolts = reachableBolts;
    }

    public Map<String, Object> getPropagationDistance() {
        return propagationDistance;
    }

    public void setPropagationDistance(Map<String, Object> propagationDistance) {
        this.propagationDistance = propagationDistance;
    }

    public Integer getMaxDepth() {
        return maxDepth;
    }

    public void setMaxDepth(Integer maxDepth) {
        this.maxDepth = maxDepth;
    }

}