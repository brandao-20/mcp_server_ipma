FROM python:3.9-slim

WORKDIR /app

# Copia só o requirements.txt e instala primeiro (para cache)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto do código
COPY src/ ./src
COPY mcp_manifest.json .

# Exponha a porta
EXPOSE 5000

ENV FLASK_APP=src/mcp_server.py
CMD ["flask","run","--host=0.0.0.0","--port","${PORT:-5000}"]
