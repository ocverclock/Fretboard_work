#!/usr/bin/env python3
"""
Générateur pédagogique de cellules CAGED et de pentatoniques enrichies.

Objectif pédagogique : ajouter une seule information à la fois autour d'une
forme d'accord connue.

Deux modules :
1. Cellules de quatre notes
   - Maj 1235
   - Maj 1345
   - Maj 13#45
   - m 1235
   - m 1345
2. Pentatoniques enrichies
   - majeure + 4, #4, 7 ou b7
   - mineure + 2, 6 ou b6

La page conserve toujours la même disposition :
    C   A   G
      E   D

Le bandeau supérieur rappelle l'ordre géographique réel des formes sur le
manche. Chaque carte est ensuite un zoom local indépendant afin de faciliter
la comparaison visuelle.

Dépendances : aucune pour les fiches et le guide A4 HTML/SVG.
CairoSVG et pypdf sont optionnels pour produire directement un PDF fusionné.
"""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata
import xml.sax.saxutils as xml_escape


GENERATOR_VERSION = "1.3.4"
SCRIPT_NAME = "generateur_cellules_caged_v1_3_4.py"

FIRST_FRET = 0
LAST_FRET = 15
STRINGS = ("E", "A", "D", "G", "B", "E")  # ordre interne : cordes 6 -> 1
TUNING_PCS = (4, 9, 2, 7, 11, 4)
SHAPES = ("C", "A", "G", "E", "D")
GRID_LAYOUT = (("C", "A", "G"), ("E", "D"))

CANVAS_WIDTH = 1600
CANVAS_HEIGHT = 1240
PRINT_PAGE_WIDTH = 1754   # A4 paysage
PRINT_PAGE_HEIGHT = 1240
PRINT_MARGIN_X = 118
PRINT_MARGIN_Y = 36
PRINT_SCALE = min((PRINT_PAGE_WIDTH - 2 * PRINT_MARGIN_X) / CANVAS_WIDTH,
                  (PRINT_PAGE_HEIGHT - 2 * PRINT_MARGIN_Y) / CANVAS_HEIGHT)

ROOT_COLOR = "rgb(255,145,145)"
THIRD_COLOR = "rgb(255,212,125)"
FIFTH_COLOR = "rgb(150,202,255)"
SEVENTH_COLOR = "rgb(202,175,240)"
OTHER_COLOR = "rgb(238,238,238)"
CARD_FILL = "rgb(252,252,252)"
CARD_STROKE = "rgb(195,195,195)"
SELECTED_STROKE = "rgb(34,83,155)"
ADDED_STROKE = "rgb(108,55,170)"
ADDED_HALO = "rgb(232,217,247)"
GRID_STROKE = "rgb(70,70,70)"
TEXT = "rgb(35,35,35)"
MUTED = "rgb(105,105,105)"

NATURAL_PITCHES = {
    "C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11,
}
LETTER_ORDER = ("C", "D", "E", "F", "G", "A", "B")

DEGREE_INTERVALS = {
    "1": 0,
    "b2": 1, "2": 2,
    "b3": 3, "3": 4,
    "4": 5, "#4": 6, "b5": 6,
    "5": 7,
    "b6": 8, "6": 9,
    "b7": 10, "7": 11,
}

DEGREE_LETTER_STEPS = {
    "1": 0,
    "b2": 1, "2": 1,
    "b3": 2, "3": 2,
    "4": 3, "#4": 3, "b5": 4,
    "5": 4,
    "b6": 5, "6": 5,
    "b7": 6, "7": 6,
}

CAGED_OPEN_ROOTS = {"C": 0, "A": 9, "G": 7, "E": 4, "D": 2}

# Décalages par rapport au départ de la forme. Ordre corde 6 -> corde 1.
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
class LessonProfile:
    key: str
    module: str
    quality: str
    title: str
    short_title: str
    formula: tuple[str, ...]
    base_formula: tuple[str, ...]
    added_degree: str
    color_name: str
    resolution: str
    instruction: str


CELL_PROFILES = {
    "maj1235": LessonProfile(
        key="maj1235", module="cellule", quality="majeur",
        title="Cellule majeure 1–2–3–5", short_title="Maj 1235",
        formula=("1", "2", "3", "5"), base_formula=("1", "3", "5"),
        added_degree="2", color_name="ouverte / add9",
        resolution="2 → 1 ou 3",
        instruction="Fais d'abord entendre l'accord 1–3–5, puis utilise 2 comme élan vers 1 ou 3.",
    ),
    "maj1345": LessonProfile(
        key="maj1345", module="cellule", quality="majeur",
        title="Cellule majeure 1–3–4–5", short_title="Maj 1345",
        formula=("1", "3", "4", "5"), base_formula=("1", "3", "5"),
        added_degree="4", color_name="suspendue / gospel / rock",
        resolution="4 → 3 ou 5",
        instruction="Le 4 crée une tension : ne le traite pas comme un repos, fais-le revenir vers 3 ou avancer vers 5.",
    ),
    "maj13#45": LessonProfile(
        key="maj13#45", module="cellule", quality="majeur",
        title="Cellule majeure 1–3–#4–5", short_title="Maj 13#45",
        formula=("1", "3", "#4", "5"), base_formula=("1", "3", "5"),
        added_degree="#4", color_name="lydienne / moderne",
        resolution="#4 → 5",
        instruction="Le #4 est une couleur, pas une destination : fais entendre sa poussée naturelle vers 5.",
    ),
    "min1235": LessonProfile(
        key="min1235", module="cellule", quality="mineur",
        title="Cellule mineure 1–2–b3–5", short_title="m 1235",
        formula=("1", "2", "b3", "5"), base_formula=("1", "b3", "5"),
        added_degree="2", color_name="mineure ouverte / add9",
        resolution="2 → 1 ou b3",
        instruction="Fais entendre la couleur mineure avec b3 ; le 2 sert d'approche vers 1 ou b3.",
    ),
    "min1345": LessonProfile(
        key="min1345", module="cellule", quality="mineur",
        title="Cellule mineure 1–b3–4–5", short_title="m 1345",
        formula=("1", "b3", "4", "5"), base_formula=("1", "b3", "5"),
        added_degree="4", color_name="noyau pentatonique mineur",
        resolution="4 → b3 ou 5",
        instruction="Cette cellule prépare la pentatonique mineure : ajoute ensuite b7 pour la compléter.",
    ),
}

