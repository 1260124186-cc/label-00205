package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 处理告警请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AlertHandleRequest {

    @JsonProperty("action")
    private String action;

    @JsonProperty("handler_id")
    private Object handlerId;

    @JsonProperty("handler_name")
    private Object handlerName;

    @JsonProperty("handle_note")
    private Object handleNote;

    @JsonProperty("silence_minutes")
    private Object silenceMinutes;

    public String getAction() {
        return action;
    }

    public void setAction(String action) {
        this.action = action;
    }

    public Object getHandlerId() {
        return handlerId;
    }

    public void setHandlerId(Object handlerId) {
        this.handlerId = handlerId;
    }

    public Object getHandlerName() {
        return handlerName;
    }

    public void setHandlerName(Object handlerName) {
        this.handlerName = handlerName;
    }

    public Object getHandleNote() {
        return handleNote;
    }

    public void setHandleNote(Object handleNote) {
        this.handleNote = handleNote;
    }

    public Object getSilenceMinutes() {
        return silenceMinutes;
    }

    public void setSilenceMinutes(Object silenceMinutes) {
        this.silenceMinutes = silenceMinutes;
    }

}