package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 训练状态响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TrainingStatusResponse {

    @JsonProperty("is_training")
    private Boolean isTraining;

    @JsonProperty("current_session")
    private Object currentSession;

    @JsonProperty("recent_sessions")
    private List<TrainingSessionSchema> recentSessions;

    public Boolean getIsTraining() {
        return isTraining;
    }

    public void setIsTraining(Boolean isTraining) {
        this.isTraining = isTraining;
    }

    public Object getCurrentSession() {
        return currentSession;
    }

    public void setCurrentSession(Object currentSession) {
        this.currentSession = currentSession;
    }

    public List<TrainingSessionSchema> getRecentSessions() {
        return recentSessions;
    }

    public void setRecentSessions(List<TrainingSessionSchema> recentSessions) {
        this.recentSessions = recentSessions;
    }

}