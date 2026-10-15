import re

from logos import club_id_from
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


def parse_table(table, competition_id, with_status):
    classement = []
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 10:
            continue

        try:
            position = int(cells[0].get_text(strip=True))
            equipe_link = cells[2].find("a")
            equipe = equipe_link.get_text(strip=True) if equipe_link else cells[2].get_text(strip=True)
            crest = cells[1].find("img")

            buts = re.search(r"(\d+):(\d+)", cells[7].get_text(strip=True))
            # Avant la victoire à 3 points, Transfermarkt affiche « 57:19 » (points pour et contre)
            points = re.match(r"\d+", cells[9].get_text(strip=True))

            classement.append({
                "position": position,
                "equipe": equipe,
                # Identifiant Transfermarkt et nom complet : clés du registre des clubs (logos)
                "club_id": club_id_from(equipe_link),
                "nom_complet": crest.get("alt") if crest else None,
                "matchs_joues": int(cells[3].get_text(strip=True)),
                "gagnes": int(cells[4].get_text(strip=True)),
                "nuls": int(cells[5].get_text(strip=True)),
                "perdus": int(cells[6].get_text(strip=True)),
                "buts_marques": int(buts.group(1)) if buts else 0,
                "buts_encaisses": int(buts.group(2)) if buts else 0,
                "difference": int(cells[8].get_text(strip=True)),
                "points": int(points.group(0)),
                # Zones (Europe, relégation…) connues pour la saison en cours seulement
                "positionStatus": get_position_status(competition_id, position) if with_status else "",
            })
        except (ValueError, AttributeError):
            continue  # ligne de séparation ou d'en-tête
    return classement


def scrape(season, competition, with_status=True):
    soup = fetch_soup(f"{TM_BASE}/{competition['slug']}/tabelle/wettbewerb/{competition['id']}/saison_id/{season}")
    return parse_ranking(soup, competition, with_status)


def parse_ranking(soup, competition, with_status=True):
    """Classement lu sur une page « tabelle » Transfermarkt déjà téléchargée."""
    tables = soup.find_all("table", {"class": "items"})
    if not tables:
        raise ScraperError("Tableau du classement introuvable")

    # Championnat en plusieurs groupes (D2 des années 70-90) : celui où joue l'AJA
    parsed = [parse_table(t, competition["id"], with_status) for t in tables]
    for classement in parsed:
        if any("Auxerre" in team["equipe"] for team in classement):
            return classement
    return parsed[0]


def main():
    season = season_start_year()
    competition = detect_competition(season)
    write_dataset(OUTPUT_FILE, scrape(season, competition), minimum=16, context=season_context(season, competition))


if __name__ == "__main__":
    main()
