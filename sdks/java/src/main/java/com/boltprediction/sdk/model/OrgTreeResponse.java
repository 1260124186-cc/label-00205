package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** OrgTreeResponse */
@JsonIgnoreProperties(ignoreUnknown = true)
public class OrgTreeResponse {

    @JsonProperty("tenant_id")
    private Integer tenantId;

    @JsonProperty("nodes")
    private List<OrgNodeResponse> nodes;

    public Integer getTenantId() {
        return tenantId;
    }

    public void setTenantId(Integer tenantId) {
        this.tenantId = tenantId;
    }

    public List<OrgNodeResponse> getNodes() {
        return nodes;
    }

    public void setNodes(List<OrgNodeResponse> nodes) {
        this.nodes = nodes;
    }

}