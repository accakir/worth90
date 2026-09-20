# Worth90 — Puanlama Metodolojisi

Bu doküman, `score.py`'deki formülün **hangi istatistiği neden aldığını** ve
**ağırlıkları neye göre belirlediğimizi** anlatıyor. Kod satır satır neyi
hesapladığını gösterir, ama neden o eşiği/o ağırlığı seçtiğimizi göstermez —
bu doküman o boşluğu dolduruyor.

## Temel fikir: iki farklı "izlenmeye değer" türü var

Bir maç iki ayrı sebeple keyifli olabilir, ve bu ikisi bazen **ters yönde**
çalışır:

- **Drama / belirsizlik**: Sonucun son ana kadar askıda kalması, geri
  dönüşler, kıl payı kaçan fırsatlar. 2-2 biten, üç kez el değiştiren bir
  maç bunun örneği.
- **Gösteri / dominasyon kalitesi**: Tek taraflı ama yüksek kaliteli,
  akıcı, çok gollü bir galibiyet. 5-0 biten ama sıkıcı olmayan bir maç
  bunun örneği.

Formül bu ikisini **tek bir toplam skorda** birleştiriyor, ama farklı
tier'ler (katmanlar) üzerinden: Tier 1-4 dramaya, Tier 5 gösteriye/
dominasyona odaklanıyor. Tier 5 sadece gol farkı 3+ olduğunda devreye
giriyor — çünkü o noktadan sonra "kim kazanacak" belirsizliği zaten
kalmıyor, soru "bu galibiyet ne kadar kaliteliydi"ye dönüşüyor.

## Tier 1 — Sonuç belirsizliği (max 59 ham puan)

Bir maçı izlenir kılan en güçlü sinyal, sonucun ne zaman netleştiği.

- **Skor yön değişimi (değişim başına 8 puan, max 3 değişim → 24 puan):**
  Liderliğin kaç kez el değiştirdiği (ev sahibi önde → berabere →
  deplasman önde gibi). 3'te sınırladık çünkü bunun ötesi gerçek hayatta
  neredeyse hiç olmuyor ve marjinal fayda azalıyor.
- **80+ dakikada gelen beraberlik/galibiyet golü (20 puan, ikisi birden
  olursa +10 daha → 30 puan):** Maçın en dramatik anı genelde son
  dakikalarda gelen bir gol. Sadece beraberlik golü mü, yoksa hem
  beraberlik hem de galibiyet mi (yani takım önce eşitleyip sonra öne
  geçti) — ikincisi çok daha nadir ve daha dramatik olduğu için ekstra
  puan alıyor.
- **80. dakikaya ≤1 farkla girilmesi (10 puan, ya da geç gol zaten
  gerçekleştiyse 5 puan):** "Maç hâlâ açık mıydı" sinyali. Geç gol zaten
  olduysa bu bilgi kısmen tekrar sayılıyor olur, o yüzden puanı yarıya
  indiriyoruz.

## Tier 2 — Kıl payı anlar (max 45 ham puan)

Gerçekleşmemiş ama gerçekleşebilecek dram, ve maçın sertliğini/
gerginliğini gösteren olaylar.

- **Kırmızı kart — direkt (12) vs ikinci sarıdan (8):** Direkt kırmızı
  daha ani ve oyunu daha çok değiştiren bir olay, bu yüzden daha yüksek
  puan alıyor.
- **Kaçırılan penaltı (10) vs gerçekleşen penaltı (5):** Kaçırılan
  penaltı, golden bile daha dramatik — hem gerilim hem hayal kırıklığı
  içeriyor. Gerçekleşen penaltı "beklenen" bir sonuç olduğu için daha
  düşük puanlanıyor.
- **Direğe çarpan şut (şut başına 4, max 3 şut → 12):** Her biri kıl
  payı kaçan bir an.
