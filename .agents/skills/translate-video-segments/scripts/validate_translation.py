#!/usr/bin/env python3
"""Validate a translated transcript before resuming the dubbing pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = ("id", "text", "start", "end", "duration")


def _reject_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def _load_array(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle, parse_constant=_reject_constant)
    if not isinstance(data, list):
        raise ValueError(f"{path.name} must contain a JSON array")
    if not all(isinstance(item, dict) for item in data):
        raise ValueError(f"every item in {path.name} must be a JSON object")
    return data


def _resolve_target(work_dir: Path, target: str | None) -> str:
    if target:
        if target not in {"vi", "jp"}:
            raise ValueError("target must be vi or jp")
        return target
    candidates = [
        code
        for code, filename in (("vi", "transcript_vi.json"), ("jp", "transcript_jp.json"))
        if (work_dir / filename).is_file()
    ]
    if len(candidates) != 1:
        raise ValueError("cannot infer target; pass --target vi or --target jp")
    return candidates[0]


def validate(work_dir: Path, target: str | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    original_path = work_dir / "transcript_original.json"
    try:
        target = _resolve_target(work_dir, target)
    except ValueError as exc:
        return [str(exc)], warnings
    translated_filename = "transcript_vi.json" if target == "vi" else "transcript_jp.json"
    text_field = "text_vi" if target == "vi" else "text_jp"
    max_chars_per_second = 15 if target == "vi" else 10
    translated_path = work_dir / translated_filename

    for path in (original_path, translated_path):
        if not path.is_file():
            errors.append(f"missing file: {path}")
    if errors:
        return errors, warnings

    try:
        original = _load_array(original_path)
        translated = _load_array(translated_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [str(exc)], warnings

    if len(original) != len(translated):
        errors.append(
            f"segment count differs: original={len(original)}, translated={len(translated)}"
        )

    original_ids = [item.get("id") for item in original]
    translated_ids = [item.get("id") for item in translated]
    if len(set(map(repr, original_ids))) != len(original_ids):
        errors.append("transcript_original.json contains duplicate IDs")
    if original_ids != translated_ids:
        errors.append("translated IDs or segment order differ from the original")

    for index, (source, translated_segment) in enumerate(zip(original, translated)):
        label = f"segment {source.get('id', index)!r}"
        missing_source = [field for field in REQUIRED_FIELDS if field not in source]
        if missing_source:
            errors.append(f"{label}: original is missing {', '.join(missing_source)}")

        for key, value in source.items():
            if key not in translated_segment:
                errors.append(f"{label}: translated object dropped field {key!r}")
            elif translated_segment[key] != value:
                errors.append(f"{label}: original field {key!r} was modified")

        unexpected_fields = set(translated_segment) - set(source) - {text_field}
        if unexpected_fields:
            errors.append(
                f"{label}: unexpected translated fields: "
                f"{', '.join(sorted(unexpected_fields))}"
            )

        translated_text = translated_segment.get(text_field)
        if not isinstance(translated_text, str) or not translated_text.strip():
            errors.append(f"{label}: {text_field} must be a non-empty string")
            continue
        if not any(character.isalnum() for character in translated_text):
            errors.append(f"{label}: {text_field} cannot contain punctuation only")

        duration = source.get("duration")
        if isinstance(duration, (int, float)) and duration > 0:
            soft_limit = max(12, int(duration * max_chars_per_second) + 6)
            if len(translated_text) > soft_limit:
                warnings.append(
                    f"{label}: {text_field} has {len(translated_text)} characters for "
                    f"{duration:.2f}s (soft limit {soft_limit})"
                )

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a translated transcript against transcript_original.json."
    )
    parser.add_argument("work_dir", type=Path)
    parser.add_argument("--target", choices=("vi", "jp"))
    args = parser.parse_args()

    errors, warnings = validate(args.work_dir.expanduser().resolve(), args.target)
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    if errors:
        print(f"Validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1
    print(f"Validation passed with {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
