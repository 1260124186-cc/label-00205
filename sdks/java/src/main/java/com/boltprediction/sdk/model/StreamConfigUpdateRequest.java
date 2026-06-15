package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 流式预测配置更新请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class StreamConfigUpdateRequest {

    @JsonProperty("window_size")
    private Object windowSize;

    @JsonProperty("max_concurrent_streams")
    private Object maxConcurrentStreams;

    @JsonProperty("rate_per_stream")
    private Object ratePerStream;

    public Object getWindowSize() {
        return windowSize;
    }

    public void setWindowSize(Object windowSize) {
        this.windowSize = windowSize;
    }

    public Object getMaxConcurrentStreams() {
        return maxConcurrentStreams;
    }

    public void setMaxConcurrentStreams(Object maxConcurrentStreams) {
        this.maxConcurrentStreams = maxConcurrentStreams;
    }

    public Object getRatePerStream() {
        return ratePerStream;
    }

    public void setRatePerStream(Object ratePerStream) {
        this.ratePerStream = ratePerStream;
    }

}