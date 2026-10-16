import pytest
from prometheus_client import CollectorRegistry

from app import create_app
from app.config import Config
from app.repository import InMemoryTaskRepository


@pytest.fixture
def app():
    config = Config(database_url=None, version="test", log_level="WARNING")
    return create_app(
        config=config,
        repository=InMemoryTaskRepository(),
        registry=CollectorRegistry(),
    )


@pytest.fixture
def client(app):
    return app.test_client()
