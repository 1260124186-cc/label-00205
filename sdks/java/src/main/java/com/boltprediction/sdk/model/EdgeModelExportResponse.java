package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** EdgeModelExportResponse */
@JsonIgnoreProperties(ignoreUnknown = true)
public class EdgeModelExportResponse {

    @JsonProperty("model_type")
    private String modelType;

    @JsonProperty("node_id")
    private Object nodeId;

    @JsonProperty("version")
    private String version;

    @JsonProperty("export_format")
    private String exportFormat;

    @JsonProperty("package_url")
    private String packageUrl;

    @JsonProperty("file_hash")
    private String fileHash;

    @JsonProperty("file_size")
    private Integer fileSize;

    @JsonProperty("includes_preprocessing")
    private Boolean includesPreprocessing;

    @JsonProperty("includes_signature")
    private Boolean includesSignature;

    @JsonProperty("exported_at")
    private String exportedAt;

    public String getModelType() {
        return modelType;
    }

    public void setModelType(String modelType) {
        this.modelType = modelType;
    }

    public Object getNodeId() {
        return nodeId;
    }

    public void setNodeId(Object nodeId) {
        this.nodeId = nodeId;
    }

    public String getVersion() {
        return version;
    }

    public void setVersion(String version) {
        this.version = version;
    }

    public String getExportFormat() {
        return exportFormat;
    }

    public void setExportFormat(String exportFormat) {
        this.exportFormat = exportFormat;
    }

    public String getPackageUrl() {
        return packageUrl;
    }

    public void setPackageUrl(String packageUrl) {
        this.packageUrl = packageUrl;
    }

    public String getFileHash() {
        return fileHash;
    }

    public void setFileHash(String fileHash) {
        this.fileHash = fileHash;
    }

    public Integer getFileSize() {
        return fileSize;
    }

    public void setFileSize(Integer fileSize) {
        this.fileSize = fileSize;
    }

    public Boolean getIncludesPreprocessing() {
        return includesPreprocessing;
    }

    public void setIncludesPreprocessing(Boolean includesPreprocessing) {
        this.includesPreprocessing = includesPreprocessing;
    }

    public Boolean getIncludesSignature() {
        return includesSignature;
    }

    public void setIncludesSignature(Boolean includesSignature) {
        this.includesSignature = includesSignature;
    }

    public String getExportedAt() {
        return exportedAt;
    }

    public void setExportedAt(String exportedAt) {
        this.exportedAt = exportedAt;
    }

}