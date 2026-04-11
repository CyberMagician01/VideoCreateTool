from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

TEXT_SUFFIXES = {
    ".py",
    ".js",
    ".html",
    ".css",
    ".md",
    ".txt",
    ".json",
    ".yml",
    ".yaml",
}

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    "pwtmp",
    "node_modules",
}

LEGACY_HEURISTIC_ALLOWLIST = {
    "static/app.js",
    "scripts/check_encoding.py",
    "scripts/repair_project_names.py",
}

MOJIBAKE_TOKENS = (
    "锛",
    "銆",
    "鍙",
    "浣犳",
    "璇",
    "鏂",
    "缂",
    "闀",
    "椤",
    "鎿",
    "杩",
    "鐢",
    "鈥",
    "鈩",
)


def _iter_text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def _find_mojibake_hits(text: str) -> List[str]:
    hits = [token for token in MOJIBAKE_TOKENS if token in text]
    return hits


def _check_file(path: Path) -> Tuple[bool, str]:
    raw = path.read_bytes()

    if b"\xef\xbf\xbd" in raw:
        return False, "contains UTF-8 replacement bytes (EF BF BD)"

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return False, f"not valid UTF-8 ({exc})"

    hits = _find_mojibake_hits(text)
    if hits:
        return False, f"suspicious mojibake tokens: {', '.join(hits[:6])}"

    return True, ""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check repository text files for encoding issues.")
    parser.add_argument("--root", default=".", help="Workspace root path (default: current directory)")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"[error] root not found: {root}")
        return 2

    problems: List[Tuple[Path, str]] = []
    checked = 0
    for path in _iter_text_files(root):
        checked += 1
        rel = path.relative_to(root).as_posix()
        ok, detail = _check_file(path)
        if (
            not ok
            and detail.startswith("suspicious mojibake tokens:")
            and rel in LEGACY_HEURISTIC_ALLOWLIST
        ):
            continue
        if not ok:
            problems.append((path, detail))

    print(f"[encoding-check] scanned: {checked} files")
    if not problems:
        print("[encoding-check] PASS")
        return 0

    print(f"[encoding-check] FAIL: {len(problems)} file(s) with issues")
    for path, detail in problems:
        rel = path.relative_to(root)
        print(f" - {rel}: {detail}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
