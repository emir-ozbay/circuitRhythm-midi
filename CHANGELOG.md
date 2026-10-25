# Changelog

## Güvenli Heap Durum Bloğu (`c_seq_state`) ve Thumb-2 Üretici (M3 Adım 2) — 2026-10-25
- `src/thumb_asm.py` oluşturuldu:
  - `analysis/sources/CIRCUIT-REMIX/tools/thumb.py` içindeki MIT lisanslı Thumb-2 assembler yardımcıları (MIT lisans bildirimi korunarak) ve ek `bl`, `b_w`, `push`, `pop`, `ldr`, `str`, `ldrb`, `strb`, `movw`, `movt`, `str_reg`, `ldr_reg` yardımcıları temiz bir modül olarak taşındı.
- `src/seq_Patch.py` oluşturuldu:
  - `CODE_CAVE_BASE = 0x0806A570`, `HEAP_LIMIT_PTR = 0x20002B54` (stok `0x2004F760`), `HEAP_CUR_PTR = 0x20002B58` sabitleri tanımlandı.
  - Güvenli 256 baytlık RAM durum bloğu `SEQ_STATE_ADDR = 0x2004F660` (`0x2004F760 - 256`), `SEQ_STATE_MAGIC = 0x31514553` (`"SEQ1"`) ve ofset tablosu (`+0x00` `magic`, `+0x04` `seq_enabled`, `+0x05` `last_normal_proj`, `+0x06` `last_seq_proj` varsayılan `32`, `+0x08` `grid_ptr`) tanımlandı.
  - `c_seq_state()` fonksiyonunu Thumb-2 makine kodu olarak üreten `emit_seq_state()`, `arm_code()` ve `c_seq_state()` fonksiyonları yazıldı.
- `tests/test_seq_state.py` oluşturuldu:
  - Capstone disassembly doğrulaması ve Unicorn emülatöründe 8 kapsamlı test (`TestThumbAsmEncodings`, `TestSeqStateEmulation`) eklendi; toplam 46 testin tamamı PASS oldu.

## Code Cave Desteği ve Genişletilmiş Patcher (M3 Adım 1) — 2026-10-25
- `scripts/patch_firmware.py` aracı `[0x0806A570, 0x08080000)` uygulama boş flash alanını (code cave) destekleyecek şekilde güncellendi:
  - `FLASH_END = 0x08080000` ve `MAX_IMAGE_SIZE = 0x70000` (458.752 bayt) sabitleri eklendi.
  - `validate_patch_ranges`: `[0x08010200, 0x08080000)` aralığını denetler; `0x0806A570` stok sınırını ortadan kesen yamaları (`p.address < APP_END and p.end_address > APP_END`) ve code cave alanında `0xFF` harici bayt bekleyen yamaları kesin olarak `AddressBoundsError` ile reddeder.
  - `apply_patches`: Uzatma yamalarında imajı `0xFF` ile gereken adrese kadar genişletir, unprogrammed `0xFF` baytlarını doğrular, yamayı yazar ve imaj boyutunu 4 baytlık word hizasına (`(-len) % 4`) `0xFF` ile yuvarlar.
  - `pack_syx` & `unpack_syx`: `STOCK_IMAGE_SIZE` ile `FLASH_END - APP_BASE` arasındaki 4-byte hizalı imaj boyutlarını destekler; SysEx header'ına güncel boyut ve MPEG-2 CRC-32 yazar. `unpack_syx` fonksiyonuna `allow_extended: bool = False` parametresi eklendi.
- `tests/test_patcher.py`: 6 yeni test (`TestCodeCaveSupport`) eklenerek toplam 21 patcher testi ve 38 entegrasyon testi PASS oldu (`0x0806A56E` sınır kesme, boyut/hizalama, CRC ve round-trip doğrulamaları).

