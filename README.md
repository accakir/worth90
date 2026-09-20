# Worth90

Futbol maçları için istatistiklere dayalı, heyecan & keyif puanı hesaplamaya
çalışan deneysel bir çalışma. FotMob'un açık (dökümante edilmemiş) JSON
uçlarından beslenir; kart, penaltı, direk, xG/xGOT, possession gibi verilerle
Tier 1–5 ağırlıklı bir formülle her maça 0–100 arası bir puan verir.

## YouTube özet araması

`data/matches.json`'daki her maça, yayıncıların **resmi sezon özetleri
playlist'i** taranarak eşleşen özet videosu ekleniyor (kota-dostu
`playlistItems.list` kullanılıyor, `search.list` değil). Playlist'ler zaten
sadece o ligin özetlerine ayrılmış olduğu için hem daha isabetli hem çok daha
az kota harcıyor -- tüm kanal upload geçmişini taramaya gerek yok.

Lig -> playlist eşleşmeleri (`youtube.py` içindeki `LEAGUE_PLAYLISTS`):

| Lig | Yayıncı | Playlist |
|---|---|---|
| Premier Lig | beIN Sports Türkiye | PLC-ntSjW5uvU |
| Ligue 1 | beIN Sports Türkiye | PLN2uIXbY_9ZA |
| Süper Lig | beIN Sports Türkiye | PLSBL5_PlWv-4 |
| Bundesliga | S Sport | PLVwTHtGF6Uwc |
| Serie A | S Sport | PLWi99Pdx7Qjo |
| La Liga | S Sport | PLc1u-zFXPFvA |
| Şampiyonlar Ligi | TRT Spor | PLQs_w-FaXbl0 |
| Avrupa Ligi | TRT Spor | PLOWxTUd8YsIs |
| Konferans Ligi | TRT Spor | PLFwIjFJS4so0 |

**Önemli:** Eşleştirme her zaman **iki takım adının da** aynı video
başlığında geçmesini şart koşuyor -- playlist'e geçmek tek-takım-adıyla
arama yapmayı güvenli hale getirmiyor (`Real` → Madrid/Betis/Valladolid,
`Deportivo` → A Coruña/Alavés gibi çakışma riskleri hâlâ geçerli).

Takım adı eşleştirmesi FotMob'un resmi adını kullanıyor; Türkçe kanalların
farklı isimlendirdiği takımlar (`Bayern Münih`, `Marsilya`, `PSG` vb.)
`youtube.py`'deki `TEAM_ALIASES` sözlüğünde tanımlı -- yeni bir uyuşmazlık
fark edersen buraya ekleyebilirsin.

### Kurulum

1. GitHub repo → Settings → Secrets and variables → Actions → "New repository secret"
2. İsim: `YOUTUBE_API_KEY`, değer: kendi YouTube Data API v3 anahtarın
3. Lokal çalıştırmada ortam değişkeni olarak ver:
   ```bash
   export YOUTUBE_API_KEY="senin-anahtarin"
   python scan.py
   ```

`YOUTUBE_API_KEY` tanımlı değilse `scan.py` özet aramasını atlar, sadece
puanlama çalışır (hata vermez).

## Arayüz (GitHub Pages)

`index.html`, `data/matches.json`'u aynı repodan (`fetch("data/matches.json")`)
çalışma zamanında çeker — GitHub Pages'te aynı origin'den servis edildiği için
canlı çalışır, ayrı bir hosting veya build adımına gerek yok.

### Kurulum

1. Repo → Settings → Pages
2. "Build and deployment" → Source: **Deploy from a branch**
3. Branch: `main`, klasör: `/ (root)`
4. Kaydet, birkaç dakika sonra `https://<kullanici-adi>.github.io/worth90/` üzerinden erişilebilir

`scan.py` her çalıştığında `data/matches.json`'u güncelleyip commit'liyor;
Pages de bu commit'i otomatik yeniden yayınlıyor, ekstra bir işlem gerekmez.

### Davranış notları

- Sayfa açılışında hiçbir video aranmaz/yüklenmez.
- Bir maç satırına tıklanınca sadece o satır akordeon gibi açılır ve
  `data/matches.json`'daki `highlight.URL` alanına bakar (canlı arama yapmaz,
  zaten `scan.py`'nin önceden bulduğu sonucu gösterir).
- `highlight` boşsa "özet henüz bulunamadı" mesajı gösterilir.
- Aynı anda tek satır açık kalır; başka bir satıra tıklanınca öncekinin
  video embed'i kaldırılır (DOM'dan tamamen siliniyor, arka planda yüklü kalmıyor).

## Kurulum

```bash
pip install -r requirements.txt
```

## Lig ID'lerini tamamla

`leagues.py` içinde 4 lig zaten doğrulanmış (Premier Lig, La Liga, Serie A,
Süper Lig). Kalan 5 lig için (Ligue 1, Bundesliga, Şampiyonlar Ligi, Avrupa
Ligi, Konferans Ligi):

1. fotmob.com'da ilgili ligi aç
2. URL'deki `/leagues/<ID>/...` kısmındaki sayıyı kopyala
3. `leagues.py`'deki `None` değerini bu sayı ile değiştir

## Manuel çalıştırma

```bash
python scan.py
```

`data/matches.json` dosyasını günceller — yeni biten maçları bulup puanlar,
zaten puanlanmış maçlara dokunmaz.

## Otomatik çalıştırma (GitHub Actions)

`.github/workflows/scan.yml` her 3 saatte bir `scan.py`'yi çalıştırıp
`data/matches.json`'u otomatik commit'ler. Sıklığı değiştirmek için
workflow dosyasındaki `cron` satırını düzenle.

Repoyu GitHub'a push ettikten sonra Actions sekmesinde "Run workflow" ile
elle de tetikleyebilirsin.

## Dosya yapısı

```
index.html     -> Arayüz (GitHub Pages) - data/matches.json'u fetch ile çeker
score.py       -> Puanlama formülü (Tier 1-5) + FotMob'dan maç verisi çekme
leagues.py     -> Takip edilen ligler ve FotMob leagueId'leri
fixtures.py    -> Bir ligin fikstürünü/bitmiş maçlarını çekme
youtube.py     -> Yayıncı YouTube kanallarının resmi özet playlist'lerinden maç özeti bulma
scan.py        -> Orkestratör: ligleri gez, yeni maçları puanla, özet ara, JSON'a yaz
reset_highlights.py -> Tüm highlight alanlarını sıfırlayıp yeniden aratmak için (tek seferlik)
data/matches.json -> Puanlanmış tüm maçların biriktiği veri dosyası
.github/workflows/scan.yml -> Cron job tanımı
METHODOLOGY.md -> Puanlama formülünün her bileşeninin gerekçesi
```

## Notlar

- FotMob'un kullandığımız uçları resmi/dökümante bir API değil; format
  değişebilir. `score.py` ve `fixtures.py` içindeki `__NEXT_DATA__` parse
  mantığı bozulursa önce FotMob'un sayfa yapısını tekrar kontrol et.
- `calculate_score_safe`, art arda isteklerde 2 saniyelik bekleme uygular
  (rate-limit/ban riskini azaltmak için). Büyük hacimde tarama yavaş
  olacaktır, bu bilinçli bir tercih.
- Formülün her bileşeninin **neden** o ağırlığı/eşiği aldığına dair
  ayrıntılı gerekçe için **[METHODOLOGY.md](./METHODOLOGY.md)**'ye bak.
