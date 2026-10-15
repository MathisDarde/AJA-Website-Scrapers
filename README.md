# AJA Website Scrapers

Données de l'AJ Auxerre publiées en JSON sur GitHub Pages pour [Mémoire d'Auxerrois](https://memoiredauxerrois.fr) :

| Fichier | Source | Contenu |
| --- | --- | --- |
| `data/aja_calendrier.json` | Transfermarkt | Matchs de championnat de la saison, avec les résultats |
| `data/classementligue1.json` | Transfermarkt | Classement du championnat de l'AJA (nom historique, Ligue 2 comprise) |
| `data/aja_statistics.json` | Transfermarkt | Statistiques des joueurs, toutes compétitions |
| `data/aja_effectif.json` | aja.fr | Effectif et staff de la saison |
| `data/meta.json` | — | Saison, championnat détecté, date de dernière mise à jour de chaque fichier |
| `data/saisons/<année>/` | Transfermarkt | Archive d'une saison (`saison`, `calendrier`, `classement`, `statistiques`), depuis 1974-1975 |
| `data/saisons/index.json` | — | Parcours de l'AJA : championnat, rang, points et bilan de chaque saison |
| `data/saisons/matchs.json` | — | Tous les matchs de championnat de l'AJA, toutes saisons (historique, confrontations) |

## Fonctionnement

- **Saison automatique** : la saison bascule le 1er juillet (2026-2027 à partir du 01/07/2026). Pour forcer une saison : `SEASON=2025`.
- **Championnat automatique** : Ligue 1 ou Ligue 2, lu chaque saison sur le calendrier Transfermarkt du club ; le classement et ses zones (Europe, barrages, relégation / montée) suivent.
- **GitHub Actions** (`.github/workflows/daily_scraper.yml`) : calendrier, classement et statistiques toutes les 2 heures, effectif une fois par jour. Un commit n'est fait que si les données changent, et un commit vide toutes les 4 semaines au plus empêche GitHub de désactiver les cron pendant l'intersaison.
- **Échecs** : chaque requête est retentée 4 fois ; un scraper en échec, ou qui renvoie trop peu de données, garde le fichier précédent et rend le run rouge (mail de GitHub), sans bloquer les autres.

## Archive des saisons

La saison en cours est archivée à chaque passage de `run_all.py` : à la bascule de juillet, la saison terminée reste donc dans `data/saisons/` avec son état final. Les saisons précédentes ont été remplies une fois pour toutes :

```bash
python public/scripts/backfill.py              # de 1974 à la saison précédente, saisons manquantes
python public/scripts/backfill.py 2010 2015    # plage précise
python public/scripts/backfill.py --force      # réécrit aussi les saisons déjà archivées
```

Transfermarkt bloque les serveurs de GitHub par un défi anti-robot (HTTP 202) : `common.py` le fait résoudre par un Chrome sans interface (Playwright) au premier défi rencontré, puis réutilise son jeton.

## Lancer à la main

```bash
pip install -r requirements.txt
python public/scripts/run_all.py              # calendrier, classement, statistiques
python public/scripts/run_all.py --effectif   # + effectif
EFFECTIF_COMPLET=1 python public/scripts/run_all.py --effectif   # relit aussi toutes les fiches joueurs
```

Les fiches des joueurs (naissance, taille, pied) ne sont relues que pour les nouveaux venus, et pour tout l'effectif le lundi : un passage dure une trentaine de secondes au lieu de deux minutes.

Ou depuis GitHub : onglet **Actions** → *AJ Auxerre Scrapers* → **Run workflow** (effectif compris).
