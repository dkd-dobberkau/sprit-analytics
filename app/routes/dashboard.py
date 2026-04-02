from flask import Blueprint, render_template
from app import db_service

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    stats = db_service.query("""
        SELECT count() AS n FROM station GROUP ALL
    """)
    station_count = stats[0]["n"] if stats else 0

    runs = db_service.query("""
        SELECT started_at, finished_at, stations_seen, events_written, error
        FROM collector_run
        ORDER BY started_at DESC
        LIMIT 1
    """)
    last_run = runs[0] if runs else None

    cheapest_diesel = db_service.query("""
        SELECT station AS station_ref, station.name AS name, station.brand AS brand,
               station.place AS place, diesel, e5, e10, status, fetched_at
        FROM price_event
        WHERE diesel != NONE AND status = 'open'
        ORDER BY fetched_at DESC
        LIMIT 200
    """)

    seen = set()
    unique = []
    for row in cheapest_diesel:
        key = row.get("name", "")
        if key not in seen:
            seen.add(key)
            unique.append(row)
    unique.sort(key=lambda r: r.get("diesel") or 999)

    return render_template(
        "pages/index.html",
        station_count=station_count,
        last_run=last_run,
        cheapest=unique[:20],
    )
