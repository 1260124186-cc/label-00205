package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 根因螺栓信息 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class RootCauseBoltSchema {

    @JsonProperty("bolt_id")
    private String boltId;

    @JsonProperty("index")
    private Integer index;

    @JsonProperty("root_cause_score")
    private Double rootCauseScore;

    @JsonProperty("status_code")
    private Integer statusCode;

    @JsonProperty("health_index")
    private Double healthIndex;

    @JsonProperty("is_abnormal")
    private Boolean isAbnormal;

    public String getBoltId() {
        return boltId;
    }

    public void setBoltId(String boltId) {
        this.boltId = boltId;
    }

    public Integer getIndex() {
        return index;
    }

    public void setIndex(Integer index) {
        this.index = index;
    }

    public Double getRootCauseScore() {
        return rootCauseScore;
    }

    public void setRootCauseScore(Double rootCauseScore) {
        this.rootCauseScore = rootCauseScore;
    }

    public Integer getStatusCode() {
        return statusCode;
    }

    public void setStatusCode(Integer statusCode) {
        this.statusCode = statusCode;
    }

    public Double getHealthIndex() {
        return healthIndex;
    }

    public void setHealthIndex(Double healthIndex) {
        this.healthIndex = healthIndex;
    }

    public Boolean getIsAbnormal() {
        return isAbnormal;
    }

    public void setIsAbnormal(Boolean isAbnormal) {
        this.isAbnormal = isAbnormal;
    }

}