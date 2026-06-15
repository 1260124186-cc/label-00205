package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** TenantUserUpdateRequest */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TenantUserUpdateRequest {

    @JsonProperty("display_name")
    private Object displayName;

    @JsonProperty("email")
    private Object email;

    @JsonProperty("phone")
    private Object phone;

    @JsonProperty("role")
    private Object role;

    @JsonProperty("org_node_id")
    private Object orgNodeId;

    @JsonProperty("status")
    private Object status;

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

    public Object getRole() {
        return role;
    }

    public void setRole(Object role) {
        this.role = role;
    }

    public Object getOrgNodeId() {
        return orgNodeId;
    }

    public void setOrgNodeId(Object orgNodeId) {
        this.orgNodeId = orgNodeId;
    }

    public Object getStatus() {
        return status;
    }

    public void setStatus(Object status) {
        this.status = status;
    }

}