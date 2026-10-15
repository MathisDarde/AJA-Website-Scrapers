"""
Archive des saisons de l'AJA : data/saisons/<année>/ et deux fichiers de synthèse.

    data/saisons/2026/saison.json        saison et championnat
    data/saisons/2026/calendrier.json    matchs de championnat
    data/saisons/2026/classement.json    classement du championnat
    data/saisons/2026/statistiques.json  statistiques des joueurs
    data/saisons/index.json              parcours de l'AJA, une ligne par saison
    data/saisons/matchs.json             tous les matchs de championnat, toutes saisons
    data/clubs.json                      registre des clubs croisés : noms et logo actuel
"""

import os
import re

from common import DATA_DIR, TM_CLUB_ID, read_json, season_label, write_dataset
from logos import ensure_logo
import historical_logos

SEASONS_DIR = "saisons"


def season_path(season, name):
    return f"{SEASONS_DIR}/{season}/{name}.json"


def is_archived(season):
    return all(
        os.path.exists(os.path.join(DATA_DIR, season_path(season, name)))
        for name in ("saison", "calendrier", "classement")
    )


def write_season(season, competition, calendrier, classement, statistiques):
    """Archive une saison ; un jeu de données manquant (None) laisse l'éventuel fichier existant."""
    write_dataset(season_path(season, "saison"), {"seasonId": season, "season": season_label(season), "competition": competition},
                  minimum=1, context={}, record_meta=False)
    # Seuils bas : 2019-2020 s'est arrêtée après 28 journées (Covid), les stats des années 70 sont lacunaires
    for name, data, minimum in (("calendrier", calendrier, 20), ("classement", classement, 10), ("statistiques", statistiques, 1)):
        if data is not None:
            write_dataset(season_path(season, name), data, minimum=minimum, context={}, record_meta=False)


def _opponent(contre):
    """« FC Lorient (10.) » → « FC Lorient »."""
    return re.sub(r"\s*\(\d+\.\)\s*$", "", contre or "").strip()


def _score(resultat, dom_ext):
    """Buts de l'AJA et de l'adversaire, ou None si le match n'est pas joué."""
    match = re.match(r"(\d+):(\d+)", resultat or "")
    if not match:
        return None
    home, away = int(match.group(1)), int(match.group(2))
    return (home, away) if dom_ext == "D" else (away, home)


def build_index():
    """Reconstruit index.json et matchs.json à partir des saisons archivées."""
    root = os.path.join(DATA_DIR, SEASONS_DIR)
    seasons = sorted((int(d) for d in os.listdir(root) if d.isdigit()), reverse=True) if os.path.isdir(root) else []

    index, matchs = [], []
    # Registre des clubs : identifiant Transfermarkt → noms rencontrés (du plus récent au plus ancien)
    clubs = {str(TM_CLUB_ID): {"nom": "AJ Auxerre", "noms": ["AJ Auxerre", "Auxerre", "AJA"]}}

    def register(club_id, *names):
        if not club_id:
            return
        club = clubs.setdefault(club_id, {"nom": next(n for n in names if n), "noms": []})
        for name in names:
            if name and name not in club["noms"]:
                club["noms"].append(name)

    for season in seasons:
        infos = read_json(os.path.join(root, str(season), "saison.json"), None)
        if not infos:
            continue
        classement = read_json(os.path.join(root, str(season), "classement.json"), [])
        calendrier = read_json(os.path.join(root, str(season), "calendrier.json"), [])
        aja = next((team for team in classement if "Auxerre" in team["equipe"]), None)

        index.append({
            "seasonId": season,
            "season": infos["season"],
            "competition": infos["competition"],
            "equipes": len(classement),
            "aja": {k: aja[k] for k in ("position", "points", "matchs_joues", "gagnes", "nuls", "perdus",
                                        "buts_marques", "buts_encaisses")} if aja else None,
        })

        for team in classement:
            register(team.get("club_id"), team["equipe"], team.get("nom_complet"))

        for m in calendrier:
            register(m.get("adversaire_id"), _opponent(m.get("contre")), m.get("adversaire_nom_complet"))
            score = _score(m.get("resultat"), m.get("dom_ext"))
            matchs.append({
                "seasonId": season,
                "competition": infos["competition"]["id"],
                "journee": m.get("journee"),
                "date": m.get("date"),
                "horaire": m.get("horaire"),
                "dom_ext": m.get("dom_ext"),
                "adversaire": _opponent(m.get("contre")),
                "adversaire_id": m.get("adversaire_id"),
                "resultat": m.get("resultat"),
                "buts_aja": score[0] if score else None,
                "buts_adversaire": score[1] if score else None,
                "spectateurs": m.get("spectateurs"),
            })

    if index:
        write_dataset(f"{SEASONS_DIR}/index.json", index, minimum=1, context={}, record_meta=False)
        write_dataset(f"{SEASONS_DIR}/matchs.json", matchs, minimum=1, context={}, record_meta=False)

    # Logo actuel de chaque club (téléchargé une fois) ; les logos d'époque sont gérés par
    # l'admin du blog, Wikidata étant trop lacunaire et parfois faux pour les logos datés
    for club_id, club in clubs.items():
        club["logo"] = ensure_logo(club_id)
    write_dataset("clubs.json", dict(sorted(clubs.items(), key=lambda c: int(c[0]))), minimum=1, context={}, record_meta=False)

    # Logos d'époque (Wikipédia FR + liste manuelle) des clubs pas encore examinés
    historical_logos.update(clubs.keys())
