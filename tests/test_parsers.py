"""
Lecteurs de pages sur des pages réelles enregistrées (tests/fixtures, voir record_fixtures.py).
Les valeurs attendues sont des faits vérifiés (AJA championne 1995-1996 avec 72 points, etc.).
"""

import gzip
import os
import sys
from datetime import date

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "public", "scripts"))

import aja_calendrier_scrape as calendrier  # noqa: E402
import aja_effectif_scrape as effectif  # noqa: E402
import aja_players_stats_scrape as stats  # noqa: E402
import historical_logos  # noqa: E402
import ligue1_ranking_scrape as classement  # noqa: E402
from archive import _opponent, _score  # noqa: E402
from common import ScraperError, competition_from_soup, season_start_year  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def page(name):
    with gzip.open(os.path.join(FIXTURES, f"{name}.html.gz"), "rt", encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "html.parser")


def wikitext(name):
    with gzip.open(os.path.join(FIXTURES, f"{name}.wikitext.gz"), "rt", encoding="utf-8") as f:
        return f.read()


def aja(table):
    return next(team for team in table if "Auxerre" in team["equipe"])


FR1 = {"slug": "ligue-1", "id": "FR1", "name": "Ligue 1"}
FR2 = {"slug": "ligue-2", "id": "FR2", "name": "Ligue 2"}


# --- Saison ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "today, expected",
    [(date(2026, 6, 30), 2025), (date(2026, 7, 1), 2026), (date(2027, 1, 1), 2026), (date(2027, 7, 1), 2027)],
)
def test_season_switches_on_july_first(today, expected, monkeypatch):
    monkeypatch.delenv("SEASON", raising=False)
    assert season_start_year(today) == expected


def test_season_can_be_forced(monkeypatch):
    monkeypatch.setenv("SEASON", "1995")
    assert season_start_year(date(2026, 10, 15)) == 1995


# --- Championnat détecté sur le calendrier ----------------------------------------------------


@pytest.mark.parametrize("season, competition", [(1995, FR1), (2019, FR2), (1974, FR2), (2026, FR1)])
def test_competition_is_read_from_the_season_calendar(season, competition):
    assert competition_from_soup(page(f"tm_calendrier_{season}"), season) == competition


def test_cup_only_season_has_no_league():
    # 1972-1973 : seule la Coupe de France figure sur Transfermarkt
    with pytest.raises(ScraperError):
        competition_from_soup(page("tm_calendrier_1972"), 1972)


# --- Calendrier --------------------------------------------------------------------------------


def test_calendar_1995_title_season():
    matches = calendrier.parse_calendar(page("tm_calendrier_1995"), FR1)
    assert len(matches) == 38
    first = matches[0]
    assert first["date"] == "mer. 19 juil. 1995"
    assert first["contre"] == "FC Nantes (7.)"
    assert (first["dom_ext"], first["resultat"], first["adversaire_id"]) == ("E", "1:0", "995")


def test_calendar_2019_stopped_by_covid_after_28_matchdays():
    assert len(calendrier.parse_calendar(page("tm_calendrier_2019"), FR2)) == 28


def test_calendar_keeps_only_the_league_table():
    # La page liste aussi la Coupe de France : seules les journées de D2 doivent rester
    matches = calendrier.parse_calendar(page("tm_calendrier_1974"), FR2)
    assert len(matches) == 34
    assert all(m["journee"].isdigit() for m in matches)


def test_calendar_of_current_season_has_played_and_upcoming_matches():
    matches = calendrier.parse_calendar(page("tm_calendrier_2026"), FR1)
    assert len(matches) == 34
    played = [m for m in matches if m["resultat"] and m["resultat"] != "-:-"]
    assert 0 < len(played) < 34
    assert all(m["adversaire_id"] for m in matches)


# --- Classement --------------------------------------------------------------------------------


def test_ranking_1995_aja_champion():
    table = classement.parse_ranking(page("tm_classement_fr1_1995"), FR1, with_status=False)
    assert len(table) == 20
    assert {k: aja(table)[k] for k in ("position", "points", "gagnes", "nuls", "perdus", "buts_marques", "buts_encaisses")} == {
        "position": 1, "points": 72, "gagnes": 22, "nuls": 6, "perdus": 10, "buts_marques": 66, "buts_encaisses": 30,
    }
    assert aja(table)["club_id"] == "290"
    assert all(team["positionStatus"] == "" for team in table)


def test_ranking_before_three_points_per_win():
    # Transfermarkt affiche « 57:19 » (points pour et contre) avant 1981
    table = classement.parse_ranking(page("tm_classement_fr1_1980"), FR1, with_status=False)
    assert (table[0]["equipe"], table[0]["points"]) == ("Saint-Étienne", 57)
    assert (aja(table)["position"], aja(table)["points"]) == (10, 36)


def test_ranking_second_division_1974():
    table = classement.parse_ranking(page("tm_classement_fr2_1974"), FR2, with_status=False)
    assert len(table) == 18
    assert (aja(table)["position"], aja(table)["points"]) == (10, 37)


