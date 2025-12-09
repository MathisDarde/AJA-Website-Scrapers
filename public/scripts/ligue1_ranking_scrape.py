import cloudscraper
from bs4 import BeautifulSoup
import json
import os
import re
import time
import random
from fake_useragent import UserAgent

URL = "https://www.transfermarkt.fr/ligue-1/tabelle/wettbewerb/FR1/saison_id/2025"
OUTPUT_FILE = "./data/classementligue1.json"

def get_position_status(position: int) -> str:
    if 1 <= position <= 3: return "UEFA Champions League"
    elif position == 4: return "Barrages Champions League"
    elif position == 5: return "UEFA Europa League"
    elif position == 6: return "Barrages Conference League"
    elif position == 16: return "Barrages Ligue 2"
    elif position in (17, 18): return "Ligue 2"
    else: return ""

def get_soup(url):
    ua = UserAgent()
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    headers = {
        "User-Agent": ua.random,
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    time.sleep(random.uniform(2, 5))

    try:
        print(f"🔄 Scraping {url}...")
        res = scraper.get(url, headers=headers)
        if res.status_code != 200:
            print(f"⚠️ Erreur HTTP {res.status_code}")
            return None
        return BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        print(f"❌ Exception réseau : {e}")
        return None

def scrape_transfermarkt():
    soup = get_soup(URL)
    if not soup: return []

    classement = []
    table = soup.find("table", {"class": "items"})

    if not table:
        print("❌ Tableau classement non trouvé")
        return []

    rows = table.find_all("tr")

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 10:
            continue

        try:
            position = int(cells[0].get_text(strip=True))
            equipe_link = cells[2].find("a", {"class": "vereinprofil_tooltip"})
            equipe = equipe_link.get_text(strip=True) if equipe_link else cells[2].get_text(strip=True)
            
            matchs = int(cells[3].get_text(strip=True))
            victoires = int(cells[4].get_text(strip=True))
            nuls = int(cells[5].get_text(strip=True))
            defaites = int(cells[6].get_text(strip=True))

            buts_text = cells[7].get_text(strip=True)
            buts_match = re.search(r"(\d+):(\d+)", buts_text)
            bp = int(buts_match.group(1)) if buts_match else 0
            bc = int(buts_match.group(2)) if buts_match else 0

            diff = int(cells[8].get_text(strip=True))
            points = int(cells[9].get_text(strip=True))

            classement.append({
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
            })
            
            print(f"✓ {position}. {equipe}")

        except Exception as e:
            continue

    return classement

def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    print("=" * 70)
    print("🏆 SCRAPING CLASSEMENT LIGUE 1 - TRANSFERMARKT")
    print("=" * 70)

    classement = scrape_transfermarkt()

    if not classement:
        print("❌ Aucune donnée récupérée.")
        exit(1)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(classement, f, indent=2, ensure_ascii=False)

    print(f"✅ {len(classement)} équipes sauvegardées → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()