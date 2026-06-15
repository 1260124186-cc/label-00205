package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 案例审核请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class CaseReviewRequest {

    @JsonProperty("review_result")
    private String reviewResult;

    @JsonProperty("review_comment")
    private Object reviewComment;

    @JsonProperty("reviewer_id")
    private Object reviewerId;

    @JsonProperty("reviewer_name")
    private Object reviewerName;

    @JsonProperty("review_level")
    private Integer reviewLevel;

    public String getReviewResult() {
        return reviewResult;
    }

    public void setReviewResult(String reviewResult) {
        this.reviewResult = reviewResult;
    }

    public Object getReviewComment() {
        return reviewComment;
    }

    public void setReviewComment(Object reviewComment) {
        this.reviewComment = reviewComment;
    }

    public Object getReviewerId() {
        return reviewerId;
    }

    public void setReviewerId(Object reviewerId) {
        this.reviewerId = reviewerId;
    }

    public Object getReviewerName() {
        return reviewerName;
    }

    public void setReviewerName(Object reviewerName) {
        this.reviewerName = reviewerName;
    }

    public Integer getReviewLevel() {
        return reviewLevel;
    }

    public void setReviewLevel(Integer reviewLevel) {
        this.reviewLevel = reviewLevel;
    }

}