
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


def normalize_key(key):
    key = key.strip().lower()
    if key == "num_workers":
        return "workers"
    return key


def convert_value(key, value):
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in (
            "true", "1", "yes", "on"
        )

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
    # Existing OS environment variables are not overwritten.
    load_dotenv(override=False)

    # Layer 4: environment variables
    for key in config:
        if key == "workers":
            env_names = [
                "APP_NUM_WORKERS",
                "APP_WORKERS",
            ]
        else:
            env_names = ["APP_" + key.upper()]

        for env_name in env_names:
            value = os.environ.get(env_name)
            if value is not None:
                config[key] = value
                break

    # Convert configuration values to the correct types.
    for key in config:
        config[key] = convert_value(key, config[key])

    return config


@app.get("/")
def home():
    return {
        "status": "ok",
        "service": "effective-config-api",
    }


@app.get("/effective-config")
async def effective_config(request: Request):
    config = load_config()

    # Layer 5: CLI-style overrides.
    # Example: ?set=port=8574&set=debug=true
    for item in request.query_params.getlist("set"):
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        key = normalize_key(key)

        if key in config:
            config[key] = convert_value(key, value)

    # Return a masked API key.
    config["api_key"] = "****"

    return config
