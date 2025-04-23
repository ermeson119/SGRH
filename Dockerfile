FROM python:3.10-slim

# Instala dependências do sistema necessárias para compilar pacotes como psycopg2 e o redis-cli
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copia o script de entrada e dá permissão de execução
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENV FLASK_APP=main.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=8000

# Usa o script de entrada para iniciar o Flask
CMD ["./entrypoint.sh"]