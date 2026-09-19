"""Worth90 — yayıncı YouTube kanallarının resmi özet playlist'lerinden maç özeti bulma."""

import unicodedata
from googleapiclient.discovery import build

# Her ligin, ilgili yayıncının resmi "sezon özetleri" playlist'i.
# Playlist'ler zaten sadece o ligin özetlerine ayrılmış olduğu için hem daha
# isabetli hem çok daha az kota harcıyor (tüm kanal geçmişini taramaya gerek yok).
LEAGUE_PLAYLISTS: dict[str, str] = {
    "Bundesliga": "PLVwTHtGF6Uwc",
    "Serie A": "PLWi99Pdx7Qjo",
    "La Liga": "PLc1u-zFXPFvA",
    "Ligue 1": "PLN2uIXbY_9ZA",
    "Premier Lig": "PLC-ntSjW5uvU",
    "Süper Lig": "PLSBL5_PlWv-4",
    "Avrupa Ligi": "PLOWxTUd8YsIs",
    "Şampiyonlar Ligi": "PLQs_w-FaXbl0",
    "Konferans Ligi": "PLFwIjFJS4so0",
}

# Sadece gösterim/bilgi amaçlı: hangi lig hangi yayıncıya ait
LEAGUE_CHANNEL_MAP: dict[str, str] = {
    "Bundesliga": "S_SPORT",
    "Serie A": "S_SPORT",
    "La Liga": "S_SPORT",
    "Ligue 1": "BEIN_SPORTS_TR",
    "Premier Lig": "BEIN_SPORTS_TR",
    "Süper Lig": "BEIN_SPORTS_TR",
    "Avrupa Ligi": "TRT_SPOR",
    "Şampiyonlar Ligi": "TRT_SPOR",
    "Konferans Ligi": "TRT_SPOR",
}

HIGHLIGHT_KEYWORDS = ["ozet", "highlights", "goller", "mac ozeti"]
JUNK_KEYWORDS = [
    "canli", "mac sonu", "devre arasi", "trio",
    "aktuel futbol", "iptal edilen", "kafa goli", "aciklamalari",
    "shorts", "short", "basketbol", "basket", "voleybol",
    "roportaj", "soylesi", "aciklama", "flas",
]


# FotMob'daki resmi takım adı -> Türkçe yayıncı kanallarının kullandığı
# farklı ad(lar). Bu sözlük sadece kelime-bazlı eşleşmenin YAKALAYAMADIĞI
# gerçek farkları içeriyor (çoğu takım zaten ortak kelime sayesinde
# otomatik eşleşiyor, örn. "Athletic Club" ~ "Athletic Bilbao").
# NOT: İki takım adının da eşleşmesi şartı korunuyor -- playlist'e geçmek
# tek-takım-adıyla arama yapmayı GÜVENLİ hale getirmiyor (Real Madrid/Betis/
# Valladolid, Deportivo A Coruña/Alavés gibi çakışma riskleri hâlâ geçerli).
TEAM_ALIASES: dict[str, list[str]] = {
    "Bayern München": ["Bayern Münih"],
    "Hamburger SV": ["Hamburg"],
    "Marseille": ["Marsilya"],
    "Paris Saint-Germain": ["PSG"],
    "Bodø/Glimt": ["Bodo Glimt"],
    "Union St.Gilloise": ["Gilloise", "U.S Gilloise"],
    "Amed Sportif": ["Amed SF"],
    "Olympiacos": ["Olympiakos"],
}


def _clean_text(text: str) -> str:
    # Önce Türkçe'ye özgü karakterleri elle çeviriyoruz çünkü unicodedata
    # bunları bazen yanlış / eksik decompose ediyor (ı, ğ, ş gibi).
    text = (
        text.lower()
        .replace("ı", "i")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ö", "o")
        .replace("ç", "c")
    )
    # Sonra genel aksan temizliği: é->e, ü(diğer diller)->u, ñ->n, vs.
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    # NFKD'nin çözemediği özel harfler (İskandinav vb.)
    text = (
        text.replace("ø", "o")
        .replace("æ", "ae")
        .replace("þ", "th")
        .replace("ß", "ss")
        .replace("đ", "d")
    )
    return text


def _match_team_name(team_input: str, title_clean: str) -> bool:
    candidates = [team_input] + TEAM_ALIASES.get(team_input, [])
    for candidate in candidates:
        words = [_clean_text(w) for w in candidate.split() if len(w) > 2]
        if any(word in title_clean for word in words):
            return True
    return False


def get_playlist_for_league(league_name: str) -> str | None:
    return LEAGUE_PLAYLISTS.get(league_name)


def search_match_highlight_in_playlist(youtube, playlist_id: str, channel_label: str, team_a: str, team_b: str) -> dict:
    items = []
    next_page_token = None

    # Playlist'ler küçük (birkaç - birkaç düzine video), genelde 1-2 sayfa yeter
    for _ in range(3):
        request = youtube.playlistItems().list(
            playlistId=playlist_id,
            part="snippet",
            maxResults=50,
            pageToken=next_page_token,
        )
        response = request.execute()
        items.extend(response.get("items", []))
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    best_match = None

    for item in items:
        title = item["snippet"]["title"]
        title_clean = _clean_text(title)

        has_team_a = _match_team_name(team_a, title_clean)
        has_team_b = _match_team_name(team_b, title_clean)

        if has_team_a and has_team_b:
            has_kw = any(kw in title_clean for kw in HIGHLIGHT_KEYWORDS)
            is_junk = any(junk in title_clean for junk in JUNK_KEYWORDS)

            if is_junk:
                continue

            video_data = {
                "Durum": "✅ KESİN MAÇ ÖZETİ",
                "Kanal": channel_label,
                "Başlık": title,
                "URL": f"https://www.youtube.com/watch?v={item['snippet']['resourceId']['videoId']}",
                "Tarih": item["snippet"]["publishedAt"],
            }

            if has_kw:
                return video_data

            if not best_match:
                video_data["Durum"] = "⚡ MUHTEMEL EŞLEŞME"
                best_match = video_data

    if best_match:
        return best_match

    return {"Durum": f"❌ '{team_a} - {team_b}' playlist'te bulunamadı."}


def find_highlight_for_match(youtube, league_name: str, home: str, away: str) -> dict | None:
    """İlgili ligin resmi özet playlist'inde arama yapar."""
    playlist_id = get_playlist_for_league(league_name)
    if playlist_id is None:
        return {"Durum": f"❌ {league_name} için playlist tanımlı değil."}

    channel_label = LEAGUE_CHANNEL_MAP.get(league_name, "?")
    return search_match_highlight_in_playlist(youtube, playlist_id, channel_label, home, away)


def build_youtube_client(api_key: str):
    return build("youtube", "v3", developerKey=api_key)
