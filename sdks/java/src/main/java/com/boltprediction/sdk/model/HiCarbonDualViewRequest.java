package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** HI rollup 与碳排并列展示请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class HiCarbonDualViewRequest {

    @JsonProperty("nodes")
    private List<Map<String, Object>> nodes;

    public List<Map<String, Object>> getNodes() {
        return nodes;
    }

    public void setNodes(List<Map<String, Object>> nodes) {
        this.nodes = nodes;
    }

}