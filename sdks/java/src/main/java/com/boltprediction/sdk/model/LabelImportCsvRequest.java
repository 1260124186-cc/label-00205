package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** CSV标注导入请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class LabelImportCsvRequest {

    @JsonProperty("csv_path")
    private String csvPath;

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("label_column")
    private Object labelColumn;

    @JsonProperty("id_column")
    private Object idColumn;

    @JsonProperty("data_column")
    private Object dataColumn;

    @JsonProperty("timestamp_column")
    private Object timestampColumn;

    @JsonProperty("labeler_name")
    private Object labelerName;

    @JsonProperty("auto_approve")
    private Boolean autoApprove;

    @JsonProperty("skip_errors")
    private Boolean skipErrors;

    public String getCsvPath() {
        return csvPath;
    }

    public void setCsvPath(String csvPath) {
        this.csvPath = csvPath;
    }

    public String getNodeType() {
        return nodeType;
    }

    public void setNodeType(String nodeType) {
        this.nodeType = nodeType;
    }

    public Object getLabelColumn() {
        return labelColumn;
    }

    public void setLabelColumn(Object labelColumn) {
        this.labelColumn = labelColumn;
    }

    public Object getIdColumn() {
        return idColumn;
    }

    public void setIdColumn(Object idColumn) {
        this.idColumn = idColumn;
    }

    public Object getDataColumn() {
        return dataColumn;
    }

    public void setDataColumn(Object dataColumn) {
        this.dataColumn = dataColumn;
    }

    public Object getTimestampColumn() {
        return timestampColumn;
    }

    public void setTimestampColumn(Object timestampColumn) {
        this.timestampColumn = timestampColumn;
    }

    public Object getLabelerName() {
        return labelerName;
    }

    public void setLabelerName(Object labelerName) {
        this.labelerName = labelerName;
    }

    public Boolean getAutoApprove() {
        return autoApprove;
    }

    public void setAutoApprove(Boolean autoApprove) {
        this.autoApprove = autoApprove;
    }

    public Boolean getSkipErrors() {
        return skipErrors;
    }

    public void setSkipErrors(Boolean skipErrors) {
        this.skipErrors = skipErrors;
    }

}