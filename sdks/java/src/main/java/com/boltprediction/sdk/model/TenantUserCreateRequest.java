package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** TenantUserCreateRequest */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TenantUserCreateRequest {

    @JsonProperty("username")
    private String username;

    @JsonProperty("password")
    private String password;

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

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getPassword() {
        return password;
    }

    public void setPassword(String password) {
        this.password = password;
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

}