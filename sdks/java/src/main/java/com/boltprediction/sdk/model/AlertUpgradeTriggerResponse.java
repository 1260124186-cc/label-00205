package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 手动触发告警升级响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AlertUpgradeTriggerResponse {

    @JsonProperty("upgraded_count")
    private Integer upgradedCount;

    @JsonProperty("message")
    private String message;

    public Integer getUpgradedCount() {
        return upgradedCount;
    }

    public void setUpgradedCount(Integer upgradedCount) {
        this.upgradedCount = upgradedCount;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

}