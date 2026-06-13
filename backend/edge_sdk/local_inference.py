import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import numpy as np
from loguru import logger

try:
    import onnxruntime as ort
except ImportError:
    ort = None

try:
    import torch
except ImportError:
    torch = None

STATUS_LABELS = {0: '正常', 1: '关注级预警', 2: '检查级预警', 3: '紧急级预警', 4: '故障'}


@dataclass
class InferenceConfig:
    model_path: str = ""
    model_format: str = "onnx"
    preprocessing_path: str = ""
    device: str = "cpu"
    num_threads: int = 4
    warmup_runs: int = 3


@dataclass
class InferenceResult:
    predicted_class: int
    confidence: float
    probabilities: np.ndarray
    inference_time_ms: float
    model_version: str = ""


class PreprocessingPipeline:
    def __init__(self, preprocessing_config: dict):
        self.normalization_method = preprocessing_config.get("normalization_method", "zscore")
        self.scaler_mean = np.array(preprocessing_config.get("scaler_mean", []), dtype=np.float32)
        self.scaler_scale = np.array(preprocessing_config.get("scaler_scale", []), dtype=np.float32)
        self.scaler_min = np.array(preprocessing_config.get("scaler_min", []), dtype=np.float32)
        self.scaler_max = np.array(preprocessing_config.get("scaler_max", []), dtype=np.float32)
        self.sequence_length = preprocessing_config.get("sequence_length", 1)
        self.input_dim = preprocessing_config.get("input_dim", 1)
        self.kalman_process_noise = preprocessing_config.get("kalman_process_noise", 1e-5)
        self.kalman_measurement_noise = preprocessing_config.get("kalman_measurement_noise", 1e-2)

    def transform(self, data: np.ndarray) -> np.ndarray:
        if self.normalization_method == "zscore":
            mean = self.scaler_mean
            scale = self.scaler_scale
            if mean.size > 0 and scale.size > 0:
                if data.ndim == 1 and mean.ndim == 1:
                    return (data - mean) / scale
                return (data - mean) / scale
            return data
        elif self.normalization_method == "minmax":
            min_val = self.scaler_min
            max_val = self.scaler_max
            if min_val.size > 0 and max_val.size > 0:
                if data.ndim == 1 and min_val.ndim == 1:
                    return (data - min_val) / (max_val - min_val + 1e-8)
                return (data - min_val) / (max_val - min_val + 1e-8)
            return data
        return data

    def prepare_sequence(self, data: np.ndarray, sequence_length: int) -> np.ndarray:
        if data.ndim == 1:
            data = data.reshape(-1, 1)

        n_samples = data.shape[0]
        n_features = data.shape[1]

        if n_samples < sequence_length:
            pad_length = sequence_length - n_samples
            padding = np.zeros((pad_length, n_features), dtype=data.dtype)
            data = np.vstack([padding, data])
            n_samples = data.shape[0]

        sequences = []
        for i in range(n_samples - sequence_length + 1):
            seq = data[i:i + sequence_length]
            time_index = np.arange(i, i + sequence_length, dtype=np.float32).reshape(-1, 1)
            seq_with_time = np.hstack([seq, time_index])
            sequences.append(seq_with_time)

        if not sequences:
            seq = data[:sequence_length]
            time_index = np.arange(0, sequence_length, dtype=np.float32).reshape(-1, 1)
            seq_with_time = np.hstack([seq, time_index])
            sequences.append(seq_with_time)

        return np.stack(sequences, axis=0)


