"""Worth90 — bir ligin fikstür/maç listesini FotMob'dan çeker."""

import json
import re
import requests

from score import HEADERS


def fetch_league_matches(league_id: int) -> list[dict]:
    """Bir ligin sezon boyu tüm maçlarını (oynanmış + oynanmamış) döndürür."""
    url = f"https://www.fotmob.com/leagues/{league_id}/matches"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
        resp.text,
    )
    if not m:
        raise ValueError(f"__NEXT_DATA__ bulunamadı: league_id={league_id}")

    next_data = json.loads(m.group(1))
    page_props = next_data["props"]["pageProps"]
    all_matches = page_props["fixtures"]["allMatches"]
    return all_matches


def finished_matches_since(league_id: int, since_match_ids: set[str]) -> list[dict]:
    """Bittiği halde daha önce puanlanmamış (since_match_ids'te olmayan) maçları döndürür."""
    all_matches = fetch_league_matches(league_id)
    finished = [m for m in all_matches if m["status"].get("finished")]
    new_ones = [m for m in finished if m["id"] not in since_match_ids]
    return new_ones
