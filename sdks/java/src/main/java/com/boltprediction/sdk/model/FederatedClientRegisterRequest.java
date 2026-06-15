package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 联邦学习客户端注册请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FederatedClientRegisterRequest {

    @JsonProperty("client_id")
    private String clientId;

    @JsonProperty("factory_name")
    private Object factoryName;

    @JsonProperty("location")
    private Object location;

    @JsonProperty("client_info")
    private Object clientInfo;

    public String getClientId() {
        return clientId;
    }

    public void setClientId(String clientId) {
        this.clientId = clientId;
    }

    public Object getFactoryName() {
        return factoryName;
    }

    public void setFactoryName(Object factoryName) {
        this.factoryName = factoryName;
    }

    public Object getLocation() {
        return location;
    }

    public void setLocation(Object location) {
        this.location = location;
    }

    public Object getClientInfo() {
        return clientInfo;
    }

    public void setClientInfo(Object clientInfo) {
        this.clientInfo = clientInfo;
    }

}