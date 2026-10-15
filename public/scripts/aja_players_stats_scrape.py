from common import TM_BASE, TM_CLUB_ID, ScraperError, detect_competition, fetch_soup, season_context, season_start_year, write_dataset

OUTPUT_FILE = "aja_statistics.json"


def parse_players_table(soup):
    players = []
    table = soup.find("table", {"class": "items"})
    if not table:
        raise ScraperError("Tableau des statistiques introuvable")

    rows = table.find_all("tr", class_=["odd", "even"])
    for row in rows:
        tds = row.find_all("td")
        if len(tds) < 15:
            continue

        numero = tds[0].get_text(strip=True)
        
        # Nom et poste
        nom, position = "", ""
        nom_poste_table = tds[1].find("table")
        if nom_poste_table:
            nom_el = nom_poste_table.select_one(".hauptlink a")
            nom = nom_el.get_text(strip=True) if nom_el else ""
            try:
                # Parfois la structure change légèrement
                trs_sub = nom_poste_table.find_all("tr")
                if len(trs_sub) > 1:
                    position = trs_sub[1].find("td").get_text(strip=True)
            except:
                pass

        age = tds[5].get_text(strip=True)
        matches = tds[7].get_text(strip=True)
        titularisations = tds[8].get_text(strip=True)

        goals = tds[9].get_text(strip=True)
        goals = goals if goals != "-" else "0"
        
        assists = tds[10].get_text(strip=True)
        assists = assists if assists != "-" else "0"

        yellow_cards = tds[11].get_text(strip=True)
        yellow_cards = yellow_cards if yellow_cards != "-" else "0"

        two_yellows = tds[12].get_text(strip=True)
        two_yellows_val = int(two_yellows) if two_yellows != "-" and two_yellows.isdigit() else 0

        red_cards = tds[13].get_text(strip=True)
        red_cards_val = int(red_cards) if red_cards != "-" and red_cards.isdigit() else 0

        total_red_cards = two_yellows_val + red_cards_val

        sub_in = tds[14].get_text(strip=True)
        sub_in = sub_in if sub_in != "-" else "0"
        
        sub_out = tds[15].get_text(strip=True)
        sub_out = sub_out if sub_out != "-" else "0"

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

def scrape(season):
    # reldata=&<saison> : toutes compétitions confondues
    soup = fetch_soup(f"{TM_BASE}/aj-auxerre/leistungsdaten/verein/{TM_CLUB_ID}/reldata/%26{season}/plus/1")
    return parse_players_table(soup)


def main():
    season = season_start_year()
    competition = detect_competition(season)
    write_dataset(OUTPUT_FILE, scrape(season), minimum=15, context=season_context(season, competition))


if __name__ == "__main__":
    main()
