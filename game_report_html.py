import argparse
import os
import sys
import json
import requests
import xml.etree.ElementTree as ET
from html import escape
from urllib.parse import quote
import openai
import logging
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# Constants
CACHE_FILE = "game_metadata_cache.json"
DEFAULT_STORE_CACHE_PATH = os.path.expanduser("~/Library/Application Support/heroic/store_cache")
DEFAULT_OUTPUT_PATH = "heroic_game_report.html"

# Load arguments from config.txt if it exists
if os.path.exists("config.txt"):
    with open("config.txt", "r") as f:
        config_args = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        sys.argv.extend(config_args)

# Argument parser
parser = argparse.ArgumentParser(description="Generate a game library report.")
parser.add_argument("--store-cache", default=DEFAULT_STORE_CACHE_PATH, help="Path to Heroic store_cache directory")
parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, help="Output HTML file path")
parser.add_argument("--steam-user", required=True, help="Steam custom profile ID")
parser.add_argument("--openai-api-key", help="OpenAI API key for enrichment")
args = parser.parse_args()

store_cache_path = args.store_cache
output_path = args.output
steam_username = args.steam_user
openai_key = args.openai_api_key
def get_openai_client(api_key):
    if not hasattr(get_openai_client, "_client"):
        get_openai_client._client = openai.OpenAI(api_key=api_key)
    return get_openai_client._client

CACHE_FILE = "game_metadata_cache.json"
game_cache = {}

def load_cache() -> None:
    """Load the game metadata cache from a file if it exists."""
    global game_cache
    if not os.path.exists(CACHE_FILE):
        game_cache = {}
        logging.info("No cache file found. Starting fresh.")
        return
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            game_cache = json.load(f)
        logging.info(f"Cache loaded. {len(game_cache)} items.")
    except Exception as e:
        logging.warning(f"Failed to load cache: {e}")
        game_cache = {}

def save_cache(update: Optional[Dict] = None) -> None:
    """Save the game metadata cache to a file. Optionally update it first."""
    if update and isinstance(update, dict):
        logging.debug(f"Updating cache with: {update}")
        game_cache.update(update)
    try:
        tmp_file = CACHE_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(game_cache, f, indent=2, ensure_ascii=False)
        os.replace(tmp_file, CACHE_FILE)
        logging.info("Cache saved.")
    except Exception as e:
        logging.error(f"Failed to save cache: {e}")


def load_json(filename: str) -> Optional[Dict]:
    """Load JSON data from a file."""
    try:
        with open(os.path.join(store_cache_path, filename), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"Error reading {filename}: {e}")
        return None

def build_reference_links(title: str) -> Dict[str, str]:
    """Build reference links for a game."""
    slug = quote(title.lower().replace(" ", "-").replace(":", "").replace("'", ""))
    q = quote(title)
    q_plus = quote(title.replace(" ", "+"))
    q_hltb = quote(title).replace("%20", "%2520")
    return {
        "SteamDB": f"https://steamdb.info/search/?a=app&q={q}",
        "PCGamingWiki": f"https://www.pcgamingwiki.com/wiki/Special:Search?search={q}",
        "MobyGames": f"https://www.mobygames.com/search/quick?q={q}",
        "GiantBomb": f"https://www.giantbomb.com/search/?q={q}&indices[0]=game",
        "GameFAQs": f"https://gamefaqs.gamespot.com/search?game={q}",
        "ProtonDB": f"https://www.protondb.com/search?q={quote(title)}",
        "Metacritic": f"https://www.metacritic.com/game/{slug}",
        "IGDB": f"https://www.igdb.com/games/{slug}",
        "HowLongToBeat": f"https://howlongtobeat.com/?q={q_hltb}"
    }

