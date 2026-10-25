# Devralma durumu

25 Ekim 2026. **M0, M1, M2 ve M3 altyapısı tamamlandı. Kapsam ve mimari kesinleştirildi:**
- **64 adım hedefinden tamamen vazgeçildi;** kalıcı sınır stok veri yapısıyla %100 uyumlu olan **32 adımdır**.
- **Proje Yönetimi Mimari Keşfi (`0x0804F080` – `0x0804F2B8`):** Stok Projects görünümünün (`[ctrl + 0x50]`) her Pack içindeki 64 projeyi `[proj_view + 0x36]` baytıyla iki adet 32-projelik sayfaya (`0`: Proje 1–32, `1`: Proje 33–64) böldüğü makine kodunda doğrulandı. Normal modda `sayfa 0`, Sequencer modunda `sayfa 1` kilitlenerek ve `Packs` (`0x0803DB54`) ile Projects içi Up/Down (`0x0804F12C`) kapatılarak, SD dosya sistemine müdahale etmeden **32 bağımsız Sequencer projesi** (orijinal New, Save, Duplicate, Clear destekli) sağlanacaktır.
- **Sayfa (`1–16`) Tuşu ve Ekran Modları (`0x0803E2D8`):** `grid_mode == 0` (eski Sample/Step ekranı) 32-pad adım ekranına dönüştürülürken sayfa ofseti `0`'a kilitlenecek; `Note` (`1/7`), `Velocity` (`2`), `Gate` (`3`), `Pattern Settings` (`4`), `Microstep` (`5`) ve `Probability` (`6`) ekranlarında ise alt 16 pad ve `1–16` sayfa değiştirme tuşu %100 orijinal haliyle korunacaktır.
- **Faz 2 Müzikal Hedefi:** Serbest polifoni yerine Root Nota + Macro Knob ile Akor/Triad üretici (Mono, 5th, Maj, Min, Sus2/4, 7th) uygulanacaktır.

## Ortam ve bütünlük

- Stock: 508.861 bayt; SHA-256 `11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf`. Stock ve reference snapshot'ları değiştirilmedi.
- Windows AMD64 build **26200.9711**, Python **3.11.9** (64-bit, `.venv` aktif), Capstone **5.0.9**, Unicorn **2.1.4**. `-O` kullanılmadı.

## Doğrulanan yeni makine kodu adresleri (M1 ekleri)

| İşlev | Adres ve somut bulgu |
|---|---|
| Buton -> Grid Mode dönüşümü | `0x0803E2D8`: Button 8 (`Sample`) -> `mode 0` (veya `9`); Button 9 (`Note`) -> `mode 1` (`7`); Button 10 (`Velocity`) -> `mode 2`; Button 11 (`Gate`) -> `mode 3` (`5`); Button 12 (`Pattern Settings`) -> `mode 4` (`6`) |
| Projects butonu ve Packs geçişi | `0x0803DB2E` (Button 26 = `Projects`): `Shift == 0` ve aktif görünüm `6` değilse `[ctrl + 0x50]` (`0x0804F080`) çağrılır ve Projects görünümü açılır; `Shift != 0` veya zaten Projects görünümündeyse `0x0803DB54` dalıyla Packs görünümüne (`mode 5`, `[ctrl + 0x40]`) geçilir |
| Projects görünümü kurulumu | `0x0804F080`: Aktif proje numarasını (`0..63`) okur, `lsrs r2, r2, #5` ile sayfa (`0` veya `1`) hesaplayıp `[proj_view + 0x36]` (yani `[r5, #0x16]`) adresine yazar ve `0x0804F27E` LED çizimini çağırır |
| Projects pad basışı (Load/New/Clear/Dup) | `0x0804F09E`: `[proj_view + 0x36]` sayfasını okur, `add.w r5, r5, r0, lsl #5` ile `pad + (sayfa * 32)` proje indeksini hesaplar; Clear (`+0x18`), Save (`+0x2C`), Duplicate (`+0x1C`) ve Load/New (`0x08047038`) işlemlerini yürütür |
| Projects Up/Down sayfa değiştirme | `0x0804F12C`: Down (`0x13` = 19) basıldığında `[proj_view + 0x36] = 1`, Up (`0x14` = 20) basıldığında `[proj_view + 0x36] = 0` yazar |
| Projects LED çizimi | `0x0804F27E`: `[proj_view + 0x36]` değerini okuyup `0x0804F2B8` (`add.w r5, sl, r0, lsl #5`) ile `0..31` veya `32..63` projelerini 32 pad'e çizer |
| Güvenli Heap Durum Bloğu | Stok bump allocator (`0x08025A98`): limit `[0x20002B54]` (`0x2004F760`), current `[0x20002B58]` (`0x2004EA98`). `0x2004F660` adresinde 256 baytlık blok (`HEAP_LIMIT - 256`) ayırmak için limit düşürülebilir |
| Uygulama Sonu / Code Cave Alanı | Stok imaj sonu `0x0806A570`; uygulama flash üst sınırı `0x08080000` (~88 KB boş flash alanı) |

