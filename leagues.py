"""
Worth90 — takip edilecek ligler ve FotMob leagueId'leri.

Doğrulanmış ID'ler (bu konuşma sırasında FotMob'dan teyit edildi):
    Premier Lig = 47, La Liga = 87, Serie A = 55, Süper Lig = 71

Henüz doğrulanmamış 5 lig için ID'yi kendin bulup aşağıya yapıştırman gerekiyor:
    1. https://www.fotmob.com adresine git
    2. İlgili ligi aç (örn. Bundesliga)
    3. Adres çubuğundaki URL'e bak: https://www.fotmob.com/leagues/<ID>/overview/...
    4. <ID> kısmını aşağıya yaz

None olan değerler scan.py tarafından atlanır (hata vermez, sadece o lig taranmaz).
"""

LEAGUE_IDS = {
    "Premier Lig": 47,
    "La Liga": 87,
    "Serie A": 55,
    "Süper Lig": 71,
    "Ligue 1": 53,
    "Bundesliga": 54,
    "Şampiyonlar Ligi": 42,
    "Avrupa Ligi": 73,
    "Konferans Ligi": 10216,
}
