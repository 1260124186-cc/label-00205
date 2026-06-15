package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 创建处置记录请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class DisposalRecordCreate {

    @JsonProperty("work_order_id")
    private Integer workOrderId;

    @JsonProperty("disposal_type")
    private String disposalType;

    @JsonProperty("disposal_content")
    private String disposalContent;

    @JsonProperty("disposal_time")
    private Object disposalTime;

    @JsonProperty("operator_id")
    private Object operatorId;

    @JsonProperty("operator_name")
    private Object operatorName;

    @JsonProperty("before_value")
    private Object beforeValue;

    @JsonProperty("after_value")
    private Object afterValue;

    @JsonProperty("materials_used")
    private Object materialsUsed;

    @JsonProperty("photos")
    private Object photos;

    @JsonProperty("notes")
    private Object notes;

    @JsonProperty("extra_info")
    private Object extraInfo;

    public Integer getWorkOrderId() {
        return workOrderId;
    }

    public void setWorkOrderId(Integer workOrderId) {
        this.workOrderId = workOrderId;
    }

    public String getDisposalType() {
        return disposalType;
    }

    public void setDisposalType(String disposalType) {
        this.disposalType = disposalType;
    }

    public String getDisposalContent() {
        return disposalContent;
    }

    public void setDisposalContent(String disposalContent) {
        this.disposalContent = disposalContent;
    }

    public Object getDisposalTime() {
        return disposalTime;
    }

    public void setDisposalTime(Object disposalTime) {
        this.disposalTime = disposalTime;
    }

    public Object getOperatorId() {
        return operatorId;
    }

    public void setOperatorId(Object operatorId) {
        this.operatorId = operatorId;
    }

    public Object getOperatorName() {
        return operatorName;
    }

    public void setOperatorName(Object operatorName) {
        this.operatorName = operatorName;
    }

    public Object getBeforeValue() {
        return beforeValue;
    }

    public void setBeforeValue(Object beforeValue) {
        this.beforeValue = beforeValue;
    }

    public Object getAfterValue() {
        return afterValue;
    }

    public void setAfterValue(Object afterValue) {
        this.afterValue = afterValue;
    }

    public Object getMaterialsUsed() {
        return materialsUsed;
    }

    public void setMaterialsUsed(Object materialsUsed) {
        this.materialsUsed = materialsUsed;
    }

    public Object getPhotos() {
        return photos;
    }

    public void setPhotos(Object photos) {
        this.photos = photos;
    }

    public Object getNotes() {
        return notes;
    }

    public void setNotes(Object notes) {
        this.notes = notes;
    }

    public Object getExtraInfo() {
        return extraInfo;
    }

    public void setExtraInfo(Object extraInfo) {
        this.extraInfo = extraInfo;
    }

}