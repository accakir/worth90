"""
Worth90 — ana tarama scripti.

Yapılanlar:
1. leagues.py'deki her lig için bitmiş maçları çeker
2. data/matches.json'da zaten olmayan (yeni biten) maçları bulur
3. Her yeni maç için score.py ile puan hesaplar
4. Sonucu data/matches.json'a ekleyip kaydeder

GitHub Actions'tan cron ile periyodik çalıştırılmak üzere tasarlandı.
İstekler arasına kasıtlı bekleme (score.py -> calculate_score_safe) eklidir,
bu yüzden büyük hacimlerde YAVAŞ çalışır -- bu bilinçli bir tercih (ban riskini azaltmak için).
"""

import json
import os

from leagues import LEAGUE_IDS
from fixtures import finished_matches_since
from score import calculate_score_safe, badge_for
from youtube import build_youtube_client, find_highlight_for_match

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "matches.json")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")


def load_existing() -> dict:
    if not os.path.exists(DATA_PATH):
        return {}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save(data: dict) -> None:
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _highlight_missing(entry: dict) -> bool:
    """Bir maç için özet henüz bulunamamışsa True döner (tekrar aranmalı)."""
    h = entry.get("highlight")
    if h is None:
        return True
    return "URL" not in h  # sadece bulunan videoların URL'si var


def main() -> None:
    existing = load_existing()
    existing_ids = set(existing.keys())

    youtube = build_youtube_client(YOUTUBE_API_KEY) if YOUTUBE_API_KEY else None
    if youtube is None:
        print("[UYARI] YOUTUBE_API_KEY tanımlı değil, özet araması atlanacak.")

    total_new = 0
    total_highlights_found = 0

    for league_name, league_id in LEAGUE_IDS.items():
        if league_id is None:
            print(f"[ATLA] {league_name}: leagues.py'de ID tanımlı değil")
            continue

        print(f"[TARA] {league_name} (id={league_id})")
        try:
            new_matches = finished_matches_since(league_id, existing_ids)
        except Exception as exc:  # noqa: BLE001
            print(f"[HATA] {league_name} fikstür çekilemedi: {exc}")
            continue

        print(f"  -> {len(new_matches)} yeni biten maç bulundu")

        for m in new_matches:
            match_id = m["id"]
            label = f"{m['home']['name']} {m['status'].get('scoreStr', '')} {m['away']['name']}"
            print(f"  [PUANLA] {label}")

            result = calculate_score_safe(match_id)
            if result is None:
                continue

            badge = badge_for(result["score"])

            existing[match_id] = {
                "match_id": match_id,
                "league": league_name,
                "date": m["status"]["utcTime"],
                "home": m["home"]["name"],
                "away": m["away"]["name"],
                "score_str": m["status"].get("scoreStr", ""),
                "raw_total": result["raw_total"],
                "score": result["score"],
                "badge": badge["tr"],
                "boxed": badge["boxed"],
                "tiers": {
                    "tier1": result["tier1"],
                    "tier2": result["tier2"],
                    "tier3": result["tier3"],
                    "tier4": result["tier4"],
                    "tier5": result["tier5"],
                },
                "highlight": None,
            }
            total_new += 1
            existing_ids.add(match_id)

    # --- Özet araması: yeni + daha önce bulunamamış maçlar için ---
    if youtube is not None:
        pending = [e for e in existing.values() if _highlight_missing(e)]
        print(f"\n[ÖZET ARA] {len(pending)} maç için özet aranacak")

        for entry in pending:
            result = find_highlight_for_match(
                youtube, entry["league"], entry["home"], entry["away"]
            )
            entry["highlight"] = result
            if "URL" in result:
                total_highlights_found += 1
                print(f"  ✅ {entry['home']} - {entry['away']}: bulundu")
            else:
                print(f"  ❌ {entry['home']} - {entry['away']}: henüz yok")

    save(existing)
    print(
        f"\nToplam {total_new} yeni maç puanlandı, "
        f"{total_highlights_found} yeni özet bulundu. data/matches.json güncellendi."
    )


if __name__ == "__main__":
    main()
