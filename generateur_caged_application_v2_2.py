#!/usr/bin/env python3
"""
Générateur pédagogique CAGED V2.1 : CAGED complet -> arpège -> gamme -> liaison.

Le script peut produire :
- une seule transition CAGED ;
- ou les cinq transitions, dans l'ordre réel où elles apparaissent sur le manche.

V2.1 :
- diagramme 1 = CAGED complet avec la forme étudiée mise en évidence ;
- textes pédagogiques renforcés ;
- géométrie du manche verrouillée par des tests automatiques ;
- version et empreinte du script intégrées dans chaque SVG.

Dépendances : bibliothèque standard Python uniquement.

Exemple interactif :
    python generateur_caged_application_v2.py

Exemple direct :
    python generateur_caged_application_v2.py \
        --tonalite G --accord majeur --forme toutes --etiquettes mixte
"""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata
import xml.sax.saxutils as xml_escape


# -----------------------------------------------------------------------------
# Réglages généraux
# -----------------------------------------------------------------------------
GENERATOR_VERSION = "2.2.0"
SCRIPT_NAME = "generateur_caged_application_v2_1.py"

FIRST_FRET = 0
LAST_FRET = 15
STRINGS = ("E", "A", "D", "G", "B", "E")  # cordes 6 -> 1
TUNING_PCS = (4, 9, 2, 7, 11, 4)
SHAPES = ("C", "A", "G", "E", "D")

CANVAS_WIDTH = 1440
LEFT_MARGIN = 155.0
RIGHT_MARGIN = 95.0
OPEN_X = LEFT_MARGIN - 55.0
FRET_WIDTH = (CANVAS_WIDTH - LEFT_MARGIN - RIGHT_MARGIN) / LAST_FRET
BOARD_HEIGHT = 345.0
STRING_TOP = 102.0
STRING_GAP = 38.0

ROOT_COLOR = "rgb(255,145,145)"
THIRD_COLOR = "rgb(255,212,125)"
FIFTH_COLOR = "rgb(150,202,255)"
SEVENTH_COLOR = "rgb(202,175,240)"
OTHER_COLOR = "rgb(235,235,235)"
CURRENT_ZONE_COLOR = "rgb(255,246,214)"
NEXT_ZONE_COLOR = "rgb(229,239,255)"
OVERLAP_ZONE_COLOR = "rgb(222,245,225)"
OVERLAP_STROKE = "rgb(53,133,68)"
PENTA_STROKE = "rgb(108,55,170)"
SELECTED_STROKE = "rgb(34,83,155)"
MUTED_FILL = "rgb(248,248,248)"
MUTED_STROKE = "rgb(150,150,150)"
MUTED_TEXT = "rgb(105,105,105)"

NATURAL_PITCHES = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}
LETTER_ORDER = ("C", "D", "E", "F", "G", "A", "B")

# Fondamentale de chaque accord ouvert servant de matrice au CAGED.
CAGED_OPEN_ROOTS = {
    "C": 0,
    "A": 9,
    "G": 7,
    "E": 4,
    "D": 2,
}

# Voicings de référence, exprimés en décalages de cases par rapport au départ
# de la forme. L'ordre est corde 6 -> corde 1. None = corde non jouée.
CHORD_TEMPLATES: dict[str, dict[str, tuple[int | None, ...]]] = {
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
    "7": {
        "C": (None, 3, 2, 3, 1, 0),
        "A": (None, 0, 2, 0, 2, 0),
        "G": (3, 2, 0, 0, 0, 1),
        "E": (0, 2, 0, 1, 0, 0),
        "D": (None, None, 0, 2, 1, 2),
    },
    "maj7": {
        "C": (None, 3, 2, 0, 0, 0),
        "A": (None, 0, 2, 1, 2, 0),
        "G": (3, 2, 0, 0, 0, 2),
        "E": (0, 2, 1, 1, 0, 0),
        "D": (None, None, 0, 2, 2, 2),
    },
    "m7": {
        "C": (None, 3, 1, 3, 1, None),
        "A": (None, 0, 2, 0, 1, 0),
        "G": (3, 1, 0, 0, 3, 1),
        "E": (0, 2, 0, 0, 0, 0),
        "D": (None, None, 0, 2, 1, 1),
    },
}


@dataclass(frozen=True)
class Profile:
    key: str
    title: str
    chord_intervals: tuple[int, ...]
    chord_degrees: tuple[str, ...]
    scale_intervals: tuple[int, ...]
    scale_degrees: tuple[str, ...]
    mode_name: str


PROFILES: dict[str, Profile] = {
    "majeur": Profile(
        key="majeur",
        title="majeur",
        chord_intervals=(0, 4, 7),
        chord_degrees=("1", "3", "5"),
        scale_intervals=(0, 2, 4, 5, 7, 9, 11),
        scale_degrees=("1", "2", "3", "4", "5", "6", "7"),
        mode_name="gamme majeure / mode ionien",
    ),
    "mineur": Profile(
        key="mineur",
        title="mineur",
        chord_intervals=(0, 3, 7),
        chord_degrees=("1", "b3", "5"),
        scale_intervals=(0, 2, 3, 5, 7, 8, 10),
        scale_degrees=("1", "2", "b3", "4", "5", "b6", "b7"),
        mode_name="gamme mineure naturelle / mode éolien",
    ),
    "7": Profile(
        key="7",
        title="7 (dominante)",
        chord_intervals=(0, 4, 7, 10),
        chord_degrees=("1", "3", "5", "b7"),
        scale_intervals=(0, 2, 4, 5, 7, 9, 10),
        scale_degrees=("1", "2", "3", "4", "5", "6", "b7"),
        mode_name="mode mixolydien",
    ),
    "maj7": Profile(
        key="maj7",
        title="maj7",
        chord_intervals=(0, 4, 7, 11),
        chord_degrees=("1", "3", "5", "7"),
        scale_intervals=(0, 2, 4, 5, 7, 9, 11),
        scale_degrees=("1", "2", "3", "4", "5", "6", "7"),
        mode_name="gamme majeure / mode ionien",
    ),
    "m7": Profile(
        key="m7",
        title="m7",
        chord_intervals=(0, 3, 7, 10),
        chord_degrees=("1", "b3", "5", "b7"),
        scale_intervals=(0, 2, 3, 5, 7, 8, 10),
        scale_degrees=("1", "2", "b3", "4", "5", "b6", "b7"),
        mode_name="gamme mineure naturelle / mode éolien",
    ),
}


