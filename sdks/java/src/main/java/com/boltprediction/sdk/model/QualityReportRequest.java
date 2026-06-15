package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 生成质量报告请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class QualityReportRequest {

    @JsonProperty("report_date")
    private Object reportDate;

    @JsonProperty("sensor_ids")
    private Object sensorIds;

    @JsonProperty("save_to_db")
    private Boolean saveToDb;

    public Object getReportDate() {
        return reportDate;
    }

    public void setReportDate(Object reportDate) {
        this.reportDate = reportDate;
    }

    public Object getSensorIds() {
        return sensorIds;
    }

    public void setSensorIds(Object sensorIds) {
        this.sensorIds = sensorIds;
    }

    public Boolean getSaveToDb() {
        return saveToDb;
    }

    public void setSaveToDb(Boolean saveToDb) {
        this.saveToDb = saveToDb;
    }

}