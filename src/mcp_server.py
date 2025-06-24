"""Servidor MCP IPMA (JSON-RPC 2.0 em /rpc)."""

from __future__ import annotations
import logging
import os
from typing import Any, Dict, List

import requests
from cachetools import TTLCache
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv()

DISTRICTS_URL = os.getenv("IPMA_DISTRICTS_URL")
WEATHER_TYPES_URL = os.getenv("IPMA_WEATHER_TYPES_URL")
FORECAST_URL = os.getenv("IPMA_FORECAST_URL")
WARNINGS_URL = os.getenv("IPMA_WARNINGS_URL")
OBS_URL = os.getenv("IPMA_OBS_URL")

app = Flask(__name__)
CORS(app)

logging.basicConfig(
    filename="src/mcp_server.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

cache: TTLCache[str, Any] = TTLCache(maxsize=128, ttl=600)
district_mapping: Dict[str, Dict[str, Any]] = {}
city_mapping: Dict[str, str] = {}
name_to_gid: Dict[str, str] = {}
weather_types: Dict[int, str] = {}


def _safe_get(url: str) -> dict:
    try:
        return requests.get(url, timeout=10).json()
    except Exception as exc:
        logging.error("Falha a obter %s: %s", url, exc)
        return {}


def load_districts() -> None:
    data = cache.setdefault("districts", _safe_get(DISTRICTS_URL))
    district_mapping.clear()
    city_mapping.clear()
    name_to_gid.clear()

    for item in data.get("data", []):
        did = str(item.get("idDistrito"))
        gid = str(item.get("globalIdLocal"))
        name = item.get("local", "Desconhecido")
        district_mapping.setdefault(
            did, {"name": name, "cities": {}}
        )["cities"][gid] = name
        city_mapping[gid] = name
        name_to_gid[name.lower()] = gid

    logging.info(
        "Cidades: %d — Distritos: %d",
        len(city_mapping),
        len(district_mapping),
    )


def load_weather_types() -> None:
    data = cache.setdefault(
        "weather_types", _safe_get(WEATHER_TYPES_URL)
    )
    weather_types.clear()
    for item in data.get("data", []):
        weather_types[item["idWeatherType"]] = item[
            "descWeatherTypePT"
        ]
    logging.info("Tipos de tempo: %d", len(weather_types))


load_districts()
load_weather_types()


def _ipma_forecast_for_gid(gid: str) -> List[Dict[str, Any]]:
    key = f"forecast_{gid}"
    data = cache.setdefault(
        key, _safe_get(FORECAST_URL.format(id=gid))
    )
    return data.get("data", [])


def get_forecast(city: str) -> Dict[str, Any]:
    gid = name_to_gid.get(city.lower())
    if not gid:
        raise ValueError(f"Cidade '{city}' não encontrada")
    previsoes = _ipma_forecast_for_gid(gid)
    if not previsoes:
        raise RuntimeError(f"Sem previsão para {city}")
    hoje = previsoes[0]
    text = (
        f"Meteorologia para hoje em {city} "
        f"({hoje['forecastDate']}):\n"
        f"Condição: "
        f"{weather_types.get(hoje['idWeatherType'], 'N/A')}\n"
        f"Temperatura: {hoje['tMin']}°C a {hoje['tMax']}°C\n"
        f"Probabilidade de Precipitação: "
        f"{hoje['precipitaProb']}%\n"
        f"Direção do Vento: {hoje['predWindDir']}\n"
        f"Velocidade do Vento: {hoje['classWindSpeed']}"
    )
    return {"content": [{"type": "text", "text": text}], "isError": False}


TOOLS_LIST = [
    {
        "name": "get_forecast",
        "description": "Previsão diária IPMA",
        "inputSchema": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    }
]


def _json_rpc_error(
    code: int, msg: str, _id: Any | None = None
) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": _id,
        "error": {"code": code, "message": msg},
    }


@app.post("/rpc")
def rpc() -> Any:  # type: ignore[return-value]
    payload = request.get_json() or {}
    _id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params", {})

    if payload.get("jsonrpc") != "2.0" or not method:
        return _json_rpc_error(-32600, "Inválido", _id), 400

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": _id,
            "result": {"tools": TOOLS_LIST},
        }

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        if name != "get_forecast":
            return _json_rpc_error(
                -32601, "Tool não existe", _id
            ), 404
        city = args.get("city", "")
        try:
            result = get_forecast(str(city))
        except ValueError as exc:
            return _json_rpc_error(-32602, str(exc), _id), 400
        except Exception as exc:
            logging.exception("Erro interno")
            return _json_rpc_error(-32000, str(exc), _id), 500
        return {"jsonrpc": "2.0", "id": _id, "result": result}

    return _json_rpc_error(-32601, "Método desconhecido", _id), 404


@app.get("/mcp/districts")
def rest_districts():
    return jsonify({"districts": district_mapping})


@app.post("/mcp/previsao")
def rest_previsao():
    body = request.get_json() or {}
    gid = str(body.get("global_id", ""))
    if gid not in city_mapping:
        return jsonify({"error": "global_id inválido"}), 400
    previsoes = _ipma_forecast_for_gid(gid)
    resp = [
        {
            "data": f["forecastDate"],
            "cidade": city_mapping[gid],
            "previsao": weather_types.get(
                f["idWeatherType"], "N/A"
            ),
            "temperatura_min": f["tMin"],
            "temperatura_max": f["tMax"],
            "precipitacao_prob": f["precipitaProb"],
            "vento_dir": f["predWindDir"],
            "vento_vel": f["classWindSpeed"],
        }
        for f in previsoes
    ]
    return jsonify({"previsoes": resp})


@app.get("/mcp/observations")
def rest_observations():
    data = cache.setdefault("obs", _safe_get(OBS_URL))
    return jsonify({"observacoes": data.get("data", [])})


@app.get("/mcp/warnings")
def rest_warnings():
    data = cache.setdefault(
        "warnings", _safe_get(WARNINGS_URL)
    )
    return jsonify({"avisos": data.get("data", [])})


# ——— health‐check obrigatório para o Smithery ——— #
@app.get("/")
def health() -> Any:
    """Health‐check para Smithery."""
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
