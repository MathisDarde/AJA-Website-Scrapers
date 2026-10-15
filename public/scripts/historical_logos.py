"""
Logos d'époque des clubs : lus dans les galeries « Logos » de Wikipédia FR, complétés et
corrigés à la main dans logos-historiques-manuels.json (racine du dépôt, prioritaire).

    data/logos-historiques.json   { "<id Transfermarkt>": [ { "de", "a", "logo", "legende", "source" } ] }
    data/logos/historique/        images téléchargées (PNG 200 px)

« de » et « a » sont des années de début de saison incluses (1992 = 1992-1993), null = sans
limite. Seuls les logos *passés* sont gardés : la période en cours reste au logo actuel du blog.
"""

import hashlib
import os
import re
from urllib.parse import quote, unquote

from curl_cffi import requests

from common import DATA_DIR, read_json, season_start_year, write_dataset

OUTPUT_FILE = "logos-historiques.json"
MANUAL_FILE = os.path.abspath(os.path.join(DATA_DIR, "..", "logos-historiques-manuels.json"))
IMAGES_DIR = "logos/historique"
# Clubs déjà examinés sur Wikipédia (même sans résultat), pour ne pas tout relire à chaque passage
CHECKED_FILE = "logos-historiques-verifies.json"

HEADERS = {
    "User-Agent": "aja-blog-scrapers/1.0 (https://github.com/mathisdarde/AJA-Website-Scrapers)",
    "Accept": "application/sparql-results+json, application/json",
}
YEAR = r"(1[89]\d\d|20\d\d)"


def _get(url, **kw):
    for _ in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60, **kw)
            if r.status_code == 200:
                return r
        except Exception:
            pass
    return None


def wikipedia_articles(club_ids):
    """Identifiant Transfermarkt → titre de l'article Wikipédia FR (via Wikidata, propriété P7223)."""
    articles = {}
    ids = list(club_ids)
    for i in range(0, len(ids), 100):
        values = " ".join(f'"{c}"' for c in ids[i:i + 100])
        query = (f"SELECT ?tm ?article WHERE {{ VALUES ?tm {{ {values} }} ?club wdt:P7223 ?tm . "
                 "?article schema:about ?club ; schema:isPartOf <https://fr.wikipedia.org/> . }")
        r = _get("https://query.wikidata.org/sparql", params={"query": query})
        if not r:
            continue
        for b in r.json()["results"]["bindings"]:
            articles[b["tm"]["value"]] = unquote(b["article"]["value"].split("/wiki/")[1]).replace("_", " ")
    return articles


def clean_caption(raw):
    """Légende lisible : sans paramètres d'image (alt=…), balises, modèles ni références."""
    text = re.sub(r"<ref[^>]*>.*?</ref>|<ref[^/]*/>", "", raw, flags=re.S)
    # Modèles ({{Centrer|…}}) et liens ([[…|…]]) d'abord, pour que leurs « | » ne coupent pas la légende
    for _ in range(3):
        text = re.sub(r"\{\{[^|{}]*\}\}", "", text)  # {{ref nec}}, {{douteux}} : sans contenu
        text = re.sub(r"\{\{[^|{}]*\|([^{}]*)\}\}", r"\1", text)
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", text)
    parts = [p for p in text.split("|") if not re.match(r"\s*(alt|upright|link|lien|class)\s*=", p)]
    text = parts[-1] if parts else ""
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"'{2,}|\s+", " ", text).strip(" .")


def parse_period(caption):
    """(de, a) d'après la légende ; une date de changement Y ouvre la saison Y-(Y+1)."""
    c = caption.lower()
    if m := re.search(rf"ann[ée]es\s+{YEAR}", c):
        start = int(m.group(1))
        return start, start + 9
    if m := re.search(rf"{YEAR}\s*(?:-|–|à|au|et)\s*{YEAR}", c):
        start, end = int(m.group(1)), int(m.group(2))
        return start, max(start, end - 1)
    if m := re.search(rf"(?:depuis|à partir de|dès)\s+{YEAR}", c) or re.search(rf"{YEAR}\s*[-–]\s*(?!\s*\d)", c):
        return int(m.group(1)), None  # « depuis 1997 », « (2026-) »
    if m := re.search(rf"(?:avant|jusqu'en|jusqu’en|jusqu'à)\s+{YEAR}", c):
        return None, int(m.group(1)) - 1
    if m := re.search(YEAR, c):
        return int(m.group(1)), None  # année seule : bornée plus bas par le logo suivant
    return None


