# Worth90 — Puanlama Metodolojisi (v2)

Bu doküman, `score.py`'deki formülün **hangi istatistiği neden aldığını** ve
**ağırlıkları neye göre belirlediğimizi** anlatıyor.

## v1'den v2'ye: neden değişti

İlk formül (v1) tamamen elle, birkaç çapa maça bakarak kalibre edilmişti —
"göz kararı" bir sistemdi. v2, **600 kişilik bir anketten** gelen göreceli
önem puanlarına dayanıyor. Anket iki bölümden oluştu:

1. **15 madde**, her maç için geçerli olan sinyaller (skor yön değişimi, geç
   goller, kartlar, penaltılar, xG farkı vb.) — her katılımcı 15 seviyeyi
   (1-5) **3'er kez** kullanarak zorunlu dağılım yaptı (tavan etkisini
   önlemek için).
2. **4 madde**, sadece 3+ farkla biten maçlar için geçerli olan dominasyon
   sinyalleri (toplam gol, kazananın xG'si, possession, kaybedenin xG'si) —
   her seviye (1-5) **birer kez** kullanılarak net bir sıralama elde edildi.
3. **Bir makro soru**: "Gerilimli/yakın biten bir maç mı, yoksa baskın/
   farklı biten bir maç mı sizi daha çok izlemeye teşvik eder?" — sonuç:
   **Drama %68.3 / Farklı skor %31.7**.

## Temel fikir: iki farklı "izlenmeye değer" türü var

- **Drama formülü**: sonucun son ana kadar belirsiz kaldığı, geri dönüşlerin
  olduğu maçları ölçer. Tavanı **100**.
- **Dominasyon formülü**: tek taraflı ama kaliteli, çok gollü bir galibiyeti
  ölçer. Tavanı **77** (aşağıda açıklanıyor).

Hangi formül(ler) kullanılır, **gol farkına** göre:

| Gol farkı | Kullanılan formül |
|---|---|
| 0 veya 1 | Sadece Drama |
| 2 | (Drama + Dominasyon) / 2 |
| 3 ve üstü | Sadece Dominasyon |

**Fark=2 neden ortalama?** Sıfır ile üç arasında sert bir geçiş yerine, iki
adımlı bir yumuşatma: 2 farklı bir maç hem biraz dramatik hem biraz
dominasyonlu olabilir (örn. 3-1). Bu, tam sınırda (2→3) oluşacak ani
sıçramayı ikiye böler. **Not:** Bu tam bir çözüm değil, bir azaltma — 2-0
gibi az olaylı, düşük tempolu bir dominasyon maçının da kendi içinde sınırlı
bir seyir zevki olduğu kabul ediliyor, bu yüzden fazla "kurtarılmaya"
çalışılmadı.

## Drama formülü (ham tavan: 133.25 → 100'e normalize)

Sıralama, ankette çıkan önem puanına göre (yüksekten düşüğe):

| Madde | Puan | Anket puanı | Not |
|---|---|---|---|
| 80+ dakikada beraberlik/galibiyet golü | 1. gol 8, 2. +5, 3. +3 → **16** | 3.83 | Azalan katkı: her ek olay biraz daha az önemli |
| 80. dakikaya ≤1 farkla girilmesi | **15.5** | 3.74 | Sabit, tek seferlik |
| Skor yön değişimi | 1. 9, 2. +4, 3. +2 → **15** | 3.71 | |
| İki takımın da büyük fırsat yakalaması | min(ev,dep) 1'er 9, 2'şer +3.5, 3'er +2 → **14.5** | 3.69 | İki takımın en zayıf halkasına bakılır |
| Uzaktan gol | 1. gol 7, 2. +4, 3. +2 → **13** | 3.59 | |
| Direkt kırmızı kart | 1. 8, 2. +3 → **11** | 2.49* | *bkz. aşağıdaki not |
| Kaçırılan penaltı | 1. 7, 2. +3 → **10** | 2.65* | *bkz. aşağıdaki not |
| xG farkının küçüklüğü | max **8**, fark≥3'te 0 | 3.13 | Sadece fark<2 formülünde etkili çünkü Tier 5'te aynı veri (xG) farklı şekilde kullanılıyor |
| Toplam kaleci kurtarışı | 8 kurtarışta tam puan, lineer → **7.5** | 3.10 | |
| İkinci sarıdan kırmızı kart | 1. 5, 2. +2.5 → **7.5** | 2.31* | *bkz. aşağıdaki not |
| Direğe çarpan şut | 1. 3, 2. +2 → **5** | 2.92 | |
| İki takımın da büyük fırsat kaçırması | min(ev,dep) 1'er 2.5, 2'şer +1.5, 3'er +0.75 → **4.75** | 2.89 | |
| Gol olan penaltı | sabit **3** (kaç olursa olsun) | 3.26* | *bkz. aşağıdaki not |
| Toplam sarı kart | 7 kartta tam puan, lineer → **1.5** | 2.40 | |
| Toplam korner | 15 kornerde tam puan, lineer → **1** | 2.33 | |

