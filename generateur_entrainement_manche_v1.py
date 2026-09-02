#!/usr/bin/env python3
"""Génère une fiche d'exercice A4 et son corrigé.

Le but est de retirer progressivement les réponses visibles. Les quatre
niveaux passent des notes naturelles à la double lecture note + degré. Une
graine rend la fiche reproductible pour pouvoir refaire exactement le même
test après quelques jours.
"""
from __future__ import annotations

import argparse
import hashlib
import random
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from fretboard_core import (
    MUTED_COLOR,
    NATURAL_PITCHES,
    STRINGS_TOP_TO_BOTTOM,
    TEXT_COLOR,
    chromatic_name,
    degree_color,
    parse_tonality,
    pitch_class,
    safe_token,
    scale_degrees,
    scale_intervals,
    spelled_scale,
    svg_text,
)


VERSION = "1.0.0"
SCRIPT_NAME = "generateur_entrainement_manche_v1.py"

PAGE_W = 1240
PAGE_H = 1754
FIRST_FRET = 0
LAST_FRET = 14

SECTION_TOPS = (175, 565, 955, 1345)
SECTION_TITLES = (
    "Cordes graves — 6 et 5",
    "Cordes centrales — 4 et 3",
    "Cordes aiguës — 2 et 1",
    "Mélange sur les six cordes",
)
SECTION_STRINGS = ((6, 5), (4, 3), (2, 1), (1, 2, 3, 4, 5, 6))

LEVELS = {
    1: ("Notes naturelles", "Écris le nom de chaque note naturelle repérée."),
    2: ("Notes chromatiques", "Écris le nom de chaque note, altérations comprises."),
    3: ("Degrés de la tonalité", "Écris le degré de chaque note par rapport à la tonique."),
    4: ("Double lecture", "Écris la note et son degré : la carte doit être lisible dans les deux sens."),
}


@dataclass(frozen=True)
class Question:
    number: int
    string_number: int
    fret: int
    pc: int
    note: str
    degree: str

    def answer(self, level: int) -> str:
        if level in (1, 2):
            return self.note
        if level == 3:
            return self.degree
        return f"{self.note} / {self.degree}"


def script_fingerprint() -> str:
    try:
        return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
    except OSError:
        return "indisponible"


def build_maps(root: str, mode: str) -> tuple[dict[int, str], dict[int, str]]:
    root_pc = pitch_class(root)
    notes = spelled_scale(root, mode)
    degree_by_pc: dict[int, str] = {}
    note_by_pc: dict[int, str] = {}
    for interval, degree, note in zip(scale_intervals(mode), scale_degrees(mode), notes):
        pc = (root_pc + interval) % 12
        degree_by_pc[pc] = degree
        note_by_pc[pc] = note
    return degree_by_pc, note_by_pc


def candidates_for_section(
    root: str,
    mode: str,
    level: int,
    string_numbers: tuple[int, ...],
) -> list[tuple[int, int, int, str, str]]:
    degree_by_pc, note_by_pc = build_maps(root, mode)
    natural_pcs = set(NATURAL_PITCHES.values())
    open_by_string = {number: pc for number, _, pc in STRINGS_TOP_TO_BOTTOM}
    candidates: list[tuple[int, int, int, str, str]] = []
    for string_number in string_numbers:
        open_pc = open_by_string[string_number]
        for fret in range(FIRST_FRET, LAST_FRET + 1):
            pc = (open_pc + fret) % 12
            if level == 1 and pc not in natural_pcs:
                continue
            if level in (3, 4) and pc not in degree_by_pc:
                continue
            note = note_by_pc.get(pc, chromatic_name(pc, root))
            degree = degree_by_pc.get(pc, "—")
            candidates.append((string_number, fret, pc, note, degree))
    return candidates


def allocate_counts(total: int) -> tuple[int, int, int, int]:
    if not 8 <= total <= 32:
        raise ValueError("La quantité doit être comprise entre 8 et 32.")
    base, remainder = divmod(total, 4)
    return tuple(base + (1 if index < remainder else 0) for index in range(4))  # type: ignore[return-value]


def create_questions(root: str, mode: str, level: int, quantity: int, seed: int) -> list[list[Question]]:
    if level not in LEVELS:
        raise ValueError("Niveau invalide : utilise 1, 2, 3 ou 4.")
    rng = random.Random(seed)
    counts = allocate_counts(quantity)
    sections: list[list[Question]] = []
    next_number = 1
    used: set[tuple[int, int]] = set()
    for strings, count in zip(SECTION_STRINGS, counts):
        candidates = candidates_for_section(root, mode, level, strings)
        fresh = [item for item in candidates if (item[0], item[1]) not in used]
        pool = fresh if len(fresh) >= count else candidates
        selected = rng.sample(pool, count)
        selected.sort(key=lambda item: (item[0], item[1]))
        questions: list[Question] = []
        for string_number, fret, pc, note, degree in selected:
            used.add((string_number, fret))
            questions.append(Question(next_number, string_number, fret, pc, note, degree))
            next_number += 1
        sections.append(questions)
    return sections


