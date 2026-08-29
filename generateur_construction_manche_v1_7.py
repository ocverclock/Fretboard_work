#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from pathlib import Path

VERSION = "1.7.0"
SCRIPT_NAME = "generateur_construction_manche_v1_7.py"

# -----------------------------------------------------------------------------
# Document A4 portrait
# -----------------------------------------------------------------------------
PAGE_W = 1240
PAGE_H = 1754
FIRST_FRET = 0
LAST_FRET = 12

STRINGS = (
    (1, "E", 4),
    (2, "B", 11),
    (3, "G", 7),
    (4, "D", 2),
    (5, "A", 9),
    (6, "E", 4),
)

NATURAL_PITCHES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
LETTER_ORDER = ("C", "D", "E", "F", "G", "A", "B")

PROFILES = {
    "majeur": {
        "title": "majeur",
        "mode_name": "gamme majeure / mode ionien",
        "scale_intervals": (0, 2, 4, 5, 7, 9, 11),
        "scale_degrees": ("1", "2", "3", "4", "5", "6", "7"),
        "chord_degrees": ("1", "3", "5"),
    },
    "mineur": {
        "title": "mineur naturel",
        "mode_name": "gamme mineure naturelle / mode éolien",
        "scale_intervals": (0, 2, 3, 5, 7, 8, 10),
        "scale_degrees": ("1", "2", "b3", "4", "5", "b6", "b7"),
        "chord_degrees": ("1", "b3", "5"),
    },
}

# Charte couleur proche des autres fiches
ROOT_COLOR = "rgb(255,145,145)"
THIRD_COLOR = "rgb(255,212,125)"
FIFTH_COLOR = "rgb(150,202,255)"
OTHER_COLOR = "rgb(235,235,235)"
TEXT = "rgb(35,35,35)"
MUTED = "rgb(105,105,105)"
GRID = "rgb(92,92,92)"
SEP = "rgb(175,175,175)"
OCTAVE = "rgb(52,136,76)"

# Géométrie principale
MARGIN_X = 48
HEADER_H = 150
FOOTER_Y = 1728

SECTION_TOPS = [175, 565, 955, 1345]
SECTION_H = 320

BOARD_LEFT = 132
BOARD_RIGHT = 1180
NUT_X = 174
OPEN_X = 153
FRET_W = (BOARD_RIGHT - NUT_X) / LAST_FRET
STRING_GAP = 23
NOTE_R = 8.5

# -----------------------------------------------------------------------------
# Théorie
# -----------------------------------------------------------------------------
def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")

def normalize_root(value: str) -> str:
    cleaned = value.strip().replace("♯", "#").replace("♭", "b").replace(" ", "")
    if not cleaned:
        raise ValueError("Aucune tonalité saisie.")
    low = strip_accents(cleaned).lower()

    m = re.fullmatch(r"(do|re|mi|fa|sol|la|si)([#b]?)", low)
    if m:
        name, accidental = m.groups()
        return {
            "do": "C", "re": "D", "mi": "E", "fa": "F",
            "sol": "G", "la": "A", "si": "B",
        }[name] + accidental

    m = re.fullmatch(r"([a-g])([#b]?)", low)
    if not m:
        raise ValueError("Tonalité invalide. Exemples : G, F#, Bb, Sol, Sib.")
    letter, accidental = m.groups()
    return letter.upper() + accidental

def pitch_class(note: str) -> int:
    letter = note[0].upper()
    accidental = note[1:]
    return (NATURAL_PITCHES[letter] + accidental.count("#") - accidental.count("b")) % 12

def accidental_for_delta(delta: int) -> str:
    if delta > 0:
        return "#" * delta
    if delta < 0:
        return "b" * (-delta)
    return ""

def spelled_scale(root: str, mode: str) -> list[str]:
    profile = PROFILES[mode]
    root_pc = pitch_class(root)
    root_letter_index = LETTER_ORDER.index(root[0].upper())
    out = []
    for index, interval in enumerate(profile["scale_intervals"]):
        letter = LETTER_ORDER[(root_letter_index + index) % 7]
        target_pc = (root_pc + interval) % 12
        natural_pc = NATURAL_PITCHES[letter]
        delta = (target_pc - natural_pc) % 12
        if delta > 6:
            delta -= 12
        out.append(letter + accidental_for_delta(delta))
    return out

