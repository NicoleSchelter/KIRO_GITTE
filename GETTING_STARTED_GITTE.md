
# GITTE – Schnellstart & Nutzungsanleitung (für absolute Beginner)

Diese Anleitung bringt dich **von Null auf Start** für das GITTE‑Projekt (Streamlit‑App mit LLM über Ollama und optionalem Stable Diffusion, Postgres & MinIO). Folge einfach Schritt für Schritt.

---

## 1) Was ist drin? (Projektstruktur – grob)

- `src/ui` – **Streamlit UI** (Startpunkt: `src/ui/main.py`)
- `src/logic` – Geschäftslogik (Onboarding, LLM, PALD, Consent …)
- `src/services` – Anbindungen (LLM‑Provider, Audit, Monitoring …)
- `src/data` – DB‑Zugriff (SQLAlchemy‑Modelle, Repositories)
- `config` – zentrale **Konfiguration** (Feature Flags, Texte, Envs)
- `docker-compose.yml` – Startet **App, Postgres, Ollama, MinIO** im Verbund
- `.env.example` – Beispiel‑Konfig – bitte in `.env` kopieren
- `Makefile` – bequeme **Kurzbefehle** (dev, test, up/down …)
- `requirements.txt` – Python‑Abhängigkeiten

---

## 2) Schnellstart mit Docker (empfohlen)

### Voraussetzungen
- **Docker** & **Docker Compose**
- **Ports frei**: 8501 (Streamlit), 5432 (Postgres), 11434 (Ollama), 9000/9001 (MinIO)

### Schritte
1. **.env anlegen**
   ```bash
   cp .env.example .env
   # Danach .env öffnen und bei Bedarf anpassen
   ```

2. **Starten**
   ```bash
   docker compose up --build
   ```

3. **Öffnen**
   - Streamlit‑App: http://localhost:8501  
   - MinIO Console (optional): http://localhost:9001 (Zugang laut docker-compose: minioadmin/minioadmin)

4. **Modelle für Ollama ziehen** (in separatem Terminal, wenn der Ollama‑Container läuft)
   ```bash
   docker exec -it <ollama-container-name> ollama pull llama3
   docker exec -it <ollama-container-name> ollama pull mistral
   docker exec -it <ollama-container-name> ollama pull llava
   ```
   > Tipp: Den Container‑Namen siehst du mit `docker ps` (Service heißt in compose meist `ollama`).  
   > Standardmodell in der Config ist `llama3` (siehe `config/config.py`).

5. **App neu laden**  
   Wenn die Modelle da sind, Browser aktualisieren.

### Stoppen
```bash
docker compose down
```

---

## 3) Lokal ohne Docker (für Fortgeschrittene oder wenn gewünscht)

### Voraussetzungen
- **Python 3.10+**
- **PostgreSQL** lokal oder in Docker
- **Ollama** lokal: https://ollama.ai (Port 11434)  
- (Optional) **MinIO** oder setze MINIO aus

### Schritte
1. **Virtuelle Umgebung & Pakete**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scriptsctivate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **Postgres bereitstellen**
   - Schnell per Docker:
     ```bash
     docker run --name gitte-pg -e POSTGRES_PASSWORD=password -e POSTGRES_USER=gitte -e POSTGRES_DB=data_collector -p 5432:5432 -d postgres:15
     ```
   - Prüfe, ob die `.env` den DSN nutzt:
     ```env
     POSTGRES_DSN=postgresql://gitte:password@localhost:5432/data_collector
     ```

3. **.env anlegen**
   ```bash
   cp .env.example .env
   # Falls kein MinIO genutzt wird:
   # FEATURE_ENABLE_MINIO_STORAGE=false
   ```

4. **Ollama lokal starten & Modelle ziehen**
   ```bash
   ollama pull llama3
   ollama pull mistral
   ollama pull llava
   ```

5. **App starten**
   ```bash
   streamlit run src/ui/main.py
   ```

---

## 4) Konfiguration – das Wichtigste

