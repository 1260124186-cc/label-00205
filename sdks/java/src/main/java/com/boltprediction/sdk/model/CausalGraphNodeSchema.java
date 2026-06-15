package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 因果图节点 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class CausalGraphNodeSchema {

    @JsonProperty("id")
    private String id;

    @JsonProperty("index")
    private Integer index;

    @JsonProperty("in_degree")
    private Integer inDegree;

    @JsonProperty("out_degree")
    private Integer outDegree;

    @JsonProperty("total_degree")
    private Integer totalDegree;

    @JsonProperty("centrality")
    private Double centrality;

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public Integer getIndex() {
        return index;
    }

    public void setIndex(Integer index) {
        this.index = index;
    }

    public Integer getInDegree() {
        return inDegree;
    }

    public void setInDegree(Integer inDegree) {
        this.inDegree = inDegree;
    }

    public Integer getOutDegree() {
        return outDegree;
    }

    public void setOutDegree(Integer outDegree) {
        this.outDegree = outDegree;
    }

    public Integer getTotalDegree() {
        return totalDegree;
    }

    public void setTotalDegree(Integer totalDegree) {
        this.totalDegree = totalDegree;
    }

    public Double getCentrality() {
        return centrality;
    }

    public void setCentrality(Double centrality) {
        this.centrality = centrality;
    }

}