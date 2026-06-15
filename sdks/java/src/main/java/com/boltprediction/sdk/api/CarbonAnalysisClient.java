package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** CarbonAnalysis API 客户端 */
public class CarbonAnalysisClient extends BaseAPIClient {

    public CarbonAnalysisClient(ApiClientConfig config) {
        super(config);
    }

    /** 装置级月度碳排风险贡献排行 */
    public CarbonMonthlyRankingResponse getCarbonMonthlyRankingApiV1CarbonRankingMonthlyPost(
            CarbonMonthlyRankingRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/carbon/ranking/monthly",
                params,
                body,
                CarbonMonthlyRankingResponse.class
        );
    }

    /** HI rollup 与碳排并列展示 */
    public HiCarbonDualViewResponse getHiCarbonDualViewApiV1CarbonHiDualViewPost(
            HiCarbonDualViewRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/carbon/hi-dual-view",
                params,
                body,
                HiCarbonDualViewResponse.class
        );
    }

    /** 导出 ESG 报表片段 */
    public EsgReportFragmentResponse exportEsgReportFragmentApiV1CarbonEsgExportPost(
            EsgReportExportRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/carbon/esg/export",
                params,
                body,
                EsgReportFragmentResponse.class
        );
    }

    /** 获取碳排模型系数配置 */
    public CarbonModelConfigResponse getCarbonModelConfigApiV1CarbonConfigGet(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/carbon/config",
                params,
                null,
                CarbonModelConfigResponse.class
        );
    }

    /** 更新碳排模型系数配置 */
    public CarbonModelConfigResponse updateCarbonModelConfigApiV1CarbonConfigPost(
            CarbonModelConfigUpdateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/carbon/config",
                params,
                body,
                CarbonModelConfigResponse.class
        );
    }

}