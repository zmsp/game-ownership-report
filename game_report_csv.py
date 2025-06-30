import os
import json
import requests
import xml.etree.ElementTree as ET
import csv
import io
import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a game library CSV report from Heroic and Steam.")
    parser.add_argument(
        "--store-cache",
        default=os.path.expanduser("~/Library/Application Support/heroic/store_cache"),
        help="Path to Heroic store_cache directory (default: macOS path)"
    )
    parser.add_argument(
        "--output",
        default="heroic_game_report.csv",
        help="Output CSV file path"
    )
    parser.add_argument(
        "--steam-user",
        required=True,
        help="Steam custom profile ID (must be public)"
    )
    return parser.parse_args()


def load_json(path, filename):
    try:
        with open(os.path.join(path, filename), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return {}


def extract_gog_games(path):
    data = load_json(path, "gog_library.json")
    games = []
    for game in data.get("games", []):
        platform_info = [p for p, cond in [("Mac", game.get("is_mac_native")), ("Linux", game.get("is_linux_native"))] if cond]
        games.append({
            "title": f"{game.get('title')} {'(DLC)' if game.get('install', {}).get('is_dlc') else ''}",
            "description": game.get("extra", {}).get("about", {}).get("description", ""),
            "developer": game.get("developer", ""),
            "genres": ", ".join(game.get("extra", {}).get("genres", [])),
            "store_url": f"https://www.gog.com/game/{game.get('app_name')}" if game.get("app_name") else "",
            "image_url": game.get("art_cover") or game.get("art_square") or game.get("art_background") or "",
            "extra_info": f"{'Installed' if game.get('is_installed') else 'Not installed'} {' | '.join(platform_info)}"
        })
    return games


def extract_amazon_games(path):
    data = load_json(path, "nile_library.json")
    games = []
    for game in data.get("library", []):
        platform_info = [p for p, cond in [("Mac", game.get("is_mac_native")), ("Linux", game.get("is_linux_native"))] if cond]
        games.append({
            "title": game.get("title"),
            "description": game.get("description", ""),
            "developer": game.get("developer", ""),
            "genres": ", ".join(game.get("extra", {}).get("genres", [])),
            "store_url": "",
            "image_url": game.get("art_cover") or game.get("art_square") or "",
            "extra_info": f"{'Installed' if game.get('is_installed') else 'Not installed'} {' | '.join(platform_info)}"
        })
    return games


def extract_epic_games(path):
    data = load_json(path, "legendary_library.json")
    games = []
    for game in data.get("library", []):
        games.append({
            "title": game.get("title"),
            "description": game.get("extra", {}).get("about", {}).get("description", ""),
            "developer": game.get("developer", ""),
            "genres": "",
            "store_url": game.get("extra", {}).get("storeUrl", ""),
            "image_url": game.get("art_cover") or game.get("art_square") or "",
            "extra_info": "Owned via Epic"
        })
    return games


def fetch_steam_games(custom_id):
    url = f"https://steamcommunity.com/id/{custom_id}/games?tab=all&xml=1"
    try:
        response = requests.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        games = []
        for game in root.findall(".//game"):
            appid = game.find("appID").text
            games.append({
                "title": game.find("name").text,
                "description": "",
                "developer": "",
                "genres": "",
                "store_url": f"https://store.steampowered.com/app/{appid}",
                "image_url": f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg",
                "extra_info": "Owned on Steam"
            })
        return games
    except Exception as e:
        print(f"Error fetching Steam games: {e}")
        return []


def build_csv_report(gog, epic, amazon, steam):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Platform", "Title", "Developer", "Genres", "Status", "Description", "Image URL", "Store Link"])
    for label, group in [("GOG", gog), ("Epic", epic), ("Amazon", amazon), ("Steam", steam)]:
        for game in group:
            writer.writerow([
                label,
                game.get("title", ""),
                game.get("developer", ""),
                game.get("genres", ""),
                game.get("extra_info", ""),
                game.get("description", "")[:200],
                game.get("image_url", ""),
                game.get("store_url", "")
            ])
    return output.getvalue()


if __name__ == "__main__":
    args = parse_args()
    gog_games = extract_gog_games(args.store_cache)
    epic_games = extract_epic_games(args.store_cache)
    amazon_games = extract_amazon_games(args.store_cache)
    steam_games = fetch_steam_games(args.steam_user)

    csv_data = build_csv_report(gog_games, epic_games, amazon_games, steam_games)
    with open(args.output, "w", encoding="utf-8-sig") as f:
        f.write(csv_data)

    print(f"CSV report saved to {args.output}")