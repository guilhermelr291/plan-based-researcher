# Quick Task 008: Search-wave judge must see real paper keys

**Date:** 2026-08-31
**Status:** Done

## Description

Stop search-wave eval from retrying a passing step because the judge invents `arxiv_id`s (`QLoRA-2023`) that clip drops — LangSmith trace `01a058c6-e1a8-71a0-b9e1-44ed67f3f1a6` then burned the 120s timeout on a doomed second wave.

## Files Changed

- `src/plan_based_researcher/eval/strategies.py` — hit lines include `arxiv_id`/`version`; checklist forbids invented ids; truncate abstracts
- `src/plan_based_researcher/eval/admission.py` — clip treats judge `v1` as hit `1`
- `src/plan_based_researcher/agents/planner.py` — explain = one search; original papers are historical; do not demand Hu et al. for a recent-only query

## Verification

- [x] `_format_hit` includes `arxiv_id=2305.14314 version=1`
- [x] Checklist tells the judge to copy keys verbatim
- [x] `clip_ranked_keys` drops `QLoRA-2023` and binds `2305.14314`/`v1` to version `1`
- [x] `finalize_wave_rankings` passes step 1 and fails step 0 for the trace-shaped judgement

## Commit

(not created — commit when asked)
