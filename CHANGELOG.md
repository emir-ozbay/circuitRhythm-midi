# Changelog

## Pad Basılı Tutarken Track veya Ekran Değişiminde Sahiplik Temizliği (M4 Adım 5) — 2026-10-25
- `src/seq_patch.py` (ve `src/seq_Patch.py`) güncellendi:
  - `STOCK_GRID_MODE_UPDATE = 0x0804DAAC` ve `STOCK_STEP_LED_CALC = 0x0805CF24` sabitleri eklendi.
  - `HOOK_GRID_MODE_CLEANUP = 0x0804D6E0` (`EXPECTED_GRID_MODE_CLEANUP = 00 f0 e4 f9`, `bl #0x804daac`) kanca sabiti eklendi.
  - `emit_grid_mode_cleanup(a: Asm)` fonksiyonu eklendi:
    - Grid Container mod/track güncelleme fonksiyonu `0x0804D6B6` içindeki `0x0804D6E0` çağrısına bağlandı.
    - Orijinal `0x0804DAAC` fonksiyonunu çağıran 5. stack argümanını güvenle iletip çalıştırır.
    - `[r5 + 0x228]` (Grid fiziksel basılı pad maskesi) sıfırlanır.
    - 8 track (`t = 0..7`) taranarak `view = [r5 + 0x74 + 4*t]` kontrol edilir; `view != 0` ve basılı adım varsa (`[view + 0xB8] != 0` veya `[view + 0xC0] != 0`):
      - `[view + 0xB8] = 0` (pending toggle maskesi) ve `[view + 0xC0] = 0` (held pad maskesi) temizlenir.
      - 32 adım (`s = 0..31`) taranarak `view + 0x74 + 2*s` durum word'ünde `bit 3` (`0x0008`, held) set ise `bic` ile temizlenir ve `0x0805CF24(view, s)` ile adımın LED rengi normale döndürülür.
    - Fonksiyon çıkışında çağrıcının yazmaçları (`r4..r8, pc/lr`) eksiksiz geri yüklenir.
  - `build_step_routing_patches()`: 9 in-place Thumb-2 `BL` kancasını ve code cave yamasını üretir.
- `tests/test_step_routing.py` güncellendi:
  - `test_patched_hooks_and_code_cave_disassembly`: 9 in-place `BL` kancasını ve code cave yerleşimini Capstone ile doğrular.
  - `test_held_pad_ownership_cleanup_on_track_or_mode_change`: Pad 5 (üst satır) basılıyken track değiştirildiğinde ve Pad 20 (alt satır) basılıyken `grid_mode = 2` (Velocity) yapıldığında `grid + 0x228`, `view + 0xB8`, `view + 0xC0` ve durum biti 3'ün tertemiz sıfırlandığı, LED'in parlak beyazdan normal renge döndüğü Unicorn ile kanıtlandı.
- Toplam test sayısı 59'dan **60'a yükseldi** ve tüm testler PASS oldu.

## 32-Adım LED Compositor Makine Kodu Yaması (M4 Adım 4) — 2026-10-25
- `src/seq_patch.py` (ve `src/seq_Patch.py`) güncellendi:
  - `HOOK_COMP_TOP_LEDS = 0x0804DDA4` (`EXPECTED_COMP_TOP_LEDS = 04 f0 b0 f9`, `bl #0x8052108`) ve `HOOK_COMP_BOTTOM_MEMCPY = 0x0804DDBE` (`EXPECTED_COMP_BOTTOM_MEMCPY = d4 f7 97 ff`, `bl #0x8022cf0`) sabitleri eklendi.
  - `c_comp_top_leds`: Stok Compositor (`0x0804DD1C`) içinde `0x0804DDA4` noktasına bağlandı. `seq_enabled == 1` ve `grid_mode == 0` (`[r6 + 0x264] == 0`) iken Step View LED tamponunun başını (`ldr r0, [sb, #4]; ldr r0, [r0]`) döndürür; aksi halde orijinal `0x08052108(sb)` çağırır.
  - `c_comp_bottom_memcpy`: Stok Compositor (`0x0804DD1C`) içinde `0x0804DDBE` noktasına bağlandı. `seq_enabled == 1` ve `grid_mode == 0` iken `r1` kaynak adresini Step View'ın ikinci 16 adımıyla (`ldr r1, [sb, #4]; ldr r1, [r1]; adds r1, #0x20`) güncelleyip `0x08022CF0(r0, r1, 0x20)` (`memcpy`) çağırır; aksi halde `r1`'e dokunmadan orijinal `0x08022CF0(r0, r1, 0x20)` çağırır.
  - `build_step_routing_patches()`: 8 adet in-place 4-baytlık Thumb-2 `BL` kancası (`0x0804D7B6`, `0x0804D7CC`, `0x0804D7FC`, `0x0804D812`, `0x0805CB14`, `0x0805CCFA`, `0x0804DDA4`, `0x0804DDBE`) ve genişletilmiş code-cave yamasını üretir.