## Sonraki tek somut görev

**M4 Devamı (Mod Geçiş Kısayolu ve Proje/Ses Susturma):** Normal Mod ile Sequencer Only Modu arasında geçiş sağlayan güvenli buton kısayolunu (Shift kombinasyonu), Sequencer modunda dahili sample motoru tetiklemesini susturmayı (`0x08031A19` / `0x080467D2`), bağımsız 32 Sequencer projesi için sayfa kilidini (`[proj_view + 0x36]`) ve Packs kilidini (`0x0803DB54`) `src/seq_patch.py` içine ekleyip Unicorn'da doğrulamak.

## Tamamlanan Son Aşama (M4 Adım 5 — Basılı Tutarken Sahiplik Temizliği Makine Kodu — TAMAMLANDI)

- **Değiştirilen Dosyalar:**
  - `src/seq_patch.py` (ve `src/seq_Patch.py`):
    - `STOCK_GRID_MODE_UPDATE = 0x0804DAAC` ve `STOCK_STEP_LED_CALC = 0x0805CF24` tanımlandı.
    - `HOOK_GRID_MODE_CLEANUP = 0x0804D6E0` (`EXPECTED_GRID_MODE_CLEANUP = 00 f0 e4 f9`, `bl #0x804daac`) kancası eklendi.
    - `emit_grid_mode_cleanup(a: Asm)` fonksiyonu eklendi:
      * Grid Container mod/track güncelleme fonksiyonu `0x0804D6B6` içinde `0x0804D6E0` adresindeki çağrıyı kancalar.
      * Orijinal `0x0804DAAC` fonksiyonuna giden 5. stack argümanını güvenle aktarır (`ldr.w ip, [sp]; push {r4..r8, lr}; sub sp, #8; str.w ip, [sp]; bl 0x0804daac; add sp, #8`).
      * `[r5 + 0x228]` (Grid fiziksel basılı pad maskesi) sıfırlanır.
      * 8 track (`t = 0..7`) taranarak `view = [r5 + 0x74 + 4*t]` kontrol edilir; `view != 0` ve (`[view + 0xB8] != 0` veya `[view + 0xC0] != 0`) ise:
        - `[view + 0xB8] = 0` (pending toggle maskesi) ve `[view + 0xC0] = 0` (held pad maskesi) sıfırlanır.
        - 32 adım (`s = 0..31`) döngüsüyle `view + 0x74 + 2*s` durum word'ünde `bit 3` (`0x0008`) set ise `bics` ile temizlenir ve `0x0805CF24(view, s)` çağrılarak adımın LED rengi parlak beyazdan normal renge döndürülür.
      * `pop {r4..r8, lr}; bx lr` ile çağrıcının yazmaçları (`r4=8`, `r5=grid`, `r6=grid+0x260`, `r7=mode`, `r8=grid+0x238`) ve dönüş adresi eksiksiz geri yüklenir.
    - `build_step_routing_patches()`: 9 in-place Thumb-2 `BL` kancasını ve code cave yamasını üretir.
  - `tests/test_step_routing.py`:
    - `test_patched_hooks_and_code_cave_disassembly`: 9 in-place `BL` kancasının tamamını ve code cave yerleşimini Capstone ile doğrular.
    - `test_held_pad_ownership_cleanup_on_track_or_mode_change`: Pad 5 (üst satır) basılı tutulurken track değiştirildiğinde (`0x0804D6B6`) ve Pad 20 (alt satır) basılı tutulurken `grid_mode = 2` (Velocity) yapıldığında (`0x0804D6B6`), asılı kalan `bit 3`, `view + 0xB8`, `view + 0xC0` ve `grid + 0x228` maskelerinin tertemiz sıfırlandığı ve LED'in normale döndüğü Unicorn'da doğrulandı.
