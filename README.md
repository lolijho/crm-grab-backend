# CRM Grab Backend

Backend API per l'applicazione CRM Grab, sviluppato in Python con FastAPI.

## 🚀 Deploy su Railway

Questa repository è configurata per il deploy automatico su Railway.

### Configurazione Railway

- **Framework**: Python/FastAPI
- **Build Command**: Automatico (pip install -r requirements.txt)
- **Start Command**: Definito nel `Procfile`
- **Port**: 8001 (configurabile tramite variabile d'ambiente PORT)

### File di Configurazione

- `requirements.txt` - Dipendenze Python
- `Procfile` - Comando di avvio per Railway
- `railway.json` - Configurazioni specifiche Railway
- `Dockerfile` - Container configuration (opzionale)

## 🔧 Sviluppo Locale

```bash
# Installare le dipendenze
pip install -r requirements.txt

# Avviare il server di sviluppo
python server.py
```

Il server sarà disponibile su `http://localhost:8001`

## 📁 Struttura

- `server.py` - Server principale FastAPI
- `init_db.py` - Inizializzazione database
- `translations.py` - Gestione traduzioni
- `*_test.py` - File di test
- `sql/` - Script SQL
- `scripts/` - Script di utilità

## 🌐 Frontend

Il frontend React è deployato separatamente su Netlify:
- Repository: [crm-grab](https://github.com/lolijho/crm-grab)
- URL: [Da configurare dopo il deploy]

## 🔗 Variabili d'Ambiente

Configurare su Railway:

```env
# Database
DATABASE_URL=your_database_url
MONGODB_URI=your_mongodb_uri

# API Keys
OPENAI_API_KEY=your_openai_key

# CORS
FRONTEND_URL=https://your-netlify-app.netlify.app

# Altri
PORT=8001
```

## 📝 Note

- Separato dal frontend per ottimizzare i deploy
- Configurato per Railway con auto-deploy da GitHub
- CORS configurato per accettare richieste dal frontend Netlify
