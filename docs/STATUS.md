# Devralma durumu

25 Ekim 2026. **M0 tamamlandı. M1 tamamlandı. M2 Adım 2 (Patcher Aracı) ve Adım 3 (M2 İlk Mikro Yama Adayının Sentetik Doğrulanması ve Cihaz Testi Teklifi) tamamlandı. Test edilen M2 adayı SysEx `build/` altında üretildi; fiziksel cihaza gönderilmedi.**
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
.\.venv\Scripts\python.exe scripts/patch_firmware.py --candidate-m2
.\.venv\Scripts\python.exe scripts/verify_m2_candidate.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/run_ui_audit.py
.\.venv\Scripts\python.exe scripts/run_baseline.py
```

| Test Paketi / Script | Sonuç | Gerçekte kanıtladığı |
|---|---|---|
| `scripts/patch_firmware.py --candidate-m2` | PASS | `build/circuitrhythm-5706-m2-candidate.syx` (SHA-256 `8c6996e22eec4848e31696f512ff4a9c0f151a76e37eb05837553c25743cc356`, CRC `0x2DBD7611`) ve manifest üretildi. İmajda yalnız 1 bayt değişti (`0x0805CF68`: `1f` -> `1e`). |
| `scripts/verify_m2_candidate.py` | PASS | 32 adımın tamamında (0..31) Unicorn sentetik RAM emülasyonu: basılı adım LED'i palet 31'den 30'a değişti; kalan 31 LED, 20.800 baytlık pattern belleği ve edit buffer'ları %100 bayt bayt korundu. Rapor `logs/m2-verification-.../` altına yazıldı. |
| `tests/test_patcher.py` (15 test) | PASS (15/15) | Güvenlik sınırları, bozuk hash reddi, çakışma engeli, kayıpsız roundtrip ve tam durum RAM emülasyonu (`test_pad_press_synthetic_ram_full_state_comparison`) doğrulandı. |
| `tests/test_ui_contracts.py` (7 test) | PASS (7/7) | UI kontratları ve yaşam döngüsü regresyon görmedi. |
| `scripts/run_ui_audit.py` | PASS | UI audit sentetik RAM ve statik kanıtları doğrulandı (`logs/ui-audit-.../`). |
| `scripts/run_baseline.py` | PASS | Host baseline testleri eksiksiz geçti (`logs/baseline-.../`). |

## Yeni kesin bulgular

- **M2 Mikro Yamasının Sentetik İzolasyon Kanıtı:**
  - Tek komutluk `0x0805CF68` (`movs r2, #31` -> `movs r2, #30`) yaması uygulandığında, imajda tam olarak 1 bayt değiştiği (`0x0805CF68`: `0x1F` -> `0x1E`), kalan 370.031 baytın stok ile birebir aynı kaldığı teyit edildi.
  - Unicorn emülatöründe basılı adım durumunda (bit 3) stok imajın palet 31 (`0x0055`), yamalı imajın ise palet 30 (`0x001E`) renk kodunu yazdığı, 32 adımın tamamında (0..31) test edilerek kanıtlandı.
  - Basış esnasında geriye kalan 31 adımın LED kayıtlarının kesinlikle etkilenmediği, 8 pattern'lik 20.800 bayt pattern belleğinin ve edit buffer'larının (`st1`, `st2`, `selection`, `note`) tek bir bayt dahi değişmeden korunduğu matematiksel olarak doğrulandı.
  - Pad release (bırakma) sonrasında nota bilgisinin pattern belleğine stok kod ile birebir aynı şekilde commit edildiği ve LED'in aktif adım rengine döndüğü kanıtlandı.
- **Cihaz Testi Teklifi ve Kurtarma Hazırlığı:**
  - `docs/M2-DEVICE-TEST-PROPOSAL.md` oluşturuldu.
  - Test SysEx dosya yolu, SHA-256 hash'leri, tek baytlık diff manifesti, donanım öncesi zorunlu yedekleme kontrol listesi (Components + SD kart tam imajı) ve resmî bootloader kurtarma adımları (Sample Rec + Sample + Note) belgelendi.

## Değişen dosyalar

- `tests/test_patcher.py` (genişletildi; `test_pad_press_synthetic_ram_full_state_comparison` eklendi, toplam 15 test)
- `scripts/verify_m2_candidate.py` (yeni; M2 sentetik doğrulama runner'ı)
- `docs/M2-DEVICE-TEST-PROPOSAL.md` (yeni; M2 cihaz testi teklifi, diff, hash ve recovery kontrol listesi)
- `CHANGELOG.md` (güncellendi)
- `docs/STATUS.md` (güncellendi)

Geçici yapay çıktılar (`build/`, `logs/`) `.gitignore` altında korunmaktadır. Stock dosyalara dokunulmamıştır.

## Başarısız denemeler ve açık sınırlar

- 64 baytlık LED dizisi diff kontrolünde, hem palet 31 (`0x0055`) hem de palet 30 (`0x001E`) renk kodlarının yüksek baytı `0x00` olduğundan, 16-bit word farkı bayt seviyesinde 2 değil 1 baytlık fark (`step * 2`) oluşturmaktadır; test beklentisi buna göre netleştirildi.
- Fiziksel cihaza hiçbir firmware gönderilmedi, komut iletilmedi veya MIDI/USB bağlantısı açılmadı.
- Üretilen aday firmware'in bootloader tarafından kabul edilip edilmeyeceği veya cihaz açılışında kimlik bloğu uyuşmazlığına yol açıp açmayacağı fiziksel donanımda ölçülmemiştir.
- Recovery prosedürleri donanım üzerinde fiilen icra edilmemiştir.

## Sonraki tek somut görev

M2 Adım 4: Kullanıcıdan onay alındığı takdirde, `docs/M2-DEVICE-TEST-PROPOSAL.md` yönergelerine uygun olarak yedeklerin alınması ve M2 adayının fiziksel cihaz üzerinde test edilmesi (kullanıcı onayı verilene kadar cihaza yükleme yapılmayacaktır).
