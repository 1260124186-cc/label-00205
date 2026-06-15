package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 过滤结果 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FilteredDataResultSchema {

    @JsonProperty("original_count")
    private Integer originalCount;

    @JsonProperty("filtered_count")
    private Integer filteredCount;

    @JsonProperty("removed_indices")
    private List<Integer> removedIndices;

    @JsonProperty("removal_reasons")
    private Map<String, String> removalReasons;

    @JsonProperty("filter_strategy")
    private String filterStrategy;

    @JsonProperty("confidence_multiplier")
    private Double confidenceMultiplier;

    @JsonProperty("adjusted_confidence")
    private Object adjustedConfidence;

    public Integer getOriginalCount() {
        return originalCount;
    }

    public void setOriginalCount(Integer originalCount) {
        this.originalCount = originalCount;
    }

    public Integer getFilteredCount() {
        return filteredCount;
    }

    public void setFilteredCount(Integer filteredCount) {
        this.filteredCount = filteredCount;
    }

    public List<Integer> getRemovedIndices() {
        return removedIndices;
    }

    public void setRemovedIndices(List<Integer> removedIndices) {
        this.removedIndices = removedIndices;
    }

    public Map<String, String> getRemovalReasons() {
        return removalReasons;
    }

    public void setRemovalReasons(Map<String, String> removalReasons) {
        this.removalReasons = removalReasons;
    }

    public String getFilterStrategy() {
        return filterStrategy;
    }

    public void setFilterStrategy(String filterStrategy) {
        this.filterStrategy = filterStrategy;
    }

    public Double getConfidenceMultiplier() {
        return confidenceMultiplier;
    }

    public void setConfidenceMultiplier(Double confidenceMultiplier) {
        this.confidenceMultiplier = confidenceMultiplier;
    }

    public Object getAdjustedConfidence() {
        return adjustedConfidence;
    }

    public void setAdjustedConfidence(Object adjustedConfidence) {
        this.adjustedConfidence = adjustedConfidence;
    }

}