def fret_x(fret: int) -> float:
    board_left = 174
    board_right = 1180
    open_x = 151
    fret_w = (board_right - board_left) / LAST_FRET
    return open_x if fret == 0 else board_left + (fret - 0.5) * fret_w


def string_y(board_top: float, string_number: int) -> float:
    return board_top + (string_number - 1) * 25


def render_marker(question: Question, board_top: float, level: int, correction: bool) -> str:
    x = fret_x(question.fret)
    y = string_y(board_top, question.string_number)
    if not correction:
        return (
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="10" fill="white" stroke="rgb(35,83,155)" stroke-width="2.3"/>'
            + svg_text(x, y + 3.5, question.number, size=7, weight=800)
        )

    degree = question.degree if question.degree != "—" else "2"
    parts = [
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="10" fill="{degree_color(degree)}" stroke="{TEXT_COLOR}" stroke-width="1.2"/>'
    ]
    if level == 4:
        parts.append(svg_text(x, y - 0.5, question.note, size=5.5, weight=800))
        parts.append(svg_text(x, y + 6, question.degree, size=5, weight=750))
    else:
        parts.append(svg_text(x, y + 3, question.answer(level), size=6.5, weight=800))
    return "".join(parts)


def render_board(board_top: float, questions: list[Question], level: int, correction: bool) -> str:
    board_left = 174
    board_right = 1180
    open_x = 151
    fret_w = (board_right - board_left) / LAST_FRET
    board_bottom = string_y(board_top, 6)
    parts: list[str] = []

    for string_number, string_name, _ in STRINGS_TOP_TO_BOTTOM:
        y = string_y(board_top, string_number)
        parts.append(f'<line x1="{open_x-12:.1f}" y1="{y:.1f}" x2="{board_right:.1f}" y2="{y:.1f}" stroke="{TEXT_COLOR}" stroke-width="{1.0 + string_number * 0.17:.2f}"/>')
        parts.append(svg_text(115, y + 4, f"{string_number}{string_name}", size=11, weight=700, anchor="end"))

    parts.append(f'<line x1="{board_left:.1f}" y1="{board_top-13:.1f}" x2="{board_left:.1f}" y2="{board_bottom+13:.1f}" stroke="rgb(15,15,15)" stroke-width="6"/>')
    for fret in range(1, LAST_FRET + 1):
        x = board_left + fret * fret_w
        parts.append(f'<line x1="{x:.1f}" y1="{board_top-13:.1f}" x2="{x:.1f}" y2="{board_bottom+13:.1f}" stroke="rgb(80,80,80)" stroke-width="1"/>')
    for fret in range(FIRST_FRET, LAST_FRET + 1):
        parts.append(svg_text(fret_x(fret), board_bottom + 25, fret, size=8, weight=650, color=MUTED_COLOR))
    for question in questions:
        parts.append(render_marker(question, board_top, level, correction))
    return "".join(parts)


def render_answers(top: float, questions: list[Question], level: int, correction: bool) -> str:
    parts: list[str] = []
    columns = 3
    column_w = 355
    start_x = 92
    for index, question in enumerate(questions):
        row = index // columns
        col = index % columns
        x = start_x + col * column_w
        y = top + row * 32
        location = f"{question.number}. corde {question.string_number}, case {question.fret}"
        parts.append(svg_text(x, y, location, size=10, weight=650, anchor="start"))
        answer_x = x + 176
        if correction:
            parts.append(svg_text(answer_x, y, f"= {question.answer(level)}", size=10, weight=800, anchor="start"))
        else:
            parts.append(f'<line x1="{answer_x:.1f}" y1="{y+3:.1f}" x2="{x+325:.1f}" y2="{y+3:.1f}" stroke="rgb(120,120,120)" stroke-width="1"/>')
    return "".join(parts)


def render_section(
    section_index: int,
    top: float,
    questions: list[Question],
    level: int,
    correction: bool,
) -> str:
    board_top = top + 68
    parts = [
        f'<line x1="48" y1="{top:.1f}" x2="1192" y2="{top:.1f}" stroke="rgb(175,175,175)" stroke-width="1.1"/>',
        svg_text(66, top + 28, section_index + 1, size=13, weight=800),
        svg_text(96, top + 28, SECTION_TITLES[section_index], size=17, weight=750, anchor="start"),
        render_board(board_top, questions, level, correction),
        render_answers(top + 278, questions, level, correction),
    ]
    return "".join(parts)


