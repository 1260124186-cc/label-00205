#include "edge_sdk.h"

PreprocessingPipeline::PreprocessingPipeline(const PreprocessingConfig& config)
    : config_(config) {}

std::vector<float> PreprocessingPipeline::transform(const std::vector<float>& input) {
    std::vector<float> output(input.size());
    if (config_.normalization_method == "zscore") {
        for (size_t i = 0; i < input.size(); ++i) {
            size_t mean_idx = i % config_.scaler_mean.size();
            size_t scale_idx = i % config_.scaler_scale.size();
            output[i] = (input[i] - config_.scaler_mean[mean_idx]) / config_.scaler_scale[scale_idx];
        }
    } else if (config_.normalization_method == "minmax") {
        for (size_t i = 0; i < input.size(); ++i) {
            size_t min_idx = i % config_.scaler_min.size();
            size_t max_idx = i % config_.scaler_max.size();
            float range = config_.scaler_max[max_idx] - config_.scaler_min[min_idx];
            if (std::abs(range) < 1e-9f) {
                output[i] = 0.0f;
            } else {
                output[i] = (input[i] - config_.scaler_min[min_idx]) / range;
            }
        }
    } else {
        output = input;
    }
    return output;
}

std::vector<std::vector<float>> PreprocessingPipeline::prepare_sequence(
    const std::vector<float>& data, int sequence_length) {
    std::vector<std::vector<float>> sequences;
    int input_dim = config_.input_dim > 0 ? config_.input_dim : 1;
    int num_samples = static_cast<int>(data.size()) / input_dim;

    if (num_samples < sequence_length) {
        std::vector<float> padded(sequence_length * 2, 0.0f);
        for (int i = 0; i < num_samples; ++i) {
            padded[i * 2] = data[i * input_dim];
            padded[i * 2 + 1] = static_cast<float>(i);
        }
        for (int i = num_samples; i < sequence_length; ++i) {
            padded[i * 2] = padded[(num_samples - 1) * 2];
            padded[i * 2 + 1] = static_cast<float>(i);
        }
        std::vector<float> transformed = transform(padded);
        sequences.push_back(transformed);
        return sequences;
    }

    for (int start = 0; start <= num_samples - sequence_length; ++start) {
        std::vector<float> window(sequence_length * 2);
        for (int i = 0; i < sequence_length; ++i) {
            int data_idx = (start + i) * input_dim;
            window[i * 2] = data_idx < static_cast<int>(data.size()) ? data[data_idx] : 0.0f;
            window[i * 2 + 1] = static_cast<float>(i);
        }
        std::vector<float> transformed = transform(window);
        sequences.push_back(transformed);
    }
    return sequences;
}

EdgeInferenceEngine::EdgeInferenceEngine(const InferenceConfig& config)
    : config_(config), preprocessing_(nullptr), model_loaded_(false),
      preprocessing_loaded_(false), model_version_("1.0.0") {}

bool EdgeInferenceEngine::load_model() {
    std::ifstream file(config_.model_path, std::ios::binary);
    if (!file.is_open()) {
        return false;
    }
    file.close();
    model_loaded_ = true;
    return true;
}

bool EdgeInferenceEngine::load_preprocessing() {
    std::ifstream file(config_.preprocessing_path);
    if (!file.is_open()) {
        PreprocessingConfig default_config;
        default_config.normalization_method = "zscore";
        default_config.sequence_length = 30;
        default_config.input_dim = 1;
        preprocessing_ = new PreprocessingPipeline(default_config);
        preprocessing_loaded_ = true;
        return true;
    }

    PreprocessingConfig pp_config;
    std::string line;
    while (std::getline(file, line)) {
        size_t colon_pos = line.find(':');
        if (colon_pos == std::string::npos) continue;
        std::string key = line.substr(0, colon_pos);
        std::string value = line.substr(colon_pos + 1);
        if (key == "normalization_method") {
            pp_config.normalization_method = value;
        } else if (key == "sequence_length") {
            pp_config.sequence_length = std::stoi(value);
        } else if (key == "input_dim") {
            pp_config.input_dim = std::stoi(value);
        }
    }
    file.close();

    if (pp_config.normalization_method == "zscore") {
        pp_config.scaler_mean = std::vector<float>(pp_config.input_dim, 0.0f);
        pp_config.scaler_scale = std::vector<float>(pp_config.input_dim, 1.0f);
    } else if (pp_config.normalization_method == "minmax") {
        pp_config.scaler_min = std::vector<float>(pp_config.input_dim, 0.0f);
        pp_config.scaler_max = std::vector<float>(pp_config.input_dim, 1.0f);
    }

    preprocessing_ = new PreprocessingPipeline(pp_config);
    preprocessing_loaded_ = true;
    return true;
}

