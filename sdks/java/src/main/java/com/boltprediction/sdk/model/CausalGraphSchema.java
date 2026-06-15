package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 因果图 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class CausalGraphSchema {

    @JsonProperty("nodes")
    private List<CausalGraphNodeSchema> nodes;

    @JsonProperty("edges")
    private List<CausalGraphEdgeSchema> edges;

    @JsonProperty("adjacency_matrix")
    private List<List<Double>> adjacencyMatrix;

    @JsonProperty("edge_weights")
    private List<List<Double>> edgeWeights;

    @JsonProperty("bolt_ids")
    private List<String> boltIds;

    public List<CausalGraphNodeSchema> getNodes() {
        return nodes;
    }

    public void setNodes(List<CausalGraphNodeSchema> nodes) {
        this.nodes = nodes;
    }

    public List<CausalGraphEdgeSchema> getEdges() {
        return edges;
    }

    public void setEdges(List<CausalGraphEdgeSchema> edges) {
        this.edges = edges;
    }

    public List<List<Double>> getAdjacencyMatrix() {
        return adjacencyMatrix;
    }

    public void setAdjacencyMatrix(List<List<Double>> adjacencyMatrix) {
        this.adjacencyMatrix = adjacencyMatrix;
    }

    public List<List<Double>> getEdgeWeights() {
        return edgeWeights;
    }

    public void setEdgeWeights(List<List<Double>> edgeWeights) {
        this.edgeWeights = edgeWeights;
    }

    public List<String> getBoltIds() {
        return boltIds;
    }

    public void setBoltIds(List<String> boltIds) {
        this.boltIds = boltIds;
    }

}