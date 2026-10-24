# Circuit Rhythm MIDI Sequencer Modu

Bu proje, Novation Circuit Rhythm (stok build 5706) firmware'i üzerinde çalışan, bağımsız ve güvenli bir MIDI Sequencer modifikasyonudur.

---

## 1. Temel Amaç ve Ürün Hedefi

Circuit Rhythm normalde sample tabanlı bir groovebox'tır. Bu projenin amacı:

- **Harici MIDI Kontrolcüsü / Sequencer:** Cihazın dahili sample çalma motorundan bağımsız, harici synth ve ses modüllerini süren bir sequencer olarak çalışmasını sağlamak.
- **Tek Ekranda 32 Adım:** Normalde 16'şar adımlık sayfalar (1–16 ve 17–32) halinde gezilen step sequencer'ı, 32 pad'in tamamını kullanarak aynı pattern'in 1–32 adımlarını tek bir ekranda aynı anda gösterecek ve düzenletecek hale getirmek.

---

## 2. Kapsam ve Sınırlar

Proje hedefleri [docs/SCOPE.md](docs/SCOPE.md) belgesinde aşamalara ayrılmıştır:

### İlk Sürüm (Şu Anki Kapsam - 32 Adım)
- 32 pad üzerinde aynı pattern'in 32 adımı birlikte görüntülenir ve düzenlenir.
- 8 track ve pattern yapısı aynen korunur (track sayısı veya pattern sayısı azaltılmaz).
- Gate, Velocity, Microstep, Probability, Tie ve Mutate gibi stok sequencer yetenekleri ve parametreleri eksiksiz korunur.
- Henüz çakışması olmayan güvenli bir tuş kombinasyonuyla stok mod ve Sequencer Only modu arasında geçiş sağlanır.
- Sequencer Only modunda Packs sayfası devre dışı bırakılır; ileride projelerin stok projelerle karışmaması için ayrı proje alanı oluşturulur.

### Gelecek Hedef (64 Adım)
- Tek bir mantıksal pattern'de 64 adım desteği ve sayfalar arasında gezinme.

> [!NOTE]
> Bellek analizi ([analysis/LONG-PATTERN-TESTS.md](analysis/LONG-PATTERN-TESTS.md)), stok veri yapısında doğrudan 33. adıma yazmanın veri çakışmasına yol açtığını göstermiştir. Bu nedenle 64 adıma geçiş için RAM/kayıt mimarisi kanıtlanmadan sınır artırılmayacaktır.

---

## 3. Mevcut Teknik Durum

Projenin şu anki durumu [docs/STATUS.md](docs/STATUS.md) ve [docs/UI-TRACE-5706.md](docs/UI-TRACE-5706.md) dokümanlarında özetlenmiştir:

- **Temel Doğrulama (M0):** Orijinal `stock/circuitrhythm-firmware-5706.syx` dosyası SHA-256 (`11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf`) ile sabitlendi. Baseline testleri, SysEx çözme/paketleme ve Unicorn ARM Cortex-M emülasyon testleri başarıyla çalıştı.
- **UI ve Akış Analizi (M1):** Pad basış dağıtımı (`0x08040108`), step görünümü vtable yapısı (`0x080682CC`), step toggle (`0x0805D610`), commit/notify mekanizması ve LED observer zinciri statik disassembly ve sentetik testlerle doğrulandı.
- **İlk Yama Taslağı (M2 Adayı):** Risk içermeyen, yalnızca step basıldığında LED rengini palet 31 yerine 30 yapan tek komutluk bir tanılama yaması ([docs/FIRST-PATCH-SCOPE.md](docs/FIRST-PATCH-SCOPE.md)) tasarlandı; ancak henüz derlenmedi veya cihaza yüklenmedi.

---

## 4. Güvenlik ve Çalışma Kuralları

- **Cihaz Güvenliği:** Fiziksel cihaza izinsiz hiçbir firmware veya komut gönderilmez. Orijinal SysEx dosyası asla ezilmez.
- **Bootloader Koruması:** Bootloader, flash option byte'ları veya koruma bayraklarına kesinlikle müdahale edilmez. Yalnızca denetlenmiş uygulama (`0x08010000+`) alanı hedeflenir.
- **Aşamalı İlerleme:** Tüm kod değişiklikleri önce yerel testlerde ve emülatörde kanıtlanır; testler [docs/ROADMAP.md](docs/ROADMAP.md) sırasına göre küçük adımlarla yürütülür.

---

## Dokümantasyon ve Rehberler

- [START-HERE.md](START-HERE.md) — İlk kurulum, ortam gereksinimleri ve test çalıştırma rehberi
- [docs/SCOPE.md](docs/SCOPE.md) — Güncel ve gelecekteki fonksiyonel kapsam
- [docs/STATUS.md](docs/STATUS.md) — Güncel geliştirme durumu ve açık görevler
- [docs/ROADMAP.md](docs/ROADMAP.md) — Aşama aşama geliştirme kilometre taşları
- [docs/RECOVERY.md](docs/RECOVERY.md) — Cihaz yedekleme, bootloader ve kurtarma prosedürleri
