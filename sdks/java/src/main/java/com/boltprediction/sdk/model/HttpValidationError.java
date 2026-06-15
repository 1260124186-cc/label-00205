package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** HTTPValidationError */
@JsonIgnoreProperties(ignoreUnknown = true)
public class HttpValidationError {

    @JsonProperty("detail")
    private List<ValidationError> detail;

    public List<ValidationError> getDetail() {
        return detail;
    }

    public void setDetail(List<ValidationError> detail) {
        this.detail = detail;
    }

}