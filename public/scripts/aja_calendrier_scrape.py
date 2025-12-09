from curl_cffi import requests
from bs4 import BeautifulSoup
import json
import os
import time
import random

# URL du calendrier AJ Auxerre 2025-2026
URL = "https://www.transfermarkt.fr/aj-auxerre/spielplan/verein/290/saison_id/2025#FR1"
OUTPUT_FILE = "./data/aja_calendrier.json"

def get_soup(url):
    """
    Utilise curl_cffi pour imiter parfaitement un navigateur Chrome (TLS Fingerprint).
    """
    # Pause aléatoire (toujours utile)
    time.sleep(random.uniform(2, 5))
    
    try:
        print(f"📡 Connexion à {url} avec curl_cffi...")
        
        # impersonate="chrome120" est la clé magique pour passer Cloudflare
        response = requests.get(
            url, 
            impersonate="chrome120", 
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return BeautifulSoup(response.text, "html.parser")
        else:
            print(f"⚠️ Erreur HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Erreur réseau : {e}")
        return None

def find_calendar_table(soup):
    tables = soup.find_all("table")
    for t in tables:
        ths = [th.get_text(strip=True) for th in t.find_all("th")]
        if "Journée" in ths and "Contre" in ths and "Résultat" in ths:
            return t
    return None

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
    # S'assurer que le dossier existe
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    soup = get_soup(URL)
    if not soup:
        print("❌ Impossible de récupérer la page (blocage ou erreur).")
        exit(1) # Quitter avec erreur pour les logs

    table = find_calendar_table(soup)
    if not table:
        print("❌ Tableau calendrier non trouvé dans le HTML.")
        return

    print("✅ Tableau trouvé, extraction des données...")
    data = parse_calendar_table_transfermarkt(table)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ {len(data)} matchs enregistrés → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()