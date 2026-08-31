#!/usr/bin/env python3
"""Build the Exo7 id -> OpenYourMath UUID manifest."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


UUID_RE = re.compile(r"\\uuid\{([^}]*)\}")
EXO7ID_RE = re.compile(r"\\exo7id\{([^}]*)\}")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def first_match(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    if not match:
        return None
    return match.group(1).strip()


def as_int(value: str | None) -> int | None:
    if value is None:
        return None
    if not value.isdigit():
        return None
    return int(value)


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def load_legacy_entries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in {path}")
    return data


def build_manifest(root: Path, legacy_path: Path) -> dict[str, Any]:
    root = root.resolve()
    exercises_root = root / "content" / "exercises" / "exo7"
    legacy_entries = load_legacy_entries(legacy_path)
    legacy_by_id = {entry["exo7id"]: entry for entry in legacy_entries if "exo7id" in entry}

    mappings: list[dict[str, Any]] = []
    anomalies: dict[str, Any] = {
        "missing_uuid": [],
        "missing_exo7id": [],
        "uuid_filename_mismatch": [],
        "duplicate_uuid_in_content": [],
        "duplicate_exo7id_in_content": [],
        "legacy_uuid_mismatch": [],
        "legacy_only": [],
        "content_only": [],
        "legacy_duplicate_uuid": [],
        "legacy_numeric_uuid": [],
    }

    uuid_to_paths: dict[str, list[str]] = defaultdict(list)
    exo7id_to_paths: dict[int, list[str]] = defaultdict(list)
    content_ids: set[int] = set()

    for tex_path in sorted(exercises_root.rglob("*.tex")):
        text = read_text(tex_path)
        declared_uuid = first_match(UUID_RE, text)
        exo7id = as_int(first_match(EXO7ID_RE, text))
        file_uuid = tex_path.stem
        rel_path = relative(tex_path, root)

        if declared_uuid is None:
            anomalies["missing_uuid"].append({"path": rel_path})
        elif declared_uuid != file_uuid:
            anomalies["uuid_filename_mismatch"].append(
                {"path": rel_path, "file_uuid": file_uuid, "declared_uuid": declared_uuid}
            )
        if exo7id is None:
            anomalies["missing_exo7id"].append({"path": rel_path, "uuid": declared_uuid or file_uuid})

        uuid = declared_uuid or file_uuid
        uuid_to_paths[uuid].append(rel_path)
        if exo7id is not None:
            exo7id_to_paths[exo7id].append(rel_path)
            content_ids.add(exo7id)

        legacy = legacy_by_id.get(exo7id) if exo7id is not None else None
        legacy_uuid = legacy.get("uuid") if legacy else None
        if legacy and legacy_uuid != uuid:
            anomalies["legacy_uuid_mismatch"].append(
                {
                    "exo7id": exo7id,
                    "content_uuid": uuid,
                    "legacy_uuid": legacy_uuid,
                    "path": rel_path,
                }
            )

        mappings.append(
            {
                "exo7id": exo7id,
                "uuid": uuid,
                "path": rel_path,
                "legacy_uuid": legacy_uuid,
                "source_file": f"exercices/ex{exo7id:06d}.txt" if exo7id is not None else None,
                "status": "ok" if exo7id is not None and declared_uuid == file_uuid else "content_anomaly",
            }
        )

    for uuid, paths in sorted(uuid_to_paths.items()):
        if len(paths) > 1:
            anomalies["duplicate_uuid_in_content"].append({"uuid": uuid, "paths": paths})
    for exo7id, paths in sorted(exo7id_to_paths.items()):
        if len(paths) > 1:
            anomalies["duplicate_exo7id_in_content"].append({"exo7id": exo7id, "paths": paths})

    legacy_ids = {entry["exo7id"] for entry in legacy_entries if "exo7id" in entry}
    for exo7id in sorted(legacy_ids - content_ids):
        entry = legacy_by_id[exo7id]
        anomalies["legacy_only"].append(
            {
                "exo7id": exo7id,
                "legacy_uuid": entry.get("uuid"),
                "source_file": f"exercices/ex{exo7id:06d}.txt",
            }
        )
    for exo7id in sorted(content_ids - legacy_ids):
        paths = exo7id_to_paths[exo7id]
        anomalies["content_only"].append({"exo7id": exo7id, "paths": paths})

    legacy_uuid_counter: Counter[str] = Counter(str(entry.get("uuid")) for entry in legacy_entries)
    legacy_uuid_entries: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in legacy_entries:
        uuid = str(entry.get("uuid"))
        legacy_uuid_entries[uuid].append({"exo7id": entry.get("exo7id"), "uuid": entry.get("uuid")})
        if uuid.isdigit():
            anomalies["legacy_numeric_uuid"].append(
                {"exo7id": entry.get("exo7id"), "legacy_uuid": entry.get("uuid")}
            )
    for uuid, count in sorted(legacy_uuid_counter.items()):
        if count > 1:
            anomalies["legacy_duplicate_uuid"].append({"uuid": uuid, "entries": legacy_uuid_entries[uuid]})

    return {
        "schema": "exo7-id-map/v1",
        "source": "exo7",
        "generated_from": {
            "content_root": relative(exercises_root, root),
            "legacy_migration_file": relative(legacy_path, root),
        },
        "summary": {
            "mapping_count": len(mappings),
            "legacy_count": len(legacy_entries),
            "anomaly_counts": {key: len(value) for key, value in anomalies.items()},
        },
        "mappings": sorted(mappings, key=lambda item: (item["exo7id"] is None, item["exo7id"] or 0, item["uuid"])),
        "anomalies": anomalies,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Exo7 id to UUID manifest.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--legacy",
        type=Path,
        default=None,
        help="Path to migrations/exo7/exercices.json. Defaults under --root.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output manifest path. Defaults to sources/manifests/exo7-id-map.json under --root.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    legacy = args.legacy or root / "migrations" / "exo7" / "exercices.json"
    output = args.output or root / "sources" / "manifests" / "exo7-id-map.json"
    manifest = build_manifest(root, legacy.resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