- `tests/test_step_routing.py` güncellendi:
  - `test_patched_hooks_and_code_cave_disassembly`: Capstone ile 8 in-place `BL` kancasının tamamını ve code cave yerleşimini doğrular.
- `tests/test_led_compositor.py` güncellendi:
  - `CompositorTestBase` ortak temel sınıfı oluşturuldu.
  - `PatchedLedCompositorTests` eklendi: Yamanmış 5706 firmware imajı üzerinde doğrudan gerçek stok `0x0804DD1C(grid)` fonksiyonunu çalıştıran 4 yeni test eklendi:
    - `test_patched_compositor_32step_mapping_and_playhead_flow`: Tek bir `0x0804DD1C(grid)` çağrısının üst 16 pad'e adım 0..15'i, alt 16 pad'e adım 16..31'i kopyaladığı, `page_store = 1` iken dahi üst pad'lerin kaymadığı ve Playhead'in 0..31 boyunca kesintisiz aktığı ve satır yalıtımının tam olduğu kanıtlandı.
    - `test_patched_compositor_velocity_mode_preserves_bottom_pads`: Velocity Modunda (`grid_mode = 2`) alt 16 pad'e Velocity LED tamponunun kopyalandığı kanıtlandı.
    - `test_patched_compositor_normal_mode_seq_disabled`: Sequencer Modu kapalıyken (`seq_enabled = 0`) sayfa 0 ve sayfa 1 stok davranışının korunduğu kanıtlandı.
    - `test_patched_compositor_memory_safety_and_no_overflow`: Bellek güvenliği, canary desenleri ve `view + 0xB4` bütünlüğü doğrulandı.
- Toplam test sayısı 55'ten **59'a yükseldi** ve tüm testler PASS oldu.
- `src/thumb_asm.py` güncellendi:
  - 16-bit PC-bağıl `adr(addr, target, rd)` (`ADR Rd, label`) ve `pop(..., lr=True)` (`POP.W {..., lr}`) yardımcıları eklendi.
- `src/seq_patch.py` güncellendi:
  - `c_resolve_subview(r0=grid, r1=pad)`: `c_seq_state()` çağırarak `grid` adresini `[state + 0x08]` içine kaydeder; `seq_enabled == 1` ve `grid_mode == 0` (`[grid + 0x264] == 0`) iken `0x0804DC86(grid, 0)` çağırarak 32 pad'in tamamını `Step View`'a yönlendirir; aksi halde orijinal `0x0804DC86(grid, pad)` çağırır.
  - `c_transform_pad(r0=grid, r1=pad, r2=track, r3=mode)`: `seq_enabled == 1` ve `mode == 0` iken `r0 = pad & 0x1F` döndürür; aksi halde orijinal `0x0804DF3E(grid, pad, track, mode)` çağırır.
  - `c_step_page_read(r0=page_store, r1=0)`: `seq_enabled == 1`, `grid_ptr != 0` ve `grid_mode == 0` iken code-cave içindeki sabit `c_zero_word` (`0x00000000`) adresini döndürerek Step Press (`0x0805CB04`) ve Step Release (`0x0805CCF0`) içinde sayfa ofsetini `0`'a kilitler (`step >= 32` taşmasını engeller); diğer modlarda (`grid_mode != 0`) orijinal `0x0803FC58(page_store, 0)` çağırarak `1–16` sayfa tuşunu korur.
  - `build_step_routing_patches()`: Code-cave yamasını ve 6 adet in-place 4-baytlık Thumb-2 `BL` kancasını (`0x0804D7B6`, `0x0804D7CC`, `0x0804D7FC`, `0x0804D812`, `0x0805CB14`, `0x0805CCFA`) oluşturur.
- `tests/test_step_routing.py` güncellendi:
  - Yamanmış 5706 imajını Unicorn'a yükleyen `PatchedStepRoutingTests` eklendi (`seq_enabled = 1, grid_mode = 0, page_store = 1` altında 32 pad tam yaşam döngüsü ve `view + 0xB4` koruma kanıtı; `grid_mode = 2` Velocity ve `grid_mode = 3` Gate modlarında `1–16` sayfa geçişi ve alt 16 pad yönlendirmesi korunumu; toplam 55 test PASS).

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