def enrich_game_metadata_cached(title, api_key, existing):
    if not api_key or title in game_cache:
        logging.info(f"Skipping enrichment for: {title} (cached or no API key)")
        return game_cache.get(title, existing)

    existing_desc = existing.get("description", "")
    existing_dev = existing.get("developer", "")
    existing_genres = existing.get("genres", "")
    if isinstance(existing_genres, list):
        existing_genres = ", ".join(existing_genres)

    prompt = f"""
    You're a video game metadata assistant. Fill all fields. Use "" if unknown. Only replace existing values if yours are clearly better. Lists should be comma-separated strings.

    Known:
    Title: {title}
    Developer: {existing_dev}
    Genres: {existing_genres}
    Description: {existing_desc}

    Return one JSON object with:
    - developer
    - genres
    - description
    - rating (0–10)
    - tier (S/A/B/C/D)
    - average_time_to_beat (hours)
    - time_to_100 (total hours to fully complete the game, including all extras and achievements)
    - year_released
    - complexity (Simple/Moderate/Complex)
    - mood_tags
    - replayability (Low/Medium/High)
    - best_for (e.g., Solo, Couch Co-op, Split-Screen, Local Versus, Party (Local))
    - energy_required (Low/Medium/High)
    - summary (2 short sentence — why you should play this game and why you should not)
    - steamdeck_category (include both number and label, e.g. "5 - Verified")
    - steamdeck_playability (short note)
    """

    try:
        client = get_openai_client(api_key)
        logging.info(f"Enriching metadata for: {title}")
        response = client.chat.completions.create(
            model="gpt-4.1-nano",  # Consider using turbo models if available and suitable
            messages=[
                {"role": "system", "content": "Enrich video game metadata. Use 'x' if unknown. Return compact JSON."},
                {"role": "user", "content": prompt.strip()}
            ],
            temperature=0.5,  # Lower temp for more predictable, structured output
            max_tokens=800,  # Optional: limit output size if needed
        )
        content = response.choices[0].message.content
        enriched_data = json.loads(content)

        if isinstance(enriched_data.get("genres"), list):
            enriched_data["genres"] = ", ".join(enriched_data["genres"])

        for key in ["developer", "genres", "description"]:
            if not existing.get(key) or (len(str(enriched_data.get(key, ""))) > len(str(existing.get(key, "")))):
                existing[key] = enriched_data.get(key, existing.get(key))

        # Apply all the additional keys
        existing["rating"] = enriched_data.get("rating", "N/A")
        existing["tier"] = enriched_data.get("tier", "N/A")
        existing["average_time_to_beat"] = enriched_data.get("average_time_to_beat", "N/A")
        existing["year_released"] = enriched_data.get("year_released", "N/A")
        existing["time_to_100"] = enriched_data.get("time_to_100", "N/A")
        existing["complexity"] = enriched_data.get("complexity", "N/A")
        existing["mood_tags"] = enriched_data.get("mood_tags", "")
        existing["replayability"] = enriched_data.get("replayability", "N/A")
        existing["best_for"] = enriched_data.get("best_for", "N/A")
        existing["energy_required"] = enriched_data.get("energy_required", "N/A")
        existing["summary"] = enriched_data.get("summary", "")
        existing["steamdeck_category"] = enriched_data.get("steamdeck_category", "Unknown")
        existing["steamdeck_playability"] = enriched_data.get("steamdeck_playability", "")

        game_cache[title] = existing
        save_cache()
        logging.info(f"Metadata enriched for: {title}")
        return existing
    except Exception as e:
        logging.error(f"OpenAI error for {title}: {e}")
        return existing



def enrich_games_with_openai(games: List[Dict], api_key: Optional[str]) -> List[Dict]:
    """Enrich metadata for a list of games."""
    if not api_key:
        logging.warning("No OpenAI API key provided. Skipping enrichment.")
        return games
    for game in games:
        enriched = enrich_game_metadata_cached(game["title"], api_key, game)
        game.update(enriched)
    return games

# Game extraction functions
def extract_gog_games() -> List[Dict]:
    """Extract games from GOG."""
    data = load_json("gog_library.json") or {}
    games = []
    for game in data.get("games", []):
        title = f"{game.get('title')} {'(DLC)' if game.get('install', {}).get('is_dlc', False) else ''}"
        gog_slug = game.get('title', '').lower().replace(' ', '_').replace(':', '').replace("'", "")
        games.append({
            "title": title,
            "description": game.get("extra", {}).get("about", {}).get("description", ""),
            "developer": game.get("developer", ""),
            "store_url": f"https://www.gog.com/en/game/{gog_slug}",
            "image_url": game.get("art_cover") or game.get("art_square") or game.get("art_background") or "",
            "genres": ", ".join(game.get("extra", {}).get("genres", [])),
            "extra_info": f"{'Installed' if game.get('is_installed') else 'Not installed'}",
            "reference_links": build_reference_links(title)
        })
    return games

def extract_amazon_games() -> List[Dict]:
    """Extract games from Amazon."""
    data = load_json("nile_library.json") or {}
    games = []
    for game in data.get("library", []):
        title = game.get("title")
        games.append({
            "title": title,
            "description": game.get("description", ""),
            "developer": game.get("developer", ""),
            "store_url": "",
            "image_url": game.get("art_cover") or game.get("art_square") or "",
            "genres": ", ".join(game.get("extra", {}).get("genres", [])),
            "extra_info": f"{'Installed' if game.get('is_installed') else 'Not installed'}",
            "reference_links": build_reference_links(title)
        })
    return games

def extract_epic_games() -> List[Dict]:
    """Extract games from Epic Games."""
    data = load_json("legendary_library.json") or {}
    games = []
    for game in data.get("library", []):
        title = game.get("title")
        games.append({
            "title": title,
            "description": game.get("extra", {}).get("about", {}).get("description", ""),
            "developer": game.get("developer", ""),
            "store_url": game.get("extra", {}).get("storeUrl", ""),
            "image_url": game.get("art_cover", "") or game.get("art_square", ""),
            "genres": "",
            "extra_info": "Owned via Epic",
            "reference_links": build_reference_links(title)
        })
    return games

