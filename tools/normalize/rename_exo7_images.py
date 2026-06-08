#!/usr/bin/env python3
"""Rename exercise images referenced with \\includegraphics.

For every LaTeX exercise file under src/exo7 (excluding the images directory),
this script searches for \\includegraphics commands, renames the corresponding
image files inside src/exo7/images to follow the pattern
<exercise-uuid>-<index>.<ext>, updates the LaTeX references, and logs the
changes into a JSON file.

Usage:
    python script/rename_exo7_images.py [--log LOG_PATH] [--dry-run]

The JSON log contains two keys:
  - "renames": list of successful rename operations.
  - "skipped": list of references that were not renamed (e.g. missing image,
    shared across multiple exercises, or unsupported extension).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

# Directories relative to repository root
REPO_ROOT = Path(__file__).resolve().parents[1]
EXO7_DIR = REPO_ROOT / "src" / "exo7"
IMAGES_DIR = EXO7_DIR / "images"

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf", ".eps"}
INCLUDE_REGEX = re.compile(r"\\includegraphics(?:\[(?:(?!\]).)*\])?\{([^}]+)\}")


@dataclass
class IncludeMatch:
    start: int
    end: int
    raw_path: str
    prefix: str
    basename: str
    stem: str
    ext_in_tex: str


@dataclass
class TexFileData:
    path: Path
    content: str
    matches: List[IncludeMatch] = field(default_factory=list)


def split_path(raw_path: str) -> Optional[IncludeMatch]:
    cleaned = raw_path.strip()
    if not cleaned:
        return None
    last_slash = cleaned.rfind("/")
    if last_slash == -1:
        prefix = ""
        basename = cleaned
    else:
        prefix = cleaned[: last_slash + 1]
        basename = cleaned[last_slash + 1 :]
    stem = Path(basename).stem
    ext = Path(basename).suffix
    return IncludeMatch(start=0, end=0, raw_path=cleaned, prefix=prefix, basename=basename, stem=stem, ext_in_tex=ext)


def collect_tex_files() -> List[TexFileData]:
    tex_files: List[TexFileData] = []
    for tex_path in sorted(EXO7_DIR.rglob("*.tex")):
        if IMAGES_DIR in tex_path.parents:
            # Skip helper files bundled with the images directory
            continue
        try:
            content = tex_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            print(f"[WARN] Could not decode {tex_path} as UTF-8: {exc}", file=sys.stderr)
            continue
        matches: List[IncludeMatch] = []
        for match in INCLUDE_REGEX.finditer(content):
            raw = match.group(1)
            include_match = split_path(raw)
            if include_match is None:
                continue
            include_match.start, include_match.end = match.span(1)
            matches.append(include_match)
        if matches:
            tex_files.append(TexFileData(path=tex_path, content=content, matches=matches))
    return tex_files


def find_image_variants(stem: str) -> List[Path]:
    files = [p for p in IMAGES_DIR.glob(f"{stem}.*") if p.suffix.lower() in IMAGE_EXTENSIONS]
    return files


def ensure_unique_usage(tex_files: Sequence[TexFileData]) -> Dict[str, Set[Path]]:
    usage: Dict[str, Set[Path]] = {}
    for tex in tex_files:
        for match in tex.matches:
            if not match.stem:
                continue
            usage.setdefault(match.stem, set()).add(tex.path)
    return usage


def rename_images(tex_files: Sequence[TexFileData], log_path: Path, dry_run: bool = False) -> None:
    image_usage = ensure_unique_usage(tex_files)
    performed: Dict[str, str] = {}
    renames: List[Dict[str, object]] = []
    skipped: List[Dict[str, str]] = []

    for tex in tex_files:
        uuid = tex.path.stem
        file_counter = 0
        file_base_to_new: Dict[str, str] = {}
        updated_content_parts: List[str] = []
        cursor = 0
        content_changed = False

        for match in tex.matches:
            start, end = match.start, match.end
            raw_path_segment = tex.content[start:end]
            prefix = match.prefix
            stem = match.stem
            ext_in_tex = match.ext_in_tex
            original_include = prefix + match.basename

            updated_content_parts.append(tex.content[cursor:start])

            if not stem:
                skipped.append({
                    "tex_file": str(tex.path.relative_to(REPO_ROOT)),
                    "include_path": original_include,
                    "reason": "empty image stem"
                })
                updated_content_parts.append(raw_path_segment)
                cursor = end
                continue

            if stem in file_base_to_new:
                new_base = file_base_to_new[stem]
                if ext_in_tex:
                    new_include = prefix + new_base + ext_in_tex
                else:
                    new_include = prefix + new_base
                updated_content_parts.append(new_include)
                if new_include != raw_path_segment:
                    content_changed = True
                cursor = end
                continue

            variants = find_image_variants(stem)
            if not variants:
                skipped.append({
                    "tex_file": str(tex.path.relative_to(REPO_ROOT)),
                    "include_path": original_include,
                    "reason": "no image variants found"
                })
                updated_content_parts.append(raw_path_segment)
                cursor = end
                continue

            usage_paths = image_usage.get(stem, set())
            if len(usage_paths) > 1:
                skipped.append({
                    "tex_file": str(tex.path.relative_to(REPO_ROOT)),
                    "include_path": original_include,
                    "reason": "image shared by multiple exercises"
                })
                updated_content_parts.append(raw_path_segment)
                cursor = end
                continue

            file_counter += 1
            new_base = f"{uuid}-{file_counter}"

            if stem in performed and performed[stem] != new_base:
                skipped.append({
                    "tex_file": str(tex.path.relative_to(REPO_ROOT)),
                    "include_path": original_include,
                    "reason": "image stem already renamed elsewhere"
                })
                file_counter -= 1
                updated_content_parts.append(raw_path_segment)
                cursor = end
                continue

            candidate_pairs = []
            conflict = False
            for old_path in variants:
                new_path = old_path.with_name(new_base + old_path.suffix)
                if new_path.exists() and new_path != old_path:
                    print(f"[ERROR] Target already exists: {new_path}", file=sys.stderr)
                    skipped.append({
                        "tex_file": str(tex.path.relative_to(REPO_ROOT)),
                        "include_path": original_include,
                        "reason": f"target already exists: {new_path.name}"
                    })
                    conflict = True
                    break
                candidate_pairs.append((old_path, new_path))

            if conflict:
                file_counter -= 1
                updated_content_parts.append(raw_path_segment)
                cursor = end
                continue

            if stem == new_base:
                file_base_to_new[stem] = new_base
                performed[stem] = new_base
                skipped.append({
                    "tex_file": str(tex.path.relative_to(REPO_ROOT)),
                    "include_path": original_include,
                    "reason": "already matched target naming"
                })
                updated_content_parts.append(raw_path_segment)
                cursor = end
                continue

            rename_pairs: List[Dict[str, str]] = []
            for old_path, new_path in candidate_pairs:
                if old_path == new_path:
                    continue
                if not dry_run:
                    old_path.rename(new_path)
                rename_pairs.append({
                    "from": str(old_path.relative_to(REPO_ROOT)),
                    "to": str(new_path.relative_to(REPO_ROOT)),
                })

            if ext_in_tex:
                new_include = prefix + new_base + ext_in_tex
            else:
                new_include = prefix + new_base
            performed[stem] = new_base
            file_base_to_new[stem] = new_base
            renames.append({
                "tex_file": str(tex.path.relative_to(REPO_ROOT)),
                "image_index": file_counter,
                "original_include": original_include,
                "new_base": new_base,
                "new_include": new_include,
                "renamed_files": rename_pairs,
            })
            updated_content_parts.append(new_include)
            if new_include != raw_path_segment:
                content_changed = True

            cursor = end

        updated_content_parts.append(tex.content[cursor:])
        if content_changed and not dry_run:
            tex.path.write_text("".join(updated_content_parts), encoding="utf-8")

    log_data = {
        "renames": renames,
        "skipped": skipped,
        "dry_run": dry_run,
    }
    log_path.write_text(json.dumps(log_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rename images referenced in exo7 LaTeX exercises.")
    parser.add_argument(
        "--log",
        type=Path,
        default=REPO_ROOT / "rename_log.json",
        help="Path to the JSON file that will store rename operations.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate renames without touching files. Still writes the JSON log.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    if not EXO7_DIR.exists() or not IMAGES_DIR.exists():
        print(f"[ERROR] Expected directories not found: {EXO7_DIR} or {IMAGES_DIR}", file=sys.stderr)
        sys.exit(1)

    tex_files = collect_tex_files()
    if not tex_files:
        print("[INFO] No LaTeX files with images found.")
        return

    rename_images(tex_files, args.log, dry_run=args.dry_run)
    if args.dry_run:
        print(f"Dry run complete. Planned rename log stored in {args.log}")
    else:
        print(f"Renames applied. Log stored in {args.log}")


if __name__ == "__main__":
    main()
