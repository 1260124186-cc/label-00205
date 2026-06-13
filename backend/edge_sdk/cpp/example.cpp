#include "edge_sdk.h"
#include <iostream>

int main() {
    EdgeClient client("edge-device-001",
                      "http://localhost:8000",
                      "lstm_classifier",
                      "node-01");

    if (!client.initialize()) {
        std::cerr << "Failed to initialize EdgeClient" << std::endl;
        return 1;
    }

    std::vector<float> sample_data;
    for (int i = 0; i < 30; ++i) {
        sample_data.push_back(static_cast<float>(i) * 0.1f);
    }

    InferenceResult result = client.predict(sample_data);

    std::cout << "Prediction:" << std::endl;
    std::cout << "  Predicted class: " << result.predicted_class << std::endl;
    std::cout << "  Confidence: " << result.confidence << std::endl;
    std::cout << "  Inference time: " << result.inference_time_ms << " ms" << std::endl;
    std::cout << "  Model version: " << result.model_version << std::endl;
    std::cout << "  Probabilities:";
    for (float p : result.probabilities) {
        std::cout << " " << p;
    }
    std::cout << std::endl;

    client.force_sync();
    client.shutdown();

    return 0;
}
