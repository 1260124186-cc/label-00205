package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** ValidationError */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ValidationError {

    @JsonProperty("loc")
    private List<Object> loc;

    @JsonProperty("msg")
    private String msg;

    @JsonProperty("type")
    private String type;

    @JsonProperty("input")
    private Object input;

    @JsonProperty("ctx")
    private Map<String, Object> ctx;

    public List<Object> getLoc() {
        return loc;
    }

    public void setLoc(List<Object> loc) {
        this.loc = loc;
    }

    public String getMsg() {
        return msg;
    }

    public void setMsg(String msg) {
        this.msg = msg;
    }

    public String getType() {
        return type;
    }

    public void setType(String type) {
        this.type = type;
    }

    public Object getInput() {
        return input;
    }

    public void setInput(Object input) {
        this.input = input;
    }

    public Map<String, Object> getCtx() {
        return ctx;
    }

    public void setCtx(Map<String, Object> ctx) {
        this.ctx = ctx;
    }

}