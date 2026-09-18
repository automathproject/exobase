#!/usr/bin/env python3
"""Render and verify the human-readable Exo7 referential."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "migrations/exo7/chapitres_complet.json"
DEFAULT_OUTPUT = ROOT / "content/referentials/exo7/referentiel.md"


def render(catalog: list[dict]) -> str:
    chapter_count = len(catalog)
    subchapter_count = sum(len(chapter["sousChapitres"]) for chapter in catalog)
    lines = [
        "# Référentiel Exo7",
        "",
        "Codes canoniques de la classification Exo7. Chaque chapitre est identifié par "
        "son code entier et chaque sous-chapitre par son code décimal.",
        "",
        "Ce document est généré depuis `migrations/exo7/chapitres_complet.json` par "
        "`python3 tools/render_exo7_referential.py`. Ne pas le modifier à la main.",
        "",
        f"Il recense {chapter_count} chapitres et {subchapter_count} sous-chapitres.",
        "",
        "---",
        "",
        "## Chapitres et sous-chapitres",
        "",
    ]
    for chapter in catalog:
        lines.append(f"### `{chapter['id']}` — {chapter['titre']}")
        for subchapter in chapter["sousChapitres"]:
            lines.append(f"- `{subchapter['code']}` — {subchapter['description']}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when the rendered referential differs from the versioned file",
    )
    args = parser.parse_args()

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    rendered = render(catalog)
    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
        if current != rendered:
            print(
                f"Référentiel Exo7 désynchronisé : régénérez {args.output.relative_to(ROOT)} "
                "avec python3 tools/render_exo7_referential.py.",
                file=sys.stderr,
            )
            return 1
        print("✅ Référentiel Exo7 synchronisé.")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"Référentiel Exo7 généré : {args.output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