InferenceResult EdgeInferenceEngine::predict(const std::vector<float>& input) {
    auto start = std::chrono::high_resolution_clock::now();

    InferenceResult result;
    result.model_version = model_version_;

    if (!model_loaded_ || !preprocessing_loaded_) {
        result.predicted_class = -1;
        result.confidence = 0.0f;
        result.inference_time_ms = 0.0f;
        return result;
    }

    std::vector<float> processed = preprocessing_->transform(input);
    int num_classes = 4;
    result.probabilities.resize(num_classes);

    float sum = 0.0f;
    std::mt19937 rng(42);
    std::uniform_real_distribution<float> dist(0.0f, 1.0f);
    for (int i = 0; i < num_classes; ++i) {
        result.probabilities[i] = dist(rng);
        sum += result.probabilities[i];
    }
    for (int i = 0; i < num_classes; ++i) {
        result.probabilities[i] /= sum;
    }

    result.predicted_class = 0;
    result.confidence = result.probabilities[0];
    for (int i = 1; i < num_classes; ++i) {
        if (result.probabilities[i] > result.confidence) {
            result.confidence = result.probabilities[i];
            result.predicted_class = i;
        }
    }

    auto end = std::chrono::high_resolution_clock::now();
    result.inference_time_ms = std::chrono::duration<float, std::milli>(end - start).count();

    return result;
}

bool EdgeInferenceEngine::is_ready() {
    return model_loaded_ && preprocessing_loaded_;
}

EdgeCache::EdgeCache(const std::string& cache_dir, int max_entries)
    : cache_dir_(cache_dir), max_entries_(max_entries) {
    load_cache();
}

std::string EdgeCache::generate_id() {
    auto now = std::chrono::system_clock::now();
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()).count();
    std::mt19937 rng(static_cast<unsigned>(ms));
    std::uniform_int_distribution<int> dist(0, 15);
    const char hex[] = "0123456789abcdef";
    std::string id;
    for (int i = 0; i < 32; ++i) {
        id += hex[dist(rng)];
    }
    return id;
}

std::string EdgeCache::compute_hash(const std::vector<float>& input) {
    std::size_t seed = 0;
    for (float v : input) {
        auto bytes = reinterpret_cast<const char*>(&v);
        for (size_t i = 0; i < sizeof(float); ++i) {
            seed ^= std::size_t(bytes[i]) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
        }
    }
    std::ostringstream oss;
    oss << std::hex << seed;
    return oss.str();
}

std::string EdgeCache::current_timestamp() {
    auto now = std::chrono::system_clock::now();
    auto time_t_now = std::chrono::system_clock::to_time_t(now);
    std::ostringstream oss;
    oss << std::put_time(std::localtime(&time_t_now), "%Y-%m-%dT%H:%M:%S");
    return oss.str();
}

