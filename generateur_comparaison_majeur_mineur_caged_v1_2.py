#!/usr/bin/env python3
"""
Générateur de comparaison majeur / mineur par forme CAGED.

Objectif : comparer, sur la même fondamentale et la même forme CAGED :
- pentatonique majeure
- gamme majeure
- pentatonique mineure
- gamme mineure naturelle

La sortie est un SVG A4 paysage autonome, sans dépendance externe.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata
import xml.sax.saxutils as xml_escape

VERSION = "1.2.0"
SCRIPT_NAME = "generateur_comparaison_majeur_mineur_caged_v1_2.py"

# Page A4 paysage en unités SVG
PAGE_W = 1754
PAGE_H = 1240
MARGIN = 62

# Guitare
STRINGS = ("E", "A", "D", "G", "B", "E")  # interne : corde 6 -> corde 1
TUNING_PCS = (4, 9, 2, 7, 11, 4)
SHAPES = ("C", "A", "G", "E", "D")
FIRST_FRET = 0
LAST_FRET = 15
CAGED_OPEN_ROOTS = {"C": 0, "A": 9, "G": 7, "E": 4, "D": 2}

NATURAL_PITCHES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
LETTER_ORDER = ("C", "D", "E", "F", "G", "A", "B")

MAJOR_SCALE = ((0, "1"), (2, "2"), (4, "3"), (5, "4"), (7, "5"), (9, "6"), (11, "7"))
MINOR_SCALE = ((0, "1"), (2, "2"), (3, "b3"), (5, "4"), (7, "5"), (8, "b6"), (10, "b7"))
MAJOR_PENTA = ((0, "1"), (2, "2"), (4, "3"), (7, "5"), (9, "6"))
MINOR_PENTA = ((0, "1"), (3, "b3"), (5, "4"), (7, "5"), (10, "b7"))

# Couleurs sobres, cohérentes avec les autres générateurs
ROOT_COLOR = "rgb(255,145,145)"
THIRD_COLOR = "rgb(255,212,125)"
FIFTH_COLOR = "rgb(150,202,255)"
COMMON_COLOR = "rgb(230,238,230)"
MAJOR_COLOR = "rgb(232,242,255)"
MINOR_COLOR = "rgb(245,235,252)"
PENTA_STROKE = "rgb(34,83,155)"
CHORD_STROKE = "rgb(108,55,170)"
GRID = "rgb(55,55,55)"
MUTED = "rgb(95,95,95)"
TEXT = "rgb(30,30,30)"

CHORD_TEMPLATES = {
    "majeur": {
        "C": (None, 3, 2, 0, 1, 0),
        "A": (None, 0, 2, 2, 2, 0),
        "G": (3, 2, 0, 0, 0, 3),
        "E": (0, 2, 2, 1, 0, 0),
        "D": (None, None, 0, 2, 3, 2),
    },
    "mineur": {
        "C": (None, 3, 1, 0, 1, None),
        "A": (None, 0, 2, 2, 1, 0),
        "G": (3, 1, 0, 0, 3, 3),
        "E": (0, 2, 2, 0, 0, 0),
        "D": (None, None, 0, 2, 3, 1),
    },
}

@dataclass(frozen=True)
class Spot:
    string_index: int
    fret: int
    degree: str
    note: str
    chord: bool = False
    penta: bool = False


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def pitch_class(note: str) -> int:
    letter = note[0].upper()
    if letter not in NATURAL_PITCHES:
        raise ValueError(f"Note invalide : {note}")
    accidental = note[1:]
    return (NATURAL_PITCHES[letter] + accidental.count("#") - accidental.count("b")) % 12


def normalize_root(value: str) -> tuple[str, int]:
    cleaned = value.strip().replace("♯", "#").replace("♭", "b").replace(" ", "")
    if not cleaned:
        raise ValueError("Aucune tonalité saisie.")
    low = strip_accents(cleaned).lower()
    m = re.fullmatch(r"(do|re|mi|fa|sol|la|si)([#b]{0,3})", low)
    if m:
        name, acc = m.groups()
        letter = {"do": "C", "re": "D", "mi": "E", "fa": "F", "sol": "G", "la": "A", "si": "B"}[name]
        root = letter + acc
    else:
        m = re.fullmatch(r"([a-g])([#b]{0,3})", low)
        if not m:
            raise ValueError("Tonalité invalide. Exemples : A, F#, Bb, Ré, Sib.")
        letter, acc = m.groups()
        root = letter.upper() + acc
    return root, pitch_class(root)


def normalize_shape(value: str) -> str:
    cleaned = strip_accents(value.strip()).upper()
    if cleaned in SHAPES:
        return cleaned
    if cleaned in {"", "T", "TOUT", "TOUS", "TOUTES", "ALL", "*"}:
        return "toutes"
    raise ValueError("Forme invalide. Utilise C, A, G, E, D ou T pour toutes.")


def accidental_for_delta(delta: int) -> str:
    if delta > 0:
        return "#" * delta
    if delta < 0:
        return "b" * (-delta)
    return ""


def spelled_scale(root: str, formula: tuple[tuple[int, str], ...]) -> dict[str, str]:
    root_pc = pitch_class(root)
    root_letter_index = LETTER_ORDER.index(root[0].upper())
    by_degree: dict[str, str] = {}
    for degree_index, (interval, degree) in enumerate(formula):
        # b3 partage la lettre du troisième degré ; b6 celle du sixième, etc.
        # On déduit le numéro diatonique depuis le symbole.
        number = int(degree.replace("b", "").replace("#", ""))
        letter = LETTER_ORDER[(root_letter_index + number - 1) % 7]
        target_pc = (root_pc + interval) % 12
        natural_pc = NATURAL_PITCHES[letter]
        delta = (target_pc - natural_pc) % 12
        if delta > 6:
            delta -= 12
        by_degree[degree] = letter + accidental_for_delta(delta)
    return by_degree


def shape_start(root_pc: int, shape: str) -> int:
    return (root_pc - CAGED_OPEN_ROOTS[shape]) % 12


def caged_occurrences(root_pc: int) -> list[tuple[int, str]]:
    out = []
    for shape in SHAPES:
        base = shape_start(root_pc, shape)
        for octave in range(-2, 4):
            out.append((base + octave * 12, shape))
    return sorted(out, key=lambda x: (x[0], SHAPES.index(x[1])))


def shape_context(root_pc: int, shape: str) -> tuple[int, int, str, int]:
    start = shape_start(root_pc, shape)
    occ = caged_occurrences(root_pc)
    idx = next(i for i, item in enumerate(occ) if item == (start, shape))
    next_start, next_shape = occ[idx + 1]
    end = min(LAST_FRET, next_start + 2)
    begin = max(FIRST_FRET, start)
    return begin, end, next_shape, next_start


def exact_chord_positions(root_pc: int, quality: str, shape: str) -> set[tuple[int, int]]:
    start = shape_start(root_pc, shape)
    positions = set()
    for string_index, offset in enumerate(CHORD_TEMPLATES[quality][shape]):
        if offset is None:
            continue
        fret = start + offset
        if FIRST_FRET <= fret <= LAST_FRET:
            positions.add((string_index, fret))
    return positions


def note_color(degree: str) -> str:
    if degree == "1":
        return ROOT_COLOR
    if degree in {"3", "b3"}:
        return THIRD_COLOR
    if degree == "5":
        return FIFTH_COLOR
    if degree in {"2", "4"}:
        return COMMON_COLOR
    return "rgb(238,238,238)"


def spots_for(root: str, root_pc: int, formula: tuple[tuple[int, str], ...], penta_formula: tuple[tuple[int, str], ...], quality: str, shape: str) -> list[Spot]:
    start, end, _, _ = shape_context(root_pc, shape)
    note_names = spelled_scale(root, formula)
    exact = exact_chord_positions(root_pc, quality, shape)
    penta_degrees = {degree for _, degree in penta_formula}
    interval_by_pc = {((root_pc + interval) % 12): degree for interval, degree in formula}
    spots: list[Spot] = []
    for string_index, tuning in enumerate(TUNING_PCS):
        for fret in range(start, end + 1):
            pc = (tuning + fret) % 12
            if pc not in interval_by_pc:
                continue
            degree = interval_by_pc[pc]
            spots.append(Spot(string_index, fret, degree, note_names[degree], chord=(string_index, fret) in exact, penta=degree in penta_degrees))
    return spots


def text_svg(x, y, text, size=14, weight=500, anchor="middle", color=TEXT) -> str:
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="Arial, Helvetica, sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{xml_escape.escape(str(text))}</text>'


def range_left(fret: int, left: float, col_w: float, start: int) -> float:
    return left + (fret - start) * col_w


def render_board(title: str, subtitle: str, root: str, root_pc: int, shape: str, formula, penta_formula, quality: str, x: float, y: float, w: float, h: float) -> str:
    start, end, next_shape, next_start = shape_context(root_pc, shape)
    board_left = x + 82
    board_right = x + w - 34
    board_top = y + 112
    string_gap = 31
    fret_count = max(1, end - start + 1)
    col_w = (board_right - board_left) / fret_count
    top_line = board_top - 13
    bottom_line = board_top + 5 * string_gap + 13

    fill = MAJOR_COLOR if quality == "majeur" else MINOR_COLOR
    parts = [f'<g>']
    parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="18" fill="{fill}" stroke="rgb(190,190,190)" stroke-width="1.4"/>')
    parts.append(text_svg(x + w / 2, y + 34, title, 22, 700))
    parts.append(text_svg(x + w / 2, y + 60, subtitle, 13, 600, color=MUTED))
    parts.append(text_svg(x + w / 2, y + 84, f"Forme {shape} : cases {start} à {end}  |  suivante : {next_shape} case {next_start}", 12, 600, color=MUTED))

    # cordes
    for internal in range(5, -1, -1):
        row = 5 - internal
        yy = board_top + row * string_gap
        thickness = 1.2 + (5 - internal) * 0.28
        parts.append(f'<line x1="{board_left - 24:.1f}" y1="{yy:.1f}" x2="{board_right:.1f}" y2="{yy:.1f}" stroke="{GRID}" stroke-width="{thickness:.2f}"/>')
        parts.append(text_svg(x + 26, yy + 4, f"{6 - internal} {STRINGS[internal]}", 11, 700, anchor="start"))

    # frettes
    for i in range(fret_count + 1):
        fx = board_left + i * col_w
        stroke_w = 5 if start == 0 and i == 0 else 1.7
        color = "rgb(15,15,15)" if start == 0 and i == 0 else GRID
        parts.append(f'<line x1="{fx:.1f}" y1="{top_line:.1f}" x2="{fx:.1f}" y2="{bottom_line:.1f}" stroke="{color}" stroke-width="{stroke_w}"/>')
    for fret in range(start, end + 1):
        cx = board_left + (fret - start + 0.5) * col_w
        parts.append(text_svg(cx, bottom_line + 22, str(fret), 10, 700))

    def spot_xy(s: Spot) -> tuple[float, float]:
        row = 5 - s.string_index
        return board_left + (s.fret - start + 0.5) * col_w, board_top + row * string_gap

    for s in spots_for(root, root_pc, formula, penta_formula, quality, shape):
        xx, yy = spot_xy(s)
        if s.chord:
            parts.append(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="19.5" fill="none" stroke="{CHORD_STROKE}" stroke-width="3.0" stroke-dasharray="5 2"/>')
        stroke = PENTA_STROKE if s.penta else "rgb(45,45,45)"
        stroke_w = 3.2 if s.penta else 1.6
        parts.append(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="14" fill="{note_color(s.degree)}" stroke="{stroke}" stroke-width="{stroke_w}"/>')
        parts.append(text_svg(xx, yy - 1, s.degree, 9, 800))
        parts.append(text_svg(xx, yy + 10, s.note, 7, 700))

    parts.append('</g>')
    return "\n".join(parts)


def render_legend() -> str:
    y = 150
    items = [
        (ROOT_COLOR, "1 tonique"),
        (THIRD_COLOR, "3 / b3 : couleur majeure ou mineure"),
        (FIFTH_COLOR, "5 quinte"),
        (COMMON_COLOR, "2 et 4 : notes communes"),
        ("blue-solid", "contour bleu plein : notes de pentatonique"),
        ("violet-dashed", "contour violet pointillé : forme d’accord exacte"),
    ]
    total = 1320
    start = (PAGE_W - total) / 2
    parts = []
    for i, (color, label) in enumerate(items):
        x = start + i * (total / len(items))
        if color == "blue-solid":
            parts.append(f'<circle cx="{x:.1f}" cy="{y-4}" r="10" fill="white" stroke="{PENTA_STROKE}" stroke-width="3"/>')
        elif color == "violet-dashed":
            parts.append(f'<circle cx="{x:.1f}" cy="{y-4}" r="10" fill="none" stroke="{CHORD_STROKE}" stroke-width="3" stroke-dasharray="5 2"/>')
        else:
            parts.append(f'<circle cx="{x:.1f}" cy="{y-4}" r="10" fill="{color}" stroke="rgb(50,50,50)" stroke-width="1.2"/>')
        parts.append(text_svg(x + 18, y, label, 11, 700, anchor="start"))
    return "\n".join(parts)


def render_global_strip(root_pc: int, y: float) -> str:
    left = 250
    right = PAGE_W - 250
    w = right - left
    strip_h = 34
    colors = {"C": "rgb(220,235,255)", "A": "rgb(225,245,225)", "G": "rgb(255,242,205)", "E": "rgb(255,225,225)", "D": "rgb(235,225,250)"}
    occ = caged_occurrences(root_pc)
    parts = [text_svg(PAGE_W/2, y - 14, "Ordre géographique des formes pour cette fondamentale", 14, 700)]
    for i in range(len(occ)-1):
        s, sh = occ[i]
        e, _ = occ[i+1]
        vs, ve = max(FIRST_FRET, s), min(LAST_FRET, e)
        if ve <= vs:
            continue
        x = left + (vs - FIRST_FRET) / (LAST_FRET - FIRST_FRET) * w
        rw = (ve - vs) / (LAST_FRET - FIRST_FRET) * w
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{rw:.1f}" height="{strip_h}" fill="{colors[sh]}" stroke="rgb(100,100,100)" stroke-width="1"/>')
        parts.append(text_svg(x + rw/2, y + 23, sh, 13, 800))
    for fret in range(FIRST_FRET, LAST_FRET+1):
        x = left + (fret - FIRST_FRET) / (LAST_FRET - FIRST_FRET) * w
        parts.append(text_svg(x, y + 53, str(fret), 9, 700))
    return "\n".join(parts)


def safe_token(s: str) -> str:
    return s.replace("#", "sharp").replace("b", "flat").replace(" ", "_")


def generate_svg(root: str, root_pc: int, shape: str, output: Path | None = None) -> Path:
    if output is None:
        output = Path(f"{safe_token(root)}_comparaison_majeur_mineur_forme_{shape}.svg")

    major_notes = " - ".join(spelled_scale(root, MAJOR_SCALE)[d] for _, d in MAJOR_SCALE)
    minor_notes = " - ".join(spelled_scale(root, MINOR_SCALE)[d] for _, d in MINOR_SCALE)

    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="297mm" height="210mm" viewBox="0 0 {PAGE_W} {PAGE_H}">',
        '<style>@page { size: A4 landscape; margin: 8mm; }</style>',
        f'<rect x="0" y="0" width="{PAGE_W}" height="{PAGE_H}" fill="white"/>',
        text_svg(PAGE_W/2, 55, f"{root} — comparaison majeur / mineur — forme {shape}", 30, 800),
        text_svg(PAGE_W/2, 88, "Même fondamentale, même zone CAGED : observe ce qui reste commun et ce qui change la couleur.", 15, 600, color=MUTED),
        text_svg(PAGE_W/2, 116, f"Majeur : {major_notes}     |     Mineur naturel : {minor_notes}", 12, 700),
        render_legend(),
        render_global_strip(root_pc, 188),
    ]

    card_w = 790
    card_h = 385
    x1 = 58
    x2 = 906
    y1 = 285
    y2 = 720
    parts.append(render_board("1 — Pentatonique majeure", "1–2–3–5–6 : l’accord majeur avec deux chemins mélodiques", root, root_pc, shape, MAJOR_PENTA, MAJOR_PENTA, "majeur", x1, y1, card_w, card_h))
    parts.append(render_board("2 — Gamme majeure", "1–2–3–4–5–6–7 : le 4 et le 7 complètent la couleur majeure", root, root_pc, shape, MAJOR_SCALE, MAJOR_PENTA, "majeur", x2, y1, card_w, card_h))
    parts.append(render_board("3 — Pentatonique mineure", "1–b3–4–5–b7 : passage immédiat à l’état mineur/blues", root, root_pc, shape, MINOR_PENTA, MINOR_PENTA, "mineur", x1, y2, card_w, card_h))
    parts.append(render_board("4 — Gamme mineure naturelle", "1–2–b3–4–5–b6–b7 : le b6 assombrit fortement la gamme", root, root_pc, shape, MINOR_SCALE, MINOR_PENTA, "mineur", x2, y2, card_w, card_h))

    footer_y = 1145
    parts.append(text_svg(PAGE_W/2, footer_y, "À travailler : compare 3 ↔ b3, 6 ↔ b6, 7 ↔ b7. Les points communs les plus solides sont 1, 2, 4 et 5.", 15, 800))
    parts.append(text_svg(PAGE_W/2, footer_y + 25, "Ne joue pas les quatre dessins comme des gammes séparées : pars de l’accord, puis change une seule couleur à la fois.", 13, 600, color=MUTED))
    parts.append(text_svg(PAGE_W/2, PAGE_H - 22, f"{SCRIPT_NAME} v{VERSION}", 9, 500, color="rgb(145,145,145)"))
    parts.append("</svg>")
    output.write_text("\n".join(parts), encoding="utf-8")
    return output


def generate_for_shapes(root: str, root_pc: int, shape_choice: str, output: Path | None = None) -> list[Path]:
    """Génère une ou toutes les formes.

    Si shape_choice vaut "toutes", le script écrit un SVG par forme CAGED.
    Si --sortie est fourni avec toutes, il est traité comme un dossier.
    """
    if shape_choice != "toutes":
        return [generate_svg(root, root_pc, shape_choice, output)]

    output_dir = output if output is not None else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)
    return [
        generate_svg(
            root,
            root_pc,
            shape,
            output_dir / f"{safe_token(root)}_comparaison_majeur_mineur_forme_{shape}.svg",
        )
        for shape in SHAPES
    ]


def validate() -> None:
    # ordre visuel et contenus essentiels
    out = Path("/tmp/__comparaison_caged_test.svg")
    generate_svg("A", pitch_class("A"), "E", out)
    svg = out.read_text(encoding="utf-8")
    out.unlink(missing_ok=True)
    required = ["Pentatonique majeure", "Gamme majeure", "Pentatonique mineure", "Gamme mineure naturelle", "3 ↔ b3", "contour bleu plein : notes de pentatonique", "contour violet pointillé : forme d’accord exacte", "297mm", "A4 landscape"]
    missing = [r for r in required if r not in svg]
    if missing:
        raise AssertionError(f"Éléments manquants : {missing}")
    # Am forme E doit afficher A C E comme accord mineur exact, et A C D E G en penta.
    spots = spots_for("A", pitch_class("A"), MINOR_PENTA, MINOR_PENTA, "mineur", "E")
    degrees = {s.degree for s in spots}
    if degrees != {"1", "b3", "4", "5", "b7"}:
        raise AssertionError(f"Pentatonique mineure incohérente : {degrees}")
    paths = generate_for_shapes("A", pitch_class("A"), "toutes", Path("/tmp/__comparaison_toutes"))
    if len(paths) != 5 or not all(path.exists() for path in paths):
        raise AssertionError("La génération de toutes les formes est incohérente.")
    for path in paths:
        path.unlink(missing_ok=True)
    Path("/tmp/__comparaison_toutes").rmdir()


def ask_until(prompt: str, fn):
    while True:
        try:
            return fn(input(prompt))
        except ValueError as e:
            print(f"Erreur : {e}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compare majeur / mineur dans une même forme CAGED.")
    p.add_argument("--tonalite")
    p.add_argument("--forme")
    p.add_argument("--sortie")
    p.add_argument("--test", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    validate()
    if args.test:
        print("Validation réussie : comparaison penta/gamme majeur/mineur cohérente.")
        print(f"Version {VERSION}")
        return
    if args.tonalite:
        root, root_pc = normalize_root(args.tonalite)
    else:
        root, root_pc = ask_until("Tonalité / fondamentale (ex. A, F#, Bb, Ré) : ", normalize_root)
    if args.forme:
        shape = normalize_shape(args.forme)
    else:
        raw_shape = input("Forme CAGED [C/A/G/E/D/T toutes] (défaut T) : ").strip()
        shape = normalize_shape(raw_shape or "T")

    output = Path(args.sortie) if args.sortie else None
    results = generate_for_shapes(root, root_pc, shape, output)
    if len(results) == 1:
        print(f"SVG généré : {results[0]}")
    else:
        print("SVG générés :")
        for result in results:
            print(f"- {result}")
    print(f"Version {VERSION}")


if __name__ == "__main__":
    main()
