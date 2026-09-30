## Description
<!-- Provide a brief summary of the changes introduced by this pull request. -->

## Motivation & Context
<!-- Why is this change required? What issue does it fix? Link to issue (#123) if applicable. -->

## Changes Checklist
- [ ] Preserves 100% local-first invariant (no telemetry, no external network calls, no cloud APIs).
- [ ] Preserves non-destructive safety (no auto-execution, no shell execution, no arbitrary file overwrites).
- [ ] Does NOT commit any model weights (`.gguf`, `.bin`), databases (`.sqlite`), logs, or secrets.
- [ ] Architecture boundaries respected (UI code does not directly execute business or LLM calls).
- [ ] CPU/RAM usage considered (no unbounded memory allocations or unconstrained loops).
- [ ] Unit/Integration tests added or updated.
- [ ] `ruff check src tests scripts` passes cleanly.
- [ ] `pytest -v` passes cleanly.

## Testing Performed
<!-- Describe the specific tests executed and manual verification steps performed. -->
