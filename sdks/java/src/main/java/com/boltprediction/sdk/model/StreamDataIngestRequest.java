package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 流式数据注入请求

支持单条或微批次数据注入 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class StreamDataIngestRequest {

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("value")
    private Object value;

    @JsonProperty("timestamp")
    private Object timestamp;

    @JsonProperty("values")
    private Object values;

    @JsonProperty("timestamps")
    private Object timestamps;

    @JsonProperty("data")
    private Object data;

    @JsonProperty("metadata")
    private Object metadata;

    public String getNodeType() {
        return nodeType;
    }

    public void setNodeType(String nodeType) {
        this.nodeType = nodeType;
    }

    public String getNodeId() {
        return nodeId;
    }

    public void setNodeId(String nodeId) {
        this.nodeId = nodeId;
    }

    public Object getValue() {
        return value;
    }

    public void setValue(Object value) {
        this.value = value;
    }

    public Object getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(Object timestamp) {
        this.timestamp = timestamp;
    }

    public Object getValues() {
        return values;
    }

    public void setValues(Object values) {
        this.values = values;
    }

    public Object getTimestamps() {
        return timestamps;
    }

    public void setTimestamps(Object timestamps) {
        this.timestamps = timestamps;
    }

    public Object getData() {
        return data;
    }

    public void setData(Object data) {
        this.data = data;
    }

    public Object getMetadata() {
        return metadata;
    }

    public void setMetadata(Object metadata) {
        this.metadata = metadata;
    }

}