### Anket-önyargısı düzeltmesi (yıldızlı maddeler)

Kart ve penaltı maddelerinde ham anket sıralaması ile verilen ağırlıklar
**kasıtlı olarak** ters düşüyor: anket "gol olan penaltı"yı (3.26) yüksek,
"direkt kırmızı kartı" (2.49) düşük puanlamış — ama bu maddeler formülde
tam tersi şekilde ağırlıklandırıldı.

**Gerekçe:** Anket sorusu katılımcılara soyut bir senaryo olarak
sorulmadı; birinci tur pilot yanıtlardan, katılımcıların bu maddeleri
**"kendi takımım kırmızı kart görürse / penaltı kaçırırsa"** çerçevesinden
cevapladığı görüldü — yani "keyifli" değil "üzücü" bir olay olarak
işaretlediler. Tarafsız bir izleyici perspektifinden ise direkt kırmızı
kart, kaçırılan penaltı ve ikinci sarıdan kırmızı, maçın akışını değiştiren
gerçekten dramatik olaylardır. Bu yüzden bu üç madde + "gol olan penaltı"
için ham anket sırası değil, **sağduyu + çerçeveleme düzeltmesi** kullanıldı.

**Not:** Bu düzeltme şu an için bir **hipotez** — ayrı bir anket turunda
("tarafsız bir izleyici olarak...") doğrudan test edilmedi. İleride bu
varsayımı doğrulayacak ek bir soru sorulması METHODOLOGY'nin bir sonraki
revizyonu için aday.

## Dominasyon formülü (ham tavan: 133.25 → 77'ye normalize)

Sadece gol farkı ≥2 iken (fark=2'de ortalamanın bir parçası, fark≥3'te
tek başına) hesaplanır.

| Madde | Puan | Anket puanı |
|---|---|---|
| Toplam gol | 2→5*, 3→8, 4→11, 5→16, 6→20, 7+→23 (max **23**) | 3.57 (4'lü grupta en yüksek) |
| Kazananın xG'si | xG≥3'te tam puan, orantılı → max **18** | 2.53 |
| Kaybedenin xG'si | >1 ise sabit **14** | 2.10 |
| Kazananın possession'ı | >%60 ise sabit **14** | 1.92 (4'lü grupta en düşük) |
| Uzaktan gol | Drama ile aynı → max **13** | (paylaşılan madde) |
| Direkt kırmızı kart | Drama ile aynı → max **11** | (paylaşılan madde) |
| Kaçırılan penaltı | Drama ile aynı → max **10** | (paylaşılan madde) |
| Toplam kaleci kurtarışı | Drama ile aynı → max **7.5** | (paylaşılan madde) |
| İkinci sarıdan kırmızı kart | Drama ile aynı → max **7.5** | (paylaşılan madde) |
| Direğe çarpan şut | Drama ile aynı → max **5** | (paylaşılan madde) |
| İki takımın da büyük fırsat kaçırması | Drama ile aynı → max **4.75** | (paylaşılan madde) |
| Gol olan penaltı | Drama ile aynı → sabit **3** | (paylaşılan madde) |
| Toplam sarı kart | Drama ile aynı → max **1.5** | (paylaşılan madde) |
| Toplam korner | Drama ile aynı → max **1** | (paylaşılan madde) |

