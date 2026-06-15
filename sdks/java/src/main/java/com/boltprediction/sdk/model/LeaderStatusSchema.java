package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** Leader选举状态 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class LeaderStatusSchema {

    @JsonProperty("leader_key")
    private String leaderKey;

    @JsonProperty("leader_id")
    private String leaderId;

    @JsonProperty("lease_expire_time")
    private OffsetDateTime leaseExpireTime;

    @JsonProperty("last_heartbeat")
    private OffsetDateTime lastHeartbeat;

    @JsonProperty("version")
    private Integer version;

    @JsonProperty("is_expired")
    private Boolean isExpired;

    @JsonProperty("is_current_instance")
    private Boolean isCurrentInstance;

    public String getLeaderKey() {
        return leaderKey;
    }

    public void setLeaderKey(String leaderKey) {
        this.leaderKey = leaderKey;
    }

    public String getLeaderId() {
        return leaderId;
    }

    public void setLeaderId(String leaderId) {
        this.leaderId = leaderId;
    }

    public OffsetDateTime getLeaseExpireTime() {
        return leaseExpireTime;
    }

    public void setLeaseExpireTime(OffsetDateTime leaseExpireTime) {
        this.leaseExpireTime = leaseExpireTime;
    }

    public OffsetDateTime getLastHeartbeat() {
        return lastHeartbeat;
    }

    public void setLastHeartbeat(OffsetDateTime lastHeartbeat) {
        this.lastHeartbeat = lastHeartbeat;
    }

    public Integer getVersion() {
        return version;
    }

    public void setVersion(Integer version) {
        this.version = version;
    }

    public Boolean getIsExpired() {
        return isExpired;
    }

    public void setIsExpired(Boolean isExpired) {
        this.isExpired = isExpired;
    }

    public Boolean getIsCurrentInstance() {
        return isCurrentInstance;
    }

    public void setIsCurrentInstance(Boolean isCurrentInstance) {
        this.isCurrentInstance = isCurrentInstance;
    }

}