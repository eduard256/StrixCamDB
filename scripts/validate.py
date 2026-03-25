#!/usr/bin/env python3
"""Validate all StrixCamDB data files: brands, presets, and OUI."""

import json
import os
import re
import sys

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
BRANDS_DIR = os.path.join(BASE_DIR, "brands")
PRESETS_DIR = os.path.join(BASE_DIR, "presets")
OUI_FILE = os.path.join(BASE_DIR, "oui.json")

REQUIRED_ROOT = {"version", "brand", "brand_id", "streams"}
REQUIRED_STREAM = {"id", "url", "protocol", "port", "models"}
REQUIRED_PRESET_ROOT = {"version", "name", "preset_id", "streams"}
REQUIRED_PRESET_STREAM = {"url", "protocol", "port"}

MAC_PREFIX_RE = re.compile(r'^[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}$')

errors = []
warnings = []
stats = {
    "brand_files": 0,
    "streams": 0,
    "preset_files": 0,
    "preset_streams": 0,
    "oui_entries": 0,
}


# ===== BRANDS =====

def validate_brand(filepath, filename):
    brand_id_expected = filename.replace(".json", "")

    try:
        with open(filepath) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"brands/{filename}: invalid JSON: {e}")
        return
    except IOError as e:
        errors.append(f"brands/{filename}: cannot read: {e}")
        return

    if not isinstance(data, dict):
        errors.append(f"brands/{filename}: root must be object")
        return

    for field in REQUIRED_ROOT:
        if field not in data:
            errors.append(f"brands/{filename}: missing field '{field}'")

    if data.get("version") != 2:
        errors.append(f"brands/{filename}: version must be 2, got {data.get('version')}")

    if data.get("brand_id") != brand_id_expected:
        errors.append(f"brands/{filename}: brand_id mismatch '{data.get('brand_id')}' != '{brand_id_expected}'")

    if not data.get("brand", "").strip():
        errors.append(f"brands/{filename}: brand name is empty")

    streams = data.get("streams", [])
    if not isinstance(streams, list):
        errors.append(f"brands/{filename}: streams must be array")
        return

    if len(streams) == 0:
        warnings.append(f"brands/{filename}: no streams")

    seen_ids = set()
    seen_urls = set()

    for i, stream in enumerate(streams):
        stats["streams"] += 1
        prefix = f"brands/{filename}: stream[{i}]"

        if not isinstance(stream, dict):
            errors.append(f"{prefix}: must be object")
            continue

        for field in REQUIRED_STREAM:
            if field not in stream:
                errors.append(f"{prefix}: missing field '{field}'")

        sid = stream.get("id", "")
        if sid in seen_ids:
            errors.append(f"{prefix}: duplicate id '{sid}'")
        seen_ids.add(sid)

        val = stream.get("protocol", "")
        if not isinstance(val, str) or not val.strip():
            errors.append(f"{prefix}: protocol must be non-empty string")

        port = stream.get("port")
        if not isinstance(port, int):
            errors.append(f"{prefix}: port must be int")
        elif port < 0 or port > 65535:
            errors.append(f"{prefix}: port {port} out of range")

        models = stream.get("models")
        if not isinstance(models, list) or len(models) == 0:
            errors.append(f"{prefix}: models must be non-empty array")
        elif not all(isinstance(m, str) for m in models):
            errors.append(f"{prefix}: all models must be strings")

        url = stream.get("url")
        if not isinstance(url, str):
            errors.append(f"{prefix}: url must be string")

        dedup_key = f"{stream.get('protocol')}:{stream.get('port')}:{stream.get('url')}"
        if dedup_key in seen_urls:
            errors.append(f"{prefix}: duplicate stream {dedup_key}")
        seen_urls.add(dedup_key)

        if "notes" in stream and not isinstance(stream["notes"], str):
            errors.append(f"{prefix}: notes must be string")
        if "tags" in stream:
            if not isinstance(stream["tags"], list) or not all(isinstance(t, str) for t in stream["tags"]):
                errors.append(f"{prefix}: tags must be array of strings")

        allowed = REQUIRED_STREAM | {"notes", "tags"}
        extra = set(stream.keys()) - allowed
        if extra:
            warnings.append(f"{prefix}: unexpected fields: {extra}")


