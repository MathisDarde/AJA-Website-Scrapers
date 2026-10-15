# AJA Website Scrapers

Données de l'AJ Auxerre publiées en JSON sur GitHub Pages pour [Mémoire d'Auxerrois](https://memoiredauxerrois.fr) :

| Fichier | Source | Contenu |
| --- | --- | --- |
| `data/aja_calendrier.json` | Transfermarkt | Matchs de championnat de la saison, avec les résultats |
| `data/classementligue1.json` | Transfermarkt | Classement du championnat de l'AJA (nom historique, Ligue 2 comprise) |
| `data/aja_statistics.json` | Transfermarkt | Statistiques des joueurs, toutes compétitions |
| `data/aja_effectif.json` | aja.fr | Effectif et staff de la saison |
| `data/meta.json` | — | Saison, championnat détecté, date de dernière mise à jour de chaque fichier |

## Fonctionnement

- **Saison automatique** : la saison bascule le 1er juillet (2026-2027 à partir du 01/07/2026). Pour forcer une saison : `SEASON=2025`.
- **Championnat automatique** : Ligue 1 ou Ligue 2, lu chaque saison sur le calendrier Transfermarkt du club ; le classement et ses zones (Europe, barrages, relégation / montée) suivent.
- **GitHub Actions** (`.github/workflows/daily_scraper.yml`) : calendrier, classement et statistiques toutes les 2 heures, effectif une fois par jour. Un commit n'est fait que si les données changent, et un commit vide toutes les 4 semaines au plus empêche GitHub de désactiver les cron pendant l'intersaison.
- **Échecs** : chaque requête est retentée 4 fois ; un scraper en échec, ou qui renvoie trop peu de données, garde le fichier précédent et rend le run rouge (mail de GitHub), sans bloquer les autres.

## Lancer à la main

```bash
pip install -r requirements.txt
python public/scripts/run_all.py              # calendrier, classement, statistiques
python public/scripts/run_all.py --effectif   # + effectif
```

Ou depuis GitHub : onglet **Actions** → *AJ Auxerre Scrapers* → **Run workflow** (effectif compris).
