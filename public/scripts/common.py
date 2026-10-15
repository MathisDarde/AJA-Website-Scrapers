"""Outils partagés par les scrapers : saison en cours, requêtes HTTP, écriture des JSON."""

from curl_cffi import requests
from bs4 import BeautifulSoup
from datetime import date, datetime, timezone
import json
import os
import random
import re
import time

# data/ à la racine du dépôt, quel que soit le dossier depuis lequel on lance les scripts
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
META_FILE = os.path.join(DATA_DIR, "meta.json")

TM_BASE = "https://www.transfermarkt.fr"
TM_CLUB_ID = 290  # AJ Auxerre

# Mois de bascule vers la saison suivante : la Ligue 1 se termine fin mai (barrages début juin)
# et le calendrier de la saison suivante est publié courant juin.
SEASON_SWITCH_MONTH = 7


class ScraperError(Exception):
    """Données introuvables ou incohérentes : le fichier existant est conservé."""


def season_start_year(today=None):
    """Année de début de la saison en cours (2026 pour 2026-2027), forçable avec SEASON=2025."""
    forced = os.environ.get("SEASON")
    if forced:
        return int(forced)
    today = today or date.today()
    return today.year if today.month >= SEASON_SWITCH_MONTH else today.year - 1


def season_label(start_year):
    return f"{start_year}-{start_year + 1}"


def season_context(start_year, competition):
    """Infos de saison enregistrées dans meta.json avec chaque fichier."""
    return {"season": season_label(start_year), "seasonId": start_year, "competition": competition}


# Jeton du pare-feu AWS WAF de Transfermarkt, obtenu par un vrai navigateur (voir _solve_waf_challenge)
_waf = {"cookies": None, "user_agent": None}


def _solve_waf_challenge(url):
    """
    Depuis les serveurs de GitHub Actions, Transfermarkt répond à toute requête par un défi
    JavaScript (HTTP 202, x-amzn-waf-action: challenge). Un Chrome sans interface le résout en
    quelques secondes ; ses cookies (aws-waf-token) et son user-agent servent ensuite aux
    requêtes normales. Chrome est préinstallé sur les runners GitHub.
    """
    from playwright.sync_api import sync_playwright  # seulement si le défi apparaît

    print("🛡️  Défi anti-robot de Transfermarkt : résolution avec Chrome sans interface…")
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            browser = p.chromium.launch(headless=True)  # Chromium de Playwright, si installé
        page = browser.new_page(locale="fr-FR")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector("table", timeout=45000)
        _waf["cookies"] = {c["name"]: c["value"] for c in page.context.cookies()}
        _waf["user_agent"] = page.evaluate("navigator.userAgent")
        browser.close()
    print("🛡️  Défi résolu")


def fetch_soup(url, attempts=4):
    """Page HTML, en imitant Chrome et en réessayant avec un délai croissant."""
    last_error = None
    challenge_solved = False
    for attempt in range(1, attempts + 1):
        time.sleep(random.uniform(1, 3))
        try:
            print(f"📡 {url} (essai {attempt}/{attempts})")
            headers = {"Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}
            if _waf["user_agent"]:
                headers["User-Agent"] = _waf["user_agent"]
            response = requests.get(
                url,
                impersonate="chrome",
                headers=headers,
                cookies=_waf["cookies"],
                timeout=30,
            )
            if response.status_code == 200:
                return BeautifulSoup(response.content, "html.parser")
            last_error = f"HTTP {response.status_code}"
            if response.headers.get("x-amzn-waf-action") == "challenge" and not challenge_solved:
                # Une seule résolution par page ; le jeton sert ensuite à toutes les suivantes
                _solve_waf_challenge(url)
                challenge_solved = True
                continue
        except ScraperError:
            raise
        except Exception as e:  # réseau, TLS, timeout, navigateur…
            last_error = str(e)
        print(f"⚠️  {last_error}")
        if attempt < attempts:
            time.sleep(15 * attempt)
    raise ScraperError(f"{url} inaccessible après {attempts} essais ({last_error})")


def detect_competition(season):
    """
    Championnat de l'AJA pour la saison (Ligue 1, Ligue 2…), lu sur le calendrier de cette
    saison : c'est le titre lié à une compétition au-dessus du tableau par journées.
    (L'en-tête de la page du club, lui, donne toujours le championnat actuel.)
    """
    soup = fetch_soup(f"{TM_BASE}/aj-auxerre/spielplan/verein/{TM_CLUB_ID}/saison_id/{season}")
    for title in soup.find_all("h2"):
        link = title.find("a", href=re.compile(r"/startseite/wettbewerb/"))
        table = title.find_next("table")
        headers = [th.get_text(strip=True) for th in table.find_all("th")] if table else []
        if link and "Journée" in headers:
            match = re.match(r"/([^/]+)/startseite/wettbewerb/([^/?#]+)", link["href"])
            if match:
                return {"slug": match.group(1), "id": match.group(2), "name": title.get_text(strip=True)}
    raise ScraperError(f"Championnat de l'AJA introuvable pour la saison {season_label(season)}")


def _read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_dataset(filename, data, minimum, context):
    """
    Écrit data/<filename> si les données sont plausibles (au moins `minimum` éléments)
    et ont changé ; met à jour meta.json en conséquence. Renvoie True si le fichier a changé.
    """
    if len(data) < minimum:
        raise ScraperError(f"{filename} : {len(data)} éléments, {minimum} attendus au minimum")

    path = os.path.join(DATA_DIR, filename)
    os.makedirs(DATA_DIR, exist_ok=True)
    if _read_json(path, None) == data:
        print(f"= {filename} inchangé ({len(data)} éléments)")
        return False

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    meta = _read_json(META_FILE, {})
    meta.update(context)
    meta.setdefault("files", {})[filename] = {
        "updatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "items": len(data),
    }
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"✅ {filename} mis à jour ({len(data)} éléments)")
    return True
