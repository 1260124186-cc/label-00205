package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 数据质量评估结果

Attributes:
    level: 数据质量等级 full=完整, partial=部分缺失, degraded=降级单变量
    complete_ratio: 完整数据占比 (0-1)
    missing_channels: 被丢弃/降级时缺失的通道列表
    interpolation_count: 插值填充的总数据点数
    interpolation_flags: 可选，每个时间点每通道的插值标记（1=插值 0=原始）
    degradation_applied: 是否触发了降级策略 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class DataQualityInfo {

    @JsonProperty("level")
    private String level;

    @JsonProperty("complete_ratio")
    private Double completeRatio;

    @JsonProperty("missing_channels")
    private List<String> missingChannels;

    @JsonProperty("interpolation_count")
    private Integer interpolationCount;

    @JsonProperty("degradation_applied")
    private Boolean degradationApplied;

    @JsonProperty("actual_channels_used")
    private List<String> actualChannelsUsed;

    public String getLevel() {
        return level;
    }

    public void setLevel(String level) {
        this.level = level;
    }

    public Double getCompleteRatio() {
        return completeRatio;
    }

    public void setCompleteRatio(Double completeRatio) {
        this.completeRatio = completeRatio;
    }

    public List<String> getMissingChannels() {
        return missingChannels;
    }

    public void setMissingChannels(List<String> missingChannels) {
        this.missingChannels = missingChannels;
    }

    public Integer getInterpolationCount() {
        return interpolationCount;
    }

    public void setInterpolationCount(Integer interpolationCount) {
        this.interpolationCount = interpolationCount;
    }

    public Boolean getDegradationApplied() {
        return degradationApplied;
    }

    public void setDegradationApplied(Boolean degradationApplied) {
        this.degradationApplied = degradationApplied;
    }

    public List<String> getActualChannelsUsed() {
        return actualChannelsUsed;
    }

    public void setActualChannelsUsed(List<String> actualChannelsUsed) {
        this.actualChannelsUsed = actualChannelsUsed;
    }

}