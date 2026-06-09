#!/usr/bin/env python3
"""Import TikZ source files from exercices-exo7 into exobase.

Two operations are performed:

1. COPY: `.tex` files in exercices-exo7/images/ named `img{6digits}-{index}.tex`
   are copied to content/images/exo7/tikz/ and renamed `{uuid}-tikz-{index}.tex`
   using the mapping from sources/manifests/exo7-id-map.json.

2. MOVE: misplaced `.tex` files at the root of content/images/exo7/ (same pattern)
   are moved into content/images/exo7/tikz/ with the same renaming.

Files that cannot be resolved to a UUID, or whose target already exists, are
reported in the "skipped" section of the log.

Usage:
    python tools/import/import_exo7_tikz.py [--exo7-repo PATH] [--log PATH] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
IMAGES_DIR = REPO_ROOT / "content" / "images" / "exo7"
TIKZ_DIR = IMAGES_DIR / "tikz"
MAP_FILE = REPO_ROOT / "sources" / "manifests" / "exo7-id-map.json"

# Default path of the exercices-exo7 clone (sibling of exobase)
DEFAULT_EXO7_REPO = REPO_ROOT.parent / "exercices-exo7"

IMG_PATTERN = re.compile(r"^img(\d+)-(\d+)\.tex$")


@dataclass
class CopyOp:
    source: Path
    dest: Path
    exo7id: int
    uuid: str
    index: int
    kind: str  # "copy" | "move"


@dataclass
class SkippedOp:
    source: Path
    reason: str


def load_id_map(map_file: Path) -> Dict[int, str]:
    data = json.loads(map_file.read_text(encoding="utf-8"))
    return {m["exo7id"]: m["uuid"] for m in data["mappings"] if m.get("uuid") and m.get("exo7id")}


def plan_copies(exo7_images: Path, id_to_uuid: Dict[int, str]) -> tuple[List[CopyOp], List[SkippedOp]]:
    ops: List[CopyOp] = []
    skipped: List[SkippedOp] = []
    existing_targets = {f.name for f in TIKZ_DIR.glob("*-tikz-*.tex")} if TIKZ_DIR.exists() else set()

    for src in sorted(exo7_images.glob("img*.tex")):
        m = IMG_PATTERN.match(src.name)
        if not m:
            skipped.append(SkippedOp(source=src, reason="non-standard filename, cannot resolve exo7id"))
            continue
        exo7id, idx = int(m.group(1)), int(m.group(2))
        uuid = id_to_uuid.get(exo7id)
        if not uuid:
            skipped.append(SkippedOp(source=src, reason=f"exo7id {exo7id} not found in id-map"))
            continue
        dest_name = f"{uuid}-tikz-{idx}.tex"
        if dest_name in existing_targets:
            skipped.append(SkippedOp(source=src, reason=f"target {dest_name} already exists in tikz/"))
            continue
        ops.append(CopyOp(source=src, dest=TIKZ_DIR / dest_name,
                          exo7id=exo7id, uuid=uuid, index=idx, kind="copy"))
        existing_targets.add(dest_name)

    return ops, skipped


def plan_moves(id_to_uuid: Dict[int, str]) -> tuple[List[CopyOp], List[SkippedOp]]:
    ops: List[CopyOp] = []
    skipped: List[SkippedOp] = []
    existing_targets = {f.name for f in TIKZ_DIR.glob("*-tikz-*.tex")} if TIKZ_DIR.exists() else set()

    for src in sorted(IMAGES_DIR.glob("*.tex")):
        m = IMG_PATTERN.match(src.name)
        if not m:
            skipped.append(SkippedOp(source=src, reason="non-standard filename, cannot resolve exo7id"))
            continue
        exo7id, idx = int(m.group(1)), int(m.group(2))
        uuid = id_to_uuid.get(exo7id)
        if not uuid:
            skipped.append(SkippedOp(source=src, reason=f"exo7id {exo7id} not found in id-map"))
            continue
        dest_name = f"{uuid}-tikz-{idx}.tex"
        if dest_name in existing_targets:
            skipped.append(SkippedOp(source=src, reason=f"target {dest_name} already exists in tikz/"))
            continue
        ops.append(CopyOp(source=src, dest=TIKZ_DIR / dest_name,
                          exo7id=exo7id, uuid=uuid, index=idx, kind="move"))
        existing_targets.add(dest_name)

    return ops, skipped


def execute(ops: List[CopyOp], skipped: List[SkippedOp], log_path: Path, dry_run: bool) -> None:
    if not dry_run:
        TIKZ_DIR.mkdir(parents=True, exist_ok=True)

    done: List[Dict] = []
    for op in ops:
        rel_src = op.source.relative_to(REPO_ROOT) if REPO_ROOT in op.source.parents else op.source
        rel_dest = op.dest.relative_to(REPO_ROOT)
        if not dry_run:
            if op.kind == "move":
                op.source.rename(op.dest)
            else:
                shutil.copy2(op.source, op.dest)
        done.append({
            "kind": op.kind,
            "from": str(rel_src),
            "to": str(rel_dest),
            "exo7id": op.exo7id,
            "uuid": op.uuid,
        })

    log_data = {
        "dry_run": dry_run,
        "summary": {"done": len(done), "skipped": len(skipped)},
        "done": done,
        "skipped": [{"source": str(s.source), "reason": s.reason} for s in skipped],
    }
    log_path.write_text(json.dumps(log_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    label = "[DRY RUN] " if dry_run else ""
    print(f"{label}Opérations effectuées : {len(done)}")
    print(f"{label}Ignorées              : {len(skipped)}")
    print(f"Log écrit dans        : {log_path}")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import TikZ sources from exercices-exo7 into exobase.")
    parser.add_argument(
        "--exo7-repo",
        type=Path,
        default=DEFAULT_EXO7_REPO,
        help=f"Path to the exercices-exo7 clone (default: {DEFAULT_EXO7_REPO})",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=REPO_ROOT / "logs" / "import_tikz.json",
        help="Path to the JSON log file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate without touching files.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)

    exo7_images = args.exo7_repo / "images"
    if not exo7_images.exists():
        print(f"[ERROR] exercices-exo7 images dir not found: {exo7_images}", file=sys.stderr)
        sys.exit(1)
    if not MAP_FILE.exists():
        print(f"[ERROR] id-map not found: {MAP_FILE}", file=sys.stderr)
        sys.exit(1)

    id_to_uuid = load_id_map(MAP_FILE)

    copy_ops, copy_skipped = plan_copies(exo7_images, id_to_uuid)
    move_ops, move_skipped = plan_moves(id_to_uuid)

    all_ops = copy_ops + move_ops
    all_skipped = copy_skipped + move_skipped

    print(f"Copies planifiées : {len(copy_ops)}")
    print(f"Déplacements      : {len(move_ops)}")
    print(f"Ignorés           : {len(all_skipped)}")

    args.log.parent.mkdir(parents=True, exist_ok=True)
    execute(all_ops, all_skipped, args.log, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
