---
name: translate-video-segments
description: Translate ASR transcript segments to Vietnamese or Japanese and resume this repository's video-dubbing pipeline. Use when the user provides a video URL, local video, pipeline work directory, transcript_original.json, or asks Codex to complete a dubbing workflow automatically.
---

# Translate Video Segments

Run a Vietnamese or Japanese dubbing workflow from source video to final
output, or finish an existing work directory that is waiting for translation.

## Guardrails

- Work from the repository root containing `pipeline_vi.py`.
- Never print, copy, or commit values from `.env`.
- Do not install dependencies or use browser cookies without user approval.
- Preserve every source segment and field. Add only `text_vi`.
- Never resume the pipeline until translation validation passes.

## Select The Entry Point

1. If the user gives a work directory or `transcript_original.json`, continue
   from that work directory. Determine the target from
   `TRANSLATE_PENDING.txt`; ask when it is missing and the target is ambiguous.
2. Select the matching pipeline and output schema:

   - Vietnamese: `pipeline_vi.py`, `transcript_vi.json`, `text_vi`
   - Japanese: `pipeline.py`, `transcript_jp.json`, `text_jp`

3. If the user gives a video URL or local video, run phase 1 first:

   ```bash
   python pipeline_vi.py --url "<url>" --source-lang <lang> --voice <male|female>
   python pipeline_vi.py --file "<video>" --source-lang <lang> --voice <male|female>
   python pipeline.py --url "<url>" --source-lang <lang> --voice <azure-voice>
   python pipeline.py --file "<video>" --source-lang <lang> --voice <azure-voice>
   ```

   Reuse the repository virtual environment when one exists. Respect user
   choices for voice, source language, background mode, and output directory.
   The expected phase-1 result is `status=translate_pending` and a work
   directory containing `transcript_original.json`.

4. If required arguments cannot be inferred safely, ask only for the missing
   source language or voice choice.

## Translate

1. Read `<work_dir>/transcript_original.json` as structured JSON.
2. Read `<work_dir>/TRANSLATE_PENDING.txt` and use its `STYLE`,
   `DURATION-AWARE LENGTH`, and `CONSISTENCY` rules as the source of truth. If
   the hint is missing, read the fallback rules in `src/translate_pending.py`.
3. Create the target transcript as one JSON array with the same length, order,
   IDs, and original field values. Add exactly one non-empty target text field
   to every segment (`text_vi` or `text_jp`).
4. Keep translations conversational and concise enough for each segment's
   duration. Maintain one glossary for recurring names, terms, and pronouns.
5. For a long transcript, translate in bounded batches while carrying the same
   glossary forward. Reassemble in original order before validation.
6. For censored or punctuation-only source segments, write a short speakable
   Vietnamese reaction such as `Hả.` or `Á.`. Never write an empty string or
   punctuation-only TTS text.

## Validate And Resume

Run the bundled validator:

```bash
python .agents/skills/translate-video-segments/scripts/validate_translation.py "<work_dir>" --target <vi|jp>
```

Fix every error. Review length warnings and shorten translations that are
clearly too long for their time windows. Then resume:

```bash
python <pipeline_vi.py|pipeline.py> --resume "<work_dir>"
```

When the original local video is outside the work directory, add:

```bash
--file "<original_video>"
```

Report the final video path and any stages that were skipped or could not run.
Do not claim completion unless the pipeline exits successfully and the output
file exists with a non-zero size.
