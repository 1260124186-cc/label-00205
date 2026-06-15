package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** KnowledgeBase API 客户端 */
public class KnowledgeBaseClient extends BaseAPIClient {

    public KnowledgeBaseClient(ApiClientConfig config) {
        super(config);
    }

    /** 创建案例 */
    public Map<String, Object> createKnowledgeCaseApiV1KnowledgeCasesPost(
            KnowledgeCaseCreateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/knowledge/cases",
                params,
                body,
                Map.class
        );
    }

    /** 查询案例列表 */
    public KnowledgeCaseListResponse listKnowledgeCasesApiV1KnowledgeCasesGet(
            Object status,
            Object nodeType,
            Object faultType,
            Object faultLevel,
            Object tenantId,
            Object keyword,
            Integer limit,
            Integer offset
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (status != null) params.put("status", String.valueOf(status));
        if (nodeType != null) params.put("node_type", String.valueOf(nodeType));
        if (faultType != null) params.put("fault_type", String.valueOf(faultType));
        if (faultLevel != null) params.put("fault_level", String.valueOf(faultLevel));
        if (tenantId != null) params.put("tenant_id", String.valueOf(tenantId));
        if (keyword != null) params.put("keyword", String.valueOf(keyword));
        if (limit != null) params.put("limit", String.valueOf(limit));
        if (offset != null) params.put("offset", String.valueOf(offset));

        return _request(
                "GET",
                "/api/v1/api/v1/knowledge/cases",
                params,
                null,
                KnowledgeCaseListResponse.class
        );
    }

    /** 获取案例详情 */
    public Map<String, Object> getKnowledgeCaseApiV1KnowledgeCasesCaseIdGet(
            Integer caseId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/knowledge/cases/" + caseId + "",
                params,
                null,
                Map.class
        );
    }

    /** 更新案例 */
    public Map<String, Object> updateKnowledgeCaseApiV1KnowledgeCasesCaseIdPut(
            Integer caseId,
            KnowledgeCaseUpdateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "PUT",
                "/api/v1/api/v1/knowledge/cases/" + caseId + "",
                params,
                body,
                Map.class
        );
    }

    /** 删除案例 */
    public Map<String, Object> deleteKnowledgeCaseApiV1KnowledgeCasesCaseIdDelete(
            Integer caseId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "DELETE",
                "/api/v1/api/v1/knowledge/cases/" + caseId + "",
                params,
                null,
                Map.class
        );
    }

    /** 提交审核 */
    public Map<String, Object> submitCaseForReviewApiV1KnowledgeCasesCaseIdSubmitReviewPost(
            Integer caseId,
            Object operatorId,
            Object operatorName
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (operatorId != null) params.put("operator_id", String.valueOf(operatorId));
        if (operatorName != null) params.put("operator_name", String.valueOf(operatorName));

        return _request(
                "POST",
                "/api/v1/api/v1/knowledge/cases/" + caseId + "/submit-review",
                params,
                null,
                Map.class
        );
    }

    /** 审核案例 */
    public Map<String, Object> reviewKnowledgeCaseApiV1KnowledgeCasesCaseIdReviewPost(
            Integer caseId,
            CaseReviewRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/knowledge/cases/" + caseId + "/review",
                params,
                body,
                Map.class
        );
    }

    /** 获取审核记录 */
    public Map<String, Object> listCaseReviewsApiV1KnowledgeCasesCaseIdReviewsGet(
            Integer caseId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/knowledge/cases/" + caseId + "/reviews",
                params,
                null,
                Map.class
        );
    }

    /** 获取版本历史 */
    public Map<String, Object> listCaseVersionsApiV1KnowledgeCasesCaseIdVersionsGet(
            Integer caseId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/knowledge/cases/" + caseId + "/versions",
                params,
                null,
                Map.class
        );
    }

    /** 获取指定版本 */
    public Map<String, Object> getCaseVersionApiV1KnowledgeCasesCaseIdVersionsVersionGet(
            Integer caseId,
            Integer version
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/knowledge/cases/" + caseId + "/versions/" + version + "",
                params,
                null,
                Map.class
        );
    }

    /** 对比版本差异 */
    public Map<String, Object> compareCaseVersionsApiV1KnowledgeCasesCaseIdVersionsCompareGet(
            Integer caseId,
            Integer versionFrom,
            Integer versionTo
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (versionFrom != null) params.put("version_from", String.valueOf(versionFrom));
        if (versionTo != null) params.put("version_to", String.valueOf(versionTo));

        return _request(
                "GET",
                "/api/v1/api/v1/knowledge/cases/" + caseId + "/versions/compare",
                params,
                null,
                Map.class
        );
    }

    /** 回退到指定版本 */
    public Map<String, Object> revertCaseToVersionApiV1KnowledgeCasesCaseIdVersionsVersionRevertPost(
            Integer caseId,
            Integer version,
            Object operatorId,
            Object operatorName
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (operatorId != null) params.put("operator_id", String.valueOf(operatorId));
        if (operatorName != null) params.put("operator_name", String.valueOf(operatorName));

        return _request(
                "POST",
                "/api/v1/api/v1/knowledge/cases/" + caseId + "/versions/" + version + "/revert",
                params,
                null,
                Map.class
        );
    }

    /** 检索相似案例 (Top-K) */
    public Map<String, Object> searchSimilarCasesApiV1KnowledgeCasesSearchSimilarPost(
            CaseSimilaritySearchRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/knowledge/cases/search/similar",
                params,
                body,
                Map.class
        );
    }

    /** 获取案例推荐 (推荐措施 + RAG上下文) */
    public Map<String, Object> getCaseRecommendationsApiV1KnowledgeCasesRecommendPost(
            CaseSimilaritySearchRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/knowledge/cases/recommend",
                params,
                body,
                Map.class
        );
    }

    /** 获取知识库统计 */
    public Map<String, Object> getKnowledgeStatisticsApiV1KnowledgeStatisticsGet(
            Object tenantId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (tenantId != null) params.put("tenant_id", String.valueOf(tenantId));

        return _request(
                "GET",
                "/api/v1/api/v1/knowledge/statistics",
                params,
                null,
                Map.class
        );
    }

}