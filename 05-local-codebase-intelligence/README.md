# Local Codebase Explorer

A private, deterministic code search tool built with SQLite FTS5. It indexes source files into overlapping line chunks and returns ranked excerpts with file/line citations. Python 3.10+ with SQLite FTS5 enabled; no API keys or pip packages.

From this directory:

```sh
python explorer.py index .. --db codebase.sqlite
python explorer.py search 'conditional integration saturation' --db codebase.sqlite
python explorer.py search 'telemetry acknowledgement' --db codebase.sqlite --limit 3
```

JSON results contain citations such as `02-pid-playground/playground.py:31-70` and the indexed source text. No matching tokens returns an empty array. This retrieves evidence; it does not generate answers or claim semantic understanding.

## Architecture

Indexing creates a SQLite FTS5 table, replacing the previous snapshot inside a transaction. Files are split into 40-line chunks with a 30-line stride. Queries become OR-connected literal words, ranked with SQLite BM25. Paths and start/end lines accompany each chunk. Search opens the database read-only. Re-index after source changes because citations refer to the indexed snapshot.

Supported extensions: Python, C/C++, JavaScript, TypeScript/TSX, Markdown, Rust and Go. Hidden paths, common dependency/build directories, symlinks, non-UTF8 files and files larger than 256 KB are skipped. Traversal is recursive and suited to small repositories.

## Privacy and limits

No requests leave the process. The database contains source excerpts and should be treated as source code. Filename filters cannot guarantee secret exclusion: review what you index. This baseline has no embeddings, generative model, incremental index, symbol graph or cross-language parser. Word search may miss synonyms and can retrieve unrelated chunks. SQLite must include FTS5; the CLI reports a database error if it does not.

## Evaluation ideas

Maintain questions paired with known source paths. Measure recall@5 and inspect whether line citations support the question. Compare chunk sizes on the same questions. Add embeddings only after measuring where this lexical baseline fails.