- **Komut ve Sonuç:** `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` -> **60 testin tamamı PASS** (0 hata). `analysis/` ve `stock/` altındaki hiçbir dosya değiştirilmedi.
- **Başarısız Hipotezler / Açık Riskler:** İlk derlemede `c_grid_mode_cleanup` çıkışında `pop {r4..r8, pc}` kullanılmıştı; `test_seq_state.py` içindeki `test_c_seq_state_disassembles_cleanly` testi code cave son talimatının `bx lr` olmasını beklediği için `pop {r4..r8, lr}; bx lr` ile hizalandı ve tüm testler geçti. Açık risk olarak mod geçiş kısayolu, proje sayfası kilidi ve dahili ses susturma sırayla ele alınacaktır.

## Tamamlanan Önceki Aşama (M4 Adım 4 — 32-Adım LED Compositor Makine Kodu — TAMAMLANDI)

- **Değiştirilen Dosyalar:**
  - `src/seq_patch.py`:
    - `HOOK_COMP_TOP_LEDS = 0x0804DDA4` (`EXPECTED_COMP_TOP_LEDS = 04 f0 b0 f9`, `bl #0x8052108`)
    - `HOOK_COMP_BOTTOM_MEMCPY = 0x0804DDBE` (`EXPECTED_COMP_BOTTOM_MEMCPY = d4 f7 97 ff`, `bl #0x8022cf0`)
    - `c_comp_top_leds(r0=sb)`: `c_seq_state()` çağırır; `seq_enabled == 1` ve `grid_mode == 0` (`[r6 + 0x264] == 0`) ise Step View'ın 64 baytlık LED tamponunun başını (`ldr r0, [sb, #4]; ldr r0, [r0]`) döndürür (sayfa 1'de kalınmış olsa dahi üst 16 pad her zaman adım 0..15'i gösterir); aksi halde orijinal `0x08052108(sb)` çağırır.
    - `c_comp_bottom_memcpy(r0, r1, r2)`: `c_seq_state()` çağırır; `seq_enabled == 1` ve `grid_mode == 0` ise `r1` kaynak adresini Step View'ın ikinci 16 adımıyla (`ldr r1, [sb, #4]; ldr r1, [r1]; adds r1, #0x20`) güncelleyip `0x08022CF0(r0, r1, 0x20)` (`memcpy`) çağırır; aksi halde `r1`'e dokunmadan orijinal `0x08022CF0(r0, r1, 0x20)` çağırır.
    - `build_step_routing_patches()`: 8 adet in-place 4-baytlık Thumb-2 `BL` kancasını ve genişletilmiş code-cave yamasını üretir.
  - `tests/test_step_routing.py`:
    - `test_patched_hooks_and_code_cave_disassembly`: Capstone ile tüm 8 in-place `BL` kancasını ve code-cave yerleşimini doğrular.
  - `tests/test_led_compositor.py`:
    - `CompositorTestBase` temel sınıfı oluşturuldu.
    - `PatchedLedCompositorTests`: Yamanmış 5706 firmware imajı üzerinde doğrudan gerçek stok `0x0804DD1C(grid)` fonksiyonunu çalıştıran 4 test eklendi (`test_patched_compositor_32step_mapping_and_playhead_flow`, `test_patched_compositor_velocity_mode_preserves_bottom_pads`, `test_patched_compositor_normal_mode_seq_disabled`, `test_patched_compositor_memory_safety_and_no_overflow`).
