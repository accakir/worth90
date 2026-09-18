# Worth90

Bu klasör, Colab'a bağlı eski defter yerine yerelde tekrar çalıştırılabilen uygulamayı içerir.

1. Bir terminal açıp bu klasöre gelin.
2. `python -m pip install -r requirements.txt` ile bağımlılıkları kurun.
3. Günlük küçük toplama için `python app.py collect --limit 8` çalıştırın.
4. Arayüz için `python app.py serve`, ardından `http://127.0.0.1:5000`.

Her çalışma en fazla 12 yeni maçı işler. Lig listeleri arası 3–6 saniye, maç istekleri arası rastgele 10–18 saniye bekler; daha önce SQLite veritabanına yazılmış maçları tekrar indirmez. Bu, yükü azaltır fakat herhangi bir sitenin engellemeyeceğine dair garanti değildir. FotMob'un kullanım koşullarına ve erişim sınırlarına uyun.

Özet için isteğe bağlı olarak `YOUTUBE_API_KEY` ortam değişkenini tanımlayın. Video isteği ancak kullanıcı bir maç satırını açtığında atılır; bulunan video yerel veritabanında önbelleğe alınır. Aynı anda yalnızca bir iframe açıktır ve diğer satır açıldığında eskisi DOM'dan kaldırılır.
