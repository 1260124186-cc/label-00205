package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 更新审计记录保留年限请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AuditRetentionUpdateRequest {

    @JsonProperty("retention_years")
    private Integer retentionYears;

    public Integer getRetentionYears() {
        return retentionYears;
    }

    public void setRetentionYears(Integer retentionYears) {
        this.retentionYears = retentionYears;
    }

}