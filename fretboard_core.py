#!/usr/bin/env python3
"""Socle théorique et SVG partagé par les nouveaux générateurs.

Le projet historique conserve ses scripts autonomes. Ce module évite de
dupliquer une troisième fois la normalisation des tonalités, l'orthographe
diatonique et les constantes du manche dans les nouveaux outils.
"""
from __future__ import annotations

import html
import re
import unicodedata


# Ordre d'affichage : corde 1 en haut, corde 6 en bas.
STRINGS_TOP_TO_BOTTOM = (
    (1, "E", 4),
    (2, "B", 11),
    (3, "G", 7),
    (4, "D", 2),
    (5, "A", 9),
    (6, "E", 4),
)

NATURAL_PITCHES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
LETTER_ORDER = ("C", "D", "E", "F", "G", "A", "B")

MAJOR_INTERVALS = (0, 2, 4, 5, 7, 9, 11)
MAJOR_DEGREES = ("1", "2", "3", "4", "5", "6", "7")
MINOR_INTERVALS = (0, 2, 3, 5, 7, 8, 10)
MINOR_DEGREES = ("1", "2", "b3", "4", "5", "b6", "b7")

INTERVAL_DEGREES = {
    0: "1", 1: "b2", 2: "2", 3: "b3", 4: "3", 5: "4",
    6: "b5", 7: "5", 8: "b6", 9: "6", 10: "b7", 11: "7",
}

SHARP_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
FLAT_NAMES = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")
FLAT_KEYS = {"F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb"}

ROOT_COLOR = "rgb(255,145,145)"
THIRD_COLOR = "rgb(255,212,125)"
FIFTH_COLOR = "rgb(150,202,255)"
SEVENTH_COLOR = "rgb(202,175,240)"
OTHER_COLOR = "rgb(238,238,238)"
TEXT_COLOR = "rgb(35,35,35)"
MUTED_COLOR = "rgb(105,105,105)"


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def normalize_note(value: str) -> str:
    cleaned = value.strip().replace("♯", "#").replace("♭", "b").replace(" ", "")
    low = strip_accents(cleaned).lower()
    french = re.fullmatch(r"(do|re|mi|fa|sol|la|si)([#b]?)", low)
    if french:
        name, accidental = french.groups()
        letter = {
            "do": "C", "re": "D", "mi": "E", "fa": "F",
            "sol": "G", "la": "A", "si": "B",
        }[name]
        return letter + accidental
    international = re.fullmatch(r"([a-g])([#b]?)", low)
    if not international:
        raise ValueError("Tonalité invalide. Exemples : G, F#, Bb, Sol, Sib, Am.")
    letter, accidental = international.groups()
    return letter.upper() + accidental


def parse_tonality(value: str) -> tuple[str, str]:
    """Retourne (fondamentale, mode) avec mode majeur ou mineur."""
    cleaned = strip_accents(value.strip()).replace("♯", "#").replace("♭", "b")
    low = cleaned.lower().replace(" ", "")
    mode = "majeur"
    for suffix in ("mineur", "minor", "min"):
        if low.endswith(suffix):
            cleaned = cleaned[: -len(suffix)]
            mode = "mineur"
            break
    else:
        if low.endswith("m") and not low.endswith("maj"):
            cleaned = cleaned[:-1]
            mode = "mineur"
        elif low.endswith("majeur"):
            cleaned = cleaned[:-6]
        elif low.endswith("major"):
            cleaned = cleaned[:-5]
        elif low.endswith("maj"):
            cleaned = cleaned[:-3]
    return normalize_note(cleaned), mode


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
    intervals = MAJOR_INTERVALS if mode == "majeur" else MINOR_INTERVALS
    root_pc = pitch_class(root)
    start_letter = LETTER_ORDER.index(root[0])
    notes: list[str] = []
    for index, interval in enumerate(intervals):
        letter = LETTER_ORDER[(start_letter + index) % 7]
        target_pc = (root_pc + interval) % 12
        delta = (target_pc - NATURAL_PITCHES[letter]) % 12
        if delta > 6:
            delta -= 12
        notes.append(letter + accidental_for_delta(delta))
    return notes


def scale_degrees(mode: str) -> tuple[str, ...]:
    return MAJOR_DEGREES if mode == "majeur" else MINOR_DEGREES


def scale_intervals(mode: str) -> tuple[int, ...]:
    return MAJOR_INTERVALS if mode == "majeur" else MINOR_INTERVALS


def chromatic_name(pc: int, root: str) -> str:
    names = FLAT_NAMES if root in FLAT_KEYS or "b" in root else SHARP_NAMES
    return names[pc % 12]


def safe_token(value: str) -> str:
    return value.replace("#", "sharp").replace("b", "flat").replace(" ", "_").replace("/", "-")


def degree_color(degree: str) -> str:
    if degree == "1":
        return ROOT_COLOR
    if degree in {"3", "b3"}:
        return THIRD_COLOR
    if degree == "5":
        return FIFTH_COLOR
    if degree in {"7", "b7"}:
        return SEVENTH_COLOR
    return OTHER_COLOR


def svg_text(
    x: float,
    y: float,
    value: object,
    *,
    size: int = 14,
    weight: int = 500,
    anchor: str = "middle",
    color: str = TEXT_COLOR,
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{color}">'
        f'{html.escape(str(value))}</text>'
    )