- **Komut ve Sonuç:** `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` -> **59 testin tamamı PASS** (0 hata). `analysis/` ve `stock/` altındaki hiçbir dosya değiştirilmedi.
- **Başarısız Hipotezler / Açık Riskler:** İlk çalıştırmada `PatchedLedCompositorTests` `LedCompositorTests`'ten türediği için stok imaj varsayan testleri de çalıştırmıştı; `CompositorTestBase` oluşturularak stok ve yamanmış test sınıfları ayrıştırıldı. Playhead testinde 31. adımın döngü sonrası temizlenmesi sağlandı. Açık riskler sırayla ele alınacaktır.

- **Değiştirilen Dosyalar:**
  - `src/thumb_asm.py`: 16-bit PC-bağıl `adr` (`ADR Rd, label`) ve 32-bit `pop(..., lr=True)` (`POP.W {..., lr}`) yardımcıları eklendi.
  - `src/seq_patch.py`:
    - `c_resolve_subview(r0=grid, r1=pad)`: `c_seq_state()` çağırır, `state != 0` ise `grid` işaretçisini `[state + 0x08]` (`grid_ptr`) içine kaydeder; `seq_enabled == 1` ve `[grid + 0x264] == 0` (`grid_mode == 0`) iken `0x0804DC86(grid, 0)` çağırarak 0..31 arasındaki tüm pad'leri `Step View`'a yönlendirir; diğer modlarda (`grid_mode != 0`) veya `seq_enabled == 0` iken orijinal `0x0804DC86(grid, pad)` çağırır.
    - `c_transform_pad(r0=grid, r1=pad, r2=track, r3=mode)`: `seq_enabled == 1` ve `r3 == 0` (`mode == 0`) iken `pad & 0x1F` (`0..31`) döndürür; aksi halde orijinal `0x0804DF3E(grid, pad, track, mode)` çağırır.
    - `c_step_page_read(r0=page_store, r1=0)`: `seq_enabled == 1`, `[state + 0x08]` (`grid_ptr`) geçerli ve `[grid_ptr + 0x264] == 0` (`grid_mode == 0`) iken code-cave içindeki 4-bayt hizalı sabit `c_zero_word` (`0x00000000`) adresini döndürerek sayfa ofsetini `0`'a kilitler (`+16` taşmasını önler); `grid_mode != 0` iken (Velocity, Gate, Note, Pattern Settings vb.) orijinal `0x0803FC58(page_store, 0)` çağırarak `1–16` sayfa tuşunu %100 korur.
    - `build_step_routing_patches()`: Code-cave yamasını ve 6 adet in-place 4-baytlık Thumb-2 `BL` kancasını (`0x0804D7B6`, `0x0804D7CC`, `0x0804D7FC`, `0x0804D812`, `0x0805CB14`, `0x0805CCFA`) üretir.
  - `tests/test_step_routing.py`: `PatchedStepRoutingTests` sınıfı eklendi (Capstone kanca doğrulaması, `seq_enabled = 1, grid_mode = 0, page_store = 1` iken 32 pad açma/kapatma ve `view + 0xB4` koruma kanıtı, `grid_mode = 2` Velocity ve `grid_mode = 3` Gate modlarında `1–16` sayfa geçişi ile alt 16 pad yönlendirmesinin korunumu, `seq_enabled = 0` normal mod uyumluluğu).
- **Komut ve Sonuç:** `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` -> **55 testin tamamı PASS** (0 hata). `analysis/` ve `stock/` altındaki hiçbir dosya değiştirilmedi.
- **Başarısız Hipotezler / Açık Riskler:** İlk denemede `c_zero_word` öncesi eklenen 2-baytlık `nop` dolgusu `c_seq_state` boyutu (`0x5E`) nedeniyle `c_zero_word` adresini `+2` kaydırdı; `nop` kaldırılarak `0x0806A634` (4-bayt hizalı) adresi doğrulandı. Açık risk olarak M4 sahiplik temizliği, M5 LED compositor ve M6 proje/ses susturma kancaları sırayla Unicorn'da doğrulanacaktır.

