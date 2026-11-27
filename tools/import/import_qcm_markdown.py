#!/usr/bin/env python3
"""Importe un document de QCM rédigé en markdown dans content/qcm/<source>/<lot>/.

    python3 tools/import/import_qcm_markdown.py CHEMIN/qcm.md            # simulation
    python3 tools/import/import_qcm_markdown.py CHEMIN/qcm.md --apply
    python3 tools/import/import_qcm_markdown.py CHEMIN/qcm.md --apply --prune

Le markdown est la source : on le modifie, puis on relance l'import. Le format
(commentaires `<!-- exobase: … -->`, options `- A.`, blocs `<details>` de
correction) est décrit dans content/qcm/FORMAT.md, section « Import depuis un
markdown ».

- Une question sans `uuid` en reçoit un, tiré dans l'espace commun aux
  exercices et aux qcm ; avec --apply, il est écrit dans le commentaire du
  markdown, ce qui garde l'identifiant stable si l'on renumérote.
- Un fichier du lot absent du markdown est signalé ; --prune le supprime.
- content/provenance/qcm-markdown.json consigne, par lot, le document source et
  le commit de son dépôt.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import secrets
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QCM_ROOT = ROOT / "content" / "qcm"
PROVENANCE = ROOT / "content" / "provenance" / "qcm-markdown.json"
BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

DOC_REQUIRED = ["source", "lot", "auteur", "organisation", "datecreate", "niveau", "module", "chapitre"]
HEADER_ORDER = ["uuid", "titre", "auteur", "organisation", "licence", "datecreate", "niveau", "module",
                "chapitre", "sousChapitre", "difficulte", "theme"]
SINGLE = "(*une seule réponse*)"

COMMENT_RE = re.compile(r"^<!--\s*exobase:(.*?)-->\s*$")
HEADING_RE = re.compile(r"^###\s+(\S+)\s+—\s+(.*)$")
SUB_RE = re.compile(r"^\*\*([^*]+?)\.\*\*\s*(.*)$")
OPTION_RE = re.compile(r"^- ([A-Z])\.\s+(.*)$")
ANSWER_RE = re.compile(r"^Réponses? justes? : \*\*([A-Z](?:\s*,\s*[A-Z])*)\*\*\s*([.,;:]?)\s*(.*)$")
MATH_RE = re.compile(r"(\$\$.*?\$\$|\$[^$]*\$)", re.S)


class FormatError(Exception):
    pass


@dataclass
class Question:
    label: str
    stem: str
    answers: list[tuple[bool, str]]
    explanation: str
    single: bool


@dataclass
class Item:
    label: str
    line: int
    meta: dict
    texte: str = ""
    questions: list[Question] = field(default_factory=list)


# ---------------------------------------------------------------- conversion du texte

def inline(text: str) -> str:
    """Markdown en ligne vers le texte LaTeX du format qcm (aucune mise en forme hors formules)."""
    parts = MATH_RE.split(text)
    for i in range(0, len(parts), 2):  # indices pairs : hors formules
        chunk = parts[i]
        chunk = re.sub(r"\*\*(.+?)\*\*", r"\1", chunk, flags=re.S)
        chunk = re.sub(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])", r"\1", chunk, flags=re.S)
        chunk = re.sub(r"(?<!\\)([%&#])", r"\\\1", chunk)
        parts[i] = chunk
    return "".join(parts)


def paragraphs(lines: list[str]) -> str:
    """Paragraphes séparés par une ligne vide ; chaque puce devient un paragraphe."""
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            if current:
                blocks.append(current)
                current = []
            continue
        if line.startswith("- "):
            if current:
                blocks.append(current)
            current = [line[2:]]
        else:
            current.append(line.strip())
    if current:
        blocks.append(current)
    return "\n\n".join(inline("\n".join(block)) for block in blocks)


def parse_meta(comment: str) -> dict:
    meta = {}
    for part in comment.split(";"):
        if not part.strip():
            continue
        if "=" not in part:
            raise FormatError(f"métadonnée sans « = » : {part.strip()!r}")
        key, value = part.split("=", 1)
        meta[key.strip()] = value.strip()
    return meta


# ---------------------------------------------------------------- lecture du markdown

def parse_question(label: str, lines: list[str], single: bool, where: str) -> Question:
    try:
        start = next(i for i, l in enumerate(lines) if l.strip().startswith("<details>"))
        end = next(i for i in range(start, len(lines)) if lines[i].strip() == "</details>")
    except StopIteration:
        raise FormatError(f"{where} : bloc <details> de correction absent ou non fermé")

    head, body = lines[:start], lines[start + 1:end]
    first_option = next((i for i, l in enumerate(head) if OPTION_RE.match(l)), None)
    if first_option is None:
        raise FormatError(f"{where} : aucune option « - A. … »")
    stem_lines = head[:first_option]
    answers_raw: list[tuple[str, str]] = []
    for line in head[first_option:]:
        match = OPTION_RE.match(line)
        if match:
            answers_raw.append((match.group(1), match.group(2).strip()))
        elif line.strip():
            if not line.startswith("  "):
                raise FormatError(f"{where} : ligne inattendue après les options : {line.strip()!r}")
            letter, text = answers_raw[-1]
            answers_raw[-1] = (letter, f"{text} {line.strip()}")
    letters = [letter for letter, _ in answers_raw]
    if letters != [chr(ord("A") + i) for i in range(len(letters))]:
        raise FormatError(f"{where} : options mal lettrées ({', '.join(letters)})")

    stem = "\n".join(stem_lines).strip()
    if SINGLE in stem:
        single = True
        stem = re.sub(r"\s*" + re.escape(SINGLE), "", stem)
    if not stem:
        raise FormatError(f"{where} : énoncé vide")

    body = [l for l in body if not l.strip().startswith("<summary")]
    while body and not body[0].strip():
        body.pop(0)
    match = ANSWER_RE.match(body[0].strip()) if body else None
    if not match:
        raise FormatError(f"{where} : la correction doit commencer par « Réponse(s) juste(s) : **…** »")
    good = {letter.strip() for letter in match.group(1).split(",")}
    unknown = good - set(letters)
    if unknown:
        raise FormatError(f"{where} : bonne(s) réponse(s) {', '.join(sorted(unknown))} sans option")
    if single and len(good) != 1:
        raise FormatError(f"{where} : marquée « une seule réponse » avec {len(good)} bonnes réponses")
    if match.group(2) not in {"", "."}:
        raise FormatError(f"{where} : terminer la ligne « Réponse(s) juste(s) : **…** » par un point "
                          "(la suite devient le début de la correction)")
    explanation = paragraphs([match.group(3)] + body[1:])

    answers = [(letter in good, inline(text)) for letter, text in answers_raw]
    return Question(label, inline(stem), answers, explanation, single)


def parse_document(path: Path) -> tuple[dict, list[Item], list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    doc_meta: dict | None = None
    items: list[Item] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        comment = COMMENT_RE.match(line.strip())
        if comment and doc_meta is None and not items:
            doc_meta = parse_meta(comment.group(1))
            i += 1
            continue
        heading = HEADING_RE.match(line)
        if not heading:
            i += 1
            continue
        j = i + 1
        while j < len(lines) and not lines[j].startswith("#"):
            j += 1
        items.append(parse_item(heading, lines, i, j))
        i = j
    if doc_meta is None:
        raise FormatError("commentaire <!-- exobase: … --> de document absent (avant la première question)")
    missing = [k for k in DOC_REQUIRED if not doc_meta.get(k)]
    if missing:
        raise FormatError(f"métadonnées de document manquantes : {', '.join(missing)}")
    return doc_meta, items, lines


def parse_item(heading: re.Match, lines: list[str], start: int, end: int) -> Item:
    label, heading_text = heading.group(1), heading.group(2)
    where = f"ligne {start + 1} ({label})"
    k = start + 1
    while k < end and not lines[k].strip():
        k += 1
    comment = COMMENT_RE.match(lines[k].strip()) if k < end else None
    if not comment:
        raise FormatError(f"{where} : commentaire <!-- exobase: … --> attendu sous le titre")
    meta = parse_meta(comment.group(1))
    meta["_comment_line"] = k
    if not meta.get("titre"):
        title = re.sub(r"\s*\([^)]*\)\s*$", "", heading_text).strip()
        if "$" in title:
            raise FormatError(f"{where} : titre avec formule ; donner titre=… dans le commentaire")
        meta["titre"] = title
    # Les métadonnées sont recopiées telles quelles dans \titre{…}, \theme{…} :
    # un « % » y ouvrirait un commentaire LaTeX (titre vide, contenu écarté par
    # OpenYourMath) ; « & » et « # » y sont aussi des caractères spéciaux.
    for key, value in meta.items():
        bad = re.search(r"[%&#]", value) if isinstance(value, str) else None
        if bad:
            raise FormatError(f"{where} : « {bad.group()} » interdit dans {key}=… ; le reformuler en toutes lettres")
    body = lines[k + 1:end]
    while body and body[-1].strip() in {"", "---"}:
        body.pop()

    item = Item(label, start + 1, meta)
    subs = [n for n, l in enumerate(body) if SUB_RE.match(l)]
    single_heading = SINGLE in heading_text
    if not subs:
        item.questions.append(parse_question(label, body, single_heading, where))
        return item

    item.texte = paragraphs(body[:subs[0]]).strip()
    for n, sub_start in enumerate(subs):
        sub_end = subs[n + 1] if n + 1 < len(subs) else len(body)
        match = SUB_RE.match(body[sub_start])
        segment = [match.group(2)] + body[sub_start + 1:sub_end]
        item.questions.append(parse_question(match.group(1), segment, False, f"{where}, {match.group(1)}"))
    return item


# ---------------------------------------------------------------- écriture

def render(meta: dict, item: Item) -> str:
    lines = []
    for key in HEADER_ORDER:
        if key in meta:
            lines.append(f"\\{key}{{{meta[key]}}}")
    if len(item.questions) > 1:
        lines.append("\\serie{ordonnee}")
    lines += ["", "\\contenu{"]
    if item.texte:
        lines += ["\\texte{", item.texte, "}", ""]
    for q in item.questions:
        lines.append("\\begin{question}")
        if q.single:
            lines.append("\\qtype{onlyone}")
        lines.append(q.stem)
        lines.append("\\begin{answers}")
        lines += [f"\\{'good' if good else 'bad'}{{{text}}}" for good, text in q.answers]
        lines.append("\\end{answers}")
        if q.explanation:
            lines += ["\\begin{explanations}", q.explanation, "\\end{explanations}"]
        lines += ["\\end{question}", ""]
    lines[-1] = "}"
    return "\n".join(lines) + "\n"


def git(path: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def source_provenance(path: Path) -> dict:
    top = git(path.parent, "rev-parse", "--show-toplevel")
    if not top:
        return {"fichier": str(path)}
    relative = str(path.resolve().relative_to(Path(top).resolve()))
    return {
        "depot": git(path.parent, "remote", "get-url", "origin") or top,
        "fichier": relative,
        "commit": git(path.parent, "rev-parse", "HEAD"),
        "modifie_hors_commit": bool(git(Path(top), "status", "--porcelain", "--", relative)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="document markdown de QCM")
    parser.add_argument("--apply", action="store_true", help="écrire (sinon simulation)")
    parser.add_argument("--prune", action="store_true", help="supprimer les fichiers du lot absents du markdown")
    args = parser.parse_args()

    source = args.source.resolve()
    try:
        doc_meta, items, md_lines = parse_document(source)
    except FormatError as error:
        print(f"{args.source}: {error}", file=sys.stderr)
        return 1

    target = QCM_ROOT / doc_meta["source"] / doc_meta["lot"]
    taken = {p.stem for p in (ROOT / "content").rglob("*.tex") if p.parent != target}
    seen: dict[str, str] = {}
    new_ids: list[tuple[Item, str]] = []
    for item in items:
        uuid = item.meta.get("uuid")
        if not uuid:
            while True:
                uuid = "".join(secrets.choice(BASE62) for _ in range(4))
                if uuid not in taken and uuid not in seen and not (target / f"{uuid}.tex").exists():
                    break
            item.meta["uuid"] = uuid
            new_ids.append((item, uuid))
        if not re.fullmatch(r"[0-9A-Za-z]{4}", uuid):
            print(f"{item.label} : uuid {uuid!r} invalide (4 caractères alphanumériques)", file=sys.stderr)
            return 1
        if uuid in seen:
            print(f"{item.label} : uuid {uuid} déjà porté par {seen[uuid]}", file=sys.stderr)
            return 1
        if uuid in taken:
            print(f"{item.label} : uuid {uuid} déjà pris hors du lot {doc_meta['source']}/{doc_meta['lot']}",
                  file=sys.stderr)
            return 1
        seen[uuid] = item.label

    report = {"add": [], "update": [], "same": []}
    outputs = {}
    for item in items:
        meta = {k: v for k, v in doc_meta.items() if k not in {"source", "lot"}}
        meta.update({k: v for k, v in item.meta.items() if not k.startswith("_")})
        text = render(meta, item)
        path = target / f"{meta['uuid']}.tex"
        outputs[path] = text
        if not path.exists():
            report["add"].append((item, path))
        elif path.read_text(encoding="utf-8") != text:
            report["update"].append((item, path))
        else:
            report["same"].append((item, path))
    orphans = sorted(p for p in target.glob("*.tex") if p not in outputs) if target.exists() else []

    rel = target.relative_to(ROOT)
    print(f"{args.source} → {rel}/ ({len(items)} contenus, "
          f"{sum(len(i.questions) for i in items)} questions)")
    for key, mark, title in (("add", "＋", "Ajouts"), ("update", "↻", "Mises à jour"), ("same", "=", "Inchangés")):
        if report[key]:
            print(f"{mark} {title} : {len(report[key])}")
            if key != "same":
                for item, path in report[key]:
                    print(f"    {item.label}\t{path.stem}\t{item.meta['titre']}")
    for item, uuid in new_ids:
        print(f"  uuid tiré pour {item.label} : {uuid}")
    for path in orphans:
        print(f"✗ {path.relative_to(ROOT)} absent du markdown" + (" : supprimé" if args.prune and args.apply else ""))

    if not args.apply:
        print("Simulation : relancer avec --apply pour écrire.")
        return 0

    target.mkdir(parents=True, exist_ok=True)
    for path, text in outputs.items():
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
    if args.prune:
        for path in orphans:
            path.unlink()

    if new_ids:
        for item, uuid in new_ids:
            k = item.meta["_comment_line"]
            md_lines[k] = re.sub(r"exobase:\s*", f"exobase: uuid={uuid}; ", md_lines[k], count=1)
        source.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
        print(f"uuid écrits dans {args.source}")

    # La provenance n'est réécrite que si le lot ou sa source ont changé :
    # relancer l'import sans modification ne touche à rien.
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8")) if PROVENANCE.exists() else {
        "type_de_contenu": "qcm",
        "format_source": "markdown (content/qcm/FORMAT.md, « Import depuis un markdown »)",
        "transformation": "tools/import/import_qcm_markdown.py",
        "lots": {},
    }
    key = f"{doc_meta['source']}/{doc_meta['lot']}"
    entry = {
        **source_provenance(source),
        "contenus": len(items),
        "questions": sum(len(i.questions) for i in items),
    }
    previous = {k: v for k, v in provenance["lots"].get(key, {}).items() if k != "importe_le"}
    changed = report["add"] or report["update"] or (args.prune and orphans)
    if changed or previous != entry:
        provenance["lots"][key] = {**entry, "importe_le": dt.date.today().isoformat()}
        PROVENANCE.write_text(json.dumps(provenance, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("Écrit. Contrôle : python3 tools/validate/check_qcm_sources.py " + str(rel))
    return 0


if __name__ == "__main__":
    sys.exit(main())
