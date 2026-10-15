"""
Remplit l'archive des saisons passées (une fois pour toutes ; la saison en cours est
archivée par run_all.py à chaque passage).

    python public/scripts/backfill.py              # de 1974 à la saison précédente, saisons manquantes
    python public/scripts/backfill.py 2010 2015    # plage précise
    python public/scripts/backfill.py --force      # réécrit aussi les saisons déjà archivées
"""

import sys
import time

import aja_calendrier_scrape
import aja_players_stats_scrape
import ligue1_ranking_scrape
from archive import build_index, is_archived, write_season
from common import ScraperError, detect_competition, season_label, season_start_year

# Plus ancienne saison de championnat de l'AJA disponible sur Transfermarkt (D2 1974-1975)
FIRST_SEASON = 1974


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    first = int(args[0]) if args else FIRST_SEASON
    last = int(args[1]) if len(args) > 1 else season_start_year() - 1
    force = "--force" in sys.argv

    failures = []
    for season in range(first, last + 1):
        if is_archived(season) and not force:
            continue
        print(f"\n=== {season_label(season)}")
        try:
            competition = detect_competition(season)
            print(f"🏆 {competition['name']}")
            calendrier = aja_calendrier_scrape.scrape(season, competition)
            classement = ligue1_ranking_scrape.scrape(season, competition, with_status=False)
            try:
                statistiques = aja_players_stats_scrape.scrape(season)
            except ScraperError as e:
                print(f"⚠️  statistiques : {e}")
                statistiques = None
            write_season(season, competition, calendrier, classement, statistiques)
        except ScraperError as e:
            print(f"❌ {e}")
            failures.append(season_label(season))
        time.sleep(2)

    build_index()
    if failures:
        print(f"\n⚠️  Saisons non archivées : {', '.join(failures)}")


if __name__ == "__main__":
    main()
