"""
Worth90 — maç heyecan/keyif puanlama formülü (v2, anket-kalibreli).

İki ayrı formül var:
  - DRAMA formülü: sonuç belirsizliği, geri dönüş, kıl payı anlar (tavan: 100)
  - DOMİNASYON formülü: tek taraflı ama kaliteli galibiyet (tavan: 77)

Hangi formül(ler) kullanılır, gol farkına (|home_goals - away_goals|) göre:
  - fark <= 1  -> sadece DRAMA
  - fark == 2  -> (DRAMA + DOMİNASYON) / 2
  - fark >= 3  -> sadece DOMİNASYON

Ağırlıklar 600 kişilik bir anketten + çerçeveleme-önyargısı düzeltmesinden
(kart/penaltı maddelerinde katılımcıların "kendi takımım" perspektifiyle
cevap verdiği tespit edilip düzeltildi) geliyor. Detaylı gerekçe için
METHODOLOGY.md'ye bak.
"""

import json
import re
import time
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://www.fotmob.com/",
}

DRAMA_MAX = 133.25       # ham toplam, drama tarafının teorik tavanı
DOMINATION_MAX = 133.25  # ham toplam, dominasyon tarafının teorik tavanı

DRAMA_NORMALIZE_TO = 100.0
DOMINATION_NORMALIZE_TO = 77.0  # anket "Drama 0.683 / Farkli skor 0.317" oranininin
                                  # kupkok-sikistirmasindan turetildi (bkz. METHODOLOGY.md)


def fetch_match_content(match_id: str) -> dict:
    """FotMob mac sayfasindan __NEXT_DATA__ icindeki content blogunu ceker."""
    url = f"https://www.fotmob.com/match/{match_id}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
        resp.text,
    )
    if not m:
        raise ValueError(f"__NEXT_DATA__ bulunamadi: match_id={match_id}")
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


def _diminishing(count: int, increments: list) -> float:
    """1. olay tam puan, sonrakiler azalan artislarla -- increments listesindeki
    kadar olayi sayar, listenin uzunlugu dogal tavani belirler."""
    total = 0.0
    for i in range(min(count, len(increments))):
        total += increments[i]
    return total


def _min_chance_score(home_val: float, away_val: float, increments: list) -> float:
    """Iki takimin da en az X kez su istatistige sahip olmasi -- min(home,away)
    uzerinden azalan artislarla puanlanir."""
    min_val = min(home_val, away_val)
    return _diminishing(int(min_val), increments)


def _linear_cap(value: float, cap_at: float, max_points: float) -> float:
    """0'dan cap_at'e kadar lineer artan, sonrasinda sabit max_points."""
    if value >= cap_at:
        return max_points
    if value <= 0:
        return 0.0
    return max_points * (value / cap_at)


def _total_goals_domination_points(total_goals: int) -> float:
    """Toplam gol -> dominasyon puani (duzensiz merdiven, ankette 'toplam gol'
    en yuksek agirlikli dominasyon maddesi ciktigi icin ayri bir tablo).
    NOT: 2 degeri, fark=2 blend durumunda min toplam gol olasiligi icin
    extrapole edilmis bir deger (kullanicidan onay bekliyor)."""
    table = {2: 5, 3: 8, 4: 11, 5: 16, 6: 20}
    if total_goals in table:
        return table[total_goals]
    if total_goals >= 7:
        return 23
    return 0.0


