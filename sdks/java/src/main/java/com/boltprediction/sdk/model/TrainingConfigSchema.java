package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 完整训练配置 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TrainingConfigSchema {

    @JsonProperty("epochs")
    private Object epochs;

    @JsonProperty("batch_size")
    private Object batchSize;

    @JsonProperty("learning_rate")
    private Object learningRate;

    @JsonProperty("validation_split")
    private Object validationSplit;

    @JsonProperty("early_stopping")
    private Object earlyStopping;

    @JsonProperty("lr_scheduler")
    private Object lrScheduler;

    @JsonProperty("class_imbalance")
    private Object classImbalance;

    @JsonProperty("incremental")
    private Object incremental;

    @JsonProperty("focal_loss")
    private Object focalLoss;

    public Object getEpochs() {
        return epochs;
    }

    public void setEpochs(Object epochs) {
        this.epochs = epochs;
    }

    public Object getBatchSize() {
        return batchSize;
    }

    public void setBatchSize(Object batchSize) {
        this.batchSize = batchSize;
    }

    public Object getLearningRate() {
        return learningRate;
    }

    public void setLearningRate(Object learningRate) {
        this.learningRate = learningRate;
    }

    public Object getValidationSplit() {
        return validationSplit;
    }

    public void setValidationSplit(Object validationSplit) {
        this.validationSplit = validationSplit;
    }

    public Object getEarlyStopping() {
        return earlyStopping;
    }

    public void setEarlyStopping(Object earlyStopping) {
        this.earlyStopping = earlyStopping;
    }

    public Object getLrScheduler() {
        return lrScheduler;
    }

    public void setLrScheduler(Object lrScheduler) {
        this.lrScheduler = lrScheduler;
    }

    public Object getClassImbalance() {
        return classImbalance;
    }

    public void setClassImbalance(Object classImbalance) {
        this.classImbalance = classImbalance;
    }

    public Object getIncremental() {
        return incremental;
    }

    public void setIncremental(Object incremental) {
        this.incremental = incremental;
    }

    public Object getFocalLoss() {
        return focalLoss;
    }

    public void setFocalLoss(Object focalLoss) {
        this.focalLoss = focalLoss;
    }

}