package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 因果图边 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class CausalGraphEdgeSchema {

    @JsonProperty("source")
    private String source;

    @JsonProperty("target")
    private String target;

    @JsonProperty("source_idx")
    private Integer sourceIdx;

    @JsonProperty("target_idx")
    private Integer targetIdx;

    @JsonProperty("weight")
    private Double weight;

    @JsonProperty("correlation")
    private Double correlation;

    @JsonProperty("p_value")
    private Object pValue;

    @JsonProperty("f_stat")
    private Object fStat;

    @JsonProperty("lag")
    private Object lag;

    @JsonProperty("type")
    private String type;

    public String getSource() {
        return source;
    }

    public void setSource(String source) {
        this.source = source;
    }

    public String getTarget() {
        return target;
    }

    public void setTarget(String target) {
        this.target = target;
    }

    public Integer getSourceIdx() {
        return sourceIdx;
    }

    public void setSourceIdx(Integer sourceIdx) {
        this.sourceIdx = sourceIdx;
    }

    public Integer getTargetIdx() {
        return targetIdx;
    }

    public void setTargetIdx(Integer targetIdx) {
        this.targetIdx = targetIdx;
    }

    public Double getWeight() {
        return weight;
    }

    public void setWeight(Double weight) {
        this.weight = weight;
    }

    public Double getCorrelation() {
        return correlation;
    }

    public void setCorrelation(Double correlation) {
        this.correlation = correlation;
    }

    public Object getPValue() {
        return pValue;
    }

    public void setPValue(Object pValue) {
        this.pValue = pValue;
    }

    public Object getFStat() {
        return fStat;
    }

    public void setFStat(Object fStat) {
        this.fStat = fStat;
    }

    public Object getLag() {
        return lag;
    }

    public void setLag(Object lag) {
        this.lag = lag;
    }

    public String getType() {
        return type;
    }

    public void setType(String type) {
        this.type = type;
    }

}