PENTA_PROFILES = {
    "maj+4": LessonProfile(
        key="maj+4", module="penta", quality="majeur",
        title="Pentatonique majeure + 4", short_title="Penta Maj + 4",
        formula=("1", "2", "3", "4", "5", "6"),
        base_formula=("1", "2", "3", "5", "6"), added_degree="4",
        color_name="majeure avec tension 11",
        resolution="4 → 3 ou 5",
        instruction="Conserve la pentatonique comme base ; ajoute 4 ponctuellement et résous-le vers 3 ou 5.",
    ),
    "maj+#4": LessonProfile(
        key="maj+#4", module="penta", quality="majeur",
        title="Pentatonique majeure + #4 / #11", short_title="Penta Maj + #4",
        formula=("1", "2", "3", "#4", "5", "6"),
        base_formula=("1", "2", "3", "5", "6"), added_degree="#4",
        color_name="lydienne / fusion",
        resolution="#4 → 5",
        instruction="La pentatonique reste stable ; le #4 apporte la couleur lydienne et pousse vers 5.",
    ),
    "maj+7": LessonProfile(
        key="maj+7", module="penta", quality="majeur",
        title="Pentatonique majeure + 7", short_title="Penta Maj + 7",
        formula=("1", "2", "3", "5", "6", "7"),
        base_formula=("1", "2", "3", "5", "6"), added_degree="7",
        color_name="majeure / maj7",
        resolution="7 → 1",
        instruction="Le 7 décrit fortement l'accord majeur 7 ; utilise-le comme aspiration vers la tonique.",
    ),
    "maj+b7": LessonProfile(
        key="maj+b7", module="penta", quality="majeur",
        title="Pentatonique majeure + b7", short_title="Penta Maj + b7",
        formula=("1", "2", "3", "5", "6", "b7"),
        base_formula=("1", "2", "3", "5", "6"), added_degree="b7",
        color_name="dominante / mixolydienne",
        resolution="b7 → 6 ou 1",
        instruction="Le b7 transforme la couleur majeure en dominante ; vise ensuite 6 ou 1 selon la phrase.",
    ),
    "min+2": LessonProfile(
        key="min+2", module="penta", quality="mineur",
        title="Pentatonique mineure + 2 / 9", short_title="Penta m + 2",
        formula=("1", "2", "b3", "4", "5", "b7"),
        base_formula=("1", "b3", "4", "5", "b7"), added_degree="2",
        color_name="mineure ouverte / add9",
        resolution="2 → 1 ou b3",
        instruction="Le 2 ouvre la pentatonique mineure ; fais-le retomber vers 1 ou b3 pour garder l'accord lisible.",
    ),
    "min+6": LessonProfile(
        key="min+6", module="penta", quality="mineur",
        title="Pentatonique mineure + 6", short_title="Penta m + 6",
        formula=("1", "b3", "4", "5", "6", "b7"),
        base_formula=("1", "b3", "4", "5", "b7"), added_degree="6",
        color_name="dorienne",
        resolution="6 → 5 ou b7",
        instruction="Le 6 naturel donne immédiatement la couleur dorienne ; compare-le ensuite au b6.",
    ),
    "min+b6": LessonProfile(
        key="min+b6", module="penta", quality="mineur",
        title="Pentatonique mineure + b6", short_title="Penta m + b6",
        formula=("1", "b3", "4", "5", "b6", "b7"),
        base_formula=("1", "b3", "4", "5", "b7"), added_degree="b6",
        color_name="mineure naturelle / éolienne",
        resolution="b6 → 5",
        instruction="Le b6 assombrit la pentatonique et signale le mineur naturel ; fais-le revenir vers 5.",
    ),
}

ALL_PROFILES = {**CELL_PROFILES, **PENTA_PROFILES}
CELL_LEARNING_ORDER = ("maj1235", "min1235", "maj1345", "min1345", "maj13#45")
PENTA_LEARNING_ORDER = ("maj+4", "maj+#4", "maj+7", "maj+b7", "min+2", "min+6", "min+b6")


@dataclass(frozen=True)
class Spot:
    string_index: int
    fret: int
    degree: str
    note: str
    exact_chord: bool = False
    added: bool = False


# -----------------------------------------------------------------------------
# Utilitaires musicaux
# -----------------------------------------------------------------------------
def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def pitch_class(note: str) -> int:
    letter = note[0].upper()
    accidental = note[1:]
    if letter not in NATURAL_PITCHES:
        raise ValueError(f"Note invalide : {note}")
    return (NATURAL_PITCHES[letter] + accidental.count("#") - accidental.count("b")) % 12


def normalize_root(user_input: str) -> tuple[str, int]:
    cleaned = user_input.strip().replace("♯", "#").replace("♭", "b").replace(" ", "")
    if not cleaned:
        raise ValueError("Aucune fondamentale saisie.")

    simple = strip_accents(cleaned).lower()
    fr = re.fullmatch(r"(do|re|mi|fa|sol|la|si)([#b]{0,2})", simple)
    if fr:
        name, accidental = fr.groups()
        letter = {"do": "C", "re": "D", "mi": "E", "fa": "F", "sol": "G", "la": "A", "si": "B"}[name]
        root = letter + accidental
    else:
        intl = re.fullmatch(r"([a-g])([#b]{0,2})", simple)
        if not intl:
            raise ValueError("Fondamentale inconnue. Exemples : A, F#, Bb, Ré, Sib.")
        letter, accidental = intl.groups()
        root = letter.upper() + accidental
    return root, pitch_class(root)


def accidental_for_delta(delta: int) -> str:
    return "#" * delta if delta > 0 else "b" * (-delta) if delta < 0 else ""


def note_for_degree(root: str, degree: str) -> str:
    root_pc = pitch_class(root)
    letter_index = LETTER_ORDER.index(root[0].upper())
    target_letter = LETTER_ORDER[(letter_index + DEGREE_LETTER_STEPS[degree]) % 7]
    target_pc = (root_pc + DEGREE_INTERVALS[degree]) % 12
    delta = (target_pc - NATURAL_PITCHES[target_letter]) % 12
    if delta > 6:
        delta -= 12
    return target_letter + accidental_for_delta(delta)


def degree_for_pc(root_pc: int, formula: tuple[str, ...], pc: int) -> str | None:
    interval = (pc - root_pc) % 12
    for degree in formula:
        if DEGREE_INTERVALS[degree] == interval:
            return degree
    return None


def shape_start(root_pc: int, shape: str) -> int:
    return (root_pc - CAGED_OPEN_ROOTS[shape]) % 12


def local_range(root_pc: int, shape: str) -> tuple[int, int]:
    start = shape_start(root_pc, shape)
    if start == 0:
        return 0, 5
    return start, min(LAST_FRET, start + 4)


def exact_positions(root_pc: int, quality: str, shape: str) -> set[tuple[int, int]]:
    start = shape_start(root_pc, shape)
    result: set[tuple[int, int]] = set()
    for string_index, offset in enumerate(CHORD_TEMPLATES[quality][shape]):
        if offset is not None:
            result.add((string_index, start + offset))
    return result


def spots_for_shape(root: str, root_pc: int, profile: LessonProfile, shape: str) -> list[Spot]:
    fret_start, fret_end = local_range(root_pc, shape)
    exact = exact_positions(root_pc, profile.quality, shape)
    spots: list[Spot] = []

    for string_index, open_pc in enumerate(TUNING_PCS):
        for fret in range(fret_start, fret_end + 1):
            pc = (open_pc + fret) % 12
            degree = degree_for_pc(root_pc, profile.formula, pc)
            if degree is None:
                continue
            spots.append(
                Spot(
                    string_index=string_index,
                    fret=fret,
                    degree=degree,
                    note=note_for_degree(root, degree),
                    exact_chord=(string_index, fret) in exact,
                    added=degree == profile.added_degree,
                )
            )
    return spots


# -----------------------------------------------------------------------------
# SVG
# -----------------------------------------------------------------------------
def esc(text: str) -> str:
    return xml_escape.escape(str(text))


def text_svg(x: float, y: float, text: str, *, size: int, weight: int = 400,
             anchor: str = "middle", color: str = TEXT) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{color}">{esc(text)}</text>'
    )


def degree_color(degree: str) -> str:
    if degree == "1":
        return ROOT_COLOR
    if degree in {"3", "b3"}:
        return THIRD_COLOR
    if degree in {"5", "b5"}:
        return FIFTH_COLOR
    if degree in {"7", "b7"}:
        return SEVENTH_COLOR
    return OTHER_COLOR


