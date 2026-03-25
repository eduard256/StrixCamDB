---
name: StrixCamDB-Add-OUI
description: Add new MAC prefix (OUI) to brand mappings in oui.json. Use when user wants to add a camera brand's MAC address prefix to the OUI database.
argument-hint: "[MAC prefix and brand, e.g. 3C:EF:8C Dahua]"
disable-model-invocation: true
---

# StrixCamDB-Add-OUI

You are editing the OUI database in StrixCamDB. This maps MAC address prefixes to camera brands.

Chat with the user in Russian. All data in files -- in English.

---

## FILE

`oui.json` in the repository root. Format:

```json
{
  "3C:EF:8C": "Dahua",
  "44:47:CC": "Hikvision",
  "00:12:17": "Cisco"
}
```

Key: MAC prefix (first 3 octets, uppercase, colon-separated).
Value: Brand name (human-readable).

---

## STEP 1: Collect information

If the user provided details in arguments -- parse them. If not -- ask:

- MAC prefix (e.g. `3C:EF:8C`)
- Brand name (e.g. `Dahua`)

Multiple entries can be added at once.

---

## STEP 2: Validate

1. Read `oui.json`
2. Check format: prefix must be `XX:XX:XX` (uppercase hex, colon-separated)
3. If prefix already exists -- warn the user and show current brand mapping
4. If brand name doesn't match any `brand_id` in `brands/` -- warn but don't block (OUI uses human-readable names, not brand_id)
5. Normalize prefix to uppercase: `3c:ef:8c` -> `3C:EF:8C`

---

## STEP 3: Write

1. Read `oui.json`
2. Add new entries
3. Sort keys alphabetically
4. Write back with 2-space indent, `ensure_ascii: false`, trailing newline

---

## STEP 4: Verify

1. Confirm file is valid JSON: `python3 -c "import json; json.load(open('oui.json'))"`
2. Show the user what was added
3. Check for inconsistencies -- if user adds a prefix for a brand that has other prefixes, mention them

---

## STEP 5: Commit

Ask the user:

- **Commit only** -- commit to main, CI updates cameras.db
- **Commit + fix version** -- commit and create a version tag
- **Don't commit** -- leave uncommitted

### Commit message:
- One entry: `Add OUI prefix {prefix} for {brand}`
- Multiple: `Add {N} OUI prefixes`

### Rules -- ABSOLUTE:
- One line, imperative verb, no period at the end
- No `feat:`, `fix:`, `chore:` prefixes
- No emoji, no "Co-Authored-By", no mention of AI/Claude

---

## CRITICAL RULE

NEVER delete or modify existing OUI entries without explicit user confirmation. You can ONLY ADD new entries by default. If you see something suspicious -- tell the user but don't touch it.
