package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 可导入文件列表项 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class LabelImportFileItemSchema {

    @JsonProperty("filename")
    private String filename;

    @JsonProperty("path")
    private String path;

    @JsonProperty("size_bytes")
    private Integer sizeBytes;

    @JsonProperty("modified_time")
    private Object modifiedTime;

    public String getFilename() {
        return filename;
    }

    public void setFilename(String filename) {
        this.filename = filename;
    }

    public String getPath() {
        return path;
    }

    public void setPath(String path) {
        this.path = path;
    }

    public Integer getSizeBytes() {
        return sizeBytes;
    }

    public void setSizeBytes(Integer sizeBytes) {
        this.sizeBytes = sizeBytes;
    }

    public Object getModifiedTime() {
        return modifiedTime;
    }

    public void setModifiedTime(Object modifiedTime) {
        this.modifiedTime = modifiedTime;
    }

}