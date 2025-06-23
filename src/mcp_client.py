import requests
import argparse
import re

BASE = "http://localhost:5000"

def get_districts():
    return requests.get(f"{BASE}/mcp/districts").json().get("districts", {})

def get_forecast(gid):
    return requests.post(f"{BASE}/mcp/previsao", json={"global_id": gid}).json()

def find_city_global_id(city_name):
    """Find the global_id for a given city name."""
    districts = get_districts()
    city_name = city_name.lower().strip()
    for district_id, district_data in districts.items():
        cities = district_data["cities"]
        for global_id, name in cities.items():
            if name.lower() == city_name:
                return global_id
    return None

def parse_city_from_query(query):
    """Extract the city name from a natural language query."""
    match = re.search(r"em\s+([A-Za-zÀ-ÖØ-öø-ÿ\s]+)$", query, re.IGNORECASE)
    if not match:
        match = re.search(r"para\s+([A-Za-zÀ-ÖØ-öø-ÿ\s]+)$", query, re.IGNORECASE)
    return match.group(1).strip() if match else None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch weather forecast from IPMA API.")
    parser.add_argument("--smoke-test", action="store_true", help="Run a smoke test with Braga's global_id.")
    parser.add_argument("--query", type=str, help="Natural language query, e.g., 'Diz-me a meteorologia para hoje em Braga'")
    args = parser.parse_args()

    if args.smoke_test:
        resp = get_forecast("1030500")
        if "previsoes" in resp:
            print("🎉 Smoke test passou!")
            exit(0)
        else:
            print("Erro: Smoke test falhou. Verifique o servidor.")
            exit(1)

    if not args.query:
        print("Erro: Forneça uma query com --query (exemplo: 'Diz-me a meteorologia para hoje em Braga').")
        exit(1)

    city_name = parse_city_from_query(args.query)
    if not city_name:
        print("Erro: Não foi possível identificar a cidade na query.")
        exit(1)

    global_id = find_city_global_id(city_name)
    if not global_id:
        print(f"Erro: Cidade '{city_name}' não encontrada na lista de cidades.")
        exit(1)

    forecast = get_forecast(global_id).get("previsoes", [])
    if forecast:
        today = forecast[0]
        print(f"\nMeteorologia para hoje em {today['cidade']} ({today['data']}):")
        print(f"Condição: {today['previsao']}")
        print(f"Temperatura: {today['temperatura_min']}°C a {today['temperatura_max']}°C")
        print(f"Probabilidade de Precipitação: {today['precipitacao_prob']}%")
        print(f"Direção do Vento: {today['vento_dir']}")
        print(f"Velocidade do Vento: {today['vento_vel']}")
    else:
        print(f"Sem previsão disponível para {city_name}.")