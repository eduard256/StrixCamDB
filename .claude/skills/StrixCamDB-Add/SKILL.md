---
name: StrixCamDB-Add
description: Add new brands, camera models, or stream URLs to StrixCamDB. Use when user wants to add camera data to the database, mentions adding a brand/model/URL, or provides camera stream information.
argument-hint: "[description of what to add]"
disable-model-invocation: true
---

# StrixCamDB-Add

You are editing the StrixCamDB camera database. Follow the rules below exactly.

Chat with the user in Russian. All data in JSON files -- in English.

### CRITICAL RULE -- READ-ONLY FOR EXISTING DATA

You can ONLY ADD new data: new brands, new streams, new models. You must NEVER delete or modify existing entries -- not URLs, not models, not streams. Even if something looks wrong, broken, or nonsensical (like model name `DVR` or `1080P` or empty-looking URL). These entries may be valid for specific cameras.

If you see something suspicious -- tell the user. But don't touch it without explicit confirmation.

---

## STEP 1: Determine the operation

If the user provided details in the command arguments -- parse them and determine what to do automatically. If not -- ask using AskUserQuestion:

**What do you want to do?**
1. **Add new brand** -- create a new JSON file for a brand that doesn't exist yet
2. **Add stream URL** -- add a new stream entry to an existing brand
3. **Add model to stream** -- add a model name to an existing stream's `models` array
4. **Add OUI prefix** -- add MAC address prefix to brand mapping in `oui.json`
5. **Process contribution issues** -- review and apply data from GitHub issues

### Adding OUI prefix

When user selects "Add OUI prefix":

1. Ask for MAC prefix (e.g. `3C:EF:8C`) and brand name (e.g. `Dahua`)
2. Multiple entries can be added at once
3. Normalize prefix to uppercase: `3c:ef:8c` -> `3C:EF:8C`
4. Validate format: must be `XX:XX:XX` (uppercase hex, colon-separated)
5. Read `oui.json`, check if prefix already exists -- if yes, warn and show current mapping
6. Add new entries, sort keys alphabetically
7. Write back with 2-space indent, `ensure_ascii: false`, trailing newline
8. Verify: `python3 -c "import json; json.load(open('oui.json'))"`

**OUI file format** (`oui.json` in repository root):

```json
{
  "3C:EF:8C": "Dahua",
  "44:47:CC": "Hikvision"
}
```

Key: MAC prefix (first 3 octets). Value: brand name (human-readable).

### Processing contribution issues

When user selects "Process contribution issues":

1. Run `gh issue list --repo eduard256/StrixCamDB --label contribution --state open` to list pending contributions
2. Show the list to the user
3. For each issue the user wants to process:
   a. Run `gh issue view {number} --repo eduard256/StrixCamDB` to read the YAML data
   b. Parse the YAML block from the issue body:
      ```yaml
      brand: Dahua
      model: IPC-HDW1220S
      url: /live
      protocol: rtsp
      port: 554
      mac_prefix: 3C:EF:8C
      comment: Works on firmware v2.800
      ```
   c. Validate the data:
      - Is the protocol known? If not -- warn the user, suggest `/StrixCamDB-New-Protocol-Or-Placeholders`
      - Does the brand file exist? If not -- this is "Add new brand" operation
      - Is this URL already in the brand file? If yes -- warn about duplicate
      - Does the model look suspicious? Warn but don't block
   d. Apply the data using the normal add flow (STEP 3-5 below)
   e. After successful commit, close the issue:
      `gh issue close {number} --repo eduard256/StrixCamDB --comment "Added to database"`
   f. If the data is invalid or rejected by user:
      `gh issue close {number} --repo eduard256/StrixCamDB --reason "not planned" --comment "Rejected: {reason}"`

---

## STEP 2: Collect required information

### For "Add new brand"

Ask (or parse from input):
- Brand name (human-readable, e.g. `Hikvision`)
- At least one stream URL with protocol and port

Brand ID is auto-generated from brand name: lowercase, spaces to hyphens, special chars removed.

### For "Add stream URL"

Ask (or parse from input):
- Brand name or brand_id (search in `brands/` directory if unclear)
- URL path (e.g. `/Streaming/Channels/101`)
- Protocol (`rtsp`, `http`, `https`, `rtsps`, `rtmp`, `mms`, `bubble`, `rtp`)
- Port number (e.g. `554`, `80`. Use `0` if unknown)
- Which models this stream works for (list of model names, or `*` for all)

### For "Add model to stream"

Ask (or parse from input):
- Brand name or brand_id
- Model name to add
- Which stream(s) to add it to (show existing streams, let user pick)

---

## STEP 3: Validate before writing

### Brand file structure

Every brand file is `brands/{brand_id}.json`:

```json
{
  "version": 2,
  "brand": "Brand Name",
  "brand_id": "brand-name",
  "streams": [
    {
      "id": "brand-name-1",
      "url": "/path/to/stream",
      "protocol": "rtsp",
      "port": 554,
      "models": ["Model-A", "Model-B"],
      "notes": "Optional notes"
    }
  ]
}
```

