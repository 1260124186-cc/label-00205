package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 更新通知渠道请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class NotificationChannelUpdate {

    @JsonProperty("channel_type")
    private Object channelType;

    @JsonProperty("channel_name")
    private Object channelName;

    @JsonProperty("config")
    private Object config;

    @JsonProperty("enabled")
    private Object enabled;

    @JsonProperty("is_default")
    private Object isDefault;

    public Object getChannelType() {
        return channelType;
    }

    public void setChannelType(Object channelType) {
        this.channelType = channelType;
    }

    public Object getChannelName() {
        return channelName;
    }

    public void setChannelName(Object channelName) {
        this.channelName = channelName;
    }

    public Object getConfig() {
        return config;
    }

    public void setConfig(Object config) {
        this.config = config;
    }

    public Object getEnabled() {
        return enabled;
    }

    public void setEnabled(Object enabled) {
        this.enabled = enabled;
    }

    public Object getIsDefault() {
        return isDefault;
    }

    public void setIsDefault(Object isDefault) {
        this.isDefault = isDefault;
    }

}