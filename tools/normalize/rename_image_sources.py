#!/usr/bin/env python3
"""Rename image source files (.tex or .ggb) based on rename_preview.json.

For each entry in the JSON file produced by rename_exo7_images.py, this script
looks for accompanying source files inside src/exo7/images whose base name is
still the original image stem (e.g. img001234-1.tex). It renames these sources
according to the new exercise UUID and image index:

- .ggb files are renamed directly to <new_base>.ggb.
- .tex files are inspected to detect TikZ or PSTricks content and renamed to
  <uuid>-tikz-<index>.tex or <uuid>-ps-<index>.tex respectively.

Any actions (or skipped items) are written to a JSON log for traceability.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = REPO_ROOT / "rename_preview.json"
IMAGES_DIR = REPO_ROOT / "src" / "exo7" / "images"


@dataclass
class RenameInstruction:
    original_stem: str
    new_base: str
    uuid: str
    index: str


@dataclass
class SourceRename:
    source_path: Path
    dest_path: Path
    reason: str


@dataclass
class Skip:
    source_path: Path
    reason: str


def load_instructions(json_path: Path) -> List[RenameInstruction]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    instructions: Dict[str, RenameInstruction] = {}

    for entry in data.get("renames", []):
        original_include: str = entry.get("original_include", "")
        new_base: str = entry.get("new_base", "")
        if not original_include or not new_base:
            continue
        original_stem = Path(original_include).name
        if not original_stem:
            continue
        try:
            uuid, index = new_base.rsplit("-", 1)
        except ValueError:
            # Fallback: treat entire new_base as uuid, set index to "1"
            uuid, index = new_base, "1"
        # Keep only first occurrence for each original stem to avoid duplicates
        instructions.setdefault(original_stem, RenameInstruction(original_stem, new_base, uuid, index))
    return list(instructions.values())


def detect_tex_flavour(tex_path: Path) -> Optional[str]:
    try:
        content = tex_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = tex_path.read_text(encoding="latin-1")
    lower = content.lower()
    if "tikzpicture" in lower or "\\tikz" in lower:
        return "tikz"
    if "pspicture" in lower or "pstricks" in lower:
        return "ps"
    return None


def build_source_actions(instructions: List[RenameInstruction], dry_run: bool) -> Dict[str, List[Dict[str, str]]]:
    performed: List[Dict[str, str]] = []
    skipped: List[Dict[str, str]] = []

    for inst in instructions:
        original = inst.original_stem
        candidates = [IMAGES_DIR / f"{original}.tex", IMAGES_DIR / f"{original}.ggb"]
        for source_path in candidates:
            if not source_path.exists():
                continue
            if source_path.suffix == ".ggb":
                dest_path = source_path.with_name(f"{inst.new_base}.ggb")
                if dest_path.exists() and dest_path != source_path:
                    skipped.append({
                        "source": str(source_path.relative_to(REPO_ROOT)),
                        "reason": f"target already exists: {dest_path.name}",
                    })
                    continue
                if not dry_run and dest_path != source_path:
                    source_path.rename(dest_path)
                performed.append({
                    "source": str(source_path.relative_to(REPO_ROOT)),
                    "destination": str(dest_path.relative_to(REPO_ROOT)),
                    "type": "ggb",
                })
                continue

            if source_path.suffix == ".tex":
                flavour = detect_tex_flavour(source_path)
                if flavour is None:
                    skipped.append({
                        "source": str(source_path.relative_to(REPO_ROOT)),
                        "reason": "could not detect tikz or pstricks",
                    })
                    continue
                dest_name = f"{inst.uuid}-{flavour}-{inst.index}.tex"
                dest_path = source_path.with_name(dest_name)
                if dest_path.exists() and dest_path != source_path:
                    skipped.append({
                        "source": str(source_path.relative_to(REPO_ROOT)),
                        "reason": f"target already exists: {dest_path.name}",
                    })
                    continue
                if not dry_run and dest_path != source_path:
                    source_path.rename(dest_path)
                performed.append({
                    "source": str(source_path.relative_to(REPO_ROOT)),
                    "destination": str(dest_path.relative_to(REPO_ROOT)),
                    "type": flavour,
                })
    return {"renamed": performed, "skipped": skipped}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rename image source files using rename_preview.json")
    parser.add_argument("json", nargs="?", default=DEFAULT_JSON, type=Path, help="Path to rename_preview JSON file")
    parser.add_argument("--log", default=REPO_ROOT / "rename_source_log.json", type=Path, help="Where to write the results JSON")
    parser.add_argument("--dry-run", action="store_true", help="List actions without renaming files")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    json_path: Path = args.json
    if not json_path.exists():
        raise SystemExit(f"JSON file not found: {json_path}")
    if not IMAGES_DIR.exists():
        raise SystemExit(f"Images directory not found: {IMAGES_DIR}")

    instructions = load_instructions(json_path)
    results = build_source_actions(instructions, dry_run=args.dry_run)
    results.update({
        "json_source": str(json_path.relative_to(REPO_ROOT)),
        "dry_run": args.dry_run,
    })
    args.log.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.dry_run:
        print(f"Dry run complete. Planned operations written to {args.log}")
    else:
        print(f"Source renames applied. Log written to {args.log}")


if __name__ == "__main__":
    main()
