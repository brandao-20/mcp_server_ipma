# MCP Server IPMA
[![smithery badge](https://smithery.ai/badge/@brandao-20/mcp_server_ipma)](https://smithery.ai/server/@brandao-20/mcp_server_ipma)

Um servidor MCP (Model Context Protocol) que fornece acesso aos dados meteorológicos do IPMA (Instituto Português do Mar e da Atmosfera) através de linguagem natural.

## Funcionalidades

- **Previsão Meteorológica**: Obter previsões para qualquer cidade de Portugal
- **Avisos Meteorológicos**: Consultar avisos ativos em tempo real
- **Dados Sísmicos**: Aceder a informações sobre terramotos recentes
- **Estações Meteorológicas**: Observações em tempo real das estações do IPMA
- **Índice UV**: Previsões do índice ultravioleta
- **Listagem de Locais**: Ver todas as cidades disponíveis

## Instalação e Configuração

### Instalando via Smithery

Para instalar ipma-mcp-server para Claude Desktop automaticamente via [Smithery](https://smithery.ai/server/@DiogoAzevedo03/ipma-mcp-server):

```bash
npx -y @smithery/cli@latest install @brandao-20/mcp_server_ipma --client claude
```

### 1. Clonar e Instalar Dependências

```bash
# Criar diretório do projeto
git clone https://github.com/brandao-20/mcp_server_ipma.git
cd mcp_server_ipma

# Instalar dependências
npm install
```

### 2. Correr o Projeto

```bash
npm start
```

### 3. Configurar no Claude Desktop

Editar o arquivo de configuração do Claude Desktop:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

Adicionar a configuração:

```json
{
  "mcpServers": {
    "mcp_server_ipma": {
      "command": "node",
      "args": ["C:\\Users\\nome_user\\mcp_server_ipma\\src\\index.js"],
      "env": {}
    }
  }
}
```

### 4. Reiniciar o Claude Desktop

Após guardar a configuração, reinicie o Claude Desktop.

## Ferramentas Disponíveis

### `get_locations`
Listar todas as cidades disponíveis para previsão.

**Exemplo de uso:**
```
Quais cidades posso consultar a previsão do tempo?
```

### `get_weather_forecast`
Obter previsão meteorológica para uma cidade específica.

**Parâmetros:**
- `city` (obrigatório): Nome da cidade (exemplo "Braga")
- `days` (opcional): Número de dias de previsão

**Exemplo de uso:**
```
Qual é a previsão do tempo para Braga nos próximos 2 dias?
```

### `get_weather_warnings`
Obter avisos meteorológicos ativos em Portugal.

**Exemplo de uso:**
```
Há algum aviso meteorológico ativo?
```

### `get_uv_forecast`
Obter previsão do índice UV.

**Exemplo de uso:**
```
Qual é a previsão do índice UV para hoje?
```

### `get_seismic_data`
Obter dados sísmicos recentes.

**Parâmetros:**
- `area` (opcional): "continent", "azores", "madeira", ou "all" (padrão: "all")

**Exemplo de uso:**
```
Mostra-me os terramotos recentes nos Açores
```

## Exemplos de Uso

Após configurar o servidor, pode fazer perguntas como:

- "Qual é a previsão do tempo para Viana do Castelo esta semana?"
- "Há avisos de chuva forte para hoje?"
- "Qual é o índice UV previsto para Braga?"

## Desenvolvimento

### Estrutura do Projeto

```
mcp_server_ipma/
├── src/
│   └── index.js          
├── package-lock.json               
├── package.json  
├── README.md              
└── smithery.yaml     
       
```

## API IPMA

Este servidor usa a API pública do IPMA. Principais endpoints utilizados:

- Previsões meteorológicas por cidade
- Avisos meteorológicos
- Dados sísmicos
- Observações das estações
- Índice UV
- Lista de locais disponíveis

## Links Úteis

- [IPMA Official Website](https://www.ipma.pt)
- [IPMA API Documentation](https://api.ipma.pt)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [Claude Desktop](https://claude.ai/desktop)