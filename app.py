"""Worth90: nazik FotMob toplayıcısı ve özet videosu API'si.

Kullanım:
  py -m pip install -r requirements.txt
  set YOUTUBE_API_KEY=...        # yalnızca video araması için
  py app.py collect --limit 8
  py app.py serve
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from flask import Flask, jsonify, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "worth90.sqlite3"
USER_AGENT = "Worth90 research collector/1.0 (personal, low-volume)"
LEAGUES = {
    "Premier Lig": {"id": 47, "slug": "premier-league"},
    "La Liga": {"id": 87, "slug": "laliga"},
    "Serie A": {"id": 55, "slug": "serie-a"},
    "Ligue 1": {"id": 53, "slug": "ligue-1"},
    "Bundesliga": {"id": 54, "slug": "bundesliga"},
    "Süper Lig": {"id": 71, "slug": "super-lig"},
    "Şampiyonlar Ligi": {"id": 42, "slug": "champions-league"},
    "Avrupa Ligi": {"id": 73, "slug": "europa-league"},
    "Konferans Ligi": {"id": 10216, "slug": "uefa-conference-league"},
}
CHANNELS = {
    "BEIN_SPORTS_TR": "UCPe9vNjHF1kEExT5kHwc7aw",
    "S_SPORT": "UCpdSUUHlxMjO0c5824FGcsA",
    "TRT_SPOR": "UCfYNqluOf8EbQkL44otydMw",
}


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS matches (
          match_id TEXT PRIMARY KEY, date TEXT, league TEXT, home TEXT, away TEXT,
          score TEXT, points REAL, tiers_json TEXT, collected_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS highlights (
          match_id TEXT PRIMARY KEY, video_id TEXT, title TEXT, channel TEXT,
          checked_at TEXT NOT NULL
        );
    """)
    return conn


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8"})
    return s


def fetch_html(s: requests.Session, url: str) -> str:
    response = s.get(url, timeout=25)
    response.raise_for_status()
    return response.text


def next_data(html: str) -> dict[str, Any]:
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not match:
        raise ValueError("FotMob sayfasındaki __NEXT_DATA__ bulunamadı; sayfa yapısı değişmiş olabilir.")
    return json.loads(match.group(1))


