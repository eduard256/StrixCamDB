#!/usr/bin/env python3
"""Convert legacy camera database to StrixCamDB v2 format.

Reads from legacy/brands/*.json and writes to brands/*.json.
Applies minimal transformations: removes dead fields, deduplicates,
skips empty URLs, converts ALL to wildcard. Everything else is preserved as-is.
"""

import json
import os
import sys

LEGACY_DIR = os.path.join(os.path.dirname(__file__), "..", "legacy", "brands")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "brands")

# Files to skip entirely
SKIP_FILES = {"index.json", "indexa.json"}

# Brands to skip (different format or empty)
SKIP_BRANDS = {"auto"}

# Stats
stats = {
    "brands_processed": 0,
    "brands_skipped": 0,
    "streams_total": 0,
    "streams_skipped_empty_url": 0,
    "streams_skipped_duplicate": 0,
    "models_all_converted": 0,
    "streams_skipped_empty_type": 0,
    "streams_skipped_empty_models": 0,
}


def convert_brand(data, brand_id):
    """Convert a single brand from legacy to v2 format.

    Returns the new brand dict or None if it should be skipped.
    """
    # Must be a dict with entries
    if not isinstance(data, dict):
        return None
    if "entries" not in data and "cameras" in data:
        # auto.json-style format, skip
        return None
    if "entries" not in data:
        return None

    brand_name = data.get("brand", "")
    if not brand_name:
        return None

    streams = []
    seen_urls = set()
    counter = 0

    for entry in data["entries"]:
        url = entry.get("url", "")

        # Skip empty URLs
        if not url.strip():
            stats["streams_skipped_empty_url"] += 1
            continue

        # Skip entries with empty type
        if not entry.get("type", "").strip():
            stats["streams_skipped_empty_type"] += 1
            continue

        # Skip entries with empty models list
        if not entry.get("models"):
            stats["streams_skipped_empty_models"] += 1
            continue

        # Deduplicate by protocol:port:url
        proto = entry.get("protocol", "")
        port = entry.get("port", 0)
        dedup_key = f"{proto}:{port}:{url}"
        if dedup_key in seen_urls:
            stats["streams_skipped_duplicate"] += 1
            continue
        seen_urls.add(dedup_key)

        counter += 1

        # Build stream object
        stream = {
            "id": f"{brand_id}-{counter}",
            "url": url,
            "type": entry.get("type", ""),
            "protocol": proto,
            "port": port,
        }

        # Convert models: ["ALL"] -> ["*"]
        models = entry.get("models", [])
        if models == ["ALL"]:
            models = ["*"]
            stats["models_all_converted"] += 1
        stream["models"] = models

        # Keep notes if present and non-empty
        notes = entry.get("notes", "")
        if notes and notes.strip():
            stream["notes"] = notes.strip()

        streams.append(stream)
        stats["streams_total"] += 1

    if not streams:
        return None

    return {
        "version": 2,
        "brand": brand_name,
        "brand_id": brand_id,
        "streams": streams,
    }


def main():
    legacy_dir = os.path.abspath(LEGACY_DIR)
    output_dir = os.path.abspath(OUTPUT_DIR)

    if not os.path.isdir(legacy_dir):
        print(f"Error: legacy directory not found: {legacy_dir}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    files = sorted(f for f in os.listdir(legacy_dir) if f.endswith(".json"))

    for filename in files:
        if filename in SKIP_FILES:
            stats["brands_skipped"] += 1
            continue

        brand_id = filename.replace(".json", "")
        if brand_id in SKIP_BRANDS:
            stats["brands_skipped"] += 1
            continue

        filepath = os.path.join(legacy_dir, filename)
        try:
            with open(filepath) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  WARN: failed to read {filename}: {e}", file=sys.stderr)
            stats["brands_skipped"] += 1
            continue

        # Skip JSON arrays (index files that slipped through)
        if isinstance(data, list):
            stats["brands_skipped"] += 1
            continue

        result = convert_brand(data, brand_id)
        if result is None:
            stats["brands_skipped"] += 1
            continue

        # Write output
        output_path = os.path.join(output_dir, filename)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            f.write("\n")

        stats["brands_processed"] += 1

    # Print summary
    print("=" * 50)
    print("Conversion complete")
    print("=" * 50)
    print(f"  Brands processed:       {stats['brands_processed']}")
    print(f"  Brands skipped:         {stats['brands_skipped']}")
    print(f"  Streams created:        {stats['streams_total']}")
    print(f"  Empty URLs skipped:     {stats['streams_skipped_empty_url']}")
    print(f"  Duplicates skipped:     {stats['streams_skipped_duplicate']}")
    print(f"  Empty type skipped:     {stats['streams_skipped_empty_type']}")
    print(f"  Empty models skipped:   {stats['streams_skipped_empty_models']}")
    print(f"  ALL -> * converted:     {stats['models_all_converted']}")


if __name__ == "__main__":
    main()