@dataclass(frozen=True)
class ShapeContext:
    shape: str
    start: int
    next_shape: str
    next_start: int
    next_next_shape: str
    next_next_start: int

    @property
    def current_zone(self) -> tuple[int, int]:
        return max(FIRST_FRET, self.start), min(LAST_FRET, self.next_start + 2)

    @property
    def next_zone(self) -> tuple[int, int]:
        return max(FIRST_FRET, self.next_start), min(LAST_FRET, self.next_next_start + 2)

    @property
    def overlap_zone(self) -> tuple[int, int] | None:
        start = max(self.current_zone[0], self.next_zone[0])
        end = min(self.current_zone[1], self.next_zone[1])
        return (start, end) if start <= end else None


@dataclass(frozen=True)
class NoteSpot:
    string_index: int  # 0 = corde 6, 5 = corde 1
    fret: int
    note: str
    degree: str
    exact: bool = False
    transition: bool = False
    muted: bool = False
    pentatonic: bool = False


# -----------------------------------------------------------------------------
# Tonalités et orthographe musicale
# -----------------------------------------------------------------------------
def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def pitch_class(note: str) -> int:
    letter = note[0].upper()
    if letter not in NATURAL_PITCHES:
        raise ValueError(f"Note invalide : {note}")
    accidental = note[1:]
    offset = accidental.count("#") - accidental.count("b")
    return (NATURAL_PITCHES[letter] + offset) % 12


def normalize_root(user_input: str) -> tuple[str, int]:
    cleaned = (
        user_input.strip()
        .replace("♯", "#")
        .replace("♭", "b")
        .replace(" ", "")
    )
    if not cleaned:
        raise ValueError("Aucune tonalité saisie.")

    ascii_cleaned = strip_accents(cleaned).lower()
    french_match = re.fullmatch(r"(do|re|mi|fa|sol|la|si)([#b]{0,3})", ascii_cleaned)
    if french_match:
        french_name, accidental = french_match.groups()
        letter = {
            "do": "C",
            "re": "D",
            "mi": "E",
            "fa": "F",
            "sol": "G",
            "la": "A",
            "si": "B",
        }[french_name]
        root = letter + accidental
    else:
        international_match = re.fullmatch(r"([a-g])([#b]{0,3})", ascii_cleaned)
        if not international_match:
            raise ValueError(
                f"Tonalité inconnue : {user_input}. Exemples : G, F#, Bb, Ré, Sib."
            )
        letter, accidental = international_match.groups()
        root = letter.upper() + accidental

    return root, pitch_class(root)


def accidental_for_delta(delta: int) -> str:
    if delta > 0:
        return "#" * delta
    if delta < 0:
        return "b" * (-delta)
    return ""


def build_spelled_scale(root: str, intervals: tuple[int, ...]) -> list[str]:
    """Construit une gamme avec une lettre différente pour chaque degré."""
    root_pc = pitch_class(root)
    root_letter_index = LETTER_ORDER.index(root[0].upper())
    notes: list[str] = []

    for degree_index, interval in enumerate(intervals):
        letter = LETTER_ORDER[(root_letter_index + degree_index) % 7]
        target_pc = (root_pc + interval) % 12
        natural_pc = NATURAL_PITCHES[letter]
        delta = (target_pc - natural_pc) % 12
        if delta > 6:
            delta -= 12
        notes.append(letter + accidental_for_delta(delta))

    return notes


# -----------------------------------------------------------------------------
# CAGED : ordre et zones
# -----------------------------------------------------------------------------
def shape_start(root_pc: int, shape: str) -> int:
    return (root_pc - CAGED_OPEN_ROOTS[shape]) % 12


def all_occurrences(root_pc: int) -> list[tuple[int, str]]:
    occurrences: list[tuple[int, str]] = []
    for shape in SHAPES:
        base = shape_start(root_pc, shape)
        for octave in range(-2, 4):
            occurrences.append((base + 12 * octave, shape))
    return sorted(occurrences, key=lambda item: (item[0], SHAPES.index(item[1])))


def shape_context(root_pc: int, shape: str) -> ShapeContext:
    current_start = shape_start(root_pc, shape)
    occurrences = all_occurrences(root_pc)

    current_index = next(
        index
        for index, item in enumerate(occurrences)
        if item == (current_start, shape)
    )
    next_start, next_shape = occurrences[current_index + 1]
    next_next_start, next_next_shape = occurrences[current_index + 2]

    return ShapeContext(
        shape=shape,
        start=current_start,
        next_shape=next_shape,
        next_start=next_start,
        next_next_shape=next_next_shape,
        next_next_start=next_next_start,
    )


def ordered_contexts(root_pc: int) -> list[ShapeContext]:
    visible_starts = sorted(
        ((shape_start(root_pc, shape), shape) for shape in SHAPES),
        key=lambda item: item[0],
    )
    return [shape_context(root_pc, shape) for _, shape in visible_starts]


# -----------------------------------------------------------------------------
# Création des notes à afficher
# -----------------------------------------------------------------------------
def pentatonic_intervals_and_degrees(profile: Profile) -> tuple[tuple[int, ...], tuple[str, ...]]:
    """Retourne la pentatonique de référence à l'intérieur de la gamme affichée.

    - majeur / maj7 / 7 : pentatonique majeure (1 2 3 5 6)
    - mineur / m7       : pentatonique mineure (1 b3 4 5 b7)
    """
    if profile.key in {"mineur", "m7"}:
        return (0, 3, 5, 7, 10), ("1", "b3", "4", "5", "b7")
    return (0, 2, 4, 7, 9), ("1", "2", "3", "5", "6")


def scale_maps(
    root_pc: int,
    profile: Profile,
    spelled_notes: list[str],
) -> tuple[dict[int, str], dict[int, str]]:
    degree_by_interval = dict(zip(profile.scale_intervals, profile.scale_degrees))
    note_by_pc = {
        (root_pc + interval) % 12: note
        for interval, note in zip(profile.scale_intervals, spelled_notes)
    }
    return degree_by_interval, note_by_pc


