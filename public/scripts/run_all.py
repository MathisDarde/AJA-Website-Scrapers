"""
Lance les scrapers pour la saison en cours et met à jour data/*.json.

    python public/scripts/run_all.py              # calendrier, classement, statistiques
    python public/scripts/run_all.py --effectif   # + effectif (aja.fr, une requête par joueur)

Chaque scraper est indépendant : un échec n'empêche pas les autres de tourner et laisse
le fichier précédent en place. Le code de sortie est non nul si au moins un a échoué,
pour que GitHub Actions le signale.
"""

import sys
import traceback

import aja_calendrier_scrape
import aja_effectif_scrape
import aja_players_stats_scrape
import ligue1_ranking_scrape
from common import ScraperError, detect_competition, season_context, season_label, season_start_year, write_dataset


def main():
    season = season_start_year()
    print(f"🗓️  Saison {season_label(season)}")
    failures = []
    jobs = []

    try:
        competition = detect_competition(season)
        print(f"🏆 Championnat : {competition['name']} ({competition['id']})")
        context = season_context(season, competition)
        jobs += [
            # (fichier, scraper, minimum d'éléments attendus)
            (aja_calendrier_scrape.OUTPUT_FILE, lambda: aja_calendrier_scrape.scrape(season, competition), 30),
            (ligue1_ranking_scrape.OUTPUT_FILE, lambda: ligue1_ranking_scrape.scrape(season, competition), 16),
            (aja_players_stats_scrape.OUTPUT_FILE, lambda: aja_players_stats_scrape.scrape(season), 15),
        ]
    except ScraperError as e:
        # Transfermarkt injoignable : l'effectif (aja.fr) peut quand même être mis à jour
        print(f"❌ {e}")
        failures.append("transfermarkt")
        context = {}

    if "--effectif" in sys.argv:
        jobs.append((aja_effectif_scrape.OUTPUT_FILE, lambda: aja_effectif_scrape.scrape(season), 20))

    for filename, scrape, minimum in jobs:
        print(f"\n— {filename}")
        try:
            write_dataset(filename, scrape(), minimum, context)
        except ScraperError as e:
            print(f"❌ {e}")
            failures.append(filename)
        except Exception:
            traceback.print_exc()
            failures.append(filename)

    if failures:
        print(f"\n❌ Échec : {', '.join(failures)} (fichiers précédents conservés)")
        sys.exit(1)
    print("\n✅ Tous les scrapers ont réussi")


if __name__ == "__main__":
    main()
