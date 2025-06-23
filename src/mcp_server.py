from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import os, requests, logging
from cachetools import TTLCache

# Carrega .env
load_dotenv()
DISTRICTS_URL     = os.getenv("IPMA_DISTRICTS_URL")
WEATHER_TYPES_URL = os.getenv("IPMA_WEATHER_TYPES_URL")
FORECAST_URL      = os.getenv("IPMA_FORECAST_URL")
WARNINGS_URL      = os.getenv("IPMA_WARNINGS_URL")
OBS_URL           = os.getenv("IPMA_OBS_URL")

# App e CORS
app = Flask(__name__)
CORS(app)

# Logging
logging.basicConfig(filename="src/mcp_server.log",
                    level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# Cache TTL 10m
cache = TTLCache(maxsize=100, ttl=600)

# Mappings
district_mapping = {}
city_mapping     = {}
weather_types    = {}

def load_districts():
    try:
        data = cache.setdefault("districts", requests.get(DISTRICTS_URL, timeout=10).json())
        district_mapping.clear()
        city_mapping.clear()
        for item in data["data"]:
            d = str(item["idDistrito"])
            c = str(item["globalIdLocal"])
            name = item.get("local", "Desconhecido")
            district_mapping.setdefault(d, {"name": name, "cities": {}})["cities"][c] = name
            city_mapping[c] = name
        logging.info(f"Carregados {len(city_mapping)} cidades e {len(district_mapping)} distritos")
    except Exception as e:
        logging.error(f"Erro ao carregar distritos: {str(e)}")

def load_weather_types():
    try:
        data = cache.setdefault("weather_types", requests.get(WEATHER_TYPES_URL, timeout=10).json())
        logging.info(f"Dados brutos da API de tipos de tempo: {data}")
        weather_types.clear()
        for item in data["data"]:
            wid = item["idWeatherType"]
            desc = item.get("descWeatherTypePT", "Descrição não disponível no momento")
            weather_types[wid] = desc
            logging.debug(f"Tipo de tempo {wid}: {desc}")
        logging.info(f"Carregados {len(weather_types)} tipos de tempo")
    except Exception as e:
        logging.error(f"Erro ao carregar tipos de tempo: {str(e)}")

# Inicializa
load_districts()
load_weather_types()

@app.route("/mcp/districts")
def get_districts():
    return jsonify({"districts": district_mapping}), 200

@app.route("/mcp/cities")
def get_cities():
    d = request.args.get("district_id")
    if d:
        if d in district_mapping:
            return jsonify({"district_id": d, "cities": district_mapping[d]["cities"]}), 200
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
        data = cache.setdefault(key, requests.get(FORECAST_URL.format(id=gid), timeout=10).json())
        logging.info(f"Dados brutos da API de previsão para global_id {gid}: {data}")
        if not data.get("data"):
            return jsonify({"error": "Sem dados"}), 404

        resp = []
        for f in data["data"]:
            wid = f["idWeatherType"]
            if wid not in weather_types:
                logging.warning(f"Tipo de tempo {wid} não encontrado em weather_types")
            resp.append({
                "data": f["forecastDate"],
                "cidade": city_mapping[gid],
                "previsao": weather_types.get(wid, "Descrição não disponível no momento"),
                "temperatura_min": f.get("tMin", "N/A"),
                "temperatura_max": f.get("tMax", "N/A"),
                "precipitacao_prob": f.get("precipitaProb", "N/A"),
                "vento_dir": f.get("predWindDir", "N/A"),
                "vento_vel": f.get("classWindSpeed", "N/A")
            })
        return jsonify({"previsoes": resp, "updated": data.get("dataUpdate")}), 200
    except Exception as e:
        logging.error(f"Erro ao buscar previsão para global_id {gid}: {str(e)}")
        return jsonify({"error": "Erro interno no servidor"}), 500

@app.route("/mcp/observations")
def observations():
    data = cache.setdefault("obs", requests.get(OBS_URL, timeout=10).json())
    return jsonify({"observacoes": data.get("data", [])}), 200

@app.route("/mcp/warnings")
def warnings():
    data = cache.setdefault("warnings", requests.get(WARNINGS_URL, timeout=10).json())
    return jsonify({"avisos": data.get("data", [])}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)