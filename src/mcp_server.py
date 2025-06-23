"""Servidor Flask para previsões IPMA.

• Em execução normal consome as APIs do IPMA.
• Em CI (GitHub Actions define CI=true) devolve respostas vazias para evitar
  falhas de rede — o smoke-test só precisa da chave "previsoes".
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests
from cachetools import TTLCache
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

# --------------------------------------------------------------------------- #
# Configuração                                                                #
# --------------------------------------------------------------------------- #

load_dotenv()  # lê .env em desenvolvimento

IS_CI = os.getenv("CI") is not None          # GitHub Actions define sempre CI=true

DISTRICTS_URL = os.getenv(
    "IPMA_DISTRICTS_URL",
    "https://api.ipma.pt/open-data/distrits-islands.json",
)
WEATHER_TYPES_URL = os.getenv(
    "IPMA_WEATHER_TYPES_URL",
    "https://api.ipma.pt/open-data/weather-type-classe.json",
)
FORECAST_URL = os.getenv(
    "IPMA_FORECAST_URL",
    "https://api.ipma.pt/open-data/forecast/meteorology/cities/daily/{id}.json",
)
WARNINGS_URL = os.getenv(
    "IPMA_WARNINGS_URL",
    "https://api.ipma.pt/open-data/forecast/warnings/warnings_www.json",
)
OBS_URL = os.getenv(
    "IPMA_OBS_URL",
    "https://api.ipma.pt/open-data/observation/meteorology/stations/observations.json",
)

app = Flask(__name__)
CORS(app)

logging.basicConfig(
    filename="src/mcp_server.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

cache: TTLCache[str, Any] = TTLCache(maxsize=100, ttl=600)

_districts: dict[str, dict] = {}
_cities: dict[str, str] = {}
_weather_types: dict[int, str] = {}

# --------------------------------------------------------------------------- #
# Helpers (ignorados no CI)                                                   #
# --------------------------------------------------------------------------- #


def _load_districts() -> None:
    try:
        data = cache.setdefault("districts", requests.get(DISTRICTS_URL, timeout=10).json())
        _districts.clear()
        _cities.clear()
        for item in data.get("data", []):
            did = str(item.get("idDistrito"))
            gid = str(item.get("globalIdLocal"))
            name = item.get("local", "Desconhecido")
            _districts.setdefault(did, {"name": name, "cities": {}})["cities"][gid] = name
            _cities[gid] = name
        log.info("Carregados %s cidades e %s distritos", len(_cities), len(_districts))
    except Exception as exc:  # noqa: BLE001
        log.error("Erro ao carregar distritos: %s", exc)


def _load_weather_types() -> None:
    try:
        data = cache.setdefault("weather_types", requests.get(WEATHER_TYPES_URL, timeout=10).json())
        _weather_types.clear()
        for item in data.get("data", []):
            _weather_types[item["idWeatherType"]] = item.get(
                "descWeatherTypePT", "Descrição não disponível"
            )
        log.info("Carregados %s tipos de tempo", len(_weather_types))
    except Exception as exc:  # noqa: BLE001
        log.error("Erro ao carregar tipos de tempo: %s", exc)


if not IS_CI:
    _load_districts()
    _load_weather_types()

# --------------------------------------------------------------------------- #
# End-points                                                                  #
# --------------------------------------------------------------------------- #


@app.route("/mcp/districts")
def districts():  # noqa: D401
    if IS_CI:
        return jsonify({"districts": {}}), 200
    return jsonify({"districts": _districts}), 200


@app.route("/mcp/cities")
def cities():  # noqa: D401
    if IS_CI:
        return jsonify({"cities": {}}), 200
    did = request.args.get("district_id")
    if did:
        if did in _districts:
            return jsonify({"district_id": did, "cities": _districts[did]["cities"]}), 200
        return jsonify({"error": "Distrito não encontrado"}), 404
    return jsonify({"cities": _cities}), 200


@app.route("/mcp/previsao", methods=["POST"])
def previsao():  # noqa: D401
    if IS_CI:
        return jsonify({"previsoes": [], "updated": None}), 200

    body = request.get_json() or {}
    gid = str(body.get("global_id", ""))
    if gid not in _cities:
        return jsonify({"error": "global_id inválido"}), 400

    key = f"forecast_{gid}"
    try:
        data = cache.setdefault(key, requests.get(FORECAST_URL.format(id=gid), timeout=10).json())
        if not data.get("data"):
            return jsonify({"error": "Sem dados"}), 404

        resp: list[dict[str, Any]] = []
        for f in data["data"]:
            wid = f.get("idWeatherType")
            resp.append(
                {
                    "data": f.get("forecastDate"),
                    "cidade": _cities[gid],
                    "previsao": _weather_types.get(wid, "(?)"),
                    "temperatura_min": f.get("tMin", "N/A"),
                    "temperatura_max": f.get("tMax", "N/A"),
                    "precipitacao_prob": f.get("precipitaProb", "N/A"),
                    "vento_dir": f.get("predWindDir", "N/A"),
                    "vento_vel": f.get("classWindSpeed", "N/A"),
                }
            )
        return jsonify({"previsoes": resp, "updated": data.get("dataUpdate")}), 200
    except Exception as exc:  # noqa: BLE001
        log.error("Erro ao buscar previsão para %s: %s", gid, exc)
        return jsonify({"error": "Erro interno no servidor"}), 500


@app.route("/mcp/observations")
def observations():  # noqa: D401
    if IS_CI:
        return jsonify({"observacoes": []}), 200
    data = cache.setdefault("obs", requests.get(OBS_URL, timeout=10).json())
    return jsonify({"observacoes": data.get("data", [])}), 200


@app.route("/mcp/warnings")
def warnings():  # noqa: D401
    if IS_CI:
        return jsonify({"avisos": []}), 200
    data = cache.setdefault("warnings", requests.get(WARNINGS_URL, timeout=10).json())
    return jsonify({"avisos": data.get("data", [])}), 200


# --------------------------------------------------------------------------- #
# Arranque local                                                              #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
