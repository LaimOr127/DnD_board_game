#!/bin/sh
set -eu
umask 077

destination=${1:?Pass a directory for backups}
mkdir -p "$destination"
stamp=$(date -u +%Y%m%dT%H%M%S)-$$
temporary=$(mktemp "$destination/.rooms.XXXXXXXX")
trap 'rm -f "$temporary"' EXIT
trap 'exit 1' HUP INT TERM

docker compose exec -T game python - >"$temporary" <<'PY'
import shutil
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

with tempfile.TemporaryDirectory(dir="/data") as temporary:
    snapshot = Path(temporary) / "rooms.sqlite3"
    with closing(sqlite3.connect("file:/data/rooms.sqlite3?mode=ro", uri=True)) as source:
        with closing(sqlite3.connect(snapshot)) as target:
            source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise RuntimeError("SQLite backup failed integrity_check")
    with snapshot.open("rb") as saved:
        shutil.copyfileobj(saved, sys.stdout.buffer)
PY
mv "$temporary" "$destination/rooms-$stamp.sqlite3"
printf '%s\n' "$destination/rooms-$stamp.sqlite3"
