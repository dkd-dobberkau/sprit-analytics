"""
Tankerkönig → SurrealDB Collector
==================================
Sammelt Spritpreise über die Tankerkönig-API und schreibt sie in SurrealDB.

Verwendung:
    # Einmalig / manuell:
    python collector.py

    # Als Cronjob alle 5 Minuten (nicht öfter! Nutzungsbedingungen):
    */5 * * * * cd /pfad/zum/script && python collector.py >> collector.log 2>&1

Konfiguration über Umgebungsvariablen oder .env-Datei (siehe unten).
"""

import os
import sys
import time
import random
import logging
import httpx
from datetime import datetime, timezone
from surrealdb import AsyncSurreal as Surreal, RecordID

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("tk_collector")

# ─── Konfiguration ────────────────────────────────────────────────────────────
# Entweder direkt hier eintragen oder als Umgebungsvariablen setzen.
# Niemals den API-Key in Git committen!

TK_API_KEY   = os.getenv("TK_API_KEY",   "DEIN-API-KEY-HIER")   # <-- ersetzen
TK_BASE_URL  = "https://creativecommons.tankerkoenig.de/json"

# Suchzentrum und Radius — Frankfurt Innenstadt als Default
SEARCH_LAT   = float(os.getenv("SEARCH_LAT",   "50.1109"))
SEARCH_LNG   = float(os.getenv("SEARCH_LNG",   "8.6821"))
SEARCH_RAD   = float(os.getenv("SEARCH_RAD",   "10.0"))    # km, max 25

# SurrealDB
SURREAL_URL  = os.getenv("SURREAL_URL",  "ws://localhost:8000/rpc")
SURREAL_USER = os.getenv("SURREAL_USER", "root")
SURREAL_PASS = os.getenv("SURREAL_PASS", "root")
SURREAL_NS   = os.getenv("SURREAL_NS",   "tk")
SURREAL_DB   = os.getenv("SURREAL_DB",   "spritpreise")

# Rate-Limit: max 1 Request/Minute per API-Key (Nutzungsbedingungen)
JITTER_SECONDS = (5, 30)

TK_BASE_URL = TK_BASE_URL.rstrip("/")


# ─── Tankerkönig API ──────────────────────────────────────────────────────────

def tk_list(lat: float, lng: float, rad: float) -> list[dict]:
    """
    API-Methode 1: Umkreissuche.
    Liefert Tankstellen-Infos + aktuelle Preise für alle Sorten.
    """
    url = f"{TK_BASE_URL}/list.php"
    params = {
        "lat":    lat,
        "lng":    lng,
        "rad":    rad,
        "type":   "all",       # alle Sorten, Sortierung nach Entfernung
        "apikey": TK_API_KEY,
    }
    response = httpx.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    if not data.get("ok"):
        raise RuntimeError(f"Tankerkönig list.php Fehler: {data.get('message')}")

    return data.get("stations", [])


def tk_prices(station_ids: list[str]) -> dict:
    """
    API-Methode 2: Preisabfrage für bis zu 10 bekannte Tankstellen.
    Effizienter für Folge-Abfragen nach dem initialen list.php.
    """
    if not station_ids:
        return {}

    # API erlaubt max 10 IDs pro Request
    results = {}
    for chunk_start in range(0, len(station_ids), 10):
        chunk = station_ids[chunk_start : chunk_start + 10]
        url = f"{TK_BASE_URL}/prices.php"
        params = {
            "ids":    ",".join(chunk),
            "apikey": TK_API_KEY,
        }
        response = httpx.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        if not data.get("ok"):
            log.warning(f"prices.php Fehler für chunk {chunk}: {data.get('message')}")
            continue

        results.update(data.get("prices", {}))

    return results


def tk_detail(station_id: str) -> dict:
    """
    API-Methode 3: Detail-Abfrage (Öffnungszeiten etc.)
    Nur bei Erstanlage einer Tankstelle aufrufen, nicht regelmäßig!
    """
    url = f"{TK_BASE_URL}/detail.php"
    params = {"id": station_id, "apikey": TK_API_KEY}
    response = httpx.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    if not data.get("ok"):
        raise RuntimeError(f"Tankerkönig detail.php Fehler: {data.get('message')}")

    return data.get("station", {})


# ─── SurrealDB Helpers ────────────────────────────────────────────────────────

def surreal_record_id(table: str, uuid: str) -> RecordID:
    """Erstellt eine SurrealDB RecordID."""
    return RecordID(table, uuid)


async def upsert_station(db: Surreal, station: dict) -> None:
    """
    Legt Tankstellen-Stammdaten an oder aktualisiert sie.
    Merge statt Replace, damit bestehende Felder erhalten bleiben.
    """
    sid = station["id"]
    record_id = surreal_record_id("station", sid)

    data = {
        "id":           sid,
        "name":         station.get("name", ""),
        "brand":        station.get("brand", ""),
        "street":       station.get("street", ""),
        "house_number": station.get("houseNumber"),
        "post_code":    str(station.get("postCode", "")),
        "place":        station.get("place", ""),
        "lat":          station.get("lat", 0.0),
        "lng":          station.get("lng", 0.0),
        "is_open":      station.get("isOpen", False),
        "updated_at":   datetime.now(timezone.utc),
    }

    # Öffnungszeiten nur überschreiben wenn vorhanden
    if "openingTimes" in station:
        data["opening_times"] = station["openingTimes"]
    if "overrides" in station:
        data["overrides"] = station["overrides"]
    if "wholeDay" in station:
        data["whole_day"] = station["wholeDay"]
    if "state" in station:
        data["state"] = station["state"]

    await db.upsert(record_id, data)


