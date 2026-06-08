#!/usr/bin/env python3
"""Inventory exobase content without modifying it."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


UUID_RE = re.compile(r"\\uuid\{([^}]*)\}")
TEMP_IMAGE_RE = re.compile(r"(_tmp|contourtmp|\.aux$|\.log$|\.out$|\.synctex)", re.I)


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def read_uuid(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")
    match = UUID_RE.search(text)
    if not match:
        return None
    return match.group(1).strip()


def inventory_exercises(root: Path, include_files: bool) -> dict[str, Any]:
    exercises_root = root / "content" / "exercises"
    sources: dict[str, Any] = {}

    if not exercises_root.exists():
        return sources

    for source_dir in sorted(path for path in exercises_root.iterdir() if path.is_dir()):
        source = source_dir.name
        tex_files = sorted(source_dir.rglob("*.tex"))
        missing_uuid: list[str] = []
        uuid_mismatches: list[dict[str, str]] = []
        uuids: Counter[str] = Counter()
        files: list[dict[str, str | None]] = []

        for tex_path in tex_files:
            declared_uuid = read_uuid(tex_path)
            file_uuid = tex_path.stem
            if declared_uuid is None:
                missing_uuid.append(relative(tex_path, root))
            else:
                uuids[declared_uuid] += 1
                if declared_uuid != file_uuid:
                    uuid_mismatches.append(
                        {
                            "path": relative(tex_path, root),
                            "file_uuid": file_uuid,
                            "declared_uuid": declared_uuid,
                        }
                    )

            if include_files:
                files.append(
                    {
                        "path": relative(tex_path, root),
                        "declared_uuid": declared_uuid,
                    }
                )

        duplicate_uuids = [
            {"uuid": uuid, "count": count}
            for uuid, count in sorted(uuids.items())
            if count > 1
        ]

        data: dict[str, Any] = {
            "tex_count": len(tex_files),
            "missing_uuid_count": len(missing_uuid),
            "uuid_mismatch_count": len(uuid_mismatches),
            "duplicate_uuid_count": len(duplicate_uuids),
        }
        if missing_uuid:
            data["missing_uuid_samples"] = missing_uuid[:20]
        if uuid_mismatches:
            data["uuid_mismatch_samples"] = uuid_mismatches[:20]
        if duplicate_uuids:
            data["duplicate_uuid_samples"] = duplicate_uuids[:20]
        if include_files:
            data["files"] = files
        sources[source] = data

    return sources


def inventory_images(root: Path, include_files: bool) -> dict[str, Any]:
    images_root = root / "content" / "images"
    sources: dict[str, Any] = {}

    if not images_root.exists():
        return sources

    for source_dir in sorted(path for path in images_root.iterdir() if path.is_dir()):
        source = source_dir.name
        extension_counts: Counter[str] = Counter()
        temporary_files: list[str] = []
        files: list[str] = []

        for image_path in sorted(path for path in source_dir.rglob("*") if path.is_file()):
            suffix = image_path.suffix.lower() or "<none>"
            extension_counts[suffix] += 1
            rel_path = relative(image_path, root)

            if TEMP_IMAGE_RE.search(image_path.name):
                temporary_files.append(rel_path)
            if include_files:
                files.append(rel_path)

        data: dict[str, Any] = {
            "file_count": sum(extension_counts.values()),
            "extensions": dict(sorted(extension_counts.items())),
            "temporary_candidate_count": len(temporary_files),
        }
        if temporary_files:
            data["temporary_candidate_samples"] = temporary_files[:30]
        if include_files:
            data["files"] = files
        sources[source] = data

    return sources


def inventory_archive(root: Path) -> dict[str, Any]:
    archive_root = root / "archive"
    metadata_legacy = archive_root / "metadata-legacy"
    src_old = root / "src_old"

    result: dict[str, Any] = {}
    if metadata_legacy.exists():
        result["metadata_legacy_file_count"] = sum(
            1 for path in metadata_legacy.rglob("*") if path.is_file()
        )
    if src_old.exists():
        by_source: dict[str, int] = {}
        for source_dir in sorted(path for path in src_old.iterdir() if path.is_dir()):
            by_source[source_dir.name] = sum(1 for path in source_dir.rglob("*.tex"))
        result["src_old_tex_counts"] = by_source

    return result


def build_inventory(root: Path, include_files: bool) -> dict[str, Any]:
    root = root.resolve()
    return {
        "root": root.as_posix(),
        "content": {
            "exercises": inventory_exercises(root, include_files),
            "images": inventory_images(root, include_files),
        },
        "archive": inventory_archive(root),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventorie exobase sans modifier les contenus."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Racine du depot exobase.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Ecrit le rapport JSON dans ce fichier. Par defaut, affiche sur stdout.",
    )
    parser.add_argument(
        "--include-files",
        action="store_true",
        help="Inclut la liste detaillee des fichiers dans le rapport.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Formate le JSON avec indentation.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_inventory(args.root, args.include_files)
    indent = 2 if args.pretty else None
    content = json.dumps(report, ensure_ascii=False, indent=indent)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content + "\n", encoding="utf-8")
        return

    print(content)


if __name__ == "__main__":
    main()
