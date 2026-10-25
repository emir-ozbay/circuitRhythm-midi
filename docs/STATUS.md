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

**M4 Adımı:** Mod geçişi (`seq_enabled`), `grid_mode == 0`'da 32 pad -> Step View yönlendirmesi (`0x0804DC86`, `0x0804DF3E`), sayfa ofsetinin `grid_mode == 0`'da `0`'a kilitlenmesi (`0x0805CB04`, `0x0805CCF0`) ve sahiplik temizliği (`view + 0xB8`, `view + 0xC0`, `view + 0x74` bit 3) makine kodu yamalarını `src/seq_Patch.py` içine ekleyip Unicorn emülatöründe doğrulamak.

## Tamamlanan Son Aşama (M3 Adım 1 & Adım 2 — TAMAMLANDI)

- **M3 Adım 1:** `scripts/patch_firmware.py` code-cave desteği (`FLASH_END = 0x08080000`, 4-bayt hizalama, dinamik boyut ve MPEG-2 CRC-32 header güncellemesi) ve `tests/test_patcher.py` içindeki 6 yeni test (`TestCodeCaveSupport`) tamamlandı.
- **M3 Adım 2:**
  - `src/thumb_asm.py`: MIT lisanslı Thumb/Thumb-2 makine kodu üreticisi (`Asm`, `bl`, `b_w`, `push`, `pop`, `ldr`, `str`, `ldrb`, `strb`, `movw`, `movt` vb.) oluşturuldu.
  - `src/seq_Patch.py`: `CODE_CAVE_BASE = 0x0806A570`, `SEQ_STATE_ADDR = 0x2004F660` (256 bayt, `MAGIC = 0x31514553` `"SEQ1"`), durum bloğu ofsetleri (`+0x00` `magic`, `+0x04` `seq_enabled`, `+0x05` `last_normal_proj`, `+0x06` `last_seq_proj = 32`, `+0x08` `grid_ptr`) ve `c_seq_state()` Thumb-2 makine kodu üreticisi tamamlandı.
  - `tests/test_seq_state.py`: Capstone disassembly ve Unicorn emülasyon testleri (8 yeni test: normal rezervasyon, ikinci çağrıda durum koruma, tam sınır `current == 0x2004F660`, dolu heap `current > 0x2004F660`, beklenmeyen limit reddi, bozuk magic kurtarma ve stok bump allocator `0x08025A98` entegrasyonu) eklendi.
- **Komut ve Sonuç:** `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` -> **46 testin tamamı PASS** (0 hata). `analysis/` ve `stock/` altındaki hiçbir dosya değiştirilmedi.
- **Başarısız Hipotezler / Açık Riskler:** Başarısız hipotez yok. Açık risk olarak M4–M6 kancalarının gerçek RTOS görev sıralaması ve yığın kullanımı Unicorn testleriyle adım adım doğrulanmaya devam edecektir.
