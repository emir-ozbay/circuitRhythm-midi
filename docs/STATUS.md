# Devralma durumu

25 Ekim 2026. **M0 tamamlandı. M1 tamamlandı. M2 Adım 2 (Patcher Aracı) ve Adım 3 (Sentetik Doğrulama ve Cihaz Testi Teklifi) tamamlandı. Adım 4 (32 Pad Step Yönlendirmesi, Sayfa Mantığı ve Taşma Koruması) tamamlandı.**
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
| `tests/test_step_routing.py` (5 test) | PASS (5/5) | Stok container yönlendirmesi, `step >= 32` taşma ve bellek bozulma kanıtları (`view+0xB4`, ST1/ST2 parametre ezilmeleri), güvenli 32-pad tam döngü (tüm 32 adım ON/OFF ve commit), sınır ötesi çoklu basış ve clamping maskeleme doğrulandı. |
| `tests/test_patcher.py` (15 test) | PASS (15/15) | Güvenlik sınırları, bozuk hash reddi, çakışma engeli, kayıpsız roundtrip ve tam durum RAM emülasyonu (`test_pad_press_synthetic_ram_full_state_comparison`) doğrulandı. |
| `tests/test_ui_contracts.py` (7 test) | PASS (7/7) | UI kontratları, step press/release yaşam döngüsü ve sahiplik sınırları regresyon görmedi. |
| `scripts/verify_m2_candidate.py` | PASS | 32 adımın tamamında (0..31) Unicorn sentetik RAM emülasyonu: basılı adım LED'i palet 31'den 30'a değişti; kalan 31 LED ve 20.800 baytlık pattern belleği %100 korundu. |
| `scripts/patch_firmware.py --candidate-m2` | PASS | `build/circuitrhythm-5706-m2-candidate.syx` (SHA-256 `8c6996e2...`, CRC `0x2DBD7611`) ve manifest üretildi. İmajda yalnız 1 bayt değişti (`0x0805CF68`: `1f` -> `1e`). |
| `scripts/run_ui_audit.py` | PASS | UI audit sentetik RAM ve statik kanıtları doğrulandı (`logs/ui-audit-.../`). |
| `scripts/run_baseline.py` | PASS | Host baseline testleri eksiksiz geçti (`logs/baseline-.../`). |

## Yeni kesin bulgular

- **Step View 32 Adım Nativ Kapasitesi:**
  - Step View iç mimarisi (`view + 0x74..0xB2` durum sözcükleri, `view + 0xB8` bekleyen toggle maskesi, `view + 0xC0` basılı pad maskesi, 64-baytlık mantıksal LED tamponu, ST1 ve ST2 32-entry dizileri) 32 adımı (`0..31`) yerel olarak desteklemektedir.
  - Stok kodda 16 adımla sınırlı kalınmasının yegane sebebi, Grid Container'ın (`0x0804DC86`) `pad >= 16`'yı alt görünüme yönlendirmesi ve Step View'ın (`0x0805CB04` / `0x0805CCF0`) sayfa durumuna göre (`[view + 0x60] != 0`) yerel pad'e `+16` ofset eklemesidir.
- **İndeks Taşması (`step >= 32`) ve Bellek Tahribatı Kanıtı:**
  - Eğer alt 16 pad (`16..31`) Step View'a yönlendirilirken sayfa ofseti (`+16`) uygulanırsa, `step = 16..31 + 16 = 32..47` indeksleri oluşur.
  - Bu taşmanın doğurduğu üç kritik bellek hasarı Unicorn ile somut olarak kanıtlanmıştır:
    1. `view + 0x74 + 2 * 32 = view + 0xB4`: Durum biti 3 (`0x08`), Step View'ın `0xB4` ikincil/temizleme kontrol baytını ezer. `0x0805D020` sonraki basışta `view + 0x38` fonksiyon pointer'ını çalıştırmayı deneyerek unmapped erişim hatası ve crash üretir.
    2. ST2 Parametre Ezilmesi: Note setter'ı (`0x08054A5C`), `step=32` yazımında word hesabı (`32 >> 2 = 8`) sebebiyle Word 8'e yazar; bu da Step 0'ın Gate uzunluğudur. Pattern commit edildiğinde Step 0'ın Gate uzunluğu bozulur.
    3. ST1 Parametre Ezilmesi: Velocity setter'ı (`0x080549B0`), `step=32` yazımında Word 8'e yazar; bu da Step 0'ın Probability değeridir. Pattern commit edildiğinde Step 0'ın Probability değeri bozulur.
    4. LED buffer taşması: 64 baytlık tampon aşılır, heap'te bitişik alanlar ezilir.
- **32-Pad Sequencer Modu Güvenli Yönlendirme Tasarımı:**
  - Tüm 32 pad basışı (`0..31`) Step View'a aktarılır.
  - Pad indeksi doğrudan adım indeksi olarak ele alınır (`step == pad`).
  - Step View için sayfa ofseti sıfırlanır / izole edilir (`page == 0`).
  - Yönlendirme katmanında `pad & 0x1F` maskesi uygulanarak 31 üstü indeks girişi kesin olarak engellenir.
  - 32 adımın tamamında (0..31) ON ve OFF döngüleri, pattern commit ve LED palet güncellemeleri hatasız çalışır (`view + 0xB4` tamamen korunur).

## Değişen dosyalar

- `tests/test_step_routing.py` (yeni; 32 pad yönlendirme, sayfa mantığı ve taşma koruması testleri, 5 test)
- `docs/UI-TRACE-5706.md` (güncellendi; adres haritası, yeni testler ve mimari sınırlar eklendi)
- `CHANGELOG.md` (güncellendi)
- `docs/STATUS.md` (güncellendi)

Geçici yapay çıktılar (`build/`, `logs/`) `.gitignore` altında korunmaktadır. Stock dosyalara dokunulmamıştır.

## Başarısız denemeler ve açık sınırlar

- `view + 0xB4` alanının kontrol yapısı incelenirken, bu alana doğrudan sahte değer yazıldığında `0x0805D020` fonksiyonunun `view + 0x38` pointer'ını çağırmaya çalıştığı ve çöktüğü görülmüştür; alanın normal durumda `0x00` kalması gerektiği kanıtlanmıştır.
- Fiziksel cihaza hiçbir firmware gönderilmedi, komut iletilmedi veya MIDI/USB bağlantısı açılmadı.
- Testler sentetik RAM emülasyonu ile sınırlandırılmıştır; donanım tarama zamanlaması ve RTOS thread etkileşimi henüz fiziksel cihazda ölçülmemiştir.

## Sonraki tek somut görev

M3/M4 Hazırlığı: Grid Container (`0x0804DC86` / `0x0804DF3E`) ve Step View sayfa ofseti için 32-pad yönlendirme mikro-yama tasarımının formüle edilmesi ve sentetik testlerle doğrulanması.