def scale_maps(root: str, mode: str):
    profile = PROFILES[mode]
    root_pc = pitch_class(root)
    scale = spelled_scale(root, mode)
    degree_by_pc = {}
    note_by_pc = {}
    for interval, degree, note in zip(profile["scale_intervals"], profile["scale_degrees"], scale):
        pc = (root_pc + interval) % 12
        degree_by_pc[pc] = degree
        note_by_pc[pc] = note
    return degree_by_pc, note_by_pc

# -----------------------------------------------------------------------------
# SVG helpers
# -----------------------------------------------------------------------------
def esc(text) -> str:
    return html.escape(str(text))

def text_svg(x: float, y: float, text: str, *, size: int, weight: int = 400,
             anchor: str = "middle", color: str = TEXT) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{color}">{esc(text)}</text>'
    )

def fret_x(fret: int) -> float:
    return OPEN_X if fret == 0 else NUT_X + (fret - 0.5) * FRET_W

def string_y(board_top: float, string_number: int) -> float:
    return board_top + (string_number - 1) * STRING_GAP

def degree_color(degree: str) -> str:
    if degree == "1":
        return ROOT_COLOR
    if degree in {"3", "b3"}:
        return THIRD_COLOR
    if degree == "5":
        return FIFTH_COLOR
    return OTHER_COLOR

def label_color(degree: str) -> str:
    return "white" if degree in {"1", "5"} else TEXT

def render_note(x: float, y: float, degree: str, note: str, label_mode: str) -> str:
    parts = [
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{NOTE_R:.1f}" '
        f'fill="{degree_color(degree)}" stroke="{TEXT}" stroke-width="1.15"/>'
    ]
    if label_mode == "degres":
        parts.append(text_svg(x, y + 3, degree, size=8, weight=700, color=label_color(degree)))
    elif label_mode == "notes":
        parts.append(text_svg(x, y + 3, note, size=7, weight=700, color=label_color(degree)))
    else:
        parts.append(text_svg(x, y - 1, degree, size=6, weight=700, color=label_color(degree)))
        parts.append(text_svg(x, y + 5.5, note, size=4.8, weight=600, color=label_color(degree)))
    return "".join(parts)

# -----------------------------------------------------------------------------
# Rendu du manche
# -----------------------------------------------------------------------------
def render_octave_lines(board_top: float, root_pc: int) -> str:
    patterns = ((6, 4, 2), (5, 3, 2), (4, 2, 3), (3, 1, 3))
    open_pc_by_string = {n: pc for n, _, pc in STRINGS}
    parts = []
    for low, high, delta_fret in patterns:
        for fret in range(FIRST_FRET, LAST_FRET + 1):
            if (open_pc_by_string[low] + fret) % 12 != root_pc:
                continue
            target = fret + delta_fret
            if target > LAST_FRET:
                continue
            if (open_pc_by_string[high] + target) % 12 != root_pc:
                continue
            parts.append(
                f'<line x1="{fret_x(fret):.1f}" y1="{string_y(board_top, low):.1f}" '
                f'x2="{fret_x(target):.1f}" y2="{string_y(board_top, high):.1f}" '
                f'stroke="{OCTAVE}" stroke-width="2.4" stroke-linecap="round" opacity="0.78"/>'
            )
    return "".join(parts)

