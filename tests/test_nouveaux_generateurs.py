from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from generateur_entrainement_manche_v1 import create_questions, generate_pair
from generateur_harmonisation_progressions_v1 import (
    build_harmony,
    generate_svg,
    progression_choice,
)


class TrainingGeneratorTests(unittest.TestCase):
    def test_series_are_reproducible(self) -> None:
        first = create_questions("G", "majeur", 4, 24, 123)
        second = create_questions("G", "majeur", 4, 24, 123)
        self.assertEqual(first, second)

    def test_pair_is_valid_a4_svg(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            exercise, correction = generate_pair("A", "mineur", 3, 20, 5, Path(directory))
            ET.parse(exercise)
            ET.parse(correction)
            self.assertIn('width="210mm"', exercise.read_text(encoding="utf-8"))

    def test_script_runs_alone_without_companion_module(self) -> None:
        source = Path(__file__).parents[1] / "generateur_entrainement_manche_v1.py"
        with tempfile.TemporaryDirectory() as directory:
            isolated = Path(directory) / source.name
            shutil.copy2(source, isolated)
            result = subprocess.run(
                [sys.executable, str(isolated), "--test"],
                cwd=directory,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


class HarmonyGeneratorTests(unittest.TestCase):
    def test_major_triad_harmonization(self) -> None:
        symbols = [chord.symbol for chord in build_harmony("C", "majeur", False)]
        self.assertEqual(symbols, ["C", "Dm", "Em", "F", "G", "Am", "Bdim"])

    def test_minor_seventh_harmonization(self) -> None:
        symbols = [chord.symbol for chord in build_harmony("A", "mineur", True)]
        self.assertEqual(symbols, ["Am7", "Bm7b5", "Cmaj7", "Dm7", "Em7", "Fmaj7", "G7"])

    def test_harmony_sheet_is_valid_a4_svg(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            name, progression = progression_choice("majeur", "ii-V-I")
            output = Path(directory) / "sheet.svg"
            generate_svg("C", "majeur", name, progression, True, "mixte", output)
            ET.parse(output)
            self.assertIn('width="297mm"', output.read_text(encoding="utf-8"))

    def test_script_runs_alone_without_companion_module(self) -> None:
        source = Path(__file__).parents[1] / "generateur_harmonisation_progressions_v1.py"
        with tempfile.TemporaryDirectory() as directory:
            isolated = Path(directory) / source.name
            shutil.copy2(source, isolated)
            result = subprocess.run(
                [sys.executable, str(isolated), "--test"],
                cwd=directory,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