Öffne `.env` (aus `.env.example` kopiert). Relevante Schlüssel:
- **ENVIRONMENT**: `development` (Standard) oder `production`
- **POSTGRES_DSN**: DSN zur Datenbank
- **OLLAMA_URL**: z. B. `http://localhost:11434` oder Container‑URL
- **SD_MODEL_NAME**: Stable‑Diffusion‑Modellname (optional)
- **Feature Flags** (präfix `FEATURE_…`), z. B.:
  - `FEATURE_ENABLE_IMAGE_GENERATION=true/false`
  - `FEATURE_ENABLE_MINIO_STORAGE=true/false`
  - `FEATURE_USE_FEDERATED_LEARNING=true/false`

> Alle Defaults stehen in `config/config.py` und können per ENV überschrieben werden.

---

## 5) Typische Workflows

### Entwicklung
```bash
make dev           # (falls im Makefile definiert, sonst: streamlit run src/ui/main.py)
make up            # docker compose up
make down          # docker compose down
make logs          # Logs aller Services
```

### Tests & Migrationen
```bash
make test          # (Unit/Integration – falls Tests vorhanden)
make migrate       # Alembic‑Migrationen (wenn konfiguriert)
make seed          # Beispiel‑Daten einspielen (falls vorhanden)
```

---

## 6) Häufige Stolpersteine & Lösungen

1) **LLM antwortet nicht / Timeouts**  
   - Prüfe, ob **Ollama läuft** und die **Modelle** gezogen sind.  
   - `OLLAMA_URL` korrekt? (Docker‑Netz vs. localhost)  
   - Feature Flag `FEATURE_SAVE_LLM_LOGS=true` hilft beim Debuggen (Logs).

2) **Bilderzeugung schlägt fehl**  
   - Setze testweise `FEATURE_ENABLE_IMAGE_GENERATION=false`.  
   - Oder stelle sicher, dass **GPU/Dependencies** passen (bei SD lokal).  
   - Ohne MinIO: `FEATURE_ENABLE_MINIO_STORAGE=false` setzen.

3) **Datenbank‑Fehler**  
   - Ist Postgres erreichbar? Stimmt `POSTGRES_DSN`?  
   - Migrationen ausgeführt? (siehe `alembic.ini`/`make migrate`)

4) **Import‑Fehler in Streamlit**  
   - Achte auf `PYTHONPATH`/Arbeitsverzeichnis. Im Dockerfile ist `PYTHONPATH=/app` gesetzt. Lokal notfalls so starten:  
     ```bash
     PYTHONPATH=. streamlit run src/ui/main.py
     ```

---

## 7) Bekannte kleine Code‑Bugs (schnell behebbar)

**Problem A:** In `src/ui/main.py` wird `render_admin_interface(...)` aufgerufen, importiert ist aber `render_admin_ui`.  
**Fix:** Ersetze den Aufruf durch `render_admin_ui(user_id)` **oder** ändere den Import/Wrapper konsistent.

**Problem B (potenziell):** Doppelte/ähnliche Funktionen `render_guided_onboarding_flow` vs. `render_guided_onboarding`.  
**Hinweis:** Nutze **einen** Namen konsistent (die App importiert `render_guided_onboarding_flow`). Entferne/vereinheitliche die andere Variante, falls ungenutzt.

> Wenn du möchtest, liefere ich dir gern fertige **Patch‑Diffs** für beide Stellen.

---

## 8) Wie starte ich GITTE in 3 Minuten? (Cheat‑Sheet)

```bash
# 1) .env anlegen
cp .env.example .env

# 2) Docker‑Stack hochfahren
docker compose up --build

# 3) Modelle holen (wenn Ollama-Container läuft)
docker exec -it <ollama> ollama pull llama3

# 4) Browser öffnen
open http://localhost:8501   # Windows: start, Linux: xdg-open
```

Fertig. Wenn etwas hakt, sag mir kurz, was im Terminal steht – ich gebe dir die konkreten Fix‑Kommandos.
