#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema, ErrorCode, McpError } from "@modelcontextprotocol/sdk/types.js";
import fetch from "node-fetch";

class IPMAServer {
  constructor() {
    this.baseUrl = "https://api.ipma.pt/open-data";
    this.server = new Server(
      {
        name: "ipma-weather-server",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
    
    this.server.onerror = (error) => console.error("[MCP Error]", error);
    process.on("SIGINT", async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: "get_weather_forecast",
          description: "Obter previsão meteorológica para uma cidade específica em Portugal",
          inputSchema: {
            type: "object",
            properties: {
              city: {
                type: "string",
                description: "Nome da cidade (ex: Lisboa, Porto, Coimbra, Faro, etc.)"
              },
              days: {
                type: "number",
                description: "Número de dias de previsão (máximo 10)",
                default: 5
              }
            },
            required: ["city"]
          }
        },
        {
          name: "get_weather_warnings",
          description: "Obter avisos meteorológicos ativos em Portugal",
          inputSchema: {
            type: "object",
            properties: {}
          }
        },
        {
          name: "get_seismic_data",
          description: "Obter dados sísmicos recentes",
          inputSchema: {
            type: "object",
            properties: {
              area: {
                type: "string",
                description: "Área: 'continent', 'azores', 'madeira', ou 'all'",
                default: "all"
              }
            }
          }
        },
        {
          name: "get_locations",
          description: "Listar todas as cidades/locais disponíveis para previsão",
          inputSchema: {
            type: "object",
            properties: {}
          }
        },
        {
          name: "get_weather_stations",
          description: "Obter dados de observação das estações meteorológicas",
          inputSchema: {
            type: "object",
            properties: {}
          }
        },
        {
          name: "get_uv_forecast",
          description: "Obter previsão do índice UV",
          inputSchema: {
            type: "object",
            properties: {}
          }
        }
      ]
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      try {
        const { name, arguments: args } = request.params;
        switch (name) {
          case "get_weather_forecast":
            if (!args?.city) {
              throw new McpError(ErrorCode.InvalidParams, "City parameter is required");
            }
            return await this.getWeatherForecast(args.city, args.days || 5);
          case "get_weather_warnings":
            return await this.getWeatherWarnings();
          case "get_seismic_data":
            return await this.getSeismicData(args?.area || "all");
          case "get_locations":
            return await this.getLocations();
          case "get_weather_stations":
            return await this.getWeatherStations();
          case "get_uv_forecast":
            return await this.getUVForecast();
          default:
            throw new McpError(ErrorCode.MethodNotFound, `Tool ${name} not found`);
        }
      } catch (error) {
        if (error instanceof McpError) {
          throw error;
        }
        const errorMessage = error instanceof Error ? error.message : String(error);
        throw new McpError(ErrorCode.InternalError, `Error: ${errorMessage}`);
      }
    });
  }

  async getWeatherForecast(city, days) {
    try {
      const locationsResponse = await fetch(`${this.baseUrl}/distrits-islands.json`);
      const locationsData = await locationsResponse.json();
      
      const location = locationsData.data.find((loc) => 
        loc.local.toLowerCase().includes(city.toLowerCase())
      );

      if (!location) {
        return {
          content: [
            {
              type: "text",
              text: `Cidade "${city}" não encontrada. Use get_locations para ver cidades disponíveis.`
            }
          ]
        };
      }

      const forecastResponse = await fetch(
        `${this.baseUrl}/forecast/meteorology/cities/daily/${location.globalIdLocal}.json`
      );
      const forecastData = await forecastResponse.json();

      const weatherTypesResponse = await fetch(`${this.baseUrl}/weather-type-classe.json`);
      const weatherTypesData = await weatherTypesResponse.json();

      const weatherTypes = weatherTypesData.data.reduce((acc, item) => {
        acc[item.idWeatherType] = item;
        return acc;
      }, {});

      const limitedData = forecastData.data.slice(0, days);
      
      let result = `📍 **Previsão para ${location.local}**\n\n`;
      result += `📍 Coordenadas: ${location.latitude}, ${location.longitude}\n`;
      result += `🕐 Última atualização: ${forecastData.dataUpdate}\n\n`;

      limitedData.forEach((day) => {
        const weatherDesc = weatherTypes[day.idWeatherType]?.descWeatherTypePT || "Desconhecido";
        result += `📅 **${day.forecastDate}**\n`;
        result += `🌡️ Temperatura: ${day.tMin}°C - ${day.tMax}°C\n`;
        result += `☁️ Condições: ${weatherDesc}\n`;
        result += `🌧️ Probabilidade de precipitação: ${day.precipitaProb}%\n`;
        result += `💨 Vento: ${day.predWindDir}\n\n`;
      });

      return {
        content: [
          {
            type: "text",
            text: result
          }
        ]
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new McpError(ErrorCode.InternalError, `Erro ao obter previsão: ${errorMessage}`);
    }
  }

  async getWeatherWarnings() {
    try {
      const response = await fetch(`${this.baseUrl}/forecast/warnings/warnings_www.json`);
      const data = await response.json();

      if (!Array.isArray(data) || data.length === 0) {
        return {
          content: [
            {
              type: "text",
              text: "✅ Não há avisos meteorológicos ativos no momento."
            }
          ]
        };
      }

      let result = "⚠️ **Avisos Meteorológicos Ativos**\n\n";
      
      data.forEach((warning) => {
        const startDate = new Date(warning.startTime).toLocaleString('pt-PT');
        const endDate = new Date(warning.endTime).toLocaleString('pt-PT');
        
        result += `🚨 **${warning.awarenessTypeName}**\n`;
        result += `📍 Área: ${warning.idAreaAviso}\n`;
        result += `🔴 Nível: ${warning.awarenessLevelID}\n`;
        result += `⏰ De: ${startDate}\n`;
        result += `⏰ Até: ${endDate}\n`;
        if (warning.text) {
          result += `📝 Detalhes: ${warning.text}\n`;
        }
        result += "\n";
      });

      return {
        content: [
          {
            type: "text",
            text: result
          }
        ]
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new McpError(ErrorCode.InternalError, `Erro ao obter avisos: ${errorMessage}`);
    }
  }

  async getSeismicData(area) {
    try {
      let areaId;
      switch (area.toLowerCase()) {
        case "continent":
          areaId = 1;
          break;
        case "azores":
          areaId = 2;
          break;
        case "madeira":
          areaId = 3;
          break;
        default:
          areaId = 1;
      }

      const response = await fetch(`${this.baseUrl}/observation/seismic/${areaId}.json`);
      const data = await response.json();

      if (!data.data || data.data.length === 0) {
        return {
          content: [
            {
              type: "text",
              text: "📍 Não há dados sísmicos recentes para a área especificada."
            }
          ]
        };
      }

      let result = `🌍 **Dados Sísmicos - ${area}**\n\n`;
      result += `🕐 Última atualização: ${data.data[0]?.dataUpdate}\n\n`;

      const recentData = data.data.slice(0, 10);
      
      recentData.forEach((earthquake) => {
        const eventTime = new Date(earthquake.time).toLocaleString('pt-PT');
        result += `📅 **${eventTime}**\n`;
        result += `📍 Local: ${earthquake.obsRegion || 'N/A'}\n`;
        result += `📏 Magnitude: ${earthquake.magnitud} ${earthquake.magType}\n`;
        result += `🌊 Profundidade: ${earthquake.depth} km\n`;
        result += `🗺️ Coordenadas: ${earthquake.lat}, ${earthquake.lon}\n\n`;
      });

      return {
        content: [
          {
            type: "text",
            text: result
          }
        ]
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new McpError(ErrorCode.InternalError, `Erro ao obter dados sísmicos: ${errorMessage}`);
    }
  }

  async getLocations() {
    try {
      const response = await fetch(`${this.baseUrl}/distrits-islands.json`);
      const data = await response.json();

      let result = "📍 **Locais Disponíveis para Previsão**\n\n";
      
      const groupedByDistrict = {};
      
      data.data.forEach((location) => {
        if (!groupedByDistrict[location.idDistrito]) {
          groupedByDistrict[location.idDistrito] = [];
        }
        groupedByDistrict[location.idDistrito].push(location);
      });

      Object.values(groupedByDistrict).forEach((locations) => {
        result += `**Região ${locations[0].idDistrito}:**\n`;
        locations.forEach((loc) => {
          result += `• ${loc.local} (${loc.latitude}, ${loc.longitude})\n`;
        });
        result += "\n";
      });

      return {
        content: [
          {
            type: "text",
            text: result
          }
        ]
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new McpError(ErrorCode.InternalError, `Erro ao obter locais: ${errorMessage}`);
    }
  }

  async getWeatherStations() {
    try {
      const response = await fetch(`${this.baseUrl}/observation/meteorology/stations/observations.json`);
      const data = await response.json();

      const stationsResponse = await fetch(`${this.baseUrl}/observation/meteorology/stations/stations.json`);
      const stationsData = await stationsResponse.json();

      const stationsInfo = stationsData.reduce((acc, station) => {
        acc[station.properties.idEstacao] = station.properties.localEstacao;
        return acc;
      }, {});

      let result = "🌡️ **Observações das Estações Meteorológicas**\n\n";
      
      const timestamps = Object.keys(data);
      const latestTimestamp = timestamps[timestamps.length - 1];
      const latestObservations = data[latestTimestamp];

      result += `🕐 Observações de: ${latestTimestamp}\n\n`;

      const stationIds = Object.keys(latestObservations).slice(0, 15);
      
      stationIds.forEach((stationId) => {
        const obs = latestObservations[stationId];
        const stationName = stationsInfo[stationId] || `Estação ${stationId}`;
        
        result += `📍 **${stationName}**\n`;
        if (obs.temperatura > -99) result += `🌡️ Temperatura: ${obs.temperatura}°C\n`;
        if (obs.humidade > -99) result += `💧 Humidade: ${obs.humidade}%\n`;
        if (obs.pressao > -99) result += `📊 Pressão: ${obs.pressao} hPa\n`;
        if (obs.intensidadeVento > -99) result += `💨 Vento: ${obs.intensidadeVento} m/s\n`;
        if (obs.precAcumulada > -99) result += `🌧️ Precipitação: ${obs.precAcumulada} mm\n`;
        result += "\n";
      });

      return {
        content: [
          {
            type: "text",
            text: result
          }
        ]
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new McpError(ErrorCode.InternalError, `Erro ao obter dados das estações: ${errorMessage}`);
    }
  }

  async getUVForecast() {
    try {
      const response = await fetch(`${this.baseUrl}/forecast/meteorology/uv/uv.json`);
      const data = await response.json();

      if (!Array.isArray(data) || data.length === 0) {
        return {
          content: [
            {
              type: "text",
              text: "☀️ Não há dados de UV disponíveis no momento."
            }
          ]
        };
      }

      const locationsResponse = await fetch(`${this.baseUrl}/distrits-islands.json`);
      const locationsData = await locationsResponse.json();
      
      const locationMap = locationsData.data.reduce((acc, loc) => {
        acc[loc.globalIdLocal] = loc.local;
        return acc;
      }, {});

      let result = "☀️ **Previsão do Índice UV**\n\n";
      
      const uvByDate = {};
      data.forEach((uvData) => {
        if (!uvByDate[uvData.data]) {
          uvByDate[uvData.data] = [];
        }
        uvByDate[uvData.data].push(uvData);
      });

      Object.keys(uvByDate).slice(0, 3).forEach((date) => {
        result += `📅 **${date}**\n`;
        
        uvByDate[date].slice(0, 10).forEach((uv) => {
          const locationName = locationMap[uv.globalIdLocal] || `Local ${uv.globalIdLocal}`;
          const uvLevel = parseFloat(uv.iUv);
          let uvCategory = "";
          
          if (uvLevel <= 2) uvCategory = "Baixo 🟢";
          else if (uvLevel <= 5) uvCategory = "Moderado 🟡";
          else if (uvLevel <= 7) uvCategory = "Alto 🟠";
          else if (uvLevel <= 10) uvCategory = "Muito Alto 🔴";
          else uvCategory = "Extremo 🟣";
          
          result += `• ${locationName}: UV ${uv.iUv} (${uvCategory}) - ${uv.intervaloHora}\n`;
        });
        result += "\n";
      });

      return {
        content: [
          {
            type: "text",
            text: result
          }
        ]
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new McpError(ErrorCode.InternalError, `Erro ao obter previsão UV: ${errorMessage}`);
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("IPMA MCP Server running on stdio");
  }
}

const server = new IPMAServer();
server.run().catch(console.error);