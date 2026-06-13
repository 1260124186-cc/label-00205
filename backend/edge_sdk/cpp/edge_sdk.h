#pragma once

#include <string>
#include <vector>
#include <functional>
#include <mutex>
#include <thread>
#include <atomic>
#include <chrono>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <numeric>
#include <cmath>
#include <random>
#include <iomanip>

struct InferenceConfig {
    std::string model_path;
    std::string model_format;
    std::string preprocessing_path;
    std::string device;
    int num_threads;
    int warmup_runs;
};

struct InferenceResult {
    int predicted_class;
    float confidence;
    std::vector<float> probabilities;
    float inference_time_ms;
    std::string model_version;
};

struct PreprocessingConfig {
    std::string normalization_method;
    std::vector<float> scaler_mean;
    std::vector<float> scaler_scale;
    std::vector<float> scaler_min;
    std::vector<float> scaler_max;
    int sequence_length;
    int input_dim;
};

struct CacheEntry {
    std::string id;
    std::string timestamp;
    std::string device_id;
    std::string model_type;
    std::string node_id;
    std::string input_hash;
    std::string prediction_json;
    bool synced;
    int sync_attempts;
};

struct SyncConfig {
    std::string server_url;
    int sync_interval_seconds;
    std::string model_type;
    std::string node_id;
    std::string local_model_dir;
    bool verify_integrity;
    int max_retries;
    std::string edge_device_id;
};

class PreprocessingPipeline {
public:
    explicit PreprocessingPipeline(const PreprocessingConfig& config);
    std::vector<float> transform(const std::vector<float>& input);
    std::vector<std::vector<float>> prepare_sequence(const std::vector<float>& data, int sequence_length);

private:
    PreprocessingConfig config_;
};

class EdgeInferenceEngine {
public:
    explicit EdgeInferenceEngine(const InferenceConfig& config);
    bool load_model();
    bool load_preprocessing();
    InferenceResult predict(const std::vector<float>& input);
    bool is_ready();

private:
    InferenceConfig config_;
    PreprocessingPipeline* preprocessing_;
    bool model_loaded_;
    bool preprocessing_loaded_;
    std::string model_version_;
};

class EdgeCache {
public:
    EdgeCache(const std::string& cache_dir, int max_entries);
    CacheEntry store(const std::string& device_id, const std::string& model_type,
                     const std::string& node_id, const std::vector<float>& input,
                     const std::string& prediction_json);
    std::vector<CacheEntry> get_unsynced(int limit);
    void mark_synced(const std::vector<std::string>& ids);
    int batch_upload(const std::string& upload_url);

private:
    std::string cache_dir_;
    int max_entries_;
    std::mutex mutex_;
    std::vector<CacheEntry> entries_;
    void load_cache();
    void save_cache();
    std::string generate_id();
    std::string compute_hash(const std::vector<float>& input);
    std::string current_timestamp();
};

class ModelSyncService {
public:
    explicit ModelSyncService(const SyncConfig& config);
    void start();
    void stop();
    bool sync_once();

private:
    SyncConfig config_;
    std::atomic<bool> running_;
    std::thread sync_thread_;
    bool check_for_update();
    bool download_model(const std::string& remote_path, const std::string& local_path);
};

class EdgeClient {
public:
    EdgeClient(const std::string& device_id, const std::string& server_url,
               const std::string& model_type, const std::string& node_id);
    bool initialize();
    void shutdown();
    InferenceResult predict(const std::vector<float>& input);
    void force_sync();

private:
    std::string device_id_;
    std::string server_url_;
    std::string model_type_;
    std::string node_id_;
    EdgeInferenceEngine* engine_;
    EdgeCache* cache_;
    ModelSyncService* sync_service_;
    bool initialized_;
};
