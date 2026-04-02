from flask import Blueprint, render_template, request
from app import db_service

bp = Blueprint("api", __name__)


@bp.route("/stations/search")
def search_stations():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return render_template("components/station_rows.html", stations=[])

    results = db_service.query("""
        SELECT id, name, brand, place, street, house_number, post_code, is_open
        FROM station
        WHERE string::lowercase(name) CONTAINS string::lowercase($q)
           OR string::lowercase(brand) CONTAINS string::lowercase($q)
           OR string::lowercase(place) CONTAINS string::lowercase($q)
           OR post_code CONTAINS $q
        ORDER BY brand, name
        LIMIT 50
    """, {"q": q})

    return render_template("components/station_rows.html", stations=results)


@bp.route("/prices/cheapest")
def cheapest_prices():
    fuel = request.args.get("fuel", "diesel")
    if fuel not in ("diesel", "e5", "e10"):
        fuel = "diesel"

    results = db_service.query(f"""
        SELECT station AS station_ref, station.name AS name, station.brand AS brand,
               station.place AS place, station.street AS street,
               diesel, e5, e10, status, fetched_at
        FROM price_event
        WHERE {fuel} != NONE AND status = 'open'
        ORDER BY fetched_at DESC
        LIMIT 300
    """)

    seen = set()
    unique = []
    for row in results:
        key = row.get("name", "")
        if key not in seen:
            seen.add(key)
            unique.append(row)
    unique.sort(key=lambda r: r.get(fuel) or 999)

    return render_template(
        "components/price_table.html",
        prices=unique[:30],
        fuel=fuel,
    )


@bp.route("/station/<path:station_id>/history")
def station_history(station_id):
    events = db_service.query("""
        SELECT fetched_at, diesel, e5, e10, status
        FROM price_event
        WHERE station = type::record('station', $sid)
        ORDER BY fetched_at ASC
    """, {"sid": station_id})

    station = db_service.query("""
        SELECT name, brand, place, street, house_number
        FROM type::record('station', $sid)
    """, {"sid": station_id})

    info = station[0] if station else {"name": station_id, "brand": ""}

    return render_template(
        "components/price_chart.html",
        events=events,
        station=info,
    )


@bp.route("/collector/runs")
def collector_runs():
    runs = db_service.query("""
        SELECT started_at, finished_at, duration_s, stations_seen, events_written, error
        FROM collector_run
        ORDER BY started_at DESC
        LIMIT 20
    """)

    return render_template("components/run_table.html", runs=runs)