def test_ranking_zones_follow_the_competition():
    l2 = classement.parse_ranking(page("tm_classement_fr2_2023"), FR2, with_status=True)
    assert (aja(l2)["position"], aja(l2)["points"], aja(l2)["positionStatus"]) == (1, 74, "Ligue 1")

    l1 = classement.parse_ranking(page("tm_classement_fr1_2026"), FR1, with_status=True)
    assert len(l1) == 18
    assert l1[0]["positionStatus"] == "UEFA Champions League"
    assert [t["positionStatus"] for t in l1[-2:]] == ["Ligue 2", "Ligue 2"]


# --- Statistiques des joueurs ----------------------------------------------------------------


def test_player_stats_1995():
    players = stats.parse_players_table(page("tm_stats_1995"))
    assert len(players) == 29
    laslandes = next(p for p in players if p["nom"] == "Lilian Laslandes")
    assert laslandes["goals"] == "15"
    assert set(players[0]) >= {"numero", "nom", "age", "position", "matches", "goals", "assists", "minutes"}


# --- aja.fr -------------------------------------------------------------------------------------


def test_team_page_lists_players_and_staff_of_the_season():
    label, members = effectif.parse_team(page("aja_equipe_pro"), 2026)
    assert label == "2026-2027"
    assert len(members) == 48
    nardi = members[0]
    assert (nardi["nom"], nardi["poste"], nardi["numéro"]) == ("Paul Nardi", "Gardien", "1")
    assert nardi["image_url"].startswith("https://www.aja.fr/wp-content/uploads/")


def test_team_page_falls_back_to_previous_season_when_new_one_is_not_published():
    label, members = effectif.parse_team(page("aja_equipe_pro"), 2027)
    assert label == "2026-2027" and len(members) == 48


def test_player_page_details():
    assert effectif.details_from_soup(page("aja_fiche_diomande")) == {
        "date_naissance": "09/04/2001", "ville": "Yopougon", "taille": "1m84", "poids": "74Kg", "pied": "Droit",
    }


# --- Logos d'époque (Wikipédia FR) ---------------------------------------------------------------


@pytest.mark.parametrize(
    "caption, period",
    [
        ("{{Centrer|Avant 1992.}}", (None, 1991)),
        ("{{Centrer|1992-1997.}}", (1992, 1996)),
        ("{{Centrer|Depuis 1997.}}", (1997, None)),
        ("1979 à 1984", (1979, 1983)),
        ("Logo de 1962 à 2002.", (1962, 2001)),
        ("<center>Années 1960.</center>", (1960, 1969)),
        ("alt=Ecu rectangulaire blanc et vert|1978-1980.", (1978, 1979)),
        ("<center>Jusqu'en 1967</center>", (None, 1966)),
        ("Écusson entre 1999 et 2020.", (1999, 2019)),
        ("Logo actuel{{,}}(2026-)", (2026, None)),
        ("<center>1921 à 1934<ref>source</ref></center>", (1921, 1933)),
        ("Saison 1974-75", (1974, None)),
    ],
)
def test_logo_caption_periods(caption, period):
    assert historical_logos.parse_period(historical_logos.clean_caption(caption)) == period


def test_aja_logos_from_wikipedia():
    logos = historical_logos.logos_from_wikitext(wikitext("wiki_aja"))
    assert [(start, end) for _, _, start, end in logos] == [(None, 1991), (1992, 1996), (1997, None)]


def test_anniversary_logos_are_ignored():
    captions = [caption for _, caption, _, _ in historical_logos.logos_from_wikitext(wikitext("wiki_marseille"))]
    assert not any("anniversaire" in c.lower() for c in captions)
    assert "1993 à 2004" in captions


def test_single_year_logo_runs_until_the_next_one():
    # Metz : « 1936 » vaut jusqu'au logo de 1967
    periods = {(start, end) for _, _, start, end in historical_logos.logos_from_wikitext(wikitext("wiki_metz"))}
    assert (1936, 1966) in periods and (1967, 1999) in periods


def test_toulouse_periods_follow_each_other():
    periods = [(start, end) for _, _, start, end in historical_logos.logos_from_wikitext(wikitext("wiki_toulouse"))]
    assert periods[:6] == [(1979, 1983), (1984, 1989), (1990, 1994), (1995, 2000), (2001, 2009), (2010, 2017)]


# --- Archive ------------------------------------------------------------------------------------


def test_opponent_name_without_ranking():
    assert _opponent("FC Lorient (10.)") == "FC Lorient"
    assert _opponent("Paris SG") == "Paris SG"


@pytest.mark.parametrize(
    "resultat, dom_ext, score",
    [("2:1", "D", (2, 1)), ("2:1", "E", (1, 2)), ("-:-", "D", None), ("", "E", None)],
)
def test_score_from_aja_point_of_view(resultat, dom_ext, score):
    assert _score(resultat, dom_ext) == score
