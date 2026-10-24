# Changelog

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
