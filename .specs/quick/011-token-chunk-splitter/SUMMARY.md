# Summary: 011 Token-based PDF chunking

**Date:** 2026-08-31
**Status:** Done

`Policy.chunk_size` / `chunk_overlap` are now 512 / 50 **tiktoken tokens** (`cl100k_base`, same encoding as `text-embedding-3-small`). Retrieve builds the splitter with `RecursiveCharacterTextSplitter.from_tiktoken_encoder` so those numbers are not interpreted as characters.

Already-ingested papers in pgvector keep the old 500-character chunks until they are loaded again (new `arxiv_id`+`version`, or a store reset).