- **İki takımın da büyük fırsat yakalaması (3 puan):** Karşılıklı gerçek
  tehdit = çekişme kanıtı. Tek taraflı büyük fırsat bunu ödüllendirmiyor.
- **İki takımın da büyük fırsat kaçırması (8 puan):** Bundan daha güçlü
  bir sinyal — ikisi de kritik anlarda kaçırdıysa maç gerçekten
  kıl payında gitmiş demektir.

## Tier 3 — Kalite/çekişme (max 18 ham puan)

- **xG farkının küçüklüğü (max 10, sadece gol farkı <3 iken aktif):**
  İki takımın gerçek pozisyon kalitesi ne kadar yakınsa maç o kadar
  dengeli demektir. **Gol farkı 3+ olduğunda bu bileşeni tamamen
  kapatıyoruz** — çünkü o durumda xG farkı zaten büyük olacaktır ve
  aynı ham veriyi (expected_goals) Tier 5'te farklı bir şekilde
  (winner/loser xG olarak) zaten kullanıyoruz. Aynı veriyi iki tier'de
  aynı anda saymamak için bu ayrım gerekli.
- **Toplam xGOT + toplam kaleci kurtarışı (max 8, eşik 6-12 arası
  lineer):** Yüksek bir toplam, "kaleyi bulan tehlikeli şutlar ve bunlara
  karşı yapılan kritik kurtarışlar" demek — yani hem atak hem
  kalecilik kalitesi yüksekti.

## Tier 4 — Tansiyon (max 9 ham puan)

- **Toplam sarı kart (6'ya kadar 0, 7-12 arası kart başına 1, 12+ sabit
  6):** Az kart normal bir maç, ama belli bir eşiği geçince sertlik
  sinyali oluyor. Tavan koyduk çünkü aşırı kartlı bir maç otomatik
  olarak "daha iyi" sayılmamalı — bu bileşen küçük bir katkı olarak
  kalmalı.
- **Toplam korner (6'ya kadar 0, 7-12 arası korner başına 0.5, 12+ sabit
  3):** Dolaylı bir baskı göstergesi, en zayıf sinyallerden biri
  olduğu için düşük ağırlıkta.

## Tier 5 — Dominasyon Düzeltmesi (max 36 ham puan, sadece |gol farkı| ≥ 3)

Bu tier'in tek amacı: **Tier 1-4'ün yakalayamadığı maçları kurtarmak.**
Örneğin Barcelona'nın penaltısız, kartsız, geri dönüşsüz 5-0 kazandığı bir
maç, Tier 1-4'te neredeyse hiç puan almaz (skor hiç değişmedi, kart yok,
penaltı yok) ve yanlışlıkla "sıkıcı" kategorisine düşer. Tier 5 bunu
düzeltiyor.

- **Toplam gol (gol başına 2, max 5 gol → 10):** En kaba ama en somut
  "gösteri" kanıtı.
- **Kazananın xG'si (max 10, xG≥3'te tam puan):** Golün şans eseri değil,
  gerçekten hak edilmiş olduğunu gösteriyor.
- **Kazananın possession'ı ≥%60 (5 puan):** Kontrollü, hakimiyet kurulmuş
  bir galibiyet.
- **Kaybedenin xG'si >1 (5 puan):** Kaybeden taraf da rekabetçi oynadıysa
  (tamamen ezilmediyse) bu bir bonus. Kaçırılan büyük fırsat yerine xG
  eşiği seçtik çünkü xG sürekli bir ölçü, ikili (0/1) bir sinyalden daha
  ince ayrım yapabiliyor.
- **Uzaktan gol (gol başına 3, max 2 gol → 6):** Ceza sahası dışından
  atılan goller (`shotmapEvent.isFromInsideBox === false`), estetik/
  seyirlik değeri yüksek anlar.

