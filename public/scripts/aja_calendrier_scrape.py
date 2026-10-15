from logos import club_id_from
from common import TM_BASE, TM_CLUB_ID, ScraperError, detect_competition, fetch_soup, season_context, season_start_year, write_dataset

OUTPUT_FILE = "aja_calendrier.json"


def find_calendar_table(soup, competition_name):
    """Tableau du championnat (la page liste aussi les coupes, sous leur propre titre)."""
    tables = []
    for t in soup.find_all("table"):
        ths = [th.get_text(strip=True) for th in t.find_all("th")]
        if "Journée" in ths and "Contre" in ths and "Résultat" in ths:
            title = t.find_previous("h2")
            if title and title.get_text(strip=True) == competition_name:
                return t
            tables.append(t)
    return tables[0] if tables else None


def parse_calendar_table_transfermarkt(table):
    def get_full_text(td):
        return td.get_text(strip=True) if td else None

    def get_contre_text(td):
        if td is None:
            return None
        a = td.find("a")
        span = td.find("span", class_="tabellenplatz")
        a_text = a.get_text(strip=True) if a else ""
        span_text = span.get_text(strip=True) if span else ""
        return f"{a_text} {span_text}".strip()

    def get_result_text(td):
        if td is None:
            return None
        span = td.find("span", class_="greentext")
        if span:
            return span.get_text(strip=True)
        return get_full_text(td)

    matches = []
    # On saute le header
    rows = table.find_all("tr")[1:]
    
    for row in rows:
        tds = row.find_all("td")
        if len(tds) < 10:
            continue

        journee = get_full_text(tds[0])
        date = get_full_text(tds[1])
        horaire = get_full_text(tds[2])
        dom_ext = get_full_text(tds[3])
        classement = get_full_text(tds[4])
        contre = get_contre_text(tds[6])
        crest = tds[5].find("img")
        formation = get_full_text(tds[7])
        spectateurs = get_full_text(tds[8])
        resultat = get_result_text(tds[9])

        match = {
            "journee": journee,
            "date": date,
            "horaire": horaire,
            "dom_ext": dom_ext,
            "classement": classement,
            "contre": contre,
            "adversaire_id": club_id_from(tds[6].find("a")),
            "adversaire_nom_complet": crest.get("alt") if crest else None,
            "formation": formation,
            "spectateurs": spectateurs,
            "resultat": resultat
        }
        matches.append(match)

    return matches

def scrape(season, competition):
    soup = fetch_soup(f"{TM_BASE}/aj-auxerre/spielplan/verein/{TM_CLUB_ID}/saison_id/{season}")
    return parse_calendar(soup, competition)


def parse_calendar(soup, competition):
    """Matchs de championnat lus sur une page calendrier Transfermarkt déjà téléchargée."""
    table = find_calendar_table(soup, competition["name"])
    if not table:
        raise ScraperError("Tableau du calendrier introuvable")
    return parse_calendar_table_transfermarkt(table)


def main():
    season = season_start_year()
    competition = detect_competition(season)
    # 34 journées en Ligue 1, 38 en Ligue 2 : en dessous de 30, la page est incomplète
    write_dataset(OUTPUT_FILE, scrape(season, competition), minimum=30, context=season_context(season, competition))


if __name__ == "__main__":
    main()