### Root fields

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `version` | int | yes | Always `2` |
| `brand` | string | yes | Human-readable name, capitalized properly |
| `brand_id` | string | yes | Lowercase, hyphens only, must match filename |
| `streams` | array | yes | At least one stream |

### Stream fields

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `id` | string | yes | Format: `{brand_id}-{N}` where N is sequential. Must be unique within file |
| `url` | string | yes | URL path only (no protocol://host:port prefix). Can contain placeholders |
| `protocol` | string | yes | One of: `rtsp`, `http`, `https`, `rtsps`, `rtmp`, `mms`, `bubble`, `rtp` |
| `port` | int | yes | 0-65535. Use `0` if unknown (means "use default for protocol") |
| `models` | array | yes | Non-empty. Use `["*"]` if stream works for all models of this brand |
| `notes` | string | no | Only add if genuinely useful context exists |

### Supported URL placeholders

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `[CHANNEL]` | Channel number, 0-based | `0`, `1`, `2` |
| `[CHANNEL+1]` | Channel number, 1-based | `1`, `2`, `3` |
| `[USERNAME]` | Login username | `admin` |
| `[PASSWORD]` | Login password | `12345` |
| `[WIDTH]` | Video width | `1920` |
| `[HEIGHT]` | Video height | `1080` |
| `[IP]` | Camera IP address | `192.168.1.100` |
| `[PORT]` | Port number | `554` |
| `[AUTH]` | Base64-encoded `username:password` | |

Alternative forms: `[USER]`, `[PASS]`, `[PWD]`, `[PASWORD]`, `{CHANNEL}`, `{channel+1}` -- all supported.

### Validation rules

1. `brand_id` must match the filename (without `.json`)
2. Every `id` must be unique within the file
3. No duplicate streams -- same `protocol:port:url` combination must not appear twice
4. `url` must not be empty
5. `models` must not be empty
6. `port` must be integer 0-65535
7. `protocol` must be a non-empty string
8. If brand file already exists -- read it first, don't overwrite

---

## STEP 4: Write changes

### Adding a new brand

1. Verify file `brands/{brand_id}.json` does NOT exist
2. Create the file with `version: 2`, brand info, and streams
3. Stream IDs start from `{brand_id}-1`

### Adding a stream to existing brand

1. Read existing `brands/{brand_id}.json`
2. Find the highest existing stream ID number (e.g. if last is `dahua-47`, next is `dahua-48`)
3. Append new stream to the `streams` array
4. Write file back with `indent=2`, `ensure_ascii=False`, trailing newline

### Adding a model to existing stream

1. Read existing `brands/{brand_id}.json`
2. Find the target stream by ID or URL
3. Add model name to the `models` array (if not already present)
4. Write file back

### JSON formatting rules

- 2-space indent
- No trailing commas
- `ensure_ascii: false` (preserve Unicode)
- Single trailing newline at end of file
- Keys order in root: `version`, `brand`, `brand_id`, `streams`
- Keys order in stream: `id`, `url`, `protocol`, `port`, `models`, `notes`

---

## STEP 5: Verify

After writing:
1. Run `python3 scripts/validate.py` to check for errors
2. If validation fails -- fix the issue immediately
3. Show the user what was changed (brief summary)

### Consistency check -- IMPORTANT

Before finishing, check for problems and report them to the user immediately:
- Duplicate streams (same `protocol:port:url`) within the brand file
- Model names that look like categories, not real models (e.g. `DVR`, `PTZ`, `1080P`, `Other`) -- warn the user but don't block
- Unknown protocol values not listed in `schemas/brand.schema.json` -- warn the user, suggest running `/StrixCamDB-New-Protocol-Or-Placeholders`
- Placeholder in URL that is not documented in README.md -- warn the user
- Any other inconsistencies between schemas, README, and actual data -- report immediately

---

## STEP 6: Commit and version

Ask the user using AskUserQuestion:

**Question:** "Commit changes?"
- **Commit only** -- commit to main, CI will update latest release automatically
- **Commit + fix version** -- commit and create a version tag (ask for version, e.g. `v0.2.0`)
- **Don't commit** -- leave changes uncommitted

### If committing:

1. Stage changed files: `git add brands/{brand_id}.json`
2. Commit with message in AlexxIT style:
   - New brand: `Add {brand} camera database`
   - New stream: `Add stream URL for {brand}`
   - New model: `Add {model} to {brand}`
3. Push to main: `git push origin main`

### If fixing version:

1. After commit and push, create tag: `git tag v{X.Y.Z}`
2. Push tag: `git push origin v{X.Y.Z}`
3. Confirm that CI will create a versioned release

### Commit message rules -- ABSOLUTE:
- One line, imperative verb, no period at the end
- No `feat:`, `fix:`, `chore:` prefixes
- No emoji, no "Co-Authored-By", no mention of AI/Claude
- Examples: `Add Reolink camera database`, `Add RTSP stream for TP-Link Tapo`, `Add DS-2CD2047 to Hikvision`
