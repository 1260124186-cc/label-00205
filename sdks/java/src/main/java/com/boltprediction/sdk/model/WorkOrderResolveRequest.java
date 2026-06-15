package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 解决工单请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class WorkOrderResolveRequest {

    @JsonProperty("resolve_note")
    private String resolveNote;

    @JsonProperty("resolver_id")
    private Object resolverId;

    @JsonProperty("resolver_name")
    private Object resolverName;

    public String getResolveNote() {
        return resolveNote;
    }

    public void setResolveNote(String resolveNote) {
        this.resolveNote = resolveNote;
    }

    public Object getResolverId() {
        return resolverId;
    }

    public void setResolverId(Object resolverId) {
        this.resolverId = resolverId;
    }

    public Object getResolverName() {
        return resolverName;
    }

    public void setResolverName(Object resolverName) {
        this.resolverName = resolverName;
    }

}