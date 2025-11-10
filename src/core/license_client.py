# src/core/license_client.py
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

API_BASE_URL = "https://license-key-api.up.railway.app"

# pasta onde vamos salvar client_id + license_key
CONFIG_DIR = Path.home() / ".eldorado_placer"
CONFIG_PATH = CONFIG_DIR / "license_config.json"


@dataclass
class LicenseConfig:
    client_id: str
    license_key: Optional[str] = None


@dataclass
class LicenseCheckResult:
    valid: bool
    reason: Optional[str] = None
    raw: Optional[dict] = None


# -------------------------------------------------
# Persistência local
# -------------------------------------------------
def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> LicenseConfig:
    """Carrega client_id + license_key do disco (ou cria um novo client_id)."""
    _ensure_config_dir()
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            client_id = data.get("client_id") or str(uuid.uuid4())
            license_key = data.get("license_key")
            return LicenseConfig(client_id=client_id, license_key=license_key)
        except Exception:
            # Se o arquivo estiver corrompido, gera uma nova config
            pass

    client_id = str(uuid.uuid4())
    cfg = LicenseConfig(client_id=client_id, license_key=None)
    save_config(cfg)
    return cfg


def save_config(cfg: LicenseConfig) -> None:
    _ensure_config_dir()
    payload = {
        "client_id": cfg.client_id,
        "license_key": cfg.license_key,
    }
    CONFIG_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# -------------------------------------------------
# Comunicação com a API de licença
# -------------------------------------------------
def verify_license(license_key: str, client_id: str) -> LicenseCheckResult:
    """
    Chama POST /license/verify na API.

    Possíveis 'reason':
      - "not found"
      - "expired"
      - "bound_to_another_client"
      - "network_error: ..."
      - "invalid_response_status_xxx"
      - None (quando valid == True)
    """
    url = f"{API_BASE_URL}/license/verify"
    try:
        resp = requests.post(
            url,
            json={"key": license_key, "client_id": client_id},
            timeout=10,
        )
    except requests.RequestException as exc:
        return LicenseCheckResult(
            valid=False,
            reason=f"network_error: {exc}",
            raw=None,
        )

    try:
        data = resp.json()
    except Exception:
        return LicenseCheckResult(
            valid=False,
            reason=f"invalid_response_status_{resp.status_code}",
            raw=None,
        )

    valid = bool(data.get("valid"))
    reason = data.get("reason")
    return LicenseCheckResult(valid=valid, reason=reason, raw=data)
