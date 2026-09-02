#!/usr/bin/env python3
"""Génère une fiche A4 d'harmonisation et de travail d'une progression.

Complément des cartes CAGED : on ne regarde plus une gamme isolée. La fiche
montre les accords diatoniques de la tonalité, puis les notes d'accord de la
progression choisie sur quatre manches de 14 frettes.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

VERSION = "1.0.1"
SCRIPT_NAME = "generateur_harmonisation_progressions_v1.py"

# Ce générateur est volontairement autonome : il peut être téléchargé et
# exécuté seul, sans module Python à placer à côté.
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
        accidental = "#" * delta if delta > 0 else "b" * (-delta)
        notes.append(letter + accidental)
    return notes


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

PAGE_W = 1754
PAGE_H = 1240
FIRST_FRET = 0
LAST_FRET = 14

MAJOR_ROMAN = ("I", "ii", "iii", "IV", "V", "vi", "vii°")
MINOR_ROMAN = ("i", "ii°", "III", "iv", "v", "VI", "VII")

PROGRESSIONS = {
    "majeur": {
        "I-IV-V-I": (0, 3, 4, 0),
        "I-vi-IV-V": (0, 5, 3, 4),
        "ii-V-I": (1, 4, 0),
        "vi-IV-I-V": (5, 3, 0, 4),
    },
    "mineur": {
        "i-iv-v-i": (0, 3, 4, 0),
        "i-bVII-bVI-bVII": (0, 6, 5, 6),
        "i-bVI-III-bVII": (0, 5, 2, 6),
        "iiø-v-i": (1, 4, 0),
    },
}

DEFAULT_PROGRESSION = {"majeur": "I-IV-V-I", "mineur": "i-iv-v-i"}

TRIAD_SUFFIX = {
    (0, 4, 7): "",
    (0, 3, 7): "m",
    (0, 3, 6): "dim",
}
SEVENTH_SUFFIX = {
    (0, 4, 7, 11): "maj7",
    (0, 4, 7, 10): "7",
    (0, 3, 7, 10): "m7",
    (0, 3, 6, 10): "m7b5",
}


@dataclass(frozen=True)
class Chord:
    degree_index: int
    roman: str
    root: str
    root_pc: int
    notes: tuple[str, ...]
    pcs: tuple[int, ...]
    degrees: tuple[str, ...]
    symbol: str


def script_fingerprint() -> str:
    try:
        return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
    except OSError:
        return "indisponible"


def build_harmony(root: str, mode: str, seventh: bool) -> list[Chord]:
    notes = spelled_scale(root, mode)
    romans = MAJOR_ROMAN if mode == "majeur" else MINOR_ROMAN
    count = 4 if seventh else 3
    suffixes = SEVENTH_SUFFIX if seventh else TRIAD_SUFFIX
    harmony: list[Chord] = []
    for degree_index in range(7):
        indexes = tuple((degree_index + 2 * offset) % 7 for offset in range(count))
        chord_notes = tuple(notes[index] for index in indexes)
        pcs = tuple(pitch_class(note) for note in chord_notes)
        chord_root_pc = pcs[0]
        intervals = tuple((pc - chord_root_pc) % 12 for pc in pcs)
        if intervals not in suffixes:
            raise AssertionError(f"Accord non reconnu : {chord_notes} / {intervals}")
        degrees = tuple(INTERVAL_DEGREES[interval] for interval in intervals)
        harmony.append(
            Chord(
                degree_index=degree_index,
                roman=romans[degree_index],
                root=chord_notes[0],
                root_pc=chord_root_pc,
                notes=chord_notes,
                pcs=pcs,
                degrees=degrees,
                symbol=chord_notes[0] + suffixes[intervals],
            )
        )
    return harmony


def normalize_labels(value: str) -> str:
    cleaned = strip_accents(value.strip().lower()).replace(" ", "")
    aliases = {
        "1": "degres", "degre": "degres", "degres": "degres",
        "2": "notes", "note": "notes", "notes": "notes",
        "3": "mixte", "mixte": "mixte", "lesdeux": "mixte",
    }
    if cleaned not in aliases:
        raise ValueError("Étiquettes invalides : degrés, notes ou mixte.")
    return aliases[cleaned]


def progression_choice(mode: str, value: str | None) -> tuple[str, tuple[int, ...]]:
    if not value:
        key = DEFAULT_PROGRESSION[mode]
        return key, PROGRESSIONS[mode][key]
    raw = value.strip().replace("–", "-").replace("—", "-").replace(" ", "")
    lowered = strip_accents(raw).lower()
    for key, degrees in PROGRESSIONS[mode].items():
        if strip_accents(key).lower() == lowered:
            return key, degrees
    choices = ", ".join(PROGRESSIONS[mode])
    raise ValueError(f"Progression inconnue pour le mode {mode} : {choices}.")


def render_legend(y: float) -> str:
    items = [
        ("rgb(255,145,145)", "1 fondamentale"),
        ("rgb(255,212,125)", "3 / b3 tierce"),
        ("rgb(150,202,255)", "5 quinte"),
        ("rgb(202,175,240)", "7 / b7 septième"),
    ]
    parts: list[str] = []
    start_x = 370
    for index, (color, label) in enumerate(items):
        x = start_x + index * 280
        parts.append(f'<circle cx="{x}" cy="{y}" r="11" fill="{color}" stroke="{TEXT_COLOR}" stroke-width="1.2"/>')
        parts.append(svg_text(x + 20, y + 5, label, size=13, weight=650, anchor="start"))
    return "".join(parts)


def render_harmony_table(harmony: list[Chord], y: float, seventh: bool) -> str:
    title = "Accords de septième diatoniques" if seventh else "Triades diatoniques"
    parts = [svg_text(90, y - 12, title, size=15, weight=750, anchor="start")]
    left = 90
    width = (PAGE_W - 180) / 7
    for index, chord in enumerate(harmony):
        x = left + index * width
        fill = "rgb(245,245,245)" if index % 2 == 0 else "white"
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="68" fill="{fill}" stroke="rgb(165,165,165)"/>')
        parts.append(svg_text(x + width / 2, y + 23, chord.roman, size=13, weight=750))
        parts.append(svg_text(x + width / 2, y + 45, chord.symbol, size=16, weight=800))
        parts.append(svg_text(x + width / 2, y + 61, "-".join(chord.notes), size=9, weight=550, color=MUTED_COLOR))
    return "".join(parts)


def render_note_label(x: float, y: float, degree: str, note: str, labels: str) -> str:
    if labels == "degres":
        return svg_text(x, y + 3, degree, size=8, weight=800)
    if labels == "notes":
        return svg_text(x, y + 3, note, size=7, weight=800)
    return (
        svg_text(x, y - 1, degree, size=6, weight=800)
        + svg_text(x, y + 6, note, size=5, weight=700)
    )


def render_chord_card(
    chord: Chord,
    next_chord: Chord | None,
    number: int,
    x: float,
    y: float,
    width: float,
    height: float,
    labels: str,
) -> str:
    board_left = x + 78
    board_right = x + width - 28
    nut_x = board_left + 18
    open_x = board_left - 8
    fret_w = (board_right - nut_x) / LAST_FRET
    board_top = y + 112
    string_gap = 27
    board_bottom = board_top + 5 * string_gap
    common = set(chord.pcs) & set(next_chord.pcs) if next_chord else set()

    parts = [
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" rx="16" fill="white" stroke="rgb(190,190,190)" stroke-width="1.4"/>',
        svg_text(x + 26, y + 34, number, size=16, weight=800),
        svg_text(x + 52, y + 34, f"{chord.symbol} ({chord.roman})", size=21, weight=800, anchor="start"),
        svg_text(x + width - 28, y + 34, " - ".join(chord.notes), size=13, weight=700, anchor="end"),
        svg_text(x + width / 2, y + 61, f"Formule : {' - '.join(chord.degrees)}", size=12, weight=650, color=MUTED_COLOR),
    ]
    if next_chord:
        common_names = [note for note in chord.notes if pitch_class(note) in common]
        message = (
            f"Vers {next_chord.symbol} : note(s) commune(s) {' - '.join(common_names)}"
            if common_names else
            f"Vers {next_chord.symbol} : aucune note commune, vise sa tierce la plus proche"
        )
        parts.append(svg_text(x + width / 2, y + 83, message, size=11, weight=650, color="rgb(52,112,65)"))

    for string_number, string_name, _ in STRINGS_TOP_TO_BOTTOM:
        sy = board_top + (string_number - 1) * string_gap
        parts.append(f'<line x1="{open_x-8:.1f}" y1="{sy:.1f}" x2="{board_right:.1f}" y2="{sy:.1f}" stroke="{TEXT_COLOR}" stroke-width="{1.0 + string_number * 0.18:.2f}"/>')
        parts.append(svg_text(x + 54, sy + 4, f"{string_number}{string_name}", size=10, weight=700, anchor="end"))

    parts.append(f'<line x1="{nut_x:.1f}" y1="{board_top-13:.1f}" x2="{nut_x:.1f}" y2="{board_bottom+13:.1f}" stroke="rgb(15,15,15)" stroke-width="5"/>')
    for fret in range(1, LAST_FRET + 1):
        fx = nut_x + fret * fret_w
        parts.append(f'<line x1="{fx:.1f}" y1="{board_top-13:.1f}" x2="{fx:.1f}" y2="{board_bottom+13:.1f}" stroke="rgb(75,75,75)" stroke-width="1"/>')

    def fret_x(fret: int) -> float:
        return open_x if fret == 0 else nut_x + (fret - 0.5) * fret_w

    for fret in range(FIRST_FRET, LAST_FRET + 1):
        parts.append(svg_text(fret_x(fret), board_bottom + 31, fret, size=8, weight=650, color=MUTED_COLOR))

    note_by_pc = dict(zip(chord.pcs, chord.notes))
    degree_by_pc = dict(zip(chord.pcs, chord.degrees))
    for string_number, _, open_pc in STRINGS_TOP_TO_BOTTOM:
        sy = board_top + (string_number - 1) * string_gap
        for fret in range(FIRST_FRET, LAST_FRET + 1):
            pc = (open_pc + fret) % 12
            if pc not in degree_by_pc:
                continue
            cx = fret_x(fret)
            degree = degree_by_pc[pc]
            if pc in common:
                parts.append(f'<circle cx="{cx:.1f}" cy="{sy:.1f}" r="12" fill="none" stroke="rgb(52,136,76)" stroke-width="3"/>')
            parts.append(f'<circle cx="{cx:.1f}" cy="{sy:.1f}" r="8.7" fill="{degree_color(degree)}" stroke="{TEXT_COLOR}" stroke-width="1"/>')
            parts.append(render_note_label(cx, sy, degree, note_by_pc[pc], labels))

    parts.append(svg_text(x + width / 2, y + height - 19, "Joue 1-3-5(-7), puis relie au prochain accord sans saut inutile.", size=11, weight=650, color=MUTED_COLOR))
    return "".join(parts)


def generate_svg(
    root: str,
    mode: str,
    progression_name: str,
    progression: tuple[int, ...],
    seventh: bool,
    labels: str,
    output: Path | None = None,
) -> Path:
    harmony = build_harmony(root, mode, seventh)
    progression_chords = [harmony[index] for index in progression]
    if len(progression_chords) == 3:
        progression_chords.append(progression_chords[-1])
    if output is None:
        kind = "septiemes" if seventh else "triades"
        output = Path(f"{safe_token(root)}_{mode}_{safe_token(progression_name)}_{kind}_A4_v1.svg")

    scale = spelled_scale(root, mode)
    mode_title = "majeur" if mode == "majeur" else "mineur naturel"
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        f'<!-- Généré par {SCRIPT_NAME} v{VERSION} — empreinte {script_fingerprint()} -->',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="297mm" height="210mm" viewBox="0 0 {PAGE_W} {PAGE_H}">',
        '<style>@page { size: A4 landscape; margin: 0; }</style>',
        f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="white"/>',
        svg_text(PAGE_W / 2, 47, f"{root} {mode_title} — harmonisation et progression", size=29, weight=800),
        svg_text(PAGE_W / 2, 77, f"Gamme : {' - '.join(scale)}   |   Progression : {progression_name}", size=15, weight=650, color=MUTED_COLOR),
        svg_text(PAGE_W / 2, 102, "But : voir l'accord dans la gamme, puis relier les notes proches au lieu de réciter une position.", size=13, weight=650),
        render_legend(130),
        render_harmony_table(harmony, 166, seventh),
    ]

    card_w = 790
    card_h = 405
    positions = ((65, 265), (899, 265), (65, 700), (899, 700))
    for index, (chord, (x, y)) in enumerate(zip(progression_chords, positions), start=1):
        next_chord = progression_chords[index] if index < len(progression_chords) else None
        parts.append(render_chord_card(chord, next_chord, index, x, y, card_w, card_h, labels))

    parts.append(svg_text(PAGE_W / 2, PAGE_H - 20, f"{SCRIPT_NAME} v{VERSION} — 14 frettes — empreinte {script_fingerprint()}", size=9, weight=500, color=MUTED_COLOR))
    parts.append("</svg>")
    output.write_text("\n".join(parts), encoding="utf-8")
    return output


def validate() -> None:
    g_major = build_harmony("G", "majeur", False)
    if [chord.symbol for chord in g_major] != ["G", "Am", "Bm", "C", "D", "Em", "F#dim"]:
        raise AssertionError("Harmonisation de G majeur incorrecte.")
    a_minor_7 = build_harmony("A", "mineur", True)
    if [chord.symbol for chord in a_minor_7] != ["Am7", "Bm7b5", "Cmaj7", "Dm7", "Em7", "Fmaj7", "G7"]:
        raise AssertionError("Harmonisation de A mineur naturel incorrecte.")
    out = Path("/tmp/__harmonisation_progressions_test.svg")
    name, progression = progression_choice("majeur", "I-IV-V-I")
    generate_svg("G", "majeur", name, progression, False, "mixte", out)
    ET.parse(out)
    svg = out.read_text(encoding="utf-8")
    out.unlink(missing_ok=True)
    required = ["297mm", "A4 landscape", "14 frettes", "I-IV-V-I", "Triades diatoniques"]
    missing = [item for item in required if item not in svg]
    if missing:
        raise AssertionError(f"Éléments manquants dans la fiche : {missing}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Génère une fiche d'harmonisation et de progression sur 14 frettes.")
    parser.add_argument("--tonalite", help="Ex. G, Bb, Am, F#m")
    parser.add_argument("--progression", help="Ex. I-IV-V-I, I-vi-IV-V, i-iv-v-i")
    parser.add_argument("--accords", default="triades", choices=("triades", "septiemes"))
    parser.add_argument("--etiquettes", default="mixte", help="degres, notes ou mixte")
    parser.add_argument("--sortie", help="Chemin du SVG")
    parser.add_argument("--test", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate()
    if args.test:
        print("Validation réussie : harmonisations majeure/mineure, progressions et SVG A4 cohérents.")
        print(f"Version {VERSION} — empreinte {script_fingerprint()}")
        return

    raw_tonality = args.tonalite or input("Tonalité (ex. G, Bb, Am, F#m) : ").strip()
    root, mode = parse_tonality(raw_tonality)
    progression_name, progression = progression_choice(mode, args.progression)
    labels = normalize_labels(args.etiquettes)
    output = Path(args.sortie) if args.sortie else None
    result = generate_svg(
        root=root,
        mode=mode,
        progression_name=progression_name,
        progression=progression,
        seventh=args.accords == "septiemes",
        labels=labels,
        output=output,
    )
    print(f"SVG généré : {result}")
    print(f"Progression : {progression_name} en {root} {mode}")


if __name__ == "__main__":
    main()
