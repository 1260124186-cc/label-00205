package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** TenantResponse */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TenantResponse {

    @JsonProperty("id")
    private Integer id;

    @JsonProperty("tenant_code")
    private String tenantCode;

    @JsonProperty("tenant_name")
    private String tenantName;

    @JsonProperty("contact_email")
    private Object contactEmail;

    @JsonProperty("contact_phone")
    private Object contactPhone;

    @JsonProperty("status")
    private String status;

    @JsonProperty("settings")
    private Object settings;

    @JsonProperty("expire_time")
    private Object expireTime;

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

    public String getTenantCode() {
        return tenantCode;
    }

    public void setTenantCode(String tenantCode) {
        this.tenantCode = tenantCode;
    }

    public String getTenantName() {
        return tenantName;
    }

    public void setTenantName(String tenantName) {
        this.tenantName = tenantName;
    }

    public Object getContactEmail() {
        return contactEmail;
    }

    public void setContactEmail(Object contactEmail) {
        this.contactEmail = contactEmail;
    }

    public Object getContactPhone() {
        return contactPhone;
    }

    public void setContactPhone(Object contactPhone) {
        this.contactPhone = contactPhone;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Object getSettings() {
        return settings;
    }

    public void setSettings(Object settings) {
        this.settings = settings;
    }

    public Object getExpireTime() {
        return expireTime;
    }

    public void setExpireTime(Object expireTime) {
        this.expireTime = expireTime;
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