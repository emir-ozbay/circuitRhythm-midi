# Changelog

## M2 İlk Mikro Yama Adayının Sentetik Doğrulanması ve Cihaz Testi Teklifi (M2 Step 3) — 2026-10-25
- Unicorn emülasyonu ile 32 adımın tamamında (adım 0..31) aynı RAM durumunda kapsamlı karşılaştırma yapıldı:
  - Basılan adımın 16-bit LED kaydının stok palet 31'den (`0x0055`) yamalı palet 30'a (`0x001E`) değiştiği doğrulandı.
  - Geriye kalan 31 adımın LED kayıtlarının bayt bayt korunduğu ve stok ile aynı kaldığı kanıtlandı.
  - 8 pattern'in tamamını içeren 20.800 baytlık pattern belleğinin ve edit buffer'larının (`st1`, `st2`, `selection`, `note`) basış sırasında tek bir bayt dahi değişmeden korunduğu kanıtlandı.
  - Bırakma (release) döngüsünde `0x0805CCF0` fonksiyonunun stok ve yamanmış firmware'de aynı şekilde pattern belleğine nota commit ettiği ve LED'leri aktif adım rengine güncellediği bayt bayt kanıtlandı.
- `tests/test_patcher.py` içine `test_pad_press_synthetic_ram_full_state_comparison` testi eklendi (patcher testleri 15'e, test paketi toplamı 22'ye yükseldi; tüm testler PASS).
- `scripts/verify_m2_candidate.py` geliştirildi; hash, binary diff, vektör tablosu ve 32 adımlık Unicorn emülasyonu çalıştırılarak `logs/m2-verification-<timestamp>/verification_report.json` raporu üretildi.
- `docs/M2-DEVICE-TEST-PROPOSAL.md` belgesi hazırlandı; test SysEx'i (`build/circuitrhythm-5706-m2-candidate.syx`, SHA-256 `8c6996e2...`), diff/manifest ayrıntıları, donanım öncesi yedekleme önkoşulları ve kurtarma adımları dokümante edildi.
- Fiziksel cihaza hiçbir firmware gönderilmedi veya donanım erişimi yapılmadı.

## Güvenli Firmware Yama (Patcher) Aracı ve Testleri (M2 Step 2) — 2026-10-24
- `scripts/patch_firmware.py` geliştirildi:
  - Giriş SysEx dosyasının SHA-256 (`11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf`) ve çıkarılan binary imaj hash'inin zorunlu doğrulanması sağlandı; geçersiz veya bozuk girdiler reddedildi.
  - Hedef dosya güvenliği: Orijinal SysEx veya girdi dosyası üzerine yazma engellendi; çıktılar `build/` altına yönlendirildi.
  - Adres sınır denetimi: Yalnızca uygulama yazılabilir alanı (`[0x08010200, 0x0806A570)`) izinli kılındı; bootloader (`<0x08010000`), Cortex-M vektör tablosu ve kimlik alanı (`[0x08010000, 0x08010200)`) ile uygulama sonu ötesi yazma girişimleri kesin olarak engellendi.
  - Orijinal bayt kontrolü (assert original bytes): Hedef adresteki baytlar beklenenden farklıysa işlem iptal edilir.
  - Çakışan aralık denetimi (reject overlapping ranges): Birden fazla yama verildiğinde kesişen aralıklar tespit edilip reddedilir.
  - Saf Python MPEG-2 CRC-32 ve SysEx paketleyici (`pack_syx` / `unpack_syx`): Novation INIT, HEADER, WRITE ve FINISH (vektör bloğu) mesajlarını hatasız ayrıştırıp yeniden üreten ve bağımsız upstream araçlarıyla doğrulanan kod eklendi.
  - Ayrıntılı manifest JSON raporu üretimi: Girdi/çıktı dosya yolları, SHA-256 hash'leri, CRC-32 değerleri, bayt farkları ve güvenlik teyitleri raporlanır.
- `tests/test_patcher.py` yazıldı ve 14 kapsamlı test eklendi:
  - Hash doğrulama ve bozuk girdi reddi.
  - Orijinal dosyaya yazma engeli.
  - Vektör tablosu, bootloader ve sınır dışı adres reddi.
  - Çakışan aralık ve orijinal bayt uyuşmazlığı reddi.
  - Stok imajın kayıpsız (bit-identical) SysEx roundtrip teyidi.
  - M2 aday yaması (`0x0805CF68`: `1f 22` -> `1e 22`) ile tam olarak 1 baytlık diff oluşumu ve manifest teyidi.
  - Unicorn sentetik RAM emülasyonunda stok kodun palet 31 (`0x0055`), yamalı kodun ise palet 30 (`0x001E`) renk word'ü yazdığının kanıtlanması.

## Step Press/Release döngüsü ve sahiplik doğrulaması (M1 Step 1) — 2026-10-24
- `0x0805CB04` (step press) ve `0x0805CCF0` (step release) fonksiyonları sentetik RAM Unicorn test ortamında birleştirildi.
- Sınır adımları 0, 15, 16 ve 31 için iki tam toggle döngüsü doğrulandı: basışta held bit 3 ve LED palet 31 aktivasyonu; bırakışta toggle, pattern commit, hit bit 1 aktivasyonu, timer 6 durdurma ve observer üzerinden held bit 3'ün temizlenmesi.
- Basılı tutarken sayfa veya track değiştirildiğinde step sahipliğinin (step ownership) nasıl korunduğu ve öksüz (orphaned) kaldığı kanıtlandı.
- `scripts/run_ui_audit.py` 7 davranış testi ve yeni disassembly pencereleri (`0x0805cffe`, `0x0805d3f8`, `0x0805ce48`) ile güncellendi.
- `docs/UI-TRACE-5706.md` ve `docs/STATUS.md` güncellendi.

## Kapsam ve dokümantasyon senkronizasyonu — 2026-10-24
- Proje köküne `README.md` eklendi; temel amaç, kapsam, mevcut teknik durum ve güvenlik kuralları güncellendi.
- `docs/SCOPE.md` güncellendi ve ürün hedefleriyle birebir uyumlu hale getirildi.
- `docs/STATUS.md` güncellendi.

## Yerel doğrulama ve M1 incelemesi — 2026-10-24
- Windows Python 3.11.9 ortamında baseline tekrar üretildi; cihaz erişimi yapılmadı.
- Stock pad routing, setter/notify/commit ve LED observer için sentetik RAM davranış testleri eklendi.
- Tekrarlanabilir UI audit runner, adres haritası ve tek komutluk renk denemesi kapsam taslağı eklendi.
- Upstream/reference checkout baytları korundu; dump/capture/kişisel proje ignore kuralları eklendi.
- Firmware veya 32/64 adım modu üretilmedi.

## Handoff 2026-10-24
- Kullanıcıya özel stock 5706, kaynak snapshot'ları, raporlar ve sınırlı emülasyon testleri paketlendi.
- Güncel hedef: 32 adım; ileride 64. Custom firmware henüz uygulanmadı.
- Salt bilgisayar baseline runner, paket hash kontrolü ve Windows başlangıç scriptleri eklendi.