def fetch_steam_games_from_xml(custom_id: str) -> List[Dict]:
    """Fetch games from Steam using XML."""
    url = f"https://steamcommunity.com/id/{custom_id}/games?tab=all&xml=1"
    try:
        response = requests.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        games = []
        for game in root.findall(".//game"):
            appid = game.find("appID").text
            name = game.find("name").text
            games.append({
                "title": name,
                "description": "",
                "developer": "",
                "store_url": f"https://store.steampowered.com/app/{appid}",
                "image_url": f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg",
                "genres": "",
                "extra_info": "Owned on Steam",
                "reference_links": build_reference_links(name)
            })
        return games
    except Exception as e:
        logging.error(f"Error fetching Steam games for {custom_id}: {e}")
        return []

# HTML generation
import logging
from html import escape
def build_html_row(game, platform):
    try:
        ref_links = (
            "<div class='d-flex flex-wrap gap-1'>"
            + "".join(
                f'<a href="{escape(url)}" target="_blank" class="btn btn-outline-secondary btn-sm px-1 py-0">{escape(name)}</a>'
                for name, url in game.get("reference_links", {}).items()
            )
            + "</div>"
        )

        store_url = game.get("store_url", "")
        image_html = f'<img src="{escape(game.get("image_url", ""))}" class="cover img-fluid mb-2" style="max-width:120px;"/>' if game.get("image_url") else ''
        title_html = f'<div class="text-wrap text-break fw-semibold" style="max-width: 200px;">{escape(game.get("title", ""))}</div>'

        if store_url:
            title_and_cover = f'<a href="{escape(store_url)}" target="_blank">{image_html}{title_html}</a>'
        else:
            title_and_cover = f'{image_html}{title_html}'

        return f"""
        <tr>
        <td>
            <div class="d-flex flex-column align-items-center text-center">
                {title_and_cover}
            </div>
        </td>
        <td><div class="text-wrap text-break">{escape(platform)}</div></td>
        <td><div class="text-wrap text-break">{escape(game.get("extra_info", ""))}</div></td>
        <td><div class="text-wrap text-break">{escape(str(game.get("developer", "") or ""))}</div></td>
        <td><div class="text-wrap text-break">{escape(game.get("genres", ""))}</div></td>
        <td><div class="text-wrap text-break">{game.get("rating", "")}</div></td>
        <td><div class="text-wrap text-break">{escape(str(game.get("tier", "")))}</div></td>
                <td><div class="text-wrap text-break">{game.get("year_released", "")}</div></td>
        <td><div class="text-wrap text-break">{game.get("average_time_to_beat", "")}</div></td>
        <td><div class="text-wrap text-break">{game.get("time_to_100", "")}</div></td>
        <td><div class="text-wrap text-break">{escape(str(game.get("complexity", "")))}</div></td>
        <td><div class="text-wrap text-break">{escape(str(game.get("mood_tags", "")))}</div></td>
        <td><div class="text-wrap text-break">{escape(str(game.get("replayability", "")))}</div></td>
        <td><div class="text-wrap text-break">{escape(str(game.get("best_for", "")))}</div></td>
        <td><div class="text-wrap text-break">{escape(str(game.get("energy_required", "")))}</div></td>
        <td><div class="text-wrap text-break">{escape(game.get("steamdeck_category", "Unknown"))}</div></td>
        <td><div class="text-wrap text-break" style="max-width: 400px;" title="{escape(game.get('steamdeck_playability', ''))}">{escape(game.get("steamdeck_playability", "")[:120]) + ('...' if len(game.get("steamdeck_playability", "")) > 120 else '')}</div></td>
        <td><div class="text-wrap text-break" style="max-width: 400px;" title="{escape(game.get('summary', ''))}">{escape(game.get("summary", "")[:120]) + ('...' if len(game.get("summary", "")) > 120 else '')}</div></td>
        <td><div class="text-wrap text-break" style="max-width: 400px;" title="{escape(game.get('description', ''))}">{escape(game.get("description", "")[:120]) + ('...' if len(game.get("description", "")) > 120 else '')}</div></td>
        <td><div class="text-wrap text-break">{ref_links}</div></td>
        </tr>
        """
    except Exception as e:
        logging.exception(f"Failed to build HTML row for game: {game.get('title', 'Unknown')}. Error: {e}")
        return f"<tr><td colspan='22'>Error rendering row for {escape(str(game.get('title', 'Unknown')))}</td></tr>"



