#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import re
import unicodedata
import webbrowser
from pathlib import Path

FIRST_FRET = 0
LAST_FRET = 15
TUNING = [("E", 4), ("B", 11), ("G", 7), ("D", 2), ("A", 9), ("E", 4)]

NATURAL_PCS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
LETTERS = ["C", "D", "E", "F", "G", "A", "B"]

MAJOR_INTERVALS = [0, 2, 4, 5, 7, 9, 11]
MAJOR_DEGREES = ["1", "2", "3", "4", "5", "6", "7"]
MINOR_INTERVALS = [0, 2, 3, 5, 7, 8, 10]
MINOR_DEGREES = ["1", "2", "b3", "4", "5", "b6", "b7"]

MAJOR_PENTA = {0, 2, 4, 7, 9}
MINOR_PENTA = {0, 3, 5, 7, 10}
MAJOR_TRIAD = {0, 4, 7}
MINOR_TRIAD = {0, 3, 7}

W = 1320
LEFT = 95
RIGHT = 45
FRET_W = (W - LEFT - RIGHT) / (LAST_FRET - FIRST_FRET + 1)
STRING_GAP = 48
BOARD_H = STRING_GAP * 5
NOTE_R = 17

BG = "#ffffff"
TEXT = "#202020"
GRID = "#333333"
ROOT_FILL = "#ff9696"
THIRD_FILL = "#ffd991"
FIFTH_FILL = "#a8d3ff"
OTHER_FILL = "#eeeeee"
CHORD_STROKE = "#7c3aed"
PENTA_STROKE = "#2563eb"


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def pitch_class(note: str) -> int:
    letter = note[0].upper()
    accidental = note[1:]
    return (NATURAL_PCS[letter] + accidental.count("#") - accidental.count("b")) % 12


def normalize_note(value: str) -> str:
    value = value.strip().replace("♯", "#").replace("♭", "b").replace(" ", "")
    ascii_value = strip_accents(value).lower()

    fr = re.fullmatch(r"(do|re|mi|fa|sol|la|si)([#b]?)", ascii_value)
    if fr:
        name, accidental = fr.groups()
        letter = {"do": "C", "re": "D", "mi": "E", "fa": "F",
                  "sol": "G", "la": "A", "si": "B"}[name]
        return letter + accidental

    international = re.fullmatch(r"([a-g])([#b]?)", ascii_value)
    if not international:
        raise ValueError("Tonalité invalide. Exemples : C, F#, Bb, Am, F#m, Sib.")
    letter, accidental = international.groups()
    return letter.upper() + accidental


def parse_key(value: str) -> tuple[str, str]:
    cleaned = value.strip().replace(" ", "")
    minor = cleaned.lower().endswith("m")
    note_part = cleaned[:-1] if minor else cleaned
    return normalize_note(note_part), ("minor" if minor else "major")


def accidental(delta: int) -> str:
    if delta > 0:
        return "#" * delta
    if delta < 0:
        return "b" * (-delta)
    return ""


def spelled_scale(root: str, intervals: list[int]) -> list[str]:
    root_pc = pitch_class(root)
    start_letter = LETTERS.index(root[0])
    result = []
    for index, interval in enumerate(intervals):
        letter = LETTERS[(start_letter + index) % 7]
        target = (root_pc + interval) % 12
        delta = (target - NATURAL_PCS[letter]) % 12
        if delta > 6:
            delta -= 12
        result.append(letter + accidental(delta))
    return result


def relative_pair(root: str, mode: str) -> tuple[str, str, list[str]]:
    if mode == "major":
        major_root = root
        major_scale = spelled_scale(major_root, MAJOR_INTERVALS)
        minor_root = major_scale[5]
    else:
        minor_root = root
        minor_scale = spelled_scale(minor_root, MINOR_INTERVALS)
        major_root = minor_scale[2]
        major_scale = spelled_scale(major_root, MAJOR_INTERVALS)
    return major_root, minor_root, major_scale


def degree_map(root_pc: int, intervals: list[int], degrees: list[str]) -> dict[int, str]:
    return {(root_pc + interval) % 12: degree for interval, degree in zip(intervals, degrees)}


def fill_for_interval(interval: int, mode: str) -> str:
    if interval == 0:
        return ROOT_FILL
    if interval == (4 if mode == "major" else 3):
        return THIRD_FILL
    if interval == 7:
        return FIFTH_FILL
    return OTHER_FILL


