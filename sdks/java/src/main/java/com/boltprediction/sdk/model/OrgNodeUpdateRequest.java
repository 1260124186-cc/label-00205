package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** OrgNodeUpdateRequest */
@JsonIgnoreProperties(ignoreUnknown = true)
public class OrgNodeUpdateRequest {

    @JsonProperty("node_name")
    private Object nodeName;

    @JsonProperty("node_code")
    private Object nodeCode;

    @JsonProperty("sort_order")
    private Object sortOrder;

    @JsonProperty("extra_info")
    private Object extraInfo;

    @JsonProperty("status")
    private Object status;

    public Object getNodeName() {
        return nodeName;
    }

    public void setNodeName(Object nodeName) {
        this.nodeName = nodeName;
    }

    public Object getNodeCode() {
        return nodeCode;
    }

    public void setNodeCode(Object nodeCode) {
        this.nodeCode = nodeCode;
    }

    public Object getSortOrder() {
        return sortOrder;
    }

    public void setSortOrder(Object sortOrder) {
        this.sortOrder = sortOrder;
    }

    public Object getExtraInfo() {
        return extraInfo;
    }

    public void setExtraInfo(Object extraInfo) {
        this.extraInfo = extraInfo;
    }

    public Object getStatus() {
        return status;
    }

    public void setStatus(Object status) {
        this.status = status;
    }

}