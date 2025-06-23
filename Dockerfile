# Usamos uma imagem base leve com Python 3
FROM python:3.9-slim

# Definimos o diretório da aplicação
WORKDIR /app

# Copiamos requirements e instalamos as dependências
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos o restante código
COPY . .

# Expomos a porta (a variável PORT vem do Smithery em runtime)
EXPOSE 5000

# Definimos o comando de arranque:
# - usamos flask run para suporte nativo
# - definimos a variável FLASK_APP e host/port a partir de PORT
ENV FLASK_APP=src/mcp_server.py
CMD ["flask", "run", "--host=0.0.0.0", "--port", "${PORT:-5000}"]
