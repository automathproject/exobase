#!/usr/bin/env python3
"""Importe les QCM du dépôt qcm-exo7 dans content/qcm/exo7/.

Le dépôt source regroupe les questions par fichier thématique
(`questions-<lot>/questions-<chapitre>.tex`), au format du paquet exo7qcm.
L'import produit un fichier par *contenu qcm* :

- une question indépendante devient un fichier à une question ;
- une sous-section dont les questions partagent un énoncé commun devient une
  *série ordonnée* : un seul fichier, le contexte dans \\texte{}, les questions
  à la suite, dans l'ordre où elles doivent être jouées.

Le corps des questions reste du exo7qcm ; seules les métadonnées passent dans
l'en-tête exobase. Les règles de normalisation sont décrites dans
content/qcm/FORMAT.md et rappelées dans le manifeste de provenance.

Sans --apply, rien n'est écrit : le script affiche ce qu'il ferait.

    python3 tools/import/import_qcm_exo7.py
    python3 tools/import/import_qcm_exo7.py --apply
    python3 tools/import/import_qcm_exo7.py --source /chemin/vers/qcm-exo7 --apply
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT.parent / "qcm-exo7"
QCM_ROOT = ROOT / "content" / "qcm" / "exo7"
IMAGES_ROOT = ROOT / "content" / "images" / "exo7"
ID_MAP_PATH = ROOT / "sources" / "manifests" / "qcm-exo7-id-map.json"
PROVENANCE_PATH = ROOT / "content" / "provenance" / "qcm-exo7.json"
AUTHORS_PATH = ROOT / "content" / "authors.json"
REFERENTIAL_PATH = ROOT / "migrations" / "exo7" / "chapitres_complet.json"

ORGANISATION = "exo7"
LICENCE = "CC BY-NC-SA 4.0"
LICENCE_URL = "https://creativecommons.org/licenses/by-nc-sa/4.0/deed.fr"
DEFAULT_STEM = "Quelles sont les assertions vraies ?"

# Lots du dépôt source : dossier, niveau, auteurs par défaut (pseudos).
LOTS = {
    "lille-1": {"dir": "questions-lille-1", "niveau": "L1"},
    "lille-2": {"dir": "questions-lille-2", "niveau": "L1"},
    "hilisit": {"dir": "questions-hilisit", "niveau": "L1"},
    "worms": {"dir": "questions-probabilites-worms", "niveau": "L2", "auteurs": ["worms"]},
    "arnaud": {"dir": "questions-arnaud", "niveau": "L1", "auteurs": ["bodin"]},
}

# Auteurs des QCM : nom affiché dans \qcmauthor -> entrée de authors.json.
AUTHORS = {
    "Arnaud Bodin": {"pseudo": "bodin"},
    "Abdellah Hanani": {"pseudo": "hanani", "nom": "Hanani", "prenom": "Abdellah"},
    "Mohamed Mzari": {"pseudo": "mzari", "nom": "Mzari", "prenom": "Mohamed"},
    "Barnabé Croizat": {"pseudo": "croizat", "nom": "Croizat", "prenom": "Barnabé"},
    "Christine Sacré": {"pseudo": "sacre", "nom": "Sacré", "prenom": "Christine"},
    "Julien Worms": {"pseudo": "worms", "nom": "Worms", "prenom": "Julien"},
}
NEW_AUTHORS = [a for a in AUTHORS.values() if "nom" in a]

# Classification Exo7 des fichiers qui n'en portent pas dans leurs titres.
# Clé : « lot/chapitre » ; valeur : libellé de sous-section -> code, « * » par défaut.
CLASSIFICATION = {
    "lille-2/applications-lineaires": {"*": "107.01"},
    "lille-2/courbes": {"*": "244.01"},
    "lille-2/developpements-limites": {
        "Opérations sur les DL": "125.02",
        "Applications des DL": "125.03",
    },
    "lille-2/equations-differentielles": {
        "Equations du premier ordre": "225.01",
        "Equations du second ordre": "225.02",
    },
    "lille-2/espaces-vectoriels": {
        "Espaces vectoriels": "106.01",
        "Base et dimension": "106.04",
        "Espaces vectoriels supplémentaires": "106.03",
    },
    "lille-2/integrales": {"*": "127.99"},
    "lille-2/matrice-application": {"*": "108.03"},
    "lille-2/matrices": {"Calcul matriciel": "108.01", "Inverse d'une matrice": "108.05"},
    "lille-2/primitives": {"*": "127.11"},
    "lille-2/systemes": {"*": "200.03"},
    "hilisit/arithmetique": {
        "pgcd": "103.03",
        "Théorème de Bézout": "103.04",
        "Nombres premiers": "103.04",
        "Congruences": "103.99",
    },
    "hilisit/equations-differentielles": {"Primitive": "127.11", "*": "225.01"},
    "hilisit/logique": {"Logique": "100.01", "Ensembles": "100.02", "Raisonnements": "100.03"},
    "worms/worms": {
        "Probabilités, événements": "260.01",
        "Variables discrètes": "260.03",
        "Variables continues": "261.01",
    },
    "arnaud/arnaud": {"Logique": "100.99", "Arithmétique": "103.99", "Réels": "120.99"},
}

# Lot « arnaud » : la sous-section « Réels » mélange les chapitres d'analyse,
# le titre de la question tranche.
CLASSIFICATION_BY_TITLE = {
    "Réel et rationnels": "120.01",
    "Limites de suites": "121.01",
    "Suites définies par récurrence": "121.02",
    "Fonctions continues": "123.01",
    "Théorème des valeurs intermédiaires, fonctions bornées": "123.01",
    "Dérivation": "124.01",
    "Théorème de Rolle et des accroissements finis": "124.02",
    "Fonctions usuelles": "126.99",
    "Fonctions réciproques": "126.99",
}

MODULES = [
    (range(100, 120), "Algèbre"),
    (range(120, 140), "Analyse"),
    (range(140, 160), "Géométrie"),
    (range(200, 220), "Algèbre"),
    (range(220, 240), "Analyse"),
    (range(240, 260), "Géométrie"),
    (range(260, 280), "Probabilité et statistique"),
]

DIFFICULTY = {
    "Facile": 1, "Moyen": 2, "Difficile": 3,
    "Niveau 1": 1, "Niveau 2": 2, "Niveau 3": 3, "Niveau 4": 3,
}

# Titres des séries ordonnées (les sous-sections du lot Worms portent toutes le
# nom de leur section). Clé : clé source de la première question.
SERIES_TITLES = {
    "worms.worms.001": "Deux événements de probabilités données",
    "worms.worms.005": "Permis de conduire en deux tentatives",
    "worms.worms.010": "Tirage au sort de SMS",
    "worms.worms.014": "Deux dés à trois faces",
    "worms.worms.021": "Absences dans une équipe de basket",
    "worms.worms.025": "Pile ou face jusqu'au premier pile",
    "worms.worms.029": "Somme de deux dés",
    "worms.worms.034": "Loi sur trois valeurs à paramètre",
}

# Texte hors question qui n'est ni un contexte de série ni un préambule.
IGNORED_LOOSE = re.compile(
    r"Répondre en cochant|des assertions vraies \(et seulement celles-ci\)"
    r"|n'ont aucun rapport entre elles|indépendantes les unes des autres"
)

# Une réponse qui en désigne d'autres par leur position : l'ordre doit être gardé.
POSITIONAL_ANSWER = re.compile(
    r"ci-dessus|ci-dessous|précédent|aucune des (réponses|propositions|assertions)"
    r"|autres? (valeur|réponse)s?\b|d'autres valeurs",
    re.IGNORECASE,
)

# Corrections éditoriales : erreurs manifestes de la source, corrigées à
# l'import. Clé source -> liste de (texte attendu, remplacement, justification).
PATCHES = {
    "worms.worms.038": [
        (
            r"\bad{$f_2(x) = c' \, x^{24} \, \mathbb{I}_{[-100,100]}(x)$}",
            r"\good{$f_2(x) = c' \, x^{24} \, \mathbb{I}_{[-100,100]}(x)$}",
            "f_2 est une densité d'après l'explication de la source (« c' existe bien »).",
        ),
        (
            r"\bad{$f_4(x) = \frac {\pi}2 \sin(\pi x) \, \mathbb{I}_{[0,1]}(x)$}",
            r"\good{$f_4(x) = \frac {\pi}2 \sin(\pi x) \, \mathbb{I}_{[0,1]}(x)$}",
            "f_4 est une densité d'après l'explication de la source (« donc oui »).",
        ),
    ],
}

BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


@dataclass
class Question:
    key: str
    index: int  # rang dans le fichier source, à partir de 1
    title: str
    body: str  # contenu entre \begin{question} et \end{question}
    section: str
    subsection_raw: str
    label: str
    subsub: str
    difficulty: int | None
    codes: list[str]
    line: int


@dataclass
class Group:
    """Un contenu qcm : une question, ou une série ordonnée."""
    questions: list[Question]
    context: str = ""  # énoncé commun d'une série
    preamble: str = ""  # conventions de chapitre, répétées devant chaque contenu
    ordered: bool = False


@dataclass
class SourceFile:
    lot: str
    chapter: str
    path: Path
    authors: list[str] = field(default_factory=list)
    links: list[dict] = field(default_factory=list)
    groups: list[Group] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    created: str = ""


def strip_comment(line: str) -> str:
    return re.sub(r"(?<!\\)%.*$", "", line)


def read_braced(text: str, start: int) -> tuple[str, int]:
    """Contenu du groupe {…} ouvert en `start` et position qui suit sa fermeture."""
    assert text[start] == "{"
    depth = 0
    i = start
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


def parse_heading(raw: str) -> tuple[str, str | None, list[str]]:
    """« Logique | Facile | 100.01, 100.02 » -> (libellé, difficulté, codes)."""
    parts = [p.strip() for p in raw.split("|")]
    label = parts[0]
    level = None
    codes: list[str] = []
    for part in parts[1:]:
        if re.fullmatch(r"[\d.,\s]+", part):
            codes = [c.strip() for c in part.split(",") if c.strip()]
        else:
            level = re.sub(r"\s+", " ", part)
    return label, level, codes


def parse_source_file(lot: str, path: Path) -> SourceFile:
    chapter = path.stem.replace("questions-", "")
    src = SourceFile(lot=lot, chapter=chapter, path=path)
    lines = path.read_text(encoding="utf-8").split("\n")

    section = ""
    section_codes: list[str] = []
    sub_raw = ""
    label = ""
    level: str | None = None
    codes: list[str] = []
    subsub = ""
    in_subsection = False
    preamble: list[str] = []  # texte de niveau section
    context: list[str] = []  # texte de niveau sous-section, avant la 1re question
    current: Group | None = None  # série en cours
    index = 0
    i = 0

    def flush_series():
        nonlocal current
        if current and current.questions:
            src.groups.append(current)
        current = None

    while i < len(lines):
        raw = lines[i]
        line = strip_comment(raw).strip()
        if not line:
            i += 1
            continue

        m = re.match(r"\\(section|subsection|subsubsection)(\*?)\{", line)
        if m:
            title, _ = read_braced(line, m.end() - 1)
            kind, starred = m.group(1), m.group(2)
            if kind == "section" and starred and not section and "QCM" in title:
                i += 1  # titre de document, pas une section du contenu
                continue
            flush_series()
            context = []
            if kind == "section":
                section, _, section_codes = parse_heading(title)
                sub_raw, label, level, codes, subsub = "", "", None, [], ""
                in_subsection = False
                preamble = []
            elif kind == "subsection":
                sub_raw = title
                label, level, codes = parse_heading(title)
                subsub = ""
                in_subsection = True
            else:
                subsub = title.strip()
            i += 1
            continue

        m = re.match(r"\\qcmauthor\{", line)
        if m:
            names, _ = read_braced(line, m.end() - 1)
            src.authors = [n.strip() for n in names.split(",") if n.strip()]
            i += 1
            continue
        if line.startswith("\\qcmtitle"):
            i += 1
            continue
        m = re.match(r"\\qcmlink(?:\[(\w+)\])?\{", line)
        if m:
            url, pos = read_braced(line, m.end() - 1)
            text, _ = read_braced(line, pos)
            src.links.append({"type": m.group(1) or "link", "url": url, "titre": text})
            i += 1
            continue

        m = re.match(r"\\begin\{question\}(?:\[([^\]]*)\])?", line)
        if m:
            body_lines = [raw[raw.index("\\begin{question}") + len(m.group(0)):]]
            start_line = i + 1
            i += 1
            while "\\end{question}" not in strip_comment(lines[i]):
                body_lines.append(lines[i])
                i += 1
            body_lines.append(lines[i][:lines[i].index("\\end{question}")])
            i += 1
            index += 1
            question = Question(
                key=f"{lot}.{chapter}.{index:03d}",
                index=index,
                title=(m.group(1) or "").strip(),
                body="\n".join(body_lines),
                section=section,
                subsection_raw=sub_raw,
                label=label or section,
                subsub=subsub,
                difficulty=DIFFICULTY.get(level) if level else None,
                codes=list(codes or section_codes),
                line=start_line,
            )
            if current is None and context:
                current = Group(questions=[], context="\n".join(context).strip(), ordered=True)
                context = []
            if current is not None:
                current.questions.append(question)
            else:
                src.groups.append(Group(questions=[question], preamble="\n".join(preamble).strip()))
            continue

        # Texte hors question : contexte de série, préambule de chapitre, ou rebut.
        if IGNORED_LOOSE.search(line):
            i += 1
            continue
        if in_subsection and current is None:
            context.append(raw.rstrip())
        elif not in_subsection and section:
            preamble.append(re.sub(r"^\\noindent\s*", "", raw.strip()))
        else:
            src.dropped.append(f"{path.name}:{i + 1}: {line}")
        i += 1

    flush_series()
    if context:
        src.dropped.extend(f"{path.name}: {l}" for l in context)
    return src


def git(source: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(source), *args], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def short_uuid(key: str, taken: set[str]) -> str:
    """UUID court à 4 caractères, dérivé de la clé source donc reproductible."""
    attempt = 0
    while True:
        digest = hashlib.sha256(f"qcm-exo7:{key}:{attempt}".encode()).digest()
        value = int.from_bytes(digest[:8], "big")
        uuid = ""
        for _ in range(4):
            value, rem = divmod(value, 62)
            uuid += BASE62[rem]
        if uuid not in taken:
            return uuid
        attempt += 1


def existing_uuids() -> set[str]:
    """UUID déjà pris par les exercices : un qcm ne doit jamais en réutiliser un."""
    return {p.stem for p in (ROOT / "content" / "exercises").rglob("*.tex")}


def load_referential() -> dict:
    chapters = json.loads(REFERENTIAL_PATH.read_text(encoding="utf-8"))
    by_code = {}
    for chapter in chapters:
        by_code[str(chapter["id"])] = {"chapitre": chapter["titre"], "sousChapitre": ""}
        for sub in chapter["sousChapitres"]:
            by_code[sub["code"]] = {"chapitre": chapter["titre"], "sousChapitre": sub["description"]}
    return by_code


def module_for(code: str) -> str:
    chapter = int(code.split(".")[0])
    for span, module in MODULES:
        if chapter in span:
            return module
    raise ValueError(f"module inconnu pour le code {code}")


def classify(src: SourceFile, question: Question, referential: dict) -> tuple[list[str], dict]:
    codes = question.codes
    if not codes:
        table = CLASSIFICATION.get(f"{src.lot}/{src.chapter}")
        if table is None:
            raise ValueError(f"aucune classification pour {src.lot}/{src.chapter}")
        key = question.label if src.lot != "worms" else question.section
        code = CLASSIFICATION_BY_TITLE.get(question.title) or table.get(key) or table.get("*")
        if code is None:
            raise ValueError(f"{question.key} : sous-section « {key} » sans classification")
        codes = [code]
    first = codes[0]
    entry = referential.get(first)
    if entry is None:  # ex. 124.00 : le chapitre existe, pas ce sous-code
        chapter_entry = referential.get(first.split(".")[0])
        if chapter_entry is None:
            raise ValueError(f"{question.key} : code Exo7 inconnu {first}")
        entry = {"chapitre": chapter_entry["chapitre"], "sousChapitre": "Autre"}
    return codes, {**entry, "module": module_for(first)}


def capitalize(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def keywords_of(body: str) -> list[str]:
    words: list[str] = []
    for match in re.finditer(r"\\qtags\{([^}]*)\}", body):
        for tag in match.group(1).split(","):
            name, _, value = tag.partition("=")
            if name.strip() == "motcle":
                words.extend(w.strip() for w in value.split("/") if w.strip())
    return words


def title_of(question: Question) -> str:
    if question.title:
        return question.title
    match = re.search(r"\\qtags\{[^}]*motcle=([^,}]*)", question.body)
    if match and match.group(1).strip():
        return capitalize(match.group(1).strip())
    return capitalize(question.subsub or question.label)


def answers_block(body: str) -> str:
    match = re.search(r"\\begin\{answers\}(.*?)\\end\{answers\}", body, flags=re.S)
    return "\n".join(strip_comment(l) for l in match.group(1).split("\n")) if match else ""


def normalize_body(question: Question, uuid: str, codes: list[str], image_counter: list[int],
                   images: list[dict], src: SourceFile, notes: dict) -> str:
    body = question.body

    for expected, replacement, reason in PATCHES.get(question.key, []):
        if expected not in body:
            raise ValueError(f"{question.key} : correction inapplicable, texte introuvable : {expected}")
        body = body.replace(expected, replacement)
        notes["corrections"].append({"source": question.key, "uuid": uuid, "motif": reason})

    lines = [l.rstrip() for l in body.split("\n")]
    # Les mots-clés passent dans \theme{} ; \qtags reste dans la question, comme
    # dans la source, pour les outils exo7qcm.
    flags = [l.strip() for l in lines if re.fullmatch(r"\s*\\q(tags|keeporder|oneline|multicols|idontknow|type)\b.*", l)]
    rest = [l for l in lines if l.strip() not in flags or not l.strip()]
    text = "\n".join(rest).strip("\n")
    text = re.sub(r"\n{3,}", "\n\n", text)

    answers = answers_block(text)
    if "\\qkeeporder" not in flags and POSITIONAL_ANSWER.search(answers):
        flags.append("\\qkeeporder")
        notes["keeporder"].append(question.key)
    if "\\good" not in answers and not any(f.startswith("\\qtype") for f in flags):
        flags.append("\\qtype{zerotoall}")
        notes["zerotoall"].append(question.key)

    stem = strip_comment(text.split("\\begin{answers}")[0]).strip()
    if not stem:
        text = DEFAULT_STEM + "\n" + text.lstrip("\n")
        notes["default_stem"].append(question.key)

    def replace_image(match: re.Match) -> str:
        options, name = match.group(1) or "", match.group(2).strip()
        source_image = next(
            (p for ext in ("png", "jpg", "jpeg", "pdf", "svg")
             for p in [src.path.parent / f"{Path(name).stem}.{ext}"] if p.exists()),
            None,
        )
        if source_image is None:
            raise ValueError(f"{question.key} : image introuvable « {name} »")
        image_counter[0] += 1
        ext = source_image.suffix.lstrip(".").lower()
        target = f"{uuid}-{image_counter[0]}.{ext}"
        images.append({"from": source_image, "to": IMAGES_ROOT / ext / target})
        tikz = source_image.with_suffix(".tikz")
        if tikz.exists():
            images.append({"from": tikz, "to": IMAGES_ROOT / "tikz" / f"{uuid}-tikz-{image_counter[0]}.tex"})
        return f"\\qimage{options}{{images/{ext}/{target}}}"

    text = re.sub(r"(?m)^(?!\s*%)(.*?)\\qimage(\[[^\]]*\])?\{([^}]*)\}",
                  lambda m: m.group(1) + replace_image(re.match(r"\\qimage(\[[^\]]*\])?\{([^}]*)\}", m.group(0)[len(m.group(1)):])),
                  text)

    header = [f"\\qclassification{{{','.join(codes)}}}"] + flags
    return "\\begin{question}\n" + "\n".join(header) + "\n" + text.strip("\n") + "\n\\end{question}"


def render(group: Group, src: SourceFile, uuid: str, referential: dict, notes: dict,
           images: list[dict]) -> tuple[str, dict]:
    first = group.questions[0]
    codes, meta = classify(src, first, referential)
    names = src.authors or []
    pseudos = [AUTHORS[n]["pseudo"] for n in names] if names else LOTS[src.lot]["auteurs"]

    themes: list[str] = []
    for question in group.questions:
        for word in [question.label if question.label != meta["chapitre"] else "", *keywords_of(question.body)]:
            word = re.sub(r"\s+", " ", word).strip()
            if word and "$" not in word and word.lower() not in [t.lower() for t in themes]:
                themes.append(word)

    title = SERIES_TITLES.get(first.key) if group.ordered else title_of(first)
    if not title:
        raise ValueError(f"{first.key} : série sans titre, compléter SERIES_TITLES")
    if "$" in title:  # pas de formule dans un titre
        title = capitalize(first.label if "$" not in first.label else meta["sousChapitre"] or meta["chapitre"])

    difficulties = {q.difficulty for q in group.questions}
    difficulty = first.difficulty if len(difficulties) == 1 else None

    image_counter = [0]
    blocks = []
    for question in group.questions:
        q_codes, _ = classify(src, question, referential)
        blocks.append(normalize_body(question, uuid, q_codes, image_counter, images, src, notes))

    head = [
        f"\\uuid{{{uuid}}}",
        f"\\titre{{{title}}}",
        f"\\auteur{{{' ; '.join(pseudos)}}}",
        f"\\organisation{{{ORGANISATION}}}",
        f"\\licence{{{LICENCE}}}",
        f"\\datecreate{{{src.created}}}",
        f"\\niveau{{{LOTS[src.lot]['niveau']}}}",
        f"\\module{{{meta['module']}}}",
        f"\\chapitre{{{meta['chapitre']}}}",
        f"\\sousChapitre{{{meta['sousChapitre']}}}",
        f"\\difficulte{{{difficulty or ''}}}",
        f"\\theme{{{', '.join(themes)}}}",
        f"\\exo7qcmid{{{first.key}}}",
    ]
    if group.ordered:
        head.append("\\serie{ordonnee}")

    body = []
    shared = group.context or group.preamble
    if shared:
        body.append("\\texte{\n" + shared.strip() + "\n}")
    body.extend(blocks)
    content = "\n".join(head) + "\n\n\\contenu{\n" + "\n\n".join(body) + "\n}\n"

    record = {
        "uuid": uuid,
        "source": f"{LOTS[src.lot]['dir']}/{src.path.name}",
        "questions": [q.index for q in group.questions],
        "ligne": first.line,
        "sous_section": first.subsection_raw or first.section,
        "serie": group.ordered,
    }
    return content, record


def update_authors(apply: bool) -> list[str]:
    authors = json.loads(AUTHORS_PATH.read_text(encoding="utf-8"))
    known = {a.get("pseudo") for a in authors}
    added = []
    for author in NEW_AUTHORS:
        if author["pseudo"] in known:
            continue
        authors.append({
            "pseudo": author["pseudo"],
            "nom": author["nom"],
            "prenom": author["prenom"],
            "email": None,
            "license_code": LICENCE,
            "license_url": LICENCE_URL,
        })
        added.append(author["pseudo"])
    if added and apply:
        # Ajout en fin de fichier, sans réécrire les entrées existantes.
        text = AUTHORS_PATH.read_text(encoding="utf-8").rstrip()
        entries = json.dumps(authors[-len(added):], ensure_ascii=False, indent=2)
        inner = "\n".join("  " + line for line in entries.split("\n")[1:-1])
        AUTHORS_PATH.write_text(text[:text.rindex("]")].rstrip() + ",\n" + inner + "\n]\n", encoding="utf-8")
    return added


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="clone de qcm-exo7")
    parser.add_argument("--apply", action="store_true", help="écrire les fichiers")
    args = parser.parse_args()

    source: Path = args.source.resolve()
    if not (source / "exo7qcm.sty").exists():
        print(f"Dépôt qcm-exo7 introuvable : {source}", file=sys.stderr)
        return 2

    referential = load_referential()
    id_map = json.loads(ID_MAP_PATH.read_text(encoding="utf-8")) if ID_MAP_PATH.exists() else {}
    previous = {key: entry["uuid"] for key, entry in id_map.get("contenus", {}).items()}
    taken = existing_uuids() | set(previous.values())

    notes = {"corrections": [], "keeporder": [], "zerotoall": [], "default_stem": []}
    files: dict[Path, str] = {}
    images: list[dict] = []
    records: dict[str, dict] = {}
    lots_report = {}
    dropped: list[str] = []
    counts = {"contenus": 0, "questions": 0, "series": 0}

    for lot, config in LOTS.items():
        lot_report = {"dossier": config["dir"], "niveau": config["niveau"], "fichiers": []}
        for path in sorted((source / config["dir"]).glob("questions-*.tex")):
            src = parse_source_file(lot, path)
            src.created = git(source, "log", "--diff-filter=A", "--format=%as", "--", str(path.relative_to(source))).split("\n")[-1]
            dropped.extend(src.dropped)
            for group in src.groups:
                key = group.questions[0].key
                uuid = previous.get(key)
                if uuid is None:
                    uuid = short_uuid(key, taken)
                    taken.add(uuid)
                content, record = render(group, src, uuid, referential, notes, images)
                files[QCM_ROOT / lot / f"{uuid}.tex"] = content
                records[key] = record
                counts["contenus"] += 1
                counts["questions"] += len(group.questions)
                counts["series"] += group.ordered
            lot_report["fichiers"].append({
                "fichier": path.name,
                "auteurs": src.authors or [next(n for n, a in AUTHORS.items() if a["pseudo"] == p) for p in config["auteurs"]],
                "contenus": len(src.groups),
                "questions": sum(len(g.questions) for g in src.groups),
                "liens": src.links,
            })
        lots_report[lot] = lot_report

    stale = sorted(set(p for p in QCM_ROOT.rglob("*.tex")) - set(files)) if QCM_ROOT.exists() else []
    changed = [p for p, content in files.items() if not p.exists() or p.read_text(encoding="utf-8") != content]
    new_authors = update_authors(args.apply)

    print(f"Source : {source} ({git(source, 'rev-parse', '--short', 'HEAD')})")
    print(f"Contenus qcm : {counts['contenus']} ({counts['questions']} questions, dont {counts['series']} séries ordonnées)")
    print(f"Fichiers à écrire : {len(changed)} ; inchangés : {len(files) - len(changed)} ; images : {len(images)}")
    print(f"Ordre des réponses figé (\\qkeeporder ajouté) : {len(notes['keeporder'])}")
    print(f"Énoncé par défaut ajouté : {len(notes['default_stem'])}")
    print(f"Questions sans bonne réponse (\\qtype{{zerotoall}}) : {len(notes['zerotoall'])} {notes['zerotoall']}")
    for correction in notes["corrections"]:
        print(f"Correction éditoriale {correction['source']} : {correction['motif']}")
    for line in dropped:
        print(f"Texte hors question écarté : {line}")
    for path in stale:
        print(f"Présent dans exobase mais plus produit par l'import (laissé en place) : {path.relative_to(ROOT)}")
    if new_authors:
        print(f"Auteurs ajoutés à authors.json : {', '.join(new_authors)}")

    if not args.apply:
        print("\nSimulation : relancer avec --apply pour écrire.")
        return 0

    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    for image in images:
        image["to"].parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(image["from"], image["to"])

    commit = git(source, "rev-parse", "HEAD")
    ID_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    ID_MAP_PATH.write_text(json.dumps({
        "description": "Correspondance entre les questions de qcm-exo7 et les contenus qcm d'exobase. "
                       "La clé est <lot>.<chapitre>.<rang de la première question dans le fichier source> ; "
                       "elle fait autorité sur l'UUID lors d'un nouvel import.",
        "contenus": records,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    PROVENANCE_PATH.write_text(json.dumps({
        "source": "QCM Exo7",
        "url": "https://github.com/exo7math/qcm-exo7",
        "commit": commit,
        "licence": LICENCE,
        "licence_url": LICENCE_URL,
        "format_source": "exo7qcm (LaTeX)",
        "type_de_contenu": "qcm",
        "destination": "content/qcm/exo7/<lot>/<uuid>.tex",
        "transformation": "tools/import/import_qcm_exo7.py",
        "contenus": counts["contenus"],
        "questions": counts["questions"],
        "series_ordonnees": counts["series"],
        "manifeste_detaille": "sources/manifests/qcm-exo7-id-map.json",
        "normalisation": {
            "series": "Une sous-section dont les questions suivent un énoncé commun devient un seul contenu, marqué \\serie{ordonnee}.",
            "preambule": "Les conventions posées en tête de chapitre sont répétées dans \\texte{} devant chaque question concernée.",
            "difficulte": "Facile/Moyen/Difficile -> 1/2/3 ; Niveau 1/2/3/4 -> 1/2/3/3 (le libellé d'origine reste dans le manifeste détaillé).",
            "classification": "Codes Exo7 de la source quand ils existent, sinon attribués par la table CLASSIFICATION de l'outil.",
            "ordre_des_reponses": "\\qkeeporder ajouté quand une réponse en désigne d'autres par leur position.",
            "enonce_par_defaut": f"« {DEFAULT_STEM} » ajouté aux questions sans énoncé.",
        },
        "corrections_editoriales": notes["corrections"],
        "qkeeporder_ajoute": notes["keeporder"],
        "enonce_par_defaut_ajoute": notes["default_stem"],
        "sans_bonne_reponse": notes["zerotoall"],
        "texte_ecarte": dropped,
        "lots": lots_report,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\nÉcrit : {len(changed)} fichiers, {len(images)} images, manifestes mis à jour.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
