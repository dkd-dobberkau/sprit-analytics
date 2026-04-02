"""Synchronous SurrealDB service for Flask."""

import os
from surrealdb import Surreal


class SurrealService:
    def __init__(self):
        self._db = None

    def init_app(self, app):
        app.config.setdefault("SURREAL_URL", os.getenv("SURREAL_URL", "ws://localhost:8000/rpc"))
        app.config.setdefault("SURREAL_USER", os.getenv("SURREAL_USER", "root"))
        app.config.setdefault("SURREAL_PASS", os.getenv("SURREAL_PASS", "root"))
        app.config.setdefault("SURREAL_NS", os.getenv("SURREAL_NS", "tk"))
        app.config.setdefault("SURREAL_DB", os.getenv("SURREAL_DB", "spritpreise"))
        self._app = app

    def _connect(self):
        cfg = self._app.config
        db = Surreal(cfg["SURREAL_URL"])
        db.signin({"username": cfg["SURREAL_USER"], "password": cfg["SURREAL_PASS"]})
        db.use(cfg["SURREAL_NS"], cfg["SURREAL_DB"])
        return db

    @property
    def db(self):
        if self._db is None:
            self._db = self._connect()
        return self._db

    def query(self, sql: str, params: dict | None = None):
        try:
            return self.db.query(sql, params)
        except Exception:
            self._db = None
            return self._connect().query(sql, params)
