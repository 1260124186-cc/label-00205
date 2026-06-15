package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** RiskAssessment API 客户端 */
public class RiskAssessmentClient extends BaseAPIClient {

    public RiskAssessmentClient(ApiClientConfig config) {
        super(config);
    }

    /** 风险评估 */
    public RiskAssessmentResponse assessRiskApiV1RiskAssessPost(
            RiskAssessmentRequest body,
            String validationMode
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (validationMode != null) params.put("validation_mode", String.valueOf(validationMode));

        return _request(
                "POST",
                "/api/v1/api/v1/risk/assess",
                params,
                body,
                RiskAssessmentResponse.class
        );
    }

    /** 风险评估可解释性分析 */
    public RiskAssessExplainResponse assessRiskExplainApiV1RiskAssessExplainPost(
            RiskAssessExplainRequest body,
            String validationMode
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (validationMode != null) params.put("validation_mode", String.valueOf(validationMode));

        return _request(
                "POST",
                "/api/v1/api/v1/risk/assess/explain",
                params,
                body,
                RiskAssessExplainResponse.class
        );
    }

    /** 更新节点级风险校准配置 */
    public RiskCalibrationResponse updateRiskCalibrationApiV1RiskCalibrationPost(
            RiskCalibrationUpdateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/risk/calibration",
                params,
                body,
                RiskCalibrationResponse.class
        );
    }

    /** 查询节点级风险校准配置 */
    public RiskCalibrationResponse getRiskCalibrationApiV1RiskCalibrationGet(
            String nodeType,
            String nodeId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (nodeType != null) params.put("node_type", String.valueOf(nodeType));
        if (nodeId != null) params.put("node_id", String.valueOf(nodeId));

        return _request(
                "GET",
                "/api/v1/api/v1/risk/calibration",
                params,
                null,
                RiskCalibrationResponse.class
        );
    }

}