"""
Worth90 — maç heyecan/keyif puanlama formülü.
FotMob'un __NEXT_DATA__ JSON'undan çıkan match_facts ve stats üzerinden çalışır.
"""

import json
import re
import time
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://www.fotmob.com/",
}

NORMALIZE_DIVISOR = 130  # ham puanı 0-100'e çekmek için bölüm


def fetch_match_content(match_id: str) -> dict:
    """FotMob maç sayfasından __NEXT_DATA__ içindeki content bloğunu çeker."""
    url = f"https://www.fotmob.com/match/{match_id}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
        resp.text,
    )
    if not m:
        raise ValueError(f"__NEXT_DATA__ bulunamadı: match_id={match_id}")
    next_data = json.loads(m.group(1))
    return next_data["props"]["pageProps"]["content"]


def _get_num(stats: dict, key: str, idx: int) -> float:
    try:
        v = stats.get(key, [0, 0])[idx]
        if isinstance(v, str):
            v = float(v.split()[0].replace("(", "").replace("%", ""))
        return float(v)
    except (TypeError, ValueError, IndexError):
        return 0.0


def _leader(hs: int, aws: int) -> str:
    if hs > aws:
        return "home"
    if aws > hs:
        return "away"
    return "draw"


def calculate_score(match_id: str) -> dict:
    """Bir FotMob match_id için Tier 1-5 ham puanını ve 0-100 normalize skoru döndürür."""
    content = fetch_match_content(match_id)

    match_facts = content["matchFacts"]
    events = match_facts["events"]["events"]
    stat_groups = content["stats"]["Periods"]["All"]["stats"]

    stats = {}
    for group in stat_groups:
        for item in group.get("stats", []):
            vals = item.get("stats")
            if vals and len(vals) == 2 and vals[0] is not None:
                stats[item["key"]] = vals

    def gn(key, idx):
        return _get_num(stats, key, idx)

    # --- Skor akışı ---
    goals = [e for e in events if e["type"] == "Goal"]
    sorted_goals = sorted(goals, key=lambda x: x["time"])
    score_sequence = [(0, 0)]
    h, a = 0, 0
    for g in sorted_goals:
        if g.get("isHome"):
            h += 1
        else:
            a += 1
        score_sequence.append((h, a))

    leaders = [_leader(hs, aws) for hs, aws in score_sequence]
    direction_changes = min(
        sum(1 for i in range(1, len(leaders)) if leaders[i] != leaders[i - 1]), 3
    )

    late_equalizer = False
    late_winner = False
    for i, g in enumerate(sorted_goals, start=1):
        if g["time"] >= 80:
            before = _leader(*score_sequence[i - 1])
            after = _leader(*score_sequence[i])
            if after == "draw":
                late_equalizer = True
            elif after != before:
                late_winner = True

    score_at_80 = (0, 0)
    for i, g in enumerate(sorted_goals, start=1):
        if g["time"] < 80:
            score_at_80 = score_sequence[i]
    close_at_80 = abs(score_at_80[0] - score_at_80[1]) <= 1

    final_h, final_a = score_sequence[-1]
    goal_diff = abs(final_h - final_a)

    # --- Tier 1: Sonuç belirsizliği ---
    tier1 = direction_changes * 8
    late_bonus = 0
    if late_equalizer or late_winner:
        late_bonus += 20
        if late_equalizer and late_winner:
            late_bonus += 10
    tier1 += late_bonus
    if close_at_80:
        tier1 += 5 if late_bonus > 0 else 10

    # --- Tier 2: Kıl payı anlar ---
    tier2 = 0
    red_direct = any(e["type"] == "Card" and e.get("card") == "Red" for e in events)
    red_second_yellow = any(
        e["type"] == "Card" and "Second" in str(e.get("card", "")) for e in events
    )
    tier2 += 12 if red_direct else (8 if red_second_yellow else 0)

    missed_pen = any(e["type"] == "MissedPenalty" for e in events)
    scored_pen = any(
        e["type"] == "Goal" and "penalty" in str(e.get("goalDescriptionKey", "")).lower()
        for e in events
    )
    tier2 += 10 if missed_pen else (5 if scored_pen else 0)

    woodwork = min(gn("shots_woodwork", 0) + gn("shots_woodwork", 1), 3)
    tier2 += woodwork * 4

    if gn("big_chance", 0) > 0 and gn("big_chance", 1) > 0:
        tier2 += 3
    if gn("big_chance_missed_title", 0) > 0 and gn("big_chance_missed_title", 1) > 0:
        tier2 += 8

    # --- Tier 3: Kalite/çekişme (xG farkı sadece fark<3 iken) ---
    if goal_diff < 3:
        xg_diff = abs(gn("expected_goals", 0) - gn("expected_goals", 1))
        tier3 = max(0, 10 * (1 - xg_diff / 3))
    else:
        tier3 = 0

    xgot_saves = (
        gn("expected_goals_on_target", 0)
        + gn("expected_goals_on_target", 1)
        + gn("keeper_saves", 0)
        + gn("keeper_saves", 1)
    )
    if xgot_saves <= 6:
        tier3_b = 0
    elif xgot_saves >= 12:
        tier3_b = 8
    else:
        tier3_b = 8 * (xgot_saves - 6) / 6
    tier3 += tier3_b

    # --- Tier 4: Tansiyon ---
    total_yellow = gn("yellow_cards", 0) + gn("yellow_cards", 1)
    tier4 = 0 if total_yellow <= 6 else (6 if total_yellow >= 12 else (total_yellow - 6) * 1)
    total_corners = gn("corners", 0) + gn("corners", 1)
    tier4 += 0 if total_corners <= 6 else (3 if total_corners >= 12 else (total_corners - 6) * 0.5)

    # --- Tier 5: Dominasyon Düzeltmesi (sadece |fark| >= 3) ---
    tier5 = 0
    if goal_diff >= 3:
        w_idx = 0 if final_h > final_a else 1
        l_idx = 1 - w_idx

        total_goals = final_h + final_a
        tier5 += min(total_goals, 5) * 2  # max 10

        winner_xg = gn("expected_goals", w_idx)
        tier5 += min(10, 10 * winner_xg / 3)  # max 10

        if gn("BallPossesion", w_idx) >= 60:
            tier5 += 5  # max 5

        if gn("expected_goals", l_idx) > 1:
            tier5 += 5  # max 5

        long_range_goals = 0
        for g in goals:
            smap = g.get("shotmapEvent") or {}
            if smap.get("isFromInsideBox") is False:
                long_range_goals += 1
        tier5 += min(long_range_goals, 2) * 3  # max 6

    raw_total = tier1 + tier2 + tier3 + tier4 + tier5
    normalized = min(100, (raw_total / NORMALIZE_DIVISOR) * 100)

    return {
        "match_id": match_id,
        "tier1": round(tier1, 2),
        "tier2": round(tier2, 2),
        "tier3": round(tier3, 2),
        "tier4": round(tier4, 2),
        "tier5": round(tier5, 2),
        "raw_total": round(raw_total, 2),
        "score": round(normalized, 1),
    }


def badge_for(score: float) -> dict:
    """0-100 normalize skora göre Türkçe badge döndürür."""
    if score < 30:
        return {"tr": "Uyutabilir", "boxed": False}
    if score < 45:
        return {"tr": "İdare Eder", "boxed": False}
    if score < 61:
        return {"tr": "İyi Maç", "boxed": False}
    if score < 76:
        return {"tr": "Tatmin Edici", "boxed": True}
    if score < 84:
        return {"tr": "Futbol Ziyafeti", "boxed": True}
    return {"tr": "Tarihe Geçer", "boxed": True}


def calculate_score_safe(match_id: str, retries: int = 2, delay: float = 2.0) -> dict | None:
    """calculate_score'u hata toleranslı çalıştırır, art arda isteklerde nazik davranır."""
    for attempt in range(retries + 1):
        try:
            result = calculate_score(match_id)
            time.sleep(delay)
            return result
        except Exception as exc:  # noqa: BLE001
            if attempt == retries:
                print(f"[HATA] match_id={match_id}: {exc}")
                return None
            time.sleep(delay * 2)
    return None
