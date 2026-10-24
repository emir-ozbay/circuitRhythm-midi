# Changelog

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