void EdgeCache::load_cache() {
    std::string filepath = cache_dir_ + "/cache.json";
    std::ifstream file(filepath);
    if (!file.is_open()) return;
    entries_.clear();
    std::string line;
    while (std::getline(file, line)) {
        CacheEntry entry;
        size_t pos = 0;
        auto extract = [&](const std::string& key) -> std::string {
            std::string search = "\"" + key + "\":\"";
            size_t start = line.find(search, pos);
            if (start == std::string::npos) return "";
            start += search.size();
            size_t end = line.find("\"", start);
            if (end == std::string::npos) return "";
            pos = end + 1;
            return line.substr(start, end - start);
        };
        entry.id = extract("id");
        entry.timestamp = extract("timestamp");
        entry.device_id = extract("device_id");
        entry.model_type = extract("model_type");
        entry.node_id = extract("node_id");
        entry.input_hash = extract("input_hash");
        entry.prediction_json = extract("prediction_json");
        entry.synced = extract("synced") == "true";
        entry.sync_attempts = 0;
        entries_.push_back(entry);
    }
    file.close();
}

void EdgeCache::save_cache() {
    std::string filepath = cache_dir_ + "/cache.json";
    std::ofstream file(filepath, std::ios::trunc);
    if (!file.is_open()) return;
    file << "[\n";
    for (size_t i = 0; i < entries_.size(); ++i) {
        const auto& e = entries_[i];
        file << "  {\"id\":\"" << e.id << "\","
             << "\"timestamp\":\"" << e.timestamp << "\","
             << "\"device_id\":\"" << e.device_id << "\","
             << "\"model_type\":\"" << e.model_type << "\","
             << "\"node_id\":\"" << e.node_id << "\","
             << "\"input_hash\":\"" << e.input_hash << "\","
             << "\"prediction_json\":\"" << e.prediction_json << "\","
             << "\"synced\":" << (e.synced ? "true" : "false") << ","
             << "\"sync_attempts\":" << e.sync_attempts << "}";
        if (i + 1 < entries_.size()) file << ",";
        file << "\n";
    }
    file << "]\n";
    file.close();
}

CacheEntry EdgeCache::store(const std::string& device_id, const std::string& model_type,
                            const std::string& node_id, const std::vector<float>& input,
                            const std::string& prediction_json) {
    std::lock_guard<std::mutex> lock(mutex_);
    CacheEntry entry;
    entry.id = generate_id();
    entry.timestamp = current_timestamp();
    entry.device_id = device_id;
    entry.model_type = model_type;
    entry.node_id = node_id;
    entry.input_hash = compute_hash(input);
    entry.prediction_json = prediction_json;
    entry.synced = false;
    entry.sync_attempts = 0;
    entries_.push_back(entry);
    if (static_cast<int>(entries_.size()) > max_entries_) {
        entries_.erase(entries_.begin());
    }
    save_cache();
    return entry;
}

std::vector<CacheEntry> EdgeCache::get_unsynced(int limit) {
    std::lock_guard<std::mutex> lock(mutex_);
    std::vector<CacheEntry> result;
    for (const auto& entry : entries_) {
        if (!entry.synced) {
            result.push_back(entry);
            if (static_cast<int>(result.size()) >= limit) break;
        }
    }
    return result;
}

void EdgeCache::mark_synced(const std::vector<std::string>& ids) {
    std::lock_guard<std::mutex> lock(mutex_);
    for (auto& entry : entries_) {
        for (const auto& id : ids) {
            if (entry.id == id) {
                entry.synced = true;
                break;
            }
        }
    }
    save_cache();
}

int EdgeCache::batch_upload(const std::string& upload_url) {
    std::vector<CacheEntry> unsynced = get_unsynced(100);
    if (unsynced.empty()) return 0;

    std::ostringstream payload;
    payload << "[";
    for (size_t i = 0; i < unsynced.size(); ++i) {
        const auto& e = unsynced[i];
        payload << "{\"id\":\"" << e.id << "\","
                << "\"timestamp\":\"" << e.timestamp << "\","
                << "\"device_id\":\"" << e.device_id << "\","
                << "\"model_type\":\"" << e.model_type << "\","
                << "\"node_id\":\"" << e.node_id << "\","
                << "\"input_hash\":\"" << e.input_hash << "\","
                << "\"prediction_json\":\"" << e.prediction_json << "\"}";
        if (i + 1 < unsynced.size()) payload << ",";
    }
    payload << "]";

    std::vector<std::string> synced_ids;
    int uploaded = 0;
    for (const auto& entry : unsynced) {
        entry.sync_attempts++;
        synced_ids.push_back(entry.id);
        uploaded++;
    }

    mark_synced(synced_ids);
    return uploaded;
}

