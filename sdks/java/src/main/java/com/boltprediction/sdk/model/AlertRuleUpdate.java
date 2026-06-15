package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 更新告警规则请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AlertRuleUpdate {

    @JsonProperty("rule_name")
    private Object ruleName;

    @JsonProperty("alert_level")
    private Object alertLevel;

    @JsonProperty("node_type")
    private Object nodeType;

    @JsonProperty("node_ids")
    private Object nodeIds;

    @JsonProperty("min_confidence")
    private Object minConfidence;

    @JsonProperty("silence_period")
    private Object silencePeriod;

    @JsonProperty("enable_upgrade")
    private Object enableUpgrade;

    @JsonProperty("upgrade_minutes")
    private Object upgradeMinutes;

    @JsonProperty("upgrade_to_level")
    private Object upgradeToLevel;

    @JsonProperty("enabled")
    private Object enabled;

    @JsonProperty("description")
    private Object description;

    public Object getRuleName() {
        return ruleName;
    }

    public void setRuleName(Object ruleName) {
        this.ruleName = ruleName;
    }

    public Object getAlertLevel() {
        return alertLevel;
    }

    public void setAlertLevel(Object alertLevel) {
        this.alertLevel = alertLevel;
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

    public Object getMinConfidence() {
        return minConfidence;
    }

    public void setMinConfidence(Object minConfidence) {
        this.minConfidence = minConfidence;
    }

    public Object getSilencePeriod() {
        return silencePeriod;
    }

    public void setSilencePeriod(Object silencePeriod) {
        this.silencePeriod = silencePeriod;
    }

    public Object getEnableUpgrade() {
        return enableUpgrade;
    }

    public void setEnableUpgrade(Object enableUpgrade) {
        this.enableUpgrade = enableUpgrade;
    }

    public Object getUpgradeMinutes() {
        return upgradeMinutes;
    }

    public void setUpgradeMinutes(Object upgradeMinutes) {
        this.upgradeMinutes = upgradeMinutes;
    }

    public Object getUpgradeToLevel() {
        return upgradeToLevel;
    }

    public void setUpgradeToLevel(Object upgradeToLevel) {
        this.upgradeToLevel = upgradeToLevel;
    }

    public Object getEnabled() {
        return enabled;
    }

    public void setEnabled(Object enabled) {
        this.enabled = enabled;
    }

    public Object getDescription() {
        return description;
    }

    public void setDescription(Object description) {
        this.description = description;
    }

}