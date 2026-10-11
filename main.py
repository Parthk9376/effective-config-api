
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def to_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes", "on")


def normalize_key(key):
    key = key.strip().lower()
    if key == "num_workers":
        return "workers"
    return key


def convert_value(key, value):
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        return to_bool(value)
    if key in ("log_level", "api_key"):
        return str(value)
    return value


def load_config():
    # Layer 1: hardcoded defaults
    config = DEFAULTS.copy()

    # Layer 2: YAML configuration
    yaml_path = Path("config.development.yaml")
    if yaml_path.exists():
        with yaml_path.open("r", encoding="utf-8") as file:
            yaml_data = yaml.safe_load(file) or {}

        if isinstance(yaml_data, dict):
            for key, value in yaml_data.items():
                key = normalize_key(key)
                if key in config:
                    config[key] = value

    # Layer 3: .env file
    # Do not override OS environment variables already present.
    load_dotenv(override=False)

    for key in config:
        env_key = "APP_" + (
            "NUM_WORKERS" if key == "workers" else key.upper()
        )
        value = os.environ.get(env_key)
        if value is not None:
            config[key] = value

    # Convert values to their required types.
    for key in config:
        config[key] = convert_value(key, config[key])

    return config


@app.get("/")
def home():
    return {
        "status": "ok",
        "service": "effective-config-api"
    }


@app.get("/effective-config")
async def effective_config(request: Request):
    config = load_config()

    # Layer 5: CLI-style overrides, e.g.
    # ?set=port=8321&set=workers=9
    for item in request.query_params.getlist("set"):
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        key = normalize_key(key)

        if key in config:
            config[key] = convert_value(key, value)

    # Mask the secret in the response using exactly four stars.
    config["api_key"] = "****"

    return config
