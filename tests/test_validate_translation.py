import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


VALIDATOR = (
    Path(__file__).resolve().parents[1]
    / ".agents"
    / "skills"
    / "translate-video-segments"
    / "scripts"
    / "validate_translation.py"
)


def _write_transcripts(work_dir: Path, translated: list[dict]) -> None:
    original = [
        {
            "id": 1,
            "text": "Hello",
            "start": 0.0,
            "end": 1.5,
            "duration": 1.5,
        }
    ]
    (work_dir / "transcript_original.json").write_text(
        json.dumps(original), encoding="utf-8"
    )
    (work_dir / "transcript_vi.json").write_text(
        json.dumps(translated, ensure_ascii=False), encoding="utf-8"
    )


def _run_validator(work_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(work_dir)],
        capture_output=True,
        check=False,
        text=True,
    )


class ValidateTranslationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_accepts_preserved_segments(self) -> None:
        _write_transcripts(
            self.work_dir,
            [
                {
                    "id": 1,
                    "text": "Hello",
                    "start": 0.0,
                    "end": 1.5,
                    "duration": 1.5,
                    "text_vi": "Xin chào",
                }
            ],
        )

        result = _run_validator(self.work_dir)

        self.assertEqual(result.returncode, 0)
        self.assertIn("Validation passed", result.stdout)

    def test_rejects_modified_fields_and_unspeakable_text(self) -> None:
        _write_transcripts(
            self.work_dir,
            [
                {
                    "id": 1,
                    "text": "Changed",
                    "start": 0.0,
                    "end": 1.5,
                    "duration": 1.5,
                    "text_vi": "...",
                }
            ],
        )

        result = _run_validator(self.work_dir)

        self.assertEqual(result.returncode, 1)
        self.assertIn("original field 'text' was modified", result.stderr)
        self.assertIn("punctuation only", result.stderr)

    def test_accepts_japanese_target(self) -> None:
        original = [
            {
                "id": 1,
                "text": "Hello",
                "start": 0.0,
                "end": 1.5,
                "duration": 1.5,
            }
        ]
        translated = [{**original[0], "text_jp": "こんにちは"}]
        (self.work_dir / "transcript_original.json").write_text(
            json.dumps(original), encoding="utf-8"
        )
        (self.work_dir / "transcript_jp.json").write_text(
            json.dumps(translated, ensure_ascii=False), encoding="utf-8"
        )

        result = subprocess.run(
            [sys.executable, str(VALIDATOR), str(self.work_dir), "--target", "jp"],
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Validation passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
