package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** TenantCreateRequest */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TenantCreateRequest {

    @JsonProperty("tenant_code")
    private String tenantCode;

    @JsonProperty("tenant_name")
    private String tenantName;

    @JsonProperty("contact_email")
    private Object contactEmail;

    @JsonProperty("contact_phone")
    private Object contactPhone;

    @JsonProperty("expire_time")
    private Object expireTime;

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

    public Object getExpireTime() {
        return expireTime;
    }

    public void setExpireTime(Object expireTime) {
        this.expireTime = expireTime;
    }

}