def script_fingerprint() -> str:
    try:
        return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
    except OSError:
        return "indisponible"


def render_header(root: str, profile: LessonProfile, label_mode: str) -> str:
    formula = " – ".join(profile.formula)
    base = " – ".join(profile.base_formula)
    return "".join([
        text_svg(CANVAS_WIDTH / 2, 48, f"{root} — {profile.title}", size=34, weight=700),
        text_svg(CANVAS_WIDTH / 2, 84,
                 f"Base : {base}   +   note ajoutée : {profile.added_degree}   →   formule : {formula}",
                 size=18, weight=700, color="rgb(60,60,60)"),
        text_svg(CANVAS_WIDTH / 2, 114,
                 f"Couleur : {profile.color_name}   |   Résolution : {profile.resolution}",
                 size=16, weight=600, color=MUTED),
        text_svg(CANVAS_WIDTH / 2, 142, profile.instruction,
                 size=15, weight=500, color=MUTED),
        render_legend(185, label_mode),
    ])


def render_legend(y: float, label_mode: str) -> str:
    items = [
        (ROOT_COLOR, "Tonique 1", "normal"),
        (THIRD_COLOR, "Tierce 3 / b3", "normal"),
        (FIFTH_COLOR, "Quinte 5", "normal"),
        (SELECTED_STROKE, "Contour bleu : forme d’accord", "outline"),
        (ADDED_STROKE, "Anneau violet : note ajoutée", "ring"),
    ]
    start = 115
    item_w = 275
    parts = [f'<g transform="translate(0,{y:.1f})">']
    for i, (color, label, kind) in enumerate(items):
        x = start + i * item_w
        if kind == "ring":
            parts.append(f'<circle cx="{x:.1f}" cy="0" r="12" fill="{ADDED_HALO}" fill-opacity="0.55" stroke="{color}" stroke-width="3.2"/>')
            parts.append(f'<circle cx="{x:.1f}" cy="0" r="7" fill="white" stroke="rgb(60,60,60)" stroke-width="1"/>')
        elif kind == "outline":
            parts.append(f'<circle cx="{x:.1f}" cy="0" r="9" fill="white" stroke="{color}" stroke-width="3.2"/>')
        else:
            parts.append(f'<circle cx="{x:.1f}" cy="0" r="9" fill="{color}" stroke="rgb(60,60,60)" stroke-width="1.4"/>')
        parts.append(text_svg(x + 20, 5, label, size=13, weight=600, anchor="start"))
    parts.append(text_svg(CANVAS_WIDTH / 2, 35, f"Étiquettes : {label_mode}", size=12, color=MUTED))
    parts.append("</g>")
    return "".join(parts)


def render_global_strip(root_pc: int, y: float) -> str:
    left = 145
    width = 1310
    fret_w = width / LAST_FRET
    parts = [f'<g transform="translate(0,{y:.1f})">']
    parts.append(text_svg(CANVAS_WIDTH / 2, 18, "Ordre géographique réel des formes sur le manche", size=17, weight=700))

    occurrences: list[tuple[int, str]] = []
    for shape in SHAPES:
        base = shape_start(root_pc, shape)
        for octave in (-12, 0, 12):
            occurrences.append((base + octave, shape))
    occurrences.sort()

    colors = {"C": "rgb(220,235,255)", "A": "rgb(225,245,225)", "G": "rgb(255,242,205)",
              "E": "rgb(255,225,225)", "D": "rgb(235,225,250)"}
    strip_y, strip_h = 34, 38
    for i in range(len(occurrences) - 1):
        start, shape = occurrences[i]
        end, _ = occurrences[i + 1]
        vis_start = max(FIRST_FRET, start)
        vis_end = min(LAST_FRET, end)
        if vis_end <= vis_start:
            continue
        x = left + vis_start * fret_w
        w = (vis_end - vis_start) * fret_w
        parts.append(f'<rect x="{x:.1f}" y="{strip_y}" width="{w:.1f}" height="{strip_h}" fill="{colors[shape]}" stroke="rgb(110,110,110)" stroke-width="1"/>')
        parts.append(text_svg(x + w / 2, strip_y + 25, shape, size=15, weight=700))
    for fret in range(16):
        parts.append(text_svg(left + fret * fret_w, 90, str(fret), size=10, weight=600, color=MUTED))
    parts.append("</g>")
    return "".join(parts)


def card_positions() -> dict[str, tuple[float, float]]:
    card_w = 490
    top_y = 360
    bottom_y = 745
    return {
        "C": (35, top_y),
        "A": (555, top_y),
        "G": (1075, top_y),
        "E": (295, bottom_y),
        "D": (815, bottom_y),
    }


