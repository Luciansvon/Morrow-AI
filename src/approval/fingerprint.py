"""Pembuatan sidik jari hash parameter untuk mendeteksi perubahan parameter aksi luar."""

import hashlib
import json
from typing import Any


class ParameterFingerprinter:
    """Menghasilkan hash SHA256 stabil dari parameter aksi luar."""

    @staticmethod
    def generate_hash(action_type: str, parameters: dict[str, Any]) -> str:
        # Serialisasi parameter dengan sort_keys agar urutan deterministik
        canonical_str = f"{action_type}:{json.dumps(parameters, sort_keys=True)}"
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    @staticmethod
    def verify_hash(action_type: str, parameters: dict[str, Any], expected_hash: str) -> bool:
        calculated = ParameterFingerprinter.generate_hash(action_type, parameters)
        return calculated == expected_hash


fingerprinter = ParameterFingerprinter()
