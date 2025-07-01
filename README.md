# Heroic + Steam Game Library Report

This tool generates an interactive HTML report (and optional CSV export) of your game library using data from:

* Heroic (GOG, Epic Games, Amazon)
* Steam (via public profile)

The report includes:

* Title, developer, genres, release year
* Description, summary, rating, and replayability
* Steam Deck compatibility, time-to-beat estimates, best play modes
* Reference links (SteamDB, PCGamingWiki, HowLongToBeat, and others)

---

## Requirements

* Python 3.7 or higher
* `requests` (for all usage)
* `openai` (optional, for metadata enrichment)

Install dependencies:

```bash
pip install requests openai
```

---

## Setup

### Heroic Launcher

Log into your GOG, Epic, and Amazon accounts using the Heroic Games Launcher. Ensure the following files are available in your Heroic `store_cache` directory:

| Platform | Path                                                      |
| -------- | --------------------------------------------------------- |
| macOS    | `~/Library/Application Support/heroic/store_cache`        |
| Linux    | `~/.config/heroic/store_cache`                            |
| Windows  | `C:\Users\<your_name>\AppData\Roaming\heroic\store_cache` |

Files used:

* `gog_library.json`
* `legendary_library.json`
* `nile_library.json`

To override the default path, use the `--store-cache` flag.

### Steam

* Your Steam profile must be public
* Use your custom profile ID from the URL: `https://steamcommunity.com/id/<your_id>`
* Pass it to the script using the `--steam-user` argument

---

## Usage

### Generate an HTML Report

```bash
python3 game_report_html.py --steam-user YOUR_STEAM_ID
```

### Additional Options

```bash
python3 game_report_html_ai.py \
  --steam-user your_steam_id \
  --store-cache "/path/to/store_cache" \
  --output "./docs/index.html"
```

### Generate a CSV Export (optional)

```bash
python3 game_report_csv.py --steam-user YOUR_STEAM_ID
```

---

## Enriching Metadata with OpenAI (optional)

To include additional game metadata such as:

* Estimated completion times
* Complexity and replayability
* Viewer-friendly summaries
* Steam Deck category and notes

You can provide your OpenAI API key:

```bash
python3 game_report_html.py \
  --steam-user YOUR_STEAM_ID \
  --openai-api-key sk-xxxx...
```

The script uses caching (`game_metadata_cache.json`) to avoid repeated API calls.

---

## Using a Config File (optional)

Instead of passing arguments each time, you can create a `config.txt` file in the same directory:

```
--steam-user your_steam_id
--output ./docs/index.html
--openai-api-key sk-xxxx...
```

Each line represents a separate argument.

---

Let me know if you'd like to include deployment instructions (for GitHub Pages, for example) or a sample output.
