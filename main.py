
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import yaml

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

def load_config():
    config = DEFAULTS.copy()

    # Layer 2: YAML
    yaml_path = Path("config.development.yaml")
    if yaml_path.exists():
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f) or {}
            config.update(data)

    # Layer 3: .env
    load_dotenv(override=False)
    for key, value in os.environ.items():
        if key.startswith("APP_"):
            name = key[4:].lower()
            if name == "num_workers":
                name = "workers"
            config[name] = value

    # Type conversion
    for key in ("port", "workers"):
        config[key] = int(config[key])

    value = str(config["debug"]).strip().lower()
    config["debug"] = value in ("true", "1", "yes", "on")

    for key in ("log_level", "api_key"):
        config[key] = str(config[key])

    return config

@app.get("/")
def home():
    return {"status": "ok", "service": "effective-config-api"}

@app.get("/effective-config")
async def effective_config(request: Request):
    config = load_config()

    # Highest precedence: CLI-style query parameters
    for key, value in request.query_params.multi_items():
        if key.lower() == "set":
            continue

    # Each set parameter contains key=value
    for item in request.query_params.getlist("set"):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip().lower()

        if key == "num_workers":
            key = "workers"

        if key in config:
            config[key] = value

    config["port"] = int(config["port"])
    config["workers"] = int(config["workers"])

    value = str(config["debug"]).strip().lower()
    config["debug"] = value in ("true", "1", "yes", "on")

    config["api_key"] = "*****"

    return config