## Kapsam Kesinleştirme ve Projects/Grid-Mode Makine Kodu Haritalaması — 2026-10-25
- Kullanıcı kararları doğrultusunda proje kapsamı (`docs/SCOPE.md`, `docs/ROADMAP.md`, `AGENTS.md`, `README.md`, `docs/STATUS.md`) güncellendi:
  - 64 adım hedefi kalıcı olarak kapsam dışına çıkarıldı; 32 adım mimarisi kesinleştirildi.
  - Serbest polifoni yerine Faz 2 hedefi olarak "Root Nota + Macro Knob ile Akor/Triad Üretici" tanımlandı.
  - Stok Projects ekranı (`0x0804F080`, `0x0804F09E`, `0x0804F12C`, `0x0804F27E`) ve buton/ekran modu dönüşüm tablosu (`0x0803E2D8`, `0x0803DB2E`) disassembly ile çözümlendi:
    - `[proj_view + 0x36]` baytının 64 projeyi iki adet 32-projelik sayfaya (`0`: 1–32, `1`: 33–64) ayırdığı kanıtlandı.
    - Normal modda `sayfa 0`, Sequencer modunda `sayfa 1` kilitlenerek 32 bağımsız Sequencer projesi (orijinal New, Save, Duplicate, Clear destekli) sağlanması planlandı.
  - Geliştirme sürecinin Unicorn emülatöründe tamamlanıp, tüm Faz 1 özelliklerinin tek bir birleşik pakette (M7) ilk gerçek cihaz testine sunulması kararlaştırıldı.

## 32 Adım LED Grid Birleştirici (Compositor) ve Playhead Gösterimi (Adım 5) — 2026-10-25
- Grid LED compositor fonksiyonu (`0x0804DD1C`), Step View LED getter yapısı (`0x0805D3BC`), Step renk motoru (`0x0805CF24`) ve yardımcı alt görünüm fonksiyonları (`0x080588AC`, `0x080588EE`, `0x0804DCB2`, `0x0804DB78`) tersine mühendislikle çözümlendi.
- Step View LED renk motoru (`0x0805CF24`) ve durum bayrakları dizisi (`view + 0x74 + 2 * step`) incelendi:
  - Durum biti 0'ın (`0x0001`) Playhead (playback cursor) olduğu Unicorn ile kesin olarak kanıtlandı.
  - Palet eşlemesi: Boş adımda parlak imleç `0x001B`, dolu adımda (hit) parlak vuruş imleci `0x001A`; imleç yokken boş adım `0x0019` (sönük), dolu adım `0x0018` (aktif renk).
- 32 Adım LED Grid Birleştirici (Compositor) mimarisi sentetik RAM'de kuruldu ve doğrulandı:
  - Step View'ın mantıksal LED tamponu yerel olarak 32 adımı (64 bayt) eksiksiz tutar.
  - İlk 16 kayıt (1–16. adımlar): üst 16 pad'e (`grid_output + 0x00`),
  - İkinci 16 kayıt (17–32. adımlar): alt 16 pad'e (`grid_output + 0x20`) `0x08022CF0` (memcpy) ile birleştirilir.
- Playhead (playback cursor) imlecinin 1'den 32'ye kesintisiz akışı Unicorn sentetik RAM'de 32 adım boyunca adım adım simüle edildi.
- Mod bağımsızlığı ve orijinal alt pad koruma doğrulaması (`tests/test_led_compositor.py`, 5 test PASS).

## 32 Pad Step Yönlendirmesi (Routing), Sayfa Mantığı ve Taşma Koruması (Adım 4) — 2026-10-25
- Grid Container alt/üst yönlendirmesi (`0x0804D7A0` / `0x0804D7DE`, `0x0804DC86`, `0x0804DF3E`) ve Step View sayfa ofseti (`0x0805CB04`, `0x0805CCF0`) detaylı incelendi.
- `step >= 32` taşmasının yol açtığı kritik bellek bozulmaları (`view + 0xB4`, ST1 ve ST2 parametre örtüşmeleri) Unicorn emülasyonu ve bayt analizleriyle kesin olarak kanıtlandı (`tests/test_step_routing.py`, 5 test PASS).

## M2 İlk Mikro Yama Adayının Sentetik Doğrulanması ve Cihaz Testi Teklifi (M2 Step 3) — 2026-10-25
- Unicorn emülasyonu ile 32 adımın tamamında (adım 0..31) aynı RAM durumunda kapsamlı karşılaştırma yapıldı (`scripts/verify_m2_candidate.py`, `docs/M2-DEVICE-TEST-PROPOSAL.md`).

## Güvenli Firmware Yama (Patcher) Aracı ve Testleri (M2 Step 2) — 2026-10-24
- `scripts/patch_firmware.py` ve `tests/test_patcher.py` (15 test PASS) geliştirildi.

## Step Press/Release döngüsü ve sahiplik doğrulaması (M1 Step 1) — 2026-10-24
- `0x0805CB04` (step press) ve `0x0805CCF0` (step release) fonksiyonları sentetik RAM Unicorn test ortamında birleştirildi (`tests/test_ui_contracts.py`, 7 test PASS).

## Handoff 2026-10-24
- Kullanıcıya özel stock 5706, kaynak snapshot'ları, raporlar ve sınırlı emülasyon testleri paketlendi.
