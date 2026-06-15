package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 领先螺栓信息 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class LeadingBoltSchema {

    @JsonProperty("bolt_id")
    private String boltId;

    @JsonProperty("index")
    private Integer index;

    @JsonProperty("leading_score")
    private Double leadingScore;

    @JsonProperty("out_degree")
    private Integer outDegree;

    @JsonProperty("in_degree")
    private Integer inDegree;

    @JsonProperty("net_degree")
    private Integer netDegree;

    @JsonProperty("out_strength")
    private Double outStrength;

    @JsonProperty("in_strength")
    private Double inStrength;

    @JsonProperty("net_strength")
    private Double netStrength;

    @JsonProperty("trend_leadership")
    private Double trendLeadership;

    @JsonProperty("is_leading")
    private Boolean isLeading;

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

    public Double getLeadingScore() {
        return leadingScore;
    }

    public void setLeadingScore(Double leadingScore) {
        this.leadingScore = leadingScore;
    }

    public Integer getOutDegree() {
        return outDegree;
    }

    public void setOutDegree(Integer outDegree) {
        this.outDegree = outDegree;
    }

    public Integer getInDegree() {
        return inDegree;
    }

    public void setInDegree(Integer inDegree) {
        this.inDegree = inDegree;
    }

    public Integer getNetDegree() {
        return netDegree;
    }

    public void setNetDegree(Integer netDegree) {
        this.netDegree = netDegree;
    }

    public Double getOutStrength() {
        return outStrength;
    }

    public void setOutStrength(Double outStrength) {
        this.outStrength = outStrength;
    }

    public Double getInStrength() {
        return inStrength;
    }

    public void setInStrength(Double inStrength) {
        this.inStrength = inStrength;
    }

    public Double getNetStrength() {
        return netStrength;
    }

    public void setNetStrength(Double netStrength) {
        this.netStrength = netStrength;
    }

    public Double getTrendLeadership() {
        return trendLeadership;
    }

    public void setTrendLeadership(Double trendLeadership) {
        this.trendLeadership = trendLeadership;
    }

    public Boolean getIsLeading() {
        return isLeading;
    }

    public void setIsLeading(Boolean isLeading) {
        this.isLeading = isLeading;
    }

}