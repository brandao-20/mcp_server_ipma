from flask import Flask, jsonify, request, render_template
import requests

app = Flask(__name__)

# URL para obter a lista de distritos e cidades
DISTRICTS_URL = "https://api.ipma.pt/open-data/distrits-islands.json"

# Mapeamento de idWeatherType para descrições
WEATHER_TYPES = {
    1: "Céu limpo",
    2: "Céu pouco nublado",
    3: "Céu parcialmente nublado",
    4: "Céu muito nublado",
    5: "Céu nublado",
    6: "Chuva fraca",
    7: "Chuva moderada",
    8: "Chuva forte",
    9: "Chuva fraca ou aguaceiros fracos",
    10: "Chuva ou aguaceiros",
    11: "Chuva forte ou aguaceiros fortes",
    12: "Nevoeiro",
    13: "Neve",
    14: "Trovoada",
}

# Mapeamento de IDs de distritos para nomes
DISTRICT_NAMES = {
    1: "Aveiro",
    2: "Beja",
    3: "Braga",
    4: "Bragança",
    5: "Castelo Branco",
    6: "Coimbra",
    7: "Évora",
    8: "Faro",
    9: "Guarda",
    10: "Leiria",
    11: "Lisboa",
    12: "Portalegre",
    13: "Porto",
    14: "Santarém",
    15: "Setúbal",
    16: "Viana do Castelo",
    17: "Vila Real",
    18: "Viseu",
    19: "Açores",
    20: "Madeira"
}

# Armazenar mapeamento de globalIdLocal para nomes de cidades
city_mapping = {}

# Função para obter a lista de distritos e cidades
def get_districts_and_cities():
    global city_mapping
    response = requests.get(DISTRICTS_URL)
    if response.status_code == 200:
        data = response.json()
        districts = {}
        city_mapping = {}
        for item in data['data']:
            district_id = item['idRegiao']
            district_name = DISTRICT_NAMES.get(district_id, f"Distrito {district_id}")
            city = item['local'].lower()
            global_id = item['globalIdLocal']
            city_mapping[global_id] = item['local']  # Armazena o nome original da cidade
            if district_name not in districts:
                districts[district_name] = []
            districts[district_name].append((city, global_id))
        print("Distritos carregados:", list(districts.keys()))  # Depuração
        return districts
    print("Erro ao carregar distritos da API")
    return {}

# Rota para a página inicial
@app.route('/')
def index():
    districts = get_districts_and_cities()
    return render_template('index.html', districts=districts)

# Rota da API para obter a previsão
@app.route('/mcp/previsao', methods=['POST'])
def previsao():
    try:
        data = request.get_json()
        global_id = data.get('global_id')

        if not global_id:
            return jsonify({"error": "globalIdLocal não fornecido"}), 400

        url = f"https://api.ipma.pt/open-data/forecast/meteorology/cities/daily/{global_id}.json"
        response = requests.get(url)

        if response.status_code != 200:
            return jsonify({"error": "Falha ao consultar a API do IPMA"}), 500

        dados = response.json()
        if 'data' in dados and len(dados['data']) > 0:
            id_tempo = dados['data'][0].get('idWeatherType', 'N/A')
            descricao_tempo = WEATHER_TYPES.get(id_tempo, "Descrição não disponível")
            cidade = dados['data'][0].get('local', city_mapping.get(global_id, "Cidade Desconhecida"))
            resposta = {
                "cidade": cidade,
                "previsao": descricao_tempo,
                "temperatura_min": dados['data'][0].get('tMin', 'N/A'),
                "temperatura_max": dados['data'][0].get('tMax', 'N/A'),
                "icon_url": f"https://www.ipma.pt/bin/weathericons/w_symb_{id_tempo}.png"
            }
            return jsonify(resposta), 200
        else:
            return jsonify({"error": "Nenhum dado de previsão encontrado"}), 500

    except Exception as e:
        return jsonify({"error": "Erro interno no servidor", "detalhes": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)