#!/usr/bin/env python3
"""Generate preset files from converted brand data.

Reads all brands/*.json, counts URL pattern popularity (by number of brands
that use each pattern), and outputs top-N preset files.
"""

import json
import os
import sys
from collections import defaultdict

BRANDS_DIR = os.path.join(os.path.dirname(__file__), "..", "brands")
PRESETS_DIR = os.path.join(os.path.dirname(__file__), "..", "presets")

# Preset configurations: (preset_id, name, description, limit)
PRESETS = [
    (
        "top-150",
        "Top 150 Stream Patterns",
        "150 most common stream URL patterns across all brands. Good for quick scanning.",
        150,
    ),
    (
        "top-1000",
        "Top 1000 Stream Patterns",
        "1000 most common stream URL patterns. Covers most IP cameras.",
        1000,
    ),
    (
        "top-5000",
        "Top 5000 Stream Patterns",
        "5000 most common stream URL patterns. Comprehensive coverage.",
        5000,
    ),
]


def main():
    brands_dir = os.path.abspath(BRANDS_DIR)
    presets_dir = os.path.abspath(PRESETS_DIR)

    if not os.path.isdir(brands_dir):
        print(f"Error: brands directory not found: {brands_dir}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(presets_dir, exist_ok=True)

    # Collect URL patterns and count brands per pattern.
    # Key: (url, type, protocol, port)
    # Value: set of brand_ids
    pattern_brands = defaultdict(set)

    files = sorted(f for f in os.listdir(brands_dir) if f.endswith(".json"))
    for filename in files:
        filepath = os.path.join(brands_dir, filename)
        try:
            with open(filepath) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            continue

        brand_id = data.get("brand_id", "")
        for stream in data.get("streams", []):
            key = (
                stream.get("url", ""),
                stream.get("type", ""),
                stream.get("protocol", ""),
                stream.get("port", 0),
            )
            pattern_brands[key].add(brand_id)

    # Sort by brand count descending, then by URL alphabetically
    sorted_patterns = sorted(
        pattern_brands.items(),
        key=lambda x: (-len(x[1]), x[0][0]),
    )

    print(f"Total unique patterns: {len(sorted_patterns)}")

    # Generate each preset
    for preset_id, name, description, limit in PRESETS:
        streams = []
        for (url, stype, protocol, port), brands in sorted_patterns[:limit]:
            entry = {
                "url": url,
                "type": stype,
                "protocol": protocol,
                "port": port,
                "brand_count": len(brands),
            }
            streams.append(entry)

        preset = {
            "version": 1,
            "name": name,
            "preset_id": preset_id,
            "description": description,
            "streams": streams,
        }

        output_path = os.path.join(presets_dir, f"{preset_id}.json")
        with open(output_path, "w") as f:
            json.dump(preset, f, indent=2, ensure_ascii=False)
            f.write("\n")

        actual = len(streams)
        top_count = streams[0]["brand_count"] if streams else 0
        bottom_count = streams[-1]["brand_count"] if streams else 0
        print(
            f"  {preset_id}.json: {actual} patterns "
            f"(brand_count {top_count} -> {bottom_count})"
        )


if __name__ == "__main__":
    main()