def svg_text(x: float, y: float, text: str, size: int = 18, weight: int = 400,
             anchor: str = "middle", color: str = TEXT) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="Arial, Helvetica, sans-serif" font-size="{size}" '
        f'font-weight="{weight}" fill="{color}">{html.escape(text)}</text>'
    )


def draw_board(title: str, subtitle: str, tonic: str, mode: str,
               scale_pcs: set[int], penta_only: bool, y0: float) -> tuple[str, float]:
    root_pc = pitch_class(tonic)
    intervals = MAJOR_INTERVALS if mode == "major" else MINOR_INTERVALS
    degrees = MAJOR_DEGREES if mode == "major" else MINOR_DEGREES
    deg_map = degree_map(root_pc, intervals, degrees)
    penta = MAJOR_PENTA if mode == "major" else MINOR_PENTA
    triad = MAJOR_TRIAD if mode == "major" else MINOR_TRIAD

    out = []
    out.append(svg_text(W / 2, y0, title, 26, 700))
    out.append(svg_text(W / 2, y0 + 27, subtitle, 16, 500, color="#666666"))

    top = y0 + 68
    bottom = top + BOARD_H

    for fret in range(FIRST_FRET, LAST_FRET + 2):
        x = LEFT + fret * FRET_W
        width = 8 if fret == 0 else 2
        out.append(f'<line x1="{x:.1f}" y1="{top:.1f}" x2="{x:.1f}" y2="{bottom:.1f}" '
                   f'stroke="{GRID}" stroke-width="{width}"/>')

    for string_index in range(6):
        y = top + string_index * STRING_GAP
        out.append(f'<line x1="{LEFT:.1f}" y1="{y:.1f}" x2="{W-RIGHT:.1f}" y2="{y:.1f}" '
                   f'stroke="{GRID}" stroke-width="{1.6 + string_index * 0.22:.2f}"/>')
        out.append(svg_text(LEFT - 32, y + 6, str(string_index + 1), 14, 700))
        out.append(svg_text(LEFT - 58, y + 6, TUNING[string_index][0], 14, 700))

    for fret in range(0, LAST_FRET + 1):
        x = LEFT + (fret + 0.5) * FRET_W
        out.append(svg_text(x, bottom + 31, str(fret), 14, 600, color="#555555"))

    for string_index, (_, open_pc) in enumerate(TUNING):
        y = top + string_index * STRING_GAP
        for fret in range(FIRST_FRET, LAST_FRET + 1):
            pc = (open_pc + fret) % 12
            if pc not in scale_pcs:
                continue

            interval = (pc - root_pc) % 12
            if penta_only and interval not in penta:
                continue

            x = LEFT + (fret + 0.5) * FRET_W
            fill = fill_for_interval(interval, mode)
            in_penta = interval in penta
            in_chord = interval in triad

            stroke = PENTA_STROKE if in_penta else "#888888"
            stroke_w = 4 if in_penta else 1.5
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{NOTE_R}" '
                       f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w}"/>')
            if in_chord:
                out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{NOTE_R + 5}" '
                           f'fill="none" stroke="{CHORD_STROKE}" stroke-width="3" '
                           f'stroke-dasharray="6 4"/>')

            out.append(svg_text(x, y + 6, deg_map[pc], 14, 700))

    return "\n".join(out), bottom + 55


def conversion_table(major_root: str, minor_root: str, major_notes: list[str], y0: float) -> tuple[str, float]:
    major_degree_by_pc = degree_map(pitch_class(major_root), MAJOR_INTERVALS, MAJOR_DEGREES)
    minor_degree_by_pc = degree_map(pitch_class(minor_root), MINOR_INTERVALS, MINOR_DEGREES)

    row_h = 42
    out = [svg_text(W / 2, y0, "Table de conversion des degrés", 25, 700)]
    y = y0 + 35

    headers = ["Note", f"Degré en {major_root}", f"Degré en {minor_root}m"]
    widths = [170, 300, 300]
    total = sum(widths)
    start = (W - total) / 2

    x = start
    for label, width in zip(headers, widths):
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{width}" height="{row_h}" '
                   'fill="#e8e8e8" stroke="#777"/>')
        out.append(svg_text(x + width / 2, y + 27, label, 16, 700))
        x += width

    y += row_h
    for index, note in enumerate(major_notes):
        pc = pitch_class(note)
        values = [note, major_degree_by_pc[pc], minor_degree_by_pc[pc]]
        x = start
        for value, width in zip(values, widths):
            fill = "#ffffff" if index % 2 == 0 else "#f7f7f7"
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{width}" height="{row_h}" '
                       f'fill="{fill}" stroke="#999"/>')
            out.append(svg_text(x + width / 2, y + 27, value, 16, 600))
            x += width
        y += row_h

    return "\n".join(out), y + 25