class EdgeInferenceEngine:
    def __init__(self, config: InferenceConfig):
        self.config = config
        self._session = None
        self._model = None
        self._pipeline: Optional[PreprocessingPipeline] = None
        self._model_version = ""
        self._ready = False

    def load_model(self):
        model_path = Path(self.config.model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        if self.config.model_format == "onnx":
            if ort is None:
                raise RuntimeError("onnxruntime is not installed")
            sess_options = ort.SessionOptions()
            sess_options.intra_op_num_threads = self.config.num_threads
            sess_options.inter_op_num_threads = self.config.num_threads
            providers = ["CPUExecutionProvider"]
            if self.config.device == "cuda":
                providers.insert(0, "CUDAExecutionProvider")
            self._session = ort.InferenceSession(
                str(model_path), sess_options=sess_options, providers=providers
            )
            logger.info(f"ONNX model loaded from {model_path}")
        elif self.config.model_format == "torchscript":
            if torch is None:
                raise RuntimeError("torch is not installed")
            map_location = "cuda" if self.config.device == "cuda" else "cpu"
            self._model = torch.jit.load(str(model_path), map_location=map_location)
            self._model.eval()
            logger.info(f"TorchScript model loaded from {model_path}")
        else:
            raise ValueError(f"Unsupported model format: {self.config.model_format}")

        self._ready = True

    def load_preprocessing(self):
        preprocessing_path = Path(self.config.preprocessing_path)
        if not preprocessing_path.exists():
            logger.warning(f"Preprocessing file not found: {preprocessing_path}")
            self._pipeline = PreprocessingPipeline({})
            return

        with open(preprocessing_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        if "scaler" in config:
            scaler_data = config["scaler"]
            if "mean_" in scaler_data and scaler_data["mean_"] is not None:
                config["scaler_mean"] = scaler_data["mean_"]
            if "scale_" in scaler_data and scaler_data["scale_"] is not None:
                config["scaler_scale"] = scaler_data["scale_"]
            if "min_" in scaler_data and scaler_data["min_"] is not None:
                config["scaler_min"] = scaler_data["min_"]
            if "max_" in scaler_data and scaler_data["max_"] is not None:
                config["scaler_max"] = scaler_data["max_"]

        if "model_version" in config:
            self._model_version = config["model_version"]

        self._pipeline = PreprocessingPipeline(config)
        logger.info(f"Preprocessing pipeline loaded from {preprocessing_path}")

    def predict(self, data: np.ndarray) -> InferenceResult:
        if not self._ready:
            raise RuntimeError("Engine is not ready. Call load_model() first.")

        start_time = time.perf_counter()

        if self._pipeline is not None:
            data = self._pipeline.transform(data)
            sequences = self._pipeline.prepare_sequence(data, self._pipeline.sequence_length)
        else:
            sequences = data

        if isinstance(sequences, np.ndarray):
            input_data = sequences.astype(np.float32)
        else:
            input_data = np.array(sequences, dtype=np.float32)

        if input_data.ndim == 2:
            input_data = np.expand_dims(input_data, axis=0)

        if self.config.model_format == "onnx":
            input_name = self._session.get_inputs()[0].name
            outputs = self._session.run(None, {input_name: input_data})
            probabilities = outputs[0]
        else:
            with torch.no_grad():
                tensor_input = torch.from_numpy(input_data).to(
                    "cuda" if self.config.device == "cuda" else "cpu"
                )
                output = self._model(tensor_input)
                if isinstance(output, (tuple, list)):
                    output = output[0]
                probabilities = output.cpu().numpy()

        if probabilities.ndim > 2:
            probabilities = probabilities.squeeze()
        if probabilities.ndim == 2:
            probabilities = probabilities[-1]

        inference_time_ms = (time.perf_counter() - start_time) * 1000

        predicted_class = int(np.argmax(probabilities))
        confidence = float(probabilities[predicted_class])

        return InferenceResult(
            predicted_class=predicted_class,
            confidence=confidence,
            probabilities=probabilities,
            inference_time_ms=inference_time_ms,
            model_version=self._model_version,
        )

    def predict_batch(self, data_list: List[np.ndarray]) -> List[InferenceResult]:
        results = []
        for data in data_list:
            result = self.predict(data)
            results.append(result)
        return results

    def _warmup(self):
        if not self._ready:
            return

        if self._pipeline is not None:
            seq_len = self._pipeline.sequence_length
            input_dim = self._pipeline.input_dim
            dummy = np.random.randn(seq_len, input_dim).astype(np.float32)
        else:
            dummy = np.random.randn(1, 10).astype(np.float32)

        for _ in range(self.config.warmup_runs):
            try:
                self.predict(dummy)
            except Exception as e:
                logger.warning(f"Warmup inference failed: {e}")

        logger.info(f"Warmup completed with {self.config.warmup_runs} runs")

    @property
    def is_ready(self) -> bool:
        return self._ready
