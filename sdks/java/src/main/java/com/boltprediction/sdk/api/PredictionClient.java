package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** Prediction API 客户端 */
public class PredictionClient extends BaseAPIClient {

    public PredictionClient(ApiClientConfig config) {
        super(config);
    }

    /** 螺栓状态预测 */
    public BoltPredictionResponse predictBoltApiV1PredictBoltPost(
            BoltPredictionRequest body,
            String validationMode,
            Object version,
            Object shadowVersion
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (validationMode != null) params.put("validation_mode", String.valueOf(validationMode));
        if (version != null) params.put("version", String.valueOf(version));
        if (shadowVersion != null) params.put("shadow_version", String.valueOf(shadowVersion));

        return _request(
                "POST",
                "/api/v1/api/v1/predict/bolt",
                params,
                body,
                BoltPredictionResponse.class
        );
    }

    /** 螺栓集成学习预测调试 */
    public BoltEnsemblePredictionResponse predictBoltEnsembleApiV1PredictBoltEnsemblePost(
            BoltEnsemblePredictionRequest body,
            String validationMode
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (validationMode != null) params.put("validation_mode", String.valueOf(validationMode));

        return _request(
                "POST",
                "/api/v1/api/v1/predict/bolt/ensemble",
                params,
                body,
                BoltEnsemblePredictionResponse.class
        );
    }

    /** 螺栓多变量耦合预测（温度/振动/扭矩等联合输入） */
    public BoltMultivariatePredictionResponse predictBoltMultivariateApiV1PredictBoltMultivariatePost(
            BoltMultivariatePredictionRequest body,
            Boolean saveToDb
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (saveToDb != null) params.put("save_to_db", String.valueOf(saveToDb));

        return _request(
                "POST",
                "/api/v1/api/v1/predict/bolt/multivariate",
                params,
                body,
                BoltMultivariatePredictionResponse.class
        );
    }

    /** 法兰面状态预测 */
    public FlangePredictionResponse predictFlangeApiV1PredictFlangePost(
            FlangePredictionRequest body,
            String validationMode,
            Object version,
            Object shadowVersion
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (validationMode != null) params.put("validation_mode", String.valueOf(validationMode));
        if (version != null) params.put("version", String.valueOf(version));
        if (shadowVersion != null) params.put("shadow_version", String.valueOf(shadowVersion));

        return _request(
                "POST",
                "/api/v1/api/v1/predict/flange",
                params,
                body,
                FlangePredictionResponse.class
        );
    }

    /** 月度趋势预测 */
    public MonthlyForecastResponse forecastMonthlyApiV1ForecastMonthlyPost(
            MonthlyForecastRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/forecast/monthly",
                params,
                body,
                MonthlyForecastResponse.class
        );
    }

    /** 批量预测 */
    public Map<String, Object> batchPredictApiV1PredictBatchPost(
            String nodeType
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (nodeType != null) params.put("node_type", String.valueOf(nodeType));

        return _request(
                "POST",
                "/api/v1/api/v1/predict/batch",
                params,
                null,
                Map.class
        );
    }

}