def render_card(root: str, root_pc: int, profile: LessonProfile, shape: str,
                label_mode: str, x: float, y: float) -> str:
    card_w, card_h = 490, 335
    board_left = x + 62
    board_right = x + card_w - 25
    board_top = y + 105
    string_gap = 29
    fret_start, fret_end = local_range(root_pc, shape)
    open_mode = fret_start == 0
    fretted_count = fret_end if open_mode else fret_end - fret_start + 1
    if fretted_count <= 0:
        raise AssertionError("Fenêtre de frettes invalide")
    nut_x = board_left
    open_x = board_left - 28
    col_w = (board_right - board_left) / fretted_count

    parts = [f'<g>']
    parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{card_w}" height="{card_h}" rx="16" fill="{CARD_FILL}" stroke="{CARD_STROKE}" stroke-width="1.5"/>')
    parts.append(text_svg(x + card_w / 2, y + 32, f"Forme {shape}", size=22, weight=700))
    start = shape_start(root_pc, shape)
    parts.append(text_svg(x + card_w / 2, y + 56,
                          f"Départ de la forme : case {start}   |   {profile.resolution}",
                          size=13, weight=600, color=MUTED))
    parts.append(text_svg(x + card_w / 2, y + 78,
                          "Bleu = accord exact • violet = note ajoutée",
                          size=12, weight=500, color=MUTED))

    # Cordes : visuellement corde 1 en haut, corde 6 en bas.
    for internal_index in range(5, -1, -1):
        display_row = 5 - internal_index
        yy = board_top + display_row * string_gap
        thickness = 1.25 + (5 - internal_index) * 0.25
        parts.append(f'<line x1="{open_x - 10:.1f}" y1="{yy:.1f}" x2="{board_right:.1f}" y2="{yy:.1f}" stroke="{GRID_STROKE}" stroke-width="{thickness:.2f}"/>')
        parts.append(text_svg(x + 18, yy + 4, f"{6 - internal_index} {STRINGS[internal_index]}", size=11, weight=700, anchor="start"))

    top_line = board_top - 12
    bottom_line = board_top + 5 * string_gap + 12
    if open_mode:
        parts.append(f'<line x1="{nut_x:.1f}" y1="{top_line:.1f}" x2="{nut_x:.1f}" y2="{bottom_line:.1f}" stroke="rgb(15,15,15)" stroke-width="6"/>')
        for i in range(1, fret_end + 1):
            fx = board_left + i * col_w
            parts.append(f'<line x1="{fx:.1f}" y1="{top_line:.1f}" x2="{fx:.1f}" y2="{bottom_line:.1f}" stroke="{GRID_STROKE}" stroke-width="1.6"/>')
        parts.append(text_svg(open_x, bottom_line + 22, "0", size=10, weight=700))
        for fret in range(1, fret_end + 1):
            cx = board_left + (fret - 0.5) * col_w
            parts.append(text_svg(cx, bottom_line + 22, str(fret), size=10, weight=700))
    else:
        for i in range(fretted_count + 1):
            fx = board_left + i * col_w
            parts.append(f'<line x1="{fx:.1f}" y1="{top_line:.1f}" x2="{fx:.1f}" y2="{bottom_line:.1f}" stroke="{GRID_STROKE}" stroke-width="1.6"/>')
        for fret in range(fret_start, fret_end + 1):
            cx = board_left + (fret - fret_start + 0.5) * col_w
            parts.append(text_svg(cx, bottom_line + 22, str(fret), size=10, weight=700))

    def spot_xy(spot: Spot) -> tuple[float, float]:
        row = 5 - spot.string_index
        yy = board_top + row * string_gap
        if open_mode and spot.fret == 0:
            xx = open_x
        elif open_mode:
            xx = board_left + (spot.fret - 0.5) * col_w
        else:
            xx = board_left + (spot.fret - fret_start + 0.5) * col_w
        return xx, yy

    for spot in spots_for_shape(root, root_pc, profile, shape):
        xx, yy = spot_xy(spot)
        radius = 13
        if spot.added:
            parts.append(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="{radius + 5.5}" fill="{ADDED_HALO}" fill-opacity="0.52" stroke="{ADDED_STROKE}" stroke-width="3.2"/>')
        stroke = SELECTED_STROKE if spot.exact_chord else "rgb(45,45,45)"
        stroke_w = 3.2 if spot.exact_chord else 1.8
        parts.append(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="{radius}" fill="{degree_color(spot.degree)}" stroke="{stroke}" stroke-width="{stroke_w}"/>')
        if label_mode == "notes":
            parts.append(text_svg(xx, yy + 4, spot.note, size=10, weight=700))
        elif label_mode == "mixte":
            parts.append(text_svg(xx, yy - 1, spot.degree, size=9, weight=700))
            parts.append(text_svg(xx, yy + 10, spot.note, size=7, weight=600))
        else:
            parts.append(text_svg(xx, yy + 4, spot.degree, size=10, weight=700))

    parts.append(text_svg(x + card_w / 2, y + card_h - 18,
                          f"Consigne : trouve {profile.added_degree}, joue-le puis résous {profile.resolution}.",
                          size=12, weight=600, color="rgb(70,70,70)"))
    parts.append("</g>")
    return "".join(parts)


def render_footer(profile: LessonProfile) -> str:
    y = 1130
    parts = [
        text_svg(CANVAS_WIDTH / 2, y,
                 "Routine : 1) joue la forme d’accord bleue  2) retrouve ses notes autour  3) ajoute le contour violet  4) résous-le consciemment.",
                 size=15, weight=700),
        text_svg(CANVAS_WIDTH / 2, y + 28,
                 "Ne parcours pas mécaniquement le dessin : crée des phrases courtes et termine sur 1, tierce ou 5.",
                 size=14, weight=500, color=MUTED),
        text_svg(CANVAS_WIDTH / 2, y + 57,
                 "Travaille ensuite la même cellule dans la forme CAGED suivante, sans changer de fondamentale.",
                 size=14, weight=500, color=MUTED),
        text_svg(CANVAS_WIDTH / 2, 1215,
                 f"{SCRIPT_NAME} v{GENERATOR_VERSION} — empreinte {script_fingerprint()}",
                 size=10, color="rgb(145,145,145)"),
    ]
    return "".join(parts)


def safe_token(text: str) -> str:
    return text.replace("#", "sharp").replace("b", "flat").replace("+", "plus").replace(" ", "_")


def generate_svg(root: str, root_pc: int, profile: LessonProfile,
                 label_mode: str = "degres", output_path: Path | None = None) -> Path:
    """Génère une fiche SVG optimisée pour l'impression A4 paysage."""
    if output_path is None:
        output_path = Path(f"{safe_token(root)}_{safe_token(profile.key)}_cellules_CAGED.svg")

    tx = (PRINT_PAGE_WIDTH - CANVAS_WIDTH * PRINT_SCALE) / 2
    ty = PRINT_MARGIN_Y

    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="297mm" height="210mm" viewBox="0 0 {PRINT_PAGE_WIDTH} {PRINT_PAGE_HEIGHT}">',
        '<style>@page { size: A4 landscape; margin: 8mm; }</style>',
        f'<rect x="0" y="0" width="{PRINT_PAGE_WIDTH}" height="{PRINT_PAGE_HEIGHT}" fill="white"/>',
        f'<g transform="translate({tx:.2f},{ty:.2f}) scale({PRINT_SCALE:.6f})">',
        render_header(root, profile, label_mode),
        render_global_strip(root_pc, 245),
    ]
    for shape, (x, y) in card_positions().items():
        parts.append(render_card(root, root_pc, profile, shape, label_mode, x, y))
    parts.append(render_footer(profile))
    parts.append('</g>')
    parts.append('</svg>')
    output_path.write_text("\n".join(parts), encoding="utf-8")
    return output_path



# -----------------------------------------------------------------------------
# Guide pédagogique imprimable
# -----------------------------------------------------------------------------
GUIDE_DETAILS = {
    "maj1235": {
        "theme": "Air et ouverture",
        "feeling": "Le 2 / 9 éclaire l'accord sans changer sa nature. Il apporte de l'espace, comme un accord add9.",
        "listen": "Écoute 1–2–3 : le 2 doit être un élan, pas un point d'arrivée.",
        "orientation": "1→2→3 pour ouvrir ; 3→2→1 pour refermer. Puis isole 2→3 et 2→1.",
        "fill": "rgb(238,247,255)",
        "accent": "rgb(57,116,164)",
    },
    "min1235": {
        "theme": "Mineur ouvert et intime",
        "feeling": "Le 2 / 9 évite un mineur trop fermé. Il apporte respiration, douceur et une mélancolie plus claire.",
        "listen": "Compare 2→b3 pour renforcer le mineur, puis 2→1 pour retrouver le repos.",
        "orientation": "1→2→b3 pour affirmer le mineur ; b3→2→1 pour revenir au repos.",
        "fill": "rgb(243,239,252)",
        "accent": "rgb(99,73,150)",
    },
    "maj1345": {
        "theme": "Suspension gospel, soul et rock",
        "feeling": "Le 4 frotte contre le 3. Il retarde volontairement la stabilité et crée une tension très expressive.",
        "listen": "Compare 4→3 pour la détente et 4→5 pour relancer la phrase.",
        "orientation": "3→4→3 pour sentir la suspension ; 3→4→5 pour créer une poussée.",
        "fill": "rgb(255,247,229)",
        "accent": "rgb(175,112,34)",
    },
    "min1345": {
        "theme": "Ancrage blues et rock",
        "feeling": "Le 4 épaissit la couleur mineure et construit déjà le noyau de la pentatonique mineure.",
        "listen": "Fais 4→b3 pour assombrir, puis 4→5 pour remettre la phrase en mouvement.",
        "orientation": "b3→4→5 pour monter ; 5→4→b3 pour retomber dans la couleur mineure.",
        "fill": "rgb(248,239,239)",
        "accent": "rgb(151,69,69)",
    },
    "maj13#45": {
        "theme": "Lumière lydienne",
        "feeling": "Le #4 semble flotter au-dessus de l'accord : couleur moderne, fusion et cinématographique.",
        "listen": "Laisse brièvement entendre #4, puis monte vers 5 pour révéler sa poussée naturelle.",
        "orientation": "3→#4→5 est le trajet principal ; 5→#4→3 permet d'entendre la couleur en descente.",
        "fill": "rgb(244,239,255)",
        "accent": "rgb(113,76,177)",
    },
    "maj+4": {
        "theme": "Pentatonique suspendue",
        "feeling": "Le 4 ajoute une rugosité familière à la pentatonique majeure. La phrase devient plus soul ou rock.",
        "listen": "Ne repose pas longtemps sur 4 : essaie 4→3, puis 4→5.",
        "orientation": "Joue 3→4→3 puis 3→4→5 ; le 4 doit rester une tension mobile.",
        "fill": "rgb(255,247,229)",
        "accent": "rgb(175,112,34)",
    },
    "maj+#4": {
        "theme": "Pentatonique lydienne",
        "feeling": "Le #4 garde la clarté majeure mais ajoute une impression de hauteur, de flottement et de modernité.",
        "listen": "Compare la même phrase avec 4 puis #4 : le #4 doit naturellement appeler 5.",
        "orientation": "Travaille 3→#4→5, puis la descente 5→#4→3 sans t'arrêter sur #4.",
        "fill": "rgb(244,239,255)",
        "accent": "rgb(113,76,177)",
    },
    "maj+7": {
        "theme": "Élégance et aspiration",
        "feeling": "Le 7 donne immédiatement une couleur maj7 : raffinée, calme, jazz et très proche de la tonique.",
        "listen": "Fais durer 7 juste assez pour sentir son attraction, puis résous 7→1.",
        "orientation": "5→7→1 pour l'aspiration ; 1→7→6 pour apprendre à redescendre sans perdre la couleur.",
        "fill": "rgb(238,249,242)",
        "accent": "rgb(55,132,83)",
    },
    "maj+b7": {
        "theme": "Dominante, groove et mouvement",
        "feeling": "Le b7 retire la douceur maj7 et donne une énergie dominante, mixolydienne, blues ou funk.",
        "listen": "Compare 7 et b7 sur la même phrase ; le b7 doit donner envie d'avancer vers un autre accord.",
        "orientation": "6→b7→1 pour monter ; 1→b7→6 pour installer le groove mixolydien.",
        "fill": "rgb(255,242,233)",
        "accent": "rgb(180,92,43)",
    },
    "min+2": {
        "theme": "Respiration et profondeur",
        "feeling": "Le 2 / 9 ouvre la pentatonique mineure sans lui retirer son identité. La ligne devient plus chantante.",
        "listen": "Essaie 2→b3 pour affirmer le mineur et 2→1 pour calmer la phrase.",
        "orientation": "1→2→b3 pour ouvrir la penta ; b3→2→1 pour retrouver son centre.",
        "fill": "rgb(238,247,255)",
        "accent": "rgb(57,116,164)",
    },
    "min+6": {
        "theme": "Mineur dorien, clair et énergique",
        "feeling": "Le 6 naturel éclaire le mineur. Il apporte une couleur dorienne, jazz, funk et moins sombre.",
        "listen": "Compare 6→5 et 6→b7, puis oppose cette couleur au b6 de la fiche suivante.",
        "orientation": "5→6→b7 pour révéler le dorien ; b7→6→5 pour revenir vers un appui solide.",
        "fill": "rgb(234,249,247)",
        "accent": "rgb(38,131,119)",
    },
    "min+b6": {
        "theme": "Mineur naturel, gravité et drame",
        "feeling": "Le b6 assombrit immédiatement la pentatonique : couleur éolienne, profonde, dramatique et cinématique.",
        "listen": "Fais b6→5 et compare directement avec 6→5 pour entendre dorien contre mineur naturel.",
        "orientation": "b7→b6→5 pour la gravité descendante ; 5→b6→b7 pour construire la tension.",
        "fill": "rgb(252,238,242)",
        "accent": "rgb(160,65,95)",
    },
}


def generate_pedagogical_guide(output_path: Path | None = None, try_pdf: bool = True) -> Path:
    """Crée une version A4 impression en 2 pages + PDF fusionné."""
    base_name = "guide_pedagogique_cellules_CAGED_A4_v1_3_2"
    if output_path is None:
        output_path = Path(f"{base_name}.pdf")
    else:
        output_path = Path(output_path)

    page_w = 1240
    page_h = 1754  # ratio A4 portrait
    left = 64
    right = page_w - 64
    content_width = right - left

    page1_svg = output_path.with_name(f"{base_name}_page1.svg")
    page2_svg = output_path.with_name(f"{base_name}_page2.svg")
    page1_pdf = output_path.with_name(f"{base_name}_page1.pdf")
    page2_pdf = output_path.with_name(f"{base_name}_page2.pdf")

    def begin_page(page_no: int) -> tuple[list[str], float]:
        parts = [
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{page_w}" height="{page_h}" viewBox="0 0 {page_w} {page_h}">',
            f'<rect x="0" y="0" width="{page_w}" height="{page_h}" fill="white"/>',
            text_svg(page_w / 2, 54, "Guide d'écoute — Cellules CAGED", size=30, weight=700),
            text_svg(page_w / 2, 86,
                     "Une note nouvelle à la fois, mais toujours une sensation musicale à reconnaître.",
                     size=15, weight=600, color=MUTED),
            text_svg(page_w / 2, 113,
                     "Le but n'est pas seulement de trouver le degré : il faut entendre ce qu'il change et savoir où il veut aller.",
                     size=13.5, weight=500, color=MUTED),
            text_svg(right, 48, f"Page {page_no}/2", size=12, weight=700, anchor="end", color=MUTED),
        ]
        return parts, 140

    def usage_panel(parts: list[str], y: float) -> float:
        h = 136
        parts.append(
            f'<rect x="{left}" y="{y}" width="{content_width}" height="{h}" rx="15" '
            'fill="rgb(249,247,252)" stroke="rgb(210,200,225)" stroke-width="1.4"/>'
        )
        parts.append(text_svg(left + 24, y + 30, "Comment utiliser ce guide", size=19, weight=700, anchor="start"))
        parts.append(
            f'<circle cx="{left + 41}" cy="{y + 65}" r="12" fill="{ADDED_HALO}" '
            f'stroke="{ADDED_STROKE}" stroke-width="3"/>'
        )
        parts.append(text_svg(left + 66, y + 71,
                              "L'anneau violet désigne la seule note nouvelle à mémoriser.",
                              size=14, weight=600, anchor="start"))
        parts.append(text_svg(left + 24, y + 98,
                              "Joue l'accord, ajoute la couleur, écoute la tension, puis applique la résolution proposée.",
                              size=13.5, weight=500, anchor="start", color=MUTED))
        parts.append(text_svg(left + 24, y + 121,
                              "Travaille ensuite l'orientation complète dans les deux sens : montée, descente et point d'arrivée.",
                              size=13.5, weight=600, anchor="start", color=ADDED_STROKE))
        return y + h + 28

    def section_header(parts: list[str], y: float, title: str, subtitle: str, intro: str) -> float:
        parts.append(text_svg(left, y, title, size=22, weight=700, anchor="start"))
        parts.append(text_svg(right, y, subtitle, size=13, weight=600, anchor="end", color=MUTED))
        y += 26
        parts.append(text_svg(left, y, intro, size=13.5, weight=500, anchor="start", color=MUTED))
        return y + 20

    def lesson_card(parts: list[str], y: float, number: int, profile: LessonProfile) -> float:
        detail = GUIDE_DETAILS[profile.key]
        card_h = 128
        accent = detail["accent"]
        fill = detail["fill"]

        parts.append(
            f'<rect x="{left}" y="{y}" width="{content_width}" height="{card_h}" rx="14" '
            f'fill="{fill}" stroke="rgb(210,210,210)" stroke-width="1.1"/>'
        )
        parts.append(f'<rect x="{left}" y="{y}" width="8" height="{card_h}" rx="4" fill="{accent}"/>')
        parts.append(f'<rect x="{left + 18}" y="{y + 14}" width="24" height="24" fill="white" stroke="rgb(55,55,55)" stroke-width="1.8"/>')
        parts.append(text_svg(left + 55, y + 32, str(number), size=14, weight=700, anchor="start"))
        parts.append(text_svg(left + 86, y + 31, profile.short_title, size=18, weight=700, anchor="start"))

        badge_x = left + 250
        parts.append(
            f'<rect x="{badge_x}" y="{y + 12}" width="118" height="28" rx="14" '
            f'fill="white" stroke="{ADDED_STROKE}" stroke-width="2"/>'
        )
        parts.append(text_svg(badge_x + 59, y + 31,
                              f"Ajout : {profile.added_degree}", size=13, weight=700, color=ADDED_STROKE))
        parts.append(text_svg(left + 385, y + 31, detail["theme"], size=15.5, weight=700,
                              anchor="start", color=accent))
        parts.append(text_svg(right - 16, y + 31, profile.resolution, size=13, weight=700,
                              anchor="end", color=ADDED_STROKE))

        parts.append(text_svg(left + 86, y + 58, "Couleur :", size=13, weight=700, anchor="start"))
        parts.append(text_svg(left + 158, y + 58, detail["feeling"], size=12.5, weight=500,
                              anchor="start", color="rgb(65,65,65)"))
        parts.append(text_svg(left + 86, y + 83, "À écouter :", size=13, weight=700, anchor="start"))
        parts.append(text_svg(left + 172, y + 83, detail["listen"], size=12.5, weight=500,
                              anchor="start", color="rgb(65,65,65)"))
        parts.append(text_svg(left + 86, y + 108, "À maîtriser :", size=13, weight=700, anchor="start", color=ADDED_STROKE))
        parts.append(text_svg(left + 188, y + 108, detail["orientation"], size=12.5, weight=600,
                              anchor="start", color="rgb(65,65,65)"))
        return y + card_h + 10

    def routine_block(parts: list[str], y: float) -> float:
        routine_h = 170
        parts.append(
            f'<rect x="{left}" y="{y}" width="{content_width}" height="{routine_h}" rx="16" '
            'fill="rgb(247,247,247)" stroke="rgb(195,195,195)" stroke-width="1.3"/>'
        )
        parts.append(text_svg(left + 22, y + 30, "Routine courte pour transformer la fiche en musique", size=19, weight=700, anchor="start"))
        routine = [
            "1. Joue l'accord seul et écoute sa stabilité.",
            "2. Ajoute la note violette une seule fois, puis reviens sur une note de l'accord.",
            "3. Répète la résolution indiquée jusqu'à pouvoir la chanter avant de la jouer.",
            "4. Improvise avec quatre ou six notes maximum : pas de gamme automatique.",
            "5. Passe à la forme CAGED suivante seulement quand la couleur reste reconnaissable.",
        ]
        for i, line in enumerate(routine):
            parts.append(text_svg(left + 22, y + 58 + i * 22, line, size=13, weight=500, anchor="start"))
        return y + routine_h + 18

    def next_session_block(parts: list[str], y: float) -> float:
        parts.append(text_svg(left, y, "Prochaine séance", size=19, weight=700, anchor="start"))
        parts.append(text_svg(left, y + 32, "Couleur choisie :", size=14, weight=600, anchor="start"))
        parts.append(f'<line x1="{left + 155}" y1="{y + 36}" x2="{right}" y2="{y + 36}" stroke="rgb(60,60,60)" stroke-width="1.2"/>')
        parts.append(text_svg(left, y + 66, "Ce que j'entends réellement :", size=14, weight=600, anchor="start"))
        parts.append(f'<line x1="{left + 235}" y1="{y + 70}" x2="{right}" y2="{y + 70}" stroke="rgb(60,60,60)" stroke-width="1.2"/>')
        parts.append(text_svg(left, y + 100, "Forme CAGED à reprendre :", size=14, weight=600, anchor="start"))
        parts.append(f'<line x1="{left + 225}" y1="{y + 104}" x2="{right}" y2="{y + 104}" stroke="rgb(60,60,60)" stroke-width="1.2"/>')
        return y + 126

    def close_page(parts: list[str]) -> str:
        parts.append(text_svg(page_w / 2, page_h - 24,
                              f"{SCRIPT_NAME} v{GENERATOR_VERSION} — empreinte {script_fingerprint()}",
                              size=10, color="rgb(145,145,145)"))
        parts.append("</svg>")
        return "\n".join(parts)

    # Page 1
    parts1, y1 = begin_page(1)
    y1 = usage_panel(parts1, y1)
    y1 = section_header(parts1, y1,
                        "A — Construire la couleur autour de l'accord",
                        "Accord CAGED + une seule note",
                        "Travaille les fiches par paires majeur / mineur : même degré ajouté, sensation différente.")
    for number, key in enumerate(CELL_LEARNING_ORDER, start=1):
        y1 = lesson_card(parts1, y1, number, CELL_PROFILES[key])
    page1_svg.write_text(close_page(parts1), encoding="utf-8")

    # Page 2
    parts2, y2 = begin_page(2)
    y2 = section_header(parts2, y2,
                        "B — Enrichir une pentatonique déjà maîtrisée",
                        "Pentatonique + une note de caractère",
                        "Ici, la pentatonique reste la maison ; la note ajoutée change la lumière de la pièce.")
    start_num = len(CELL_LEARNING_ORDER) + 1
    for offset, key in enumerate(PENTA_LEARNING_ORDER, start=0):
        y2 = lesson_card(parts2, y2, start_num + offset, PENTA_PROFILES[key])
    y2 = routine_block(parts2, y2 + 6)
    y2 = next_session_block(parts2, y2)
    page2_svg.write_text(close_page(parts2), encoding="utf-8")

    # Version imprimable sans dépendance : un fichier HTML contenant deux pages A4.
    html_path = output_path.with_name(f"{base_name}.html")
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Guide d'écoute — Cellules CAGED</title>
<style>
  @page {{ size: A4 portrait; margin: 0; }}
  html, body {{ margin: 0; padding: 0; background: #ddd; }}
  .page {{ width: 210mm; height: 297mm; margin: 0 auto; page-break-after: always; background: white; overflow: hidden; }}
  .page:last-child {{ page-break-after: auto; }}
  .page img {{ display: block; width: 210mm; height: 297mm; }}
  @media print {{ body {{ background: white; }} .page {{ margin: 0; }} }}
</style>
</head>
<body>
  <div class="page"><img src="{page1_svg.name}" alt="Guide CAGED page 1"></div>
  <div class="page"><img src="{page2_svg.name}" alt="Guide CAGED page 2"></div>
</body>
</html>
"""
    html_path.write_text(html, encoding="utf-8")

    if not try_pdf:
        return html_path

    # PDF fusionné optionnel. L'absence des modules ne bloque plus le script.
    try:
        import cairosvg
        from pypdf import PdfWriter
    except ModuleNotFoundError:
        print("\nPDF non créé : modules optionnels absents (cairosvg et/ou pypdf).")
        print(f"Guide A4 créé sans dépendance : {html_path}")
        print("Ouvre ce fichier dans ton navigateur puis imprime à 100 %, sans marges.")
        return html_path

    cairosvg.svg2pdf(url=str(page1_svg), write_to=str(page1_pdf))
    cairosvg.svg2pdf(url=str(page2_svg), write_to=str(page2_pdf))
    writer = PdfWriter()
    writer.append(str(page1_pdf))
    writer.append(str(page2_pdf))
    with output_path.open("wb") as f:
        writer.write(f)

    return output_path


# -----------------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------------
def validate_templates() -> None:
    for quality in ("majeur", "mineur"):
        for root_pc in range(12):
            chord_degrees = {"majeur": {0, 4, 7}, "mineur": {0, 3, 7}}[quality]
            for shape in SHAPES:
                template = CHORD_TEMPLATES[quality][shape]
                if len(template) != 6:
                    raise AssertionError(f"Template invalide : {quality}/{shape}")
                start = shape_start(root_pc, shape)
                found = set()
                for string_index, offset in enumerate(template):
                    if offset is None:
                        continue
                    fret = start + offset
                    interval = ((TUNING_PCS[string_index] + fret) - root_pc) % 12
                    if interval not in chord_degrees:
                        raise AssertionError(f"Note étrangère : {quality}/{shape}/{root_pc}")
                    found.add(interval)
                if found != chord_degrees:
                    raise AssertionError(f"Triade incomplète : {quality}/{shape}/{root_pc} : {found}")


def validate_profiles() -> None:
    for profile in ALL_PROFILES.values():
        if profile.added_degree not in profile.formula:
            raise AssertionError(f"Note ajoutée absente : {profile.key}")
        if not set(profile.base_formula).issubset(profile.formula):
            raise AssertionError(f"Base absente de la formule : {profile.key}")
        if profile.added_degree in profile.base_formula:
            raise AssertionError(f"La note ajoutée appartient déjà à la base : {profile.key}")
        if profile.quality == "majeur" and "3" not in profile.formula:
            raise AssertionError(f"Tierce majeure absente : {profile.key}")
        if profile.quality == "mineur" and "b3" not in profile.formula:
            raise AssertionError(f"Tierce mineure absente : {profile.key}")

        for root_pc in range(12):
            # Chaque forme doit afficher au moins une occurrence de la note ajoutée.
            root_names = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
            root = root_names[root_pc]
            for shape in SHAPES:
                spots = spots_for_shape(root, root_pc, profile, shape)
                if not any(s.added for s in spots):
                    raise AssertionError(f"Note ajoutée absente de la fenêtre : {profile.key}/{root}/{shape}")
                exact = [s for s in spots if s.exact_chord]
                # Certaines notes exactes peuvent être hors fenêtre uniquement si la fenêtre était mal définie.
                expected = exact_positions(root_pc, profile.quality, shape)
                if { (s.string_index, s.fret) for s in exact } != expected:
                    raise AssertionError(f"Forme exacte tronquée : {profile.key}/{root}/{shape}")


def validate_spelling() -> None:
    checks = {
        ("F#", "7"): "E#",
        ("Gb", "7"): "F",
        ("Bb", "b3"): "Db",
        ("C#", "#4"): "F##",
        ("A", "b6"): "F",
    }
    for (root, degree), expected in checks.items():
        actual = note_for_degree(root, degree)
        if actual != expected:
            raise AssertionError(f"Orthographe {root}/{degree} : {actual} au lieu de {expected}")


def validate_svg() -> None:
    temp = Path("/tmp/__cellules_caged_test.svg")
    generate_svg("A", pitch_class("A"), CELL_PROFILES["min1235"], "mixte", temp)
    svg = temp.read_text(encoding="utf-8")
    temp.unlink(missing_ok=True)
    required = [
        "Forme C", "Forme A", "Forme G", "Forme E", "Forme D",
        "Ordre géographique réel", "Anneau violet", "forme d’accord",
        "Routine", "297mm", "A4 landscape", f"v{GENERATOR_VERSION}", script_fingerprint(),
    ]
    missing = [item for item in required if item not in svg]
    if missing:
        raise AssertionError(f"Éléments SVG manquants : {missing}")

    # Vérifie l'ordre visuel des cordes : 1E, 2B, 3G, 4D, 5A, 6E.
    expected_labels = ["1 E", "2 B", "3 G", "4 D", "5 A", "6 E"]
    first_card = svg[svg.find("Forme C"):svg.find("Forme A")]
    positions = [first_card.find(label) for label in expected_labels]
    if any(pos < 0 for pos in positions) or positions != sorted(positions):
        raise AssertionError("Ordre visuel des cordes incorrect")


def validate_guide() -> None:
    temp = Path("/tmp/__cellules_caged_guide_test.pdf")
    generate_pedagogical_guide(temp, try_pdf=False)
    page1 = temp.with_name("guide_pedagogique_cellules_CAGED_A4_v1_3_2_page1.svg")
    page2 = temp.with_name("guide_pedagogique_cellules_CAGED_A4_v1_3_2_page2.svg")
    svg1 = page1.read_text(encoding="utf-8")
    svg2 = page2.read_text(encoding="utf-8")
    required1 = [
        "Guide d'écoute — Cellules CAGED",
        "Comment utiliser ce guide",
        "A — Construire la couleur autour de l'accord",
        "Air et ouverture",
        "À maîtriser :",
        "1→2→3 pour ouvrir",
        "Page 1/2",
        f"v{GENERATOR_VERSION}",
        script_fingerprint(),
    ]
    required2 = [
        "B — Enrichir une pentatonique déjà maîtrisée",
        "Routine courte pour transformer la fiche en musique",
        "Prochaine séance",
        "mineur naturel",
        "Page 2/2",
    ]
    missing = [item for item in required1 if item not in svg1] + [item for item in required2 if item not in svg2]
    if missing:
        raise AssertionError(f"Éléments du guide manquants : {missing}")
    for p in [
        temp, page1, page2,
        temp.with_name("guide_pedagogique_cellules_CAGED_A4_v1_3_2_page1.pdf"),
        temp.with_name("guide_pedagogique_cellules_CAGED_A4_v1_3_2_page2.pdf"),
        temp.with_name("guide_pedagogique_cellules_CAGED_A4_v1_3_1.html"),
    ]:
        p.unlink(missing_ok=True)


def run_all_validations() -> None:
    validate_templates()
    validate_profiles()
    validate_spelling()
    validate_svg()
    validate_guide()


# -----------------------------------------------------------------------------
# Interface
# -----------------------------------------------------------------------------
def normalize_module(value: str) -> str:
    cleaned = strip_accents(value.strip().lower()).replace(" ", "")
    aliases = {"1": "cellule", "cellule": "cellule", "cellules": "cellule",
               "2": "penta", "penta": "penta", "pentatonique": "penta"}
    if cleaned not in aliases:
        raise ValueError("Choisis cellule ou penta.")
    return aliases[cleaned]


def normalize_profile(value: str, module: str) -> str:
    cleaned = strip_accents(value.strip().lower()).replace(" ", "")

    all_aliases = {"toutes", "tous", "tout", "all", "*"}
    if cleaned in all_aliases:
        return "toutes"
    if module == "cellule" and cleaned == "6":
        return "toutes"
    if module == "penta" and cleaned == "8":
        return "toutes"

    aliases = {
        "maj1235": "maj1235", "majeur1235": "maj1235", "1": "maj1235",
        "m1235": "min1235", "min1235": "min1235", "mineur1235": "min1235", "2": "min1235",
        "maj1345": "maj1345", "majeur1345": "maj1345", "3": "maj1345",
        "m1345": "min1345", "min1345": "min1345", "mineur1345": "min1345", "4": "min1345",
        "maj13#45": "maj13#45", "majeur13#45": "maj13#45", "5": "maj13#45",
        "maj+4": "maj+4", "majeure+4": "maj+4",
        "maj+#4": "maj+#4", "majeure+#4": "maj+#4",
        "maj+7": "maj+7", "majeure+7": "maj+7",
        "maj+b7": "maj+b7", "majeure+b7": "maj+b7",
        "min+2": "min+2", "m+2": "min+2", "mineure+2": "min+2",
        "min+6": "min+6", "m+6": "min+6", "mineure+6": "min+6",
        "min+b6": "min+b6", "m+b6": "min+b6", "mineure+b6": "min+b6",
    }
    if module == "penta":
        aliases.update({"1": "maj+4", "2": "maj+#4", "3": "maj+7", "4": "maj+b7",
                        "5": "min+2", "6": "min+6", "7": "min+b6"})
    key = aliases.get(cleaned)
    allowed = CELL_PROFILES if module == "cellule" else PENTA_PROFILES
    if key not in allowed:
        raise ValueError("Formule inconnue pour ce module.")
    return key


def normalize_labels(value: str) -> str:
    cleaned = strip_accents(value.strip().lower()).replace(" ", "")
    aliases = {"1": "degres", "degre": "degres", "degres": "degres",
               "2": "notes", "note": "notes", "notes": "notes",
               "3": "mixte", "mixte": "mixte"}
    if cleaned not in aliases:
        raise ValueError("Choisis degrés, notes ou mixte.")
    return aliases[cleaned]


def normalize_yes_no(value: str) -> bool:
    cleaned = strip_accents(value.strip().lower())
    if cleaned in {"", "n", "non", "no"}:
        return False
    if cleaned in {"o", "oui", "y", "yes"}:
        return True
    raise ValueError("Réponds O pour oui ou N pour non.")


def ask_until(prompt: str, normalizer):
    while True:
        try:
            return normalizer(input(prompt))
        except ValueError as error:
            print(f"Erreur : {error}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Génère des fiches de cellules CAGED compactes.")
    parser.add_argument("--tonalite", help="Ex. A, F#, Bb, Ré")
    parser.add_argument("--module", help="cellule ou penta")
    parser.add_argument("--formule", help="Ex. maj1235, min1345, maj+#4, min+6")
    parser.add_argument("--etiquettes", default="degres", help="degres, notes ou mixte")
    parser.add_argument("--sortie", help="Chemin du SVG")
    parser.add_argument("--lot", choices=["cellules", "penta", "tout"], help="Génère une série complète")
    parser.add_argument("--guide", action="store_true", help="Crée uniquement le guide pédagogique puis s'arrête")
    parser.add_argument("--test", action="store_true")
    return parser.parse_args()


def generate_lot(root: str, root_pc: int, lot: str, label_mode: str) -> list[Path]:
    if lot == "cellules":
        profiles = [CELL_PROFILES[key] for key in CELL_LEARNING_ORDER]
    elif lot == "penta":
        profiles = [PENTA_PROFILES[key] for key in PENTA_LEARNING_ORDER]
    else:
        profiles = [CELL_PROFILES[key] for key in CELL_LEARNING_ORDER] + [PENTA_PROFILES[key] for key in PENTA_LEARNING_ORDER]
    return [generate_svg(root, root_pc, profile, label_mode) for profile in profiles]


def main() -> None:
    args = parse_args()
    run_all_validations()

    if args.test:
        print("Validation réussie : formes CAGED, 12 fondamentales, 12 profils, orthographes, géométrie et pédagogie cohérentes.")
        print(f"Version {GENERATOR_VERSION} — empreinte {script_fingerprint()}")
        return

    # Mode explicite par option : ne pose aucune autre question.
    if args.guide:
        result = generate_pedagogical_guide()
        print(f"Guide pédagogique généré : {result}")
        print(f"Version {GENERATOR_VERSION} — empreinte {script_fingerprint()}")
        return

    # En lancement interactif pur, le guide est proposé avant toute autre question.
    interactive_start = not any((args.tonalite, args.module, args.formule, args.lot, args.sortie))
    if interactive_start:
        guide_only = ask_until(
            "Impression du guide pédagogique ? [o/N] : ",
            normalize_yes_no,
        )
        if guide_only:
            result = generate_pedagogical_guide()
            print(f"\nGuide pédagogique généré : {result}")
            print("Aucune fiche d'exercice n'a été créée.")
            print(f"Version {GENERATOR_VERSION} — empreinte {script_fingerprint()}")
            return

    if args.tonalite:
        root, root_pc = normalize_root(args.tonalite)
    else:
        root, root_pc = ask_until("Fondamentale (ex. A, F#, Bb, Ré) : ", normalize_root)

    label_mode = normalize_labels(args.etiquettes or "degres")

    if args.lot:
        results = generate_lot(root, root_pc, args.lot, label_mode)
        print("\nFichiers générés :")
        for result in results:
            print(f"- {result}")
        print(f"Version {GENERATOR_VERSION} — empreinte {script_fingerprint()}")
        return

    if args.module:
        module = normalize_module(args.module)
    else:
        module = ask_until("Module [1 cellules, 2 pentatonique enrichie] : ", normalize_module)

    if args.formule:
        profile_key = normalize_profile(args.formule, module)
    elif module == "cellule":
        print("1 Maj1235 | 2 m1235 | 3 Maj1345 | 4 m1345 | 5 Maj13#45 | 6 Toutes")
        profile_key = ask_until("Formule : ", lambda value: normalize_profile(value, module))
    else:
        print("1 Maj+4 | 2 Maj+#4 | 3 Maj+7 | 4 Maj+b7 | 5 m+2 | 6 m+6 | 7 m+b6 | 8 Toutes")
        profile_key = ask_until("Formule : ", lambda value: normalize_profile(value, module))

    if profile_key == "toutes":
        lot = "cellules" if module == "cellule" else "penta"
        results = generate_lot(root, root_pc, lot, label_mode)
        print("\nFichiers générés :")
        for result in results:
            print(f"- {result}")
        print(f"Version {GENERATOR_VERSION} — empreinte {script_fingerprint()}")
        return

    output = Path(args.sortie) if args.sortie else None
    result = generate_svg(root, root_pc, ALL_PROFILES[profile_key], label_mode, output)
    print(f"\nSVG généré : {result}")
    print(f"Version {GENERATOR_VERSION} — empreinte {script_fingerprint()}")


if __name__ == "__main__":
    main()