def spots_in_range(
    *,
    root_pc: int,
    intervals: tuple[int, ...],
    degrees: tuple[str, ...],
    note_by_pc: dict[int, str],
    fret_start: int,
    fret_end: int,
    transition_zone: tuple[int, int] | None = None,
) -> list[NoteSpot]:
    degree_by_interval = dict(zip(intervals, degrees))
    spots: list[NoteSpot] = []

    for string_index, open_pc in enumerate(TUNING_PCS):
        for fret in range(max(FIRST_FRET, fret_start), min(LAST_FRET, fret_end) + 1):
            pc = (open_pc + fret) % 12
            interval = (pc - root_pc) % 12
            if interval not in degree_by_interval:
                continue
            transition = bool(
                transition_zone
                and transition_zone[0] <= fret <= transition_zone[1]
            )
            spots.append(
                NoteSpot(
                    string_index=string_index,
                    fret=fret,
                    note=note_by_pc[pc],
                    degree=degree_by_interval[interval],
                    transition=transition,
                )
            )
    return spots


def chord_spots_at(
    *,
    root_pc: int,
    profile: Profile,
    spelled_notes: list[str],
    shape: str,
    start: int,
    selected: bool,
    muted: bool,
) -> list[NoteSpot]:
    """Notes exactes d'un voicing CAGED à une position donnée."""
    _, note_by_pc = scale_maps(root_pc, profile, spelled_notes)
    degree_by_interval = dict(zip(profile.chord_intervals, profile.chord_degrees))
    template = CHORD_TEMPLATES[profile.key][shape]
    spots: list[NoteSpot] = []

    for string_index, offset in enumerate(template):
        if offset is None:
            continue
        fret = start + offset
        if not FIRST_FRET <= fret <= LAST_FRET:
            continue
        pc = (TUNING_PCS[string_index] + fret) % 12
        interval = (pc - root_pc) % 12
        spots.append(
            NoteSpot(
                string_index=string_index,
                fret=fret,
                note=note_by_pc[pc],
                degree=degree_by_interval[interval],
                exact=selected,
                muted=muted,
            )
        )
    return spots


def exact_chord_spots(
    *,
    root_pc: int,
    profile: Profile,
    spelled_notes: list[str],
    context: ShapeContext,
) -> list[NoteSpot]:
    return chord_spots_at(
        root_pc=root_pc,
        profile=profile,
        spelled_notes=spelled_notes,
        shape=context.shape,
        start=context.start,
        selected=True,
        muted=False,
    )


def full_caged_chord_spots(
    *,
    root_pc: int,
    profile: Profile,
    spelled_notes: list[str],
    context: ShapeContext,
) -> tuple[list[NoteSpot], list[tuple[str, float, bool]]]:
    """Affiche le réseau complet des notes de l'accord sur tout le manche.

    Le diagramme 1 doit montrer toutes les occurrences des degrés de l'accord
    (par exemple 1 / b3 / 5 pour un accord mineur), pas uniquement les cordes
    réellement jouées dans les cinq voicings. Les notes exactes de la forme
    étudiée sont ensuite superposées avec un contour bleu épais.

    Ainsi, sur la corde de mi grave d'un Am, on voit bien A case 5, C case 8
    et E case 12 dans la limite du manche affiché.
    """
    _, note_by_pc = scale_maps(root_pc, profile, spelled_notes)

    # 1) Réseau complet des notes de l'accord sur les six cordes.
    network = spots_in_range(
        root_pc=root_pc,
        intervals=profile.chord_intervals,
        degrees=profile.chord_degrees,
        note_by_pc=note_by_pc,
        fret_start=FIRST_FRET,
        fret_end=LAST_FRET,
    )
    merged: dict[tuple[int, int], NoteSpot] = {
        (spot.string_index, spot.fret): NoteSpot(
            string_index=spot.string_index,
            fret=spot.fret,
            note=spot.note,
            degree=spot.degree,
            muted=True,
        )
        for spot in network
    }

    # 2) Repères des différentes formes CAGED sur le manche.
    labels: list[tuple[str, float, bool]] = []
    for start, shape in all_occurrences(root_pc):
        occurrence_spots = chord_spots_at(
            root_pc=root_pc,
            profile=profile,
            spelled_notes=spelled_notes,
            shape=shape,
            start=start,
            selected=False,
            muted=True,
        )
        if not occurrence_spots:
            continue
        frets = [spot.fret for spot in occurrence_spots]
        selected = shape == context.shape and start == context.start
        labels.append((f"Forme {shape}", (min(frets) + max(frets)) / 2, selected))

    # 3) Forme exacte étudiée, prioritaire et mise en évidence.
    selected_spots = chord_spots_at(
        root_pc=root_pc,
        profile=profile,
        spelled_notes=spelled_notes,
        shape=context.shape,
        start=context.start,
        selected=True,
        muted=False,
    )
    for spot in selected_spots:
        merged[(spot.string_index, spot.fret)] = spot

    spots = sorted(merged.values(), key=lambda item: (item.fret, item.string_index))
    labels.sort(key=lambda item: item[1])
    return spots, labels


# -----------------------------------------------------------------------------
# SVG
# -----------------------------------------------------------------------------
def esc(text: str) -> str:
    return xml_escape.escape(str(text))


def text_svg(
    x: float,
    y: float,
    text: str,
    *,
    size: int,
    weight: int = 400,
    anchor: str = "middle",
    color: str = "rgb(35,35,35)",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{color}">'
        f'{esc(text)}</text>'
    )


def fret_x(fret: int) -> float:
    if fret == 0:
        return OPEN_X
    return LEFT_MARGIN + (fret - 0.5) * FRET_WIDTH


def string_y(string_index: int) -> float:
    """Position verticale : corde 1 en haut, corde 6 en bas."""
    return STRING_TOP + (5 - string_index) * STRING_GAP


def visual_board_bounds() -> tuple[float, float]:
    """Bornes communes au sillet et aux frettes."""
    top = min(string_y(index) for index in range(6)) - 13
    bottom = max(string_y(index) for index in range(6)) + 13
    return top, bottom


def range_left(fret: int) -> float:
    if fret <= 0:
        return OPEN_X - 29
    return LEFT_MARGIN + (fret - 1) * FRET_WIDTH


def range_right(fret: int) -> float:
    if fret <= 0:
        return OPEN_X + 29
    return LEFT_MARGIN + fret * FRET_WIDTH


