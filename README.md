# Circuit Rhythm 32-Adım MIDI Sequencer Modu

Bu proje, Novation Circuit Rhythm (stok build 5706) firmware'i üzerinde çalışan, cihazın normal sample groovebox işlevlerini koruyarak tek bir tuş kombinasyonuyla geçiş yapılabilen bağımsız bir **32-Adım MIDI Sequencer** modifikasyonudur.

---

## 1. Temel Amaç ve Kesinleşmiş Kapsam

Proje hedefleri [docs/SCOPE.md](docs/SCOPE.md) ve [docs/ROADMAP.md](docs/ROADMAP.md) belgelerinde iki net faza ayrılmıştır:

### Faz 1: Çekirdek 32-Adım Sequencer Paketi (1. Cihaz Testi)
- **Tek Ekranda 32 Adım (`grid_mode == 0`):** Eski Sample/Step ekranında 32 pad'in tamamı aynı pattern'in 1–32. adımlarını birlikte gösterir ve düzenler; Playhead 1'den 32'ye kesintisiz akar.
- **Sayfa (`1–16`) Tuşu ve Görünüm Bağımsızlığı:** Ana 32-pad ekranında (`grid_mode == 0`) sayfa kaydırma ofseti `0`'a kilitlenirken; `Velocity`, `Gate`, `Note`, `Pattern Settings`, `Microstep` ve `Probability` ekranlarında alt 16 pad kendi düzenini korur ve **`1–16` sayfa değiştirme tuşu (1–16 / 17–32 geçişi) %100 orijinal haliyle çalışır**.
- **Bağımsız 32 Sequencer Projesi (`[proj_view + 0x36]`):** Stok Projects ekranındaki 64 proje yuvasının ilk 32'si (`sayfa 0`) Normal Sample moduna, ikinci 32'si (`sayfa 1`, Proje 33–64) Sequencer Only moduna ayrılır. Sequencer modunda `Projects` tuşuna basıldığında bağımsız 32 Sequencer projesi görülür; boş pad ile yeni açma, `Save`, `Duplicate` ve `Clear` (Delete) %100 orijinal çalışır. `Packs` sayfası (`Shift + Projects`) Sequencer modunda kapatılır.
- **Sadece MIDI Çıkışı:** Sequencer modunda dahili sample ses motoru susturulur, yalnızca harici synth/modüllere MIDI Note On/Off ve Clock/CC gönderilir.

### Faz 2: Müzikal Genişleme Paketi (2. Cihaz Testi)
- **Root Nota + Knob ile Akor / Triad Üretici:** Adımdaki kök nota üzerinden bir Macro Knob ile Tek Nota (Mono), 5th, Major Triad, Minor Triad, Sus2/4 ve 7th akor seçimi.
- **32-Pad Ekranında Hızlı Uzunluk Kısayolu:** `grid_mode == 0` iken `1–16` + Pad `1..32` ile hızlı bitiş adımı seçimi.

> [!NOTE]
> **Kapsam Dışı:** 64/128 adım, serbest çok notalı polifoni ve özel SD dosya sistemi müdahaleleri bellek/veri güvenliği nedeniyle kapsam dışı bırakılmıştır.

---

## 2. Test ve Geliştirme Yöntemi

Geliştirmenin **%95'i bilgisayar üzerindeki Unicorn ARM Cortex-M emülatöründe** gerçek makine kodu çalıştırılarak doğrulanır. Fiziksel cihaza her adımda yükleme yapılmaz; yalnızca emülatörde tamamlanmış ve tüm testlerden geçmiş toplu paketler (Faz 1 ve Faz 2) cihaza yüklenir.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/run_baseline.py
.\.venv\Scripts\python.exe scripts/run_ui_audit.py
```

---

## 3. Dokümantasyon ve Rehberler

- [START-HERE.md](START-HERE.md) — İlk kurulum ve test çalıştırma rehberi
- [docs/SCOPE.md](docs/SCOPE.md) — Kesinleşmiş Faz 1 ve Faz 2 fonksiyonel kapsamı
- [docs/ROADMAP.md](docs/ROADMAP.md) — Emülatör odaklı geliştirme ve cihaz testi aşamaları
- [docs/STATUS.md](docs/STATUS.md) — Güncel teknik durum ve doğrulanan adresler
- [docs/UI-TRACE-5706.md](docs/UI-TRACE-5706.md) — 5706 makine kodu ve adres haritası
- [docs/RECOVERY.md](docs/RECOVERY.md) — Cihaz yedekleme, bootloader ve kurtarma prosedürleri
