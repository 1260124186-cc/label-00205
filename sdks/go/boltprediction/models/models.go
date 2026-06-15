package models

import "time"

// APIAuditLogListResponse
type ApiAuditLogListResponse struct {
	Total int `json:"total"`
	Items []ApiAuditLogResponse `json:"items,omitempty"`
}
// APIAuditLogResponse
type ApiAuditLogResponse struct {
	Id int `json:"id"`
	KeyId string `json:"key_id,omitempty"`
	KeyName string `json:"key_name,omitempty"`
	Method string `json:"method,omitempty"`
	Path string `json:"path,omitempty"`
	StatusCode int `json:"status_code,omitempty"`
	ClientIp string `json:"client_ip,omitempty"`
	RequestId string `json:"request_id,omitempty"`
	ExtraInfo map[string]interface{} `json:"extra_info,omitempty"`
	CreateTime time.Time `json:"create_time"`
}
// APIKeyCreateRequest
type ApiKeyCreateRequest struct {
	Name string `json:"name"`
	Permissions []string `json:"permissions,omitempty"`
	RateLimit int `json:"rate_limit,omitempty"`
	ExpiresHours interface{} `json:"expires_hours,omitempty"`
}
// APIKeyCreateResponse
type ApiKeyCreateResponse struct {
	Key string `json:"key"`
	KeyId string `json:"key_id"`
	Name string `json:"name"`
	Permissions []string `json:"permissions,omitempty"`
	RateLimit int `json:"rate_limit,omitempty"`
	ExpiresAt interface{} `json:"expires_at,omitempty"`
	CreatedAt string `json:"created_at"`
}
// APIKeyInfoResponse
type ApiKeyInfoResponse struct {
	KeyId string `json:"key_id"`
	KeyPreview string `json:"key_preview"`
	Name string `json:"name"`
	Permissions []string `json:"permissions,omitempty"`
	RateLimit int `json:"rate_limit,omitempty"`
	IsExpired bool `json:"is_expired,omitempty"`
	ExpiresAt interface{} `json:"expires_at,omitempty"`
	CreatedAt interface{} `json:"created_at,omitempty"`
}
// APIKeyListResponse
type ApiKeyListResponse struct {
	Total int `json:"total"`
	Items []ApiKeyInfoResponse `json:"items,omitempty"`
}
// APIKeyRevokeResponse
type ApiKeyRevokeResponse struct {
	KeyId string `json:"key_id"`
	Revoked bool `json:"revoked,omitempty"`
}
// APIKeyRotateResponse
type ApiKeyRotateResponse struct {
	OldKeyId string `json:"old_key_id"`
	NewKey string `json:"new_key"`
	NewKeyId string `json:"new_key_id"`
	OldKeyGraceExpires time.Time `json:"old_key_grace_expires"`
	Permissions []string `json:"permissions,omitempty"`
	RateLimit int `json:"rate_limit,omitempty"`
}
// AlertEventResponse
type AlertEventResponse struct {
	Id int `json:"id"`
	AlertNo string `json:"alert_no"`
	RuleId interface{} `json:"rule_id,omitempty"`
	AlertLevel int `json:"alert_level"`
	OriginalLevel interface{} `json:"original_level,omitempty"`
	NodeType interface{} `json:"node_type,omitempty"`
	NodeId interface{} `json:"node_id,omitempty"`
	Title interface{} `json:"title,omitempty"`
	Content interface{} `json:"content,omitempty"`
	Confidence interface{} `json:"confidence,omitempty"`
	RiskScore interface{} `json:"risk_score,omitempty"`
	Recommendations interface{} `json:"recommendations,omitempty"`
	Status string `json:"status"`
	HandlerId interface{} `json:"handler_id,omitempty"`
	HandlerName interface{} `json:"handler_name,omitempty"`
	HandleTime interface{} `json:"handle_time,omitempty"`
	HandleNote interface{} `json:"handle_note,omitempty"`
	IsUpgraded bool `json:"is_upgraded,omitempty"`
	UpgradeCount int `json:"upgrade_count,omitempty"`
	LastUpgradeTime interface{} `json:"last_upgrade_time,omitempty"`
	WorkOrderId interface{} `json:"work_order_id,omitempty"`
	SourcePredictionId interface{} `json:"source_prediction_id,omitempty"`
	SilenceUntil interface{} `json:"silence_until,omitempty"`
	CreateTime time.Time `json:"create_time"`
	UpdateTime time.Time `json:"update_time"`
}
// AlertHandleRequest
type AlertHandleRequest struct {
	Action string `json:"action"`
	HandlerId interface{} `json:"handler_id,omitempty"`
	HandlerName interface{} `json:"handler_name,omitempty"`
	HandleNote interface{} `json:"handle_note,omitempty"`
	SilenceMinutes interface{} `json:"silence_minutes,omitempty"`
}
// AlertListResponse
type AlertListResponse struct {
	Total int `json:"total"`
	Items []AlertEventResponse `json:"items"`
}
// AlertRuleCreate
type AlertRuleCreate struct {
	RuleName string `json:"rule_name"`
	AlertLevel int `json:"alert_level"`
	NodeType string `json:"node_type,omitempty"`
	NodeIds interface{} `json:"node_ids,omitempty"`
	MinConfidence float64 `json:"min_confidence,omitempty"`
	SilencePeriod int `json:"silence_period,omitempty"`
	EnableUpgrade bool `json:"enable_upgrade,omitempty"`
	UpgradeMinutes int `json:"upgrade_minutes,omitempty"`
	UpgradeToLevel interface{} `json:"upgrade_to_level,omitempty"`
	Enabled bool `json:"enabled,omitempty"`
	Description interface{} `json:"description,omitempty"`
}
// AlertRuleResponse
type AlertRuleResponse struct {
	RuleName string `json:"rule_name"`
	AlertLevel int `json:"alert_level"`
	NodeType string `json:"node_type,omitempty"`
	NodeIds interface{} `json:"node_ids,omitempty"`
	MinConfidence float64 `json:"min_confidence,omitempty"`
	SilencePeriod int `json:"silence_period,omitempty"`
	EnableUpgrade bool `json:"enable_upgrade,omitempty"`
	UpgradeMinutes int `json:"upgrade_minutes,omitempty"`
	UpgradeToLevel interface{} `json:"upgrade_to_level,omitempty"`
	Enabled bool `json:"enabled,omitempty"`
	Description interface{} `json:"description,omitempty"`
	Id int `json:"id"`
	CreateTime time.Time `json:"create_time"`
	UpdateTime time.Time `json:"update_time"`
}
// AlertRuleUpdate
type AlertRuleUpdate struct {
	RuleName interface{} `json:"rule_name,omitempty"`
	AlertLevel interface{} `json:"alert_level,omitempty"`
	NodeType interface{} `json:"node_type,omitempty"`
	NodeIds interface{} `json:"node_ids,omitempty"`
	MinConfidence interface{} `json:"min_confidence,omitempty"`
	SilencePeriod interface{} `json:"silence_period,omitempty"`
	EnableUpgrade interface{} `json:"enable_upgrade,omitempty"`
	UpgradeMinutes interface{} `json:"upgrade_minutes,omitempty"`
	UpgradeToLevel interface{} `json:"upgrade_to_level,omitempty"`
	Enabled interface{} `json:"enabled,omitempty"`
	Description interface{} `json:"description,omitempty"`
}
// AlertSubscriptionCreate
type AlertSubscriptionCreate struct {
	SubscriberType string `json:"subscriber_type"`
	SubscriberId string `json:"subscriber_id"`
	SubscriberName interface{} `json:"subscriber_name,omitempty"`
	MinAlertLevel int `json:"min_alert_level,omitempty"`
	AlertLevels interface{} `json:"alert_levels,omitempty"`
	NodeType string `json:"node_type,omitempty"`
	NodeIds interface{} `json:"node_ids,omitempty"`
	NotifyChannels interface{} `json:"notify_channels,omitempty"`
	NotifyTargets interface{} `json:"notify_targets,omitempty"`
	Enabled bool `json:"enabled,omitempty"`
}
// AlertSubscriptionResponse
type AlertSubscriptionResponse struct {
	SubscriberType string `json:"subscriber_type"`
	SubscriberId string `json:"subscriber_id"`
	SubscriberName interface{} `json:"subscriber_name,omitempty"`
	MinAlertLevel int `json:"min_alert_level,omitempty"`
	AlertLevels interface{} `json:"alert_levels,omitempty"`
	NodeType string `json:"node_type,omitempty"`
	NodeIds interface{} `json:"node_ids,omitempty"`
	NotifyChannels interface{} `json:"notify_channels,omitempty"`
	NotifyTargets interface{} `json:"notify_targets,omitempty"`
	Enabled bool `json:"enabled,omitempty"`
	Id int `json:"id"`
	CreateTime time.Time `json:"create_time"`
	UpdateTime time.Time `json:"update_time"`
}
// AlertSubscriptionUpdate
type AlertSubscriptionUpdate struct {
	SubscriberType interface{} `json:"subscriber_type,omitempty"`
	SubscriberId interface{} `json:"subscriber_id,omitempty"`
	SubscriberName interface{} `json:"subscriber_name,omitempty"`
	MinAlertLevel interface{} `json:"min_alert_level,omitempty"`
	AlertLevels interface{} `json:"alert_levels,omitempty"`
	NodeType interface{} `json:"node_type,omitempty"`
	NodeIds interface{} `json:"node_ids,omitempty"`
	NotifyChannels interface{} `json:"notify_channels,omitempty"`
	NotifyTargets interface{} `json:"notify_targets,omitempty"`
	Enabled interface{} `json:"enabled,omitempty"`
}
// AlertUpgradeTriggerResponse
type AlertUpgradeTriggerResponse struct {
	UpgradedCount int `json:"upgraded_count"`
	Message string `json:"message"`
}
// AnomalyBatchConfirmRequest
type AnomalyBatchConfirmRequest struct {
	AnomalyIds []int `json:"anomaly_ids"`
	ConfirmedBy interface{} `json:"confirmed_by,omitempty"`
	ConfirmNote interface{} `json:"confirm_note,omitempty"`
}
// AnomalyBatchFalsePositiveRequest
type AnomalyBatchFalsePositiveRequest struct {
	AnomalyIds []int `json:"anomaly_ids"`
	ConfirmedBy interface{} `json:"confirmed_by,omitempty"`
	ConfirmNote interface{} `json:"confirm_note,omitempty"`
}
// AnomalyBatchResultResponse
type AnomalyBatchResultResponse struct {
	Total int `json:"total,omitempty"`
	Success int `json:"success,omitempty"`
	Failed int `json:"failed,omitempty"`
	FailedIds []int `json:"failed_ids,omitempty"`
}
// AnomalyClassificationSchema
type AnomalyClassificationSchema struct {
	AnomalyId interface{} `json:"anomaly_id,omitempty"`
	SensorId string `json:"sensor_id"`
	AnomalyValue float64 `json:"anomaly_value"`
	AnomalyType string `json:"anomaly_type"`
	Classification string `json:"classification"`
	ClassificationConfidence float64 `json:"classification_confidence"`
	CollectionSubtype interface{} `json:"collection_subtype,omitempty"`
	TrueAnomalySubtype interface{} `json:"true_anomaly_subtype,omitempty"`
	Evidence map[string]interface{} `json:"evidence"`
	OriginalTime interface{} `json:"original_time,omitempty"`
}
// AnomalyConfirmRequest
type AnomalyConfirmRequest struct {
	AnomalyId int `json:"anomaly_id"`
	ConfirmedBy interface{} `json:"confirmed_by,omitempty"`
	ConfirmNote interface{} `json:"confirm_note,omitempty"`
}
// sc_anomaly_data
type AnomalyDataResponse struct {
	Id int `json:"id"`
	SensorId string `json:"sensor_id"`
	AnomalyValue interface{} `json:"anomaly_value,omitempty"`
	AnomalyType interface{} `json:"anomaly_type,omitempty"`
	AnomalyScore interface{} `json:"anomaly_score,omitempty"`
	OriginalTime interface{} `json:"original_time,omitempty"`
	Details interface{} `json:"details,omitempty"`
	Classification interface{} `json:"classification,omitempty"`
	ClassificationConfidence interface{} `json:"classification_confidence,omitempty"`
	CollectionSubtype interface{} `json:"collection_subtype,omitempty"`
	TrueAnomalySubtype interface{} `json:"true_anomaly_subtype,omitempty"`
	ClassificationEvidence interface{} `json:"classification_evidence,omitempty"`
	IsConfirmed bool `json:"is_confirmed,omitempty"`
	IsFalsePositive bool `json:"is_false_positive,omitempty"`
	ConfirmedBy interface{} `json:"confirmed_by,omitempty"`
	ConfirmedTime interface{} `json:"confirmed_time,omitempty"`
	ConfirmNote interface{} `json:"confirm_note,omitempty"`
	TenantId interface{} `json:"tenant_id,omitempty"`
	CreateTime interface{} `json:"create_time,omitempty"`
	UpdateTime interface{} `json:"update_time,omitempty"`
}
// AnomalyFalsePositiveRequest
type AnomalyFalsePositiveRequest struct {
	AnomalyId int `json:"anomaly_id"`
	ConfirmedBy interface{} `json:"confirmed_by,omitempty"`
	ConfirmNote interface{} `json:"confirm_note,omitempty"`
}
// AnomalyLinkResultSchema
type AnomalyLinkResultSchema struct {
	SensorId string `json:"sensor_id"`
	TotalAnomalies int `json:"total_anomalies"`
	TrueAnomalies int `json:"true_anomalies"`
	CollectionAnomalies int `json:"collection_anomalies"`
	UncertainAnomalies int `json:"uncertain_anomalies"`
	MixedAnomalies int `json:"mixed_anomalies"`
	ClassifiedAnomalies []AnomalyClassificationSchema `json:"classified_anomalies"`
}
// AnomalyListResponse
type AnomalyListResponse struct {
	Total int `json:"total"`
	Items []AnomalyDataResponse `json:"items"`
}
// sensor_id
type AnomalyQueryRequest struct {
	SensorId interface{} `json:"sensor_id,omitempty"`
	StartTime interface{} `json:"start_time,omitempty"`
	EndTime interface{} `json:"end_time,omitempty"`
	AnomalyType interface{} `json:"anomaly_type,omitempty"`
	Classification interface{} `json:"classification,omitempty"`
	IsConfirmed interface{} `json:"is_confirmed,omitempty"`
	IsFalsePositive interface{} `json:"is_false_positive,omitempty"`
	MinScore interface{} `json:"min_score,omitempty"`
	MaxScore interface{} `json:"max_score,omitempty"`
	Limit int `json:"limit,omitempty"`
	Offset int `json:"offset,omitempty"`
	SortBy string `json:"sort_by,omitempty"`
	SortOrder string `json:"sort_order,omitempty"`
}
// AnomalyStatisticsResponse
type AnomalyStatisticsResponse struct {
	TotalCount int `json:"total_count,omitempty"`
	ConfirmedCount int `json:"confirmed_count,omitempty"`
	UnconfirmedCount int `json:"unconfirmed_count,omitempty"`
	FalsePositiveCount int `json:"false_positive_count,omitempty"`
	TrueAnomalyCount int `json:"true_anomaly_count,omitempty"`
	FalsePositiveRate float64 `json:"false_positive_rate,omitempty"`
	TypeDistribution interface{} `json:"type_distribution,omitempty"`
	ClassificationDistribution interface{} `json:"classification_distribution,omitempty"`
	TimeRange interface{} `json:"time_range,omitempty"`
}
// AnomalyWarningImpactResponse
type AnomalyWarningImpactResponse struct {
	SensorId string `json:"sensor_id"`
	ShouldUpgrade bool `json:"should_upgrade,omitempty"`
	OriginalLevel int `json:"original_level"`
	UpgradedLevel int `json:"upgraded_level"`
	AnomalyCount int `json:"anomaly_count,omitempty"`
	Threshold int `json:"threshold,omitempty"`
	WindowMinutes int `json:"window_minutes,omitempty"`
}
// AuditCleanupResponse
type AuditCleanupResponse struct {
	CleanedCount int `json:"cleaned_count"`
	Message string `json:"message"`
}
// AuditExportRequest
type AuditExportRequest struct {
	StartTime time.Time `json:"start_time"`
	EndTime time.Time `json:"end_time"`
	NodeType interface{} `json:"node_type,omitempty"`
	NodeId interface{} `json:"node_id,omitempty"`
	Format string `json:"format,omitempty"`
}
// AuditListResponse
type AuditListResponse struct {
	Total int `json:"total"`
	Items []AuditRecordResponse `json:"items"`
}
// AuditRecordResponse
type AuditRecordResponse struct {
	Id int `json:"id"`
	PredictionId string `json:"prediction_id"`
	NodeType string `json:"node_type"`
	NodeId string `json:"node_id"`
	InputHash interface{} `json:"input_hash,omitempty"`
	ModelVersion interface{} `json:"model_version,omitempty"`
	ModelType interface{} `json:"model_type,omitempty"`
	FeatureSummary interface{} `json:"feature_summary,omitempty"`
	IntermediateResults interface{} `json:"intermediate_results,omitempty"`
	FinalDecision interface{} `json:"final_decision,omitempty"`
	StrategyVersion interface{} `json:"strategy_version,omitempty"`
	StrategyType interface{} `json:"strategy_type,omitempty"`
	Explainability interface{} `json:"explainability,omitempty"`
	RetentionYears int `json:"retention_years,omitempty"`
	ExpireTime interface{} `json:"expire_time,omitempty"`
	CreateTime time.Time `json:"create_time"`
}
// AuditRetentionUpdateRequest
type AuditRetentionUpdateRequest struct {
	RetentionYears int `json:"retention_years"`
}
// BatchReportGenerateRequest
type BatchReportGenerateRequest struct {
	NodeType string `json:"node_type"`
	NodeIds []string `json:"node_ids"`
	ReportType string `json:"report_type,omitempty"`
}
// BatchReportResponse
type BatchReportResponse struct {
	Total int `json:"total,omitempty"`
	Success int `json:"success,omitempty"`
	Failed int `json:"failed,omitempty"`
	Results []PeriodicReportResponse `json:"results,omitempty"`
	Errors map[string]string `json:"errors,omitempty"`
}
// BoltEnsemblePredictionRequest
type BoltEnsemblePredictionRequest struct {
	BoltId string `json:"bolt_id"`
	Data []float64 `json:"data"`
	Version interface{} `json:"version,omitempty"`
	Method interface{} `json:"method,omitempty"`
	Weights interface{} `json:"weights,omitempty"`
}
// Attributes:
// bolt_id: ID
// prediction_source:
// ensemble_method: : hard / soft / weighted
// final_status:
// final_status_code:
// final_confidence:
// final_probs:
// weights:
// individual_results:
// individual_probs:
// model_version:
// duration_ms: (ms)
// ema_accuracy: EMA
// performance_history:
type BoltEnsemblePredictionResponse struct {
	BoltId string `json:"bolt_id"`
	PredictionSource string `json:"prediction_source"`
	EnsembleMethod string `json:"ensemble_method"`
	FinalStatus string `json:"final_status"`
	FinalStatusCode int `json:"final_status_code"`
	FinalConfidence float64 `json:"final_confidence"`
	FinalProbs interface{} `json:"final_probs,omitempty"`
	Weights map[string]float64 `json:"weights"`
	IndividualResults []map[string]interface{} `json:"individual_results"`
	IndividualProbs map[string]interface{} `json:"individual_probs"`
	ModelVersion string `json:"model_version"`
	DurationMs float64 `json:"duration_ms"`
	EmaAccuracy map[string]float64 `json:"ema_accuracy"`
	PerformanceHistory map[string][]float64 `json:"performance_history"`
}
// BoltHealthIndexSchema
type BoltHealthIndexSchema struct {
	HiScore float64 `json:"hi_score"`
	HiLevel string `json:"hi_level"`
	Factors []HealthIndexFactorSchema `json:"factors"`
	PreloadStabilityScore float64 `json:"preload_stability_score"`
	AlertFrequencyScore float64 `json:"alert_frequency_score"`
	FaultHistoryScore float64 `json:"fault_history_score"`
	EnvironmentalStressScore float64 `json:"environmental_stress_score"`
	ServiceAgeScore float64 `json:"service_age_score"`
	Trend interface{} `json:"trend,omitempty"`
	TrendRate interface{} `json:"trend_rate,omitempty"`
	CalculateTime time.Time `json:"calculate_time"`
	BoltId string `json:"bolt_id"`
	BoltName interface{} `json:"bolt_name,omitempty"`
	CurrentPreload interface{} `json:"current_preload,omitempty"`
	NominalPreload interface{} `json:"nominal_preload,omitempty"`
	PreloadDeviation interface{} `json:"preload_deviation,omitempty"`
	LastMaintenanceDate interface{} `json:"last_maintenance_date,omitempty"`
}
// 1. channels
// 2. aligned_data
// Attributes:
// bolt_id:
// channels:  {: [[, ], ...]}
// aligned_data:  [[, 1, 2, ...], ...]
// aligned_channel_names:  aligned_data
// timestamps:
// apply_temp_compensation:  True
// enable_degradation:  True
// version:
type BoltMultivariatePredictionRequest struct {
	BoltId string `json:"bolt_id"`
	Channels interface{} `json:"channels,omitempty"`
	AlignedData interface{} `json:"aligned_data,omitempty"`
	AlignedChannelNames interface{} `json:"aligned_channel_names,omitempty"`
	Timestamps interface{} `json:"timestamps,omitempty"`
	ApplyTempCompensation bool `json:"apply_temp_compensation,omitempty"`
	EnableDegradation bool `json:"enable_degradation,omitempty"`
	Version interface{} `json:"version,omitempty"`
}
// - data_quality:
// - channels_info:
// - temp_compensation:
// - feature_importance:
type BoltMultivariatePredictionResponse struct {
	BoltId string `json:"bolt_id"`
	Status string `json:"status"`
	StatusCode int `json:"status_code"`
	Confidence float64 `json:"confidence"`
	RiskScore float64 `json:"risk_score"`
	RiskLevel string `json:"risk_level"`
	Diagnosis string `json:"diagnosis"`
	Recommendations []string `json:"recommendations"`
	PredictionTime time.Time `json:"prediction_time"`
	ModelVersion interface{} `json:"model_version,omitempty"`
	InputDimActual int `json:"input_dim_actual"`
	ChannelsInfo []MultivariateChannelSchema `json:"channels_info,omitempty"`
	DataQuality *DataQualityInfo `json:"data_quality"`
	TempCompensation interface{} `json:"temp_compensation,omitempty"`
	FeatureImportance interface{} `json:"feature_importance,omitempty"`
	SequenceLengthUsed int `json:"sequence_length_used,omitempty"`
	PredictionSource string `json:"prediction_source,omitempty"`
	FaultDetail interface{} `json:"fault_detail,omitempty"`
	ShadowVersion interface{} `json:"shadow_version,omitempty"`
	ShadowResult interface{} `json:"shadow_result,omitempty"`
}
// Attributes:
// id:
// data:  [[, ], ...]
type BoltPredictionRequest struct {
	BoltId string `json:"bolt_id"`
	Data [][]interface{} `json:"data"`
}
// Attributes:
// bolt_id: ID
// status:
// status_code:
// confidence:
// risk_score:
// risk_level:
// diagnosis:
// recommendations:
// prediction_time:
// model_version:
// shadow_version: Shadow
// shadow_result: Shadow
type BoltPredictionResponse struct {
	BoltId string `json:"bolt_id"`
	Status string `json:"status"`
	StatusCode int `json:"status_code"`
	Confidence float64 `json:"confidence"`
	RiskScore float64 `json:"risk_score"`
	RiskLevel string `json:"risk_level"`
	Diagnosis string `json:"diagnosis"`
	Recommendations []string `json:"recommendations"`
	PredictionTime time.Time `json:"prediction_time"`
	ModelVersion interface{} `json:"model_version,omitempty"`
	ShadowVersion interface{} `json:"shadow_version,omitempty"`
	ShadowResult interface{} `json:"shadow_result,omitempty"`
	FaultDetail interface{} `json:"fault_detail,omitempty"`
	PredictionSource interface{} `json:"prediction_source,omitempty"`
	Ensemble interface{} `json:"ensemble,omitempty"`
}
// CarbonModelConfigResponse
type CarbonModelConfigResponse struct {
	Degradation *DegradationParamsSchema `json:"degradation"`
	Leakage *LeakageParamsSchema `json:"leakage"`
	EnergyCarbon *EnergyCarbonParamsSchema `json:"energy_carbon"`
}
// CarbonModelConfigUpdateRequest
type CarbonModelConfigUpdateRequest struct {
	Degradation interface{} `json:"degradation,omitempty"`
	Leakage interface{} `json:"leakage,omitempty"`
	EnergyCarbon interface{} `json:"energy_carbon,omitempty"`
	OperatorId interface{} `json:"operator_id,omitempty"`
	OperatorName interface{} `json:"operator_name,omitempty"`
	Description interface{} `json:"description,omitempty"`
}
// CarbonMonthlyRankingRequest
type CarbonMonthlyRankingRequest struct {
	Nodes []map[string]interface{} `json:"nodes"`
	TopN interface{} `json:"top_n,omitempty"`
}
// CarbonMonthlyRankingResponse
type CarbonMonthlyRankingResponse struct {
	ReportMonth string `json:"report_month"`
	TotalNodes int `json:"total_nodes"`
	TotalMonthlyCarbonIncrementKg float64 `json:"total_monthly_carbon_increment_kg"`
	TotalMonthlyLeakageVolumeM3 float64 `json:"total_monthly_leakage_volume_m3"`
	RiskDistribution map[string]int `json:"risk_distribution"`
	RankedItems []CarbonRiskItemSchema `json:"ranked_items"`
	GeneratedAt time.Time `json:"generated_at"`
}
// CarbonRiskItemSchema
type CarbonRiskItemSchema struct {
	Rank interface{} `json:"rank,omitempty"`
	NodeId string `json:"node_id"`
	NodeType string `json:"node_type"`
	NodeName string `json:"node_name"`
	HiScore float64 `json:"hi_score"`
	HiLevel string `json:"hi_level"`
	CarbonRiskScore float64 `json:"carbon_risk_score"`
	CarbonRiskLevel string `json:"carbon_risk_level"`
	MonthlyLeakageVolumeM3 float64 `json:"monthly_leakage_volume_m3"`
	MonthlyCarbonIncrementKg float64 `json:"monthly_carbon_increment_kg"`
	PriorityScore float64 `json:"priority_score"`
	Trend string `json:"trend"`
	Recommendations []string `json:"recommendations,omitempty"`
}
// CaseReviewRequest
type CaseReviewRequest struct {
	ReviewResult string `json:"review_result"`
	ReviewComment interface{} `json:"review_comment,omitempty"`
	ReviewerId interface{} `json:"reviewer_id,omitempty"`
	ReviewerName interface{} `json:"reviewer_name,omitempty"`
	ReviewLevel int `json:"review_level,omitempty"`
}
// CaseSimilaritySearchRequest
type CaseSimilaritySearchRequest struct {
	NodeType interface{} `json:"node_type,omitempty"`
	NodeId interface{} `json:"node_id,omitempty"`
	FaultType interface{} `json:"fault_type,omitempty"`
	FaultLevel interface{} `json:"fault_level,omitempty"`
	SensorData interface{} `json:"sensor_data,omitempty"`
	SensorFeatures interface{} `json:"sensor_features,omitempty"`
	FeatureVector interface{} `json:"feature_vector,omitempty"`
	Tags interface{} `json:"tags,omitempty"`
	TopK int `json:"top_k,omitempty"`
	MinSimilarity float64 `json:"min_similarity,omitempty"`
	OnlyApproved bool `json:"only_approved,omitempty"`
	TenantId interface{} `json:"tenant_id,omitempty"`
}
// CausalGraphEdgeSchema
type CausalGraphEdgeSchema struct {
	Source string `json:"source"`
	Target string `json:"target"`
	SourceIdx int `json:"source_idx"`
	TargetIdx int `json:"target_idx"`
	Weight float64 `json:"weight"`
	Correlation float64 `json:"correlation"`
	PValue interface{} `json:"p_value,omitempty"`
	FStat interface{} `json:"f_stat,omitempty"`
	Lag interface{} `json:"lag,omitempty"`
	Type string `json:"type"`
}
// CausalGraphNodeSchema
type CausalGraphNodeSchema struct {
	Id string `json:"id"`
	Index int `json:"index"`
	InDegree int `json:"in_degree"`
	OutDegree int `json:"out_degree"`
	TotalDegree int `json:"total_degree"`
	Centrality float64 `json:"centrality"`
}
// CausalGraphSchema
type CausalGraphSchema struct {
	Nodes []CausalGraphNodeSchema `json:"nodes"`
	Edges []CausalGraphEdgeSchema `json:"edges"`
	AdjacencyMatrix [][]float64 `json:"adjacency_matrix"`
	EdgeWeights [][]float64 `json:"edge_weights"`
	BoltIds []string `json:"bolt_ids"`
}
// ClassImbalanceConfig
type ClassImbalanceConfig struct {
	Strategy string `json:"strategy,omitempty"`
	OversamplingRatio interface{} `json:"oversampling_ratio,omitempty"`
}
// CMMS
type CmmsConfigCreate struct {
	SystemName string `json:"system_name"`
	SystemType interface{} `json:"system_type,omitempty"`
	BaseUrl interface{} `json:"base_url,omitempty"`
	AuthType interface{} `json:"auth_type,omitempty"`
	AuthConfig interface{} `json:"auth_config,omitempty"`
	WorkOrderSync interface{} `json:"work_order_sync,omitempty"`
	WorkOrderWebhookUrl interface{} `json:"work_order_webhook_url,omitempty"`
	WorkOrderPushUrl interface{} `json:"work_order_push_url,omitempty"`
	StatusMapping interface{} `json:"status_mapping,omitempty"`
	PriorityMapping interface{} `json:"priority_mapping,omitempty"`
	FieldMapping interface{} `json:"field_mapping,omitempty"`
	Enabled interface{} `json:"enabled,omitempty"`
	SyncDirection interface{} `json:"sync_direction,omitempty"`
	SyncInterval interface{} `json:"sync_interval,omitempty"`
	TenantId interface{} `json:"tenant_id,omitempty"`
	ExtraInfo interface{} `json:"extra_info,omitempty"`
}
// CMMS
type CmmsConfigListResponse struct {
	Total int `json:"total"`
	Items []CmmsConfigResponse `json:"items"`
}
// CMMS
type CmmsConfigResponse struct {
	Id int `json:"id"`
	SystemName string `json:"system_name"`
	SystemType interface{} `json:"system_type,omitempty"`
	BaseUrl interface{} `json:"base_url,omitempty"`
	AuthType interface{} `json:"auth_type,omitempty"`
	WorkOrderSync interface{} `json:"work_order_sync,omitempty"`
	WorkOrderWebhookUrl interface{} `json:"work_order_webhook_url,omitempty"`
	WorkOrderPushUrl interface{} `json:"work_order_push_url,omitempty"`
	StatusMapping interface{} `json:"status_mapping,omitempty"`
	PriorityMapping interface{} `json:"priority_mapping,omitempty"`
	FieldMapping interface{} `json:"field_mapping,omitempty"`
	Enabled interface{} `json:"enabled,omitempty"`
	SyncDirection interface{} `json:"sync_direction,omitempty"`
	LastSyncTime interface{} `json:"last_sync_time,omitempty"`
	SyncInterval interface{} `json:"sync_interval,omitempty"`
	TenantId interface{} `json:"tenant_id,omitempty"`
	ExtraInfo interface{} `json:"extra_info,omitempty"`
	CreateTime time.Time `json:"create_time"`
	UpdateTime time.Time `json:"update_time"`
}
// CMMS
type CmmsConfigUpdate struct {
	SystemName interface{} `json:"system_name,omitempty"`
	SystemType interface{} `json:"system_type,omitempty"`
	BaseUrl interface{} `json:"base_url,omitempty"`
	AuthType interface{} `json:"auth_type,omitempty"`
	AuthConfig interface{} `json:"auth_config,omitempty"`
	WorkOrderSync interface{} `json:"work_order_sync,omitempty"`
	WorkOrderWebhookUrl interface{} `json:"work_order_webhook_url,omitempty"`
	WorkOrderPushUrl interface{} `json:"work_order_push_url,omitempty"`
	StatusMapping interface{} `json:"status_mapping,omitempty"`
	PriorityMapping interface{} `json:"priority_mapping,omitempty"`
	FieldMapping interface{} `json:"field_mapping,omitempty"`
	Enabled interface{} `json:"enabled,omitempty"`
	SyncDirection interface{} `json:"sync_direction,omitempty"`
	SyncInterval interface{} `json:"sync_interval,omitempty"`
	ExtraInfo interface{} `json:"extra_info,omitempty"`
}
// CMMS
type CmmsSyncLogListResponse struct {
	Total int `json:"total"`
	Items []CmmsSyncLogResponse `json:"items"`
}
// CMMS
type CmmsSyncLogResponse struct {
	Id int `json:"id"`
	ConfigId interface{} `json:"config_id,omitempty"`
	SyncType interface{} `json:"sync_type,omitempty"`
	SyncDirection interface{} `json:"sync_direction,omitempty"`
	WorkOrderId interface{} `json:"work_order_id,omitempty"`
	ExternalId interface{} `json:"external_id,omitempty"`
	Status interface{} `json:"status,omitempty"`
	ErrorMessage interface{} `json:"error_message,omitempty"`
	RetryCount interface{} `json:"retry_count,omitempty"`
	SyncTime interface{} `json:"sync_time,omitempty"`
	CreateTime time.Time `json:"create_time"`
}
// CMMS
type CmmsSyncRequest struct {
	ConfigId int `json:"config_id"`
	SyncType string `json:"sync_type,omitempty"`
	WorkOrderId interface{} `json:"work_order_id,omitempty"`
}
// CMMS
type CmmsSyncResponse struct {
	Success bool `json:"success"`
	SyncLogId interface{} `json:"sync_log_id,omitempty"`
	ExternalId interface{} `json:"external_id,omitempty"`
	Message interface{} `json:"message,omitempty"`
}
// CMMS Webhook
type CmmsWebhookResponse struct {
	Success bool `json:"success"`
	Message string `json:"message"`
	ProcessedCount interface{} `json:"processed_count,omitempty"`
}
// ConfidenceAdjustmentRequest
type ConfidenceAdjustmentRequest struct {
	SensorId string `json:"sensor_id"`
	OriginalConfidence float64 `json:"original_confidence"`
	Data [][]interface{} `json:"data"`
}
// ConfidenceAdjustmentResponse
type ConfidenceAdjustmentResponse struct {
	SensorId string `json:"sensor_id"`
	OriginalConfidence float64 `json:"original_confidence"`
	AdjustedConfidence float64 `json:"adjusted_confidence"`
	QualityScore float64 `json:"quality_score"`
	QualityLevel string `json:"quality_level"`
	AdjustmentFactor float64 `json:"adjustment_factor"`
	Reasons []string `json:"reasons"`
}
// ConfigCenterResponse
type ConfigCenterResponse struct {
	WarningStrategy *WarningStrategyConfigSchema `json:"warning_strategy"`
	Thresholds *ThresholdConfigSchema `json:"thresholds"`
	ScheduledJobs []ScheduledJobSchema `json:"scheduled_jobs"`
	UpdatedAt time.Time `json:"updated_at"`
}
// DailyQualityReportSchema
type DailyQualityReportSchema struct {
	ReportDate time.Time `json:"report_date"`
	TotalSensors int `json:"total_sensors"`
	AverageQualityScore float64 `json:"average_quality_score"`
	QualityDistribution map[string]int `json:"quality_distribution"`
	ProblemSensors []ProblemSensorRankingSchema `json:"problem_sensors"`
	Recommendations []RepairRecommendationSchema `json:"recommendations"`
	AnomalyStatistics map[string]interface{} `json:"anomaly_statistics"`
	QualityTrend []map[string]interface{} `json:"quality_trend"`
	Summary string `json:"summary"`
	GeneratedAt time.Time `json:"generated_at"`
}
// DataQualityCheckBatchRequest
type DataQualityCheckBatchRequest struct {
	SensorsData map[string][][]interface{} `json:"sensors_data"`
}
// DataQualityCheckRequest
type DataQualityCheckRequest struct {
	SensorId string `json:"sensor_id"`
	Data [][]interface{} `json:"data"`
	IncludeAnomalyClassification bool `json:"include_anomaly_classification,omitempty"`
}
// DataQualityHistoryRequest
type DataQualityHistoryRequest struct {
	SensorId string `json:"sensor_id"`
	StartTime interface{} `json:"start_time,omitempty"`
	EndTime interface{} `json:"end_time,omitempty"`
	Limit int `json:"limit,omitempty"`
}
// Attributes:
// level:  full=, partial=, degraded=
// complete_ratio:  (0-1)
// missing_channels: /
// interpolation_count:
// interpolation_flags: 1= 0=
// degradation_applied:
type DataQualityInfo struct {
	Level string `json:"level,omitempty"`
	CompleteRatio float64 `json:"complete_ratio,omitempty"`
	MissingChannels []string `json:"missing_channels,omitempty"`
	InterpolationCount int `json:"interpolation_count,omitempty"`
	DegradationApplied bool `json:"degradation_applied,omitempty"`
	ActualChannelsUsed []string `json:"actual_channels_used,omitempty"`
}
// DegradationParamsSchema
type DegradationParamsSchema struct {
	NominalPreload float64 `json:"nominal_preload,omitempty"`
	MinEffectivePreloadRatio float64 `json:"min_effective_preload_ratio,omitempty"`
	RelaxationRatePerMonth float64 `json:"relaxation_rate_per_month,omitempty"`
	TemperatureAccelerationFactor float64 `json:"temperature_acceleration_factor,omitempty"`
	VibrationAccelerationFactor float64 `json:"vibration_acceleration_factor,omitempty"`
	CycleAccelerationFactor float64 `json:"cycle_acceleration_factor,omitempty"`
}
// DiagnosisReportRequest
type DiagnosisReportRequest struct {
	Status string `json:"status"`
	RiskScore float64 `json:"risk_score"`
	NodeType string `json:"node_type,omitempty"`
	NodeId interface{} `json:"node_id,omitempty"`
	FaultType interface{} `json:"fault_type,omitempty"`
	Trend interface{} `json:"trend,omitempty"`
	RecentValues interface{} `json:"recent_values,omitempty"`
	HistoricalIncidents interface{} `json:"historical_incidents,omitempty"`
}
// DiagnosisReportResponse
type DiagnosisReportResponse struct {
	DiagnosisSummary string `json:"diagnosis_summary"`
	RecommendedActions []string `json:"recommended_actions"`
	UrgencyLevel string `json:"urgency_level"`
	Model string `json:"model"`
	TokensUsed int `json:"tokens_used,omitempty"`
	LatencyMs float64 `json:"latency_ms,omitempty"`
	IsFallback bool `json:"is_fallback,omitempty"`
}
// DisposalRecordCreate
type DisposalRecordCreate struct {
	WorkOrderId int `json:"work_order_id"`
	DisposalType string `json:"disposal_type"`
	DisposalContent string `json:"disposal_content"`
	DisposalTime interface{} `json:"disposal_time,omitempty"`
	OperatorId interface{} `json:"operator_id,omitempty"`
	OperatorName interface{} `json:"operator_name,omitempty"`
	BeforeValue interface{} `json:"before_value,omitempty"`
	AfterValue interface{} `json:"after_value,omitempty"`
	MaterialsUsed interface{} `json:"materials_used,omitempty"`
	Photos interface{} `json:"photos,omitempty"`
	Notes interface{} `json:"notes,omitempty"`
	ExtraInfo interface{} `json:"extra_info,omitempty"`
}
// DisposalRecordListResponse
type DisposalRecordListResponse struct {
	Total int `json:"total"`
	Items []DisposalRecordResponse `json:"items"`
}
// DisposalRecordResponse
type DisposalRecordResponse struct {
	Id int `json:"id"`
	WorkOrderId int `json:"work_order_id"`
	DisposalType interface{} `json:"disposal_type,omitempty"`
	DisposalContent interface{} `json:"disposal_content,omitempty"`
	DisposalTime interface{} `json:"disposal_time,omitempty"`
	OperatorId interface{} `json:"operator_id,omitempty"`
	OperatorName interface{} `json:"operator_name,omitempty"`
	BeforeValue interface{} `json:"before_value,omitempty"`
	AfterValue interface{} `json:"after_value,omitempty"`
	MaterialsUsed interface{} `json:"materials_used,omitempty"`
	Photos interface{} `json:"photos,omitempty"`
	Notes interface{} `json:"notes,omitempty"`
	ExtraInfo interface{} `json:"extra_info,omitempty"`
	CreateTime time.Time `json:"create_time"`
}
// DisposalRecordUpdate
type DisposalRecordUpdate struct {
	DisposalType interface{} `json:"disposal_type,omitempty"`
	DisposalContent interface{} `json:"disposal_content,omitempty"`
	DisposalTime interface{} `json:"disposal_time,omitempty"`
	OperatorId interface{} `json:"operator_id,omitempty"`
	OperatorName interface{} `json:"operator_name,omitempty"`
	BeforeValue interface{} `json:"before_value,omitempty"`
	AfterValue interface{} `json:"after_value,omitempty"`
	MaterialsUsed interface{} `json:"materials_used,omitempty"`
	Photos interface{} `json:"photos,omitempty"`
	Notes interface{} `json:"notes,omitempty"`
	ExtraInfo interface{} `json:"extra_info,omitempty"`
}
// ESG
type EsgReportExportRequest struct {
	Nodes []map[string]interface{} `json:"nodes"`
	Format string `json:"format,omitempty"`
	IncludeMethodology bool `json:"include_methodology,omitempty"`
	TopN interface{} `json:"top_n,omitempty"`
}
// ESG
type EsgReportFragmentResponse struct {
	ReportPeriod string `json:"report_period"`
	GeneratedAt time.Time `json:"generated_at"`
	Summary *EsgReportSummarySchema `json:"summary"`
	TopRiskItems []CarbonRiskItemSchema `json:"top_risk_items"`
	TrendAnalysis *EsgTrendAnalysisSchema `json:"trend_analysis"`
	Recommendations []string `json:"recommendations"`
	MethodologyNote interface{} `json:"methodology_note,omitempty"`
	CsvContent interface{} `json:"csv_content,omitempty"`
}
// ESG
type EsgReportSummarySchema struct {
	ReportingPeriod string `json:"reporting_period"`
	TotalDevicesAnalyzed int `json:"total_devices_analyzed"`
	EstimatedMonthlyCarbonIncrementKg float64 `json:"estimated_monthly_carbon_increment_kg"`
	EstimatedMonthlyCarbonIncrementTons float64 `json:"estimated_monthly_carbon_increment_tons"`
	EstimatedMonthlyLeakageM3 float64 `json:"estimated_monthly_leakage_m3"`
	AverageCarbonPerDeviceKg float64 `json:"average_carbon_per_device_kg"`
	CarbonRiskSeverity string `json:"carbon_risk_severity"`
	Top5ContributionRatio float64 `json:"top5_contribution_ratio"`
	RiskDistribution map[string]int `json:"risk_distribution"`
}
// ESG
type EsgTrendAnalysisSchema struct {
	OverallTrend string `json:"overall_trend"`
	ImprovingCount int `json:"improving_count"`
	StableCount int `json:"stable_count"`
	DecliningCount int `json:"declining_count"`
	KeyObservation string `json:"key_observation"`
}
// EarlyStoppingConfig
type EarlyStoppingConfig struct {
	Enabled bool `json:"enabled,omitempty"`
	Patience int `json:"patience,omitempty"`
	MinDelta float64 `json:"min_delta,omitempty"`
	Mode string `json:"mode,omitempty"`
}
// EdgeDeviceHeartbeatRequest
type EdgeDeviceHeartbeatRequest struct {
	DeviceId string `json:"device_id"`
	ModelVersion interface{} `json:"model_version,omitempty"`
	CacheSize int `json:"cache_size,omitempty"`
	UnsyncedCount int `json:"unsynced_count,omitempty"`
}
// EdgeDeviceHeartbeatResponse
type EdgeDeviceHeartbeatResponse struct {
	DeviceId string `json:"device_id"`
	LatestModelVersion interface{} `json:"latest_model_version,omitempty"`
	ForceSync bool `json:"force_sync,omitempty"`
	ServerTime string `json:"server_time"`
}
// EdgeDeviceRegisterRequest
type EdgeDeviceRegisterRequest struct {
	DeviceId string `json:"device_id"`
	DeviceName interface{} `json:"device_name,omitempty"`
	DeviceType interface{} `json:"device_type,omitempty"`
	Location interface{} `json:"location,omitempty"`
	Capabilities interface{} `json:"capabilities,omitempty"`
}
// EdgeDeviceRegisterResponse
type EdgeDeviceRegisterResponse struct {
	DeviceId string `json:"device_id"`
	Status string `json:"status"`
	Message string `json:"message"`
	RegisteredAt string `json:"registered_at"`
}
// EdgeModelExportRequest
type EdgeModelExportRequest struct {
	ModelType string `json:"model_type"`
	NodeId interface{} `json:"node_id,omitempty"`
	ExportFormat string `json:"export_format,omitempty"`
	Version interface{} `json:"version,omitempty"`
}
// EdgeModelExportResponse
type EdgeModelExportResponse struct {
	ModelType string `json:"model_type"`
	NodeId interface{} `json:"node_id,omitempty"`
	Version string `json:"version"`
	ExportFormat string `json:"export_format"`
	PackageUrl string `json:"package_url"`
	FileHash string `json:"file_hash"`
	FileSize int `json:"file_size"`
	IncludesPreprocessing bool `json:"includes_preprocessing,omitempty"`
	IncludesSignature bool `json:"includes_signature,omitempty"`
	ExportedAt string `json:"exported_at"`
}
// EdgeModelLatestRequest
type EdgeModelLatestRequest struct {
	ModelType string `json:"model_type"`
	NodeId interface{} `json:"node_id,omitempty"`
	EdgeDeviceId interface{} `json:"edge_device_id,omitempty"`
}
// EdgeModelLatestResponse
type EdgeModelLatestResponse struct {
	Version string `json:"version"`
	ModelType string `json:"model_type"`
	NodeId interface{} `json:"node_id,omitempty"`
	DownloadUrl string `json:"download_url"`
	FileHash string `json:"file_hash"`
	FileSize int `json:"file_size"`
	CreatedAt string `json:"created_at"`
	Metrics interface{} `json:"metrics,omitempty"`
}
// EdgePredictionUploadRequest
type EdgePredictionUploadRequest struct {
	DeviceId string `json:"device_id"`
	Predictions []map[string]interface{} `json:"predictions"`
}
// EdgePredictionUploadResponse
type EdgePredictionUploadResponse struct {
	DeviceId string `json:"device_id"`
	ReceivedCount int `json:"received_count"`
	Status string `json:"status"`
	Message string `json:"message"`
}
// EffectEvaluationSchema
type EffectEvaluationSchema struct {
	OverallRating interface{} `json:"overall_rating,omitempty"`
	EffectivenessScore interface{} `json:"effectiveness_score,omitempty"`
	FaultResolved interface{} `json:"fault_resolved,omitempty"`
	RecurrenceWithinDays interface{} `json:"recurrence_within_days,omitempty"`
	ActualCost interface{} `json:"actual_cost,omitempty"`
	ActualDurationMinutes interface{} `json:"actual_duration_minutes,omitempty"`
	SideEffects interface{} `json:"side_effects,omitempty"`
	ImprovementMetrics interface{} `json:"improvement_metrics,omitempty"`
	Notes interface{} `json:"notes,omitempty"`
}
// EffectiveStrategyResponse
type EffectiveStrategyResponse struct {
	GlobalConfig *StrategyConfigItemResponse `json:"global_config"`
	NodeOverrides []StrategyConfigItemResponse `json:"node_overrides,omitempty"`
	Effective *StrategyConfigItemResponse `json:"effective"`
}
// EnergyCarbonParamsSchema
type EnergyCarbonParamsSchema struct {
	EnergyPerLeakageUnit float64 `json:"energy_per_leakage_unit,omitempty"`
	CarbonFactorElectricity float64 `json:"carbon_factor_electricity,omitempty"`
	CarbonFactorNaturalGas float64 `json:"carbon_factor_natural_gas,omitempty"`
	CarbonFactorSteam float64 `json:"carbon_factor_steam,omitempty"`
	CompressorEfficiency float64 `json:"compressor_efficiency,omitempty"`
	RecoveryRate float64 `json:"recovery_rate,omitempty"`
	BaseMonthlyEnergyKwh float64 `json:"base_monthly_energy_kwh,omitempty"`
	BaseMonthlyCarbonKg float64 `json:"base_monthly_carbon_kg,omitempty"`
}
// EnhancedTrainingRequest
type EnhancedTrainingRequest struct {
	ModelType string `json:"model_type"`
	NodeId interface{} `json:"node_id,omitempty"`
	ForceRetrain bool `json:"force_retrain,omitempty"`
	DataSource string `json:"data_source,omitempty"`
	IsIncremental bool `json:"is_incremental,omitempty"`
	BaseModelVersion interface{} `json:"base_model_version,omitempty"`
	FreezeLayers interface{} `json:"freeze_layers,omitempty"`
	TrainingConfig interface{} `json:"training_config,omitempty"`
}
// EnhancedTrainingResponse
type EnhancedTrainingResponse struct {
	SessionId string `json:"session_id"`
	ModelType string `json:"model_type"`
	NodeId interface{} `json:"node_id"`
	Status string `json:"status"`
	Message string `json:"message"`
	IsIncremental bool `json:"is_incremental,omitempty"`
}
// Epoch
type EpochMetricsSchema struct {
	Epoch int `json:"epoch"`
	TrainLoss float64 `json:"train_loss"`
	ValLoss interface{} `json:"val_loss,omitempty"`
	TrainAcc interface{} `json:"train_acc,omitempty"`
	ValAcc interface{} `json:"val_acc,omitempty"`
	LearningRate interface{} `json:"learning_rate,omitempty"`
	DurationSeconds float64 `json:"duration_seconds,omitempty"`
	Timestamp string `json:"timestamp"`
}
// ExplainabilityReportResponse
type ExplainabilityReportResponse struct {
	PredictionId string `json:"prediction_id"`
	AttentionWeights interface{} `json:"attention_weights,omitempty"`
	KeyTimesteps interface{} `json:"key_timesteps,omitempty"`
	RiskFactorDecomposition interface{} `json:"risk_factor_decomposition,omitempty"`
	RuleHits interface{} `json:"rule_hits,omitempty"`
	StrategyAdjustment interface{} `json:"strategy_adjustment,omitempty"`
}
// FactorContributionSchema
type FactorContributionSchema struct {
	Name string `json:"name"`
	DisplayName string `json:"display_name"`
	RawScore float64 `json:"raw_score"`
	Weight float64 `json:"weight"`
	WeightedScore float64 `json:"weighted_score"`
	ContributionRatio float64 `json:"contribution_ratio"`
	Direction string `json:"direction"`
}
// FaultDetailSchema
type FaultDetailSchema struct {
	FaultType string `json:"fault_type"`
	FaultConfidence float64 `json:"fault_confidence"`
	FaultName string `json:"fault_name"`
	Severity int `json:"severity"`
	Evidence []string `json:"evidence,omitempty"`
	Recommendations []string `json:"recommendations,omitempty"`
	Pattern interface{} `json:"pattern,omitempty"`
}
// FaultPatternSchema
type FaultPatternSchema struct {
	TrendSlope float64 `json:"trend_slope"`
	Volatility float64 `json:"volatility"`
	SuddenChanges int `json:"sudden_changes"`
	MinValue float64 `json:"min_value"`
	MaxValue float64 `json:"max_value"`
	MeanValue float64 `json:"mean_value"`
}
// FeatureImportanceInfo
type FeatureImportanceInfo struct {
	Preload float64 `json:"preload,omitempty"`
	Temperature float64 `json:"temperature,omitempty"`
	Humidity float64 `json:"humidity,omitempty"`
	Vibration float64 `json:"vibration,omitempty"`
	Torque float64 `json:"torque,omitempty"`
	Others map[string]float64 `json:"others,omitempty"`
}
// FederatedAggregatorConfig
type FederatedAggregatorConfig struct {
	Strategy string `json:"strategy,omitempty"`
	TrimRatio float64 `json:"trim_ratio,omitempty"`
	Mu float64 `json:"mu,omitempty"`
	ServerLearningRate float64 `json:"server_learning_rate,omitempty"`
	MinClientsPerRound int `json:"min_clients_per_round,omitempty"`
	EnableOutlierDetection bool `json:"enable_outlier_detection,omitempty"`
}
// FederatedClientRegisterRequest
type FederatedClientRegisterRequest struct {
	ClientId string `json:"client_id"`
	FactoryName interface{} `json:"factory_name,omitempty"`
	Location interface{} `json:"location,omitempty"`
	ClientInfo interface{} `json:"client_info,omitempty"`
}
// FederatedClientRegisterResponse
type FederatedClientRegisterResponse struct {
	ClientId string `json:"client_id"`
	Status string `json:"status"`
	Message string `json:"message"`
	RegisteredAt time.Time `json:"registered_at"`
}
// FederatedClientStatusResponse
type FederatedClientStatusResponse struct {
	ClientId string `json:"client_id"`
	FactoryId string `json:"factory_id"`
	ModelType interface{} `json:"model_type"`
	NodeId interface{} `json:"node_id"`
	CurrentRound int `json:"current_round"`
	HasGlobalModel bool `json:"has_global_model"`
	HasLocalModel bool `json:"has_local_model"`
	TrainingCount int `json:"training_count"`
	PrivacyMechanism string `json:"privacy_mechanism"`
	UpdateType string `json:"update_type"`
	TwoLevelArchEnabled bool `json:"two_level_arch_enabled"`
	LastUpdateTime interface{} `json:"last_update_time"`
}
// FederatedGlobalModelRequest
type FederatedGlobalModelRequest struct {
	ClientId string `json:"client_id"`
	ModelType string `json:"model_type"`
	NodeId string `json:"node_id"`
}
// FederatedGlobalModelResponse
type FederatedGlobalModelResponse struct {
	ModelType string `json:"model_type"`
	NodeId string `json:"node_id"`
	RoundId int `json:"round_id"`
	Version interface{} `json:"version,omitempty"`
	Weights map[string]interface{} `json:"weights"`
	ServerTime time.Time `json:"server_time"`
	EnableTwoLevelArch bool `json:"enable_two_level_arch,omitempty"`
	Metrics interface{} `json:"metrics,omitempty"`
}
// FederatedLocalTrainRequest
type FederatedLocalTrainRequest struct {
	ClientId string `json:"client_id"`
	ModelType string `json:"model_type"`
	NodeId string `json:"node_id"`
	LocalEpochs interface{} `json:"local_epochs,omitempty"`
	FineTune bool `json:"fine_tune,omitempty"`
	TrainData interface{} `json:"train_data,omitempty"`
	TrainLabels interface{} `json:"train_labels,omitempty"`
}
// FederatedLocalTrainResponse
type FederatedLocalTrainResponse struct {
	ClientId string `json:"client_id"`
	ModelType string `json:"model_type"`
	NodeId string `json:"node_id"`
	Status string `json:"status"`
	Message string `json:"message"`
	NumSamples int `json:"num_samples"`
	TrainingTime float64 `json:"training_time"`
	Metrics map[string]float64 `json:"metrics"`
}
// FederatedModelHistoryResponse
type FederatedModelHistoryResponse struct {
	ModelType string `json:"model_type"`
	NodeId string `json:"node_id"`
	History []map[string]interface{} `json:"history"`
}
// FederatedPrivacyConfig
type FederatedPrivacyConfig struct {
	Mechanism string `json:"mechanism,omitempty"`
	Epsilon float64 `json:"epsilon,omitempty"`
	Delta float64 `json:"delta,omitempty"`
	NoiseScale float64 `json:"noise_scale,omitempty"`
	ClipNorm float64 `json:"clip_norm,omitempty"`
	NumParties int `json:"num_parties,omitempty"`
	SecretShareThreshold int `json:"secret_share_threshold,omitempty"`
}
// FederatedRoundAggregateRequest
type FederatedRoundAggregateRequest struct {
	ModelType string `json:"model_type"`
	NodeId string `json:"node_id"`
}
// FederatedRoundAggregateResponse
type FederatedRoundAggregateResponse struct {
	RoundId int `json:"round_id"`
	ModelType string `json:"model_type"`
	NodeId string `json:"node_id"`
	Status string `json:"status"`
	Message string `json:"message"`
	NumClientsAggregated int `json:"num_clients_aggregated"`
	Version interface{} `json:"version,omitempty"`
	Metrics interface{} `json:"metrics,omitempty"`
	AggregatedAt time.Time `json:"aggregated_at"`
}
// FederatedRoundStartRequest
type FederatedRoundStartRequest struct {
	ModelType string `json:"model_type"`
	NodeId string `json:"node_id"`
	ExpectedClients interface{} `json:"expected_clients,omitempty"`
}
// FederatedRoundStartResponse
type FederatedRoundStartResponse struct {
	RoundId int `json:"round_id"`
	ModelType string `json:"model_type"`
	NodeId string `json:"node_id"`
	Status string `json:"status"`
	ExpectedClients []string `json:"expected_clients"`
	StartedAt time.Time `json:"started_at"`
}
// FederatedServerStatusResponse
type FederatedServerStatusResponse struct {
	RegisteredClients int `json:"registered_clients"`
	ActiveClients int `json:"active_clients"`
	TotalRounds int `json:"total_rounds"`
	CompletedRounds int `json:"completed_rounds"`
	FailedRounds int `json:"failed_rounds"`
	AggregationStrategy string `json:"aggregation_strategy"`
	ManagedModels []string `json:"managed_models"`
	CurrentRound interface{} `json:"current_round,omitempty"`
}
// FederatedUpdateUploadRequest
type FederatedUpdateUploadRequest struct {
	ClientId string `json:"client_id"`
	ModelType string `json:"model_type"`
	NodeId string `json:"node_id"`
	RoundId int `json:"round_id"`
	Weights map[string]interface{} `json:"weights"`
	NumSamples int `json:"num_samples"`
	Metrics interface{} `json:"metrics,omitempty"`
	Encrypted bool `json:"encrypted,omitempty"`
	EncryptedUpdate interface{} `json:"encrypted_update,omitempty"`
	UpdateType string `json:"update_type,omitempty"`
}
// FederatedUpdateUploadResponse
type FederatedUpdateUploadResponse struct {
	ClientId string `json:"client_id"`
	RoundId int `json:"round_id"`
	Status string `json:"status"`
	Message string `json:"message"`
	ReceivedAt time.Time `json:"received_at"`
}
// FilteredDataResultSchema
type FilteredDataResultSchema struct {
	OriginalCount int `json:"original_count"`
	FilteredCount int `json:"filtered_count"`
	RemovedIndices []int `json:"removed_indices"`
	RemovalReasons map[string]string `json:"removal_reasons"`
	FilterStrategy string `json:"filter_strategy"`
	ConfidenceMultiplier float64 `json:"confidence_multiplier"`
	AdjustedConfidence interface{} `json:"adjusted_confidence,omitempty"`
}
// FlangeHealthIndexSchema
type FlangeHealthIndexSchema struct {
	FlangeId string `json:"flange_id"`
	FlangeName interface{} `json:"flange_name,omitempty"`
	HiScore float64 `json:"hi_score"`
	HiLevel string `json:"hi_level"`
	WorstBoltHi float64 `json:"worst_bolt_hi"`
	WorstBoltId string `json:"worst_bolt_id"`
	AverageBoltHi float64 `json:"average_bolt_hi"`
	MedianBoltHi float64 `json:"median_bolt_hi"`
	DegradationRate float64 `json:"degradation_rate"`
	BoltCount int `json:"bolt_count"`
	HealthyBoltCount int `json:"healthy_bolt_count"`
	WarningBoltCount int `json:"warning_bolt_count"`
	CriticalBoltCount int `json:"critical_bolt_count"`
	BoltsHealth []BoltHealthIndexSchema `json:"bolts_health"`
	Trend interface{} `json:"trend,omitempty"`
	CalculateTime time.Time `json:"calculate_time"`
}
// Attributes:
// id:
// data:
type FlangePredictionRequest struct {
	FlangeId string `json:"flange_id"`
	Data [][][]interface{} `json:"data"`
}
// FlangePredictionResponse
type FlangePredictionResponse struct {
	FlangeId string `json:"flange_id"`
	Status string `json:"status"`
	StatusCode int `json:"status_code"`
	Confidence float64 `json:"confidence"`
	RiskScore float64 `json:"risk_score"`
	RiskLevel string `json:"risk_level"`
	BoltCount int `json:"bolt_count"`
	AttentionWeights interface{} `json:"attention_weights,omitempty"`
	Diagnosis string `json:"diagnosis"`
	Recommendations []string `json:"recommendations"`
	PredictionTime time.Time `json:"prediction_time"`
	CorrelationMatrix interface{} `json:"correlation_matrix,omitempty"`
	CausalGraph interface{} `json:"causal_graph,omitempty"`
	LeadingBolts interface{} `json:"leading_bolts,omitempty"`
	PropagationPaths interface{} `json:"propagation_paths,omitempty"`
	RootCauseAnalysis interface{} `json:"root_cause_analysis,omitempty"`
	RootCauseMeasures interface{} `json:"root_cause_measures,omitempty"`
	ModelVersion interface{} `json:"model_version,omitempty"`
	ShadowVersion interface{} `json:"shadow_version,omitempty"`
	ShadowResult interface{} `json:"shadow_result,omitempty"`
	FaultDetail interface{} `json:"fault_detail,omitempty"`
}
// Focal Loss
type FocalLossConfig struct {
	Enabled bool `json:"enabled,omitempty"`
	Gamma float64 `json:"gamma,omitempty"`
	Alpha interface{} `json:"alpha,omitempty"`
}
// HI
type HiCarbonDualItemSchema struct {
	NodeId string `json:"node_id"`
	NodeType string `json:"node_type"`
	NodeName string `json:"node_name"`
	HiScore float64 `json:"hi_score"`
	HiLevel string `json:"hi_level"`
	HiTrend string `json:"hi_trend"`
	DegradationRatePerMonth float64 `json:"degradation_rate_per_month"`
	EstimatedLeakageRateM3Hour float64 `json:"estimated_leakage_rate_m3_hour"`
	MonthlyCarbonIncrementKg float64 `json:"monthly_carbon_increment_kg"`
	CarbonRiskLevel string `json:"carbon_risk_level"`
	CarbonTrend string `json:"carbon_trend"`
}
// HI rollup
type HiCarbonDualViewRequest struct {
	Nodes []map[string]interface{} `json:"nodes"`
}
// HI rollup
type HiCarbonDualViewResponse struct {
	ReportMonth string `json:"report_month"`
	TotalNodes int `json:"total_nodes"`
	Items []HiCarbonDualItemSchema `json:"items"`
	GeneratedAt time.Time `json:"generated_at"`
}
// HTTPValidationError
type HttpValidationError struct {
	Detail []ValidationError `json:"detail,omitempty"`
}
// HealthComponentStatus
type HealthComponentStatus struct {
	Status string `json:"status"`
	Message interface{} `json:"message,omitempty"`
}
// HealthIndexBatchCalculateRequest
type HealthIndexBatchCalculateRequest struct {
	Nodes []map[string]interface{} `json:"nodes"`
	WorkingCondition interface{} `json:"working_condition,omitempty"`
	SaveToDb bool `json:"save_to_db,omitempty"`
}
// HealthIndexBatchResponse
type HealthIndexBatchResponse struct {
	TotalCount int `json:"total_count"`
	SuccessCount int `json:"success_count"`
	FailedCount int `json:"failed_count"`
	Results []map[string]interface{} `json:"results"`
	CalculateTime time.Time `json:"calculate_time"`
}
// HealthIndexCalculateRequest
type HealthIndexCalculateRequest struct {
	NodeId string `json:"node_id"`
	NodeType string `json:"node_type"`
	Data interface{} `json:"data,omitempty"`
	WorkingCondition interface{} `json:"working_condition,omitempty"`
	IncludeHistory bool `json:"include_history,omitempty"`
	SaveToDb bool `json:"save_to_db,omitempty"`
}
// HealthIndexDetailSchema
type HealthIndexDetailSchema struct {
	HiScore float64 `json:"hi_score"`
	HiLevel string `json:"hi_level"`
	Factors []HealthIndexFactorSchema `json:"factors"`
	PreloadStabilityScore float64 `json:"preload_stability_score"`
	AlertFrequencyScore float64 `json:"alert_frequency_score"`
	FaultHistoryScore float64 `json:"fault_history_score"`
	EnvironmentalStressScore float64 `json:"environmental_stress_score"`
	ServiceAgeScore float64 `json:"service_age_score"`
	Trend interface{} `json:"trend,omitempty"`
	TrendRate interface{} `json:"trend_rate,omitempty"`
	CalculateTime time.Time `json:"calculate_time"`
}
// HealthIndexFactorSchema
type HealthIndexFactorSchema struct {
	FactorName string `json:"factor_name"`
	FactorCode string `json:"factor_code"`
	Score float64 `json:"score"`
	Weight float64 `json:"weight"`
	Contribution float64 `json:"contribution"`
	Description interface{} `json:"description,omitempty"`
}
// HealthIndexHistoryResponse
type HealthIndexHistoryResponse struct {
	NodeId string `json:"node_id"`
	NodeType string `json:"node_type"`
	Total int `json:"total"`
	History []map[string]interface{} `json:"history"`
	TrendAnalysis interface{} `json:"trend_analysis,omitempty"`
}
// HealthIndexResponse
type HealthIndexResponse struct {
	NodeId string `json:"node_id"`
	NodeType string `json:"node_type"`
	HealthData *HealthIndexDetailSchema `json:"health_data"`
	Saved bool `json:"saved"`
	CalculateTime time.Time `json:"calculate_time"`
}
// HealthResponse
type HealthResponse struct {
	Status string `json:"status,omitempty"`
	Version string `json:"version"`
	Timestamp time.Time `json:"timestamp"`
	Components interface{} `json:"components,omitempty"`
}
// HealthRollupRequest
type HealthRollupRequest struct {
	LineId string `json:"line_id"`
	LineName interface{} `json:"line_name,omitempty"`
	LineType string `json:"line_type,omitempty"`
	ReportDate interface{} `json:"report_date,omitempty"`
	IncludeDetails bool `json:"include_details,omitempty"`
}
// HealthRollupResponse
type HealthRollupResponse struct {
	ReportId interface{} `json:"report_id,omitempty"`
	RollupData *ProductionLineHealthRollupSchema `json:"rollup_data"`
	Saved bool `json:"saved"`
}
// IncrementalTrainingConfig
type IncrementalTrainingConfig struct {
	Enabled bool `json:"enabled,omitempty"`
	FreezeLayers interface{} `json:"freeze_layers,omitempty"`
	BaseModelVersion interface{} `json:"base_model_version,omitempty"`
}
// JobExecutionLogListResponse
type JobExecutionLogListResponse struct {
	Total int `json:"total"`
	Items []JobExecutionLogSchema `json:"items"`
}
// JobExecutionLogSchema
type JobExecutionLogSchema struct {
	Id int `json:"id"`
	JobName string `json:"job_name"`
	JobType string `json:"job_type"`
	TriggerType string `json:"trigger_type"`
	Status string `json:"status"`
	StartTime time.Time `json:"start_time"`
	EndTime interface{} `json:"end_time,omitempty"`
	DurationSeconds interface{} `json:"duration_seconds,omitempty"`
	TotalNodes int `json:"total_nodes,omitempty"`
	SuccessCount int `json:"success_count,omitempty"`
	FailedCount int `json:"failed_count,omitempty"`
	SkippedCount int `json:"skipped_count,omitempty"`
	ShardIndex interface{} `json:"shard_index,omitempty"`
	ShardTotal interface{} `json:"shard_total,omitempty"`
	BoltIdMin interface{} `json:"bolt_id_min,omitempty"`
	BoltIdMax interface{} `json:"bolt_id_max,omitempty"`
	InstanceId interface{} `json:"instance_id,omitempty"`
	ErrorSummary interface{} `json:"error_summary,omitempty"`
	ErrorDetails interface{} `json:"error_details,omitempty"`
	CreateTime time.Time `json:"create_time"`
}
// KnowledgeCaseCreateRequest
type KnowledgeCaseCreateRequest struct {
	CaseTitle string `json:"case_title"`
	NodeType interface{} `json:"node_type,omitempty"`
	NodeId interface{} `json:"node_id,omitempty"`
	FaultType interface{} `json:"fault_type,omitempty"`
	FaultLevel interface{} `json:"fault_level,omitempty"`
	WorkingCondition interface{} `json:"working_condition,omitempty"`
	SensorData interface{} `json:"sensor_data,omitempty"`
	SensorFeatures interface{} `json:"sensor_features,omitempty"`
	Diagnosis interface{} `json:"diagnosis,omitempty"`
	RootCause interface{} `json:"root_cause,omitempty"`
	TreatmentPlan interface{} `json:"treatment_plan,omitempty"`
	EffectEvaluation interface{} `json:"effect_evaluation,omitempty"`
	SourceAlertId interface{} `json:"source_alert_id,omitempty"`
	SourcePredictionId interface{} `json:"source_prediction_id,omitempty"`
	Tags interface{} `json:"tags,omitempty"`
	CreatorId interface{} `json:"creator_id,omitempty"`
	CreatorName interface{} `json:"creator_name,omitempty"`
	TenantId interface{} `json:"tenant_id,omitempty"`
	SubmitForReview bool `json:"submit_for_review,omitempty"`
}
// KnowledgeCaseListResponse
type KnowledgeCaseListResponse struct {
	Total int `json:"total"`
	Items []KnowledgeCaseResponse `json:"items"`
}
// KnowledgeCaseResponse
type KnowledgeCaseResponse struct {
	Id int `json:"id"`
	CaseNo string `json:"case_no"`
	CaseTitle string `json:"case_title"`
	NodeType interface{} `json:"node_type,omitempty"`
	NodeId interface{} `json:"node_id,omitempty"`
	FaultType interface{} `json:"fault_type,omitempty"`
	FaultLevel interface{} `json:"fault_level,omitempty"`
	WorkingCondition interface{} `json:"working_condition,omitempty"`
	SensorFeatures interface{} `json:"sensor_features,omitempty"`
	Diagnosis interface{} `json:"diagnosis,omitempty"`
	RootCause interface{} `json:"root_cause,omitempty"`
	TreatmentPlan interface{} `json:"treatment_plan,omitempty"`
	EffectEvaluation interface{} `json:"effect_evaluation,omitempty"`
	EffectivenessScore interface{} `json:"effectiveness_score,omitempty"`
	Status string `json:"status"`
	Version int `json:"version"`
	TenantId interface{} `json:"tenant_id,omitempty"`
	CreatorId interface{} `json:"creator_id,omitempty"`
	CreatorName interface{} `json:"creator_name,omitempty"`
	ReviewerId interface{} `json:"reviewer_id,omitempty"`
	ReviewerName interface{} `json:"reviewer_name,omitempty"`
	ReviewTime interface{} `json:"review_time,omitempty"`
	ReviewComment interface{} `json:"review_comment,omitempty"`
	SourceAlertId interface{} `json:"source_alert_id,omitempty"`
	SourcePredictionId interface{} `json:"source_prediction_id,omitempty"`
	Tags interface{} `json:"tags,omitempty"`
	SimilarityScore interface{} `json:"similarity_score,omitempty"`
	CreateTime time.Time `json:"create_time"`
	UpdateTime time.Time `json:"update_time"`
}
// KnowledgeCaseUpdateRequest
type KnowledgeCaseUpdateRequest struct {
	CaseTitle interface{} `json:"case_title,omitempty"`
	FaultType interface{} `json:"fault_type,omitempty"`
	FaultLevel interface{} `json:"fault_level,omitempty"`
	WorkingCondition interface{} `json:"working_condition,omitempty"`
	SensorData interface{} `json:"sensor_data,omitempty"`
	SensorFeatures interface{} `json:"sensor_features,omitempty"`
	Diagnosis interface{} `json:"diagnosis,omitempty"`
	RootCause interface{} `json:"root_cause,omitempty"`
	TreatmentPlan interface{} `json:"treatment_plan,omitempty"`
	EffectEvaluation interface{} `json:"effect_evaluation,omitempty"`
	Tags interface{} `json:"tags,omitempty"`
	ChangeSummary interface{} `json:"change_summary,omitempty"`
	SubmitForReview bool `json:"submit_for_review,omitempty"`
	OperatorId interface{} `json:"operator_id,omitempty"`
	OperatorName interface{} `json:"operator_name,omitempty"`
}
// LrSchedulerConfig
type LrSchedulerConfig struct {
	Type string `json:"type,omitempty"`
	Factor interface{} `json:"factor,omitempty"`
	Patience interface{} `json:"patience,omitempty"`
	MinLr interface{} `json:"min_lr,omitempty"`
	StepSize interface{} `json:"step_size,omitempty"`
	Gamma interface{} `json:"gamma,omitempty"`
	TMax interface{} `json:"t_max,omitempty"`
	EtaMin interface{} `json:"eta_min,omitempty"`
}
// CSV
type LabelImportCsvRequest struct {
	CsvPath string `json:"csv_path"`
	NodeType string `json:"node_type"`
	LabelColumn interface{} `json:"label_column,omitempty"`
	IdColumn interface{} `json:"id_column,omitempty"`
	DataColumn interface{} `json:"data_column,omitempty"`
	TimestampColumn interface{} `json:"timestamp_column,omitempty"`
	LabelerName interface{} `json:"labeler_name,omitempty"`
	AutoApprove bool `json:"auto_approve,omitempty"`
	SkipErrors bool `json:"skip_errors,omitempty"`
}
// LabelImportDbRequest
type LabelImportDbRequest struct {
	SourceTable string `json:"source_table"`
	NodeType string `json:"node_type"`
	IdField string `json:"id_field"`
	LabelField string `json:"label_field"`
	DataField interface{} `json:"data_field,omitempty"`
	TimestampField interface{} `json:"timestamp_field,omitempty"`
	WhereClause interface{} `json:"where_clause,omitempty"`
	LabelerName interface{} `json:"labeler_name,omitempty"`
	AutoApprove bool `json:"auto_approve,omitempty"`
}
// LabelImportFileItemSchema
type LabelImportFileItemSchema struct {
	Filename string `json:"filename"`
	Path string `json:"path"`
	SizeBytes int `json:"size_bytes,omitempty"`
	ModifiedTime interface{} `json:"modified_time,omitempty"`
}
// LabelImportFileListResponse
type LabelImportFileListResponse struct {
	Total int `json:"total"`
	Items []LabelImportFileItemSchema `json:"items,omitempty"`
}
// LabelImportResponse
type LabelImportResponse struct {
	Status string `json:"status"`
	Message string `json:"message"`
	Result interface{} `json:"result,omitempty"`
}
// LabelImportResultSchema
type LabelImportResultSchema struct {
	Total int `json:"total,omitempty"`
	Imported int `json:"imported,omitempty"`
	Skipped int `json:"skipped,omitempty"`
	Duplicates int `json:"duplicates,omitempty"`
	Errors int `json:"errors,omitempty"`
	ErrorDetails interface{} `json:"error_details,omitempty"`
}
// Leader
type LeaderStatusSchema struct {
	LeaderKey string `json:"leader_key"`
	LeaderId string `json:"leader_id"`
	LeaseExpireTime time.Time `json:"lease_expire_time"`
	LastHeartbeat time.Time `json:"last_heartbeat"`
	Version int `json:"version"`
	IsExpired bool `json:"is_expired"`
	IsCurrentInstance bool `json:"is_current_instance"`
}
// LeadingBoltSchema
type LeadingBoltSchema struct {
	BoltId string `json:"bolt_id"`
	Index int `json:"index"`
	LeadingScore float64 `json:"leading_score"`
	OutDegree int `json:"out_degree"`
	InDegree int `json:"in_degree"`
	NetDegree int `json:"net_degree"`
	OutStrength float64 `json:"out_strength"`
	InStrength float64 `json:"in_strength"`
	NetStrength float64 `json:"net_strength"`
	TrendLeadership float64 `json:"trend_leadership"`
	IsLeading bool `json:"is_leading"`
}
// LeakageParamsSchema
type LeakageParamsSchema struct {
	BaseLeakageRateM3PerHour float64 `json:"base_leakage_rate_m3_per_hour,omitempty"`
	CriticalLeakageThreshold float64 `json:"critical_leakage_threshold,omitempty"`
	PreloadLeakageSensitivity float64 `json:"preload_leakage_sensitivity,omitempty"`
	SealAgingFactorPerYear float64 `json:"seal_aging_factor_per_year,omitempty"`
	PressureSensitivity float64 `json:"pressure_sensitivity,omitempty"`
}
// ModelInfoResponse
type ModelInfoResponse struct {
	ModelType string `json:"model_type"`
	NodeId string `json:"node_id"`
	IsTrained bool `json:"is_trained"`
	LastTrainingTime interface{} `json:"last_training_time"`
	TrainingSamples interface{} `json:"training_samples"`
	ValidationAccuracy interface{} `json:"validation_accuracy"`
	Version interface{} `json:"version,omitempty"`
	FileHash interface{} `json:"file_hash,omitempty"`
	CreateTime interface{} `json:"create_time,omitempty"`
	TrainingSessionId interface{} `json:"training_session_id,omitempty"`
	Description interface{} `json:"description,omitempty"`
	ValidationSamples interface{} `json:"validation_samples,omitempty"`
	IsIncremental interface{} `json:"is_incremental,omitempty"`
	ParentVersion interface{} `json:"parent_version,omitempty"`
	Metrics interface{} `json:"metrics,omitempty"`
	VersionHistory interface{} `json:"version_history,omitempty"`
}
// /
type ModelVersionActivateRequest struct {
	ModelType string `json:"model_type"`
	NodeId string `json:"node_id"`
	Version string `json:"version"`
}
// ModelVersionCompareRequest
type ModelVersionCompareRequest struct {
	Version1 string `json:"version1"`
	Version2 string `json:"version2"`
}
// ModelVersionCompareResponse
type ModelVersionCompareResponse struct {
	ModelId string `json:"model_id"`
	Version1 string `json:"version1"`
	Version2 string `json:"version2"`
	MetricsComparison map[string]interface{} `json:"metrics_comparison"`
	ConfigDiff map[string]interface{} `json:"config_diff"`
}
// ModelVersionListResponse
type ModelVersionListResponse struct {
	ModelId string `json:"model_id"`
	ModelType string `json:"model_type"`
	Versions []ModelVersionSchema `json:"versions"`
}
// ModelVersionRollbackRequest
type ModelVersionRollbackRequest struct {
	ModelType string `json:"model_type"`
	NodeId string `json:"node_id"`
	Version interface{} `json:"version,omitempty"`
}
// ModelVersionSchema
type ModelVersionSchema struct {
	Version string `json:"version"`
	ModelId string `json:"model_id"`
	ModelType string `json:"model_type"`
	CreatedAt time.Time `json:"created_at"`
	FilePath string `json:"file_path"`
	FileHash string `json:"file_hash"`
	Metrics map[string]float64 `json:"metrics,omitempty"`
	Config map[string]interface{} `json:"config,omitempty"`
	IsActive bool `json:"is_active,omitempty"`
	Description string `json:"description,omitempty"`
}
// MonthlyForecastRequest
type MonthlyForecastRequest struct {
	NodeId string `json:"node_id"`
	NodeType string `json:"node_type"`
	ForecastDays int `json:"forecast_days,omitempty"`
}
// MonthlyForecastResponse
type MonthlyForecastResponse struct {
	NodeId string `json:"node_id"`
	NodeType string `json:"node_type"`
	PwType string `json:"pw_type"`
	FaultType interface{} `json:"fault_type"`
	BeginTime interface{} `json:"begin_time"`
	EndTime interface{} `json:"end_time"`
	Confidence float64 `json:"confidence"`
	RecMeasures string `json:"rec_measures"`
	ForecastDates []time.Time `json:"forecast_dates"`
	ForecastValues []float64 `json:"forecast_values"`
}
// MTTR
type MttrTrendPoint struct {
	Date string `json:"date"`
	MttrHours interface{} `json:"mttr_hours,omitempty"`
	WorkOrderCount int `json:"work_order_count,omitempty"`
}
// MTTR
type MttrTrendResponse struct {
	Trend []MttrTrendPoint `json:"trend"`
	OverallMttrHours interface{} `json:"overall_mttr_hours,omitempty"`
}
// Attributes:
// name:  preload / temperature / humidity / vibration / torque / pressure
// unit:
// description:
type MultivariateChannelSchema struct {
	Name string `json:"name"`
	Unit interface{} `json:"unit,omitempty"`
	Description interface{} `json:"description,omitempty"`
}
// NotificationChannelCreate
type NotificationChannelCreate struct {
	ChannelType string `json:"channel_type"`
	ChannelName interface{} `json:"channel_name,omitempty"`
	Config interface{} `json:"config,omitempty"`
	Enabled bool `json:"enabled,omitempty"`
	IsDefault bool `json:"is_default,omitempty"`
}
// NotificationChannelResponse
type NotificationChannelResponse struct {
	ChannelType string `json:"channel_type"`
	ChannelName interface{} `json:"channel_name,omitempty"`
	Config interface{} `json:"config,omitempty"`
	Enabled bool `json:"enabled,omitempty"`
	IsDefault bool `json:"is_default,omitempty"`
	Id int `json:"id"`
	CreateTime time.Time `json:"create_time"`
	UpdateTime time.Time `json:"update_time"`
}
// NotificationChannelUpdate
type NotificationChannelUpdate struct {
	ChannelType interface{} `json:"channel_type,omitempty"`
	ChannelName interface{} `json:"channel_name,omitempty"`
	Config interface{} `json:"config,omitempty"`
	Enabled interface{} `json:"enabled,omitempty"`
	IsDefault interface{} `json:"is_default,omitempty"`
}
// NotificationLogResponse
type NotificationLogResponse struct {
	Id int `json:"id"`
	AlertId interface{} `json:"alert_id,omitempty"`
	ChannelType interface{} `json:"channel_type,omitempty"`
	SubscriberId interface{} `json:"subscriber_id,omitempty"`
	SubscriberName interface{} `json:"subscriber_name,omitempty"`
	Target interface{} `json:"target,omitempty"`
	Title interface{} `json:"title,omitempty"`
	Content interface{} `json:"content,omitempty"`
	Status string `json:"status"`
	ErrorMessage interface{} `json:"error_message,omitempty"`
	RetryCount int `json:"retry_count,omitempty"`
	SendTime time.Time `json:"send_time"`
}
// OrgNodeCreateRequest
type OrgNodeCreateRequest struct {
	TenantId int `json:"tenant_id"`
	ParentId interface{} `json:"parent_id,omitempty"`
	NodeCode interface{} `json:"node_code,omitempty"`
	NodeName string `json:"node_name"`
	NodeType string `json:"node_type"`
	SortOrder int `json:"sort_order,omitempty"`
	ExtraInfo interface{} `json:"extra_info,omitempty"`
}
// OrgNodeResponse
type OrgNodeResponse struct {
	Id int `json:"id"`
	TenantId int `json:"tenant_id"`
	ParentId interface{} `json:"parent_id,omitempty"`
	NodeCode interface{} `json:"node_code,omitempty"`
	NodeName string `json:"node_name"`
	NodeType string `json:"node_type"`
	Path interface{} `json:"path,omitempty"`
	Level int `json:"level"`
	SortOrder int `json:"sort_order"`
	ExtraInfo interface{} `json:"extra_info,omitempty"`
	Status string `json:"status"`
	CreateTime time.Time `json:"create_time"`
	UpdateTime time.Time `json:"update_time"`
	Children interface{} `json:"children,omitempty"`
}
// OrgNodeUpdateRequest
type OrgNodeUpdateRequest struct {
	NodeName interface{} `json:"node_name,omitempty"`
	NodeCode interface{} `json:"node_code,omitempty"`
	SortOrder interface{} `json:"sort_order,omitempty"`
	ExtraInfo interface{} `json:"extra_info,omitempty"`
	Status interface{} `json:"status,omitempty"`
}
// OrgTreeResponse
type OrgTreeResponse struct {
	TenantId int `json:"tenant_id"`
	Nodes []OrgNodeResponse `json:"nodes"`
}
// /
type PeriodicReportResponse struct {
	ReportType string `json:"report_type"`
	NodeId string `json:"node_id"`
	NodeType string `json:"node_type"`
	PeriodStart time.Time `json:"period_start"`
	PeriodEnd time.Time `json:"period_end"`
	DiagnosisSummary string `json:"diagnosis_summary"`
	RecommendedActions []string `json:"recommended_actions"`
	UrgencyLevel string `json:"urgency_level"`
	Statistics *ReportStatisticsSchema `json:"statistics"`
	GeneratedAt time.Time `json:"generated_at"`
	Model string `json:"model"`
	IsFallback bool `json:"is_fallback,omitempty"`
}
// PredictionCompareListResponse
type PredictionCompareListResponse struct {
	Total int `json:"total"`
	Items []PredictionCompareResponse `json:"items"`
}
// PredictionCompareResponse
type PredictionCompareResponse struct {
	Id int `json:"id"`
	WorkOrderId int `json:"work_order_id"`
	RetestId interface{} `json:"retest_id,omitempty"`
	OriginalPredictionId interface{} `json:"original_prediction_id,omitempty"`
	RetestPredictionId interface{} `json:"retest_prediction_id,omitempty"`
	OriginalStatus interface{} `json:"original_status,omitempty"`
	RetestStatus interface{} `json:"retest_status,omitempty"`
	OriginalRiskScore interface{} `json:"original_risk_score,omitempty"`
	RetestRiskScore interface{} `json:"retest_risk_score,omitempty"`
	OriginalConfidence interface{} `json:"original_confidence,omitempty"`
	RetestConfidence interface{} `json:"retest_confidence,omitempty"`
	RiskChange interface{} `json:"risk_change,omitempty"`
	RiskDelta interface{} `json:"risk_delta,omitempty"`
	StatusMatch interface{} `json:"status_match,omitempty"`
	IsFalsePositive interface{} `json:"is_false_positive,omitempty"`
	IsRecurring interface{} `json:"is_recurring,omitempty"`
	ComparisonDetail interface{} `json:"comparison_detail,omitempty"`
	CreateTime time.Time `json:"create_time"`
}
// ProblemSensorRankingSchema
type ProblemSensorRankingSchema struct {
	Rank int `json:"rank"`
	SensorId string `json:"sensor_id"`
	QualityScore float64 `json:"quality_score"`
	QualityLevel string `json:"quality_level"`
	ProblemTypes []string `json:"problem_types"`
	ViolationCount int `json:"violation_count"`
	AnomalyCount int `json:"anomaly_count"`
	CollectionAnomalyRatio float64 `json:"collection_anomaly_ratio"`
	Trend string `json:"trend"`
}
// /
type ProductionLineHealthRollupSchema struct {
	LineId string `json:"line_id"`
	LineName string `json:"line_name"`
	LineType string `json:"line_type"`
	OverallHi float64 `json:"overall_hi"`
	OverallLevel string `json:"overall_level"`
	TotalFlangeCount int `json:"total_flange_count"`
	TotalBoltCount int `json:"total_bolt_count"`
	HealthyFlangeCount int `json:"healthy_flange_count"`
	WarningFlangeCount int `json:"warning_flange_count"`
	CriticalFlangeCount int `json:"critical_flange_count"`
	HealthyBoltCount int `json:"healthy_bolt_count"`
	WarningBoltCount int `json:"warning_bolt_count"`
	CriticalBoltCount int `json:"critical_bolt_count"`
	WorstFlangeHi float64 `json:"worst_flange_hi"`
	WorstFlangeId string `json:"worst_flange_id"`
	AverageDegradationRate float64 `json:"average_degradation_rate"`
	FlangesHealth []FlangeHealthIndexSchema `json:"flanges_health"`
	RiskSummary map[string]interface{} `json:"risk_summary"`
	MaintenancePriorities []map[string]interface{} `json:"maintenance_priorities"`
	ReportDate time.Time `json:"report_date"`
	GenerateTime time.Time `json:"generate_time"`
}
// PropagationPathSchema
type PropagationPathSchema struct {
	Path []string `json:"path"`
	PathIndices []int `json:"path_indices"`
	Depth int `json:"depth"`
	TotalWeight float64 `json:"total_weight"`
	AvgWeight float64 `json:"avg_weight"`
}
// PropagationPathsSchema
type PropagationPathsSchema struct {
	SourceBolt string `json:"source_bolt"`
	SourceIdx int `json:"source_idx"`
	Paths []PropagationPathSchema `json:"paths"`
	TotalPathCount int `json:"total_path_count"`
	ReachableBolts []string `json:"reachable_bolts"`
	PropagationDistance map[string]interface{} `json:"propagation_distance"`
	MaxDepth int `json:"max_depth"`
}
// QualityCheckResultSchema
type QualityCheckResultSchema struct {
	SensorId string `json:"sensor_id"`
	TotalPoints int `json:"total_points"`
	ValidPoints int `json:"valid_points"`
	OverallScore float64 `json:"overall_score"`
	RuleScores map[string]float64 `json:"rule_scores"`
	Violations []RuleViolationSchema `json:"violations"`
	ViolationCount int `json:"violation_count"`
	CheckTime time.Time `json:"check_time"`
}
// QualityDimensionScoreSchema
type QualityDimensionScoreSchema struct {
	Dimension string `json:"dimension"`
	Score float64 `json:"score"`
	Weight float64 `json:"weight"`
	ContributingRules []string `json:"contributing_rules"`
}
// QualityEvaluationResponse
type QualityEvaluationResponse struct {
	SensorId string `json:"sensor_id"`
	QualityCheck *QualityCheckResultSchema `json:"quality_check"`
	QualityScore *SensorQualityScoreSchema `json:"quality_score"`
	FilterResult *FilteredDataResultSchema `json:"filter_result"`
	AnomalyClassification interface{} `json:"anomaly_classification,omitempty"`
	EvaluateTime time.Time `json:"evaluate_time"`
}
// QualityReportRequest
type QualityReportRequest struct {
	ReportDate interface{} `json:"report_date,omitempty"`
	SensorIds interface{} `json:"sensor_ids,omitempty"`
	SaveToDb bool `json:"save_to_db,omitempty"`
}
// QuotaResponse
type QuotaResponse struct {
	TenantId int `json:"tenant_id"`
	MaxModels int `json:"max_models"`
	MaxApiCallsPerDay int `json:"max_api_calls_per_day"`
	MaxStorageMb int `json:"max_storage_mb"`
	MaxUsers int `json:"max_users"`
	MaxOrgNodes int `json:"max_org_nodes"`
	CurrentModelCount int `json:"current_model_count"`
	CurrentApiCallsToday int `json:"current_api_calls_today"`
	CurrentStorageMb float64 `json:"current_storage_mb"`
	CurrentUserCount int `json:"current_user_count"`
	CurrentOrgNodeCount int `json:"current_org_node_count"`
	CreateTime time.Time `json:"create_time"`
	UpdateTime time.Time `json:"update_time"`
}
// QuotaUpdateRequest
type QuotaUpdateRequest struct {
	MaxModels interface{} `json:"max_models,omitempty"`
	MaxApiCallsPerDay interface{} `json:"max_api_calls_per_day,omitempty"`
	MaxStorageMb interface{} `json:"max_storage_mb,omitempty"`
	MaxUsers interface{} `json:"max_users,omitempty"`
	MaxOrgNodes interface{} `json:"max_org_nodes,omitempty"`
}
// RUL
type RulPredictionPointSchema struct {
	Date time.Time `json:"date"`
	PredictedHi float64 `json:"predicted_hi"`
	LowerBound float64 `json:"lower_bound"`
	UpperBound float64 `json:"upper_bound"`
}
// RUL
type RulPredictionRequest struct {
	NodeId string `json:"node_id"`
	NodeType string `json:"node_type"`
	ForecastDays int `json:"forecast_days,omitempty"`
	FailureThreshold float64 `json:"failure_threshold,omitempty"`
	WarningThreshold float64 `json:"warning_threshold,omitempty"`
	ModelType interface{} `json:"model_type,omitempty"`
	UseHistoryDays int `json:"use_history_days,omitempty"`
}
// RUL
type RulPredictionResponse struct {
	NodeId string `json:"node_id"`
	NodeType string `json:"node_type"`
	RulData *RulPredictionSchema `json:"rul_data"`
	CalculateTime time.Time `json:"calculate_time"`
}
// RulPredictionSchema
type RulPredictionSchema struct {
	NodeId string `json:"node_id"`
	NodeType string `json:"node_type"`
	CurrentHi float64 `json:"current_hi"`
	RulDays float64 `json:"rul_days"`
	RulLowerBound float64 `json:"rul_lower_bound"`
	RulUpperBound float64 `json:"rul_upper_bound"`
	RulConfidence float64 `json:"rul_confidence"`
	FailureThreshold float64 `json:"failure_threshold,omitempty"`
	WarningThreshold float64 `json:"warning_threshold,omitempty"`
	DaysToWarning interface{} `json:"days_to_warning,omitempty"`
	HistoricalHi []map[string]interface{} `json:"historical_hi"`
	ForecastSeries []RulPredictionPointSchema `json:"forecast_series"`
	DegradationModel string `json:"degradation_model"`
	ModelParams map[string]interface{} `json:"model_params"`
	PredictionDate time.Time `json:"prediction_date"`
}
// RateLimitStatusResponse
type RateLimitStatusResponse struct {
	KeyId string `json:"key_id"`
	Limit int `json:"limit"`
	Remaining int `json:"remaining"`
	Used int `json:"used"`
}
// RepairRecommendationSchema
type RepairRecommendationSchema struct {
	SensorId string `json:"sensor_id"`
	ProblemType string `json:"problem_type"`
	Description string `json:"description"`
	Recommendation string `json:"recommendation"`
	Priority string `json:"priority"`
	EstimatedEffort float64 `json:"estimated_effort"`
	AffectedMetrics []string `json:"affected_metrics"`
	Evidence map[string]interface{} `json:"evidence"`
}
// /
type ReportGenerateRequest struct {
	NodeType string `json:"node_type"`
	NodeId string `json:"node_id"`
	ReportType string `json:"report_type,omitempty"`
	UseLlm interface{} `json:"use_llm,omitempty"`
}
// ReportStatisticsSchema
type ReportStatisticsSchema struct {
	PredictionCount int `json:"prediction_count,omitempty"`
	AvgRiskScore float64 `json:"avg_risk_score,omitempty"`
	MinRiskScore float64 `json:"min_risk_score,omitempty"`
	MaxRiskScore float64 `json:"max_risk_score,omitempty"`
	StatusDistribution map[string]int `json:"status_distribution,omitempty"`
	Trend string `json:"trend,omitempty"`
	MaxStatus string `json:"max_status,omitempty"`
	FaultTypes []string `json:"fault_types,omitempty"`
}
// RetestRecordCreate
type RetestRecordCreate struct {
	WorkOrderId int `json:"work_order_id"`
	RetestTime interface{} `json:"retest_time,omitempty"`
	RetesterId interface{} `json:"retester_id,omitempty"`
	RetesterName interface{} `json:"retester_name,omitempty"`
	RetestResult string `json:"retest_result,omitempty"`
	MeasuredValue interface{} `json:"measured_value,omitempty"`
	DataPoints interface{} `json:"data_points,omitempty"`
	BeforeRiskScore interface{} `json:"before_risk_score,omitempty"`
	AfterRiskScore interface{} `json:"after_risk_score,omitempty"`
	StatusAfterRetest interface{} `json:"status_after_retest,omitempty"`
	Confidence interface{} `json:"confidence,omitempty"`
	RetestNotes interface{} `json:"retest_notes,omitempty"`
	Photos interface{} `json:"photos,omitempty"`
	ExtraInfo interface{} `json:"extra_info,omitempty"`
	AutoRepredict interface{} `json:"auto_repredict,omitempty"`
}
// RetestRecordListResponse
type RetestRecordListResponse struct {
	Total int `json:"total"`
	Items []RetestRecordResponse `json:"items"`
}
// RetestRecordResponse
type RetestRecordResponse struct {
	Id int `json:"id"`
	WorkOrderId int `json:"work_order_id"`
	RetestTime interface{} `json:"retest_time,omitempty"`
	RetesterId interface{} `json:"retester_id,omitempty"`
	RetesterName interface{} `json:"retester_name,omitempty"`
	RetestResult interface{} `json:"retest_result,omitempty"`
	MeasuredValue interface{} `json:"measured_value,omitempty"`
	DataPoints interface{} `json:"data_points,omitempty"`
	BeforeRiskScore interface{} `json:"before_risk_score,omitempty"`
	AfterRiskScore interface{} `json:"after_risk_score,omitempty"`
	StatusAfterRetest interface{} `json:"status_after_retest,omitempty"`
	Confidence interface{} `json:"confidence,omitempty"`
	RetestNotes interface{} `json:"retest_notes,omitempty"`
	Photos interface{} `json:"photos,omitempty"`
	ExtraInfo interface{} `json:"extra_info,omitempty"`
	CreateTime time.Time `json:"create_time"`
}
// RetestRecordUpdate
type RetestRecordUpdate struct {
	RetestTime interface{} `json:"retest_time,omitempty"`
	RetesterId interface{} `json:"retester_id,omitempty"`
	RetesterName interface{} `json:"retester_name,omitempty"`
	RetestResult interface{} `json:"retest_result,omitempty"`
	MeasuredValue interface{} `json:"measured_value,omitempty"`
	DataPoints interface{} `json:"data_points,omitempty"`
	BeforeRiskScore interface{} `json:"before_risk_score,omitempty"`
	AfterRiskScore interface{} `json:"after_risk_score,omitempty"`
	StatusAfterRetest interface{} `json:"status_after_retest,omitempty"`
	Confidence interface{} `json:"confidence,omitempty"`
	RetestNotes interface{} `json:"retest_notes,omitempty"`
	Photos interface{} `json:"photos,omitempty"`
	ExtraInfo interface{} `json:"extra_info,omitempty"`
}
// RiskAssessExplainRequest
type RiskAssessExplainRequest struct {
	NodeId string `json:"node_id"`
	NodeType string `json:"node_type"`
	Data [][]interface{} `json:"data"`
}
// RiskAssessExplainResponse
type RiskAssessExplainResponse struct {
	NodeId string `json:"node_id"`
	NodeType string `json:"node_type"`
	RiskScore float64 `json:"risk_score"`
	RiskLevel string `json:"risk_level"`
	ProbabilityDistribution *RiskProbabilityDistributionSchema `json:"probability_distribution"`
	FactorContributions []FactorContributionSchema `json:"factor_contributions"`
	BaseValue float64 `json:"base_value"`
	TotalContribution float64 `json:"total_contribution"`
	Summary string `json:"summary"`
}
// RiskAssessmentRequest
type RiskAssessmentRequest struct {
	NodeId string `json:"node_id"`
	NodeType string `json:"node_type"`
	Data [][]interface{} `json:"data"`
}
// RiskAssessmentResponse
type RiskAssessmentResponse struct {
	NodeId string `json:"node_id"`
	NodeType string `json:"node_type"`
	RiskScore float64 `json:"risk_score"`
	RiskLevel string `json:"risk_level"`
	Factors []string `json:"factors"`
	Diagnosis string `json:"diagnosis"`
	Recommendations []string `json:"recommendations"`
	Confidence float64 `json:"confidence"`
	ProbabilityDistribution interface{} `json:"probability_distribution,omitempty"`
	FactorContributions interface{} `json:"factor_contributions,omitempty"`
}
// RiskCalibrationResponse
type RiskCalibrationResponse struct {
	NodeType string `json:"node_type"`
	NodeId string `json:"node_id"`
	PriorWeights map[string]float64 `json:"prior_weights"`
	RiskThresholds map[string]interface{} `json:"risk_thresholds"`
	Version int `json:"version,omitempty"`
	IsActive bool `json:"is_active,omitempty"`
	Description interface{} `json:"description,omitempty"`
	CreateTime interface{} `json:"create_time,omitempty"`
}
// RiskCalibrationUpdateRequest
type RiskCalibrationUpdateRequest struct {
	NodeType string `json:"node_type"`
	NodeId string `json:"node_id"`
	PriorWeights interface{} `json:"prior_weights,omitempty"`
	RiskThresholds interface{} `json:"risk_thresholds,omitempty"`
	Description interface{} `json:"description,omitempty"`
	OperatorId interface{} `json:"operator_id,omitempty"`
	OperatorName interface{} `json:"operator_name,omitempty"`
}
// RiskProbabilityDistributionSchema
type RiskProbabilityDistributionSchema struct {
	PHigh float64 `json:"p_high"`
	PMedium float64 `json:"p_medium"`
	PLow float64 `json:"p_low"`
}
// RootCauseAnalysisSchema
type RootCauseAnalysisSchema struct {
	RootCauseBolt interface{} `json:"root_cause_bolt,omitempty"`
	RootCauseRanking []RootCauseBoltSchema `json:"root_cause_ranking"`
	AbnormalBolts []string `json:"abnormal_bolts"`
	IsUnbalancedLoosening bool `json:"is_unbalanced_loosening"`
	TotalBolts int `json:"total_bolts"`
	AbnormalCount int `json:"abnormal_count"`
}
// RootCauseBoltSchema
type RootCauseBoltSchema struct {
	BoltId string `json:"bolt_id"`
	Index int `json:"index"`
	RootCauseScore float64 `json:"root_cause_score"`
	StatusCode int `json:"status_code"`
	HealthIndex float64 `json:"health_index"`
	IsAbnormal bool `json:"is_abnormal"`
}
// RuleViolationSchema
type RuleViolationSchema struct {
	RuleType string `json:"rule_type"`
	RuleName string `json:"rule_name"`
	Severity string `json:"severity"`
	Description string `json:"description"`
	ViolationIndices []int `json:"violation_indices"`
	ViolationValues interface{} `json:"violation_values,omitempty"`
	Threshold interface{} `json:"threshold,omitempty"`
	ActualValue interface{} `json:"actual_value,omitempty"`
}
// ScheduledJobSchema
type ScheduledJobSchema struct {
	Id string `json:"id"`
	Name string `json:"name"`
	Enabled bool `json:"enabled"`
	Cron string `json:"cron"`
	NextRun interface{} `json:"next_run,omitempty"`
	Description interface{} `json:"description,omitempty"`
}
// SchedulerJobUpdateRequest
type SchedulerJobUpdateRequest struct {
	Enabled interface{} `json:"enabled,omitempty"`
	Cron interface{} `json:"cron,omitempty"`
}
// SchedulerTriggerResponse
type SchedulerTriggerResponse struct {
	JobName string `json:"job_name"`
	Status string `json:"status"`
	Message string `json:"message"`
	LogId interface{} `json:"log_id,omitempty"`
	IsLeader interface{} `json:"is_leader,omitempty"`
}
// SensorQualityScoreSchema
type SensorQualityScoreSchema struct {
	SensorId string `json:"sensor_id"`
	OverallScore float64 `json:"overall_score"`
	OverallLevel string `json:"overall_level"`
	Dimensions map[string]*QualityDimensionScoreSchema `json:"dimensions"`
	ValidForTraining bool `json:"valid_for_training"`
	ConfidenceAdjustment float64 `json:"confidence_adjustment"`
	RuleViolationsCount map[string]int `json:"rule_violations_count"`
	CalculateTime time.Time `json:"calculate_time"`
}
// StrategyAuditLogListResponse
type StrategyAuditLogListResponse struct {
	Total int `json:"total"`
	Items []StrategyAuditLogResponse `json:"items"`
}
// StrategyAuditLogResponse
type StrategyAuditLogResponse struct {
	Id int `json:"id"`
	ConfigId int `json:"config_id"`
	Scope string `json:"scope"`
	NodeType interface{} `json:"node_type,omitempty"`
	NodeId interface{} `json:"node_id,omitempty"`
	Action string `json:"action"`
	OldValue interface{} `json:"old_value,omitempty"`
	NewValue interface{} `json:"new_value,omitempty"`
	VersionBefore interface{} `json:"version_before,omitempty"`
	VersionAfter interface{} `json:"version_after,omitempty"`
	ChangeSummary interface{} `json:"change_summary,omitempty"`
	OperatorId interface{} `json:"operator_id,omitempty"`
	OperatorName interface{} `json:"operator_name,omitempty"`
	CreateTime interface{} `json:"create_time,omitempty"`
}
// StrategyConfigItemResponse
type StrategyConfigItemResponse struct {
	Id int `json:"id"`
	Scope string `json:"scope,omitempty"`
	NodeType interface{} `json:"node_type,omitempty"`
	NodeId interface{} `json:"node_id,omitempty"`
	StrategyType int `json:"strategy_type"`
	ConfidenceThreshold float64 `json:"confidence_threshold"`
	FalsePositiveThreshold interface{} `json:"false_positive_threshold,omitempty"`
	FalseNegativeThreshold interface{} `json:"false_negative_threshold,omitempty"`
	Version int `json:"version,omitempty"`
	IsActive bool `json:"is_active,omitempty"`
	Description interface{} `json:"description,omitempty"`
	OperatorId interface{} `json:"operator_id,omitempty"`
	OperatorName interface{} `json:"operator_name,omitempty"`
	CreateTime interface{} `json:"create_time,omitempty"`
	UpdateTime interface{} `json:"update_time,omitempty"`
}
// StrategyConfigListResponse
type StrategyConfigListResponse struct {
	Total int `json:"total"`
	Items []StrategyConfigItemResponse `json:"items"`
}
// StrategyConfigUpdateRequest
type StrategyConfigUpdateRequest struct {
	Scope string `json:"scope,omitempty"`
	NodeType interface{} `json:"node_type,omitempty"`
	NodeId interface{} `json:"node_id,omitempty"`
	StrategyType int `json:"strategy_type"`
	ConfidenceThreshold interface{} `json:"confidence_threshold,omitempty"`
	FalsePositiveThreshold interface{} `json:"false_positive_threshold,omitempty"`
	FalseNegativeThreshold interface{} `json:"false_negative_threshold,omitempty"`
	Description interface{} `json:"description,omitempty"`
	OperatorId interface{} `json:"operator_id,omitempty"`
	OperatorName interface{} `json:"operator_name,omitempty"`
}
// StrategyNodeOverrideDeleteRequest
type StrategyNodeOverrideDeleteRequest struct {
	NodeType string `json:"node_type"`
	NodeId string `json:"node_id"`
	OperatorId interface{} `json:"operator_id,omitempty"`
	OperatorName interface{} `json:"operator_name,omitempty"`
}
// StrategyRollbackRequest
type StrategyRollbackRequest struct {
	TargetVersion int `json:"target_version"`
	Scope string `json:"scope,omitempty"`
	NodeType interface{} `json:"node_type,omitempty"`
	NodeId interface{} `json:"node_id,omitempty"`
	OperatorId interface{} `json:"operator_id,omitempty"`
	OperatorName interface{} `json:"operator_name,omitempty"`
}
// StreamBatchIngestRequest
type StreamBatchIngestRequest struct {
	Messages []map[string]interface{} `json:"messages"`
}
// StreamBatchIngestResponse
type StreamBatchIngestResponse struct {
	Success bool `json:"success"`
	TotalCount int `json:"total_count"`
	AcceptedCount int `json:"accepted_count"`
	RejectedCount int `json:"rejected_count"`
	Messages []map[string]interface{} `json:"messages,omitempty"`
}
// StreamConfigResponse
type StreamConfigResponse struct {
	Success bool `json:"success"`
	Config map[string]interface{} `json:"config"`
	Message string `json:"message"`
}
// StreamConfigUpdateRequest
type StreamConfigUpdateRequest struct {
	WindowSize interface{} `json:"window_size,omitempty"`
	MaxConcurrentStreams interface{} `json:"max_concurrent_streams,omitempty"`
	RatePerStream interface{} `json:"rate_per_stream,omitempty"`
}
// StreamDataIngestRequest
type StreamDataIngestRequest struct {
	NodeType string `json:"node_type"`
	NodeId string `json:"node_id"`
	Value interface{} `json:"value,omitempty"`
	Timestamp interface{} `json:"timestamp,omitempty"`
	Values interface{} `json:"values,omitempty"`
	Timestamps interface{} `json:"timestamps,omitempty"`
	Data interface{} `json:"data,omitempty"`
	Metadata interface{} `json:"metadata,omitempty"`
}
// StreamDataIngestResponse
type StreamDataIngestResponse struct {
	Success bool `json:"success"`
	Message string `json:"message"`
	NodeId interface{} `json:"node_id,omitempty"`
	NodeType interface{} `json:"node_type,omitempty"`
	WindowCurrentSize interface{} `json:"window_current_size,omitempty"`
	WindowIsFull interface{} `json:"window_is_full,omitempty"`
	Accepted bool `json:"accepted,omitempty"`
}
// StreamEngineStatusResponse
type StreamEngineStatusResponse struct {
	IsRunning bool `json:"is_running"`
	Mode string `json:"mode"`
	ActiveStreams int `json:"active_streams"`
	TotalPredictions int `json:"total_predictions"`
	StatusChanges int `json:"status_changes"`
	WindowManager map[string]interface{} `json:"window_manager"`
	Backpressure map[string]interface{} `json:"backpressure"`
	Events map[string]interface{} `json:"events"`
	Adapters []map[string]interface{} `json:"adapters"`
}
// StreamModeSwitchRequest
type StreamModeSwitchRequest struct {
	Mode string `json:"mode"`
}
// StreamModeSwitchResponse
type StreamModeSwitchResponse struct {
	Success bool `json:"success"`
	CurrentMode string `json:"current_mode"`
	Message string `json:"message"`
}
// StreamWindowStatusResponse
type StreamWindowStatusResponse struct {
	BoltId string `json:"bolt_id"`
	WindowSize int `json:"window_size"`
	CurrentSize int `json:"current_size"`
	IsFull bool `json:"is_full"`
	LastUpdated interface{} `json:"last_updated,omitempty"`
	LastPredictionStatus interface{} `json:"last_prediction_status,omitempty"`
	PredictionCount interface{} `json:"prediction_count,omitempty"`
	FirstTimestamp interface{} `json:"first_timestamp,omitempty"`
	LastTimestamp interface{} `json:"last_timestamp,omitempty"`
}
// Attributes:
// applied:
// temperature_coefficient:   (kN/C)
// correlation:
// original_mean_preload:
// compensated_mean_preload:
// delta_t_mean:
type TemperatureCompensationInfo struct {
	Applied bool `json:"applied,omitempty"`
	TemperatureCoefficient interface{} `json:"temperature_coefficient,omitempty"`
	Correlation interface{} `json:"correlation,omitempty"`
	OriginalMeanPreload interface{} `json:"original_mean_preload,omitempty"`
	CompensatedMeanPreload interface{} `json:"compensated_mean_preload,omitempty"`
	DeltaTMean interface{} `json:"delta_t_mean,omitempty"`
}
// TenantAPIKeyCreateRequest
type TenantApiKeyCreateRequest struct {
	KeyName interface{} `json:"key_name,omitempty"`
	Permissions interface{} `json:"permissions,omitempty"`
	RateLimit int `json:"rate_limit,omitempty"`
	UserId interface{} `json:"user_id,omitempty"`
	ExpiresAt interface{} `json:"expires_at,omitempty"`
}
// TenantAPIKeyCreateResponse
type TenantApiKeyCreateResponse struct {
	Id int `json:"id"`
	TenantId int `json:"tenant_id"`
	ApiKey string `json:"api_key"`
	KeyName interface{} `json:"key_name,omitempty"`
	Permissions interface{} `json:"permissions,omitempty"`
	RateLimit int `json:"rate_limit"`
	UserId interface{} `json:"user_id,omitempty"`
	ExpiresAt interface{} `json:"expires_at,omitempty"`
	LastUsedAt interface{} `json:"last_used_at,omitempty"`
	Status string `json:"status"`
	CreateTime time.Time `json:"create_time"`
	UpdateTime time.Time `json:"update_time"`
	ApiKeyPlain interface{} `json:"api_key_plain,omitempty"`
}
// TenantAPIKeyResponse
type TenantApiKeyResponse struct {
	Id int `json:"id"`
	TenantId int `json:"tenant_id"`
	ApiKey string `json:"api_key"`
	KeyName interface{} `json:"key_name,omitempty"`
	Permissions interface{} `json:"permissions,omitempty"`
	RateLimit int `json:"rate_limit"`
	UserId interface{} `json:"user_id,omitempty"`
	ExpiresAt interface{} `json:"expires_at,omitempty"`
	LastUsedAt interface{} `json:"last_used_at,omitempty"`
	Status string `json:"status"`
	CreateTime time.Time `json:"create_time"`
	UpdateTime time.Time `json:"update_time"`
}
// TenantAPIKeyUpdateRequest
type TenantApiKeyUpdateRequest struct {
	KeyName interface{} `json:"key_name,omitempty"`
	Permissions interface{} `json:"permissions,omitempty"`
	RateLimit interface{} `json:"rate_limit,omitempty"`
	Status interface{} `json:"status,omitempty"`
	ExpiresAt interface{} `json:"expires_at,omitempty"`
}
// TenantCreateRequest
type TenantCreateRequest struct {
	TenantCode string `json:"tenant_code"`
	TenantName string `json:"tenant_name"`
	ContactEmail interface{} `json:"contact_email,omitempty"`
	ContactPhone interface{} `json:"contact_phone,omitempty"`
	ExpireTime interface{} `json:"expire_time,omitempty"`
}
// TenantListResponse
type TenantListResponse struct {
	Total int `json:"total"`
	Items []TenantResponse `json:"items"`
}
// TenantLoginRequest
type TenantLoginRequest struct {
	TenantCode string `json:"tenant_code"`
	Username string `json:"username"`
	Password string `json:"password"`
}
// TenantLoginResponse
type TenantLoginResponse struct {
	Token string `json:"token"`
	TenantId int `json:"tenant_id"`
	UserId int `json:"user_id"`
	Username string `json:"username"`
	Role string `json:"role"`
	ExpiresAt time.Time `json:"expires_at"`
}
// TenantResponse
type TenantResponse struct {
	Id int `json:"id"`
	TenantCode string `json:"tenant_code"`
	TenantName string `json:"tenant_name"`
	ContactEmail interface{} `json:"contact_email,omitempty"`
	ContactPhone interface{} `json:"contact_phone,omitempty"`
	Status string `json:"status"`
	Settings interface{} `json:"settings,omitempty"`
	ExpireTime interface{} `json:"expire_time,omitempty"`
	CreateTime time.Time `json:"create_time"`
	UpdateTime time.Time `json:"update_time"`
}
// TenantUpdateRequest
type TenantUpdateRequest struct {
	TenantName interface{} `json:"tenant_name,omitempty"`
	ContactEmail interface{} `json:"contact_email,omitempty"`
	ContactPhone interface{} `json:"contact_phone,omitempty"`
	Status interface{} `json:"status,omitempty"`
	ExpireTime interface{} `json:"expire_time,omitempty"`
	Settings interface{} `json:"settings,omitempty"`
}
// TenantUserCreateRequest
type TenantUserCreateRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
	DisplayName interface{} `json:"display_name,omitempty"`
	Email interface{} `json:"email,omitempty"`
	Phone interface{} `json:"phone,omitempty"`
	Role string `json:"role,omitempty"`
	OrgNodeId interface{} `json:"org_node_id,omitempty"`
}
// TenantUserListResponse
type TenantUserListResponse struct {
	Total int `json:"total"`
	Items []TenantUserResponse `json:"items"`
}
// TenantUserPasswordRequest
type TenantUserPasswordRequest struct {
	NewPassword string `json:"new_password"`
}
// TenantUserResponse
type TenantUserResponse struct {
	Id int `json:"id"`
	TenantId int `json:"tenant_id"`
	Username string `json:"username"`
	DisplayName interface{} `json:"display_name,omitempty"`
	Email interface{} `json:"email,omitempty"`
	Phone interface{} `json:"phone,omitempty"`
	Role string `json:"role"`
	OrgNodeId interface{} `json:"org_node_id,omitempty"`
	Status string `json:"status"`
	LastLoginTime interface{} `json:"last_login_time,omitempty"`
	CreateTime time.Time `json:"create_time"`
	UpdateTime time.Time `json:"update_time"`
}
// TenantUserUpdateRequest
type TenantUserUpdateRequest struct {
	DisplayName interface{} `json:"display_name,omitempty"`
	Email interface{} `json:"email,omitempty"`
	Phone interface{} `json:"phone,omitempty"`
	Role interface{} `json:"role,omitempty"`
	OrgNodeId interface{} `json:"org_node_id,omitempty"`
	Status interface{} `json:"status,omitempty"`
}
// ThresholdConfigSchema
type ThresholdConfigSchema struct {
	HighRiskThreshold int `json:"high_risk_threshold,omitempty"`
	MediumRiskThreshold int `json:"medium_risk_threshold,omitempty"`
	MinNormalPreload float64 `json:"min_normal_preload,omitempty"`
	MaxNormalPreload float64 `json:"max_normal_preload,omitempty"`
	WarningDeviation float64 `json:"warning_deviation,omitempty"`
	CriticalDeviation float64 `json:"critical_deviation,omitempty"`
	AutoCreateWorkOrderLevel int `json:"auto_create_work_order_level,omitempty"`
	DefaultUpgradeMinutes int `json:"default_upgrade_minutes,omitempty"`
}
// TrainingConfigSchema
type TrainingConfigSchema struct {
	Epochs interface{} `json:"epochs,omitempty"`
	BatchSize interface{} `json:"batch_size,omitempty"`
	LearningRate interface{} `json:"learning_rate,omitempty"`
	ValidationSplit interface{} `json:"validation_split,omitempty"`
	EarlyStopping interface{} `json:"early_stopping,omitempty"`
	LrScheduler interface{} `json:"lr_scheduler,omitempty"`
	ClassImbalance interface{} `json:"class_imbalance,omitempty"`
	Incremental interface{} `json:"incremental,omitempty"`
	FocalLoss interface{} `json:"focal_loss,omitempty"`
}
// TrainingRequest
type TrainingRequest struct {
	ModelType string `json:"model_type"`
	NodeId interface{} `json:"node_id,omitempty"`
	ForceRetrain bool `json:"force_retrain,omitempty"`
}
// TrainingResponse
type TrainingResponse struct {
	ModelType string `json:"model_type"`
	NodeId interface{} `json:"node_id"`
	Status string `json:"status"`
	Message string `json:"message"`
	TrainingTime float64 `json:"training_time"`
	Metrics interface{} `json:"metrics,omitempty"`
}
// TrainingSessionListResponse
type TrainingSessionListResponse struct {
	Total int `json:"total"`
	Items []TrainingSessionSchema `json:"items"`
}
// TrainingSessionSchema
type TrainingSessionSchema struct {
	SessionId string `json:"session_id"`
	ModelId string `json:"model_id"`
	ModelType string `json:"model_type"`
	Status string `json:"status"`
	StartTime interface{} `json:"start_time,omitempty"`
	EndTime interface{} `json:"end_time,omitempty"`
	TotalEpochs int `json:"total_epochs,omitempty"`
	CurrentEpoch int `json:"current_epoch,omitempty"`
	BestMetrics map[string]float64 `json:"best_metrics,omitempty"`
	MetricsHistory []EpochMetricsSchema `json:"metrics_history,omitempty"`
	Config map[string]interface{} `json:"config,omitempty"`
	ErrorMessage interface{} `json:"error_message,omitempty"`
}
// TrainingStatusResponse
type TrainingStatusResponse struct {
	IsTraining bool `json:"is_training"`
	CurrentSession interface{} `json:"current_session,omitempty"`
	RecentSessions []TrainingSessionSchema `json:"recent_sessions,omitempty"`
}
// TreatmentPlanSchema
type TreatmentPlanSchema struct {
	PlanName interface{} `json:"plan_name,omitempty"`
	Steps []TreatmentStepSchema `json:"steps,omitempty"`
	Materials interface{} `json:"materials,omitempty"`
	EstimatedCost interface{} `json:"estimated_cost,omitempty"`
	DifficultyLevel interface{} `json:"difficulty_level,omitempty"`
	PersonnelRequired interface{} `json:"personnel_required,omitempty"`
}
// TreatmentStepSchema
type TreatmentStepSchema struct {
	StepOrder int `json:"step_order"`
	Action string `json:"action"`
	Description interface{} `json:"description,omitempty"`
	Tools interface{} `json:"tools,omitempty"`
	DurationMinutes interface{} `json:"duration_minutes,omitempty"`
	SafetyNotes interface{} `json:"safety_notes,omitempty"`
}
// ValidationError
type ValidationError struct {
	Loc []interface{} `json:"loc"`
	Msg string `json:"msg"`
	Type string `json:"type"`
	Input interface{} `json:"input,omitempty"`
	Ctx map[string]interface{} `json:"ctx,omitempty"`
}
// WarningStrategyConfigSchema
type WarningStrategyConfigSchema struct {
	StrategyType int `json:"strategy_type"`
	Strategy1ConfidenceThreshold float64 `json:"strategy_1_confidence_threshold,omitempty"`
	Strategy1FalsePositiveThreshold float64 `json:"strategy_1_false_positive_threshold,omitempty"`
	Strategy2ConfidenceThreshold float64 `json:"strategy_2_confidence_threshold,omitempty"`
	Strategy2FalseNegativeThreshold float64 `json:"strategy_2_false_negative_threshold,omitempty"`
}
// WorkOrderAssignRequest
type WorkOrderAssignRequest struct {
	AssigneeId string `json:"assignee_id"`
	AssigneeName string `json:"assignee_name"`
	AssignerId interface{} `json:"assigner_id,omitempty"`
	AssignerName interface{} `json:"assigner_name,omitempty"`
}
// WorkOrderCreate
type WorkOrderCreate struct {
	Title string `json:"title"`
	Description interface{} `json:"description,omitempty"`
	Priority string `json:"priority,omitempty"`
	Status interface{} `json:"status,omitempty"`
	NodeType interface{} `json:"node_type,omitempty"`
	NodeId interface{} `json:"node_id,omitempty"`
	AlertLevel interface{} `json:"alert_level,omitempty"`
	RiskScore interface{} `json:"risk_score,omitempty"`
	AssigneeId interface{} `json:"assignee_id,omitempty"`
	AssigneeName interface{} `json:"assignee_name,omitempty"`
	CreatorId interface{} `json:"creator_id,omitempty"`
	CreatorName interface{} `json:"creator_name,omitempty"`
	DueTime interface{} `json:"due_time,omitempty"`
	Recommendations interface{} `json:"recommendations,omitempty"`
	ExtraInfo interface{} `json:"extra_info,omitempty"`
	DueHours interface{} `json:"due_hours,omitempty"`
}
// WorkOrderListResponse
type WorkOrderListResponse struct {
	Total int `json:"total"`
	Items []WorkOrderResponse `json:"items"`
}
// WorkOrderResolveRequest
type WorkOrderResolveRequest struct {
	ResolveNote string `json:"resolve_note"`
	ResolverId interface{} `json:"resolver_id,omitempty"`
	ResolverName interface{} `json:"resolver_name,omitempty"`
}
// WorkOrderResponse
type WorkOrderResponse struct {
	Title string `json:"title"`
	Description interface{} `json:"description,omitempty"`
	Priority string `json:"priority,omitempty"`
	Status interface{} `json:"status,omitempty"`
	NodeType interface{} `json:"node_type,omitempty"`
	NodeId interface{} `json:"node_id,omitempty"`
	AlertLevel interface{} `json:"alert_level,omitempty"`
	RiskScore interface{} `json:"risk_score,omitempty"`
	AssigneeId interface{} `json:"assignee_id,omitempty"`
	AssigneeName interface{} `json:"assignee_name,omitempty"`
	CreatorId interface{} `json:"creator_id,omitempty"`
	CreatorName interface{} `json:"creator_name,omitempty"`
	DueTime interface{} `json:"due_time,omitempty"`
	Recommendations interface{} `json:"recommendations,omitempty"`
	ExtraInfo interface{} `json:"extra_info,omitempty"`
	Id int `json:"id"`
	OrderNo string `json:"order_no"`
	AlertId interface{} `json:"alert_id,omitempty"`
	ResolveTime interface{} `json:"resolve_time,omitempty"`
	ResolveNote interface{} `json:"resolve_note,omitempty"`
	CreateTime time.Time `json:"create_time"`
	UpdateTime time.Time `json:"update_time"`
}
// WorkOrderStatsResponse
type WorkOrderStatsResponse struct {
	TotalWorkOrders int `json:"total_work_orders,omitempty"`
	ClosedWorkOrders int `json:"closed_work_orders,omitempty"`
	OpenWorkOrders int `json:"open_work_orders,omitempty"`
	InProgressWorkOrders int `json:"in_progress_work_orders,omitempty"`
	MttrHours interface{} `json:"mttr_hours,omitempty"`
	MttrMinutes interface{} `json:"mttr_minutes,omitempty"`
	FalsePositiveRate interface{} `json:"false_positive_rate,omitempty"`
	FalsePositiveCount int `json:"false_positive_count,omitempty"`
	RecurrenceRate interface{} `json:"recurrence_rate,omitempty"`
	RecurrenceCount int `json:"recurrence_count,omitempty"`
	AvgResolveHours interface{} `json:"avg_resolve_hours,omitempty"`
	OnTimeCompletionRate interface{} `json:"on_time_completion_rate,omitempty"`
	PriorityDistribution interface{} `json:"priority_distribution,omitempty"`
	StatusDistribution interface{} `json:"status_distribution,omitempty"`
	TimeRange interface{} `json:"time_range,omitempty"`
}
// WorkOrderStatusUpdateRequest
type WorkOrderStatusUpdateRequest struct {
	Status string `json:"status"`
	OperatorId interface{} `json:"operator_id,omitempty"`
	OperatorName interface{} `json:"operator_name,omitempty"`
	Note interface{} `json:"note,omitempty"`
}
// WorkOrderUpdate
type WorkOrderUpdate struct {
	Title interface{} `json:"title,omitempty"`
	Description interface{} `json:"description,omitempty"`
	Priority interface{} `json:"priority,omitempty"`
	Status interface{} `json:"status,omitempty"`
	AssigneeId interface{} `json:"assignee_id,omitempty"`
	AssigneeName interface{} `json:"assignee_name,omitempty"`
	DueTime interface{} `json:"due_time,omitempty"`
	Recommendations interface{} `json:"recommendations,omitempty"`
	ExtraInfo interface{} `json:"extra_info,omitempty"`
}
// WorkingConditionSchema
type WorkingConditionSchema struct {
	Temperature interface{} `json:"temperature,omitempty"`
	Pressure interface{} `json:"pressure,omitempty"`
	Humidity interface{} `json:"humidity,omitempty"`
	Vibration interface{} `json:"vibration,omitempty"`
	LoadCondition interface{} `json:"load_condition,omitempty"`
	OperatingHours interface{} `json:"operating_hours,omitempty"`
	MaintenanceCycle interface{} `json:"maintenance_cycle,omitempty"`
	LastMaintenanceDate interface{} `json:"last_maintenance_date,omitempty"`
	EquipmentAge interface{} `json:"equipment_age,omitempty"`
	Extra interface{} `json:"extra,omitempty"`
}