def degree_color(degree: str) -> str:
    if degree == "1":
        return ROOT_COLOR
    if "3" in degree:
        return THIRD_COLOR
    if "5" in degree:
        return FIFTH_COLOR
    if "7" in degree:
        return SEVENTH_COLOR
    return OTHER_COLOR


def zone_rect(
    zone: tuple[int, int],
    *,
    color: str,
    opacity: float,
) -> str:
    x = range_left(zone[0])
    width = range_right(zone[1]) - x
    return (
        f'<rect x="{x:.1f}" y="67" width="{width:.1f}" height="226" '
        f'rx="9" fill="{color}" fill-opacity="{opacity}"/>'
    )


def render_note(spot: NoteSpot, label_mode: str) -> str:
    """Dessine une pastille de taille constante.

    La hiérarchie visuelle repose uniquement sur le contour :
    - bleu épais : forme CAGED étudiée ;
    - vert épais : note située dans la zone géographique commune ;
    - gris : autres formes du CAGED complet ;
    - noir fin : note ordinaire.
    """
    x = fret_x(spot.fret)
    y = string_y(spot.string_index)
    radius = 19

    if spot.transition:
        stroke = OVERLAP_STROKE
        stroke_width = 4.5
    elif spot.exact:
        stroke = SELECTED_STROKE
        stroke_width = 4.2
    elif spot.muted:
        stroke = MUTED_STROKE
        stroke_width = 1.8
    else:
        stroke = "rgb(35,35,35)"
        stroke_width = 2.2

    fill = MUTED_FILL if spot.muted else degree_color(spot.degree)
    text_color = MUTED_TEXT if spot.muted else "rgb(35,35,35)"

    fragments = []

    if spot.pentatonic:
        fragments.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius + 6.5:.1f}" fill="none" '
            f'stroke="{PENTA_STROKE}" stroke-width="3.2" stroke-dasharray="4 3"/>'
        )

    fragments.append(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{stroke_width}"/>'
    )

    if label_mode == "degres":
        fragments.append(text_svg(x, y + 5, spot.degree, size=15, weight=700, color=text_color))
    elif label_mode == "notes":
        fragments.append(text_svg(x, y + 5, spot.note, size=14, weight=700, color=text_color))
    else:
        fragments.append(text_svg(x, y - 1, spot.degree, size=13, weight=700, color=text_color))
        fragments.append(text_svg(x, y + 13, spot.note, size=10, weight=600, color=text_color))

    return "".join(fragments)

def render_board(
    *,
    y_offset: float,
    title: str,
    subtitle: str,
    spots: list[NoteSpot],
    label_mode: str,
    current_zone: tuple[int, int] | None = None,
    current_label: str | None = None,
    next_zone: tuple[int, int] | None = None,
    next_label: str | None = None,
    overlap_zone: tuple[int, int] | None = None,
    shape_labels: list[tuple[str, float, bool]] | None = None,
) -> str:
    fragments: list[str] = [f'<g transform="translate(0,{y_offset:.1f})">']
    fragments.append(text_svg(CANVAS_WIDTH / 2, 25, title, size=21, weight=700))
    fragments.append(
        text_svg(
            CANVAS_WIDTH / 2,
            49,
            subtitle,
            size=14,
            weight=500,
            color="rgb(75,75,75)",
        )
    )

    if current_zone:
        fragments.append(zone_rect(current_zone, color=CURRENT_ZONE_COLOR, opacity=0.82))
    if next_zone:
        fragments.append(zone_rect(next_zone, color=NEXT_ZONE_COLOR, opacity=0.63))
    if overlap_zone:
        fragments.append(zone_rect(overlap_zone, color=OVERLAP_ZONE_COLOR, opacity=0.96))

    if current_zone and current_label:
        x = (range_left(current_zone[0]) + range_right(current_zone[1])) / 2
        fragments.append(text_svg(x, 84, current_label, size=13, weight=700))
    if next_zone and next_label:
        x = (range_left(next_zone[0]) + range_right(next_zone[1])) / 2
        fragments.append(text_svg(x, 84, next_label, size=13, weight=700))

    if shape_labels:
        for label, center_fret, selected in shape_labels:
            x = fret_x(int(round(center_fret))) if center_fret <= 0 else LEFT_MARGIN + (center_fret - 0.5) * FRET_WIDTH
            fragments.append(
                text_svg(
                    x,
                    84,
                    label,
                    size=13,
                    weight=800 if selected else 600,
                    color=SELECTED_STROKE if selected else MUTED_TEXT,
                )
            )

    # Cordes et accordage : corde 1 en haut, corde 6 en bas.
    string_end_x = LEFT_MARGIN + LAST_FRET * FRET_WIDTH
    for index, tuning in enumerate(STRINGS):
        y = string_y(index)
        width = 1.4 + (5 - index) * 0.32
        fragments.append(
            f'<line x1="{OPEN_X - 25:.1f}" y1="{y:.1f}" '
            f'x2="{string_end_x:.1f}" y2="{y:.1f}" '
            f'stroke="rgb(35,35,35)" stroke-width="{width:.2f}"/>'
        )
        fragments.append(
            text_svg(28, y + 5, f"{6 - index}  {tuning}", size=14, weight=700, anchor="start")
        )

    # Sillet et frettes sur toute la hauteur des six cordes.
    board_top_y, board_bottom_y = visual_board_bounds()
    fragments.append(
        f'<line x1="{LEFT_MARGIN:.1f}" y1="{board_top_y:.1f}" '
        f'x2="{LEFT_MARGIN:.1f}" y2="{board_bottom_y:.1f}" '
        'stroke="rgb(10,10,10)" stroke-width="8"/>'
    )
    for fret in range(1, LAST_FRET + 1):
        x = LEFT_MARGIN + fret * FRET_WIDTH
        fragments.append(
            f'<line x1="{x:.1f}" y1="{board_top_y:.1f}" '
            f'x2="{x:.1f}" y2="{board_bottom_y:.1f}" '
            'stroke="rgb(75,75,75)" stroke-width="2"/>'
        )

    # Numéros de cases
    fragments.append(text_svg(OPEN_X, 321, "0", size=13, weight=700))
    for fret in range(1, LAST_FRET + 1):
        fragments.append(text_svg(fret_x(fret), 321, str(fret), size=13, weight=700))

    # Repères usuels du manche
    for fret in (3, 5, 7, 9, 12, 15):
        if fret > LAST_FRET:
            continue
        x = fret_x(fret)
        if fret == 12:
            fragments.append(f'<circle cx="{x - 9:.1f}" cy="337" r="3.5" fill="rgb(90,90,90)"/>')
            fragments.append(f'<circle cx="{x + 9:.1f}" cy="337" r="3.5" fill="rgb(90,90,90)"/>')
        else:
            fragments.append(f'<circle cx="{x:.1f}" cy="337" r="3.5" fill="rgb(90,90,90)"/>')

    for spot in spots:
        fragments.append(render_note(spot, label_mode))

    fragments.append("</g>")
    return "".join(fragments)

