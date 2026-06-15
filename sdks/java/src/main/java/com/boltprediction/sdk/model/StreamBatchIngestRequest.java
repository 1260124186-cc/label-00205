package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 批量流式数据注入请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class StreamBatchIngestRequest {

    @JsonProperty("messages")
    private List<Map<String, Object>> messages;

    public List<Map<String, Object>> getMessages() {
        return messages;
    }

    public void setMessages(List<Map<String, Object>> messages) {
        this.messages = messages;
    }

}