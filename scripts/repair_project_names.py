from __future__ import annotations

import argparse
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

DB_PATH = Path("data/projects.db")
LOG_PATH = Path("data/name_repair_log.json")

MOJIBAKE_CHARS = set("锛銆鍙浣犳璇鏂缂闀椤鎿杩鐢鈥鈩")


def _is_suspicious_name(name: str) -> bool:
    text = str(name or "").strip()
    if not text:
        return True
    if chr(0xFFFD) in text:
        return True
    if "?" in text or "？" in text:
        return True
    if any(ch in MOJIBAKE_CHARS for ch in text):
        return True
    return False


def _digits(text: str) -> str:
    parts = re.findall(r"\d+", text or "")
    return "".join(parts)


def _build_project_name(project_id: int, old_name: str, used: set[str]) -> str:
    suffix = _digits(old_name)
    candidate = f"项目{suffix}" if suffix else f"项目{project_id}"
    if candidate not in used:
        used.add(candidate)
        return candidate
    i = 2
    while True:
        alt = f"{candidate}_{i}"
        if alt not in used:
            used.add(alt)
            return alt
        i += 1


def _build_snapshot_name(snapshot_id: int, old_name: str, used: set[str]) -> str:
    suffix = _digits(old_name)
    candidate = f"快照{suffix}" if suffix else f"快照{snapshot_id}"
    if candidate not in used:
        used.add(candidate)
        return candidate
    i = 2
    while True:
        alt = f"{candidate}_{i}"
        if alt not in used:
            used.add(alt)
            return alt
        i += 1


def _repair(db_path: Path, apply: bool) -> Tuple[List[Dict], List[Dict]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        projects = conn.execute(
            "SELECT id, name, deleted FROM projects ORDER BY id ASC"
        ).fetchall()
        snapshots = conn.execute(
            "SELECT id, project_id, name FROM project_snapshots ORDER BY id ASC"
        ).fetchall()

        used_project_names = {str(r["name"] or "").strip() for r in projects if str(r["name"] or "").strip()}
        used_snapshot_names = {str(r["name"] or "").strip() for r in snapshots if str(r["name"] or "").strip()}

        project_updates: List[Dict] = []
        for row in projects:
            old_name = str(row["name"] or "").strip()
            if not _is_suspicious_name(old_name):
                continue
            new_name = _build_project_name(int(row["id"]), old_name, used_project_names)
            project_updates.append(
                {"id": int(row["id"]), "deleted": int(row["deleted"] or 0), "old_name": old_name, "new_name": new_name}
            )

        snapshot_updates: List[Dict] = []
        for row in snapshots:
            old_name = str(row["name"] or "").strip()
            if not _is_suspicious_name(old_name):
                continue
            new_name = _build_snapshot_name(int(row["id"]), old_name, used_snapshot_names)
            snapshot_updates.append(
                {"id": int(row["id"]), "project_id": int(row["project_id"]), "old_name": old_name, "new_name": new_name}
            )

        if apply and (project_updates or snapshot_updates):
            for item in project_updates:
                conn.execute(
                    "UPDATE projects SET name = ? WHERE id = ?",
                    (item["new_name"], item["id"]),
                )
            for item in snapshot_updates:
                conn.execute(
                    "UPDATE project_snapshots SET name = ? WHERE id = ?",
                    (item["new_name"], item["id"]),
                )
            conn.commit()

        return project_updates, snapshot_updates
    finally:
        conn.close()


def _append_log(project_updates: List[Dict], snapshot_updates: List[Dict]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project_updates": project_updates,
        "snapshot_updates": snapshot_updates,
    }
    history: List[Dict] = []
    if LOG_PATH.exists():
        try:
            history = json.loads(LOG_PATH.read_text(encoding="utf-8"))
            if not isinstance(history, list):
                history = []
        except Exception:
            history = []
    history.append(payload)
    LOG_PATH.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair suspicious project/snapshot names in projects.db.")
    parser.add_argument("--apply", action="store_true", help="Apply updates to the database.")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"[repair] database not found: {DB_PATH}")
        return 2

    project_updates, snapshot_updates = _repair(DB_PATH, apply=args.apply)

    print(f"[repair] suspicious projects: {len(project_updates)}")
    for item in project_updates:
        print(f" - project#{item['id']}: {item['old_name']!r} -> {item['new_name']!r}")

    print(f"[repair] suspicious snapshots: {len(snapshot_updates)}")
    for item in snapshot_updates:
        print(f" - snapshot#{item['id']}: {item['old_name']!r} -> {item['new_name']!r}")

    if not args.apply:
        print("[repair] dry-run only. Use --apply to write changes.")
        return 0

    _append_log(project_updates, snapshot_updates)
    print(f"[repair] applied. Log written to {LOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
