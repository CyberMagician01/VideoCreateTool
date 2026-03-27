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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS project_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                state_json TEXT NOT NULL,
                cover_image TEXT DEFAULT '',
                last_provider TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                source_updated_at TEXT DEFAULT '',
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


def _row_to_snapshot_meta(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "name": row["name"],
        "description": row["description"] or "",
        "cover_image": row["cover_image"] or "",
        "last_provider": row["last_provider"] or "",
        "created_at": row["created_at"],
        "source_updated_at": row["source_updated_at"] or "",
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


def _get_project_state_payload(conn: sqlite3.Connection, project_id: int) -> Dict[str, Any]:
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
    return state_obj


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

    return {
        "project": _row_to_project_meta(row),
        "state": _get_project_state_payload(conn, project_id),
    }


def _list_project_snapshots(conn: sqlite3.Connection, project_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, project_id, name, description, cover_image, last_provider, created_at, source_updated_at
        FROM project_snapshots
        WHERE project_id = ?
        ORDER BY datetime(created_at) DESC, id DESC
        """,
        (project_id,),
    ).fetchall()
    return [_row_to_snapshot_meta(row) for row in rows]


def _get_project_snapshot(
    conn: sqlite3.Connection, project_id: int, snapshot_id: int
) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        """
        SELECT id, project_id, name, description, state_json, cover_image, last_provider, created_at, source_updated_at
        FROM project_snapshots
        WHERE id = ? AND project_id = ?
        """,
        (snapshot_id, project_id),
    ).fetchone()
    if not row:
        return None

    try:
        state = json.loads(row["state_json"]) if row["state_json"] else _default_project_state()
    except json.JSONDecodeError:
        state = _default_project_state()

    return {
        "snapshot": _row_to_snapshot_meta(row),
        "state": _normalize_project_state(state),
    }


def _create_project_snapshot(
    conn: sqlite3.Connection,
    *,
    project_id: int,
    name: str,
    description: str = "",
    state: Optional[Dict[str, Any]] = None,
    cover_image: str = "",
    last_provider: str = "",
    source_updated_at: str = "",
) -> Dict[str, Any]:
    project_row = conn.execute(
        "SELECT cover_image, last_provider, updated_at FROM projects WHERE id = ? AND deleted = 0",
        (project_id,),
    ).fetchone()
    if not project_row:
        raise ValueError("Project not found.")

    state_payload = _normalize_project_state(
        state if isinstance(state, dict) else _get_project_state_payload(conn, project_id)
    )
    now = _utc_now_iso()
    cur = conn.execute(
        """
        INSERT INTO project_snapshots(project_id, name, description, state_json, cover_image, last_provider, created_at, source_updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            name.strip() or f"手动快照 {now}",
            description.strip(),
            json.dumps(state_payload, ensure_ascii=False),
            cover_image or (project_row["cover_image"] or ""),
            last_provider or (project_row["last_provider"] or ""),
            now,
            source_updated_at or (project_row["updated_at"] or ""),
        ),
    )
    conn.commit()
    snapshot_id = cur.lastrowid
    snapshot = _get_project_snapshot(conn, project_id, snapshot_id)
    return snapshot or {"snapshot": None, "state": state_payload}


def _duplicate_project(
    conn: sqlite3.Connection,
    *,
    project_id: int,
    name: Optional[str] = None,
    creator: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    current = _get_project_with_state(conn, project_id)
    if not current:
        raise ValueError("Project not found.")

    project = current["project"]
    new_project = _create_project(
        conn,
        name=(name or f"{project['name']} - 副本").strip(),
        creator=(creator if creator is not None else project.get("creator", "")).strip(),
        description=(description if description is not None else project.get("description", "")).strip(),
        state=current["state"],
        cover_image=project.get("cover_image", ""),
        last_provider=project.get("last_provider", ""),
    )
    duplicated = _get_project_with_state(conn, int(new_project["id"]))
    return duplicated or {"project": new_project, "state": current["state"]}


def _restore_project_snapshot(
    conn: sqlite3.Connection,
    *,
    project_id: int,
    snapshot_id: int,
    create_backup: bool = True,
) -> Dict[str, Any]:
    project = _get_project_with_state(conn, project_id)
    if not project:
        raise ValueError("Project not found.")

    snapshot = _get_project_snapshot(conn, project_id, snapshot_id)
    if not snapshot:
        raise ValueError("Snapshot not found.")

    backup_snapshot = None
    if create_backup:
        backup_snapshot = _create_project_snapshot(
            conn,
            project_id=project_id,
            name=f"回滚前保护 {snapshot['snapshot']['name']}",
            description="系统在回滚前自动创建的保护快照",
            state=project["state"],
            cover_image=project["project"].get("cover_image", ""),
            last_provider=project["project"].get("last_provider", ""),
            source_updated_at=project["project"].get("updated_at", ""),
        )

    now = _utc_now_iso()
    conn.execute(
        """
        INSERT INTO project_states(project_id, state_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(project_id) DO UPDATE SET
            state_json = excluded.state_json,
            updated_at = excluded.updated_at
        """,
        (project_id, json.dumps(snapshot["state"], ensure_ascii=False), now),
    )
    conn.execute(
        "UPDATE projects SET updated_at = ?, cover_image = ?, last_provider = ? WHERE id = ?",
        (
            now,
            snapshot["snapshot"].get("cover_image", project["project"].get("cover_image", "")),
            snapshot["snapshot"].get("last_provider", project["project"].get("last_provider", "")),
            project_id,
        ),
    )
    conn.commit()

    restored = _get_project_with_state(conn, project_id)
    return {
        "project": restored["project"] if restored else project["project"],
        "state": restored["state"] if restored else snapshot["state"],
        "snapshot": snapshot["snapshot"],
        "backup_snapshot": backup_snapshot["snapshot"] if backup_snapshot else None,
    }
