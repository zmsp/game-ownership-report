# Heroic + Steam Game Library Report

Generates an interactive HTML report of your game library from:

- **Heroic** (GOG, Epic, Amazon)
- **Steam** (via public profile)

Includes game titles, developers, descriptions, genres, platform info, install status, cover art, and store links.

---

## Requirements

- Python 3.7+
- `requests` library (`pip install requests`)

---

## Setup

### 1. Heroic

- Launch Heroic and log into all accounts (GOG, Epic, Amazon).
- Ensure these files exist (locations by OS):

| OS      | Path |
|---------|------|
| macOS   | `~/Library/Application Support/heroic/store_cache` |
| Linux   | `~/.config/heroic/store_cache` |
| Windows | `C:\Users\<you>\AppData\Roaming\heroic\store_cache` |

Files used:
- `gog_library.json`
- `legendary_library.json`
- `nile_library.json`

Update `store_cache_path` in the script if needed.

### 2. Steam

- Set your Steam profile to **public**
- Replace `steam_username = "CHANGEME"` with your **Steam custom ID**

---

## Run

```bash
python3 game_report_html.py
python3 game_report_csv.py