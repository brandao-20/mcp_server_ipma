from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import os
import requests
import logging
from cachetools import TTLCache

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
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

cache = TTLCache(maxsize=100, ttl=600)
district_mapping = {}
city_mapping = {}
weather_types = {}

def load_districts():
    try:
        data = cache.setdefault(
            "districts",
            requests.get(DISTRICTS_URL, timeout=10).json()
        )
        district_mapping.clear()
        city_mapping.clear()
        for item in data.get("data", []):
            did = str(item.get("idDistrito"))
            gid = str(item.get("globalIdLocal"))
            name = item.get("local", "Desconhecido")
            entry = district_mapping.setdefault(
                did, {"name": name, "cities": {}}
            )
            entry["cities"][gid] = name
            city_mapping[gid] = name
        logging.info(
            f"Carregados {len(city_mapping)} cidades e "
            f"{len(district_mapping)} distritos"
        )
    except Exception as e:
        logging.error(f"Erro ao carregar distritos: {e}")

def load_weather_types():
    try:
        data = cache.setdefault(
            "weather_types",
            requests.get(WEATHER_TYPES_URL, timeout=10).json()
        )
        weather_types.clear()
        for item in data.get("data", []):
            wid = item.get("idWeatherType")
            desc = item.get(
                "descWeatherTypePT",
                "Descrição não disponível"
            )
            weather_types[wid] = desc
        logging.info(f"Carregados {len(weather_types)} tipos de tempo")
    except Exception as e:
        logging.error(f"Erro ao carregar tipos de tempo: {e}")

# inicialização
load_districts()
load_weather_types()

@app.route("/mcp/districts")
def get_districts():
    return jsonify({"districts": district_mapping}), 200

@app.route("/mcp/cities")
def get_cities():
    did = request.args.get("district_id")
    if did:
        if did in district_mapping:
            return (
                jsonify({
                    "district_id": did,
                    "cities": district_mapping[did]["cities"]
                }),
                200
            )
        return jsonify({"error": "Distrito não encontrado"}), 404
    return jsonify({"cities": city_mapping}), 200

@app.route("/mcp/previsao", methods=["POST"])
def previsao():
    body = request.get_json() or {}
    gid = str(body.get("global_id", ""))
    if gid not in city_mapping:
        return jsonify({"error": "global_id inválido"}), 400

    key = f"forecast_{gid}"
    try:
        data = cache.setdefault(
            key,
            requests.get(
                FORECAST_URL.format(id=gid),
                timeout=10
            ).json()
        )
        if not data.get("data"):
            return jsonify({"error": "Sem dados"}), 404

        resp = []
        for f in data["data"]:
            wid = f.get("idWeatherType")
            if wid not in weather_types:
                logging.warning(
                    f"Tipo de tempo {wid} não encontrado"
                )
            resp.append({
                "data": f.get("forecastDate"),
                "cidade": city_mapping[gid],
                "previsao": weather_types.get(
                    wid,
                    "Descrição não disponível"
                ),
                "temperatura_min": f.get("tMin", "N/A"),
                "temperatura_max": f.get("tMax", "N/A"),
                "precipitacao_prob": f.get("precipitaProb", "N/A"),
                "vento_dir": f.get("predWindDir", "N/A"),
                "vento_vel": f.get("classWindSpeed", "N/A")
            })
        return (
            jsonify({
                "previsoes": resp,
                "updated": data.get("dataUpdate")
            }),
            200
        )
    except Exception as e:
        logging.error(f"Erro na previsão {gid}: {e}")
        return jsonify({"error": "Erro interno"}), 500

@app.route("/mcp/observations")
def observations():
    data = cache.setdefault(
        "obs",
        requests.get(OBS_URL, timeout=10).json()
    )
    return jsonify({"observacoes": data.get("data", [])}), 200

@app.route("/mcp/warnings")
def warnings():
    data = cache.setdefault(
        "warnings",
        requests.get(WARNINGS_URL, timeout=10).json()
    )
    return jsonify({"avisos": data.get("data", [])}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)