def render_legend(y: float, label_mode: str) -> str:
    items = [
        (ROOT_COLOR, "Tonique 1"),
        (THIRD_COLOR, "Tierce 3 / b3"),
        (FIFTH_COLOR, "Quinte 5"),
        (SEVENTH_COLOR, "Septième 7 / b7"),
        (OTHER_COLOR, "Autres degrés"),
        (PENTA_STROKE, "Contour violet = note de la pentatonique"),
    ]
    fragments = [f'<g transform="translate(0,{y:.1f})">']
    total = 1280
    start = (CANVAS_WIDTH - total) / 2
    item_width = total / len(items)
    for index, (color, label) in enumerate(items):
        x = start + index * item_width
        if label.startswith("Contour violet"):
            fragments.append(
                f'<circle cx="{x + 11:.1f}" cy="0" r="10" fill="none" '
                f'stroke="{PENTA_STROKE}" stroke-width="3.2" stroke-dasharray="5 2"/>'
            )
        else:
            fragments.append(
                f'<circle cx="{x + 11:.1f}" cy="0" r="10" fill="{color}" '
                'stroke="rgb(45,45,45)" stroke-width="1.5"/>'
            )
        fragments.append(text_svg(x + 30, 5, label, size=14, weight=600, anchor="start"))
    fragments.append(
        text_svg(
            CANVAS_WIDTH / 2,
            35,
            f"Étiquettes : {label_mode}",
            size=13,
            weight=500,
            color="rgb(85,85,85)",
        )
    )
    fragments.append("</g>")
    return "".join(fragments)


def render_global_strip(root_pc: int, y: float) -> str:
    occurrences = all_occurrences(root_pc)
    fragments = [f'<g transform="translate(0,{y:.1f})">']
    fragments.append(text_svg(CANVAS_WIDTH / 2, 18, "Ordre des formes sur le manche", size=17, weight=700))

    strip_y = 35
    strip_h = 42
    for index in range(len(occurrences) - 1):
        start, shape = occurrences[index]
        end, _ = occurrences[index + 1]
        visible_start = max(FIRST_FRET, start)
        visible_end = min(LAST_FRET, end)
        if visible_end <= visible_start:
            continue
        x = LEFT_MARGIN + visible_start * FRET_WIDTH
        width = (visible_end - visible_start) * FRET_WIDTH
        color = {
            "C": "rgb(220,235,255)",
            "A": "rgb(225,245,225)",
            "G": "rgb(255,242,205)",
            "E": "rgb(255,225,225)",
            "D": "rgb(235,225,250)",
        }[shape]
        fragments.append(
            f'<rect x="{x:.1f}" y="{strip_y}" width="{width:.1f}" height="{strip_h}" '
            f'fill="{color}" stroke="rgb(80,80,80)" stroke-width="1"/>'
        )
        fragments.append(text_svg(x + width / 2, strip_y + 27, shape, size=16, weight=700))

    for fret in range(FIRST_FRET, LAST_FRET + 1):
        x = LEFT_MARGIN + fret * FRET_WIDTH
        fragments.append(text_svg(x, 96, str(fret), size=11, weight=600))
    fragments.append("</g>")
    return "".join(fragments)


def target_third(profile: Profile, spelled_notes: list[str]) -> tuple[str, str]:
    for interval, degree in zip(profile.scale_intervals, profile.scale_degrees):
        if "3" in degree:
            index = profile.scale_intervals.index(interval)
            return degree, spelled_notes[index]
    raise RuntimeError("Tierce introuvable dans le profil.")


