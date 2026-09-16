#!/usr/bin/env python3
"""Validate AMSCC metadata against the synced taxonomy and its legacy aliases."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXERCISES = ROOT / "content/exercises/amscc"
DEFAULT_REFERENCE = ROOT / "content/referentials/amscc/referentiel.md"
DEFAULT_ALIASES = ROOT / "content/referentials/amscc-aliases.json"
DEFAULT_COMPATIBILITY = ROOT / "content/referentials/amscc-exo7-compatibility.json"
DEFAULT_EXO7 = ROOT / "migrations/exo7/chapitres_complet.json"
FIELDS = ("module", "chapitre", "sousChapitre")


def tex_value(text: str, field: str) -> str:
    """Read a braced TeX command, including values containing nested braces."""
    match = re.search(rf"\\{field}\s*\{{", text)
    if not match:
        return ""
    depth, index, value = 1, match.end(), []
    while index < len(text) and depth:
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        if depth:
            value.append(char)
        index += 1
    return "".join(value).strip()


def canonical_triplets(reference: Path) -> set[tuple[str, str, str]]:
    module = chapter = None
    triplets: set[tuple[str, str, str]] = set()
    for line in reference.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            module, chapter = line[3:].strip(), None
        elif line.startswith("### "):
            chapter = line[4:].strip()
        elif line.startswith("- ") and module and chapter:
            triplets.add((module, chapter, line[2:].strip()))
    return triplets


def load_aliases(path: Path, canonical: set[tuple[str, str, str]]):
    data = json.loads(path.read_text(encoding="utf-8"))
    aliases: dict[tuple[str, str, str], dict] = {}
    errors = []
    for entry in data.get("aliases", []):
        source = tuple(entry.get("source", []))
        target = tuple(entry.get("target", []))
        if len(source) != 3 or len(target) != 3:
            errors.append(f"alias mal formé : {entry}")
            continue
        if source in aliases:
            errors.append(f"alias dupliqué : {source}")
        aliases[source] = entry
        candidates = [target, *(tuple(value) for value in entry.get("overrides", {}).values())]
        for candidate in candidates:
            if candidate not in canonical:
                errors.append(f"cible absente du référentiel : {candidate} (source {source})")
    return aliases, errors


def validate_compatibility(path: Path, canonical: set[tuple[str, str, str]], exo7_path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    catalog = json.loads(exo7_path.read_text(encoding="utf-8"))
    chapters = {entry["id"]: {item["code"] for item in entry["sousChapitres"]} for entry in catalog}
    expected_chapters = {(module, chapter) for module, chapter, _ in canonical}
    projected: set[tuple[str, str]] = set()
    errors = []
    for projection in data.get("projections", []):
        amscc = tuple(projection.get("amscc", []))
        if len(amscc) != 2 or amscc not in expected_chapters:
            errors.append(f"projection AMSCC absente du référentiel : {amscc}")
            continue
        if amscc in projected:
            errors.append(f"projection AMSCC dupliquée : {amscc}")
        projected.add(amscc)
        exo7 = projection.get("exo7")
        if exo7 is None:
            if not projection.get("reason"):
                errors.append(f"projection sans code ni justification : {amscc}")
            continue
        chapter = exo7.get("chapter")
        if chapter not in chapters:
            errors.append(f"chapitre Exo7 introuvable {chapter} pour {amscc}")
            continue
        for name, code in exo7.get("subchapters", {}).items():
            if code not in chapters[chapter]:
                errors.append(f"code Exo7 introuvable {code} pour {amscc} / {name}")
    missing = expected_chapters - projected
    if missing:
        errors.append("chapitres AMSCC sans décision Exo7 : " + ", ".join(f"{m} / {c}" for m, c in sorted(missing)))
    return errors


def resolve(raw, uuid, canonical, aliases):
    if raw in canonical:
        return raw, "canonical"
    alias = aliases.get(raw)
    if not alias:
        return None, "unresolved"
    return tuple(alias.get("overrides", {}).get(uuid, alias["target"])), "alias"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exercises", nargs="?", type=Path, default=DEFAULT_EXERCISES)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--aliases", type=Path, default=DEFAULT_ALIASES)
    parser.add_argument("--compatibility", type=Path, default=DEFAULT_COMPATIBILITY)
    parser.add_argument("--exo7", type=Path, default=DEFAULT_EXO7)
    parser.add_argument("--max-errors", type=int, default=20)
    args = parser.parse_args()

    canonical = canonical_triplets(args.reference)
    aliases, errors = load_aliases(args.aliases, canonical)
    errors.extend(validate_compatibility(args.compatibility, canonical, args.exo7))
    counts = Counter()
    unresolved = []
    for tex_path in sorted(args.exercises.glob("*.tex")):
        text = tex_path.read_text(encoding="utf-8")
        uuid = tex_value(text, "uuid") or tex_path.stem
        raw = tuple(tex_value(text, field) for field in FIELDS)
        target, state = resolve(raw, uuid, canonical, aliases)
        counts[state] += 1
        if state == "unresolved":
            unresolved.append((uuid, raw))
        elif target not in canonical:
            errors.append(f"{uuid}: cible résolue absente du référentiel : {target}")

    print(f"Référentiel AMSCC : {len(canonical)} triplets canoniques")
    print(f"Exercices : {counts['canonical']} canoniques, {counts['alias']} via alias, {counts['unresolved']} non résolus")
    for uuid, raw in unresolved[: args.max_errors]:
        errors.append(f"{uuid}: métadonnées hors référentiel : {' / '.join(raw)}")
    if errors:
        print("\nErreurs :", file=sys.stderr)
        for error in errors[: args.max_errors]:
            print(f"  - {error}", file=sys.stderr)
        if len(errors) > args.max_errors:
            print(f"  … {len(errors) - args.max_errors} erreur(s) supplémentaire(s)", file=sys.stderr)
        return 1
    print("✅ Toute métadonnée AMSCC est canonique ou couverte par un alias ; la projection Exo7 est complète.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
