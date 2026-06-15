package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 装置级月度碳排风险排行请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class CarbonMonthlyRankingRequest {

    @JsonProperty("nodes")
    private List<Map<String, Object>> nodes;

    @JsonProperty("top_n")
    private Object topN;

    public List<Map<String, Object>> getNodes() {
        return nodes;
    }

    public void setNodes(List<Map<String, Object>> nodes) {
        this.nodes = nodes;
    }

    public Object getTopN() {
        return topN;
    }

    public void setTopN(Object topN) {
        this.topN = topN;
    }

}