def render_page(
    root: str,
    mode: str,
    level: int,
    seed: int,
    sections: list[list[Question]],
    correction: bool,
) -> str:
    level_title, instruction = LEVELS[level]
    page_kind = "CORRIGÉ" if correction else "EXERCICE"
    scale = spelled_scale(root, mode)
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        f'<!-- Généré par {SCRIPT_NAME} v{VERSION} — empreinte {script_fingerprint()} -->',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 {PAGE_W} {PAGE_H}">',
        '<style>@page { size: A4 portrait; margin: 0; }</style>',
        f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="white"/>',
        svg_text(PAGE_W / 2, 42, f"{page_kind} — {level_title}", size=25, weight=800),
        svg_text(PAGE_W / 2, 70, f"{root} {mode} — niveau {level} — série {seed}", size=14, weight=700, color=MUTED_COLOR),
        svg_text(PAGE_W / 2, 96, instruction, size=12, weight=650),
        svg_text(PAGE_W / 2, 118, f"Référence tonale : {' - '.join(scale)}", size=10, weight=550, color=MUTED_COLOR),
        svg_text(PAGE_W / 2, 146, "Objectif : 90 % juste en moins de 8 minutes, puis rejouer la même série 48 h plus tard.", size=11, weight=700),
    ]
    for index, (top, questions) in enumerate(zip(SECTION_TOPS, sections)):
        parts.append(render_section(index, top, questions, level, correction))
    parts.append(svg_text(PAGE_W / 2, PAGE_H - 16, f"{SCRIPT_NAME} v{VERSION} — 14 frettes — série {seed} — empreinte {script_fingerprint()}", size=8, weight=500, color=MUTED_COLOR))
    parts.append("</svg>")
    return "\n".join(parts)


def generate_pair(
    root: str,
    mode: str,
    level: int,
    quantity: int,
    seed: int,
    output_dir: Path,
) -> tuple[Path, Path]:
    sections = create_questions(root, mode, level, quantity, seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{safe_token(root)}_{mode}_entrainement_niveau_{level}_serie_{seed}"
    exercise = output_dir / f"{stem}_exercice.svg"
    correction = output_dir / f"{stem}_corrige.svg"
    exercise.write_text(render_page(root, mode, level, seed, sections, False), encoding="utf-8")
    correction.write_text(render_page(root, mode, level, seed, sections, True), encoding="utf-8")
    return exercise, correction


def validate() -> None:
    a = create_questions("G", "majeur", 3, 24, 42)
    b = create_questions("G", "majeur", 3, 24, 42)
    if a != b:
        raise AssertionError("Une même série doit être reproductible.")
    if sum(len(section) for section in a) != 24:
        raise AssertionError("Le nombre de questions est incorrect.")
    g_scale_pcs = {(pitch_class("G") + interval) % 12 for interval in scale_intervals("majeur")}
    if any(question.pc not in g_scale_pcs for section in a for question in section):
        raise AssertionError("Le niveau degrés contient une note hors gamme.")
    natural = create_questions("G", "majeur", 1, 20, 7)
    if any(question.pc not in set(NATURAL_PITCHES.values()) for section in natural for question in section):
        raise AssertionError("Le niveau 1 contient une note altérée.")
    temp = Path("/tmp/__entrainement_manche_test")
    exercise, correction = generate_pair("G", "majeur", 4, 24, 99, temp)
    ET.parse(exercise)
    ET.parse(correction)
    svg = exercise.read_text(encoding="utf-8")
    if not all(item in svg for item in ("210mm", "A4 portrait", "14 frettes", "série 99")):
        raise AssertionError("Métadonnées A4 ou série absentes.")
    exercise.unlink(missing_ok=True)
    correction.unlink(missing_ok=True)
    temp.rmdir()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Génère une fiche de rappel actif et son corrigé sur 14 frettes.")
    parser.add_argument("--tonalite", help="Ex. G, Bb, Am, F#m")
    parser.add_argument("--niveau", type=int, choices=(1, 2, 3, 4), default=1)
    parser.add_argument("--quantite", type=int, default=24, help="De 8 à 32 questions")
    parser.add_argument("--serie", type=int, default=1, help="Graine reproductible")
    parser.add_argument("--dossier", type=Path, default=Path("."))
    parser.add_argument("--test", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate()
    if args.test:
        print("Validation réussie : quatre niveaux, séries reproductibles, exercice/corrigé A4 cohérents.")
        print(f"Version {VERSION} — empreinte {script_fingerprint()}")
        return
    raw_tonality = args.tonalite or input("Tonalité (ex. G, Bb, Am, F#m) : ").strip()
    root, mode = parse_tonality(raw_tonality)
    exercise, correction = generate_pair(root, mode, args.niveau, args.quantite, args.serie, args.dossier)
    print(f"Exercice : {exercise}")
    print(f"Corrigé : {correction}")


if __name__ == "__main__":
    main()