async def insert_price_event(
    db: Surreal,
    station_uuid: str,
    price_data: dict,
    source: str = "list",
) -> None:
    """
    Schreibt ein Preis-Event (append-only).
    price_data ist entweder ein Station-Dict aus list.php
    oder ein Preisblock aus prices.php.
    """
    station_ref = surreal_record_id("station", station_uuid)

    # Preise: in der API als Float geliefert, None wenn Sorte nicht geführt
    def price_or_none(val):
        if val is False or val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    event = {
        "station":    station_ref,
        "fetched_at": datetime.now(timezone.utc),
        "status":     price_data.get("status", "open"),
        "e5":         price_or_none(price_data.get("e5")),
        "e10":        price_or_none(price_data.get("e10")),
        "diesel":     price_or_none(price_data.get("diesel")),
        "source":     source,
    }

    await db.create("price_event", event)


# ─── Haupt-Collector ──────────────────────────────────────────────────────────

async def run_collection():
    """
    Ein vollständiger Sammeldurchlauf:
    1. Umkreissuche → Stammdaten + aktuelle Preise
    2. Stammdaten in SurrealDB anlegen / aktualisieren
    3. Preis-Events schreiben
    4. Collector-Run protokollieren
    """
    log.info(f"Starte Sammeldurchlauf: lat={SEARCH_LAT}, lng={SEARCH_LNG}, rad={SEARCH_RAD} km")

    # Zufällige Verzögerung (Nutzungsbedingungen: nicht auf runden Zeiten abfragen)
    jitter = random.randint(*JITTER_SECONDS)
    log.info(f"Jitter: {jitter}s Verzögerung")
    time.sleep(jitter)

    started_at = datetime.now(timezone.utc)
    error_msg = None
    stations_seen = 0
    events_written = 0

    db = Surreal(SURREAL_URL)
    await db.connect()
    await db.signin({"username": SURREAL_USER, "password": SURREAL_PASS})
    await db.use(SURREAL_NS, SURREAL_DB)
    log.info("SurrealDB verbunden")

    run_record = await db.create("collector_run", {
        "started_at":    started_at,
        "lat":           SEARCH_LAT,
        "lng":           SEARCH_LNG,
        "radius_km":     SEARCH_RAD,
    })
    run_id = run_record["id"] if run_record else None

    try:
        # ── Schritt 1: API-Abfrage ────────────────────────────────────────
        stations = tk_list(SEARCH_LAT, SEARCH_LNG, SEARCH_RAD)
        stations_seen = len(stations)
        log.info(f"{stations_seen} Tankstellen gefunden")

        # ── Schritt 2 + 3: Stammdaten + Preise schreiben ──────────────────
        for station in stations:
            try:
                await upsert_station(db, station)
                await insert_price_event(db, station["id"], station, source="list")
                events_written += 1
            except Exception as e:
                log.warning(f"Fehler bei Tankstelle {station.get('id')}: {e}")

        log.info(f"{events_written} Preis-Events geschrieben")

    except Exception as e:
        error_msg = str(e)
        log.error(f"Sammeldurchlauf fehlgeschlagen: {e}")

    finally:
        # ── Schritt 4: Run-Log abschließen ────────────────────────────────
        finished_at = datetime.now(timezone.utc)
        duration = (finished_at - started_at).total_seconds()
        if run_id:
            await db.merge(run_id, {
                "finished_at":    finished_at,
                "duration_s":     round(duration, 1),
                "stations_seen":  stations_seen,
                "events_written": events_written,
                "error":          error_msg,
            })
    log.info(f"Durchlauf abgeschlossen in {duration:.1f}s — {events_written} Events")

    return events_written


# ─── Nützliche Abfragen als Referenz ─────────────────────────────────────────

EXAMPLE_QUERIES = """
-- Alle Tankstellen im Radius 5 km um Frankfurt Innenstadt (approx. BBox):
SELECT * FROM station
WHERE lat BETWEEN 50.065 AND 50.157
  AND lng BETWEEN 8.597 AND 8.767;

-- Günstigster Diesel aktuell (neuestes Event pro Station):
SELECT station.name, station.brand, station.place, diesel
FROM (
    SELECT station, diesel, fetched_at
    FROM price_event
    WHERE status = 'open' AND diesel IS NOT NULL
    ORDER BY fetched_at DESC
    LIMIT BY 1 GROUP BY station
)
ORDER BY diesel ASC
LIMIT 10;

-- Preisverlauf Diesel für eine bestimmte Tankstelle (letzte 24h):
SELECT fetched_at, diesel, e5, e10
FROM price_event
WHERE station = station:`474e5046-deaf-4f9b-9a32-9797b778f047`
  AND fetched_at > time::now() - 1d
ORDER BY fetched_at ASC;

-- Durchschnittspreis Diesel nach Marke (heute):
SELECT station.brand, math::mean(diesel) AS avg_diesel, count() AS n
FROM price_event
WHERE fetched_at > time::now() - 1d
  AND status = 'open'
  AND diesel IS NOT NULL
GROUP BY station.brand
ORDER BY avg_diesel ASC;

-- Letzte 5 Collector-Runs:
SELECT started_at, finished_at, stations_seen, events_written, error
FROM collector_run
ORDER BY started_at DESC
LIMIT 5;
"""


# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    if TK_API_KEY == "DEIN-API-KEY-HIER":
        log.error("Bitte TK_API_KEY setzen (Umgebungsvariable oder direkt im Skript)")
        sys.exit(1)

    asyncio.run(run_collection())
