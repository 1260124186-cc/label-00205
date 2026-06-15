package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** EdgeDeviceRegisterRequest */
@JsonIgnoreProperties(ignoreUnknown = true)
public class EdgeDeviceRegisterRequest {

    @JsonProperty("device_id")
    private String deviceId;

    @JsonProperty("device_name")
    private Object deviceName;

    @JsonProperty("device_type")
    private Object deviceType;

    @JsonProperty("location")
    private Object location;

    @JsonProperty("capabilities")
    private Object capabilities;

    public String getDeviceId() {
        return deviceId;
    }

    public void setDeviceId(String deviceId) {
        this.deviceId = deviceId;
    }

    public Object getDeviceName() {
        return deviceName;
    }

    public void setDeviceName(Object deviceName) {
        this.deviceName = deviceName;
    }

    public Object getDeviceType() {
        return deviceType;
    }

    public void setDeviceType(Object deviceType) {
        this.deviceType = deviceType;
    }

    public Object getLocation() {
        return location;
    }

    public void setLocation(Object location) {
        this.location = location;
    }

    public Object getCapabilities() {
        return capabilities;
    }

    public void setCapabilities(Object capabilities) {
        this.capabilities = capabilities;
    }

}