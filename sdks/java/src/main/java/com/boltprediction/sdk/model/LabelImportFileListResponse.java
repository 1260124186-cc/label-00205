package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 可导入文件列表响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class LabelImportFileListResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("items")
    private List<LabelImportFileItemSchema> items;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<LabelImportFileItemSchema> getItems() {
        return items;
    }

    public void setItems(List<LabelImportFileItemSchema> items) {
        this.items = items;
    }

}