def render_board(board_top: float, root: str, mode: str, stage: int, label_mode: str) -> str:
    degree_by_pc, note_by_pc = scale_maps(root, mode)
    root_pc = pitch_class(root)
    chord_degrees = set(PROFILES[mode]["chord_degrees"])

    parts = []
    board_bottom = string_y(board_top, 6)
    top_y = board_top - 14
    bottom_y = board_bottom + 14

    if stage == 2:
        parts.append(render_octave_lines(board_top, root_pc))

    # strings
    for string_number, note_name, _ in STRINGS:
        y = string_y(board_top, string_number)
        width = 1.15 + (string_number - 1) * 0.16
        parts.append(
            f'<line x1="{OPEN_X - 12:.1f}" y1="{y:.1f}" x2="{BOARD_RIGHT:.1f}" y2="{y:.1f}" '
            f'stroke="{TEXT}" stroke-width="{width:.2f}"/>'
        )
        parts.append(text_svg(100, y + 4, f"{string_number}{note_name}", size=11, weight=700, anchor="end"))

    # nut and frets
    parts.append(
        f'<line x1="{NUT_X:.1f}" y1="{top_y:.1f}" x2="{NUT_X:.1f}" y2="{bottom_y:.1f}" '
        'stroke="rgb(10,10,10)" stroke-width="6"/>'
    )
    for fret in range(1, LAST_FRET + 1):
        x = NUT_X + fret * FRET_W
        parts.append(
            f'<line x1="{x:.1f}" y1="{top_y:.1f}" x2="{x:.1f}" y2="{bottom_y:.1f}" '
            f'stroke="{GRID}" stroke-width="1.1"/>'
        )

    # fret numbers
    parts.append(text_svg(OPEN_X, bottom_y + 18, "0", size=9, weight=700, color=MUTED))
    for fret in range(1, LAST_FRET + 1):
        parts.append(text_svg(fret_x(fret), bottom_y + 18, str(fret), size=9, weight=700, color=MUTED))

    # markers
    for fret in (3, 5, 7, 9, 12):
        x = fret_x(fret)
        marker_y = bottom_y + 32
        if fret == 12:
            parts.append(f'<circle cx="{x - 5:.1f}" cy="{marker_y:.1f}" r="2.2" fill="rgb(95,95,95)"/>')
            parts.append(f'<circle cx="{x + 5:.1f}" cy="{marker_y:.1f}" r="2.2" fill="rgb(95,95,95)"/>')
        else:
            parts.append(f'<circle cx="{x:.1f}" cy="{marker_y:.1f}" r="2.2" fill="rgb(95,95,95)"/>')

    # notes
    for string_number, _, open_pc in STRINGS:
        y = string_y(board_top, string_number)
        for fret in range(FIRST_FRET, LAST_FRET + 1):
            pc = (open_pc + fret) % 12
            if pc not in degree_by_pc:
                continue
            degree = degree_by_pc[pc]
            note = note_by_pc[pc]

            visible = False
            if stage in (1, 2):
                visible = degree == "1"
            elif stage == 3:
                visible = degree in chord_degrees
            elif stage == 4:
                visible = True

            if visible:
                parts.append(render_note(fret_x(fret), y, degree, note, label_mode))

    return "".join(parts)

# -----------------------------------------------------------------------------
# Page
# -----------------------------------------------------------------------------
def render_header(root: str, mode: str, label_mode: str) -> str:
    profile = PROFILES[mode]
    scale = spelled_scale(root, mode)
    chord_notes = [scale[0], scale[2], scale[4]]
    items = [
        (ROOT_COLOR, "1", "Tonique"),
        (THIRD_COLOR, profile["chord_degrees"][1], "Tierce"),
        (FIFTH_COLOR, "5", "Quinte"),
        (OTHER_COLOR, "2+", "Autres"),
    ]
    parts = [
        text_svg(PAGE_W / 2, 44, f"{root} {profile['title']} — construire le manche", size=24, weight=700),
        text_svg(PAGE_W / 2, 69, "Fondamentales → octaves → squelette → gamme", size=12, weight=600, color=MUTED),
        text_svg(PAGE_W / 2, 90, f"Accord : {' - '.join(chord_notes)}   |   Formule : {' - '.join(profile['chord_degrees'])}", size=10, weight=700),
        text_svg(PAGE_W / 2, 108, f"{profile['mode_name']} : {' - '.join(scale)}", size=9, weight=600, color=MUTED),
    ]
    start_x = 145
    item_w = 126
    y = 132
    for idx, (fill, short, label) in enumerate(items):
        x = start_x + idx * item_w
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9.4" fill="{fill}" stroke="{TEXT}" stroke-width="1.0"/>')
        parts.append(text_svg(x, y + 3.2, short, size=7, weight=700))
        parts.append(text_svg(x + 16, y + 3.2, label, size=10, weight=600, anchor="start"))
    lx = start_x + len(items) * item_w + 10
    parts.append(f'<line x1="{lx:.1f}" y1="{y:.1f}" x2="{lx+25:.1f}" y2="{y:.1f}" stroke="{OCTAVE}" stroke-width="2.4" stroke-linecap="round"/>')
    parts.append(text_svg(lx + 33, y + 3.2, "Octaves", size=10, weight=600, anchor="start"))
    parts.append(text_svg(PAGE_W - 48, y + 3.2, f"Étiquettes : {label_mode}", size=9, weight=500, anchor="end", color=MUTED))
    return "".join(parts)