def as_number(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    found = re.search(r"-?[0-9]+(?:[.,][0-9]+)?", str(value))
    return float(found.group(0).replace(",", ".")) if found else 0.0


def stats_map(content: dict[str, Any]) -> dict[str, list[Any]]:
    result: dict[str, list[Any]] = {}
    for group in content.get("stats", {}).get("Periods", {}).get("All", {}).get("stats", []):
        for item in group.get("stats", []):
            values = item.get("stats")
            if isinstance(values, list) and len(values) == 2:
                result[item.get("key", "")] = values
    return result


def score_content(content: dict[str, Any]) -> dict[str, float]:
    """Kullanıcının Tier 1-5 modelini güvenli eksik-veri davranışıyla uygular."""
    events = content.get("matchFacts", {}).get("events", {}).get("events", [])
    stats = stats_map(content)
    def stat(key: str, side: int) -> float:
        return as_number(stats.get(key, [0, 0])[side])

    goals = sorted((e for e in events if e.get("type") == "Goal"), key=lambda e: as_number(e.get("time")))
    sequence, home, away = [(0, 0)], 0, 0
    for goal in goals:
        home, away = (home + 1, away) if goal.get("isHome") else (home, away + 1)
        sequence.append((home, away))
    def leader(score: tuple[int, int]) -> str:
        return "home" if score[0] > score[1] else "away" if score[1] > score[0] else "draw"

    leaders = [leader(s) for s in sequence]
    changes = min(sum(a != b for a, b in zip(leaders, leaders[1:])), 3)
    late_equalizer = late_winner = False
    score_at_80 = (0, 0)
    for index, goal in enumerate(goals, start=1):
        if as_number(goal.get("time")) < 80:
            score_at_80 = sequence[index]
        else:
            before, after = leader(sequence[index - 1]), leader(sequence[index])
            late_equalizer |= after == "draw"
            late_winner |= after != "draw" and after != before
    late_bonus = 20 if late_equalizer or late_winner else 0
    late_bonus += 10 if late_equalizer and late_winner else 0
    close_at_80 = abs(score_at_80[0] - score_at_80[1]) <= 1
    tier1 = changes * 8 + late_bonus + ((5 if late_bonus else 10) if close_at_80 else 0)

    direct_red = any(e.get("type") == "Card" and e.get("card") == "Red" for e in events)
    second_yellow = any(e.get("type") == "Card" and "Second" in str(e.get("card", "")) for e in events)
    missed_penalty = any(e.get("type") == "MissedPenalty" for e in events)
    scored_penalty = any(e.get("type") == "Goal" and "penalty" in str(e.get("goalDescriptionKey", "")).lower() for e in events)
    woodwork = min(stat("shots_woodwork", 0) + stat("shots_woodwork", 1), 3)
    both_big = stat("big_chance", 0) > 0 and stat("big_chance", 1) > 0
    both_missed = stat("big_chance_missed_title", 0) > 0 and stat("big_chance_missed_title", 1) > 0
    tier2 = (12 if direct_red else 8 if second_yellow else 0) + (10 if missed_penalty else 5 if scored_penalty else 0) + woodwork * 4 + (3 if both_big else 0) + (8 if both_missed else 0)

    xg_diff = abs(stat("expected_goals", 0) - stat("expected_goals", 1))
    shot_and_save = sum(stat(k, side) for k in ("expected_goals_on_target", "keeper_saves") for side in (0, 1))
    tier3 = max(0, 10 * (1 - xg_diff / 3)) + max(0, min(8, 8 * (shot_and_save - 6) / 6))
    yellows, corners = stat("yellow_cards", 0) + stat("yellow_cards", 1), stat("corners", 0) + stat("corners", 1)
    tier4 = max(0, min(6, yellows - 6)) + max(0, min(3, (corners - 6) * .5))

    tier5 = 0.0
    if abs(home - away) >= 3:
        winner = 0 if home > away else 1
        tier5 = min(home + away, 5) * 3 + min(12, 12 * stat("expected_goals", winner) / 3)
        tier5 += 8 if stat("BallPossesion", winner) >= 60 else 0
    total = tier1 + tier2 + tier3 + tier4 + tier5
    return {"tier1": round(tier1, 2), "tier2": round(tier2, 2), "tier3": round(tier3, 2), "tier4": round(tier4, 2), "tier5": round(tier5, 2), "total": round(total, 2)}


def completed_matches(s: requests.Session) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for name, league in LEAGUES.items():
        html = fetch_html(s, f"https://www.fotmob.com/leagues/{league['id']}/matches/{league['slug']}")
        fixtures = next_data(html)["props"]["pageProps"].get("fixtures", {}).get("allMatches", [])
        for item in fixtures:
            if item.get("status", {}).get("finished"):
                matches.append({"match_id": str(item["id"]), "league": name, "home": item["home"]["name"], "away": item["away"]["name"], "score": item["status"].get("scoreStr", "-"), "date": item.get("status", {}).get("utcTime", "")[:10]})
        time.sleep(random.uniform(3.0, 6.0))
    return matches


def collect(limit: int) -> None:
    conn, s = db(), session()
    known = {row[0] for row in conn.execute("SELECT match_id FROM matches")}
    candidates = [m for m in completed_matches(s) if m["match_id"] not in known][:limit]
    print(f"{len(candidates)} yeni maç alınacak.")
    for index, match in enumerate(candidates, start=1):
        try:
            content = next_data(fetch_html(s, f"https://www.fotmob.com/match/{match['match_id']}"))["props"]["pageProps"]["content"]
            result = score_content(content)
            conn.execute("INSERT OR REPLACE INTO matches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (match["match_id"], match["date"], match["league"], match["home"], match["away"], match["score"], result["total"], json.dumps(result, ensure_ascii=False), datetime.now(timezone.utc).isoformat()))
            conn.commit()
            print(f"[{index}/{len(candidates)}] {match['home']} - {match['away']}: {result['total']}")
        except (requests.RequestException, KeyError, ValueError) as exc:
            print(f"Atlandı ({match['match_id']}): {exc}")
        if index < len(candidates):
            time.sleep(random.uniform(10.0, 18.0))


def find_highlight(match_id: str) -> dict[str, Any] | None:
    conn = db()
    cached = conn.execute("SELECT video_id, title, channel FROM highlights WHERE match_id=?", (match_id,)).fetchone()
    if cached:
        return dict(cached)
    api_key = os.environ.get("YOUTUBE_API_KEY")
    row = conn.execute("SELECT home, away FROM matches WHERE match_id=?", (match_id,)).fetchone()
    if not api_key or not row:
        return None
    query = f"{row['home']} {row['away']}"
    terms = ("özet", "highlights", "goller", "mac ozeti")
    for channel_name, channel_id in CHANNELS.items():
        response = requests.get("https://www.googleapis.com/youtube/v3/search", params={"part": "snippet", "q": query, "channelId": channel_id, "type": "video", "maxResults": 5, "key": api_key}, timeout=20)
        response.raise_for_status()
        for item in response.json().get("items", []):
            title = item["snippet"]["title"]
            normalized = title.lower().replace("ö", "o").replace("ç", "c").replace("ş", "s").replace("ı", "i")
            if any(term in normalized for term in terms):
                found = {"video_id": item["id"]["videoId"], "title": title, "channel": channel_name}
                conn.execute("INSERT OR REPLACE INTO highlights VALUES (?, ?, ?, ?, ?)", (match_id, found["video_id"], found["title"], found["channel"], datetime.now(timezone.utc).isoformat()))
                conn.commit()
                return found
    return None


app = Flask(__name__)
@app.get("/")
def home(): return send_from_directory(BASE_DIR, "index.html")
@app.get("/api/matches")
def api_matches():
    rows = db().execute("SELECT match_id AS id, date, league, home, away, score, points FROM matches ORDER BY date DESC, points DESC").fetchall()
    return jsonify([dict(row) for row in rows])
@app.get("/api/matches/<match_id>/highlight")
def api_highlight(match_id: str):
    try:
        result = find_highlight(match_id)
        return jsonify(result) if result else (jsonify({"message": "Bu maç için özet bulunamadı veya YouTube anahtarı tanımlı değil."}), 404)
    except requests.RequestException:
        return jsonify({"message": "Özet araması şu an yapılamıyor."}), 502

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("collect", "serve"))
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()
    collect(max(1, min(args.limit, 12))) if args.command == "collect" else app.run(debug=True, port=5000)
