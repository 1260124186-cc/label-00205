package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** OrgNodeCreateRequest */
@JsonIgnoreProperties(ignoreUnknown = true)
public class OrgNodeCreateRequest {

    @JsonProperty("tenant_id")
    private Integer tenantId;

    @JsonProperty("parent_id")
    private Object parentId;

    @JsonProperty("node_code")
    private Object nodeCode;

    @JsonProperty("node_name")
    private String nodeName;

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("sort_order")
    private Integer sortOrder;

    @JsonProperty("extra_info")
    private Object extraInfo;

    public Integer getTenantId() {
        return tenantId;
    }

    public void setTenantId(Integer tenantId) {
        this.tenantId = tenantId;
    }

    public Object getParentId() {
        return parentId;
    }

    public void setParentId(Object parentId) {
        this.parentId = parentId;
    }

    public Object getNodeCode() {
        return nodeCode;
    }

    public void setNodeCode(Object nodeCode) {
        this.nodeCode = nodeCode;
    }

    public String getNodeName() {
        return nodeName;
    }

    public void setNodeName(String nodeName) {
        this.nodeName = nodeName;
    }

    public String getNodeType() {
        return nodeType;
    }

    public void setNodeType(String nodeType) {
        this.nodeType = nodeType;
    }

    public Integer getSortOrder() {
        return sortOrder;
    }

    public void setSortOrder(Integer sortOrder) {
        this.sortOrder = sortOrder;
    }

    public Object getExtraInfo() {
        return extraInfo;
    }

    public void setExtraInfo(Object extraInfo) {
        this.extraInfo = extraInfo;
    }

}