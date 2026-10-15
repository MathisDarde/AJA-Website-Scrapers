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
| `data/clubs.json` | Transfermarkt | Registre des clubs croisés (identifiant, noms, logo actuel dans `data/logos/`) |
| `data/logos-historiques.json` | Wikipédia FR + liste manuelle | Logos d'époque par club et par plage de saisons (`data/logos/historique/`) |

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

## Logos des clubs

Le blog affiche pour chaque club le logo **de la saison concernée** (classements, calendriers, historique, méthodes expert) :

1. logo d'époque de `data/logos-historiques.json`, la période la plus précise l'emportant ;
2. sinon le logo actuel du blog (`public/_assets/teamlogos`), puis celui de Transfermarkt (`data/clubs.json`) ;
3. sinon un écusson neutre.

Les logos d'époque sont lus automatiquement dans les galeries « Logos » des articles Wikipédia FR des clubs (article trouvé via Wikidata, propriété P7223 = identifiant Transfermarkt), pour chaque nouveau club du registre. Les logos d'anniversaire et la période en cours (« Depuis 1997 ») sont ignorés : la saison actuelle garde le logo actuel du blog.

**À compléter ou corriger à la main** dans `logos-historiques-manuels.json` (à la racine), prioritaire sur Wikipédia et jamais écrasé :

```json
{
  "290": [
    { "de": null, "a": 1991, "logo": "logos/historique/manuel/290-ancien.png" },
    { "de": 1998, "a": 1998, "ignorer": true }
  ]
}
```

- clé : identifiant Transfermarkt du club (`data/clubs.json`, AJ Auxerre = `290`) ;
- `de` / `a` : années de début de saison incluses (1992 = 1992-1993), `null` = sans limite ;
- `logo` : URL d'une image, ou chemin dans `data/` (image à déposer dans le dépôt) ;
- `"ignorer": true` : écarte les logos automatiques de cette période.

La liste est appliquée au passage suivant des scrapers. Pour relire tous les clubs sur Wikipédia : supprimer `data/logos-historiques-verifies.json`.

## Tests

Les lecteurs de pages (Transfermarkt, aja.fr, Wikipédia) sont testés sur de vraies pages enregistrées dans `tests/fixtures/` : saison du titre 1995-1996, saison Covid 2019-2020, D2 des années 70, points d'avant 1981, légendes de logos… Ils tournent à chaque push (`.github/workflows/tests.yml`).

```bash
pip install pytest
python -m pytest tests            # tests
python tests/record_fixtures.py   # réenregistre les pages (après un changement de mise en page)
```

Les pages enregistrées ne voient pas un changement de mise en page en direct : c'est le rôle des passages planifiés, qui échouent (run rouge + mail) dès qu'un lecteur renvoie trop peu de données.

## Lancer à la main

```bash
pip install -r requirements.txt
python public/scripts/run_all.py              # calendrier, classement, statistiques
python public/scripts/run_all.py --effectif   # + effectif
EFFECTIF_COMPLET=1 python public/scripts/run_all.py --effectif   # relit aussi toutes les fiches joueurs
```

Les fiches des joueurs (naissance, taille, pied) ne sont relues que pour les nouveaux venus, et pour tout l'effectif le lundi : un passage dure une trentaine de secondes au lieu de deux minutes.

Ou depuis GitHub : onglet **Actions** → *AJ Auxerre Scrapers* → **Run workflow** (effectif compris).
