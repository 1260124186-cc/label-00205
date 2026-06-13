import base64
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from loguru import logger


@dataclass
class ModelPackage:
    package_id: str
    model_type: str
    version: str
    model_file: str
    manifest_file: str
    preprocessing_file: str
    signature_file: str
    created_at: str
    file_hashes: Dict[str, str]
    metadata: Dict[str, Any]


@dataclass
class IntegrityResult:
    is_valid: bool
    checked_files: int
    failed_files: List[str]
    signature_valid: bool
    manifest_valid: bool
    errors: List[str]


class PackageSigner:
    def __init__(self, private_key_path: Optional[str] = None):
        self._private_key_path = private_key_path
        self._private_key, self._public_key = self._load_or_generate_key()

    def _load_or_generate_key(self) -> tuple:
        if self._private_key_path and Path(self._private_key_path).exists():
            logger.info("Loading existing private key from {}", self._private_key_path)
            key_data = Path(self._private_key_path).read_bytes()
            private_key = serialization.load_pem_private_key(key_data, password=None)
            public_key = private_key.public_key()
            return private_key, public_key

        logger.info("Generating new RSA key pair (2048-bit)")
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        public_key = private_key.public_key()

        if self._private_key_path:
            key_dir = Path(self._private_key_path).parent
            key_dir.mkdir(parents=True, exist_ok=True)
            pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            Path(self._private_key_path).write_bytes(pem)
            logger.info("Saved private key to {}", self._private_key_path)

        return private_key, public_key

    def sign_package(self, package_dir: str) -> str:
        package_path = Path(package_dir)
        file_hashes: Dict[str, str] = {}

        for file_path in sorted(package_path.rglob("*")):
            if file_path.is_file() and file_path.name != "signature.json":
                relative = file_path.relative_to(package_path).as_posix()
                file_hashes[relative] = hashlib.sha256(file_path.read_bytes()).hexdigest()

        hash_payload = json.dumps(file_hashes, sort_keys=True)
        signature_bytes = self._private_key.sign(
            hash_payload.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )

        public_key_pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        signature_data = {
            "signature": base64.b64encode(signature_bytes).decode("utf-8"),
            "public_key": base64.b64encode(public_key_pem).decode("utf-8"),
            "files": file_hashes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "algorithm": "RSA-SHA256",
        }

        signature_path = package_path / "signature.json"
        signature_path.write_text(json.dumps(signature_data, indent=2), encoding="utf-8")
        logger.info("Package signed, signature written to {}", signature_path)
        return str(signature_path)

    def verify_signature(self, package_dir: str) -> bool:
        package_path = Path(package_dir)
        signature_path = package_path / "signature.json"

        if not signature_path.exists():
            logger.error("signature.json not found in {}", package_dir)
            return False

        try:
            signature_data = json.loads(signature_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to read signature.json: {}", exc)
            return False

        stored_hashes = signature_data.get("files", {})
        current_hashes: Dict[str, str] = {}
        for file_path in sorted(package_path.rglob("*")):
            if file_path.is_file() and file_path.name != "signature.json":
                relative = file_path.relative_to(package_path).as_posix()
                current_hashes[relative] = hashlib.sha256(file_path.read_bytes()).hexdigest()

        if current_hashes != stored_hashes:
            logger.error("File hash mismatch detected")
            return False

        hash_payload = json.dumps(stored_hashes, sort_keys=True)

        try:
            signature_bytes = base64.b64decode(signature_data["signature"])
            public_key_pem = base64.b64decode(signature_data["public_key"])
            public_key = serialization.load_pem_public_key(public_key_pem)
            public_key.verify(
                signature_bytes,
                hash_payload.encode("utf-8"),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            logger.info("Package signature verified successfully")
            return True
        except InvalidSignature:
            logger.error("Invalid package signature")
            return False
        except Exception as exc:
            logger.error("Signature verification failed: {}", exc)
            return False


class IntegrityVerifier:
    def verify_package(self, package_dir: str) -> IntegrityResult:
        package_path = Path(package_dir)
        errors: List[str] = []
        failed_files: List[str] = []
        checked_files = 0
        signature_valid = False
        manifest_valid = False

        signature_path = package_path / "signature.json"
        if not signature_path.exists():
            errors.append("signature.json not found")
        else:
            try:
                signature_data = json.loads(signature_path.read_text(encoding="utf-8"))
                file_hashes = signature_data.get("files", {})
                for filename, expected_hash in file_hashes.items():
                    file_path = package_path / filename
                    checked_files += 1
                    if not self._verify_file_hash(file_path, expected_hash):
                        failed_files.append(filename)
                        errors.append(f"Hash mismatch for {filename}")
                signer = PackageSigner()
                signature_valid = signer.verify_signature(package_dir)
                if not signature_valid:
                    errors.append("Signature verification failed")
            except (json.JSONDecodeError, OSError) as exc:
                errors.append(f"Failed to read signature.json: {exc}")

        manifest_valid = self._verify_manifest_consistency(package_dir)
        if not manifest_valid:
            errors.append("Manifest consistency check failed")

        is_valid = len(failed_files) == 0 and signature_valid and manifest_valid and len(errors) == 0

        return IntegrityResult(
            is_valid=is_valid,
            checked_files=checked_files,
            failed_files=failed_files,
            signature_valid=signature_valid,
            manifest_valid=manifest_valid,
            errors=errors,
        )

    def _verify_file_hash(self, file_path: Path, expected_hash: str) -> bool:
        if not file_path.exists():
            logger.error("File not found: {}", file_path)
            return False
        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            logger.error("Hash mismatch for {}: expected {}, got {}", file_path, expected_hash, actual_hash)
            return False
        return True

    def _verify_manifest_consistency(self, package_dir: Path) -> bool:
        package_path = Path(package_dir)
        package_json_path = package_path / "package.json"
        if not package_json_path.exists():
            logger.error("package.json not found in {}", package_dir)
            return False

        try:
            package_data = json.loads(package_json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to read package.json: {}", exc)
            return False

        for key in ("model_file", "manifest_file", "preprocessing_file"):
            filename = package_data.get(key, "")
            if not filename:
                logger.error("Missing '{}' in package.json", key)
                return False
            if not (package_path / filename).exists():
                logger.error("Referenced file '{}' not found in package", filename)
                return False

        return True


class PackageBundler:
    def create_package(
        self,
        model_path: str,
        manifest_path: str,
        preprocessing_path: str,
        output_dir: str,
        model_type: str,
        version: str,
        signer: Optional[PackageSigner] = None,
    ) -> ModelPackage:
        model_p = Path(model_path)
        manifest_p = Path(manifest_path)
        preprocessing_p = Path(preprocessing_path)
        output_p = Path(output_dir)

        package_id = str(uuid.uuid4())
        package_dir = output_p / package_id
        package_dir.mkdir(parents=True, exist_ok=True)

        model_dest = package_dir / model_p.name
        manifest_dest = package_dir / manifest_p.name
        preprocessing_dest = package_dir / preprocessing_p.name

        model_dest.write_bytes(model_p.read_bytes())
        manifest_dest.write_bytes(manifest_p.read_bytes())
        preprocessing_dest.write_bytes(preprocessing_p.read_bytes())

        logger.info("Bundled files into {}", package_dir)

        content_hashes: Dict[str, str] = {}
        for f in (model_dest, manifest_dest, preprocessing_dest):
            relative = f.relative_to(package_dir).as_posix()
            content_hashes[relative] = hashlib.sha256(f.read_bytes()).hexdigest()

        created_at = datetime.now(timezone.utc).isoformat()
        signature_file = "signature.json" if signer is not None else ""

        package_json_path = package_dir / "package.json"
        package_json_path.write_text(
            json.dumps(
                {
                    "package_id": package_id,
                    "model_type": model_type,
                    "version": version,
                    "model_file": model_p.name,
                    "manifest_file": manifest_p.name,
                    "preprocessing_file": preprocessing_p.name,
                    "signature_file": signature_file,
                    "created_at": created_at,
                    "file_hashes": content_hashes,
                    "metadata": {},
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        if signer is not None:
            signer.sign_package(str(package_dir))

        all_hashes: Dict[str, str] = {}
        for file_path in package_dir.rglob("*"):
            if file_path.is_file():
                relative = file_path.relative_to(package_dir).as_posix()
                all_hashes[relative] = hashlib.sha256(file_path.read_bytes()).hexdigest()

        logger.info("Package metadata written to {}", package_json_path)

        return ModelPackage(
            package_id=package_id,
            model_type=model_type,
            version=version,
            model_file=model_p.name,
            manifest_file=manifest_p.name,
            preprocessing_file=preprocessing_p.name,
            signature_file=signature_file,
            created_at=created_at,
            file_hashes=all_hashes,
            metadata={},
        )
