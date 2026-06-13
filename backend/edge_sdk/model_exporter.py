import enum
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import torch
from loguru import logger


class ExportFormat(enum.Enum):
    ONNX = "onnx"
    TORCHSCRIPT = "torchscript"


@dataclass
class ExportResult:
    model_path: Path
    manifest_path: Path
    preprocessing_path: Path
    format: ExportFormat
    model_type: str
    file_hashes: Dict[str, str]
    export_time: float


class ModelExporter:

    def export(
        self,
        model: torch.nn.Module,
        model_type: str,
        export_format: ExportFormat,
        output_dir: Path,
        preprocessing_params: Dict[str, Any],
        sample_input: torch.Tensor,
        **kwargs,
    ) -> ExportResult:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        start_time = time.time()

        if export_format == ExportFormat.ONNX:
            model_path = output_dir / f"{model_type}.onnx"
            self._export_onnx(model, model_path, sample_input, **kwargs)
        elif export_format == ExportFormat.TORCHSCRIPT:
            model_path = output_dir / f"{model_type}.pt"
            self._export_torchscript(model, model_path, sample_input, **kwargs)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")

        preprocessing_path = output_dir / f"{model_type}_preprocessing.json"
        serialized = self._serialize_preprocessing(preprocessing_params)
        preprocessing_path.write_text(json.dumps(serialized, indent=2, ensure_ascii=False))

        file_hashes = {
            model_path.name: self._compute_sha256(model_path),
            preprocessing_path.name: self._compute_sha256(preprocessing_path),
        }

        manifest_path = output_dir / f"{model_type}_manifest.json"
        manifest = self._create_manifest(model_type, export_format, preprocessing_params, file_hashes)
        manifest["export_time_seconds"] = time.time() - start_time
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

        file_hashes[manifest_path.name] = self._compute_sha256(manifest_path)

        export_time = time.time() - start_time
        logger.info(
            f"Model exported: format={export_format.value}, "
            f"type={model_type}, time={export_time:.2f}s"
        )

        return ExportResult(
            model_path=model_path,
            manifest_path=manifest_path,
            preprocessing_path=preprocessing_path,
            format=export_format,
            model_type=model_type,
            file_hashes=file_hashes,
            export_time=export_time,
        )

    def _export_onnx(
        self,
        model: torch.nn.Module,
        output_path: Path,
        sample_input: torch.Tensor,
        **kwargs,
    ):
        model.eval()
        opset_version = kwargs.get("opset_version", 14)
        input_names = kwargs.get("input_names", ["input"])
        output_names = kwargs.get("output_names", ["output"])
        dynamic_axes = kwargs.get("dynamic_axes", None)

        with torch.no_grad():
            torch.onnx.export(
                model,
                sample_input,
                str(output_path),
                opset_version=opset_version,
                input_names=input_names,
                output_names=output_names,
                dynamic_axes=dynamic_axes,
            )

        logger.info(f"ONNX model exported to {output_path}")

    def _export_torchscript(
        self,
        model: torch.nn.Module,
        output_path: Path,
        sample_input: torch.Tensor,
        **kwargs,
    ):
        model.eval()
        use_trace = kwargs.get("use_trace", True)

        with torch.no_grad():
            if use_trace:
                scripted = torch.jit.trace(model, sample_input)
            else:
                scripted = torch.jit.script(model)

        torch.jit.save(scripted, str(output_path))
        logger.info(f"TorchScript model exported to {output_path}")

    def _serialize_preprocessing(self, preprocessing_params: Dict[str, Any]) -> dict:
        result = {}

        scaler = preprocessing_params.get("scaler")
        if scaler is not None:
            scaler_type = type(scaler).__name__
            scaler_data = {
                "type": scaler_type,
                "mean_": getattr(scaler, "mean_", None),
                "scale_": getattr(scaler, "scale_", None),
                "var_": getattr(scaler, "var_", None),
                "n_samples_seen_": getattr(scaler, "n_samples_seen_", None),
                "min_": getattr(scaler, "min_", None),
                "max_": getattr(scaler, "max_", None),
            }
            for key in ("mean_", "scale_", "var_", "min_", "max_"):
                val = scaler_data[key]
                if val is not None:
                    try:
                        val = val.tolist()
                    except AttributeError:
                        pass
                    scaler_data[key] = val
            if scaler_data["n_samples_seen_"] is not None:
                n = scaler_data["n_samples_seen_"]
                try:
                    scaler_data["n_samples_seen_"] = int(n)
                except (TypeError, ValueError):
                    pass
            result["scaler"] = scaler_data

        optional_keys = [
            "normalization_method",
            "sequence_length",
            "input_dim",
            "feature_names",
            "kalman_process_noise",
            "kalman_measurement_noise",
        ]
        for key in optional_keys:
            value = preprocessing_params.get(key)
            if value is not None:
                if isinstance(value, (list, tuple)):
                    result[key] = list(value)
                else:
                    result[key] = value

        return result

    def _create_manifest(
        self,
        model_type: str,
        export_format: ExportFormat,
        preprocessing_params: Dict[str, Any],
        file_hashes: Dict[str, str],
    ) -> dict:
        manifest = {
            "model_type": model_type,
            "export_format": export_format.value,
            "files": {
                name: {"sha256": hash_value}
                for name, hash_value in file_hashes.items()
            },
            "preprocessing": {
                "has_scaler": preprocessing_params.get("scaler") is not None,
                "normalization_method": preprocessing_params.get("normalization_method"),
                "sequence_length": preprocessing_params.get("sequence_length"),
                "input_dim": preprocessing_params.get("input_dim"),
                "feature_names": preprocessing_params.get("feature_names"),
            },
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        if preprocessing_params.get("kalman_process_noise") is not None:
            manifest["preprocessing"]["kalman_process_noise"] = preprocessing_params["kalman_process_noise"]
        if preprocessing_params.get("kalman_measurement_noise") is not None:
            manifest["preprocessing"]["kalman_measurement_noise"] = preprocessing_params["kalman_measurement_noise"]

        return manifest

    @staticmethod
    def _compute_sha256(file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
