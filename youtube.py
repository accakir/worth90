"""Worth90 — yayıncı YouTube kanallarından maç özeti bulma."""

import datetime as dt
from googleapiclient.discovery import build

BROADCASTER_CHANNELS = {
    "BEIN_SPORTS_TR": "UCPe9vNjHF1kEExT5kHwc7aw",
    "S_SPORT": "UCpdSUUHlxMjO0c5824FGcsA",
    "TRT_SPOR": "UCfYNqluOf8EbQkL44otydMw",
}

# Hangi lig hangi kanalda özetleniyor
LEAGUE_CHANNEL_MAP = {
    "Premier Lig": "BEIN_SPORTS_TR",
    "Ligue 1": "BEIN_SPORTS_TR",
    "Süper Lig": "BEIN_SPORTS_TR",  # özetler 3-5 gün gecikmeli yükleniyor
    "Bundesliga": "S_SPORT",
    "Serie A": "S_SPORT",
    "La Liga": "S_SPORT",
    "Şampiyonlar Ligi": "TRT_SPOR",
    "Avrupa Ligi": "TRT_SPOR",
    "Konferans Ligi": "TRT_SPOR",
}

# Süper Lig için, maç bitiminden bu kadar gün geçmeden arama yapılmaz (kota israfı olmasın diye)
SUPER_LIG_DELAY_DAYS = 5

HIGHLIGHT_KEYWORDS = ["ozet", "highlights", "goller", "mac ozeti"]
JUNK_KEYWORDS = [
    "canli", "mac sonu", "devre arasi", "trio",
    "aktuel futbol", "iptal edilen", "kafa goli", "aciklamalari",
]


def _clean_text(text: str) -> str:
    return (
        text.lower()
        .replace("ı", "i")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ö", "o")
        .replace("ç", "c")
    )


def _match_team_name(team_input: str, title_clean: str) -> bool:
    words = [_clean_text(w) for w in team_input.split() if len(w) > 2]
    return any(word in title_clean for word in words)


def get_channel_for_league(league_name: str) -> str | None:
    return LEAGUE_CHANNEL_MAP.get(league_name)


def is_ready_for_search(league_name: str, match_date_iso: str) -> bool:
    """Süper Lig için gecikme süresini kontrol eder, diğer liglerde her zaman True döner."""
    if league_name != "Süper Lig":
        return True
    try:
        match_date = dt.datetime.fromisoformat(match_date_iso.replace("Z", "+00:00"))
    except ValueError:
        return True
    now = dt.datetime.now(dt.timezone.utc)
    return (now - match_date).days >= SUPER_LIG_DELAY_DAYS


def search_match_highlight(youtube, channel_key: str, team_a: str, team_b: str) -> dict:
    channel_id = BROADCASTER_CHANNELS.get(channel_key)
    if not channel_id:
        return {"Durum": "❌ Kanal anahtarı geçersiz."}

    uploads_playlist_id = "UU" + channel_id[2:]
    items = []
    next_page_token = None

    # İlk 100 videoyu tara (2 birim kota)
    for _ in range(2):
        request = youtube.playlistItems().list(
            playlistId=uploads_playlist_id,
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
    backup_match = None

    for item in items:
        title = item["snippet"]["title"]
        title_clean = _clean_text(title)

        has_team_a = _match_team_name(team_a, title_clean)
        has_team_b = _match_team_name(team_b, title_clean)

        if has_team_a and has_team_b:
            has_kw = any(kw in title_clean for kw in HIGHLIGHT_KEYWORDS)
            is_junk = any(junk in title_clean for junk in JUNK_KEYWORDS)

            video_data = {
                "Durum": "✅ KESİN MAÇ ÖZETİ",
                "Kanal": channel_key,
                "Başlık": title,
                "URL": f"https://www.youtube.com/watch?v={item['snippet']['resourceId']['videoId']}",
                "Tarih": item["snippet"]["publishedAt"],
            }

            if has_kw and not is_junk:
                return video_data

            if not is_junk and not best_match:
                best_match = video_data

            if not backup_match:
                backup_match = video_data

    if best_match:
        return best_match
    if backup_match:
        backup_match["Durum"] = "⚡ YEDEK İÇERİK"
        return backup_match

    return {"Durum": f"❌ {channel_key} kanalında '{team_a} - {team_b}' bulunamadı."}


def find_highlight_for_match(youtube, league_name: str, home: str, away: str, match_date_iso: str) -> dict | None:
    """Lig -> kanal eşleşmesi + Süper Lig gecikme kontrolünü yapıp arama sonucunu döndürür.
    None dönerse: henüz arama zamanı gelmedi (bekle, tekrar deneme)."""
    channel_key = get_channel_for_league(league_name)
    if channel_key is None:
        return {"Durum": f"❌ {league_name} için kanal eşleşmesi tanımlı değil."}

    if not is_ready_for_search(league_name, match_date_iso):
        return None  # henüz erken, scan.py bu maçı bu turda atlayacak

    return search_match_highlight(youtube, channel_key, home, away)


def build_youtube_client(api_key: str):
    return build("youtube", "v3", developerKey=api_key)