def render_section(
    *,
    y_start: float,
    root: str,
    root_pc: int,
    profile: Profile,
    spelled_notes: list[str],
    context: ShapeContext,
    label_mode: str,
    section_number: int,
) -> tuple[str, float]:
    _, note_by_pc = scale_maps(root_pc, profile, spelled_notes)
    current_zone = context.current_zone
    next_zone = context.next_zone
    overlap = context.overlap_zone

    caged_complete, caged_labels = full_caged_chord_spots(
        root_pc=root_pc,
        profile=profile,
        spelled_notes=spelled_notes,
        context=context,
    )
    arpeggio = spots_in_range(
        root_pc=root_pc,
        intervals=profile.chord_intervals,
        degrees=profile.chord_degrees,
        note_by_pc=note_by_pc,
        fret_start=current_zone[0],
        fret_end=current_zone[1],
    )
    scale = spots_in_range(
        root_pc=root_pc,
        intervals=profile.scale_intervals,
        degrees=profile.scale_degrees,
        note_by_pc=note_by_pc,
        fret_start=current_zone[0],
        fret_end=current_zone[1],
    )
    penta_intervals, _ = pentatonic_intervals_and_degrees(profile)
    penta_degrees = {profile.scale_degrees[profile.scale_intervals.index(interval)] for interval in penta_intervals if interval in profile.scale_intervals}
    scale = [
        NoteSpot(
            string_index=spot.string_index,
            fret=spot.fret,
            note=spot.note,
            degree=spot.degree,
            exact=spot.exact,
            transition=spot.transition,
            muted=spot.muted,
            pentatonic=spot.degree in penta_degrees,
        )
        for spot in scale
    ]
    connection = spots_in_range(
        root_pc=root_pc,
        intervals=profile.scale_intervals,
        degrees=profile.scale_degrees,
        note_by_pc=note_by_pc,
        fret_start=min(current_zone[0], next_zone[0]),
        fret_end=max(current_zone[1], next_zone[1]),
        transition_zone=overlap,
    )

    fragments: list[str] = []
    y = y_start
    fragments.append(
        f'<line x1="55" y1="{y:.1f}" x2="{CANVAS_WIDTH - 55}" y2="{y:.1f}" '
        'stroke="rgb(145,145,145)" stroke-width="1.5"/>'
    )
    y += 46
    fragments.append(
        text_svg(
            CANVAS_WIDTH / 2,
            y,
            f"{section_number}. Forme {context.shape} -> forme {context.next_shape}",
            size=29,
            weight=700,
        )
    )
    y += 29
    fragments.append(
        text_svg(
            CANVAS_WIDTH / 2,
            y,
            f"Départ forme {context.shape} : case {context.start} | "
            f"forme suivante {context.next_shape} : case {context.next_start}",
            size=16,
            weight=600,
            color="rgb(70,70,70)",
        )
    )
    y += 25

    fragments.append(
        render_board(
            y_offset=y,
            title=f"1 — Réseau CAGED complet : forme {context.shape} mise en évidence",
            subtitle="Toutes les notes de l’accord sont visibles sur le manche ; la forme exacte étudiée ressort en bleu épais.",
            spots=caged_complete,
            label_mode=label_mode,
            current_zone=current_zone,
            shape_labels=caged_labels,
        )
    )
    y += BOARD_HEIGHT + 12

    fragments.append(
        render_board(
            y_offset=y,
            title="2 — Arpège dans la même zone",
            subtitle=f"Le dessin d'accord devient un réseau de notes {' / '.join(profile.chord_degrees)}.",
            spots=arpeggio,
            label_mode=label_mode,
            current_zone=current_zone,
            current_label=f"Zone {context.shape}",
        )
    )
    y += BOARD_HEIGHT + 12

    fragments.append(
        render_board(
            y_offset=y,
            title="3 — Gamme autour de l'arpège",
            subtitle="Le contour violet entoure les notes de la pentatonique ; les autres degrés complètent la gamme, mais servent davantage de passages et de couleurs.",
            spots=scale,
            label_mode=label_mode,
            current_zone=current_zone,
            current_label=f"Zone {context.shape}",
        )
    )
    y += BOARD_HEIGHT + 12

    fragments.append(
        render_board(
            y_offset=y,
            title=f"4 — Zone géographique commune : {context.shape} -> {context.next_shape}",
            subtitle="La zone verte appartient aux deux formes : utilise-la pour passer de l'une à l'autre sans perdre tes repères sur le manche.",
            spots=connection,
            label_mode=label_mode,
            current_zone=current_zone,
            current_label=f"Forme {context.shape}",
            next_zone=next_zone,
            next_label=f"Forme {context.next_shape}",
            overlap_zone=overlap,
        )
    )
    y += BOARD_HEIGHT + 8

    third_degree, third_note = target_third(profile, spelled_notes)
    fragments.append(
        text_svg(
            CANVAS_WIDTH / 2,
            y,
            "Exercice : accord -> arpège montant -> gamme descendante -> passage par la zone géographique commune.",
            size=16,
            weight=700,
        )
    )
    y += 24
    fragments.append(
        text_svg(
            CANVAS_WIDTH / 2,
            y,
            f"Termine volontairement sur {third_note} ({third_degree}) : tu dois entendre la couleur de l'accord.",
            size=15,
            weight=600,
            color="rgb(70,70,70)",
        )
    )
    y += 42
    return "".join(fragments), y


def safe_token(text: str) -> str:
    return (
        text.replace("#", "sharp")
        .replace("b", "flat")
        .replace(" ", "_")
        .replace("/", "-")
    )


def script_fingerprint() -> str:
    """Empreinte courte du script réellement exécuté."""
    try:
        payload = Path(__file__).read_bytes()
    except OSError:
        return "indisponible"
    return hashlib.sha256(payload).hexdigest()[:12]


def generate_svg(
    *,
    root: str,
    root_pc: int,
    profile: Profile,
    shape_choice: str,
    label_mode: str,
    output_path: Path | None = None,
) -> Path:
    spelled_notes = build_spelled_scale(root, profile.scale_intervals)
    chord_notes = [
        spelled_notes[profile.scale_intervals.index(interval)]
        for interval in profile.chord_intervals
    ]

    if shape_choice == "toutes":
        contexts = ordered_contexts(root_pc)
        shape_filename = "toutes_formes"
    else:
        contexts = [shape_context(root_pc, shape_choice)]
        shape_filename = f"forme_{shape_choice}"

    if output_path is None:
        output_path = Path(
            f"{safe_token(root)}_{safe_token(profile.key)}_CAGED_"
            f"{shape_filename}_{label_mode}_v2_1.svg"
        )

    fragments: list[str] = []
    y = 52.0
    fragments.append(
        text_svg(
            CANVAS_WIDTH / 2,
            y,
            f"{root} {profile.title} — CAGED appliqué",
            size=36,
            weight=700,
            color="rgb(20,20,20)",
        )
    )
    y += 38
    fragments.append(
        text_svg(
            CANVAS_WIDTH / 2,
            y,
            "CAGED complet -> arpège -> gamme -> zone géographique commune",
            size=20,
            weight=600,
            color="rgb(65,65,65)",
        )
    )
    y += 34
    fragments.append(
        text_svg(
            CANVAS_WIDTH / 2,
            y,
            f"Accord : {' - '.join(chord_notes)}   |   Formule : {' - '.join(profile.chord_degrees)}",
            size=17,
            weight=700,
        )
    )
    y += 26
    fragments.append(
        text_svg(
            CANVAS_WIDTH / 2,
            y,
            f"{profile.mode_name} : {' - '.join(spelled_notes)}",
            size=16,
            weight=600,
        )
    )
    y += 42
    fragments.append(render_legend(y, label_mode))
    y += 65
    fragments.append(render_global_strip(root_pc, y))
    y += 118

    for index, context in enumerate(contexts, start=1):
        section, y = render_section(
            y_start=y,
            root=root,
            root_pc=root_pc,
            profile=profile,
            spelled_notes=spelled_notes,
            context=context,
            label_mode=label_mode,
            section_number=index,
        )
        fragments.append(section)

    fingerprint = script_fingerprint()
    fragments.append(
        text_svg(
            CANVAS_WIDTH / 2,
            y + 5,
            f"{SCRIPT_NAME} v{GENERATOR_VERSION} — empreinte {fingerprint}",
            size=11,
            weight=500,
            color="rgb(120,120,120)",
        )
    )
    total_height = y + 30
    svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!-- Généré par {SCRIPT_NAME} v{GENERATOR_VERSION} — empreinte {fingerprint} -->
