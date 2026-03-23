#!/usr/bin/env python3
"""Validate all brand files against StrixCamDB v2 format rules.

Checks: required fields, field types, unique IDs, no duplicate streams,
brand_id matches filename, port range, non-empty models.
"""

import json
import os
import sys

BRANDS_DIR = os.path.join(os.path.dirname(__file__), "..", "brands")

REQUIRED_ROOT = {"version", "brand", "brand_id", "streams"}
REQUIRED_STREAM = {"id", "url", "protocol", "port", "models"}

errors = []
warnings = []
total_files = 0
total_streams = 0


def validate_file(filepath, filename):
    """Validate a single brand file. Appends to global errors/warnings lists."""
    global total_streams

    brand_id_expected = filename.replace(".json", "")

    try:
        with open(filepath) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"{filename}: invalid JSON: {e}")
        return
    except IOError as e:
        errors.append(f"{filename}: cannot read: {e}")
        return

    if not isinstance(data, dict):
        errors.append(f"{filename}: root must be object, got {type(data).__name__}")
        return

    # Required root fields
    for field in REQUIRED_ROOT:
        if field not in data:
            errors.append(f"{filename}: missing required field '{field}'")

    # Version check
    if data.get("version") != 2:
        errors.append(f"{filename}: version must be 2, got {data.get('version')}")

    # brand_id matches filename
    if data.get("brand_id") != brand_id_expected:
        errors.append(
            f"{filename}: brand_id '{data.get('brand_id')}' "
            f"does not match filename '{brand_id_expected}'"
        )

    # Brand name non-empty
    if not data.get("brand", "").strip():
        errors.append(f"{filename}: brand name is empty")

    streams = data.get("streams", [])
    if not isinstance(streams, list):
        errors.append(f"{filename}: streams must be array")
        return

    if len(streams) == 0:
        warnings.append(f"{filename}: no streams")

    seen_ids = set()
    seen_urls = set()

    for i, stream in enumerate(streams):
        total_streams += 1
        prefix = f"{filename}: stream[{i}]"

        if not isinstance(stream, dict):
            errors.append(f"{prefix}: must be object")
            continue

        # Required stream fields
        for field in REQUIRED_STREAM:
            if field not in stream:
                errors.append(f"{prefix}: missing required field '{field}'")

        # ID uniqueness
        sid = stream.get("id", "")
        if sid in seen_ids:
            errors.append(f"{prefix}: duplicate id '{sid}'")
        seen_ids.add(sid)

        # Protocol is non-empty string
        val = stream.get("protocol", "")
        if not isinstance(val, str) or not val.strip():
            errors.append(f"{prefix}: 'protocol' must be non-empty string, got {repr(val)}")

        # Port range
        port = stream.get("port")
        if not isinstance(port, int):
            errors.append(f"{prefix}: port must be int, got {type(port).__name__}")
        elif port < 0 or port > 65535:
            errors.append(f"{prefix}: port {port} out of range 0-65535")

        # Models non-empty array
        models = stream.get("models")
        if not isinstance(models, list) or len(models) == 0:
            errors.append(f"{prefix}: models must be non-empty array")
        elif not all(isinstance(m, str) for m in models):
            errors.append(f"{prefix}: all models must be strings")

        # URL is string
        url = stream.get("url")
        if not isinstance(url, str):
            errors.append(f"{prefix}: url must be string")

        # Duplicate stream check (same protocol:port:url)
        dedup_key = f"{stream.get('protocol')}:{stream.get('port')}:{stream.get('url')}"
        if dedup_key in seen_urls:
            errors.append(f"{prefix}: duplicate stream {dedup_key}")
        seen_urls.add(dedup_key)

        # Optional fields type check
        if "notes" in stream and not isinstance(stream["notes"], str):
            errors.append(f"{prefix}: notes must be string")
        if "tags" in stream:
            tags = stream["tags"]
            if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
                errors.append(f"{prefix}: tags must be array of strings")

        # No unexpected fields
        allowed = REQUIRED_STREAM | {"notes", "tags"}
        extra = set(stream.keys()) - allowed
        if extra:
            warnings.append(f"{prefix}: unexpected fields: {extra}")


def main():
    global total_files

    brands_dir = os.path.abspath(BRANDS_DIR)
    if not os.path.isdir(brands_dir):
        print(f"Error: brands directory not found: {brands_dir}", file=sys.stderr)
        sys.exit(1)

    files = sorted(f for f in os.listdir(brands_dir) if f.endswith(".json"))
    total_files = len(files)

    for filename in files:
        filepath = os.path.join(brands_dir, filename)
        validate_file(filepath, filename)

    # Print results
    print("=" * 50)
    print("Validation results")
    print("=" * 50)
    print(f"  Files checked:  {total_files}")
    print(f"  Streams checked: {total_streams}")
    print(f"  Errors:         {len(errors)}")
    print(f"  Warnings:       {len(warnings)}")

    if errors:
        print(f"\n--- ERRORS ({len(errors)}) ---")
        for e in errors[:50]:
            print(f"  {e}")
        if len(errors) > 50:
            print(f"  ... and {len(errors) - 50} more")

    if warnings:
        print(f"\n--- WARNINGS ({len(warnings)}) ---")
        for w in warnings[:20]:
            print(f"  {w}")
        if len(warnings) > 20:
            print(f"  ... and {len(warnings) - 20} more")

    if errors:
        sys.exit(1)
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
