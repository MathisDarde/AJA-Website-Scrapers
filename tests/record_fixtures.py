"""
Enregistre les pages réelles utilisées par les tests (tests/fixtures/, compressées).

    python tests/record_fixtures.py

À relancer quand un site change sa mise en page : les tests montrent alors ce qui a bougé.
"""

import gzip
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "public", "scripts"))

from curl_cffi import requests  # noqa: E402

from common import TM_BASE, fetch_soup  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")

PAGES = {
    # Calendriers : saison du titre, saison Covid (28 journées), D2 en groupes, saison sans
    # championnat sur Transfermarkt (Coupe de France seulement), saison en cours
    "tm_calendrier_1995": f"{TM_BASE}/aj-auxerre/spielplan/verein/290/saison_id/1995",
    "tm_calendrier_2019": f"{TM_BASE}/aj-auxerre/spielplan/verein/290/saison_id/2019",
    "tm_calendrier_1974": f"{TM_BASE}/aj-auxerre/spielplan/verein/290/saison_id/1974",
    "tm_calendrier_1972": f"{TM_BASE}/aj-auxerre/spielplan/verein/290/saison_id/1972",
    "tm_calendrier_2026": f"{TM_BASE}/aj-auxerre/spielplan/verein/290/saison_id/2026",
    # Classements : points « 57:19 » d'avant 1981, D2 des années 70, saison en cours
    "tm_classement_fr1_1995": f"{TM_BASE}/ligue-1/tabelle/wettbewerb/FR1/saison_id/1995",
    "tm_classement_fr1_1980": f"{TM_BASE}/ligue-1/tabelle/wettbewerb/FR1/saison_id/1980",
    "tm_classement_fr2_1974": f"{TM_BASE}/ligue-2/tabelle/wettbewerb/FR2/saison_id/1974",
    "tm_classement_fr2_2023": f"{TM_BASE}/ligue-2/tabelle/wettbewerb/FR2/saison_id/2023",
    "tm_classement_fr1_2026": f"{TM_BASE}/ligue-1/tabelle/wettbewerb/FR1/saison_id/2026",
    # Statistiques des joueurs
    "tm_stats_1995": f"{TM_BASE}/aj-auxerre/leistungsdaten/verein/290/reldata/%261995/plus/1",
    # aja.fr : équipe pro et une fiche joueur
    "aja_equipe_pro": "https://www.aja.fr/equipes/equipe-pro/",
    "aja_fiche_diomande": "https://www.aja.fr/joueur/sinaly-diomande/",
}

# Wikitextes Wikipédia FR des galeries de logos
WIKI = {
    "wiki_aja": "Association de la jeunesse auxerroise",
    "wiki_marseille": "Olympique de Marseille",
    "wiki_metz": "Football Club de Metz",
    "wiki_toulouse": "Toulouse Football Club",
    "wiki_zenit": "Zénith Saint-Pétersbourg",
}


def save(name, text):
    with gzip.open(os.path.join(FIXTURES, f"{name}.gz"), "wt", encoding="utf-8") as f:
        f.write(text)
    print(f"✓ {name}")


def main():
    os.makedirs(FIXTURES, exist_ok=True)
    for name, url in PAGES.items():
        save(f"{name}.html", str(fetch_soup(url)))
    for name, title in WIKI.items():
        r = requests.get("https://fr.wikipedia.org/w/api.php", timeout=60,
                         headers={"User-Agent": "aja-blog-scrapers/1.0 (tests)"},
                         params={"action": "parse", "page": title, "prop": "wikitext", "redirects": 1, "format": "json"})
        save(f"{name}.wikitext", r.json()["parse"]["wikitext"]["*"])


if __name__ == "__main__":
    main()
