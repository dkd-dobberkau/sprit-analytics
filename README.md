# Sprit Analytics

Spritpreis-Dashboard für Deutschland. Sammelt Tankstellenpreise über die [Tankerkönig CC-API](https://creativecommons.tankerkoenig.de) und visualisiert sie in einem HTMX-Dashboard.

## Features

- **Preisvergleich** — günstigste Tankstellen nach Diesel, E5 oder E10 sortiert
- **Live-Suche** — Tankstellen nach Name, Marke, Ort oder PLZ suchen
- **Preisverlauf** — Chart.js-Diagramm pro Tankstelle über Zeit
- **Collector-Status** — Übersicht der letzten Sammeldurchläufe
- **Dark Mode** — Toggle mit localStorage-Persistenz

## Tech Stack

- **Backend:** Flask + SurrealDB
- **Frontend:** HTMX + Bootstrap 5 + Chart.js
- **Collector:** Python (httpx) mit Tankerkönig-API
- **Infrastruktur:** Docker Compose, uv

## Schnellstart (Docker)

```bash
# 1. Repository klonen
git clone https://github.com/YOUR_USER/sprit-analytics.git
cd sprit-analytics

# 2. API-Key konfigurieren
cp .env.example .env
# .env bearbeiten und TK_API_KEY eintragen
# Key beantragen: https://onboarding.tankerkoenig.de

# 3. Starten
docker compose up -d --build

# 4. Schema importieren (einmalig)
surreal import --endpoint http://localhost:8000 \
  --username root --password root \
  --namespace tk --database spritpreise \
  tankerkoenig_schema.surql

# 5. Ersten Sammeldurchlauf starten
docker compose --profile collect run --rm collector

# 6. Dashboard öffnen
open http://localhost:5001
```

## Schnellstart (lokal)

```bash
# Dependencies
uv sync

# SurrealDB starten
docker run -d --name surrealdb -p 8000:8000 \
  -v $(pwd)/data:/data \
  surrealdb/surrealdb:latest \
  start --log info --user root --pass root surrealkv:/data/tk.db

# Schema importieren
surreal import --endpoint http://localhost:8000 \
  --username root --password root \
  --namespace tk --database spritpreise \
  tankerkoenig_schema.surql

# Collector starten
export TK_API_KEY="dein-api-key"
uv run python collector.py

# Dashboard starten
uv run python main.py
# -> http://localhost:5001
```

## Konfiguration

Alle Einstellungen über `.env` oder Umgebungsvariablen:

| Variable | Default | Beschreibung |
|---|---|---|
| `TK_API_KEY` | — | Tankerkönig API-Key (Pflicht) |
| `SEARCH_LAT` | `50.1109` | Breitengrad Suchzentrum |
| `SEARCH_LNG` | `8.6821` | Längengrad Suchzentrum |
| `SEARCH_RAD` | `10.0` | Suchradius in km (max 25) |
| `SURREAL_URL` | `ws://localhost:8000/rpc` | SurrealDB Endpoint |
| `SURREAL_USER` | `root` | SurrealDB Benutzer |
| `SURREAL_PASS` | `root` | SurrealDB Passwort |

## Collector als Cronjob

```bash
# Alle 5 Minuten (nicht öfter — Nutzungsbedingungen!)
*/5 * * * * cd /pfad/zu/sprit-analytics && docker compose --profile collect run --rm collector >> collector.log 2>&1
```

## Docker Services

| Service | Container | Port | Beschreibung |
|---|---|---|---|
| `surrealdb` | sprit-surrealdb | 8000 | Datenbank (persistentes Volume) |
| `web` | sprit-web | 5001 | Flask Dashboard |
| `collector` | sprit-collector | — | Preissammler (on-demand) |

## Datenmodell

- **`station`** — Tankstellen-Stammdaten (Name, Marke, Adresse, Koordinaten)
- **`price_event`** — Append-only Preislog (Diesel, E5, E10 pro Abfrage)
- **`collector_run`** — Protokoll der Sammeldurchläufe

## Lizenz

Code: [MIT](LICENSE)

Preisdaten: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — Namensnennung [tankerkoenig.de](https://www.tankerkoenig.de) erforderlich. Nicht für Mineralölunternehmen und Tankstellenbetreiber.
