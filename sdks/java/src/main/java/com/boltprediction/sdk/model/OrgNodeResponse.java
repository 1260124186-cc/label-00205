package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** OrgNodeResponse */
@JsonIgnoreProperties(ignoreUnknown = true)
public class OrgNodeResponse {

    @JsonProperty("id")
    private Integer id;

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

    @JsonProperty("path")
    private Object path;

    @JsonProperty("level")
    private Integer level;

    @JsonProperty("sort_order")
    private Integer sortOrder;

    @JsonProperty("extra_info")
    private Object extraInfo;

    @JsonProperty("status")
    private String status;

    @JsonProperty("create_time")
    private OffsetDateTime createTime;

    @JsonProperty("update_time")
    private OffsetDateTime updateTime;

    @JsonProperty("children")
    private Object children;

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

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

    public Object getPath() {
        return path;
    }

    public void setPath(Object path) {
        this.path = path;
    }

    public Integer getLevel() {
        return level;
    }

    public void setLevel(Integer level) {
        this.level = level;
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

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public OffsetDateTime getCreateTime() {
        return createTime;
    }

    public void setCreateTime(OffsetDateTime createTime) {
        this.createTime = createTime;
    }

    public OffsetDateTime getUpdateTime() {
        return updateTime;
    }

    public void setUpdateTime(OffsetDateTime updateTime) {
        this.updateTime = updateTime;
    }

    public Object getChildren() {
        return children;
    }

    public void setChildren(Object children) {
        this.children = children;
    }

}