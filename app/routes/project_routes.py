import json
from datetime import datetime
from typing import Any, List

from flask import Blueprint, jsonify, request

from app.repositories.project_repo import (
    _create_project,
    _create_project_snapshot,
    _duplicate_project,
    _ensure_default_project,
    _get_db_conn,
    _get_project_snapshot,
    _get_project_with_state,
    _list_project_snapshots,
    _list_projects,
    _restore_project_snapshot,
)
from app.utils.helpers import _utc_now_iso
from app.utils.normalizers import _normalize_project_state

project_bp = Blueprint("project", __name__)


@project_bp.get("/api/projects")
def get_projects():
    try:
        with _get_db_conn() as conn:
            projects = _list_projects(conn)
            return jsonify({"ok": True, "projects": projects})
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@project_bp.post("/api/projects")
def create_project_api():
    req_json = request.get_json(silent=True) or {}
    name = str(req_json.get("name", "")).strip()
    creator = str(req_json.get("creator", "")).strip()
    description = str(req_json.get("description", "")).strip()
    state = req_json.get("state")

    if not name:
        return jsonify({"ok": False, "error": "Project name is required."}), 400

    try:
        with _get_db_conn() as conn:
            project = _create_project(
                conn,
                name=name,
                creator=creator,
                description=description,
                state=state if isinstance(state, dict) else None,
                cover_image=str(req_json.get("cover_image", ""))[:200000],
                last_provider=str(req_json.get("last_provider", ""))[:64],
            )
            return jsonify({"ok": True, "project": project})
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@project_bp.get("/api/projects/<int:project_id>")
def get_project(project_id: int):
    try:
        with _get_db_conn() as conn:
            data = _get_project_with_state(conn, project_id)
            if not data:
                return jsonify({"ok": False, "error": "Project not found."}), 404
            return jsonify({"ok": True, **data})
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@project_bp.put("/api/projects/<int:project_id>")
def update_project(project_id: int):
    req_json = request.get_json(silent=True) or {}
    allowed_fields = {"name", "creator", "description", "cover_image", "last_provider"}

    try:
        with _get_db_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM projects WHERE id = ? AND deleted = 0",
                (project_id,),
            ).fetchone()
            if not existing:
                return jsonify({"ok": False, "error": "Project not found."}), 404

            updates: List[str] = []
            params: List[Any] = []

            for field in allowed_fields:
                if field in req_json:
                    updates.append(f"{field} = ?")
                    if field in {"cover_image", "description"}:
                        params.append(str(req_json.get(field, ""))[:200000])
                    elif field == "last_provider":
                        params.append(str(req_json.get(field, ""))[:64])
                    else:
                        params.append(str(req_json.get(field, ""))[:255])

            now = _utc_now_iso()
            updates.append("updated_at = ?")
            params.append(now)
            params.append(project_id)

            conn.execute(
                f"UPDATE projects SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )

            if "state" in req_json:
                state_obj = req_json.get("state")
                if not isinstance(state_obj, dict):
                    return jsonify({"ok": False, "error": "state must be an object."}), 400

                normalized_state = _normalize_project_state(state_obj)
                conn.execute(
                    """
                    INSERT INTO project_states(project_id, state_json, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(project_id) DO UPDATE SET
                        state_json = excluded.state_json,
                        updated_at = excluded.updated_at
                    """,
                    (project_id, json.dumps(normalized_state, ensure_ascii=False), now),
                )

            conn.commit()
            data = _get_project_with_state(conn, project_id)
            return jsonify({"ok": True, **(data or {})})
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@project_bp.delete("/api/projects/<int:project_id>")
def delete_project(project_id: int):
    try:
        with _get_db_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM projects WHERE id = ? AND deleted = 0",
                (project_id,),
            ).fetchone()
            if not existing:
                return jsonify({"ok": False, "error": "Project not found."}), 404

            now = _utc_now_iso()
            conn.execute(
                "UPDATE projects SET deleted = 1, updated_at = ? WHERE id = ?",
                (now, project_id),
            )
            conn.commit()

            fallback = _ensure_default_project(conn)
            projects = _list_projects(conn)
            return jsonify(
                {
                    "ok": True,
                    "deleted_project_id": project_id,
                    "fallback_project": fallback,
                    "projects": projects,
                }
            )
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@project_bp.post("/api/projects/<int:project_id>/duplicate")
def duplicate_project_api(project_id: int):
    req_json = request.get_json(silent=True) or {}
    try:
        with _get_db_conn() as conn:
            duplicated = _duplicate_project(
                conn,
                project_id=project_id,
                name=str(req_json.get("name", "")).strip() or None,
                creator=str(req_json.get("creator", "")).strip() or None,
                description=str(req_json.get("description", "")).strip() or None,
            )
            return jsonify(
                {
                    "ok": True,
                    "project": duplicated.get("project"),
                    "state": duplicated.get("state"),
                    "projects": _list_projects(conn),
                }
            )
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 404
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@project_bp.get("/api/projects/<int:project_id>/snapshots")
def list_project_snapshots(project_id: int):
    try:
        with _get_db_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM projects WHERE id = ? AND deleted = 0",
                (project_id,),
            ).fetchone()
            if not existing:
                return jsonify({"ok": False, "error": "Project not found."}), 404
            return jsonify({"ok": True, "snapshots": _list_project_snapshots(conn, project_id)})
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@project_bp.post("/api/projects/<int:project_id>/snapshots")
def create_project_snapshot_api(project_id: int):
    req_json = request.get_json(silent=True) or {}
    try:
        with _get_db_conn() as conn:
            project = _get_project_with_state(conn, project_id)
            if not project:
                return jsonify({"ok": False, "error": "Project not found."}), 404

            snapshot = _create_project_snapshot(
                conn,
                project_id=project_id,
                name=str(req_json.get("name", "")).strip() or f"手动快照 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                description=str(req_json.get("description", "")).strip(),
                state=req_json.get("state") if isinstance(req_json.get("state"), dict) else project["state"],
                source_updated_at=project["project"].get("updated_at", ""),
            )
            return jsonify(
                {
                    "ok": True,
                    "snapshot": snapshot.get("snapshot"),
                    "snapshots": _list_project_snapshots(conn, project_id),
                }
            )
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@project_bp.post("/api/projects/<int:project_id>/snapshots/<int:snapshot_id>/restore")
def restore_project_snapshot_api(project_id: int, snapshot_id: int):
    try:
        with _get_db_conn() as conn:
            restored = _restore_project_snapshot(conn, project_id=project_id, snapshot_id=snapshot_id)
            return jsonify(
                {
                    "ok": True,
                    "project": restored.get("project"),
                    "state": restored.get("state"),
                    "snapshot": restored.get("snapshot"),
                    "backup_snapshot": restored.get("backup_snapshot"),
                    "snapshots": _list_project_snapshots(conn, project_id),
                }
            )
    except ValueError as e:
        message = str(e)
        status_code = 404 if "not found" in message.lower() else 400
        return jsonify({"ok": False, "error": message}), status_code
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@project_bp.get("/api/projects/<int:project_id>/state")
def get_project_state(project_id: int):
    try:
        with _get_db_conn() as conn:
            data = _get_project_with_state(conn, project_id)
            if not data:
                return jsonify({"ok": False, "error": "Project not found."}), 404
            return jsonify({"ok": True, "project_id": project_id, "state": data["state"]})
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@project_bp.put("/api/projects/<int:project_id>/state")
@project_bp.post("/api/projects/<int:project_id>/state")
def put_project_state(project_id: int):
    req_json = request.get_json(silent=True) or {}
    state = req_json.get("state")
    if not isinstance(state, dict):
        return jsonify({"ok": False, "error": "state must be an object."}), 400

    normalized_state = _normalize_project_state(state)

    try:
        with _get_db_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM projects WHERE id = ? AND deleted = 0",
                (project_id,),
            ).fetchone()
            if not existing:
                return jsonify({"ok": False, "error": "Project not found."}), 404

            now = _utc_now_iso()
            conn.execute(
                """
                INSERT INTO project_states(project_id, state_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (project_id, json.dumps(normalized_state, ensure_ascii=False), now),
            )
            conn.execute(
                "UPDATE projects SET updated_at = ? WHERE id = ?",
                (now, project_id),
            )

            if "cover_image" in req_json:
                conn.execute(
                    "UPDATE projects SET cover_image = ? WHERE id = ?",
                    (str(req_json.get("cover_image", ""))[:200000], project_id),
                )
            if "last_provider" in req_json:
                conn.execute(
                    "UPDATE projects SET last_provider = ? WHERE id = ?",
                    (str(req_json.get("last_provider", ""))[:64], project_id),
                )

            conn.commit()
            return jsonify({"ok": True, "project_id": project_id, "updated_at": now})
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500
