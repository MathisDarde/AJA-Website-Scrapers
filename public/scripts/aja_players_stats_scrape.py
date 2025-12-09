from curl_cffi import requests
from bs4 import BeautifulSoup
import json
import os
import time
import random

BASE_URL = "https://www.transfermarkt.fr/aj-auxerre/leistungsdaten/verein/290/reldata/%262025/plus/1"
OUTPUT_FILE = "./data/aja_statistics.json"

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
        print(f"❌ Exception réseau : {e}")
        return None

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

def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    soup = get_soup(BASE_URL)
    if not soup:
        print("❌ Arrêt du script : page non chargée.")
        exit(1)

    data = parse_players_table(soup)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ {len(data)} joueurs enregistrés → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()