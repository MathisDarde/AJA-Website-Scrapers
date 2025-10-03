import requests
from bs4 import BeautifulSoup
import json
import os

BASE_URL = "https://www.transfermarkt.fr/aj-auxerre/leistungsdaten/verein/290/reldata/%262025/plus/1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
OUTPUT_FILE = "./public/data/aja_statistics.json"


def get_soup(url, timeout=10):
    res = requests.get(url, headers=HEADERS, timeout=timeout)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")


def parse_players_table(soup):
    players = []
    table = soup.find("table", {"class": "items"})
    if not table:
        print("❌ Tableau des joueurs non trouvé")
        return []

    rows = table.find_all("tr", class_=["odd", "even"])
    for row in rows:
        tds = row.find_all("td")
        if len(tds) < 15:
            continue

        # numéro
        numero = tds[0].get_text(strip=True)

        # nom et poste
        nom, position = "", ""
        nom_poste_table = tds[1].find("table")
        if nom_poste_table:
            nom_el = nom_poste_table.select_one(".hauptlink a")
            nom = nom_el.get_text(strip=True) if nom_el else ""
            poste_el = nom_poste_table.find_all("tr")[1].find("td")
            position = poste_el.get_text(strip=True) if poste_el else ""

        # age
        age = tds[5].get_text(strip=True)

        # matches & titularisations
        matches = tds[7].get_text(strip=True)
        titularisations = tds[8].get_text(strip=True)

        # goals & assists
        goals = tds[9].get_text(strip=True)
        goals = goals if goals != "-" else None
        assists = tds[10].get_text(strip=True)
        assists = assists if assists != "-" else None

        # cards
        yellow_cards = tds[11].get_text(strip=True)
        yellow_cards = yellow_cards if yellow_cards != "-" else "0"

        two_yellows = tds[12].get_text(strip=True)
        two_yellows_val = int(two_yellows) if two_yellows != "-" else 0

        red_cards = tds[13].get_text(strip=True)
        red_cards_val = int(red_cards) if red_cards != "-" else 0

        total_red_cards = two_yellows_val + red_cards_val

        # substitutions in / out
        sub_in = tds[14].get_text(strip=True)
        sub_in = sub_in if sub_in != "-" else "-"
        sub_out = tds[15].get_text(strip=True)
        sub_out = sub_out if sub_out != "-" else "-"

        # points per match & minutes
        points_per_match = tds[16].get_text(strip=True)
        minutes = tds[17].get_text(strip=True)

        players.append({
            "numero": numero,
            "nom": nom,
            "age": age,
            "position": position,
            "matches": matches,
            "titularisations": titularisations,
            "goals": goals,
            "assists": assists,
            "yellow_cards": yellow_cards,
            "red_cards": total_red_cards,
            "substitutions_in": sub_in,
            "substitutions_out": sub_out,
            "points_per_match": points_per_match,
            "minutes": minutes
        })

    return players

def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    soup = get_soup(BASE_URL)
    data = parse_players_table(soup)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ {len(data)} joueurs enregistrés → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
