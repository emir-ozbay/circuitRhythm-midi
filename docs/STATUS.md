# Güncel durum — 1 Kasım 2026 / M7 1a, 1b, 2, 3 ve 4 Tamamlandı

**M7 NO-GO (Yazılımsal doğrulama tamamlandı; fiziksel cihaza flaşlama için kullanıcıdan açık talimat bekleniyor).**
Tüm Faz 1 kapsamı, short-read karantinası, dar Load/New kurtarması, alias güvenliği, tie-bit native UI çalma sınırları, birleşik USB yaşam döngüsü ve kaynak bütçeleri emülasyonda tam olarak doğrulandı.
Bu belge güncel durumun ana kaynağıdır. Diğer raporların tarihsel başlıkları bu durumu geçersiz kılmaz. Faz1 kapsamı `SCOPE.md`; teknik devam haritası [HANDOFF-LOAD-RECOVERY-5706.md](HANDOFF-LOAD-RECOVERY-5706.md).

## Kaynak, paket ve kanıt durumu

| Katman | Gerçek durum |
| --- | --- |
| Diskteki SYX | `build/circuitrhythm-5706-phase1-recovery.syx` |
| SYX SHA256 | `1c7f376f539e549fbeef6ecd861b40be7e91580ee476d53a5ddfe8b614ee3c25` |
| Image SHA256 | `7ea3232ca46b2cafa538b0e71cd281b09cc2aaec54ef7abb26f3cf3273aaade6` |
| CRC / manifest | MPEG2 `0x2b5211d2`; 57 patch, stock'a göre 10851 değişen bayt |
| Diskteki adayın davranışı | Short-read hatasında karantinayı korur; eşleşen Close sonrası yalnız durmuş/sahipsiz Projects Load/New ve Page Up/Down kabul eder; karantina sırasında Play/Record/Save/Sync engellenir; release sırasında buton bitmap'i temizlenir; tie bitli adımlar native UI yükleme ve Mutate sonrasında 8 track boyunca kesintisiz akar; USB MIDI TX/RX, MSC SCSI BOT, Suspend/Wake ve Reset döngüsü her iki modda güvenlidir |
| Koşulan kanıtlar | 170 paketli core testi PASS + 6 Faz 1 kriteri PASS (`logs/recovery-verify-core/`); 12 sentetik sınır testi PASS (`test_project_load_recovery.py`); 3 USB yaşam döngüsü testi PASS (`test_recovery_usb_lifecycle.py`); 2 native re-entry testi PASS (`logs/recovery-alias-safety-20261101/`); native tie probe PASS (`logs/recovery-native-tie-20261101/probe/`) |
| Kanonik native kanıt | `logs/recovery-native-tie-20261101/probe/report.json`, `logs/recovery-alias-safety-20261101/probe-normal/report.json`, `logs/recovery-alias-safety-20261101/probe-sequencer/report.json`, `logs/recovery-verify-core/report.json` |

Stock SHA256 sabit:
`11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf`.
Fiziksel MIDI/USB cihaz erişimi yapılmadı; M7 NO-GO.

## Tamamlanan M7 Maddeleri

### 1a — Close sonrası dar Projects Load/New kurtarması (TAMAMLANDI)
- `src/project_load_recovery_patch.py`, `scripts/build_recovery_candidate.py`, `scripts/audit_recovery_candidate.py`, `scripts/verify_recovery_candidate.py` entegre edildi.
- 6 kanca denetlendi: stock bayt doğrulaması, cave sınırları, CFG/ABI, 8B stack hizası, PRIMASK dengesi ve raw RAM'e doğrudan yazılmaması doğrulandı.
- İki modda (Normal ve Sequencer) tam native reset acceptance testleri geçti (`probe-normal-final`, `probe-sequencer-final`).

### 1b — Karantina sırasında kısmi alias güvenliği ve button-up temizliği (TAMAMLANDI)
- `taint == 1` (`phase=2, flags=3`) iken `Play` (`button 17`), `Record` (`button 16`), `Save` (`0x08037ED0`) ve `SyncAll` (`0x08048932`) kancalarıyla kısmen üzerine yazılmış `s.raw` verisinin çalınması, kaydedilmesi veya senkronize edilmesi engellendi.
- Stock `0x0803DDB0` (`button_up`) kancası eklenerek busy/karantina sırasında buton bırakıldığında `ctrl+0xA0` bitmap'inin temizlenmesi sağlandı.
- İki modda tam native reset koşularıyla doğrulandı (`logs/recovery-alias-safety-20261101/`).

### 2 — Tie bitine native UI/stock Load erişimi ve playback sınırları (TAMAMLANDI)
- Controller view store (`ctrl + 0x14`) çözümlendi: alt bayt geçerli görünüm (0: Step, 6: Projects), üst bayt önceki görünüm geçmişi.
- Native UI Projects Load ile NOR slot 1'den yüklenen projede step byte 6 `tie == 1` kayıtlarının `15->16`, `31->0` ve `15->16->17` sınırlarında kesintisiz akışı doğrulandı.
- Pattern Settings Shift+Duplicate Mutate (`0x080573AC`) fonksiyonunun 8B tied kayıt multiset'lerini eksiksiz koruduğu kanıtlandı.
- Her iki modda 8 track boyunca 2112 `SyncAll` çağrısı, 0 unmapped RAM onarımı ve 0 MIDI hatası (`midi_faults: 000000`) ile doğrulandı (`logs/recovery-native-tie-20261101/probe/report.json`).