def safe_name(note: str) -> str:
    return note.replace("#", "sharp").replace("b", "flat")


def generate(key: str, output: Path | None = None, open_result: bool = False) -> Path:
    root, mode = parse_key(key)
    major_root, minor_root, common_notes = relative_pair(root, mode)

    major_pc = pitch_class(major_root)
    common_pcs = {(major_pc + i) % 12 for i in MAJOR_INTERVALS}

    if output is None:
        output = Path(f"relatifs_{safe_name(major_root)}_{safe_name(minor_root)}m.svg")

    parts = []
    y = 50.0
    parts.append(svg_text(W / 2, y, f"{major_root} majeur ↔ {minor_root} mineur", 34, 700))
    y += 34
    parts.append(svg_text(
        W / 2, y,
        "Même collection de notes ; seule la tonique et donc la numérotation des degrés changent.",
        17, 500, color="#555555"
    ))
    y += 32
    parts.append(svg_text(
        W / 2, y,
        f"Notes communes : {' – '.join(common_notes)}",
        18, 600
    ))
    y += 36
    parts.append(svg_text(
        W / 2, y,
        "Contour bleu = pentatonique · contour violet pointillé = triade · rouge = tonique",
        15, 600, color="#555555"
    ))
    y += 35

    board, y = draw_board(
        f"Pentatonique majeure de {major_root}",
        "Lecture majeure : 1 – 2 – 3 – 5 – 6",
        major_root, "major", common_pcs, True, y
    )
    parts.append(board)
    y += 25

    board, y = draw_board(
        f"Gamme majeure de {major_root}",
        "Lecture majeure complète : 1 – 2 – 3 – 4 – 5 – 6 – 7",
        major_root, "major", common_pcs, False, y
    )
    parts.append(board)
    y += 25

    board, y = draw_board(
        f"Pentatonique mineure de {minor_root}",
        "Les mêmes cinq notes, relues depuis la tonique mineure : 1 – b3 – 4 – 5 – b7",
        minor_root, "minor", common_pcs, True, y
    )
    parts.append(board)
    y += 25

    board, y = draw_board(
        f"Gamme mineure naturelle de {minor_root}",
        "Les mêmes sept notes, relues : 1 – 2 – b3 – 4 – 5 – b6 – b7",
        minor_root, "minor", common_pcs, False, y
    )
    parts.append(board)
    y += 25

    table, y = conversion_table(major_root, minor_root, common_notes, y)
    parts.append(table)

    parts.append(svg_text(
        W / 2, y,
        f"Repère : {minor_root} est le 6e degré de {major_root} majeur ; "
        f"{major_root} est le b3 de {minor_root} mineur.",
        17, 700
    ))
    y += 45

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{int(y)}"
     viewBox="0 0 {W} {int(y)}">
<rect width="100%" height="100%" fill="{BG}"/>
{''.join(parts)}
</svg>
'''
    output.write_text(svg, encoding="utf-8")
    print(f"Généré : {output.resolve()}")
    print(f"Correspondance : {major_root} majeur ↔ {minor_root} mineur")
    print(f"Notes communes : {' - '.join(common_notes)}")

    if open_result:
        webbrowser.open(output.resolve().as_uri())
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Génère un visuel SVG des gammes relatives majeure et mineure sur le manche."
    )
    parser.add_argument(
        "tonalite", nargs="?",
        help="Tonalité majeure ou mineure, par exemple C, F#, Bb, Am, F#m."
    )
    parser.add_argument("-o", "--sortie", type=Path, help="Chemin du SVG généré.")
    parser.add_argument("--ouvrir", action="store_true", help="Ouvre le SVG après génération.")
    args = parser.parse_args()

    key = args.tonalite
    if not key:
        key = input("Tonalité majeure ou mineure (ex. C, Bb, Am, F#m) : ").strip()

    try:
        generate(key, args.sortie, args.ouvrir)
    except ValueError as exc:
        raise SystemExit(f"Erreur : {exc}") from exc


if __name__ == "__main__":
    main()
