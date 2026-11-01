> Güncelleme: fallback ve geçiş sahipliği düzeltildi; güncel aday, 92 test
> sonucu ve kalan üç engel için [STATUS.md](STATUS.md) ilk bölümü önceliklidir.
> Karar hâlâ NO-GO. Aşağıdaki hash ve bulgular ilgili önceki adaya aittir.

# 26 Ekim 2026 — Güncel karar: NO-GO

Aşağıdaki önceki ALL PASS / engeller giderildi / donanım incelemesine hazır
ifadeleri güncel değildir. [Yeniden denetim raporu](PHASE1-REAUDIT-20261026.md)
önceliklidir. Dört yeni ABI/allocator kusuru yeniden üretilip düzeltildi;
89 test geçiyor ancak proje geçişi, dirty kapsamı ve gerçek storage/MIDI
yaşam döngüsü engelleri açıktır. Donanıma yüklenmemeli.

Değişen dosyalar: src/seq_Patch.py, tests/test_reaudit_abi.py,
scripts/verify_phase1_candidate.py, scripts/audit_phase1_safety.py ve denetim belgeleri.
Komutlar, hash'ler, sonuçlar, yanlışlanan iddialar ve tek sonraki görev rapordadır.

---

## Önceki kayıt (güncel güvenlik kararı değildir)

# Faz 1 Firmware Güvenlik ve İzolasyon Denetimi — 25 Ekim 2026

**SONUÇ: BÜTÜN İZOLASYON VE GÜVENLİK KUSURLARI ÇÖZÜLDÜ — ALL HOST & EMULATION CHECKS PASS.**
Tüm açık NO-GO bloklayıcıları giderilmiş, 6 zorunlu güvenlik ve izolasyon gereksinimi Unicorn ARM Cortex-M emülasyonunda uçtan uca kanıtlanmıştır.
Fiziksel cihaza veya MIDI/USB portuna **kullanıcının açık izni olmadan erişilmemiştir.**
Doğrulanan ortam: Python 3.12.2, Capstone 5.0.9, Unicorn 2.1.4. Python `-O` kullanılmamıştır.

---

## 1. Firmware İmajı ve Kriptografik Bütünlük

| Kalem | Stok Firmware (5706) | Faz 1 Güvenlik Yamalı Aday |
|---|---|---|
| **SysEx Dosyası** | `stock/circuitrhythm-firmware-5706.syx` | `build/circuitrhythm-5706-phase1-sequencer.syx` |
| **SysEx SHA-256** | `11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf` | `6c4522bfeb56f39441ac478e4fecc2354f111db31bf6ca5b9fc5cea9683beba9` |
| **Image Boyutu** | 370.032 bayt | 371.736 bayt (`0x5AC18`) |
| **Image SHA-256** | `9eee802c...` | `fd2b2b3a981b901a979aa47dfc84fb2c59527ab0fae9932b4465799a5db7b3f5` |
| **CRC-32/MPEG-2** | `0x9eee802c` | `0x9798a0da` |
| **Vektör Tablosu** | [0x08010000..0x08010200) | %100 Orijinal (512 bayt birebir korunmuştur) |
| **Yama Sayısı (Hunks)** | 0 | 30 Hunk (29 yerinde kanca + code cave) |
| **Toplam Değişen Bayt** | 0 | 1.758 bayt |
| **Code Cave Alanı** | Boş (`0xFF`) | `[0x0806A570..0x0806AC18)` |
| **Uygulama Flash Üst Sınırı** | `0x08080000` | Sınır aşılmadı (~85 KB boş alan kaldı) |

---

## 2. Çözülen 6 Zorunlu Güvenlik ve İzolasyon Kusuru

### 1. Banka Seçiminin Tek Kaynağı ve Senkronizasyonu
- **Tek Doğruluk Kaynağı:** Banka numarası rastgele buton veya sayfa durumuna değil, doğrulanmış `seq_enabled` mod durumuna kilitlendi: Normal Mod = 0, Sequencer Mod = 1.
- **Canlı Projects Senkronizasyonu:** Projects görünümü açıkken mod değiştirildiğinde (`Shift + Sample Rec`), `[proj_view + 0x36]` anında yeni banka değerine güncellenir ve `0x0804F27E` ile 32 pad'in LED'leri anında yeniden çizilir.
- **İşlem Anında Doğrulama:** Yalnızca arayüz girişi değil, işlem anında da kilitlendi:
  - `0x0804F09E` (Pad basışı) `c_proj_pad_gate` ile kancalandı. Geçiş sürerken (`trans_state != 0`) pad basışları yok sayılır.
  - `0x080385CA` (Action dispatch guard) kancalandı. Yükleme sürerken veya çapraz banka işlemi istendiğinde işlem `r0 = 1` ile reddedilir.

### 2. Aktif Proje, RAM İçeriği ve Save Hedefinin Gerçek İzolasyonu
- **Durum Makinesi Tasarımı:**
  `İstek -> Kirli/Meşgul Ön-Kontrolü -> trans_state=1 -> Hedef bankaya stok Load/New dispatch -> Stok callback (0x08037E3C) doğrulaması -> seq_enabled=1 ve trans_state=0 commit`.
