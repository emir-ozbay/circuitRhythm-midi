# Devralma durumu

24 Ekim 2026. **M0 tamamlandı. M1 (UI yaşam döngüsü ve sınır adımları) tamamlandı. M2 Adım 2 (Güvenli Firmware Patcher Aracı ve Testleri) tamamlandı. Test edilen M2 adayı SysEx build/ altında üretildi, fiziksel cihaza gönderilmedi.**
Güncel sınır 32 adım; 64 adım, polifoni ve Elektron davranışları geliştirilmedi.

## Ortam ve bütünlük

- Dosya değişikliklerinden önce PowerShell hash kontrolü ve ardından `python scripts/check_package.py`: **PACKAGE PASS, 55 dosya**. Manifest dijital imza değildir.
- Stock: 508861 bayt; SHA-256 `11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf`. Stock/reference dosyaları değiştirilmedi; provenance'daki 24 upstream dosya yeniden doğrulandı.
- Windows AMD64 build **26200.9711**, DisplayVersion **25H2**; CPU **AMD Ryzen 7 3700X 8-Core Processor**.
  Kullanıcının ortamı Windows 11; registry ProductName `Windows 10 Pro`, Python platform çıktısı `Windows-10-10.0.26200-SP0`.
- Python **3.11.9**, MSC v.1938, 64 bit; `.venv` aktif. Capstone paket **5.0.9**, Unicorn **2.1.4**. `-O` kullanılmadı.
- Git **2.53.0.windows.2**. Remote yok. Firmware/build/log/venv/backups ignored kuralları devrede.

## Komutlar ve sonuçlar

Proje kökünde PowerShell, venv ile:

```powershell
.\.venv\Scripts\python.exe scripts/patch_firmware.py --verify-only
.\.venv\Scripts\python.exe scripts/patch_firmware.py --candidate-m2
.\.venv\Scripts\python.exe tests/test_patcher.py -v
.\.venv\Scripts\python.exe tests/test_ui_contracts.py
.\.venv\Scripts\python.exe scripts/run_ui_audit.py
.\.venv\Scripts\python.exe scripts/run_baseline.py
```

| Test Paketi / Script | Sonuç | Gerçekte kanıtladığı |
|---|---|---|
| `scripts/patch_firmware.py --verify-only` | PASS | Stock SysEx hash'i (`11d6...afaf`), 370032 bayt imaj ve MPEG-2 CRC (`0x9EEE802C`) doğrulandı. |
| `scripts/patch_firmware.py --candidate-m2` | PASS | `build/circuitrhythm-5706-m2-candidate.syx` (SHA-256 `8c6996e22eec4848e31696f512ff4a9c0f151a76e37eb05837553c25743cc356`, CRC `0x2DBD7611`) ve manifest üretildi. İmajda yalnız 1 bayt değişti (`0x0805CF68`: `1f` -> `1e`). |
| `tests/test_patcher.py` (14 test) | PASS (14/14) | Hatalı SysEx hash reddi; orijinal dosyaya/stock'a yazma engeli; vektör tablosu (`[0x08010000, 0x08010200)`) ve bootloader (`<0x08010000`) koruması; uygulama sınırı ötesi (`>=0x0806A570`) reddi; çakışan aralık reddi; orijinal bayt uyuşmazlığı iptali; kayıpsız stock SysEx roundtrip; 1 baytlık M2 adayı diff/manifest doğrulaması; Unicorn synthetic RAM üzerinde stok (palet 31) vs yamalı (palet 30) renk dallanma davranış farkı kanıtı. |
| `tests/test_ui_contracts.py` (7 test) | PASS (7/7) | UI kontratları ve yaşam döngüsü regresyon görmedi. |
| `scripts/run_ui_audit.py` | PASS | `logs/ui-audit-20261024T203642223457Z/` |
| `scripts/run_baseline.py` | PASS | `logs/baseline-20261024T203706192812Z/` |

## Yeni kesin bulgular

- **Güvenli yama mekanizması:** `scripts/patch_firmware.py` aracıyla ikili yama (binary patch) süreci tamamen otomatik, denetimli ve hataya kapalı hale getirildi.
  - Vektör tablosu (`[0x08010000, 0x08010200)`) ve Novation başlık/kimlik alanı yama girişimlerine karşı korundu.
  - Orijinal SysEx ve stock firmware dosyalarının üzerine yazma kesin olarak engellendi.
  - Hedef adresteki baytların beklenen baytlarla uyuşmaması durumunda dosya yazımı iptal edildi.
  - SysEx MPEG-2 CRC-32 ve 7-bit blok paketlemesi saf Python implementasyonuyla bağımsız upstream araçları (`syx.py` ve `rh_fw.py`) ile teyit edildi.
- **M2 Adayı Yamalı İmaj Kanıtı:**
  - Tek komutluk `0x0805CF68` (`movs r2, #31` -> `movs r2, #30`) yaması uygulandığında tam olarak 1 bayt değiştiği (`0x0805CF68`: `0x1F` -> `0x1E`), kalan 370031 baytın stok ile birebir aynı kaldığı kanıtlandı.
  - Unicorn emülatöründe basılı adım durumunda (bit 3) stok imajın palet 31 (`0x0055`), yamalı imajın ise palet 30 (`0x001E`) renk kodunu yazdığı ve diğer 31 adımın LED değerlerini etkilemediği test edildi.

## Değişen dosyalar

`scripts/patch_firmware.py` (yeni), `tests/test_patcher.py` (yeni), `CHANGELOG.md`, `docs/STATUS.md`.
Geçici yapay çıktılar (`build/`, `logs/`) `.gitignore` altında korunmaktadır. Stock dosyalara dokunulmamıştır.

## Başarısız denemeler ve açık sınırlar

- `test_patcher.py` içerisindeki synthetic RAM emülasyon testinin ilk taslağında `view+4` LED cell nesnesi eksik eşlendiğinden `UC_ERR_READ_UNMAPPED` oluştu; `test_ui_contracts.py`daki kanıtlanmış fixture yapısı (`view+4 -> cell -> leds`) kullanılarak düzeltildi.
- Fiziksel cihaza hiçbir firmware gönderilmedi, komut iletilmedi veya MIDI/USB bağlantısı açılmadı.
- Üretilen aday firmware'in bootloader tarafından kabul edilip edilmeyeceği veya cihaz açılışında kimlik bloğu uyuşmazlığına yol açıp açmayacağı fiziksel donanımda ölçülmemiştir.
- Recovery prosedürleri donanım üzerinde fiilen icra edilmemiştir.

## Sonraki tek somut görev

M2 Adım 3: Fiziksel donanım testi öncesinde test planının, yedekleme prosedürünün, recovery teyidinin ve kesin hash/manifest bilgilerini içeren onay teklifinin hazırlanması (kullanıcı onayı olmadan cihaza aktarım yapılmayacaktır).