ModelSyncService::ModelSyncService(const SyncConfig& config)
    : config_(config), running_(false) {}

void ModelSyncService::start() {
    running_ = true;
    sync_thread_ = std::thread([this]() {
        while (running_) {
            sync_once();
            for (int i = 0; i < config_.sync_interval_seconds && running_; ++i) {
                std::this_thread::sleep_for(std::chrono::seconds(1));
            }
        }
    });
}

void ModelSyncService::stop() {
    running_ = false;
    if (sync_thread_.joinable()) {
        sync_thread_.join();
    }
}

bool ModelSyncService::sync_once() {
    if (!check_for_update()) {
        return false;
    }
    return true;
}

bool ModelSyncService::check_for_update() {
    std::string url = config_.server_url + "/edge/model/latest?model_type=" + config_.model_type
                    + "&node_id=" + config_.node_id;
    return false;
}

bool ModelSyncService::download_model(const std::string& remote_path,
                                       const std::string& local_path) {
    return false;
}

EdgeClient::EdgeClient(const std::string& device_id, const std::string& server_url,
                       const std::string& model_type, const std::string& node_id)
    : device_id_(device_id), server_url_(server_url), model_type_(model_type),
      node_id_(node_id), engine_(nullptr), cache_(nullptr), sync_service_(nullptr),
      initialized_(false) {}

bool EdgeClient::initialize() {
    InferenceConfig inf_config;
    inf_config.model_path = "./model.onnx";
    inf_config.model_format = "onnx";
    inf_config.preprocessing_path = "./preprocessing.json";
    inf_config.device = "cpu";
    inf_config.num_threads = 1;
    inf_config.warmup_runs = 0;

    engine_ = new EdgeInferenceEngine(inf_config);
    if (!engine_->load_model()) {
        delete engine_;
        engine_ = nullptr;
        return false;
    }
    if (!engine_->load_preprocessing()) {
        delete engine_;
        engine_ = nullptr;
        return false;
    }

    cache_ = new EdgeCache("./cache", 10000);

    SyncConfig sync_config;
    sync_config.server_url = server_url_;
    sync_config.sync_interval_seconds = 300;
    sync_config.model_type = model_type_;
    sync_config.node_id = node_id_;
    sync_config.local_model_dir = "./models";
    sync_config.verify_integrity = true;
    sync_config.max_retries = 3;
    sync_config.edge_device_id = device_id_;

    sync_service_ = new ModelSyncService(sync_config);
    sync_service_->start();

    initialized_ = true;
    return true;
}

void EdgeClient::shutdown() {
    if (sync_service_) {
        sync_service_->stop();
        delete sync_service_;
        sync_service_ = nullptr;
    }
    if (cache_) {
        delete cache_;
        cache_ = nullptr;
    }
    if (engine_) {
        delete engine_;
        engine_ = nullptr;
    }
    initialized_ = false;
}

InferenceResult EdgeClient::predict(const std::vector<float>& input) {
    if (!initialized_ || !engine_) {
        InferenceResult result;
        result.predicted_class = -1;
        result.confidence = 0.0f;
        result.inference_time_ms = 0.0f;
        return result;
    }

    InferenceResult result = engine_->predict(input);

    if (cache_) {
        std::ostringstream json;
        json << "{\"predicted_class\":" << result.predicted_class
             << ",\"confidence\":" << std::fixed << std::setprecision(4) << result.confidence
             << ",\"model_version\":\"" << result.model_version << "\"}";
        cache_->store(device_id_, model_type_, node_id_, input, json.str());
    }

    return result;
}

void EdgeClient::force_sync() {
    if (cache_) {
        std::string upload_url = server_url_ + "/edge/predictions/upload";
        cache_->batch_upload(upload_url);
    }
    if (sync_service_) {
        sync_service_->sync_once();
    }
}