def render_section(section_no: int, section_top: float, title: str, subtitle: str,
                   root: str, mode: str, label_mode: str) -> str:
    board_top = section_top + 74
    parts = [
        f'<line x1="{MARGIN_X:.1f}" y1="{section_top:.1f}" x2="{PAGE_W - MARGIN_X:.1f}" y2="{section_top:.1f}" '
        f'stroke="{SEP}" stroke-width="1.15"/>',
        f'<circle cx="78" cy="{section_top + 24:.1f}" r="16" fill="white" stroke="{TEXT}" stroke-width="1.4"/>',
        text_svg(78, section_top + 29, str(section_no), size=12, weight=700),
        text_svg(110, section_top + 29, title, size=17, weight=700, anchor="start"),
        text_svg(PAGE_W - 70, section_top + 29, subtitle, size=10, weight=600, anchor="end", color=MUTED),
        render_board(board_top, root, mode, section_no, label_mode),
    ]
    return "".join(parts)

def script_fingerprint() -> str:
    try:
        return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
    except OSError:
        return "indisponible"

def safe_token(text: str) -> str:
    return text.replace("#", "sharp").replace("b", "flat").replace(" ", "_").replace("/", "-")

def generate_svg(root: str, mode: str, label_mode: str, output_path: Path | None = None) -> Path:
    if output_path is None:
        output_path = Path(f"{safe_token(root)}_{mode}_construction_manche_A4_portrait_v1_7.svg")
    titles = [
        ("Fondamentales", "repère la tonique"),
        ("Octaves", "relie les mêmes notes"),
        ("Squelette 1–3–5", "ajoute tierce et quinte"),
        ("Gamme complète", "complète avec 2-4-6-7"),
    ]

    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        f'<!-- Généré par {SCRIPT_NAME} v{VERSION} -->',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 {PAGE_W} {PAGE_H}">',
        '<style>@page { size: A4 portrait; margin: 0; }</style>',
        f'<rect x="0" y="0" width="{PAGE_W}" height="{PAGE_H}" fill="white"/>',
        render_header(root, mode, label_mode),
    ]
    for i, (top, (title, subtitle)) in enumerate(zip(SECTION_TOPS, titles), start=1):
        parts.append(render_section(i, top, title, subtitle, root, mode, label_mode))

    parts.append(text_svg(PAGE_W / 2, FOOTER_Y, f"{SCRIPT_NAME} v{VERSION} — 12 frettes — empreinte {script_fingerprint()}", size=8, weight=500, color=MUTED))
    parts.append("</svg>")
    output_path.write_text("\n".join(parts), encoding="utf-8")
    return output_path

# -----------------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------------
def validate() -> None:
    checks = {
        ("G", "majeur"): ["G", "A", "B", "C", "D", "E", "F#"],
        ("Bb", "majeur"): ["Bb", "C", "D", "Eb", "F", "G", "A"],
        ("A", "mineur"): ["A", "B", "C", "D", "E", "F", "G"],
    }
    for (root, mode), expected in checks.items():
        actual = spelled_scale(root, mode)
        if actual != expected:
            raise AssertionError(f"Orthographe incorrecte pour {root} {mode}: {actual}")

# -----------------------------------------------------------------------------
# Mode interactif
# -----------------------------------------------------------------------------
def ask(prompt: str, default: str) -> str:
    ans = input(f"{prompt} [{default}] : ").strip()
    return ans or default

def interactive_main() -> None:
    print("=== Générateur construction du manche — A4 portrait ===")
    root = normalize_root(ask("Tonalité", "G"))
    mode = ask("Mode (majeur/mineur)", "majeur").lower()
    label_mode = ask("Étiquettes (degres/notes/mixte)", "degres").lower()
    out_dir = Path(ask("Dossier de sortie", "."))
    out_dir.mkdir(parents=True, exist_ok=True)

    if mode not in PROFILES:
        raise SystemExit("Mode invalide : majeur ou mineur.")
    if label_mode not in {"degres", "notes", "mixte"}:
        raise SystemExit("Étiquettes invalides : degres, notes, mixte.")

    out = out_dir / f"{safe_token(root)}_{mode}_construction_manche_A4_portrait_v1_7.svg"
    print(generate_svg(root, mode, label_mode, out))

if __name__ == "__main__":
    validate()
    interactive_main()
