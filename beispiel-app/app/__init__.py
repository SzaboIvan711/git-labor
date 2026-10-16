from __future__ import annotations

import logging

from flask import Flask
from prometheus_client import CollectorRegistry
from prometheus_flask_exporter import PrometheusMetrics

from app.config import Config
from app.repository import TaskRepository, create_repository


def create_app(
    config: Config | None = None,
    repository: TaskRepository | None = None,
    registry: CollectorRegistry | None = None,
) -> Flask:
    """Application factory.

    Every argument can be injected, which is what the test suite does to run
    against the in-memory repository without touching the environment.

    `registry` defaults to the global Prometheus registry. Tests pass a fresh
    one per app, otherwise the second create_app() call in a session would try
    to register the same metric names twice.
    """
    config = config or Config.from_env()

    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    app = Flask(__name__)
    app.extensions["app_config"] = config
    app.extensions["repository"] = repository or create_repository(config)

    metrics = PrometheusMetrics(app, registry=registry)
    metrics.info("taskboard_info", "Application info", version=config.version)

    from app.routes import bp

    app.register_blueprint(bp)
    return app