def gallery_logos(title):
    """Logos datés des galeries de l'article : [(fichier, légende, de, a)]."""
    r = _get("https://fr.wikipedia.org/w/api.php",
             params={"action": "parse", "page": title, "prop": "wikitext", "redirects": 1, "format": "json"})
    return logos_from_wikitext(r.json().get("parse", {}).get("wikitext", {}).get("*", "") if r else "")


def logos_from_wikitext(text):
    """Logos datés des galeries d'un wikitexte déjà téléchargé : [(fichier, légende, de, a)]."""
    found = []
    for gallery in re.findall(r"<gallery[^>]*>(.*?)</gallery>", text, re.S):
        for line in gallery.split("\n"):
            m = re.match(r"\s*(?:Fichier|File|Image)\s*:\s*([^|]+)\|(.*)", line)
            if not m or not re.search(r"logo|blason|[ée]cusson", m.group(1) + m.group(2), re.I):
                continue
            caption = clean_caption(m.group(2))
            # Logos d'anniversaire ou spéciaux d'une saison : on garde le logo d'identité du club
            if re.search(r"anniversaire|centenaire|sp[ée]cial|commémorati", caption + m.group(1), re.I):
                continue
            period = parse_period(caption)
            if period:
                found.append((m.group(1).strip(), caption, *period))

    # Une année seule (« 1936 ») court jusqu'au logo suivant
    found.sort(key=lambda f: (f[2] is not None, f[2] or 0))
    bounded = []
    for i, (file, caption, start, end) in enumerate(found):
        if end is None and start is not None and i + 1 < len(found) and found[i + 1][2]:
            if not re.search(r"depuis|à partir|dès", caption, re.I):
                end = max(start, found[i + 1][2] - 1)
        bounded.append((file, caption, start, end))
    return bounded


def download_image(file, club_id, start):
    relative = f"{IMAGES_DIR}/{club_id}-{start or 'avant'}-{hashlib.md5(file.encode()).hexdigest()[:6]}.png"
    path = os.path.join(DATA_DIR, relative)
    if os.path.exists(path):
        return relative
    r = _get(f"https://fr.wikipedia.org/wiki/Special:FilePath/{quote(file.replace(' ', '_'))}", params={"width": 200})
    if not r or not r.headers.get("content-type", "").startswith("image/"):
        return None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(r.content)
    return relative


def update(club_ids, refresh=False):
    """Complète data/logos-historiques.json pour les clubs pas encore examinés (tous si refresh)."""
    current = season_start_year()
    auto = read_json(os.path.join(DATA_DIR, "logos-historiques-auto.json"), {})
    checked = set(read_json(os.path.join(DATA_DIR, CHECKED_FILE), []))
    todo = [c for c in club_ids if refresh or c not in checked]

    if todo:
        print(f"🖼️  Logos d'époque : {len(todo)} club(s) à examiner sur Wikipédia")
        articles = wikipedia_articles(todo)
        for club_id in todo:
            entries = []
            for file, caption, start, end in gallery_logos(articles[club_id]) if club_id in articles else []:
                # Période en cours : on garde le logo actuel du blog
                if end is None or end >= current:
                    continue
                logo = download_image(file, club_id, start)
                if logo:
                    entries.append({"de": start, "a": end, "logo": logo, "legende": caption,
                                    "source": f"Wikipédia : {articles[club_id]}"})
            if entries:
                auto[club_id] = entries
                print(f"   {club_id} {articles[club_id]} : {len(entries)} logo(s)")
            checked.add(club_id)
        write_dataset("logos-historiques-auto.json", auto, minimum=0, context={}, record_meta=False)
        write_dataset(CHECKED_FILE, sorted(checked, key=int), minimum=0, context={}, record_meta=False)

    # Liste manuelle prioritaire : remplace les périodes automatiques qu'elle recouvre
    manual = read_json(MANUAL_FILE, {})
    merged = {k: list(v) for k, v in auto.items()}
    for club_id, entries in manual.items():
        if club_id.startswith("_"):
            continue  # clés de documentation
        kept = [e for e in merged.get(club_id, []) if not any(_overlaps(e, m) for m in entries)]
        merged[club_id] = sorted(
            [{**m, "source": "manuel"} for m in entries if not m.get("ignorer")] + kept,
            key=lambda e: e.get("de") or 0,
        )
        if not merged[club_id]:
            del merged[club_id]
    write_dataset(OUTPUT_FILE, dict(sorted(merged.items(), key=lambda c: int(c[0]))), minimum=0, context={}, record_meta=False)


def _overlaps(a, b):
    lo_a, hi_a = a.get("de") or -1, a.get("a") or 10_000
    lo_b, hi_b = b.get("de") or -1, b.get("a") or 10_000
    return lo_a <= hi_b and lo_b <= hi_a
