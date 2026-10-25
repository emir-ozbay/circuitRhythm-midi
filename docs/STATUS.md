# Devralma durumu

25 Ekim 2026. **M0 tamamlandı. M1 tamamlandı. M2 Adım 2 (Patcher Aracı) ve Adım 3 (Sentetik Doğrulama ve Cihaz Testi Teklifi) tamamlandı. Adım 4 (32 Pad Step Yönlendirmesi, Sayfa Mantığı ve Taşma Koruması) tamamlandı. Adım 5 (32 Adım LED Grid Birleştirici ve Playhead Gösterimi) tamamlandı.**
Güncel sınır 32 adım; 64 adım, polifoni ve Elektron davranışları geliştirilmedi.

## Ortam ve bütünlük

- Stock: 508.861 bayt; SHA-256 `11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf`. Stock ve reference snapshot'ları değiştirilmedi.
- Windows AMD64 build **26200.9711**, DisplayVersion **25H2**; CPU **AMD Ryzen 7 3700X 8-Core Processor**.
  Registry ProductName `Windows 10 Pro`, Python platform çıktısı `Windows-10-10.0.26200-SP0`.
- Python **3.11.9**, MSC v.1938, 64 bit; `.venv` aktif. Capstone paket **5.0.9**, Unicorn **2.1.4**. `-O` kullanılmadı.
- Git **2.53.0.windows.2**. Remote yok. Firmware/build/log/venv/backups ignored kuralları devrede.

## Komutlar ve sonuçlar

