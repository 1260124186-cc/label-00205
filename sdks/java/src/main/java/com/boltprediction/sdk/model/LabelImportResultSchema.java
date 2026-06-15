package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 标注导入结果 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class LabelImportResultSchema {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("imported")
    private Integer imported;

    @JsonProperty("skipped")
    private Integer skipped;

    @JsonProperty("duplicates")
    private Integer duplicates;

    @JsonProperty("errors")
    private Integer errors;

    @JsonProperty("error_details")
    private Object errorDetails;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public Integer getImported() {
        return imported;
    }

    public void setImported(Integer imported) {
        this.imported = imported;
    }

    public Integer getSkipped() {
        return skipped;
    }

    public void setSkipped(Integer skipped) {
        this.skipped = skipped;
    }

    public Integer getDuplicates() {
        return duplicates;
    }

    public void setDuplicates(Integer duplicates) {
        this.duplicates = duplicates;
    }

    public Integer getErrors() {
        return errors;
    }

    public void setErrors(Integer errors) {
        this.errors = errors;
    }

    public Object getErrorDetails() {
        return errorDetails;
    }

    public void setErrorDetails(Object errorDetails) {
        this.errorDetails = errorDetails;
    }

}