from flask import Flask
from surrealdb import RecordID
from app.services.db import SurrealService


db_service = SurrealService()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_prefixed_env("FLASK")

    db_service.init_app(app)

    @app.template_filter("station_id")
    def station_id_filter(ref):
        if isinstance(ref, RecordID):
            return ref.id
        return str(ref)

    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.api import bp as api_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app
