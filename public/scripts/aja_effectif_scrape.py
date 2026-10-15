from curl_cffi import requests
from bs4 import BeautifulSoup
from datetime import date
import json
import os
import re
import time
import random

TEAM_URL = "https://www.aja.fr/equipes/equipe-pro/"
OUTPUT_FILE = "./data/aja_effectif.json"


def current_season():
    """Saison en cours au format « 2026-2027 » (bascule au 1er juillet)."""
    today = date.today()
    start = today.year if today.month >= 7 else today.year - 1
    return f"{start}-{start + 1}"


def get_soup(url):
    time.sleep(random.uniform(1, 3))
    try:
        response = requests.get(
            url,
            impersonate="chrome120",
            headers={"Accept-Language": "fr-FR,fr;q=0.9"},
            timeout=30,
        )
        if response.status_code == 200:
            return BeautifulSoup(response.content, "html.parser")
        print(f"⚠️ Erreur HTTP {response.status_code} sur {url}")
    except Exception as e:
        print(f"❌ Erreur réseau sur {url} : {e}")
    return None


def image_url(article):
    img = article.find("img", class_="player-preview__image")
    if not img:
        return None
    for attr in ("data-lazy-src", "src"):
        value = img.get(attr)
        if value and not value.startswith("data:"):
            return value
    return None


def age_from(date_naissance):
    match = re.match(r"(\d{2})/(\d{2})/(\d{4})", date_naissance or "")
    if not match:
        return None
    day, month, year = map(int, match.groups())
    today = date.today()
    return today.year - year - ((today.month, today.day) < (month, day))


def parse_details(fiche_url):
    """Lit « Date de naissance : 09/04/2001 », « Taille : 1m84 »… sur la fiche du joueur."""
    soup = get_soup(fiche_url)
    if not soup:
        return {}
    lines = [l.strip().replace("\xa0", " ") for l in soup.get_text("\n").split("\n") if l.strip()]
    labels = {
        "Date de naissance": "date_naissance",
        "Ville": "ville",
        "Taille": "taille",
        "Poids": "poids",
        "Pied": "pied",
    }
    details = {}
    for i, line in enumerate(lines[:-1]):
        label = line.rstrip(": ").strip()
        if label in labels and labels[label] not in details:
            value = lines[i + 1]
            if labels[label] == "date_naissance":
                value = value.split(" ")[0]
            details[labels[label]] = value
    return details


def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    season = current_season()

    soup = get_soup(TEAM_URL)
    if not soup:
        print("❌ Arrêt du script : page non chargée.")
        exit(1)

    players = []
    for item in soup.find_all("li", class_="taxonomy-teams__player-grid-item"):
        if season not in (item.get("data-filter-item-slug-list") or "").split():
            continue
        article = item.find("article")
        link = article.find("a", class_="player-preview__link") if article else None
        if not link:
            continue

        number = article.find(class_="player-preview__number")
        subtitle = article.find(class_="player-preview__subtitle")
        fiche_url = link.get("href")
        player = {
            "nom": link.get_text(strip=True),
            "poste": subtitle.get_text(strip=True) if subtitle else None,
            "numéro": number.get_text(strip=True).lstrip("#") if number else None,
            "fiche_url": fiche_url,
            "image_url": image_url(article),
        }
        details = parse_details(fiche_url)
        player.update(
            {
                "date_naissance": details.get("date_naissance"),
                "age": age_from(details.get("date_naissance")),
                "ville": details.get("ville"),
                "taille": details.get("taille"),
                "poids": details.get("poids"),
                "pied": details.get("pied"),
            }
        )
        players.append(player)
        print(f"  • {player['nom']}")

    if not players:
        print(f"❌ Aucun joueur trouvé pour la saison {season}, fichier conservé.")
        exit(1)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2, ensure_ascii=False)
    print(f"✅ {len(players)} membres de l'effectif {season} enregistrés → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
