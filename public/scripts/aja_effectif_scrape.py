from datetime import date
import json
import os
import re

from common import DATA_DIR, ScraperError, fetch_soup, season_label, season_start_year, write_dataset

TEAM_URL = "https://www.aja.fr/equipes/equipe-pro/"
OUTPUT_FILE = "aja_effectif.json"

DETAIL_FIELDS = ("date_naissance", "ville", "taille", "poids", "pied")


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
    soup = fetch_soup(fiche_url, attempts=2)
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


def team_items(soup, season):
    return [
        item
        for item in soup.find_all("li", class_="taxonomy-teams__player-grid-item")
        if season in (item.get("data-filter-item-slug-list") or "").split()
    ]


def scrape(season):
    soup = fetch_soup(TEAM_URL)

    # En début de saison, le site du club peut ne pas encore avoir rattaché l'effectif
    # à la nouvelle saison : on garde alors celui de la précédente.
    label = season_label(season)
    items = team_items(soup, label)
    if not items:
        label = season_label(season - 1)
        items = team_items(soup, label)
        print(f"ℹ️  Effectif {season_label(season)} pas encore publié, on garde {label}")

    try:
        with open(os.path.join(DATA_DIR, OUTPUT_FILE), encoding="utf-8") as f:
            previous = {p["fiche_url"]: p for p in json.load(f)}
    except (OSError, ValueError, KeyError):
        previous = {}

    players = []
    for item in items:
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
        try:
            details = parse_details(fiche_url)
        except ScraperError as e:
            # Fiche momentanément inaccessible : on reprend ce qu'on savait déjà
            print(f"⚠️  {e}")
            details = {k: previous.get(fiche_url, {}).get(k) for k in DETAIL_FIELDS}
        player.update({k: details.get(k) for k in DETAIL_FIELDS})
        player["age"] = age_from(player["date_naissance"])
        players.append(player)
        print(f"  • {player['nom']}")

    return players


def main():
    write_dataset(OUTPUT_FILE, scrape(season_start_year()), minimum=20, context={})


if __name__ == "__main__":
    main()
