package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 工单统计响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class WorkOrderStatsResponse {

    @JsonProperty("total_work_orders")
    private Integer totalWorkOrders;

    @JsonProperty("closed_work_orders")
    private Integer closedWorkOrders;

    @JsonProperty("open_work_orders")
    private Integer openWorkOrders;

    @JsonProperty("in_progress_work_orders")
    private Integer inProgressWorkOrders;

    @JsonProperty("mttr_hours")
    private Object mttrHours;

    @JsonProperty("mttr_minutes")
    private Object mttrMinutes;

    @JsonProperty("false_positive_rate")
    private Object falsePositiveRate;

    @JsonProperty("false_positive_count")
    private Integer falsePositiveCount;

    @JsonProperty("recurrence_rate")
    private Object recurrenceRate;

    @JsonProperty("recurrence_count")
    private Integer recurrenceCount;

    @JsonProperty("avg_resolve_hours")
    private Object avgResolveHours;

    @JsonProperty("on_time_completion_rate")
    private Object onTimeCompletionRate;

    @JsonProperty("priority_distribution")
    private Object priorityDistribution;

    @JsonProperty("status_distribution")
    private Object statusDistribution;

    @JsonProperty("time_range")
    private Object timeRange;

    public Integer getTotalWorkOrders() {
        return totalWorkOrders;
    }

    public void setTotalWorkOrders(Integer totalWorkOrders) {
        this.totalWorkOrders = totalWorkOrders;
    }

    public Integer getClosedWorkOrders() {
        return closedWorkOrders;
    }

    public void setClosedWorkOrders(Integer closedWorkOrders) {
        this.closedWorkOrders = closedWorkOrders;
    }

    public Integer getOpenWorkOrders() {
        return openWorkOrders;
    }

    public void setOpenWorkOrders(Integer openWorkOrders) {
        this.openWorkOrders = openWorkOrders;
    }

    public Integer getInProgressWorkOrders() {
        return inProgressWorkOrders;
    }

    public void setInProgressWorkOrders(Integer inProgressWorkOrders) {
        this.inProgressWorkOrders = inProgressWorkOrders;
    }

    public Object getMttrHours() {
        return mttrHours;
    }

    public void setMttrHours(Object mttrHours) {
        this.mttrHours = mttrHours;
    }

    public Object getMttrMinutes() {
        return mttrMinutes;
    }

    public void setMttrMinutes(Object mttrMinutes) {
        this.mttrMinutes = mttrMinutes;
    }

    public Object getFalsePositiveRate() {
        return falsePositiveRate;
    }

    public void setFalsePositiveRate(Object falsePositiveRate) {
        this.falsePositiveRate = falsePositiveRate;
    }

    public Integer getFalsePositiveCount() {
        return falsePositiveCount;
    }

    public void setFalsePositiveCount(Integer falsePositiveCount) {
        this.falsePositiveCount = falsePositiveCount;
    }

    public Object getRecurrenceRate() {
        return recurrenceRate;
    }

    public void setRecurrenceRate(Object recurrenceRate) {
        this.recurrenceRate = recurrenceRate;
    }

    public Integer getRecurrenceCount() {
        return recurrenceCount;
    }

    public void setRecurrenceCount(Integer recurrenceCount) {
        this.recurrenceCount = recurrenceCount;
    }

    public Object getAvgResolveHours() {
        return avgResolveHours;
    }

    public void setAvgResolveHours(Object avgResolveHours) {
        this.avgResolveHours = avgResolveHours;
    }

    public Object getOnTimeCompletionRate() {
        return onTimeCompletionRate;
    }

    public void setOnTimeCompletionRate(Object onTimeCompletionRate) {
        this.onTimeCompletionRate = onTimeCompletionRate;
    }

    public Object getPriorityDistribution() {
        return priorityDistribution;
    }

    public void setPriorityDistribution(Object priorityDistribution) {
        this.priorityDistribution = priorityDistribution;
    }

    public Object getStatusDistribution() {
        return statusDistribution;
    }

    public void setStatusDistribution(Object statusDistribution) {
        this.statusDistribution = statusDistribution;
    }

    public Object getTimeRange() {
        return timeRange;
    }

    public void setTimeRange(Object timeRange) {
        this.timeRange = timeRange;
    }

}