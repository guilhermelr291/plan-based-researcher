# Quick Task 010: Search-wave ranking by per-step hit indices

**Date:** 2026-08-31
**Status:** Done

## Description

The search-wave judge must rank papers with 0-based indexes into **that step’s** hit list (`ranked_hit_indices`), not invented `arxiv_id`s, so parallel searches on different topics cannot cross-contaminate keys.

## Files Changed

- `src/plan_based_researcher/eval/types.py` — `SearchStepVerdict.ranked_hit_indices` replaces `ranked_keys`
- `src/plan_based_researcher/eval/strategies.py` — number hits `[0]…`; checklist asks for per-step indexes only
- `src/plan_based_researcher/eval/admission.py` — map indexes → `PaperKey` then existing clip + U1

## Verification

- [x] Hit lines are `[n] arxiv_id=… version=…`
- [x] Checklist forbids emitting arxiv ids; asks for indexes of **that** step only
- [x] Two steps: indexes resolve against each step’s own hits (no cross-topic ids)
- [x] Out-of-range / duplicate indexes are dropped; empty mapping cannot pass
- [x] Artifact `ranked_keys` after finalize still hold real `(arxiv_id, version)`

## Commit

(not created — commit when asked)
