package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** TenantUserResponse */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TenantUserResponse {

    @JsonProperty("id")
    private Integer id;

    @JsonProperty("tenant_id")
    private Integer tenantId;

    @JsonProperty("username")
    private String username;

    @JsonProperty("display_name")
    private Object displayName;

    @JsonProperty("email")
    private Object email;

    @JsonProperty("phone")
    private Object phone;

    @JsonProperty("role")
    private String role;

    @JsonProperty("org_node_id")
    private Object orgNodeId;

    @JsonProperty("status")
    private String status;

    @JsonProperty("last_login_time")
    private Object lastLoginTime;

    @JsonProperty("create_time")
    private OffsetDateTime createTime;

    @JsonProperty("update_time")
    private OffsetDateTime updateTime;

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

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public Object getDisplayName() {
        return displayName;
    }

    public void setDisplayName(Object displayName) {
        this.displayName = displayName;
    }

    public Object getEmail() {
        return email;
    }

    public void setEmail(Object email) {
        this.email = email;
    }

    public Object getPhone() {
        return phone;
    }

    public void setPhone(Object phone) {
        this.phone = phone;
    }

    public String getRole() {
        return role;
    }

    public void setRole(String role) {
        this.role = role;
    }

    public Object getOrgNodeId() {
        return orgNodeId;
    }

    public void setOrgNodeId(Object orgNodeId) {
        this.orgNodeId = orgNodeId;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Object getLastLoginTime() {
        return lastLoginTime;
    }

    public void setLastLoginTime(Object lastLoginTime) {
        this.lastLoginTime = lastLoginTime;
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

}