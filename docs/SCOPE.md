# Proje Kapsamı ve Hedefleri

Bu belge projenin kesinleşmiş hedeflerini, mimari sınırlarını ve uygulama fazlarını tanımlar.

## 1. Temel Amaç ve Ürün Hedefi

Novation Circuit Rhythm (stok build 5706) üzerinde, cihazın normal sample groovebox işlevlerini bozmadan bir tuş kombinasyonuyla geçiş yapılabilen **32-Adım MIDI Sequencer Only** modu inşa etmek.

---

## 2. Kesinleşmiş Kapsam

### Faz 1: Çekirdek 32-Adım Sequencer Paketi (1. Gerçek Cihaz Testi Hedefi)
1. **Ana Ekranda 32 Pad = 32 Adım (`grid_mode == 0`):**
   - Eski Sample/Step sayfasında (`grid_mode == 0`) 32 pad'in tamamı aynı pattern'in 1–32. adımlarını birlikte gösterir ve düzenler (üst 16 pad = 1–16, alt 16 pad = 17–32).
   - Playhead (yürüyen imleç, durum bit 0) 1. adımdan 32. adıma kesintisiz akar.
   - 8 track ve mevcut pattern sayısı aynen korunur.
2. **Sayfa (`1–16`) Tuşu ve Görünüm Bağımsızlığı:**
   - Ana 32-pad ekranında (`grid_mode == 0`) iki sayfa da ekranda olduğu için `1–16` sayfa kaydırma ofseti `0`'a kilitlenir (`+16` eklenmez, `pad & 0x1F` taşma koruması uygulanır).
   - `Note` (`mode 1/7`), `Velocity` (`mode 2`), `Gate` (`mode 3`), `Pattern Settings` (`mode 4`), `Microstep` (`mode 5`) ve `Probability` (`mode 6`) ekranlarında alt 16 pad o ekranın orijinal düzenini korur ve **`1–16` sayfa değiştirme tuşu (1–16 / 17–32 geçişi) %100 orijinal haliyle çalışır**.
   - Pattern uzunluğu (Start/End step), yön, hız ve Mutate işlemleri `Pattern Settings` sayfasında (`mode 4`) `1–16` sayfa tuşuyla birlikte orijinal şekilde çalışmaya devam eder.
3. **Sahiplik (Ownership) Temizliği:**
   - Pad basılı tutulurken track veya ekran (`grid_mode`) değiştirildiğinde basılı adım maskeleri (`view + 0xB8`, `view + 0xC0`) ve `held` biti (`view + 0x74` bit 3) temizlenerek asılı LED/adım kalması engellenir.
4. **Bağımsız 32 Sequencer Projesi (`[proj_view + 0x36]`) ve Packs Kilidi:**
   - Stok Projects ekranındaki (`0x0804F080`) 64 proje yuvasının 1. sayfası (`[proj_view + 0x36] = 0`, Proje 1–32) Normal Sample moduna, 2. sayfası (`[proj_view + 0x36] = 1`, Proje 33–64) ise Sequencer Only moduna kilitlenir.
   - Projects ekranında Up/Down ile sayfa geçişi (`0x0804F12C`) ve Sequencer modunda `Packs` sayfası (`Shift + Projects`, `0x0803DB54`) devre dışı bırakılır.
   - Böylece Sequencer modunda `Projects` tuşuna basıldığında, normal projelerden tamamen bağımsız **32 adet Sequencer projesi** görülür; boş pad ile yeni proje açma, `Save`, `Duplicate` ve `Clear` (Delete) %100 orijinal Novation koduyla çalışır.
5. **Mod Geçişi ve Sadece MIDI Çıkışı (Dahili Sample Susturma):**
   - Güvenli bir tuş kombinasyonuyla (ör. `Shift + Sample Rec` veya `Shift + Note`) Normal Mod ile Sequencer Only Modu arasında geçiş yapılır.
   - Sequencer Only modundayken dahili sample ses motoru tetiklemesi susturulur, yalnızca harici MIDI Note On/Off ve CC/Clock çıkışı gönderilir.

### Faz 2: Müzikal Genişleme Paketi (2. Gerçek Cihaz Testi Hedefi)
1. **Root Nota + Macro Knob ile Akor / Triad Üretici:**
   - Gerçek bağımsız polifoni yerine, adımdaki tek kök nota (Root Note) üzerinden belirlenen bir Macro Knob ile `0 = Tek Nota (Mono)`, `Power Chord (5th)`, `Major Triad`, `Minor Triad`, `Sus2`, `Sus4`, `Maj7`, `Min7` akor tipleri seçilir.
   - Kanal başına aktif akor notaları izlenerek `Note Off` ve `Stop` anında tüm akor sesleri güvenle kapatılır (stuck-note koruması).
2. **32-Pad Ekranında Hızlı Uzunluk Kısayolu:**
   - Ana 32-pad ekranındayken (`grid_mode == 0`) `1–16` tuşuna basılı tutup 1..32 pad'lerinden birine basarak pattern bitiş adımını doğrudan seçme kısayolu.

---

## 3. Kapsam Dışı (Kalıcı Olarak Çıkarılanlar)
- **64 ve 128 Adım:** Stok veri yapısındaki parametre örtüşmesi ve RAM sınırı nedeniyle 64 adım hedefinden tamamen vazgeçilmiştir; adım sınırı kalıcı olarak **32 adımdır**.
- **Bağımsız Çok Notalı Polifoni:** Her notanın ayrı gate/velocity taşıdığı serbest polifoni kapsam dışıdır (yerine Faz 2'deki Root + Knob Akor üretici kullanılacaktır).
- **Özel SD Kart Dosya Sistemi:** SD kart sürücüsüne müdahale edilmeyecek, stok 2. proje bankası (`33..64`) kullanılacaktır.
