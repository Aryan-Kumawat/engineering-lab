"""Local code search with SQLite FTS5 and file/line citations. Python 3.10+."""
import argparse
import json
import re
import sqlite3
from pathlib import Path

EXTENSIONS = {'.py', '.cpp', '.c', '.h', '.hpp', '.js', '.ts', '.tsx', '.md', '.rs', '.go'}
IGNORED = {'.git', 'node_modules', 'build', 'dist', '__pycache__', '.venv', 'venv'}


def index(root, database):
    root = root.resolve()
    if not root.is_dir():
        raise ValueError('Root must be a directory')
    files = chunks = 0
    with sqlite3.connect(database) as db:
        db.execute('CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(path UNINDEXED, start UNINDEXED, end UNINDEXED, body)')
        db.execute('DELETE FROM chunks')
        for path in sorted(root.rglob('*')):
            relative = path.relative_to(root)
            if any(part in IGNORED or part.startswith('.') for part in relative.parts):
                continue
            # Skip symlinks, including files below symlinked directories.
            if any(parent.is_symlink() for parent in [path, *path.parents] if parent != root):
                continue
            if not path.is_file() or path.suffix not in EXTENSIONS or path.stat().st_size > 256_000:
                continue
            try:
                lines = path.read_text(encoding='utf-8').splitlines()
            except (UnicodeError, OSError):
                continue
            files += 1
            for start in range(0, len(lines), 30):
                body = '\n'.join(lines[start:start+40])
                db.execute('INSERT INTO chunks VALUES (?,?,?,?)',
                           (relative.as_posix(), start+1, min(start+40, len(lines)), body))
                chunks += 1
    return {'files': files, 'chunks': chunks}


def search(database, query, limit=5):
    if not 1 <= limit <= 20:
        raise ValueError('limit must be 1..20')
    tokens = re.findall(r'\w+', query, re.UNICODE)
    if not tokens:
        return []
    # Escape user terms; do not expose the FTS query language directly.
    expression = ' OR '.join('"'+term.replace('"', '""')+'"' for term in tokens)
    if not database.is_file():
        raise ValueError('Index missing; run index first')
    with sqlite3.connect(f'file:{database.resolve().as_posix()}?mode=ro', uri=True) as db:
        rows = db.execute('SELECT path,start,end,body FROM chunks WHERE chunks MATCH ? ORDER BY bm25(chunks),path,start LIMIT ?',
                          (expression, limit)).fetchall()
    return [{'citation': f'{p}:{a}-{b}', 'excerpt': text} for p,a,b,text in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['index', 'search'])
    parser.add_argument('input', help='Repository path or search question')
    parser.add_argument('--db', type=Path, default=Path('codebase.sqlite'))
    parser.add_argument('--limit', type=int, default=5)
    args = parser.parse_args()
    try:
        result = index(Path(args.input), args.db) if args.mode == 'index' else search(args.db, args.input, args.limit)
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
