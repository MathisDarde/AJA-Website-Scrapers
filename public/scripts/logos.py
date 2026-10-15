"""Logos des clubs : téléchargés une fois depuis Transfermarkt dans data/logos/<id>.png."""

import os
import re

from curl_cffi import requests

from common import DATA_DIR

LOGOS_DIR = "logos"
# Serveur d'images de Transfermarkt (pas de défi anti-robot, contrairement au site)
LOGO_URL = "https://tmssl.akamaized.net/images/wappen/head/{club_id}.png"

_failed = set()


def club_id_from(link):
    """Identifiant Transfermarkt d'un club à partir d'un lien « /fc-nantes/…/verein/995/… »."""
    match = link and re.search(r"/verein/(\d+)", link.get("href", ""))
    return match.group(1) if match else None


def ensure_logo(club_id):
    """
    Chemin du logo relatif à data/ (« logos/995.png »), téléchargé s'il manque ; None si
    le logo est introuvable (le blog retombe alors sur ses propres logos).
    """
    if not club_id or club_id in _failed:
        return None
    relative = f"{LOGOS_DIR}/{club_id}.png"
    path = os.path.join(DATA_DIR, relative)
    if os.path.exists(path):
        return relative

    try:
        response = requests.get(LOGO_URL.format(club_id=club_id), impersonate="chrome", timeout=20)
        if response.status_code == 200 and response.headers.get("content-type", "").startswith("image/"):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(response.content)
            print(f"🖼️  logo {club_id} téléchargé")
            return relative
        print(f"⚠️  logo {club_id} : HTTP {response.status_code}")
    except Exception as e:
        print(f"⚠️  logo {club_id} : {e}")
    _failed.add(club_id)
    return None
