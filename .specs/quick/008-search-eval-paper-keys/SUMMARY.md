# Summary: 008 Search-wave judge paper keys

**Date:** 2026-08-31
**Status:** Done

## What changed

Trace `01a058c6-e1a8-71a0-b9e1-44ed67f3f1a6` (`Explain how LoRA adapts transformer weights, using recent arXiv papers`) hit `CancelledError` at 120s during the second search-wave eval. Search itself succeeded. The first judge marked step 1 (QLoRA) `passed=true` but ranked `QLoRA-2023` / `QDyLoRA-2024` / `QA-LoRA-2023` because hit lines had titles and abstracts only. Clip emptied that ranking, both steps retried, and the timeout cancelled the retry eval.

Hit formatting now prints real keys, clip accepts `v1` vs `1`, and the planner prompt tells explain queries to use one search without requiring the 2021 LoRA paper when the student asked for recent work.

## Verification

- Format + checklist + clip + `finalize_wave_rankings` on the trace-shaped keys: `ok`

## Commit

(not created — commit when asked)
