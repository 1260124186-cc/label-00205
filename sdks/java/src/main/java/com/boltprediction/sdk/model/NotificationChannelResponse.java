package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 通知渠道响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class NotificationChannelResponse {

    @JsonProperty("channel_type")
    private String channelType;

    @JsonProperty("channel_name")
    private Object channelName;

    @JsonProperty("config")
    private Object config;

    @JsonProperty("enabled")
    private Boolean enabled;

    @JsonProperty("is_default")
    private Boolean isDefault;

    @JsonProperty("id")
    private Integer id;

    @JsonProperty("create_time")
    private OffsetDateTime createTime;

    @JsonProperty("update_time")
    private OffsetDateTime updateTime;

    public String getChannelType() {
        return channelType;
    }

    public void setChannelType(String channelType) {
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

    public Boolean getEnabled() {
        return enabled;
    }

    public void setEnabled(Boolean enabled) {
        this.enabled = enabled;
    }

    public Boolean getIsDefault() {
        return isDefault;
    }

    public void setIsDefault(Boolean isDefault) {
        this.isDefault = isDefault;
    }

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
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