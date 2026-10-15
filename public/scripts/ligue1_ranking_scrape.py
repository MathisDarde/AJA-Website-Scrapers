import re

from common import TM_BASE, ScraperError, detect_competition, fetch_soup, season_context, season_start_year, write_dataset

OUTPUT_FILE = "classementligue1.json"  # nom historique, lu tel quel par le blog

# Zones du classement par championnat (18 clubs en Ligue 1 comme en Ligue 2)
POSITION_STATUSES = {
    "FR1": {1: "UEFA Champions League", 2: "UEFA Champions League", 3: "UEFA Champions League",
            4: "Barrages Champions League", 5: "UEFA Europa League", 6: "Barrages Conference League",
            16: "Barrages Ligue 2", 17: "Ligue 2", 18: "Ligue 2"},
    "FR2": {1: "Ligue 1", 2: "Ligue 1", 3: "Barrages Ligue 1", 4: "Barrages Ligue 1", 5: "Barrages Ligue 1",
            16: "Barrages National", 17: "National", 18: "National"},
}


def get_position_status(competition_id, position):
    return POSITION_STATUSES.get(competition_id, {}).get(position, "")


def scrape(season, competition):
    soup = fetch_soup(f"{TM_BASE}/{competition['slug']}/tabelle/wettbewerb/{competition['id']}/saison_id/{season}")

    classement = []
    table = soup.find("table", {"class": "items"})

    if not table:
        raise ScraperError("Tableau du classement introuvable")

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
                "positionStatus": get_position_status(competition["id"], position),
            })
            
            print(f"✓ {position}. {equipe}")

        except (ValueError, AttributeError):
            continue  # ligne de séparation ou d'en-tête

    return classement

def main():
    season = season_start_year()
    competition = detect_competition(season)
    write_dataset(OUTPUT_FILE, scrape(season, competition), minimum=16, context=season_context(season, competition))


if __name__ == "__main__":
    main()