**Neden büyük fırsat ve isabetli şut sayısı burada yok?** İlk taslakta
vardı ama xG zaten bunların özünü (pozisyon kalitesi + isabet olasılığı)
taşıdığı için aynı sinyali tekrar tekrar saymış oluyorduk. Sadeleştirip
tavanı 44'ten 36'ya indirdik.

## Neden 130'a bölüp normalize ediyoruz

Ham puanların teorik maksimumu (tüm tier'ler aynı anda tavana vursa)
**167** — ama bu gerçek hayatta imkansız, çünkü Tier 1'in maksimumu (çok
sayıda yön değişimi + geç dram) ile Tier 5'in aktif olması (3+ farkla
bitmiş bir maç) birbirini mantıksal olarak dışlıyor.

Elle kurduğumuz gerçekçi senaryolarla test ettik:
- **En yüklü "kaotik çekişme" senaryosu** (birden fazla geri dönüş +
  kırmızı kart + kaçan penaltı + direkler + yoğun kalecilik): **~127 ham
  puan**
- **En yüklü "blowout" senaryosu** (büyük skorlu galibiyet + üstüne kart/
  direk gibi olaylar): **~106 ham puan**

Bölüm olarak **130**'u seçtik çünkü gerçek dünyada ulaşılması hem zor hem
imkânsız değil — bu sayede 100'e normalize edilen skor gerçekten
istisnai maçlarda tavana yaklaşıyor, sıradan maçlarda gereksiz
sıkışma olmuyor.

## Badge bantları

| Aralık | Badge | Gerekçe |
|---|---|---|
| 0-29 | Uyutabilir | Az olay, az drama, düşük kalite |
| 30-44 | İdare Eder | Vasat, izlenebilir ama unutulur |
| 45-60 | İyi Maç | Belirgin bir çekişme veya kalite var |
| 61-75 | Tatmin Edici | Net bir drama ya da gösiri sinyali |
| 76-83 | Futbol Ziyafeti | Birden fazla güçlü sinyal aynı anda |
| 84-100 | Tarihe Geçer | Neredeyse teorik tavana yakın, çok nadir |

Bu bantlar başlangıçta **elle işaretlenmiş çapa maçlarla** kalibre
edildi (bilinen "sıkıcı" ve "iyi" maçlar formülle test edilip sıralama
sağduyuyla karşılaştırıldı). Örnek çapa noktaları:

- Bologna-Lazio (0-1), Lazio-Genoa (1-0): **~37-39** ham puan — iki
  tarafın da onayladığı "sıkıcı" maçlar
- Elche-Real Madrid (2-3, iki kez geç gol), Arjantin-Mısır: **~67** ham
  puan — "iyi maç" hissi veren örnekler
- Amed Sportif-Trabzonspor (kaçırılan penaltı + son dakika galibiyeti):
  **~85** ham puan — üst banda net bir örnek

Veri biriktikçe bu sabit bantların yerini **percentile tabanlı dinamik
bantlara** bırakması planlanıyor (örn. "son 200 maça göre üst %10"), ama
şu an için sabit eşikler kullanılıyor.

## Bilinen sınırlamalar

- **Effective playing time** (topun fiilen oynanan süresi) ve **PPDA**
  (pres yoğunluğu) formülde yok — FotMob bu verileri sağlamıyor
  (PPDA sadece Understat'ta var, ayrı bir veri kaynağı).
- **VAR incelemeleri** event listesinde bazen görünüyor ama henüz
  formüle dahil edilmedi.
- Formül sadece **istatistiksel** bir tahmin — maçın gerçek "izlenebilirlik"
  hissini (yorumcu performansı, atmosfer, bağlam/rekabet önemi gibi
  ölçülemeyen faktörleri) yakalayamaz. Badge isimlerinin hepsinin
  ("Uyutabilir", "Tarihe Geçer" vb.) temkinli/olası dilde olması bilinçli
  bir tercih — bunlar kesin hükümler değil, istatistiklere dayalı
  tahminler.
