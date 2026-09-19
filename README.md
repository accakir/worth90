# Worth90

Futbol maçları için istatistiklere dayalı, heyecan & keyif puanı hesaplamaya
çalışan deneysel bir çalışma. FotMob'un açık (dökümante edilmemiş) JSON
uçlarından beslenir; kart, penaltı, direk, xG/xGOT, possession gibi verilerle
Tier 1–5 ağırlıklı bir formülle her maça 0–100 arası bir puan verir.

## YouTube özet araması

`data/matches.json`'daki her maça, yayıncı kanalların uploads playlist'i
taranarak eşleşen özet videosu ekleniyor (kota-dostu `playlistItems.list`
kullanılıyor, `search.list` değil).

Kanal eşleşmeleri (`youtube.py` içinde):

| Lig | Kanal |
|---|---|
| Premier Lig, Ligue 1 | beIN Sports Türkiye |
| Bundesliga, Serie A, La Liga | S Sport |
| Şampiyonlar Ligi, Avrupa Ligi, Konferans Ligi | TRT Spor |
| Süper Lig | beIN Sports Türkiye (3-5 gün gecikmeli, `SUPER_LIG_DELAY_DAYS`) |

Süper Lig maçları için `scan.py`, maç bitiminden `SUPER_LIG_DELAY_DAYS` gün
geçmeden arama yapmaz (kota israfı olmasın diye); sonraki taramalarda
otomatik tekrar dener.

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
youtube.py     -> Yayıncı YouTube kanallarından maç özeti bulma
scan.py        -> Orkestratör: ligleri gez, yeni maçları puanla, özet ara, JSON'a yaz
data/matches.json -> Puanlanmış tüm maçların biriktiği veri dosyası
.github/workflows/scan.yml -> Cron job tanımı
```

## Notlar

- FotMob'un kullandığımız uçları resmi/dökümante bir API değil; format
  değişebilir. `score.py` ve `fixtures.py` içindeki `__NEXT_DATA__` parse
  mantığı bozulursa önce FotMob'un sayfa yapısını tekrar kontrol et.
- `calculate_score_safe`, art arda isteklerde 2 saniyelik bekleme uygular
  (rate-limit/ban riskini azaltmak için). Büyük hacimde tarama yavaş
  olacaktır, bu bilinçli bir tercih.
- Formülün tier ağırlıkları ve normalize bölümü (130) hakkındaki
  gerekçeler için sohbet geçmişine bakılabilir; kısaca: Tier 1 sonuç
  belirsizliğini, Tier 2 kıl payı anları, Tier 3 kalite/çekişmeyi, Tier 4
  tansiyonu, Tier 5 ise 3+ farklı galibiyetlerde "dominasyon kalitesini"
  ölçer ve sadece o durumda aktif olur.
