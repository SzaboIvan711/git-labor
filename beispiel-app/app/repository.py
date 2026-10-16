from __future__ import annotations

import logging
import threading
from typing import Protocol

from app.config import Config
from app.models import Task

log = logging.getLogger(__name__)


class TaskRepository(Protocol):
    """Storage contract. Routes depend on this, never on a concrete backend."""

    def list(self) -> list[Task]: ...
    def get(self, task_id: int) -> Task | None: ...
    def add(self, title: str) -> Task: ...
    def set_done(self, task_id: int, done: bool) -> Task | None: ...
    def delete(self, task_id: int) -> bool: ...
    def healthy(self) -> bool: ...


class InMemoryTaskRepository:
    """Default backend. Data is lost when the process exits.

    Good enough for tests and for week 3, where no database exists yet.
    """

    def __init__(self) -> None:
        self._tasks: dict[int, Task] = {}
        self._next_id = 1
        self._lock = threading.Lock()

    def list(self) -> list[Task]:
        with self._lock:
            return sorted(self._tasks.values(), key=lambda t: t.id)

    def get(self, task_id: int) -> Task | None:
        with self._lock:
            return self._tasks.get(task_id)

    def add(self, title: str) -> Task:
        with self._lock:
            task = Task(id=self._next_id, title=title)
            self._tasks[task.id] = task
            self._next_id += 1
            return task

    def set_done(self, task_id: int, done: bool) -> Task | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            task.done = done
            return task

    def delete(self, task_id: int) -> bool:
        with self._lock:
            return self._tasks.pop(task_id, None) is not None

    def healthy(self) -> bool:
        return True


class PostgresTaskRepository:
    """Postgres backend, used from week 4 onwards via Docker Compose."""

    def __init__(self, dsn: str) -> None:
        import psycopg
        from psycopg_pool import ConnectionPool

        self._psycopg = psycopg
        self._pool = ConnectionPool(dsn, min_size=1, max_size=5, open=True)
        self._create_schema()

    def _create_schema(self) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id    SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    done  BOOLEAN NOT NULL DEFAULT FALSE
                )
                """
            )

    def list(self) -> list[Task]:
        with self._pool.connection() as conn:
            rows = conn.execute("SELECT id, title, done FROM tasks ORDER BY id").fetchall()
        return [Task(*row) for row in rows]

    def get(self, task_id: int) -> Task | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT id, title, done FROM tasks WHERE id = %s", (task_id,)
            ).fetchone()
        return Task(*row) if row else None

    def add(self, title: str) -> Task:
        with self._pool.connection() as conn:
            row = conn.execute(
                "INSERT INTO tasks (title) VALUES (%s) RETURNING id, title, done", (title,)
            ).fetchone()
        return Task(*row)

    def set_done(self, task_id: int, done: bool) -> Task | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                "UPDATE tasks SET done = %s WHERE id = %s RETURNING id, title, done",
                (done, task_id),
            ).fetchone()
        return Task(*row) if row else None

    def delete(self, task_id: int) -> bool:
        with self._pool.connection() as conn:
            result = conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        return result.rowcount > 0

    def healthy(self) -> bool:
        try:
            with self._pool.connection() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:
            log.exception("database health check failed")
            return False


def create_repository(config: Config) -> TaskRepository:
    if config.database_url:
        log.info("using postgres repository")
        return PostgresTaskRepository(config.database_url)
    # Each gunicorn worker imports the app separately, so an in-memory store is
    # NOT shared between workers: a task created on worker 1 is invisible to
    # worker 2. Fine for tests and single-worker development, wrong for anything
    # scaled out. Set DATABASE_URL to get a shared store.
    log.warning(
        "no DATABASE_URL set, using in-memory repository: "
        "state is per-process and is lost on restart"
    )
    return InMemoryTaskRepository()
