import requests
from bs4 import BeautifulSoup
import json
import os

# URL du calendrier AJ Auxerre 2025-2026
URL = "https://www.transfermarkt.fr/aj-auxerre/spielplan/verein/290/saison_id/2025#FR1"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
OUTPUT_FILE = "./public/data/aja_calendrier.json"

def get_soup(url):
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")

def find_calendar_table(soup):
    """
    Parcourt toutes les tables pour identifier celle contenant le calendrier.
    On repère la table par la présence des colonnes clés "Journée", "Contre", "Résultat"
    """
    tables = soup.find_all("table")
    for t in tables:
        ths = [th.get_text(strip=True) for th in t.find_all("th")]
        if "Journée" in ths and "Contre" in ths and "Résultat" in ths:
            return t
    return None

def get_full_text(td):
    """
    Récupère tout le texte d'une cellule <td>, y compris spans/divs internes,
    et nettoie les retours à la ligne et espaces.
    """
    if td is None:
        return None
    text = " ".join(td.stripped_strings)
    return text if text else None

def get_result_text(td):
    """
    Récupère le texte complet de la cellule 'Résultat', y compris liens et spans internes.
    """
    if td is None:
        return None
    text = " ".join(td.stripped_strings)
    return text if text else None

def parse_calendar_table_transfermarkt(table):
    """
    Parse le tableau du calendrier Transfermarkt pour AJ Auxerre.
    Retourne une liste de matchs avec toutes les colonnes correctement alignées.
    """

    def get_full_text(td):
        """Récupère le texte visible d'un td, ou None si td est None"""
        return td.get_text(strip=True) if td else None

    def get_contre_text(td):
        """Récupère le texte de la colonne Contre, combinant <a> et <span>"""
        if td is None:
            return None
        a = td.find("a")
        span = td.find("span", class_="tabellenplatz")
        a_text = a.get_text(strip=True) if a else ""
        span_text = span.get_text(strip=True) if span else ""
        return f"{a_text} {span_text}".strip()

    def get_result_text(td):
        """Récupère le score réel depuis td[9], span.greentext"""
        if td is None:
            return None
        span = td.find("span", class_="greentext")
        if span:
            return span.get_text(strip=True)
        return get_full_text(td)

    matches = []
    for row in table.find_all("tr")[1:]:  # ignorer le header
        tds = row.find_all("td")
        if len(tds) < 10:
            continue

        journee = get_full_text(tds[0])
        date = get_full_text(tds[1])
        horaire = get_full_text(tds[2])
        dom_ext = get_full_text(tds[3])
        classement = get_full_text(tds[4])
        # td[5] = logo, on ignore
        contre = get_contre_text(tds[6])
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
            "formation": formation,
            "spectateurs": spectateurs,
            "resultat": resultat
        }
        matches.append(match)

    return matches

def main():
    os.makedirs("./public/data", exist_ok=True)
    print("🔄 Récupération de la page Transfermarkt...")
    soup = get_soup(URL)

    table = find_calendar_table(soup)
    if not table:
        print("❌ Tableau calendrier non trouvé")
        return

    print("✅ Tableau calendrier trouvé, parsing avec correction des décalages et résultats...")
    data = parse_calendar_table_transfermarkt(table)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ {len(data)} matchs enregistrés → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
