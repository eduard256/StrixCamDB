---
name: StrixCamDB-New-Protocol-Or-Placeholders
description: Add a new protocol or placeholder to StrixCamDB. Updates schemas, README, and skill definitions to support the new value across the entire project.
argument-hint: "[protocol name or placeholder]"
disable-model-invocation: true
---

# StrixCamDB-New-Protocol-Or-Placeholders

You are adding a new protocol or URL placeholder to the StrixCamDB project. This requires updating multiple files to keep everything in sync.

Chat with the user in Russian. All file content -- in English.

---

## STEP 1: Determine the operation

If the user provided details in the command arguments -- parse them. If not -- ask using AskUserQuestion:

**What do you want to add?**
1. **New protocol** -- e.g. `webrtc`, `onvif`, `p2p`
2. **New placeholder** -- e.g. `[STREAM]`, `[PROFILE]`
3. **Both** -- new protocol and new placeholder at the same time

---

## STEP 2: Collect information

### For new protocol

Ask (or parse from input):
- Protocol name (lowercase, e.g. `webrtc`)
- Short description (what it does, when it's used)
- Default port (if known, otherwise `0`)

### For new placeholder

Ask (or parse from input):
- Placeholder name in bracket format (e.g. `[STREAM]`)
- What it represents (e.g. "Stream profile index")
- Example value (e.g. `0`, `main`)
- Are there alternative forms? (e.g. `{stream}`, `[STREAM_ID]`)

---

## STEP 3: Update files

### 3A: Adding a new protocol

Update these 4 files:

**1. `schemas/brand.schema.json`**

Find the `protocol` field description in `$defs/stream/properties/protocol`. Add the new protocol to the description list.

Before:
```
"description": "Network protocol: rtsp, http, https, mms, rtmp, rtsps, bubble, rtp, or future protocols"
```
After (example adding `webrtc`):
```
"description": "Network protocol: rtsp, http, https, mms, rtmp, rtsps, bubble, rtp, webrtc, or future protocols"
```

**2. `schemas/preset.schema.json`**

Same change -- find `protocol` field description in `$defs/preset_stream/properties/protocol` and add the new protocol.

**3. `README.md`**

Find the protocol table in the "Database Format" section under "Stream fields". Add the new protocol to the `protocol` field description cell, keeping the same comma-separated format.

**4. `.claude/skills/StrixCamDB-Add/SKILL.md`**

Two places to update:

a) In the "For Add stream URL" section, find the protocol list:
```
- Protocol (`rtsp`, `http`, `https`, `rtsps`, `rtmp`, `mms`, `bubble`, `rtp`)
```
Add the new protocol.

b) In the "Stream fields" table, find the `protocol` row and add the new protocol to the description.

---

### 3B: Adding a new placeholder

Update these 3 files:

**1. `schemas/brand.schema.json`**

Find the `url` field description in `$defs/stream/properties/url`. Add the new placeholder to the list.

**2. `README.md`**

Find the "Placeholders" section. Add a new row to the table:

```markdown
| `[NEW_PLACEHOLDER]` | Description of what it does |
```

If there are alternative forms, add them to the note below the table.

**3. `.claude/skills/StrixCamDB-Add/SKILL.md`**

Find the "Supported URL placeholders" table. Add a new row with the placeholder, description, and example value.

If there are alternative forms, add them to the "Alternative forms" line below the table.

---

## STEP 4: Verify

1. Read each updated file and confirm the changes are correct
2. Run `python3 scripts/validate.py` to make sure nothing broke
3. Show the user a summary of all changes

### Consistency check -- IMPORTANT

Before finishing, compare ALL sources of truth and report any discrepancies to the user:
- Protocol list in `schemas/brand.schema.json` vs `schemas/preset.schema.json` vs `README.md` vs `StrixCamDB-Add/SKILL.md` -- must be identical
- Placeholder list in `schemas/brand.schema.json` vs `README.md` vs `StrixCamDB-Add/SKILL.md` -- must be identical
- If any file is out of sync (e.g. someone added a protocol to README but not to schema) -- fix it now and tell the user
- If `brands/*.json` contains protocol values not listed in schemas -- warn the user

---

## STEP 5: Commit

Ask the user using AskUserQuestion:

**Commit changes?**
- **Commit only** -- commit to main, CI updates latest release
- **Commit + fix version** -- commit and create a version tag (ask for version)
- **Don't commit** -- leave uncommitted

### If committing:

1. Stage all changed files
2. Commit message in AlexxIT style:
   - Protocol: `Add {protocol} protocol support to database schema`
   - Placeholder: `Add {placeholder} placeholder support`
   - Both: `Add {protocol} protocol and {placeholder} placeholder support`
3. Push to main

### If fixing version:

1. After push, create tag: `git tag v{X.Y.Z}`
2. Push tag: `git push origin v{X.Y.Z}`

### Commit message rules -- ABSOLUTE:
- One line, imperative verb, no period at the end
- No `feat:`, `fix:`, `chore:` prefixes
- No emoji, no "Co-Authored-By", no mention of AI/Claude
