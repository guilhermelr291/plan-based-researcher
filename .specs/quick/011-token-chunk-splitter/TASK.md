# Quick Task 011: Token-based PDF chunking

**Date:** 2026-08-31
**Status:** Done

## Description

Split ingested PDF text by tiktoken tokens (512 / 50 overlap, `cl100k_base`), not characters.

## Files Changed

- `src/plan_based_researcher/policy.py` — `chunk_size=512`, `chunk_overlap=50`, `chunk_encoding=cl100k_base`
- `src/plan_based_researcher/agents/retrieve.py` — `RecursiveCharacterTextSplitter.from_tiktoken_encoder`

## Verification

- [x] Policy values are 512 / 50
- [x] Splitter length is tiktoken token count, not `len(text)`
- [x] Each produced chunk is ≤ 512 tokens under `cl100k_base`

## Commit

(not created — commit when asked)
