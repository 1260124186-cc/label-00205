package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 根因分析结果 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class RootCauseAnalysisSchema {

    @JsonProperty("root_cause_bolt")
    private Object rootCauseBolt;

    @JsonProperty("root_cause_ranking")
    private List<RootCauseBoltSchema> rootCauseRanking;

    @JsonProperty("abnormal_bolts")
    private List<String> abnormalBolts;

    @JsonProperty("is_unbalanced_loosening")
    private Boolean isUnbalancedLoosening;

    @JsonProperty("total_bolts")
    private Integer totalBolts;

    @JsonProperty("abnormal_count")
    private Integer abnormalCount;

    public Object getRootCauseBolt() {
        return rootCauseBolt;
    }

    public void setRootCauseBolt(Object rootCauseBolt) {
        this.rootCauseBolt = rootCauseBolt;
    }

    public List<RootCauseBoltSchema> getRootCauseRanking() {
        return rootCauseRanking;
    }

    public void setRootCauseRanking(List<RootCauseBoltSchema> rootCauseRanking) {
        this.rootCauseRanking = rootCauseRanking;
    }

    public List<String> getAbnormalBolts() {
        return abnormalBolts;
    }

    public void setAbnormalBolts(List<String> abnormalBolts) {
        this.abnormalBolts = abnormalBolts;
    }

    public Boolean getIsUnbalancedLoosening() {
        return isUnbalancedLoosening;
    }

    public void setIsUnbalancedLoosening(Boolean isUnbalancedLoosening) {
        this.isUnbalancedLoosening = isUnbalancedLoosening;
    }

    public Integer getTotalBolts() {
        return totalBolts;
    }

    public void setTotalBolts(Integer totalBolts) {
        this.totalBolts = totalBolts;
    }

    public Integer getAbnormalCount() {
        return abnormalCount;
    }

    public void setAbnormalCount(Integer abnormalCount) {
        this.abnormalCount = abnormalCount;
    }

}