def build_html_report(gog: List[Dict], epic: List[Dict], amazon: List[Dict], steam: List[Dict]) -> str:
    all_rows = "".join(build_html_row(game, platform) for platform, games in [
        ("GOG", gog), ("Epic", epic), ("Amazon", amazon), ("Steam", steam)
    ] for game in games)

    html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>Game Library Report</title>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css\" rel=\"stylesheet\">
  <link href=\"https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css\" rel=\"stylesheet\">
  <link href=\"https://cdn.datatables.net/buttons/2.4.2/css/buttons.bootstrap5.min.css\" rel=\"stylesheet\">
  <link href=\"https://cdn.datatables.net/responsive/2.5.3/css/responsive.bootstrap5.min.css\" rel=\"stylesheet\">
  <link href=\"https://cdn.datatables.net/colreorder/1.6.2/css/colReorder.bootstrap5.min.css\" rel=\"stylesheet\">
  <style>
    body {{ padding: 2rem; font-family: sans-serif; }}
    .cover {{ max-height: 250px; border-radius: 6px; max-width: 250px; }}
    .dt-buttons .btn {{ margin-right: 0.5rem; }}
    td {{ vertical-align: top; }}
    tbody tr:hover {{ background-color: #f8f9fa; }}
    table.dataTable th:first-child, table.dataTable td:first-child {{ width: 200px; }}
  </style>
</head>
<body>
  <div class=\"container-fluid\">
    <h1 class=\"mb-4 text-center\">Game Library Report</h1>
   
      <table id=\"games\" class=\"table table-bordered table-striped table-hover nowrap\" style=\"width:100%\">
        <thead class=\"table-light\">
       <tr>
        <th>Game</th> <!-- Title & Cover -->
        <th>Platform</th>
        <th>Status</th>
        <th>Dev</th>
        <th>Genres</th>
        <th>Rating</th>
        <th>Tier</th>
        <th>Year</th>
        <th>To Beat</th>
        <th>To 100%</th>
        <th>Complexity</th>
        <th>Mood</th>
        <th>Replay</th>
        <th>Best For</th>
        <th>Energy</th>
        <th>Deck</th>
        <th>Deck Notes</th>
        <th>Summary</th>
        <th>Desc</th>
        <th>Links</th>
        </tr>
        </thead>
        <tbody>
          {all_rows}
        </tbody>
      </table>
   
  </div>

  <script src=\"https://code.jquery.com/jquery-3.7.0.min.js\"></script>
  <script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js\"></script>
  <script src=\"https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js\"></script>
  <script src=\"https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js\"></script>
  <script src=\"https://cdn.datatables.net/buttons/2.4.2/js/dataTables.buttons.min.js\"></script>
  <script src=\"https://cdn.datatables.net/buttons/2.4.2/js/buttons.bootstrap5.min.js\"></script>
  <script src=\"https://cdn.datatables.net/buttons/2.4.2/js/buttons.html5.min.js\"></script>
  <script src=\"https://cdn.datatables.net/buttons/2.4.2/js/buttons.print.min.js\"></script>
  <script src=\"https://cdn.datatables.net/responsive/2.5.3/js/dataTables.responsive.min.js\"></script>
  <script src=\"https://cdn.datatables.net/responsive/2.5.3/js/responsive.bootstrap5.min.js\"></script>
  <script src=\"https://cdn.datatables.net/colreorder/1.6.2/js/dataTables.colReorder.min.js\"></script>
  <script src=\"https://cdn.datatables.net/colreorder/1.6.2/js/colReorder.bootstrap5.min.js\"></script>
  <script>
    $(document).ready(function () {{
        $('#games').DataTable({{
            responsive: true,
            pageLength: 50,
            lengthMenu: [[10, 50, 100, -1], [10, 50, 100, "All"]],
            dom: '<"row mb-3"<"col-md-4"l><"col-md-4"B><"col-md-4"f>>rt<"row mt-3"<"col-md-6"i><"col-md-6"p>>',
            buttons: ['copy', 'csv', 'excel', 'print', 'colvis'],
            colReorder: true,
            stateSave: true,
            order: [[1, 'asc']]
        }});
    }});
  </script>
</body>
</html>"""
    return html

# Main execution
if __name__ == "__main__":

    gog_games = extract_gog_games()
    epic_games = extract_epic_games()
    amazon_games = extract_amazon_games()
    steam_games = fetch_steam_games_from_xml(steam_username)

    load_cache()
    gog_games = enrich_games_with_openai(gog_games, openai_key)
    epic_games = enrich_games_with_openai(epic_games, openai_key)
    amazon_games = enrich_games_with_openai(amazon_games, openai_key)
    steam_games = enrich_games_with_openai(steam_games, openai_key)

    html_output = build_html_report(gog_games, epic_games, amazon_games, steam_games)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_output)
    logging.info(f"Report generated: {output_path}")