def calculate_score(match_id: str) -> dict:
    """Bir FotMob match_id icin Drama/Dominasyon skorlarini ve nihai birlesik
    puani (0-100) dondurur."""
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

    # --- Skor akisi ---
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

    # Skor yon degisimi: liderlik durumu (ev/berabere/deplasman) her el degistirdiginde 1 olay
    direction_change_count = sum(
        1 for i in range(1, len(leaders)) if leaders[i] != leaders[i - 1]
    )

    # 80+ dakikada gelen "beraberlik ya da galibiyet golu": time>=80 VE lider durumu degisti
    late_leader_change_count = 0
    for i, g in enumerate(sorted_goals, start=1):
        if g["time"] >= 80 and leaders[i] != leaders[i - 1]:
            late_leader_change_count += 1

    score_at_80 = (0, 0)
    for i, g in enumerate(sorted_goals, start=1):
        if g["time"] < 80:
            score_at_80 = score_sequence[i]
    close_at_80 = abs(score_at_80[0] - score_at_80[1]) <= 1

    final_h, final_a = score_sequence[-1]
    goal_diff = abs(final_h - final_a)
    total_goals = final_h + final_a

    # Uzaktan gol sayisi (ceza sahasi disindan, her iki formulde de ortak)
    long_range_goals = sum(
        1 for g in goals if (g.get("shotmapEvent") or {}).get("isFromInsideBox") is False
    )

    # Olay bazli sayimlar (her iki formulde de ortak)
    direct_reds = sum(1 for e in events if e["type"] == "Card" and e.get("card") == "Red")
    second_yellow_reds = sum(
        1 for e in events if e["type"] == "Card" and "Second" in str(e.get("card", ""))
    )
    missed_penalties = sum(1 for e in events if e["type"] == "MissedPenalty")
    scored_penalty = any(
        e["type"] == "Goal" and "penalty" in str(e.get("goalDescriptionKey", "")).lower()
        for e in events
    )
    woodwork = int(min(gn("shots_woodwork", 0) + gn("shots_woodwork", 1), 2))
    total_yellow = gn("yellow_cards", 0) + gn("yellow_cards", 1)
    total_corners = gn("corners", 0) + gn("corners", 1)
    total_saves = gn("keeper_saves", 0) + gn("keeper_saves", 1)

    # ==================== DRAMA FORMULU (ham, tavan 133.25) ====================
    drama_raw = 0.0
    drama_raw += _diminishing(late_leader_change_count, [8, 5, 3])          # max 16
    drama_raw += 15.5 if close_at_80 else 0.0                               # max 15.5
    drama_raw += _diminishing(direction_change_count, [9, 4, 2])            # max 15
    drama_raw += _min_chance_score(gn("big_chance", 0), gn("big_chance", 1), [9, 3.5, 2])  # max 14.5
    drama_raw += _diminishing(long_range_goals, [7, 4, 2])                  # max 13
    drama_raw += _diminishing(direct_reds, [8, 3])                         # max 11
    drama_raw += _diminishing(missed_penalties, [7, 3])                    # max 10
    xg_diff = abs(gn("expected_goals", 0) - gn("expected_goals", 1))
    drama_raw += max(0.0, 8 * (1 - xg_diff / 3))                            # max 8
    drama_raw += _linear_cap(total_saves, 8, 7.5)                          # max 7.5
    drama_raw += _diminishing(second_yellow_reds, [5, 2.5])                # max 7.5
    drama_raw += _diminishing(woodwork, [3, 2])                            # max 5
    drama_raw += _min_chance_score(
        gn("big_chance_missed_title", 0), gn("big_chance_missed_title", 1), [2.5, 1.5, 0.75]
    )                                                                       # max 4.75
    drama_raw += 3.0 if scored_penalty else 0.0                            # max 3
    drama_raw += _linear_cap(total_yellow, 7, 1.5)                         # max 1.5
    drama_raw += _linear_cap(total_corners, 15, 1.0)                       # max 1
    drama_score = min(DRAMA_NORMALIZE_TO, (drama_raw / DRAMA_MAX) * DRAMA_NORMALIZE_TO)

    # ================= DOMINASYON FORMULU (ham, tavan 133.25) =================
    winner_idx = 0 if final_h > final_a else 1
    loser_idx = 1 - winner_idx

    domination_raw = 0.0
    domination_raw += _total_goals_domination_points(total_goals)          # max 23
    winner_xg = gn("expected_goals", winner_idx)
    domination_raw += min(18.0, 18 * winner_xg / 3)                        # max 18
    loser_xg = gn("expected_goals", loser_idx)
    domination_raw += 14.0 if loser_xg > 1 else 0.0                        # max 14
    winner_poss = gn("BallPossesion", winner_idx)
    domination_raw += 14.0 if winner_poss > 60 else 0.0                    # max 14
    domination_raw += _diminishing(long_range_goals, [7, 4, 2])            # max 13
    domination_raw += _diminishing(direct_reds, [8, 3])                   # max 11
    domination_raw += _diminishing(missed_penalties, [7, 3])              # max 10
    domination_raw += _linear_cap(total_saves, 8, 7.5)                    # max 7.5
    domination_raw += _diminishing(second_yellow_reds, [5, 2.5])          # max 7.5
    domination_raw += _diminishing(woodwork, [3, 2])                      # max 5
    domination_raw += _min_chance_score(
        gn("big_chance_missed_title", 0), gn("big_chance_missed_title", 1), [2.5, 1.5, 0.75]
    )                                                                       # max 4.75
    domination_raw += 3.0 if scored_penalty else 0.0                       # max 3
    domination_raw += _linear_cap(total_yellow, 7, 1.5)                    # max 1.5
    domination_raw += _linear_cap(total_corners, 15, 1.0)                  # max 1
    domination_score = min(
        DOMINATION_NORMALIZE_TO, (domination_raw / DOMINATION_MAX) * DOMINATION_NORMALIZE_TO
    )

    # ==================== BIRLESTIRME (gol farkina gore) ====================
    if goal_diff <= 1:
        final_score = drama_score
    elif goal_diff == 2:
        final_score = (drama_score + domination_score) / 2
    else:
        final_score = domination_score

    return {
        "match_id": match_id,
        "goal_diff": goal_diff,
        "drama_raw": round(drama_raw, 2),
        "drama_score": round(drama_score, 2),
        "domination_raw": round(domination_raw, 2),
        "domination_score": round(domination_score, 2),
        "score": round(final_score, 1),
    }


def badge_for(score: float) -> dict:
    """0-100 normalize skora gore Turkce badge dondurur.
    NOT: dominasyon formulunun tavani 77 oldugu icin, saf bir 3+ farkli
    galibiyet (fark>=3) hicbir zaman 'Tarihe Gecer' (84+) bandina ulasamaz --
    bu formulun bilincli bir tasarim sonucu (bkz. METHODOLOGY.md)."""
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
    """calculate_score'u hata toleransli calistirir, art arda isteklerde nazik davranir."""
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
