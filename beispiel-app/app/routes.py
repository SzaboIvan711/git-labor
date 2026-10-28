from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template, request

from app.models import ValidationError, validate_done, validate_title

bp = Blueprint("main", __name__)


def _repo():
    return current_app.extensions["repository"]


def _config():
    return current_app.extensions["app_config"]


@bp.errorhandler(ValidationError)
def _handle_validation_error(exc: ValidationError):
    return jsonify(error=str(exc)), 400


@bp.get("/")
def index():
    return render_template("index.html", version=_config().version)


@bp.get("/health")
def health():
    """Liveness: is the process up? Must not touch the database.

    Kubernetes restarts the container when this fails, so a slow database
    must never be able to trigger a restart loop.
    """
    return jsonify(status="ok", version=_config().version)


@bp.get("/ready")
def ready():
    """Readiness: can this instance serve traffic? Checks dependencies."""
    if _repo().healthy():
        return jsonify(status="ready")
    return jsonify(status="unavailable"), 503


@bp.get("/api/tasks")
def list_tasks():
    return jsonify([t.to_dict() for t in _repo().list()])


@bp.post("/api/tasks")
def create_task():
    payload = request.get_json(silent=True) or {}
    title = validate_title(payload.get("title"))
    task = _repo().add(title)
    return jsonify(task.to_dict()), 201


@bp.get("/api/tasks/<int:task_id>")
def get_task(task_id: int):
    task = _repo().get(task_id)
    if task is None:
        return jsonify(error="task not found"), 404
    return jsonify(task.to_dict())


@bp.put("/api/tasks/<int:task_id>")
def update_task(task_id: int):
    payload = request.get_json(silent=True) or {}
    done = validate_done(payload.get("done"))
    task = _repo().set_done(task_id, done)
    if task is None:
        return jsonify(error="task not found"), 404
    return jsonify(task.to_dict())


@bp.delete("/api/tasks/<int:task_id>")
def delete_task(task_id: int):
    if not _repo().delete(task_id):
        return jsonify(error="task not found"), 404
    return "", 204


@bp.get("/api/tasks/stats")
def get_stats():
    tasks = _repo().list()

    total = len(tasks)
    done = sum(1 for task in tasks if task.done)
    open_tasks = total - done

    return jsonify({"total": total, "done": done, "open": open_tasks})
