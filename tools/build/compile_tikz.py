#!/usr/bin/env python3
"""Compile TikZ/PSTricks source files in content/images/exo7/tikz/ to PDF.

Detects the graphics engine from the source:
  - TikZ/PGF  → pdflatex (direct)
  - PSTricks  → latex → dvips -E → epstopdf → pdfcrop

Output PDFs land in content/images/exo7/pdf/ as {uuid}-{index}.pdf.
Existing PDFs are skipped unless --force is passed.

Usage:
    python tools/build/compile_tikz.py [--uuids u1 u2 ...] [--force] [--dry-run] [--log PATH]

Options:
    --uuids   UUID [...]   Only process these UUIDs (default: all with missing PDF)
    --all                  Process all TikZ sources, even those with existing PDF
    --force                Re-compile even if a PDF already exists
    --dry-run              Report what would be compiled without doing it
    --log     PATH         JSON report (default: logs/compile_tikz.json)
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
TIKZ_DIR = REPO_ROOT / "content" / "images" / "exo7" / "tikz"
PDF_DIR = REPO_ROOT / "content" / "images" / "exo7" / "pdf"

PSTRICKS_SIGNAL = re.compile(r"\\usepackage\{pstricks|\\begin\{pspicture", re.MULTILINE)


def detect_engine(src: Path) -> str:
    text = src.read_text(encoding="utf-8", errors="replace")
    return "pstricks" if PSTRICKS_SIGNAL.search(text) else "pdflatex"


def run(cmd: List[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=60
    )


def compile_pdflatex(src: Path, out_pdf: Path, tmpdir: Path) -> tuple[bool, str]:
    result = run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
         f"-output-directory={tmpdir}", str(src.resolve())],
        cwd=tmpdir,
    )
    tmp_pdf = tmpdir / (src.stem + ".pdf")
    if tmp_pdf.exists():
        # Crop whitespace
        crop_result = run(
            ["pdfcrop", str(tmp_pdf), str(tmp_pdf)],
            cwd=tmpdir,
        )
        shutil.copy2(tmp_pdf, out_pdf)
        return True, ""
    return False, result.stdout[-2000:] + result.stderr[-500:]


def compile_pstricks(src: Path, out_pdf: Path, tmpdir: Path) -> tuple[bool, str]:
    stem = src.stem

    # Step 1: latex → dvi
    r1 = run(["latex", "-interaction=nonstopmode", "-halt-on-error",
               f"-output-directory={tmpdir}", str(src.resolve())], cwd=tmpdir)
    dvi = tmpdir / (stem + ".dvi")
    if not dvi.exists():
        return False, r1.stdout[-2000:] + r1.stderr[-500:]

    # Step 2: dvips -E → eps (tight bounding box)
    eps = tmpdir / (stem + ".eps")
    r2 = run(["dvips", "-E", str(dvi), "-o", str(eps)], cwd=tmpdir)
    if not eps.exists():
        return False, r2.stdout[-2000:] + r2.stderr[-500:]

    # Step 3: epstopdf → pdf
    tmp_pdf = tmpdir / (stem + ".pdf")
    r3 = run(["epstopdf", str(eps), "--outfile", str(tmp_pdf)], cwd=tmpdir)
    if not tmp_pdf.exists():
        return False, r3.stdout[-2000:] + r3.stderr[-500:]

    shutil.copy2(tmp_pdf, out_pdf)
    return True, ""


def find_targets(force: bool, uuids: Optional[List[str]]) -> List[tuple[Path, Path]]:
    targets = []
    for src in sorted(TIKZ_DIR.glob("*-tikz-*.tex")):
        # {uuid}-tikz-{index}.tex → {uuid}-{index}.pdf
        parts = src.stem.split("-tikz-")
        if len(parts) != 2:
            continue
        uuid, idx = parts
        if uuids and uuid not in uuids:
            continue
        out_pdf = PDF_DIR / f"{uuid}-{idx}.pdf"
        if not force and out_pdf.exists():
            continue
        targets.append((src, out_pdf))
    return targets


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Compile TikZ/PSTricks sources to PDF.")
    parser.add_argument("--uuids", nargs="+", metavar="UUID",
                        help="Only process these UUIDs")
    parser.add_argument("--force", action="store_true",
                        help="Re-compile even if PDF already exists")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report without compiling")
    parser.add_argument("--log", type=Path,
                        default=REPO_ROOT / "logs" / "compile_tikz.json",
                        help="JSON report path")
    args = parser.parse_args(argv)

    targets = find_targets(force=args.force, uuids=args.uuids)

    if not targets:
        print("Rien à compiler.")
        return

    print(f"Sources à compiler : {len(targets)}")
    for src, _ in targets:
        engine = detect_engine(src)
        print(f"  {src.name}  [{engine}]")

    if args.dry_run:
        print("[DRY RUN] Aucune compilation effectuée.")
        return

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)

    done, failed = [], []

    for src, out_pdf in targets:
        engine = detect_engine(src)
        print(f"\nCompilation : {src.name}  [{engine}]")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            if engine == "pdflatex":
                ok, err = compile_pdflatex(src, out_pdf, tmp)
            else:
                ok, err = compile_pstricks(src, out_pdf, tmp)

        if ok:
            print(f"  ✓  → {out_pdf.name}")
            done.append({"source": src.name, "output": out_pdf.name, "engine": engine})
        else:
            print(f"  ✗  Échec")
            if err:
                print("    " + err[:300].replace("\n", "\n    "))
            failed.append({"source": src.name, "engine": engine, "error": err})

    log = {
        "summary": {"compiled": len(done), "failed": len(failed)},
        "compiled": done,
        "failed": failed,
    }
    args.log.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nCompilés : {len(done)}  |  Échecs : {len(failed)}")
    print(f"Log : {args.log}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
