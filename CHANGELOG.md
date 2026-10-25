# Changelog

## 32 Adım LED Grid Birleştirici (Compositor) ve Playhead Gösterimi (Adım 5) — 2026-10-25
- Grid LED compositor fonksiyonu (`0x0804DD1C`), Step View LED getter yapısı (`0x0805D3BC`), Step renk motoru (`0x0805CF24`) ve yardımcı alt görünüm fonksiyonları (`0x080588AC`, `0x080588EE`, `0x0804DCB2`, `0x0804DB78`) tersine mühendislikle çözümlendi.
- Step View LED renk motoru (`0x0805CF24`) ve durum bayrakları dizisi (`view + 0x74 + 2 * step`) incelendi:
  - Durum biti 0'ın (`0x0001`) Playhead (playback cursor) olduğu Unicorn ile kesin olarak kanıtlandı.
  - Palet eşlemesi: Boş adımda parlak imleç `0x001B`, dolu adımda (hit) parlak vuruş imleci `0x001A`; imleç yokken boş adım `0x0019` (sönük), dolu adım `0x0018` (aktif renk).
- 32 Adım LED Grid Birleştirici (Compositor) mimarisi sentetik RAM'de kuruldu ve doğrulandı:
  - Step View'ın mantıksal LED tamponu yerel olarak 32 adımı (64 bayt) eksiksiz tutar.
  - İlk 16 kayıt (1–16. adımlar): üst 16 pad'e (`grid_output + 0x00`),
  - İkinci 16 kayıt (17–32. adımlar): alt 16 pad'e (`grid_output + 0x20`) `0x08022CF0` (memcpy) ile birleştirilir.
- Playhead (playback cursor) imlecinin 1'den 32'ye kesintisiz akışı Unicorn sentetik RAM'de 32 adım boyunca adım adım simüle edildi:
  - Üst satırdan alt satıra geçişte (Adım 15 -> 16) kesinti, gecikme veya imleç kopması olmadan akış kanıtlandı.
  - Cursor üst yarıdayken alt yarıda, alt yarıdayken üst yarıda kesin izolasyon doğrulandı (asla çift yanma oluşmaz).
- Mod bağımsızlığı ve orijinal alt pad koruma doğrulaması:
  - Note (`mode 0` alt görünümü) veya Velocity (`mode 2`, `[grid + 0x9C]`) moduna geçildiğinde alt 16 pad'in o modun kendi alt subview LED tamponunu (`bottom_view + r7`) yansıttığı ve pad düzeninin bozulmadığı bayt bayt kanıtlandı.
  - Grid Container `[grid + 0x258]` track store dizisi ve `0x080588AC` kontrol akışı tespit edilerek sentetik ortama entegre edildi.
- `tests/test_led_compositor.py` test paketi eklendi (5 yeni kapsamlı test, toplam test sayısı 32'ye yükseldi; 32/32 test PASS):
  - `test_stock_step_view_led_getter_and_compositor_split`: Stok getter ve compositor ayrım mekanizması.
  - `test_step_view_32step_logical_led_buffer_mapping`: 32 adımlık mantıksal LED tamponunun 32 pad ile 1-e-1 eşlenmesi.
  - `test_playhead_continuous_flow_across_32_steps`: Playhead'in 1'den 32'ye kesintisiz akışı ve satır izolasyonu.
  - `test_other_modes_preserve_original_bottom_pad_layout`: Note ve Velocity modlarında alt pad orijinal düzeninin korunması.
  - `test_compositor_memory_safety_and_no_overflow`: Compositor bellek güvenliği, sınır koruması ve `view + 0xB4` bütünlüğü.
- `docs/UI-TRACE-5706.md` ve `docs/STATUS.md` güncellendi.
- Fiziksel donanıma hiçbir erişim yapılmadı.

## 32 Pad Step Yönlendirmesi (Routing), Sayfa Mantığı ve Taşma Koruması (Adım 4) — 2026-10-25
- Grid Container alt/üst yönlendirmesi (`0x0804D7A0` / `0x0804D7DE`, `0x0804DC86`, `0x0804DF3E`) ve Step View sayfa ofseti (`0x0805CB04`, `0x0805CCF0`) detaylı incelendi.
- Step View bellek yapısının (`view + 0x74..0xB2` durum dizisi, `view + 0xB8` pending maskesi, `view + 0xC0` held maskesi, 64 bayt LED tamponu, ST1 ve ST2 32-entry dizileri) 32 adımı yerel olarak zaten barındırdığı; sorunun Grid Container'ın `pad >= 16`'yı alt görünüme yönlendirmesi ve Step View'ın sayfa durumunda eklediği `+16` ofsetinden kaynaklandığı ortaya kondu.
- `step >= 32` taşmasının yol açtığı kritik bellek bozulmaları Unicorn emülasyonu ve bayt analizleriyle kesin olarak kanıtlandı:
  - Durum dizisi taşması (`view + 0x74 + 2 * 32 = view + 0xB4`): `view + 0xB4` kontrol baytı üzerine durum biti 3 (`0x08`) yazılır; `0x0805D020` sonraki basışta `view + 0x38` fonksiyon pointer'ını çağırıp unmapped bellek hatasına ve sistem çökmesine yol açar.
  - ST2 parametre ezilmesi: `0x08054A5C` Note setter'ına `step=32` verildiğinde `step >> 2 = 8` hesaplamasıyla Word 8'e yazılır; bu da Step 0'ın Gate uzunluğunu ezer ve pattern belleğine bozuk commit edilir.
  - ST1 parametre ezilmesi: `0x080549B0` Velocity setter'ına `step=32` verildiğinde Word 8'e yazılır; bu da Step 0'ın Probability değerini ezer ve pattern belleğine bozuk commit edilir.
  - 64-baytlık LED renk buffer'ı sınır aşımı.
- 32 Pad Sequencer Modu güvenli yönlendirme tasarımı formüle edildi:
  - Tüm 32 pad (`0..31`) Step View'a yönlendirilir.
  - Pad indeksi doğrudan adım indeksiyle 1:1 eşlenir (`step == pad`).
  - Step View için sayfa ofseti 0'a sabitlenir / izole edilir.
  - Yönlendirme katmanında `pad & 0x1F` maskesi uygulanarak 31 üstü geçersiz indeksler engellenir.
- `tests/test_step_routing.py` test modülü eklendi (5 yeni kapsamlı test, toplam test sayısı 27'ye yükseldi; tüm testler PASS):
  - `test_stock_container_routing_split`: Stok grid ayrımı ve sayfa dönüşümü.
  - `test_step_index_overflow_hazard_and_corruption_proof`: `view + 0xB4`, ST1 ve ST2 bellek bozulma kanıtları.
  - `test_safe_32pad_full_lifecycle_all_steps`: 32 adımın tamamında (0..31) ON ve OFF döngüleri, kontrol bloğu bütünlüğü, pattern commit ve LED palet güncellemeleri.
  - `test_cross_boundary_concurrent_press_and_release`: Sınır ötesi (pad 15 ve 16) eşzamanlı basış/bırakış ve bağımsız commit doğrulaması.
  - `test_routing_guard_clamping_prevents_overflow`: Sınır dışı girişlerin güvenli maskelenmesi.
- `docs/UI-TRACE-5706.md` ve `docs/STATUS.md` güncellendi.
- Fiziksel donanıma hiçbir erişim yapılmadı.

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
