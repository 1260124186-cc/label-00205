package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 碳排模型系数配置更新请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class CarbonModelConfigUpdateRequest {

    @JsonProperty("degradation")
    private Object degradation;

    @JsonProperty("leakage")
    private Object leakage;

    @JsonProperty("energy_carbon")
    private Object energyCarbon;

    @JsonProperty("operator_id")
    private Object operatorId;

    @JsonProperty("operator_name")
    private Object operatorName;

    @JsonProperty("description")
    private Object description;

    public Object getDegradation() {
        return degradation;
    }

    public void setDegradation(Object degradation) {
        this.degradation = degradation;
    }

    public Object getLeakage() {
        return leakage;
    }

    public void setLeakage(Object leakage) {
        this.leakage = leakage;
    }

    public Object getEnergyCarbon() {
        return energyCarbon;
    }

    public void setEnergyCarbon(Object energyCarbon) {
        this.energyCarbon = energyCarbon;
    }

    public Object getOperatorId() {
        return operatorId;
    }

    public void setOperatorId(Object operatorId) {
        this.operatorId = operatorId;
    }

    public Object getOperatorName() {
        return operatorName;
    }

    public void setOperatorName(Object operatorName) {
        this.operatorName = operatorName;
    }

    public Object getDescription() {
        return description;
    }

    public void setDescription(Object description) {
        this.description = description;
    }

}