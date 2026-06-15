package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 创建告警规则请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AlertRuleCreate {

    @JsonProperty("rule_name")
    private String ruleName;

    @JsonProperty("alert_level")
    private Integer alertLevel;

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("node_ids")
    private Object nodeIds;

    @JsonProperty("min_confidence")
    private Double minConfidence;

    @JsonProperty("silence_period")
    private Integer silencePeriod;

    @JsonProperty("enable_upgrade")
    private Boolean enableUpgrade;

    @JsonProperty("upgrade_minutes")
    private Integer upgradeMinutes;

    @JsonProperty("upgrade_to_level")
    private Object upgradeToLevel;

    @JsonProperty("enabled")
    private Boolean enabled;

    @JsonProperty("description")
    private Object description;

    public String getRuleName() {
        return ruleName;
    }

    public void setRuleName(String ruleName) {
        this.ruleName = ruleName;
    }

    public Integer getAlertLevel() {
        return alertLevel;
    }

    public void setAlertLevel(Integer alertLevel) {
        this.alertLevel = alertLevel;
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

    public Double getMinConfidence() {
        return minConfidence;
    }

    public void setMinConfidence(Double minConfidence) {
        this.minConfidence = minConfidence;
    }

    public Integer getSilencePeriod() {
        return silencePeriod;
    }

    public void setSilencePeriod(Integer silencePeriod) {
        this.silencePeriod = silencePeriod;
    }

    public Boolean getEnableUpgrade() {
        return enableUpgrade;
    }

    public void setEnableUpgrade(Boolean enableUpgrade) {
        this.enableUpgrade = enableUpgrade;
    }

    public Integer getUpgradeMinutes() {
        return upgradeMinutes;
    }

    public void setUpgradeMinutes(Integer upgradeMinutes) {
        this.upgradeMinutes = upgradeMinutes;
    }

    public Object getUpgradeToLevel() {
        return upgradeToLevel;
    }

    public void setUpgradeToLevel(Object upgradeToLevel) {
        this.upgradeToLevel = upgradeToLevel;
    }

    public Boolean getEnabled() {
        return enabled;
    }

    public void setEnabled(Boolean enabled) {
        this.enabled = enabled;
    }

    public Object getDescription() {
        return description;
    }

    public void setDescription(Object description) {
        this.description = description;
    }

}