# StrixCamDB

Open database of IP camera stream URLs. 3600+ brands -- from Hikvision to AliExpress no-name cameras. Primarily used in [Strix](https://github.com/eduard256/Strix), but can be used in any project.

**Want to add a camera?** Use the [contribution form](https://gostrix.github.io/#/contribute).

## Database Format

Each brand is a separate JSON file in `brands/` directory. Filename matches `brand_id`.

```json
{
  "version": 2,
  "brand": "Dahua",
  "brand_id": "dahua",
  "streams": [
    {
      "id": "dahua-1",
      "url": "/cam/realmonitor?channel=1&subtype=0&unicast=true&proto=Onvif",
      "protocol": "rtsp",
      "port": 554,
      "models": ["IPC-HDW1220S", "IPC-HDW1431S-S4", "IPC-HFW1531S"]
    },
    {
      "id": "dahua-2",
      "url": "/live",
      "protocol": "rtsp",
      "port": 554,
      "models": ["IPC-EB5541-AS", "IPC-HDBW5502N"]
    }
  ]
}
```

**Stream fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique within brand |
| `url` | string | URL path with placeholders |
| `protocol` | string | `rtsp`, `http`, `https`, `rtsps`, `rtmp`, `mms`, `bubble`, `rtp`, `dvrip` |
| `port` | int | Port number. `0` = unknown, use default for protocol |
| `models` | array | Camera models. `["*"]` = works for all models of this brand |
| `notes` | string | Optional. Human-readable notes |

## Placeholders

URL paths can contain placeholders. The application replaces them before making requests.

| Placeholder | Description |
|-------------|-------------|
| `[CHANNEL]` | Camera channel number (0-based) |
| `[CHANNEL+1]` | Camera channel number (1-based) |
| `[USERNAME]` | Login username |
| `[PASSWORD]` | Login password |
| `[WIDTH]` | Video width |
| `[HEIGHT]` | Video height |
| `[IP]` | Camera IP address |
| `[PORT]` | Port number |
| `[AUTH]` | Base64-encoded `username:password` |

Alternative forms are also supported: `[USER]`, `[PASS]`, `[PWD]`, `{CHANNEL}`, `{channel+1}`, etc.

## Presets

Presets are curated lists of the most popular URL patterns. Useful for brute-force scanning when the camera brand is unknown.

Available in `presets/` directory:

| File | Patterns | Description |
|------|----------|-------------|
| `top-150.json` | 150 | Quick scan |
| `top-1000.json` | 1000 | Covers most cameras |
| `top-5000.json` | 3028 | Comprehensive |

```json
{
  "version": 1,
  "name": "Top 150 Stream Patterns",
  "preset_id": "top-150",
  "streams": [
    {
      "url": "/Streaming/Channels/101",
      "protocol": "rtsp",
      "port": 554,
      "brand_count": 229
    }
  ]
}
```

`brand_count` -- number of brands that use this URL pattern.

## OUI Database

`oui.json` maps MAC address prefixes to camera brands. Used for auto-detecting camera brand by MAC address during network scanning. 2400+ entries.

```json
{
  "3C:EF:8C": "Dahua",
  "44:47:CC": "Hikvision"
}
```

## SQLite

Pre-built `cameras.db` is available in [GitHub Releases](https://github.com/eduard256/StrixCamDB/releases). Updated automatically on every push to `main`.

Download latest:

```
https://github.com/eduard256/StrixCamDB/releases/download/latest/cameras.db
```

### Tables

```sql
brands (id, brand_id, brand)
streams (id, brand_id, stream_id, url, protocol, port, notes)
stream_models (stream_id, model)
presets (id, preset_id, name, description)
preset_streams (id, preset_id, url, protocol, port, notes, brand_count)
oui (prefix, brand)
meta (key, value)
```

### Example queries

```sql
-- All streams for a brand
SELECT url, protocol, port FROM streams WHERE brand_id = 'hikvision';

-- Find streams by camera model
SELECT b.brand, s.url, s.protocol, s.port
FROM stream_models sm
JOIN streams s ON s.id = sm.stream_id
JOIN brands b ON b.brand_id = s.brand_id
WHERE sm.model = 'DCS-930L';

-- Detect brand by MAC address
SELECT brand FROM oui WHERE prefix = '44:47:CC';

-- Top 10 most popular URL patterns
SELECT url, brand_count FROM preset_streams
WHERE preset_id = 'top-150'
ORDER BY brand_count DESC LIMIT 10;
```

## License

Database: [CC BY-NC 4.0](LICENSE). Free for non-commercial use. Commercial use requires permission.

Code in [Strix](https://github.com/eduard256/Strix): MIT.

## Attribution

Most of the database was originally sourced from [ispyconnect.com](https://www.ispyconnect.com).