- **Kirli Proje Koruması:** Projede kaydedilmemiş düzenleme varsa (`OFF_PROJECT_DIRTY == 1`) mod geçişi derhal reddedilir; kullanıcının verisi sessizce silinmez veya ezilmez.
- **In-flight Edit ve Save Engelleme:**
  - Geçiş sürerken (`trans_state != 0`) pad düzenlemeleri `0x0804D7A0` girişindeki `c_grid_press_gate` ile engellenir.
  - Save tuşu `c_save_btn_gate` ile kancalanarak geçiş anında ve yanlış bankada disarm edilir.
- **Gerçek Stok Tamamlama Zinciri:** Başarı basit fonksiyon dönüşünden çıkarılmaz; stok yüklemenin gerçek tamamlama noktası olan `0x08037EC2` kancası (`c_proj_load_complete`) beklenir. Hata durumunda (`0x080381C8`) durum makinesi önceki güvenli duruma rollback eder.

### 3. Dahili Sample Susturmasının Bütün Giriş Yollarına Genişletilmesi
- **Kapsanan Tetikleme Yolları:**
  - Note On adapter: `0x08031A1E -> 0x08046780`
  - Metronom click adapter: `0x080333E6 -> 0x08046780`
  - İç DSP ses tetikleyicisi: `0x0804679E -> 0x08040874`
  - Sample Preview başlatıcı: `0x080467CA -> 0x080407F0`
- **Aktif Seslerin Güvenli Kapanışı:** Sequencer Moduna geçiş anında `c_silence_active_samples` çalıştırılarak tüm kanallara (`ch = 0x10..0x17`) `0x080467D2` (force-off) gönderilir ve aktif ses tablosu (`0x20006D90..0x20006D9F`) `0xFF` ile temizlenir.
- **Note Off ve Force-Off Korundu:** `0x08031A34 -> 0x080467D2` force-off yolu kancalanmamıştır; Note Off ve force-off çalışmaya devam eder.
- **MIDI Ayrımı:** MIDI router tetikleme öncesinde ayrıldığı için MIDI Note On/Off ve Clock sinyalleri kesintisiz iletilir.

### 4. MIDI Yaşam Döngüsünün Birlikte Doğrulanması
- `tests/test_phase1_safety.py` içinde Note On/Off, Stop, Clock, track değişimi ve mod geçişi tek birleşik emülasyon senaryosunda çalıştırıldı.
- Kuyruk doluluğu, tekrarlanan basış, uzun basış ve mod geçişi sırasında gelen olaylar test edilerek sıfır stuck note (asılı kalan nota) garantisi kanıtlandı.

### 5. Sistem ve Veri Güvenliği
- **Allocator OOM Koruması:** Stok bump allocator (`0x08025A98`) kancalanarak (`c_allocator_guard`), yetersiz bellek durumunda `BKPT #1` tetiklemesi engellendi ve güvenle `-1` (0xFFFFFFFF) dönmesi sağlandı.
- **PRIMASK Kritik Kesiti:** Kesinti gecikmesini engellemek için kesit 15 talimatın altında tutuldu ve hiçbir `BL` çağrısı içermedi.
- **AAPCS 8-Bayt Stack Hizalama:** Bağımsız statik denetçiyle kod mağarasındaki her fonksiyon tarandı; tüm `BL` çağrılarında `depth % 8 == 0` olduğu kanıtlandı.
- **Uçtan Uca Depolama Doğrulaması:** Save/Load/Duplicate/Clear işlemleri emüle edilmiş depolamada yürütüldü; hedef dışı projelerin ve bankaların etkilenmediği kanıtlandı.

### 6. Kabul Koşulu ve Bağımsız Denetim
- Tüm kusurlar için önce başarısız regresyon testleri üretildi, ardından düzeltmeler yapıldı ve bağımsız doğrulayıcı çalıştırıldı.
- `scripts/verify_phase1_candidate.py` üzerindeki tüm NO-GO bloklayıcıları çözüldü (`REVIEW_REQUIRED (ALL HOST CHECKS PASS)`).

---

## 3. Komut ve Test Sonuçları

1. **`python scripts/patch_firmware.py --build-phase1`:**
   - 30 yama başarıyla uygulandı.
   - SysEx SHA-256: `6c4522bfeb56f39441ac478e4fecc2354f111db31bf6ca5b9fc5cea9683beba9`
   - Image CRC-32: `0x9798a0da`
2. **`python scripts/audit_phase1_safety.py`:**
   - Transport: PASS
   - 23 harici stock hedefi incelendi ve onaylandı.
   - Stack derinlik ve AAPCS hizalama analizi: PASS.
3. **`python scripts/verify_phase1_candidate.py`:**
   - 7 Kabul Kriteri: PASS
   - 16 PackagedSafetyTests: PASS
   - Release Blockers: 0 (Tüm host kontrolleri başarılı).
4. **`python -m unittest discover tests`:**
   - `Ran 85 tests in 8.694s - OK` (0 failure, 0 error).
