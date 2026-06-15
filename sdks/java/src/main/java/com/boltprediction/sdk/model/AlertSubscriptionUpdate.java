package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 更新订阅请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AlertSubscriptionUpdate {

    @JsonProperty("subscriber_type")
    private Object subscriberType;

    @JsonProperty("subscriber_id")
    private Object subscriberId;

    @JsonProperty("subscriber_name")
    private Object subscriberName;

    @JsonProperty("min_alert_level")
    private Object minAlertLevel;

    @JsonProperty("alert_levels")
    private Object alertLevels;

    @JsonProperty("node_type")
    private Object nodeType;

    @JsonProperty("node_ids")
    private Object nodeIds;

    @JsonProperty("notify_channels")
    private Object notifyChannels;

    @JsonProperty("notify_targets")
    private Object notifyTargets;

    @JsonProperty("enabled")
    private Object enabled;

    public Object getSubscriberType() {
        return subscriberType;
    }

    public void setSubscriberType(Object subscriberType) {
        this.subscriberType = subscriberType;
    }

    public Object getSubscriberId() {
        return subscriberId;
    }

    public void setSubscriberId(Object subscriberId) {
        this.subscriberId = subscriberId;
    }

    public Object getSubscriberName() {
        return subscriberName;
    }

    public void setSubscriberName(Object subscriberName) {
        this.subscriberName = subscriberName;
    }

    public Object getMinAlertLevel() {
        return minAlertLevel;
    }

    public void setMinAlertLevel(Object minAlertLevel) {
        this.minAlertLevel = minAlertLevel;
    }

    public Object getAlertLevels() {
        return alertLevels;
    }

    public void setAlertLevels(Object alertLevels) {
        this.alertLevels = alertLevels;
    }

    public Object getNodeType() {
        return nodeType;
    }

    public void setNodeType(Object nodeType) {
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

    public Object getEnabled() {
        return enabled;
    }

    public void setEnabled(Object enabled) {
        this.enabled = enabled;
    }

}