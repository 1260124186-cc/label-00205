package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 流式数据注入响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class StreamDataIngestResponse {

    @JsonProperty("success")
    private Boolean success;

    @JsonProperty("message")
    private String message;

    @JsonProperty("node_id")
    private Object nodeId;

    @JsonProperty("node_type")
    private Object nodeType;

    @JsonProperty("window_current_size")
    private Object windowCurrentSize;

    @JsonProperty("window_is_full")
    private Object windowIsFull;

    @JsonProperty("accepted")
    private Boolean accepted;

    public Boolean getSuccess() {
        return success;
    }

    public void setSuccess(Boolean success) {
        this.success = success;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public Object getNodeId() {
        return nodeId;
    }

    public void setNodeId(Object nodeId) {
        this.nodeId = nodeId;
    }

    public Object getNodeType() {
        return nodeType;
    }

    public void setNodeType(Object nodeType) {
        this.nodeType = nodeType;
    }

    public Object getWindowCurrentSize() {
        return windowCurrentSize;
    }

    public void setWindowCurrentSize(Object windowCurrentSize) {
        this.windowCurrentSize = windowCurrentSize;
    }

    public Object getWindowIsFull() {
        return windowIsFull;
    }

    public void setWindowIsFull(Object windowIsFull) {
        this.windowIsFull = windowIsFull;
    }

    public Boolean getAccepted() {
        return accepted;
    }

    public void setAccepted(Boolean accepted) {
        this.accepted = accepted;
    }

}