#!/usr/bin/env python3
"""Build cameras.db (SQLite) from brand and preset JSON files.

Reads brands/*.json and presets/*.json, creates a normalized SQLite database
optimized for fast queries by brand, model, stream type, and URL pattern.

Output: cameras.db in the repository root (or specified path).

Usage:
    python3 scripts/build_sqlite.py                  # outputs ./cameras.db
    python3 scripts/build_sqlite.py -o /tmp/cam.db   # custom output path
"""

import argparse
import json
import os
import sqlite3
import sys
import time

BRANDS_DIR = os.path.join(os.path.dirname(__file__), "..", "brands")
PRESETS_DIR = os.path.join(os.path.dirname(__file__), "..", "presets")

SCHEMA = """
-- Database metadata
CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Camera brands
CREATE TABLE brands (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id  TEXT    NOT NULL UNIQUE,
    brand     TEXT    NOT NULL
);

-- Stream URL patterns
CREATE TABLE streams (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id   TEXT    NOT NULL,
    stream_id  TEXT    NOT NULL,
    url        TEXT    NOT NULL,
    type       TEXT    NOT NULL,
    protocol   TEXT    NOT NULL,
    port       INTEGER NOT NULL DEFAULT 0,
    notes      TEXT,
    FOREIGN KEY (brand_id) REFERENCES brands(brand_id)
);

-- Many-to-many: which models work with which streams
CREATE TABLE stream_models (
    stream_id  INTEGER NOT NULL,
    model      TEXT    NOT NULL,
    FOREIGN KEY (stream_id) REFERENCES streams(id)
);

-- Presets (curated URL pattern lists)
CREATE TABLE presets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    preset_id   TEXT    NOT NULL UNIQUE,
    name        TEXT    NOT NULL,
    description TEXT
);

-- Preset stream entries
CREATE TABLE preset_streams (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    preset_id   TEXT    NOT NULL,
    url         TEXT    NOT NULL,
    type        TEXT    NOT NULL,
    protocol    TEXT    NOT NULL,
    port        INTEGER NOT NULL DEFAULT 0,
    notes       TEXT,
    brand_count INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (preset_id) REFERENCES presets(preset_id)
);

-- Indexes for fast lookups
CREATE INDEX idx_streams_brand_id ON streams(brand_id);
CREATE INDEX idx_streams_type ON streams(type);
CREATE INDEX idx_streams_protocol ON streams(protocol);
CREATE INDEX idx_streams_url ON streams(url);
CREATE INDEX idx_stream_models_model ON stream_models(model);
CREATE INDEX idx_stream_models_stream_id ON stream_models(stream_id);
CREATE INDEX idx_preset_streams_preset_id ON preset_streams(preset_id);
"""


def load_brands(brands_dir):
    """Load all brand JSON files. Yields (filename, data) tuples."""
    for filename in sorted(os.listdir(brands_dir)):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(brands_dir, filename)
        try:
            with open(filepath) as f:
                data = json.load(f)
            if isinstance(data, dict) and "streams" in data:
                yield filename, data
        except (json.JSONDecodeError, IOError) as e:
            print(f"  WARN: skipping {filename}: {e}", file=sys.stderr)


def load_presets(presets_dir):
    """Load all preset JSON files. Yields (filename, data) tuples."""
    if not os.path.isdir(presets_dir):
        return
    for filename in sorted(os.listdir(presets_dir)):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(presets_dir, filename)
        try:
            with open(filepath) as f:
                data = json.load(f)
            if isinstance(data, dict) and "streams" in data:
                yield filename, data
        except (json.JSONDecodeError, IOError) as e:
            print(f"  WARN: skipping preset {filename}: {e}", file=sys.stderr)


def build(output_path):
    """Build the SQLite database."""
    brands_dir = os.path.abspath(BRANDS_DIR)
    presets_dir = os.path.abspath(PRESETS_DIR)

    if not os.path.isdir(brands_dir):
        print(f"Error: brands directory not found: {brands_dir}", file=sys.stderr)
        sys.exit(1)

    # Remove existing db to start fresh
    if os.path.exists(output_path):
        os.remove(output_path)

    conn = sqlite3.connect(output_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(SCHEMA)

    start = time.time()
    brand_count = 0
    stream_count = 0
    model_ref_count = 0

    # Insert brands and streams
    for filename, data in load_brands(brands_dir):
        brand_id = data["brand_id"]
        brand_name = data["brand"]

        conn.execute(
            "INSERT INTO brands (brand_id, brand) VALUES (?, ?)",
            (brand_id, brand_name),
        )
        brand_count += 1

        for stream in data.get("streams", []):
            cursor = conn.execute(
                """INSERT INTO streams (brand_id, stream_id, url, type, protocol, port, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    brand_id,
                    stream["id"],
                    stream["url"],
                    stream["type"],
                    stream["protocol"],
                    stream["port"],
                    stream.get("notes"),
                ),
            )
            row_id = cursor.lastrowid
            stream_count += 1

            # Insert model associations
            for model in stream.get("models", []):
                conn.execute(
                    "INSERT INTO stream_models (stream_id, model) VALUES (?, ?)",
                    (row_id, model),
                )
                model_ref_count += 1

    # Insert presets
    preset_count = 0
    preset_stream_count = 0

    for filename, data in load_presets(presets_dir):
        preset_id = data["preset_id"]
        conn.execute(
            "INSERT INTO presets (preset_id, name, description) VALUES (?, ?, ?)",
            (preset_id, data["name"], data.get("description")),
        )
        preset_count += 1

        for ps in data.get("streams", []):
            conn.execute(
                """INSERT INTO preset_streams (preset_id, url, type, protocol, port, notes, brand_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    preset_id,
                    ps["url"],
                    ps["type"],
                    ps["protocol"],
                    ps["port"],
                    ps.get("notes"),
                    ps.get("brand_count", 0),
                ),
            )
            preset_stream_count += 1

    # Insert metadata
    elapsed = time.time() - start
    conn.execute("INSERT INTO meta VALUES ('version', '2')")
    conn.execute("INSERT INTO meta VALUES ('format', 'StrixCamDB')")
    conn.execute(f"INSERT INTO meta VALUES ('brands', '{brand_count}')")
    conn.execute(f"INSERT INTO meta VALUES ('streams', '{stream_count}')")
    conn.execute(f"INSERT INTO meta VALUES ('presets', '{preset_count}')")

    conn.commit()

    # Optimize: run VACUUM and ANALYZE for compact file and up-to-date stats
    conn.execute("VACUUM")
    conn.execute("ANALYZE")
    conn.close()

    # File size
    size_bytes = os.path.getsize(output_path)
    size_mb = size_bytes / (1024 * 1024)

    print("=" * 50)
    print("SQLite build complete")
    print("=" * 50)
    print(f"  Output:          {output_path}")
    print(f"  File size:       {size_mb:.1f} MB ({size_bytes:,} bytes)")
    print(f"  Brands:          {brand_count}")
    print(f"  Streams:         {stream_count}")
    print(f"  Model refs:      {model_ref_count}")
    print(f"  Presets:         {preset_count}")
    print(f"  Preset streams:  {preset_stream_count}")
    print(f"  Build time:      {elapsed:.2f}s")


def main():
    parser = argparse.ArgumentParser(description="Build cameras.db from JSON sources")
    parser.add_argument(
        "-o", "--output",
        default=os.path.join(os.path.dirname(__file__), "..", "cameras.db"),
        help="Output path for SQLite database (default: ./cameras.db)",
    )
    args = parser.parse_args()
    build(os.path.abspath(args.output))


if __name__ == "__main__":
    main()