Proje kökünde PowerShell, venv ile:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/patch_firmware.py --candidate-m2
.\.venv\Scripts\python.exe scripts/verify_m2_candidate.py
.\.venv\Scripts\python.exe scripts/run_ui_audit.py
.\.venv\Scripts\python.exe scripts/run_baseline.py
```

| Test Paketi / Script | Sonuç | Gerçekte kanıtladığı |
|---|---|---|
| `tests/test_led_compositor.py` (5 test) | PASS (5/5) | Stok Step View LED getter (`0x0805D3BC`) ve Compositor (`0x0804DD1C`) davranışı; 32 adımlık Step View LED tamponunun üst 16 (1–16) ve alt 16 (17–32) pad'e 1-e-1 eşlenmesi; Playhead imlecinin (durum bit 0) 1'den 32'ye kesintisiz akışı ve satır izolasyonu; Note ve Velocity modlarında alt padlerin o modun orijinal düzenini koruduğu; bellek ve taşma sınır güvenliği doğrulandı. |
| `tests/test_step_routing.py` (5 test) | PASS (5/5) | Stok container yönlendirmesi, `step >= 32` taşma ve bellek bozulma kanıtları (`view+0xB4`, ST1/ST2 parametre ezilmeleri), güvenli 32-pad tam döngü (tüm 32 adım ON/OFF ve commit), sınır ötesi çoklu basış ve clamping maskeleme doğrulandı. |
| `tests/test_patcher.py` (15 test) | PASS (15/15) | Güvenlik sınırları, bozuk hash reddi, çakışma engeli, kayıpsız roundtrip ve tam durum RAM emülasyonu (`test_pad_press_synthetic_ram_full_state_comparison`) doğrulandı. |
| `tests/test_ui_contracts.py` (7 test) | PASS (7/7) | UI kontratları, step press/release yaşam döngüsü ve sahiplik sınırları regresyon görmedi. |
| `scripts/verify_m2_candidate.py` | PASS | 32 adımın tamamında (0..31) Unicorn sentetik RAM emülasyonu: basılı adım LED'i palet 31'den 30'a değişti; kalan 31 LED ve 20.800 baytlık pattern belleği %100 korundu. |
| `scripts/patch_firmware.py --candidate-m2` | PASS | `build/circuitrhythm-5706-m2-candidate.syx` (SHA-256 `8c6996e2...`, CRC `0x2DBD7611`) ve manifest üretildi. İmajda yalnız 1 bayt değişti (`0x0805CF68`: `1f` -> `1e`). |
| `scripts/run_ui_audit.py` | PASS | UI audit sentetik RAM ve statik kanıtları doğrulandı (`logs/ui-audit-.../`). |
| `scripts/run_baseline.py` | PASS | Host baseline testleri eksiksiz geçti (`logs/baseline-.../`). |

## Yeni kesin bulgular

- **Step View LED Renk Motoru (`0x0805CF24`) ve Playhead İmleci:**
  - Step View durum sözcüğü (`view + 0x74 + 2 * step`) içindeki Bit 0'ın (`0x0001`) Playhead (playback cursor) olduğu Unicorn ile kesin olarak kanıtlanmıştır.
  - Palet eşlemesi:
    - Boş adım (Bit 1 = 0): normalde `0x0019` (sönük), Playhead üzerinde iken `0x001B` (parlak beyaz/gri).
    - Dolu adım (Bit 1 = 1, Hit): normalde `0x0018` (aktif renk), Playhead üzerinde iken `0x001A` (parlak vuruş rengi).
    - Basılı adım (Bit 3 = 1, Held): palet 31 (`0x001F`) veya M2 yamasında palet 30 (`0x001E`).
- **32 Adım LED Grid Birleştirici (Compositor):**
  - Step View'ın mantıksal LED tamponu (`[view + 4]` -> cell -> buffer) yerel olarak 32 adımı (64 bayt) eksiksiz tutar.
  - Stok `0x0805D3BC` fonksiyonu sayfa durumuna göre 32 bayt döndürürken (Sayfa 0: `buf + 0`, Sayfa 1: `buf + 0x20`), 32-adım birleştirici mimarisinde:
    - İlk 16 kayıt (1–16. adımlar): üst 16 pad'e (`grid_output + 0x00`),
    - İkinci 16 kayıt (17–32. adımlar): alt 16 pad'e (`grid_output + 0x20`) aktarılır.
  - Playhead 0'dan 31'e kesintisiz aktığında, üst satırdan alt satıra geçişte (Adım 15 -> 16) gecikme veya kopma olmaksızın 32 pad boyunca akar; alt yarıda iken üst padlerde, üst yarıda iken alt padlerde playhead çiftlenmesi oluşmaz.
- **Mod Bağımsızlığı ve Orijinal Alt Pad Korunumu:**
  - Kullanıcı Note (`mode 0` alt view) veya Velocity (`mode 2`, `[grid + 0x9C]`) moduna geçtiğinde, Grid Compositor alt 16 pad'e Step View'ın ikinci yarısı yerine o modun orijinal LED tamponunu (`bottom_view + r7`) yansıtır.
  - Grid Container `[grid + 0x258]` track store dizisi ve `0x080588AC` kontrol fonksiyonu doğrulanarak mod geçişlerinde bellek bütünlüğü tam olarak sağlandı.

## Değişen dosyalar

- `tests/test_led_compositor.py` (yeni; 32 adım LED birleştirici, playhead akışı ve mod koruma testleri, 5 test)
- `docs/UI-TRACE-5706.md` (güncellendi; compositor, LED getter, renk motoru durum bitleri ve adres haritası)
- `CHANGELOG.md` (güncellendi)
- `docs/STATUS.md` (güncellendi)

Geçici yapay çıktılar (`build/`, `logs/`) `.gitignore` altında korunmaktadır. Stock dosyalara dokunulmamıştır.

## Başarısız denemeler ve açık sınırlar

- `test_led_compositor.py` ilk çalıştırmasında `step_led_cell` adresi `view + 0x74` durum sözcükleri dizisi içerisine denk getirildiğinden Step 6 yazılırken pointer ezilmiş ve Step 7'de unmapped write hatası oluşmuştur; pointer nesne dışına taşınarak sorun çözülmüş ve mimari sınır netleştirilmiştir.
- `mode = 2` (Velocity) çalıştırılırken `[grid + 0x258]` alanının `0x080588AC` tarafından track store dizisi olarak okunduğu tespit edilmiş ve sentetik fixture buna göre tamamlanmıştır.
- Fiziksel cihaza hiçbir firmware gönderilmedi, komut iletilmedi veya MIDI/USB bağlantısı açılmadı.
- Testler sentetik RAM emülasyonu ile sınırlandırılmıştır; donanım tarama zamanlaması ve RTOS thread etkileşimi henüz fiziksel cihazda ölçülmemiştir.

## Sonraki tek somut görev

32 Pad Yönlendirmesi (Adım 4) ve 32 Adım LED Birleştirici (Adım 5) mantığının entegre mikro-yama tasarımına dönüştürülmesi ve Sequencer Only modu geçiş tuş kombinasyonu hazırlığı.
