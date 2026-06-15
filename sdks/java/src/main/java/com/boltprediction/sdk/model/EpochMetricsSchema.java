package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** Epoch指标 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class EpochMetricsSchema {

    @JsonProperty("epoch")
    private Integer epoch;

    @JsonProperty("train_loss")
    private Double trainLoss;

    @JsonProperty("val_loss")
    private Object valLoss;

    @JsonProperty("train_acc")
    private Object trainAcc;

    @JsonProperty("val_acc")
    private Object valAcc;

    @JsonProperty("learning_rate")
    private Object learningRate;

    @JsonProperty("duration_seconds")
    private Double durationSeconds;

    @JsonProperty("timestamp")
    private String timestamp;

    public Integer getEpoch() {
        return epoch;
    }

    public void setEpoch(Integer epoch) {
        this.epoch = epoch;
    }

    public Double getTrainLoss() {
        return trainLoss;
    }

    public void setTrainLoss(Double trainLoss) {
        this.trainLoss = trainLoss;
    }

    public Object getValLoss() {
        return valLoss;
    }

    public void setValLoss(Object valLoss) {
        this.valLoss = valLoss;
    }

    public Object getTrainAcc() {
        return trainAcc;
    }

    public void setTrainAcc(Object trainAcc) {
        this.trainAcc = trainAcc;
    }

    public Object getValAcc() {
        return valAcc;
    }

    public void setValAcc(Object valAcc) {
        this.valAcc = valAcc;
    }

    public Object getLearningRate() {
        return learningRate;
    }

    public void setLearningRate(Object learningRate) {
        this.learningRate = learningRate;
    }

    public Double getDurationSeconds() {
        return durationSeconds;
    }

    public void setDurationSeconds(Double durationSeconds) {
        this.durationSeconds = durationSeconds;
    }

    public String getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(String timestamp) {
        this.timestamp = timestamp;
    }

}