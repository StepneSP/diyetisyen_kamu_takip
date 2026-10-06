# 🥗 Diyetisyen Kamu İlan Takip

İstanbul odaklı, Beslenme ve Diyetetik mezunları için kamu ilanlarını tek panelde izlemek üzere hazırlanmış Streamlit + SQLite + GitHub Actions projesi.

## Ne yapar?

- Kariyer Kapısı ve seçilmiş resmî kurum/üniversite kaynaklarını izlemek için Google News RSS tabanlı keşif kullanır.
- GSB, Adalet/CTE, MEB, İstanbul devlet üniversiteleri, İBB ve Resmî Gazete için kaynak listesi içerir.
- Bulduğu ilanları SQLite'a kaydeder.
- Aynı ilanı tekrar eklememek için URL+başlık hash'i kullanır.
- İstanbul ve Diyetisyen/Beslenme filtresi sunar.
- Kullanıcının KPSS P3 puanına göre basit bir "uygunluk" skoru hesaplar.
- GitHub Actions ile günlük otomatik tarama yapabilir.
- Başvuru işlemini otomatikleştirmez; kullanıcı her zaman resmî ilana gider.

## Önemli: veri doğruluğu

Bu proje bir **izleme/keşif aracıdır**, resmî başvuru sistemi değildir. Otomatik toplayıcı bazı ilanları kaçırabilir veya ilanı geç görebilir. Bu nedenle başvuru öncesinde her zaman "Resmî ilana git" bağlantısındaki kurum ilanı kontrol edilmelidir.

Kariyer Kapısı'nın kamu işe alım platformu, kamu ilanlarının şeffaf biçimde paylaşılması ve başvuru/yerleştirme süreçlerinin takip edilebilmesi için kullanılır:
https://kariyerkapisi.gov.tr/isealim

## İlk doğrulanmış tohum verileri

Projeye, araştırma sırasında doğrulanan örnekler başlangıç verisi olarak eklenmiştir:

- GSB 2026: 100 sözleşmeli diyetisyen.
- Adalet Bakanlığı / CTE 2026: 21 sözleşmeli diyetisyen.
- MEB Akademi 2026: İstanbul Ataşehir Zübeyde Hanım, İstanbul Sultanahmet ve İstanbul Haydarpaşa Eğitim ve Uygulama Merkezlerinin her biri için 1 diyetisyen.
- İstanbul Medeniyet Üniversitesi: 2025 4/B ilanında Diyetisyen pozisyonu.

Bu tohum kayıtlar geçmiş/duyurulmuş ilanları gösterir; "aktif başvuru" anlamına gelmez.

## Yerelde çalıştırma

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
python collector.py
streamlit run app.py
```

Tarayıcıda Streamlit'in verdiği yerel adresi aç.

## GitHub + Streamlit Community Cloud

1. Bu klasörü yeni bir GitHub repository'sine yükle.
2. Repository'yi Streamlit Community Cloud'a bağla.
3. Main file olarak `app.py` seç.
4. GitHub Actions'ın çalışabilmesi için workflow'a yazma izni açık olmalı.
5. İlk kez `Actions -> Daily public dietitian job scan -> Run workflow` ile manuel tarama yapılabilir.
6. Sonrasında günlük cron çalışır.

Streamlit Community Cloud:
https://streamlit.io/cloud

## Telegram bildirimi (sonraki sürüm)

İstersen GitHub Secrets'a:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

eklenerek yalnızca yeni ve yüksek uygunluklu ilanlarda Telegram bildirimi gönderilebilir.

## Daha sağlam sürüm için önerilen geliştirmeler

1. Kariyer Kapısı'nın ilan ekranı için Playwright tabanlı doğrudan tarayıcı otomasyonu.
2. Üniversitelerin personel duyuru sayfaları için ayrı parser'lar.
3. Resmî Gazete PDF'lerinden ilan metni çıkarma.
4. Son başvuru tarihini daha güvenilir tarih ayrıştırma.
5. İlanın aktif/pasif durumunu kontrol etme.
6. Geçmiş KPSS taban/sıralama veritabanı.
7. Kullanıcının gerçek KPSS P3 puanına göre rekabet tahmini.
8. Telegram/e-posta push bildirimi.
9. "Başvuruldu / kaydedildi / takipte" durumları.
10. İstanbul dışındaki illeri açıp kapatma.

## Neden Google News RSS kullanıldı?

İlk sürümde üçüncü taraf ücretli arama API'sine bağımlı olmamak için kaynak keşfi Google News RSS üzerinden yapıldı. Kaynak sonuçları mümkün olduğunca resmî alan adıyla sınırlandırılır. Ancak bu yöntem %100 kapsam garantisi vermez. Kariyer Kapısı için sonraki sürümde doğrudan Playwright connector eklemek daha güvenilir olacaktır.
