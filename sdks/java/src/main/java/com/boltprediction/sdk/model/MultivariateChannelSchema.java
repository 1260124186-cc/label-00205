package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 单通道时序元数据

Attributes:
    name: 通道名称（如 preload / temperature / humidity / vibration / torque / pressure）
    unit: 物理单位（可选）
    description: 中文描述（可选） */
@JsonIgnoreProperties(ignoreUnknown = true)
public class MultivariateChannelSchema {

    @JsonProperty("name")
    private String name;

    @JsonProperty("unit")
    private Object unit;

    @JsonProperty("description")
    private Object description;

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public Object getUnit() {
        return unit;
    }

    public void setUnit(Object unit) {
        this.unit = unit;
    }

    public Object getDescription() {
        return description;
    }

    public void setDescription(Object description) {
        this.description = description;
    }

}