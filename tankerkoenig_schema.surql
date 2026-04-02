OPTION IMPORT;

-- ─────────────────────────────────────────────────────────────────────────────
-- Tankerkönig → SurrealDB Schema
-- Namespace: tk   Database: spritpreise
-- ─────────────────────────────────────────────────────────────────────────────

DEFINE NAMESPACE tk;
USE NAMESPACE tk;

DEFINE DATABASE spritpreise;
USE DATABASE spritpreise;

-- ─── Tankstellen-Stammdaten ──────────────────────────────────────────────────
-- Einmal anlegen / aktualisieren, selten ändern.
-- id kommt direkt aus der MTS-K UUID, z.B. station:⟨474e5046-deaf-4f9b-9a32-9797b778f047⟩

DEFINE TABLE station SCHEMAFULL
    PERMISSIONS
        FOR select FULL
        FOR create, update WHERE $auth.role = "collector"
        FOR delete NONE;

DEFINE FIELD id            ON station TYPE string;  -- MTS-K UUID als String-Teil der Record-ID
DEFINE FIELD name          ON station TYPE string;
DEFINE FIELD brand         ON station TYPE string;
DEFINE FIELD street        ON station TYPE string;
DEFINE FIELD house_number  ON station TYPE option<string>;
DEFINE FIELD post_code     ON station TYPE string;
DEFINE FIELD place         ON station TYPE string;
DEFINE FIELD lat           ON station TYPE float;
DEFINE FIELD lng           ON station TYPE float;
DEFINE FIELD is_open       ON station TYPE bool;
DEFINE FIELD whole_day     ON station TYPE option<bool>;
DEFINE FIELD state         ON station TYPE option<string>;
DEFINE FIELD opening_times ON station TYPE option<array>;
DEFINE FIELD overrides     ON station TYPE option<array>;
DEFINE FIELD updated_at    ON station TYPE datetime  VALUE time::now();

-- Geo-Index für räumliche Abfragen
DEFINE INDEX station_geo ON station FIELDS lat, lng;
DEFINE INDEX station_brand ON station FIELDS brand;
DEFINE INDEX station_post_code ON station FIELDS post_code;


-- ─── Preis-Events (append-only Log) ─────────────────────────────────────────
-- Jede Preisabfrage erzeugt einen neuen Record.
-- Entspricht gas_station_information_history aus dem Postgres-Dump.

DEFINE TABLE price_event SCHEMAFULL
    PERMISSIONS
        FOR select FULL
        FOR create WHERE $auth.role = "collector"
        FOR update, delete NONE;

DEFINE FIELD station      ON price_event TYPE record<station>;  -- Relation zur Tankstelle
DEFINE FIELD fetched_at   ON price_event TYPE datetime  VALUE time::now();
DEFINE FIELD status       ON price_event TYPE string;           -- "open" | "closed" | "no prices"
DEFINE FIELD e5           ON price_event TYPE option<float>;    -- null wenn Sorte nicht geführt
DEFINE FIELD e10          ON price_event TYPE option<float>;
DEFINE FIELD diesel       ON price_event TYPE option<float>;
DEFINE FIELD source       ON price_event TYPE string;           -- "list" | "prices"

DEFINE INDEX price_event_station    ON price_event FIELDS station;
DEFINE INDEX price_event_fetched_at ON price_event FIELDS fetched_at;
-- Compound-Index für typische Abfrage: alle Preise einer Station, chronologisch
DEFINE INDEX price_event_station_time ON price_event FIELDS station, fetched_at;


-- ─── Collector-Run Log ───────────────────────────────────────────────────────
-- Für Debugging und Rate-Limit-Tracking.

DEFINE TABLE collector_run SCHEMAFULL
    PERMISSIONS
        FOR select, create FULL
        FOR update, delete NONE;

DEFINE FIELD started_at      ON collector_run TYPE datetime VALUE time::now();
DEFINE FIELD finished_at     ON collector_run TYPE option<datetime>;
DEFINE FIELD stations_seen   ON collector_run TYPE option<int>;
DEFINE FIELD events_written  ON collector_run TYPE option<int>;
DEFINE FIELD lat             ON collector_run TYPE float;
DEFINE FIELD lng             ON collector_run TYPE float;
DEFINE FIELD radius_km       ON collector_run TYPE float;
DEFINE FIELD error           ON collector_run TYPE option<string>;
