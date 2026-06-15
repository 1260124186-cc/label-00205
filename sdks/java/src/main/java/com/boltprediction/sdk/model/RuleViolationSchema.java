package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 规则违反详情 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class RuleViolationSchema {

    @JsonProperty("rule_type")
    private String ruleType;

    @JsonProperty("rule_name")
    private String ruleName;

    @JsonProperty("severity")
    private String severity;

    @JsonProperty("description")
    private String description;

    @JsonProperty("violation_indices")
    private List<Integer> violationIndices;

    @JsonProperty("violation_values")
    private Object violationValues;

    @JsonProperty("threshold")
    private Object threshold;

    @JsonProperty("actual_value")
    private Object actualValue;

    public String getRuleType() {
        return ruleType;
    }

    public void setRuleType(String ruleType) {
        this.ruleType = ruleType;
    }

    public String getRuleName() {
        return ruleName;
    }

    public void setRuleName(String ruleName) {
        this.ruleName = ruleName;
    }

    public String getSeverity() {
        return severity;
    }

    public void setSeverity(String severity) {
        this.severity = severity;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public List<Integer> getViolationIndices() {
        return violationIndices;
    }

    public void setViolationIndices(List<Integer> violationIndices) {
        this.violationIndices = violationIndices;
    }

    public Object getViolationValues() {
        return violationValues;
    }

    public void setViolationValues(Object violationValues) {
        this.violationValues = violationValues;
    }

    public Object getThreshold() {
        return threshold;
    }

    public void setThreshold(Object threshold) {
        this.threshold = threshold;
    }

    public Object getActualValue() {
        return actualValue;
    }

    public void setActualValue(Object actualValue) {
        this.actualValue = actualValue;
    }

}