**\* Toplam gol = 2 durumu:** Anket sadece 3+ farklı maçlar için soruldu,
yani toplam gol için en düşük gerçek veri noktası 3'tü (3-0). "2" değeri
(fark=2 blend durumunda mümkün, örn. 2-0), ilk basamağın (3→8) aynı
aralıkla geriye **extrapolasyonu** — 5 puan. Bu, anketten gelen bir veri
değil, tahmini bir doldurma; ileride ayrı bir soru ile netleştirilebilir.

**Neden "80+ dakika golü", "skor yön değişimi", "iki takımın da büyük
fırsat yakalaması" ve "xG farkı" burada yok?** Bunlar zaten Drama
formülüne özgü sinyaller — 3+ farklı bir maçta bu maddeler yapısal olarak
anlamsızlaşıyor (örn. 5-0'lık bir maçta "skor yön değişimi" hiç
gerçekleşmez). Onların yerini toplam gol, kazananın/kaybedenin xG'si ve
possession alıyor.

## Neden dominasyon tavanı 77

Anketin makro sorusu **Drama %68.3 / Farklı skor %31.7** çıktı. Bunu
dominasyon tarafının tavanına yansıtmak için üç seçenek değerlendirildi:

| Yöntem | Sonuç | Değerlendirme |
|---|---|---|
| Lineer (`100 × 0.317`) | 31.7 | Çok sert — tarihi bir 7-0 galibiyeti bile düşük puanda bırakır |
| Karekök sıkıştırma | 68.1 | Dengeli ama tercih edilen 90'dan uzak |
| **Küpkök sıkıştırma** | **77.4 → 77** | Seçilen değer |

Küpkök sıkıştırması tercih edildi çünkü anket oranına lineerden çok daha
sadık kalırken, gerçekten istisnai bir dominasyon galibiyetinin (7-0 gibi)
hâlâ yüksek/unutulmaz bir puan alabilmesine izin veriyor.

**Emergent bir sonuç:** Dominasyon formülünün tavanı (77) badge
sınırlarındaki "Tarihe Geçer" eşiğinin (84) altında kalıyor. Bu, **saf bir
3+ farklı galibiyetin hiçbir zaman en üst badge'e ulaşamayacağı** anlamına
geliyor — anketin "insanlar dramayı dominasyona tercih ediyor" bulgusunu
doğal bir şekilde yansıtan, bilinçli bir tasarım sonucu.

## Badge bantları (v1'den değişmedi)

| Aralık | Badge |
|---|---|
| 0-29 | Uyutabilir |
| 30-44 | İdare Eder |
| 45-60 | İyi Maç |
| 61-75 | Tatmin Edici |
| 76-83 | Futbol Ziyafeti |
| 84-100 | Tarihe Geçer |

## Bilinen sınırlamalar / açık sorular

- **Fark=2 ortalaması** sert geçişi azaltır ama ortadan kaldırmaz — 2-0 ile
  3-0 arasında hâlâ küçük bir sıçrama olabilir (bilerek kabul edildi).
- **Toplam gol = 2 için dominasyon puanı (5)** anketten değil,
  extrapolasyondan geliyor.
- **Kaleci kurtarışı ve kart/korner eşiklerinin "lineer artış" şekli**
  (0'dan tavana düz çizgi) anket tarafından doğrulanmadı, sadece maddenin
  kendisinin önemi anketten geliyor — eğrinin şekli (lineer/logaritmik/
  eşikli) hâlâ göz kararı.
- **Kart/penaltı çerçeveleme-önyargısı düzeltmesi** bir hipotez, ayrı bir
  anket turuyla doğrulanmadı (yukarıda detaylandırıldı).
- **Effective playing time** ve **PPDA** hâlâ formülde yok — FotMob bu
  verileri sağlamıyor.
- Formül sadece **istatistiksel** bir tahmin — maçın gerçek "izlenebilirlik"
  hissini (yorumcu performansı, atmosfer, rekabetin önemi gibi
  ölçülemeyen faktörleri) yakalayamaz. Badge isimlerinin temkinli dilde
  olması ("Uyutabilir", "Tarihe Geçer" vb.) bilinçli bir tercih.
