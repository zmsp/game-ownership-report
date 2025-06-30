import os
import json
import requests
import xml.etree.ElementTree as ET


store_cache_path = os.path.expanduser("~/Library/Application Support/heroic/store_cache")

output_path = "heroic_game_report.html"
steam_username= "CHANGEME"

def load_json(filename):
    try:
        with open(os.path.join(store_cache_path, filename), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return None


def extract_gog_games():
    data = load_json("gog_library.json") or {}
    games = []

    for game in data.get("games", []):
        title = game.get("title")
        developer = game.get("developer", "")
        description = game.get("extra", {}).get("about", {}).get("description", "")
        genres = game.get("extra", {}).get("genres", [])
        store_url = f"https://www.gog.com/game/{game.get('app_name')}" if game.get("app_name") else ""
        image_url = game.get("art_cover") or game.get("art_square") or game.get("art_background") or ""
        icon_url = game.get("art_icon", "")
        is_installed = game.get("is_installed", False)
        is_dlc = game.get("install", {}).get("is_dlc", False)
        platform_info = []
        if game.get("is_mac_native"):
            platform_info.append("Mac")
        if game.get("is_linux_native"):
            platform_info.append("Linux")

        game_info = {
            "title": f"{title} {'(DLC)' if is_dlc else ''}",
            "description": description,
            "developer": developer,
            "store_url": store_url,
            "image_url": image_url,
            "genres": ", ".join(genres),
            "icon_url": icon_url,
            "extra_info": f"{'✅ Installed' if is_installed else '❌ Not installed'} {' | '.join(platform_info)}"
        }

        games.append(game_info)

    return games


def extract_amazon_games():
    data = load_json("nile_library.json") or {}
    games = []

    for game in data.get("library", []):
        title = game.get("title")
        description = game.get("description", "")
        developer = game.get("developer", "")
        genres = game.get("extra", {}).get("genres", [])
        image_url = game.get("art_cover") or game.get("art_square") or ""
        is_installed = game.get("is_installed", False)
        platform_info = []
        if game.get("is_mac_native"):
            platform_info.append("Mac")
        if game.get("is_linux_native"):
            platform_info.append("Linux")

        games.append({
            "title": title,
            "description": description,
            "developer": developer,
            "store_url": "",
            "image_url": image_url,
            "genres": ", ".join(genres),
            "icon_url": "",
            "extra_info": f"{'✅ Installed' if is_installed else '❌ Not installed'} {' | '.join(platform_info)}"
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
                "extra_info": "🛒 Owned on Steam"
            })

        return games

    except Exception as e:
        print(f"Error fetching Steam games for {custom_id}: {e}")
        return []


def extract_epic_games():
    data = load_json("legendary_library.json") or {}
    games = []

    for game in data.get("library", []):
        games.append({
            "title": game.get("title"),
            "description": game.get("extra", {}).get("about", {}).get("description", ""),
            "developer": game.get("developer", ""),
            "store_url": game.get("extra", {}).get("storeUrl", ""),
            "image_url": game.get("art_cover", "") or game.get("art_square", ""),
            "genres": "",
            "icon_url": "",
            "extra_info": "Owned via Epic"
        })

    return games


def build_html_report(gog, epic, amazon, steam):
    def row(game):
        return f"""<tr>
            <td>{f'<img src="{game["image_url"]}" class="cover"/>' if game["image_url"] else ''}</td>
            <td>{game['title']}</td>
            <td>{game['developer']}</td>
            <td>{game['genres']}</td>
            <td>{game['extra_info']}</td>
            <td>{game['description'][:200]}{"..." if len(game['description']) > 200 else ""}</td>
            <td>{f'<a href="{game["store_url"]}" target="_blank">Link</a>' if game["store_url"] else ''}</td>
        </tr>"""

    all_games = [("GOG", gog), ("Epic", epic), ("Amazon", amazon), ("Steam", steam)]
    all_rows = "\n".join(
        row({**game, "title": f"{label}: {game['title']}"}) for label, group in all_games for game in group
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Game Library</title>
  <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
  <style>
    body {{
      font-family: sans-serif;
      margin: 2rem;
    }}
    img.cover {{
      max-height: 100px;
      border-radius: 4px;
    }}
  </style>
</head>
<body>
  <h1>🎮 Full Game Library</h1>
  <table id="games" class="display">
    <thead>
      <tr>
        <th>Cover</th>
        <th>Title</th>
        <th>Developer</th>
        <th>Genres</th>
        <th>Status</th>
        <th>Description</th>
        <th>Store Link</th>
      </tr>
    </thead>
    <tbody>
      {all_rows}
    </tbody>
  </table>
  <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
  <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
  <script>
    $(document).ready(function () {{
      $('#games').DataTable({{
        pageLength: 25
      }});
    }});
  </script>
</body>
</html>"""
    return html


# Run everything
gog_games = extract_gog_games()
epic_games = extract_epic_games()
amazon_games = extract_amazon_games()
steam_games = fetch_steam_games_from_xml(steam_username)  # Use your public Steam ID here

html_output = build_html_report(gog_games, epic_games, amazon_games, steam_games)

with open(output_path, "w", encoding="utf-8") as f:
    f.write(html_output)

print(f"✅ Report generated: {output_path}")