import argparse
import os
import json
import requests
import xml.etree.ElementTree as ET
from html import escape
from urllib.parse import quote

parser = argparse.ArgumentParser(description="Generate a game library report.")
parser.add_argument("--store-cache", default=os.path.expanduser("~/Library/Application Support/heroic/store_cache"), help="Path to Heroic store_cache directory")
parser.add_argument("--output", default="heroic_game_report.html", help="Output HTML file path")
parser.add_argument("--steam-user", required=True, help="Steam custom profile ID")
args = parser.parse_args()

store_cache_path = args.store_cache
output_path = args.output
steam_username = args.steam_user

def load_json(filename):
    try:
        with open(os.path.join(store_cache_path, filename), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return None

def build_proton_link(title, appid=None):
    return f"https://www.protondb.com/app/{appid}" if appid else f"https://www.protondb.com/search?q={quote(title)}"

def build_reference_links(title):
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
        "ProtonDB": build_proton_link(title),
        "Metacritic": f"https://www.metacritic.com/game/{slug}",
        "IGDB": f"https://www.igdb.com/games/{slug}",
        "AppleGamingWikiRating": f"https://www.codeweavers.com/search?q={q_plus}",
        "HowLongToBeat": f"https://howlongtobeat.com/?q={q_hltb}"
    }

def extract_gog_games():
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
            "icon_url": game.get("art_icon", ""),
            "extra_info": f"{'Installed' if game.get('is_installed') else 'Not installed'} {' | '.join(p for p, f in [('Mac', game.get('is_mac_native')), ('Linux', game.get('is_linux_native'))] if f)}",
            "reference_links": build_reference_links(title)
        })
        
    return games

def extract_amazon_games():
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
            "icon_url": "",
            "extra_info": f"{'Installed' if game.get('is_installed') else 'Not installed'} {' | '.join(p for p, f in [('Mac', game.get('is_mac_native')), ('Linux', game.get('is_linux_native'))] if f)}",
            "reference_links": build_reference_links(title)
        })
    return games

def extract_epic_games():
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
            "icon_url": "",
            "extra_info": "Owned via Epic",
            "reference_links": build_reference_links(title)
        })
    return games

def fetch_steam_games_from_xml(custom_id):
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
                "icon_url": "",
                "extra_info": "Owned on Steam",
                "reference_links": build_reference_links(name)
            })
        return games
    except Exception as e:
        print(f"Error fetching Steam games for {custom_id}: {e}")
        return []

def build_html_report(gog, epic, amazon, steam):
    def row(game, platform):
        ref_links = "<ul class='mb-0'>" + "".join(
            f'<li><a href="{escape(url)}" target="_blank">{name}</a></li>'
            for name, url in game.get("reference_links", {}).items()
        ) + "</ul>"

        return f"""
        <tr>
            <td>{f'<img src="{escape(game["image_url"])}" class="cover img-fluid"/>' if game["image_url"] else ''}</td>
            <td>{f'<a href="{escape(game["store_url"])}" target="_blank" class="fw-semibold">{escape(game["title"])}</a>' if game["store_url"] else escape(game["title"])}</td>
            <td>{ref_links}</td>
            <td>{escape(platform)}</td>
            <td>{f'<a href="{escape(game["store_url"])}" target="_blank">Store Page</a>' if game["store_url"] else ''}</td>
            <td>{escape(game["extra_info"])}</td>
            <td>{escape(game["developer"])}</td>
            <td>{escape(game["genres"])}</td>
            <td title="{escape(game['description'])}" style="max-width: 400px; white-space: normal; word-break: break-word;">{escape(game["description"][:120]) + ('...' if len(game["description"]) > 120 else '')}</td>
        </tr>
        """

    all_rows = "".join(row(game, platform) for platform, games in [
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
  <link href=\"https://cdn.datatables.net/colvis/1.3.0/css/colVis.bootstrap5.min.css\" rel=\"stylesheet\">
  <style>
    body {{ padding: 2rem; font-family: sans-serif; }}
    .cover {{ max-height: 250px; border-radius: 6px; max-width: 250px; }}
    .dt-buttons .btn {{ margin-right: 0.5rem; }}
    td {{ vertical-align: top; }}
    tbody tr:hover {{ background-color: #f8f9fa; }}
  </style>
</head>
<body>
  <div class=\"container-fluid\">
    <h1 class=\"mb-4 text-center\">Game Library Report</h1>
    <table id=\"games\" class=\"table table-bordered table-striped table-hover nowrap\" style=\"width:100%\">
      <thead class=\"table-light\">
        <tr>
          <th>Cover</th>
          <th>Title</th>
          <th>Links</th>
          <th>Platform</th>
          <th>Store Link</th>
          <th>Status</th>
          <th>Developer</th>
          <th>Genres</th>
          <th>Description</th>
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
  <script src=\"https://cdn.datatables.net/colvis/1.3.0/js/dataTables.colVis.min.js\"></script>
  <script>
    $(document).ready(function () {{
        $('#games').DataTable({{
            responsive: true,
            pageLength: 50,
            lengthMenu: [[10, 50, 100, -1], [10, 50, 100, "All"]],
            dom: '<"row mb-3"<"col-md-4"l><"col-md-4"B><"col-md-4"f>>rt<"row mt-3"<"col-md-6"i><"col-md-6"p>>',
            buttons: ['copy', 'csv', 'excel', 'print', 'colvis'],
            order: [[1, 'asc']]
        }});
    }});
  </script>
</body>
</html>"""
    return html

if __name__ == "__main__":
    gog_games = extract_gog_games()
    epic_games = extract_epic_games()
    amazon_games = extract_amazon_games()
    steam_games = fetch_steam_games_from_xml(steam_username)

    html_output = build_html_report(gog_games, epic_games, amazon_games, steam_games)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_output)

    print(f"Report generated: {output_path}")
