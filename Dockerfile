# Dockerfile per Railway - Backend Python FastAPI
FROM python:3.9-slim

# Imposta la directory di lavoro
WORKDIR /app

# Installa le dipendenze di sistema necessarie
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia i file di requirements
COPY requirements.txt /app/requirements.txt

# Installa le dipendenze Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copia tutto il codice del backend
COPY . /app/

# Crea un file __init__.py se non esiste
RUN touch /app/__init__.py

# Esponi la porta (Railway la sovrascriverà con la sua variabile $PORT)
EXPOSE 8001

# Comando per avviare il server - usa la variabile PORT di Railway
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8001}
# Force rebuild Wed Oct  1 11:48:22 EDT 2025