<svg xmlns="http://www.w3.org/2000/svg"
     width="{CANVAS_WIDTH}"
     height="{total_height:.1f}"
     viewBox="0 0 {CANVAS_WIDTH} {total_height:.1f}">
  <rect x="0" y="0" width="{CANVAS_WIDTH}" height="{total_height:.1f}" fill="white"/>
  {''.join(fragments)}
</svg>
'''
    output_path.write_text(svg, encoding="utf-8")
    return output_path


# -----------------------------------------------------------------------------
# Validation interne
# -----------------------------------------------------------------------------
def validate_profiles_and_templates() -> None:
    """Vérifie toutes les formes, pour les 12 fondamentales et les 5 profils."""
    for profile_key, profile in PROFILES.items():
        if profile_key not in CHORD_TEMPLATES:
            raise AssertionError(f"Templates absents pour {profile_key}")
        if not set(profile.chord_intervals).issubset(profile.scale_intervals):
            raise AssertionError(f"Accord hors gamme pour {profile_key}")

        for root_pc in range(12):
            for shape in SHAPES:
                start = shape_start(root_pc, shape)
                template = CHORD_TEMPLATES[profile_key][shape]
                if len(template) != 6:
                    raise AssertionError(f"Template {profile_key}/{shape} invalide")
                found_intervals: set[int] = set()
                for string_index, offset in enumerate(template):
                    if offset is None:
                        continue
                    fret = start + offset
                    pc = (TUNING_PCS[string_index] + fret) % 12
                    interval = (pc - root_pc) % 12
                    if interval not in profile.chord_intervals:
                        raise AssertionError(
                            f"Note étrangère : {profile_key}/{shape}, "
                            f"racine={root_pc}, intervalle={interval}"
                        )
                    found_intervals.add(interval)
                # Pour les accords de septième, la quinte peut être omise dans un
                # voicing CAGED usuel. La fondamentale, la tierce et la septième
                # restent obligatoires. Pour les triades, les trois degrés le sont.
                required_intervals = set(profile.chord_intervals)
                if len(profile.chord_intervals) == 4:
                    required_intervals.discard(7)
                if not required_intervals.issubset(found_intervals):
                    missing = required_intervals - found_intervals
                    raise AssertionError(
                        f"Degrés essentiels manquants dans {profile_key}/{shape} : "
                        f"{sorted(missing)}"
                    )

    # Vérification de quelques orthographes sensibles.
    checks = {
        ("F#", "majeur"): ["F#", "G#", "A#", "B", "C#", "D#", "E#"],
        ("Gb", "majeur"): ["Gb", "Ab", "Bb", "Cb", "Db", "Eb", "F"],
        ("Bb", "7"): ["Bb", "C", "D", "Eb", "F", "G", "Ab"],
        ("C#", "mineur"): ["C#", "D#", "E", "F#", "G#", "A", "B"],
    }
    for (root, profile_key), expected in checks.items():
        actual = build_spelled_scale(root, PROFILES[profile_key].scale_intervals)
        if actual != expected:
            raise AssertionError(f"Orthographe incorrecte pour {root} {profile_key}: {actual}")


# -----------------------------------------------------------------------------
# Validation visuelle et pédagogique
# -----------------------------------------------------------------------------
def validate_render_geometry() -> None:
    """Bloque les régressions de géométrie déjà rencontrées."""
    top_to_bottom = [
        (6 - index, STRINGS[index], string_y(index))
        for index in range(6)
    ]
    top_to_bottom.sort(key=lambda item: item[2])
    displayed = [(number, note) for number, note, _ in top_to_bottom]
    if displayed != [(1, "E"), (2, "B"), (3, "G"), (4, "D"), (5, "A"), (6, "E")]:
        raise AssertionError(f"Ordre visuel des cordes invalide : {displayed}")

    board_top, board_bottom = visual_board_bounds()
    all_y = [string_y(index) for index in range(6)]
    if not board_top < min(all_y) or not board_bottom > max(all_y):
        raise AssertionError("Les frettes et le sillet ne couvrent pas les six cordes.")

    samples = [
        NoteSpot(0, 5, "A", "1", exact=True),
        NoteSpot(0, 5, "A", "1", muted=True),
        NoteSpot(0, 5, "A", "1"),
        NoteSpot(0, 5, "A", "1", transition=True),
    ]
    if any(' r="19"' not in render_note(spot, "mixte") for spot in samples):
        raise AssertionError("Toutes les pastilles doivent avoir le même rayon.")

    # Vérification sur un SVG réel.
    temp = Path("/tmp/__caged_v2_geometry.svg")
    generate_svg(
        root="A",
        root_pc=pitch_class("A"),
        profile=PROFILES["mineur"],
        shape_choice="E",
        label_mode="mixte",
        output_path=temp,
    )
    svg = temp.read_text(encoding="utf-8")
    temp.unlink(missing_ok=True)
    expected_top = f'y1="{board_top:.1f}"'
    expected_bottom = f'y2="{board_bottom:.1f}"'
    if svg.count(expected_top) < LAST_FRET + 1 or svg.count(expected_bottom) < LAST_FRET + 1:
        raise AssertionError("Certaines frettes ou le sillet ne traversent pas tout le manche.")


def validate_caged_overview() -> None:
    """Vérifie le réseau complet et la mise en évidence de la forme choisie."""
    root = "A"
    profile = PROFILES["mineur"]
    spelled = build_spelled_scale(root, profile.scale_intervals)
    context = shape_context(pitch_class(root), "E")
    spots, labels = full_caged_chord_spots(
        root_pc=pitch_class(root),
        profile=profile,
        spelled_notes=spelled,
        context=context,
    )

    visible_shapes = {label.replace("Forme ", "") for label, _, _ in labels}
    if not set(SHAPES).issubset(visible_shapes):
        raise AssertionError(f"CAGED incomplet dans le diagramme 1 : {visible_shapes}")

    selected_labels = [label for label, _, selected in labels if selected]
    if selected_labels != ["Forme E"]:
        raise AssertionError(f"Forme étudiée mal identifiée : {selected_labels}")

    if not any(spot.exact for spot in spots) or not any(spot.muted for spot in spots):
        raise AssertionError("Le contraste forme étudiée / réseau complet est absent.")

    # Contrôle explicite du défaut corrigé : sur la corde 6 de Am,
    # les notes de l'accord visibles entre les cases 0 et 15 sont E, A, C et E.
    low_e_frets = sorted(
        spot.fret
        for spot in spots
        if spot.string_index == 0
    )
    if low_e_frets != [0, 5, 8, 12]:
        raise AssertionError(
            f"Réseau incomplet sur la corde de mi grave pour Am : {low_e_frets}"
        )


def validate_pedagogical_texts() -> None:
    """Vérifie les messages pédagogiques structurants de la V2."""
    temp = Path("/tmp/__caged_v2_pedagogy.svg")
    generate_svg(
        root="A",
        root_pc=pitch_class("A"),
        profile=PROFILES["mineur"],
        shape_choice="E",
        label_mode="mixte",
        output_path=temp,
    )
    svg = temp.read_text(encoding="utf-8")
    temp.unlink(missing_ok=True)
    required = [
        "Réseau CAGED complet : forme E mise en évidence",
        "Contour violet = note de la pentatonique",
        "davantage de passages et de couleurs",
        "Zone géographique commune : E -&gt; D",
        "La zone verte appartient aux deux formes",
        f"{SCRIPT_NAME} v{GENERATOR_VERSION}",
        script_fingerprint(),
    ]
    missing = [item for item in required if item not in svg]
    if missing:
        raise AssertionError(f"Messages pédagogiques ou version absents : {missing}")


def run_all_validations() -> None:
    validate_profiles_and_templates()
    validate_render_geometry()
    validate_caged_overview()
    validate_pedagogical_texts()


# -----------------------------------------------------------------------------
# Interface
# -----------------------------------------------------------------------------
def normalize_quality(value: str) -> str:
    cleaned = strip_accents(value.strip().lower()).replace(" ", "")
    aliases = {
        "1": "majeur",
        "majeur": "majeur",
        "major": "majeur",
        "maj": "majeur",
        "2": "mineur",
        "mineur": "mineur",
        "minor": "mineur",
        "min": "mineur",
        "3": "7",
        "7": "7",
        "dom7": "7",
        "dominante7": "7",
        "dominant7": "7",
        "4": "maj7",
        "maj7": "maj7",
        "majeur7": "maj7",
        "major7": "maj7",
        "5": "m7",
        "m7": "m7",
        "min7": "m7",
        "mineur7": "m7",
        "minor7": "m7",
    }
    if cleaned not in aliases:
        raise ValueError("Choix invalide. Utilise majeur, mineur, 7, maj7 ou m7.")
    return aliases[cleaned]


def normalize_shape(value: str) -> str:
    cleaned = strip_accents(value.strip()).upper()
    if cleaned in SHAPES:
        return cleaned
    if cleaned in {"T", "TOUT", "TOUS", "TOUTES", "ALL", "*"}:
        return "toutes"
    raise ValueError("Forme invalide. Utilise C, A, G, E, D ou toutes.")


def normalize_label_mode(value: str) -> str:
    cleaned = strip_accents(value.strip().lower()).replace(" ", "")
    aliases = {
        "1": "degres",
        "degre": "degres",
        "degres": "degres",
        "degrees": "degres",
        "2": "notes",
        "note": "notes",
        "notes": "notes",
        "3": "mixte",
        "mixte": "mixte",
        "both": "mixte",
        "lesdeux": "mixte",
    }
    if cleaned not in aliases:
        raise ValueError("Étiquettes invalides. Utilise degrés, notes ou mixte.")
    return aliases[cleaned]


def ask_until(prompt: str, normalizer):
    while True:
        try:
            return normalizer(input(prompt))
        except ValueError as error:
            print(f"Erreur : {error}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Génère un parcours CAGED V2 : vue complète, arpège, gamme et zone commune."
    )
    parser.add_argument("--tonalite", help="Ex. G, F#, Bb, Ré, Sib")
    parser.add_argument("--accord", help="majeur, mineur, 7, maj7 ou m7")
    parser.add_argument("--forme", help="C, A, G, E, D ou toutes")
    parser.add_argument("--etiquettes", help="degres, notes ou mixte")
    parser.add_argument("--sortie", help="Nom ou chemin du fichier SVG")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Exécute les validations contenu, géométrie et pédagogie.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {GENERATOR_VERSION} — empreinte {script_fingerprint()}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_all_validations()

    if args.test:
        print(
            "Validation V2 réussie : 300 voicings, orthographes, CAGED complet, "
            "géométrie du manche et textes pédagogiques cohérents."
        )
        print(f"Version {GENERATOR_VERSION} — empreinte {script_fingerprint()}")
        return

    if args.tonalite:
        root, root_pc = normalize_root(args.tonalite)
    else:
        root, root_pc = ask_until(
            "Tonalité (ex. G, F#, Bb, Ré, Sib) : ",
            normalize_root,
        )

    if args.accord:
        quality = normalize_quality(args.accord)
    else:
        quality = ask_until(
            "Type d'accord [1 majeur, 2 mineur, 3 7, 4 maj7, 5 m7] : ",
            normalize_quality,
        )

    if args.forme:
        shape_choice = normalize_shape(args.forme)
    else:
        shape_choice = ask_until(
            "Forme de départ [C/A/G/E/D] ou T pour toutes : ",
            normalize_shape,
        )

    if args.etiquettes:
        label_mode = normalize_label_mode(args.etiquettes)
    else:
        raw_labels = input("Étiquettes [1 degrés, 2 notes, 3 mixte] (défaut 3) : ").strip()
        label_mode = normalize_label_mode(raw_labels or "3")

    output = Path(args.sortie) if args.sortie else None
    result = generate_svg(
        root=root,
        root_pc=root_pc,
        profile=PROFILES[quality],
        shape_choice=shape_choice,
        label_mode=label_mode,
        output_path=output,
    )

    spelled_notes = build_spelled_scale(root, PROFILES[quality].scale_intervals)
    chord_notes = [
        spelled_notes[PROFILES[quality].scale_intervals.index(interval)]
        for interval in PROFILES[quality].chord_intervals
    ]
    print(f"\nAccord : {root} {PROFILES[quality].title} = {' - '.join(chord_notes)}")
    print(f"Gamme associée : {' - '.join(spelled_notes)}")
    print(f"SVG généré : {result}")
    print(f"Générateur : v{GENERATOR_VERSION} — empreinte {script_fingerprint()}")


if __name__ == "__main__":
    main()
