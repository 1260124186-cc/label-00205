package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 创建订阅请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AlertSubscriptionCreate {

    @JsonProperty("subscriber_type")
    private String subscriberType;

    @JsonProperty("subscriber_id")
    private String subscriberId;

    @JsonProperty("subscriber_name")
    private Object subscriberName;

    @JsonProperty("min_alert_level")
    private Integer minAlertLevel;

    @JsonProperty("alert_levels")
    private Object alertLevels;

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("node_ids")
    private Object nodeIds;

    @JsonProperty("notify_channels")
    private Object notifyChannels;

    @JsonProperty("notify_targets")
    private Object notifyTargets;

    @JsonProperty("enabled")
    private Boolean enabled;

    public String getSubscriberType() {
        return subscriberType;
    }

    public void setSubscriberType(String subscriberType) {
        this.subscriberType = subscriberType;
    }

    public String getSubscriberId() {
        return subscriberId;
    }

    public void setSubscriberId(String subscriberId) {
        this.subscriberId = subscriberId;
    }

    public Object getSubscriberName() {
        return subscriberName;
    }

    public void setSubscriberName(Object subscriberName) {
        this.subscriberName = subscriberName;
    }

    public Integer getMinAlertLevel() {
        return minAlertLevel;
    }

    public void setMinAlertLevel(Integer minAlertLevel) {
        this.minAlertLevel = minAlertLevel;
    }

    public Object getAlertLevels() {
        return alertLevels;
    }

    public void setAlertLevels(Object alertLevels) {
        this.alertLevels = alertLevels;
    }

    public String getNodeType() {
        return nodeType;
    }

    public void setNodeType(String nodeType) {
        this.nodeType = nodeType;
    }

    public Object getNodeIds() {
        return nodeIds;
    }

    public void setNodeIds(Object nodeIds) {
        this.nodeIds = nodeIds;
    }

    public Object getNotifyChannels() {
        return notifyChannels;
    }

    public void setNotifyChannels(Object notifyChannels) {
        this.notifyChannels = notifyChannels;
    }

    public Object getNotifyTargets() {
        return notifyTargets;
    }

    public void setNotifyTargets(Object notifyTargets) {
        this.notifyTargets = notifyTargets;
    }

    public Boolean getEnabled() {
        return enabled;
    }

    public void setEnabled(Boolean enabled) {
        this.enabled = enabled;
    }

}