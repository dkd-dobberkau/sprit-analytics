# Tankerkönig → SurrealDB Collector

Sammelt Spritpreise über die [Tankerkönig CC-API](https://creativecommons.tankerkoenig.de)
und speichert sie in SurrealDB.

## Setup

### 1. API-Key beantragen

Unter https://onboarding.tankerkoenig.de registrieren.
Der Key ist eine UUID (Format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).

### 2. SurrealDB starten

```bash
# Docker (empfohlen)
docker run --rm -p 8000:8000 surrealdb/surrealdb:latest \
  start --log info --user root --pass root memory

# Oder mit persistentem Speicher:
docker run -d --name surrealdb -p 8000:8000 \
  -v $(pwd)/data:/data \
  surrealdb/surrealdb:latest \
  start --log info --user root --pass root file:/data/tk.db
```

### 3. Schema anlegen

```bash
surreal import --conn ws://localhost:8000 \
  --user root --pass root \
  --ns tk --db spritpreise \
  tankerkoenig_schema.surql
```

Oder direkt in der SurrealDB CLI / Surrealist UI einfügen.

### 4. Dependencies installieren

```bash
pip install -r requirements.txt
```

### 5. Collector starten

```bash
# API-Key als Umgebungsvariable (nie in Git committen!)
export TK_API_KEY="dein-echter-api-key"

# Optional: Suchzentrum anpassen (Default: Frankfurt Innenstadt)
export SEARCH_LAT="50.1109"
export SEARCH_LNG="8.6821"
export SEARCH_RAD="10.0"   # km, max 25

python collector.py
```

### 6. Als Cronjob einrichten

```bash
# Crontab bearbeiten
crontab -e

# Alle 5 Minuten sammeln (Tankerkönig-Nutzungsbedingungen: nicht öfter)
*/5 * * * * cd /pfad/zum/projekt && TK_API_KEY=xxx python collector.py >> collector.log 2>&1
```

## Datenmodell

### Tabelle `station`
Tankstellen-Stammdaten (Name, Marke, Adresse, Koordinaten).
Wird per `UPSERT` aktualisiert — Record-ID entspricht der MTS-K UUID.

### Tabelle `price_event`
Append-only Log aller Preisabfragen. Jeder Collector-Lauf schreibt
einen neuen Record pro Tankstelle. Für Zeitreihenanalysen.

### Tabelle `collector_run`
Protokoll jedes Sammeldurchlaufs mit Zeitstempel, Anzahl Events, Fehler.

## Nützliche Abfragen

Siehe Kommentar am Ende von `collector.py` (Variable `EXAMPLE_QUERIES`).

Beispiel — günstigster Diesel aktuell:
```sql
SELECT station.name, station.brand, diesel
FROM (
    SELECT station, diesel, fetched_at FROM price_event
    WHERE status = 'open' AND diesel IS NOT NULL
    ORDER BY fetched_at DESC LIMIT BY 1 GROUP BY station
)
ORDER BY diesel ASC LIMIT 10;
```

## Lizenz

Daten unter CC BY 4.0 — Namensnennung erforderlich (Link auf www.tankerkoenig.de).
Nicht für Mineralölunternehmen und Tankstellenbetreiber.