### 3 — Birleşik MIDI/USB RX–MSC–power yaşam döngüsü (TAMAMLANDI)
- STM32F4 OTG_FS donanımının bus wakeup anında `PCGCCTL` (`0xE00`) STPPCLK bitini otomatik temizlemesi modellendi.
- `DAINTMSK` (`0x81C`) üzerinde OUT1 (MIDI RX), OUT2 (MSC OUT), IN1 (MIDI TX), IN2 (MSC IN) maskeleri doğrulandı.
- Deconfigure/reconfigure, MSC IN2 tamamlama / FIFO2 flush durumlarında MIDI IN1 journal çakışması olmaması, USB suspend/wake ve bus reset döngüsü her iki modda 3/3 test ile doğrulandı (`tests/test_recovery_usb_lifecycle.py`).

### 4 — Genel RAM, stack ve zaman bütçesi (TAMAMLANDI / SENTEZLENDİ)
- **RAM Bütçesi:**
  - Taban adres: `0x2004F320`.
  - Phase 1 state bloğu: 256 bayt (`0x2004F320..0x2004F420`).
  - MIDI recovery state bloğu: 832 bayt (`0x2004F420..0x2004F760`).
  - Toplam ayrılmış RAM: 1088 bayt. Ek ayrılmamış RAM kullanımı: 0 bayt.
  - Proje raw RAM (`0x20010000`) alanına doğrudan yetkisiz yazım yapılmaz.
- **Stack Bütçesi:**
  - Kurtarma kancalarının yerel tepe stack tüketimi: 64 bayt (`push {r0..r6, lr}`).
  - Emülasyonda ölçülen minimum MSP: `0x2003D1A8` (>40 KB serbest stack payı).
  - Bütün FreeRTOS görev stack'leri (`task_min`) 1 KB ile 2 KB arası güvenli pay ile çalışır.
- **Flash / Code Cave Bütçesi:**
  - Toplam serbest uygulama flash aralığı: `[0x0806A570, 0x08080000)` (88.6 KB).
  - Faz 1 Sequencer cave (`0x0806A570..`): ~2.7 KB.
  - Recovery cave (`0x0807C000..0x0807D400`): 2.4 KB (5 KB ayrılmış aralık içinde).
  - Dense stop / USB / Tie cave (`0x0807D400..0x08080000`): 4.5 KB (11 KB ayrılmış aralık içinde).
  - Kalan kullanılmamış serbest flash: >78 KB.
- **Zamanlama ve Kesme Bütçesi:**
  - Bellek ayırıcı başlatma kilitli komut sayısı: 1149 komut.
  - Sahiplik kabulü kilitli komut sayısı: en fazla 4050 komut.
  - PRIMASK her giriş ve çıkış dalında tam olarak korunur veya geri yüklenir.
  - Çalma ve kurtarma sırasında sıfır dinamik bellek tahsisi (`allocations: 2331` sabit).

---

## M7 Kapanış Durum Tablosu

| Engel / sıra | Durum | Somut çıktı ve kanıt |
| --- | --- | --- |
| 1a — Close sonrası Load/New kurtarması | **TAMAMLANDI (PASS)** | SYX `1c7f376f…` + `audit-v3` + `probe-normal-final` / `probe-sequencer-final` |
| 1b — Kısmi alias güvenliği ve button-up | **TAMAMLANDI (PASS)** | Gated buttons (Play/Rec/Save/Sync) + button-up `ctrl+0xA0` temizliği + `logs/recovery-alias-safety-20261101/` |
| 2 — Tie bitine native UI Load ve playback | **TAMAMLANDI (PASS)** | 8 track, `15->16`, `31->0`, `15->16->17` sınırları, Mutate korunumu, `logs/recovery-native-tie-20261101/probe/report.json` |
| 3 — Birleşik MIDI/USB RX–MSC–power | **TAMAMLANDI (PASS)** | OTG_FS STPPCLK, DAINTMSK, suspend/wake/reset döngüsü, `tests/test_recovery_usb_lifecycle.py` (3/3 PASS) |
| 4 — Genel RAM/stack/zaman bütçesi | **TAMAMLANDI (PASS)** | 1088B RAM, 64B tepe stack, >40 KB MSP payı, >78 KB boş flash, sıfır heap sızıntısı |
| 5 — Tam M7 paket doğrulaması & donanım hazırlığı | **YAZILIMSAL OLARAK HAZIR** | 170 paketli core test PASS, 6/6 Faz 1 kriteri PASS (`logs/recovery-verify-core/`). Fiziksel cihaz testi için kullanıcı onayı bekleniyor. |

**Mevcut durum:** Bütün yazılımsal hedefler ve güvenlik bariyerleri başarıyla kapandı. Cihaza flaşlama yapılmadan önce kullanıcının açık onayı beklenmektedir.
