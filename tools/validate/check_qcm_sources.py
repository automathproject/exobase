#!/usr/bin/env python3
"""Contrôle les contenus qcm de content/qcm/ (format : content/qcm/FORMAT.md).

    python3 tools/validate/check_qcm_sources.py
    python3 tools/validate/check_qcm_sources.py content/qcm/exo7/worms

Sort en code 1 dès qu'une erreur est trouvée.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QCM_ROOT = ROOT / "content" / "qcm"
REQUIRED = ["uuid", "titre", "auteur", "organisation", "datecreate", "niveau", "module", "chapitre"]
QTYPES = {"onetoall", "onlyone", "zerotoall", "truefalse"}
IMAGE_FORMATS = ["svg", "png", "jpg", "jpeg", "pdf"]


def strip_comments(text: str) -> str:
    return re.sub(r"(?m)(?<!\\)%.*$", "", text)


def braced(text: str, start: int) -> tuple[str, int]:
    depth, i = 0, start
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
        i += 1
    raise ValueError("accolade non fermée")


def parse_answers(block: str) -> list[tuple[bool, str]]:
    answers = []
    for match in re.finditer(r"\\(good|bad)\s*\{", block):
        value, _ = braced(block, match.end() - 1)
        answers.append((match.group(1) == "good", value.strip()))
    return answers


def check_file(path: Path, exercise_uuids: set[str], seen: dict[str, Path]) -> list[str]:
    errors: list[str] = []
    text = strip_comments(path.read_text(encoding="utf-8"))

    def meta(name: str) -> str | None:
        match = re.search(r"\\" + name + r"\{([^}]*)\}", text)
        return match.group(1).strip() if match else None

    for name in REQUIRED:
        if not meta(name):
            errors.append(f"métadonnée manquante ou vide : \\{name}{{}}")

    uuid = meta("uuid") or ""
    if uuid != path.stem:
        errors.append(f"\\uuid{{{uuid}}} ne correspond pas au nom du fichier")
    if uuid in exercise_uuids:
        errors.append(f"UUID {uuid} déjà porté par un exercice")
    if uuid in seen:
        errors.append(f"UUID {uuid} déjà porté par {seen[uuid].relative_to(ROOT)}")
    seen[uuid] = path

    difficulty = meta("difficulte")
    if difficulty and difficulty not in {"1", "2", "3"}:
        errors.append(f"\\difficulte{{{difficulty}}} hors de 1–3")

    start = re.search(r"\\contenu\s*\{", text)
    if not start:
        return errors + ["\\contenu{} absent"]
    try:
        content, _ = braced(text, start.end() - 1)
    except ValueError:
        return errors + ["\\contenu{} non fermé"]

    for env in ("question", "answers", "explanations"):
        opened = len(re.findall(r"\\begin\{" + env + r"\}", content))
        closed = len(re.findall(r"\\end\{" + env + r"\}", content))
        if opened != closed:
            errors.append(f"environnement {env} : {opened} ouvertures pour {closed} fermetures")

    questions = re.findall(r"\\begin\{question\}(.*?)\\end\{question\}", content, flags=re.S)
    if not questions:
        errors.append("aucune question")
    ordered = meta("serie") == "ordonnee"
    if ordered and len(questions) < 2:
        errors.append("\\serie{ordonnee} sur un contenu d'une seule question")
    if not ordered and len(questions) > 1:
        errors.append("plusieurs questions sans \\serie{ordonnee}")

    for rank, question in enumerate(questions, start=1):
        where = f"question {rank}"
        blocks = re.findall(r"\\begin\{answers\}(.*?)\\end\{answers\}", question, flags=re.S)
        if len(blocks) != 1:
            errors.append(f"{where} : {len(blocks)} blocs answers, un seul attendu")
            continue
        try:
            answers = parse_answers(blocks[0])
        except ValueError:
            errors.append(f"{where} : réponse non fermée")
            continue
        qtype_match = re.search(r"\\qtype\{([^}]*)\}", question)
        qtype = qtype_match.group(1).strip() if qtype_match else "onetoall"
        if qtype not in QTYPES:
            errors.append(f"{where} : \\qtype{{{qtype}}} non pris en charge")
        good = sum(1 for correct, _ in answers if correct)
        if len(answers) < 2:
            errors.append(f"{where} : moins de deux réponses")
        if any(not value for _, value in answers):
            errors.append(f"{where} : réponse vide")
        if good == 0 and qtype != "zerotoall":
            errors.append(f"{where} : aucune bonne réponse (ajouter \\qtype{{zerotoall}} si c'est voulu)")
        if qtype in {"onlyone", "truefalse"} and good != 1:
            errors.append(f"{where} : \\qtype{{{qtype}}} avec {good} bonnes réponses")
        stem = re.sub(r"\\q(tags|classification|type)\{[^}]*\}|\\q(keeporder|oneline|multicols|idontknow)\b", "",
                      question.split("\\begin{answers}")[0]).strip()
        if not stem:
            errors.append(f"{where} : énoncé vide")
        after = question.split("\\end{answers}")[1]
        after = re.sub(r"\\begin\{explanations\}.*?\\end\{explanations\}", "", after, flags=re.S)
        # Les espacements verticaux de la source sont sans effet hors du papier.
        after = re.sub(r"\\(vskip\s*[\d.]+\s*[a-z]{2}|vspace\*?\{[^}]*\}|(small|med|big)skip|noindent)", "", after)
        if after.strip():
            errors.append(f"{where} : texte après les réponses, hors explanations")

    source = path.relative_to(QCM_ROOT).parts[0]
    for match in re.finditer(r"\\(?:qimage|includegraphics)(?:\[[^\]]*\])?\{([^}]*)\}", content):
        name = Path(match.group(1).strip())
        candidates = [ROOT / "content" / "images" / source / fmt / f"{name.stem}.{fmt}" for fmt in IMAGE_FORMATS]
        if not any(c.exists() for c in candidates):
            errors.append(f"image introuvable : {match.group(1)}")

    return errors


def main() -> int:
    targets = [Path(a).resolve() for a in sys.argv[1:]] or [QCM_ROOT]
    files: list[Path] = []
    for target in targets:
        files.extend(sorted(target.rglob("*.tex")) if target.is_dir() else [target])

    exercise_uuids = {p.stem for p in (ROOT / "content" / "exercises").rglob("*.tex")}
    seen: dict[str, Path] = {}
    failures = 0
    questions = 0
    for path in files:
        errors = check_file(path, exercise_uuids, seen)
        questions += len(re.findall(r"\\begin\{question\}", strip_comments(path.read_text(encoding="utf-8"))))
        for error in errors:
            print(f"{path.relative_to(ROOT)}: {error}")
        failures += bool(errors)

    print(f"{len(files)} contenus qcm, {questions} questions, {failures} en erreur")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