# ===== PRESETS =====

def validate_preset(filepath, filename):
    try:
        with open(filepath) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"presets/{filename}: invalid JSON: {e}")
        return
    except IOError as e:
        errors.append(f"presets/{filename}: cannot read: {e}")
        return

    if not isinstance(data, dict):
        errors.append(f"presets/{filename}: root must be object")
        return

    for field in REQUIRED_PRESET_ROOT:
        if field not in data:
            errors.append(f"presets/{filename}: missing field '{field}'")

    preset_id_expected = filename.replace(".json", "")
    if data.get("preset_id") != preset_id_expected:
        errors.append(f"presets/{filename}: preset_id mismatch '{data.get('preset_id')}' != '{preset_id_expected}'")

    if not data.get("name", "").strip():
        errors.append(f"presets/{filename}: name is empty")

    streams = data.get("streams", [])
    if not isinstance(streams, list):
        errors.append(f"presets/{filename}: streams must be array")
        return

    for i, stream in enumerate(streams):
        stats["preset_streams"] += 1
        prefix = f"presets/{filename}: stream[{i}]"

        if not isinstance(stream, dict):
            errors.append(f"{prefix}: must be object")
            continue

        for field in REQUIRED_PRESET_STREAM:
            if field not in stream:
                errors.append(f"{prefix}: missing field '{field}'")

        port = stream.get("port")
        if isinstance(port, int) and (port < 0 or port > 65535):
            errors.append(f"{prefix}: port {port} out of range")

        val = stream.get("protocol", "")
        if not isinstance(val, str) or not val.strip():
            errors.append(f"{prefix}: protocol must be non-empty string")


# ===== OUI =====

def validate_oui(filepath):
    try:
        with open(filepath) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"oui.json: invalid JSON: {e}")
        return
    except IOError as e:
        errors.append(f"oui.json: cannot read: {e}")
        return

    if not isinstance(data, dict):
        errors.append("oui.json: must be object")
        return

    for prefix, brand in data.items():
        stats["oui_entries"] += 1

        if not MAC_PREFIX_RE.match(prefix):
            errors.append(f"oui.json: invalid MAC prefix '{prefix}' (expected XX:XX:XX uppercase)")

        if not isinstance(brand, str) or not brand.strip():
            errors.append(f"oui.json: empty brand for prefix '{prefix}'")

    # Check for duplicate prefixes with different case
    seen_lower = {}
    for prefix in data:
        lower = prefix.lower()
        if lower in seen_lower:
            warnings.append(f"oui.json: case duplicate '{prefix}' and '{seen_lower[lower]}'")
        seen_lower[lower] = prefix


# ===== MAIN =====

def main():
    # Validate brands
    brands_dir = os.path.abspath(BRANDS_DIR)
    if os.path.isdir(brands_dir):
        files = sorted(f for f in os.listdir(brands_dir) if f.endswith(".json"))
        stats["brand_files"] = len(files)
        for filename in files:
            validate_brand(os.path.join(brands_dir, filename), filename)

    # Validate presets
    presets_dir = os.path.abspath(PRESETS_DIR)
    if os.path.isdir(presets_dir):
        files = sorted(f for f in os.listdir(presets_dir) if f.endswith(".json"))
        stats["preset_files"] = len(files)
        for filename in files:
            validate_preset(os.path.join(presets_dir, filename), filename)

    # Validate OUI
    oui_file = os.path.abspath(OUI_FILE)
    if os.path.exists(oui_file):
        validate_oui(oui_file)

    # Print results
    print("=" * 50)
    print("Validation results")
    print("=" * 50)
    print(f"  Brand files:     {stats['brand_files']}")
    print(f"  Streams:         {stats['streams']}")
    print(f"  Preset files:    {stats['preset_files']}")
    print(f"  Preset streams:  {stats['preset_streams']}")
    print(f"  OUI entries:     {stats['oui_entries']}")
    print(f"  Errors:          {len(errors)}")
    print(f"  Warnings:        {len(warnings)}")

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
