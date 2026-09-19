"""
Worth90 — data/matches.json'daki TÜM highlight alanlarını sıfırlar.
Bir sonraki `python scan.py` çalıştırmasında hepsi youtube.py'nin
güncellenmiş (daha sıkı) eşleştirme mantığıyla yeniden aranır.

Kullanım:
    python reset_highlights.py
"""

import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "matches.json")


def main() -> None:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    for entry in data.values():
        entry["highlight"] = None

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"{len(data)} maçın highlight alanı sıfırlandı. "
          f"Bir sonraki scan.py çalıştırmasında yeniden aranacaklar.")


if __name__ == "__main__":
    main()
