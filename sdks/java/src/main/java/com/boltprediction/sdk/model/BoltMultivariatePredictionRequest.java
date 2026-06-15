package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 螺栓多变量耦合预测请求

请求支持两种数据格式：
1. channels 分开提供（各通道时间戳可以不同，服务端会自动对齐插值）
2. aligned_data 统一提供（各通道已在同一时间网格上，仅需缺失值插值）

Attributes:
    bolt_id: 螺栓唯一标识
    channels: 分通道提供的时序数据 {通道名: [[时间, 值], ...]}
    aligned_data: 已对齐的多通道数据 [[时间, 通道1, 通道2, ...], ...]
    aligned_channel_names: 使用 aligned_data 时必须提供，对应列的通道名称（不含时间列）
    timestamps: 可选，统一目标时间网格
    apply_temp_compensation: 是否执行温度耦合补偿（默认 True）
    enable_degradation: 缺失严重时是否降级为单变量预测（默认 True）
    version: 模型版本号（可选） */
@JsonIgnoreProperties(ignoreUnknown = true)
public class BoltMultivariatePredictionRequest {

    @JsonProperty("bolt_id")
    private String boltId;

    @JsonProperty("channels")
    private Object channels;

    @JsonProperty("aligned_data")
    private Object alignedData;

    @JsonProperty("aligned_channel_names")
    private Object alignedChannelNames;

    @JsonProperty("timestamps")
    private Object timestamps;

    @JsonProperty("apply_temp_compensation")
    private Boolean applyTempCompensation;

    @JsonProperty("enable_degradation")
    private Boolean enableDegradation;

    @JsonProperty("version")
    private Object version;

    public String getBoltId() {
        return boltId;
    }

    public void setBoltId(String boltId) {
        this.boltId = boltId;
    }

    public Object getChannels() {
        return channels;
    }

    public void setChannels(Object channels) {
        this.channels = channels;
    }

    public Object getAlignedData() {
        return alignedData;
    }

    public void setAlignedData(Object alignedData) {
        this.alignedData = alignedData;
    }

    public Object getAlignedChannelNames() {
        return alignedChannelNames;
    }

    public void setAlignedChannelNames(Object alignedChannelNames) {
        this.alignedChannelNames = alignedChannelNames;
    }

    public Object getTimestamps() {
        return timestamps;
    }

    public void setTimestamps(Object timestamps) {
        this.timestamps = timestamps;
    }

    public Boolean getApplyTempCompensation() {
        return applyTempCompensation;
    }

    public void setApplyTempCompensation(Boolean applyTempCompensation) {
        this.applyTempCompensation = applyTempCompensation;
    }

    public Boolean getEnableDegradation() {
        return enableDegradation;
    }

    public void setEnableDegradation(Boolean enableDegradation) {
        this.enableDegradation = enableDegradation;
    }

    public Object getVersion() {
        return version;
    }

    public void setVersion(Object version) {
        this.version = version;
    }

}