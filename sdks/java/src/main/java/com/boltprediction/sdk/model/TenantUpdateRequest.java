package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** TenantUpdateRequest */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TenantUpdateRequest {

    @JsonProperty("tenant_name")
    private Object tenantName;

    @JsonProperty("contact_email")
    private Object contactEmail;

    @JsonProperty("contact_phone")
    private Object contactPhone;

    @JsonProperty("status")
    private Object status;

    @JsonProperty("expire_time")
    private Object expireTime;

    @JsonProperty("settings")
    private Object settings;

    public Object getTenantName() {
        return tenantName;
    }

    public void setTenantName(Object tenantName) {
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

    public Object getStatus() {
        return status;
    }

    public void setStatus(Object status) {
        this.status = status;
    }

    public Object getExpireTime() {
        return expireTime;
    }

    public void setExpireTime(Object expireTime) {
        this.expireTime = expireTime;
    }

    public Object getSettings() {
        return settings;
    }

    public void setSettings(Object settings) {
        this.settings = settings;
    }

}