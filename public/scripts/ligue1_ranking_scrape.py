import requests
from bs4 import BeautifulSoup
import json
import os
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

URL = "https://www.transfermarkt.fr/ligue-1/tabelle/wettbewerb/FR1/saison_id/2025"
OUTPUT_FILE = "./data/classementligue1.json"
os.makedirs("./data", exist_ok=True)

def get_position_status(position: int) -> str:
    """Retourne le statut européen/relégation selon la position"""
    if 1 <= position <= 3:
        return "UEFA Champions League"
    elif position == 4:
        return "Barrages Champions League"
    elif position == 5:
        return "UEFA Europa League"
    elif position == 6:
        return "Barrages Conference League"
    elif position == 16:
        return "Barrages Ligue 2"
    elif position in (17, 18):
        return "Ligue 2"
    else:
        return ""  # pas de statut particulier


def scrape_transfermarkt():
    """Scrape Transfermarkt - structure HTML stable"""

    print(f"🔄 Scraping {URL}...\n")

    r = requests.get(URL, headers=HEADERS, timeout=10)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    classement = []

    # Le tableau a la classe "items"
    table = soup.find("table", {"class": "items"})

    if not table:
        print("❌ Tableau non trouvé")
        return []

    # Lignes avec class "odd" ou "even"
    rows = table.find_all("tr")

    for row in rows:
        cells = row.find_all("td")

        if len(cells) < 10:
            continue

        try:
            # Position
            position = int(cells[0].get_text(strip=True))

            # Équipe (dans un <a>)
            equipe_link = cells[2].find("a", {"class": "vereinprofil_tooltip"})
            equipe = (
                equipe_link.get_text(strip=True)
                if equipe_link
                else cells[2].get_text(strip=True)
            )

            # Stats
            matchs = int(cells[3].get_text(strip=True))
            victoires = int(cells[4].get_text(strip=True))
            nuls = int(cells[5].get_text(strip=True))
            defaites = int(cells[6].get_text(strip=True))

            # Buts (format "XX:XX")
            buts_text = cells[7].get_text(strip=True)
            buts_match = re.search(r"(\d+):(\d+)", buts_text)
            bp = int(buts_match.group(1)) if buts_match else 0
            bc = int(buts_match.group(2)) if buts_match else 0

            # Différence
            diff = int(cells[8].get_text(strip=True))

            # Points
            points = int(cells[9].get_text(strip=True))

            classement.append(
                {
                    "position": position,
                    "equipe": equipe,
                    "matchs_joues": matchs,
                    "gagnes": victoires,
                    "nuls": nuls,
                    "perdus": defaites,
                    "buts_marques": bp,
                    "buts_encaisses": bc,
                    "difference": diff,
                    "points": points,
                    "positionStatus": get_position_status(position),
                }
            )

            print(
                f"✓ {position:2d}. {equipe:25s} {points:2d} pts "
                f"({victoires}V-{nuls}N-{defaites}D) {bp}:{bc} → {get_position_status(position)}"
            )

        except Exception as e:
            print(f"⚠️ Erreur ligne: {e}")
            continue

    return classement


def main():
    os.makedirs("./public/data", exist_ok=True)

    print("=" * 70)
    print("🏆 SCRAPING CLASSEMENT LIGUE 1 - TRANSFERMARKT")
    print("=" * 70 + "\n")

    classement = scrape_transfermarkt()

    if not classement:
        print("\n❌ Aucune donnée récupérée")
        return

    # Sauvegarder
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(classement, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(f"✅ {len(classement)} équipes sauvegardées → {OUTPUT_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    main()
