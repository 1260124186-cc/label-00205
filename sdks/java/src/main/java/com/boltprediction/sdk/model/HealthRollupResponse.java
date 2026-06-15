package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 健康度汇总报表响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class HealthRollupResponse {

    @JsonProperty("report_id")
    private Object reportId;

    @JsonProperty("rollup_data")
    private ProductionLineHealthRollupSchema rollupData;

    @JsonProperty("saved")
    private Boolean saved;

    public Object getReportId() {
        return reportId;
    }

    public void setReportId(Object reportId) {
        this.reportId = reportId;
    }

    public ProductionLineHealthRollupSchema getRollupData() {
        return rollupData;
    }

    public void setRollupData(ProductionLineHealthRollupSchema rollupData) {
        this.rollupData = rollupData;
    }

    public Boolean getSaved() {
        return saved;
    }

    public void setSaved(Boolean saved) {
        this.saved = saved;
    }

}