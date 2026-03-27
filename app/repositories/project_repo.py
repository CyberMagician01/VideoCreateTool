import json
import sqlite3
from typing import Any, Dict, List, Optional

from app.config import DATA_DIR, DB_PATH
from app.utils.helpers import _default_project_state, _utc_now_iso
from app.utils.normalizers import _normalize_project_state


def _get_db_conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_projects_db() -> None:
    with _get_db_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                creator TEXT DEFAULT '',
                description TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                cover_image TEXT DEFAULT '',
                last_provider TEXT DEFAULT '',
                deleted INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS project_states (
                project_id INTEGER PRIMARY KEY,
                state_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
            """
        )
        conn.commit()


def _row_to_project_meta(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "creator": row["creator"] or "",
        "description": row["description"] or "",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "cover_image": row["cover_image"] or "",
        "last_provider": row["last_provider"] or "",
    }


def _create_project(
    conn: sqlite3.Connection,
    *,
    name: str,
    creator: str = "",
    description: str = "",
    state: Optional[Dict[str, Any]] = None,
    cover_image: str = "",
    last_provider: str = "",
) -> Dict[str, Any]:
    now = _utc_now_iso()
    state_payload = _normalize_project_state(state)
    cur = conn.execute(
        """
        INSERT INTO projects(name, creator, description, created_at, updated_at, cover_image, last_provider, deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (name.strip(), creator.strip(), description.strip(), now, now, cover_image, last_provider),
    )
    project_id = cur.lastrowid
    conn.execute(
        """
        INSERT INTO project_states(project_id, state_json, updated_at)
        VALUES (?, ?, ?)
        """,
        (project_id, json.dumps(state_payload, ensure_ascii=False), now),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return _row_to_project_meta(row)


def _list_projects(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM projects
        WHERE deleted = 0
        ORDER BY datetime(updated_at) DESC, id DESC
        """
    ).fetchall()
    return [_row_to_project_meta(r) for r in rows]


def _ensure_default_project(conn: sqlite3.Connection) -> Dict[str, Any]:
    projects = _list_projects(conn)
    if projects:
        return projects[0]
    return _create_project(conn, name="未命名项目")


def _get_project_with_state(conn: sqlite3.Connection, project_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT * FROM projects WHERE id = ? AND deleted = 0",
        (project_id,),
    ).fetchone()
    if not row:
        return None

    state_row = conn.execute(
        "SELECT state_json FROM project_states WHERE project_id = ?",
        (project_id,),
    ).fetchone()

    state_obj: Dict[str, Any] = _default_project_state()
    if state_row and state_row["state_json"]:
        try:
            parsed = json.loads(state_row["state_json"])
            if isinstance(parsed, dict):
                state_obj = _normalize_project_state(parsed)
        except json.JSONDecodeError:
            state_obj = _default_project_state()

    return {
        "project": _row_to_project_meta(row),
        "state": state_obj,
    }