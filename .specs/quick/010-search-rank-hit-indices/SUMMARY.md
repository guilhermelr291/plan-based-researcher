# Summary: 010 Search rank via per-step hit indices

**Date:** 2026-08-31
**Status:** Done

## What changed

The search-wave structured output no longer asks the model for `(arxiv_id, version)`. It asks for `ranked_hit_indices`: 0-based positions in **that step’s** hit list. Admission maps those indexes to keys, then clip + U1 run as before. Retrieve still reads `ranked_keys` on the artifact.

Two searches in one wave (e.g. LoRA theory vs QLoRA) each number their own `[0]…`; index `0` on step 1 cannot become step 0’s paper.

## Verification

- Format, checklist, mapping, two-step `finalize_wave_rankings`, empty ranking cannot pass: `ok`

## Commit

(not created — commit when asked)
