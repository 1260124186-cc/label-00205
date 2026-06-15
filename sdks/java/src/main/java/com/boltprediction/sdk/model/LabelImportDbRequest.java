package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 数据库标注导入请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class LabelImportDbRequest {

    @JsonProperty("source_table")
    private String sourceTable;

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("id_field")
    private String idField;

    @JsonProperty("label_field")
    private String labelField;

    @JsonProperty("data_field")
    private Object dataField;

    @JsonProperty("timestamp_field")
    private Object timestampField;

    @JsonProperty("where_clause")
    private Object whereClause;

    @JsonProperty("labeler_name")
    private Object labelerName;

    @JsonProperty("auto_approve")
    private Boolean autoApprove;

    public String getSourceTable() {
        return sourceTable;
    }

    public void setSourceTable(String sourceTable) {
        this.sourceTable = sourceTable;
    }

    public String getNodeType() {
        return nodeType;
    }

    public void setNodeType(String nodeType) {
        this.nodeType = nodeType;
    }

    public String getIdField() {
        return idField;
    }

    public void setIdField(String idField) {
        this.idField = idField;
    }

    public String getLabelField() {
        return labelField;
    }

    public void setLabelField(String labelField) {
        this.labelField = labelField;
    }

    public Object getDataField() {
        return dataField;
    }

    public void setDataField(Object dataField) {
        this.dataField = dataField;
    }

    public Object getTimestampField() {
        return timestampField;
    }

    public void setTimestampField(Object timestampField) {
        this.timestampField = timestampField;
    }

    public Object getWhereClause() {
        return whereClause;
    }

    public void setWhereClause(Object whereClause) {
        this.whereClause = whereClause;
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

}