> Güncel1 Kasım /Load short-read — Stock köprünün hata4'ü başarı apply'ına
> çevirmesi native reset/file worker ile yeniden üretildi. Yeni guard yanlış
> başarıyı atlar,native Close ve kalıcı taint ile mod geçişini kapatır. Raw alias
> rollback/toparlanma çözülmedi. Yeni aday272a8128… /CRC985753F7;M7 NO-GO.
> Güncel sayım ve tek sonraki görev STATUS.md'de;ayrıntı
> [MIDI-RECOVERY-LOAD-SHORT-READ-5706.md](MIDI-RECOVERY-LOAD-SHORT-READ-5706.md).
> Alt bölümler tarihsel sonuçlardır.

---

> Güncel31 Ekim /Canlı parametreler — Yerel native IRQ/UI canlı parametre
> testi eklendi. Firmware c9a87a9d…/CRC BEB0D013 ve kurtarma girdisi aynı;
> koşu/sayım STATUS.md'de. M7 NO-GO;GPIO/NVIC/baud/fiziksel teslim kanıtı
> değildir. Cihaza erişilmedi ve donanım denemesi önerilmiyor.

---

> Güncel31 Ekim /Gate expiry ve tie — Yeni firmware üretilmedi;c9a87a9d… /
> CRC BEB0D013 aynı. Testler yerel byte/Unicorn kanıtıdır;sentetik tie bitinin
> UI erişilebilirliği iddia edilmez. Güncel sayım STATUS.md'de. M7 NO-GO;
> cihaz erişimi/yükleme yapılmadı ve fiziksel test önerilmiyor.

---

> Güncel31 Ekim /64 stok ses Stop — Yeni aday c9a87a9d… /CRC BEB0D013;
> yalnız yerel build/emülasyon.64 Off+Stop için bounded native output servisi
> eklendi;quarantine/fault bayrakları temizlenmez.149 temel test ve native
> iki-mod IRQ/32-adım regresyonu PASS. Güncel senaryolar STATUS.md'de.
> M7 NO-GO;yükleme/port erişimi izni yok. Alt raporlar eski SHA'lara aittir.

---

> Güncel31 Ekim /Native timer IRQ — Borca host yazısı olmadan IRQ66→
> Main358→slot11/2B750→uygulama370→player zinciri PASS.10690 IRQ/tüketim;
> iki modda1–32–1,544 LED,8 canlı notada Stop ve40 On/40 Off/193 Clock.
> Sonlu DSP recording-idle ve ham ADC referans/pil profilleri;native pil
> hesabı/kapanış kodu korunur.2 yeni exact-SYX +29 örtüşen hedefli test PASS.
> Önceki149 yeniden koşulmadı;verifier151/core-only144. Firmware3f979b70… /
> CRC5AB3F54B,üretim ve1088B rezervasyon aynı. M7 NO-GO;cihaz erişimi yok.
> Sonraki:uzun gate/farklı adım notalarıyla64 aktif stok ses ve native Stop.
> STATUS veMIDI-RECOVERY-TIMER-IRQ-5706.md güncel;altı tarihseldir.

---

> Güncel31 Ekim /Native Play–Stop — Tek reset,8 gerçek player,iki modda
>1–32–1 ve193 microstep commit/player/mod PASS;544 LED bileşimi. Mod/iki UART
> portu başına40 On/40 Off ve8 canlı notada native Stop flush PASS.
> Timer borcu sonlu sentetik girdidir;hardware IRQ/geçen zaman kanıtı değildir.
> Yeni1 exact-SYX +28 örtüşen hedefli test PASS;önceki148 yeniden koşulmadı.
> Verifier149/core-only143;firmware3f979b70…/CRC5AB3F54B veüretim aynı.
> Native cursor bit6;eski bit0 etiketi ayrı edit/recorder store'udur.
> M7 NO-GO. Sonraki:40000C00/vector66 IRQ→borç→Main timer zinciri.
> STATUS veMIDI-RECOVERY-PLAYBACK-5706.md güncel;altı tarihseldir.

---

> Güncel31 Ekim /Probability — Native yardımcı görünüm sayfa/pad grubu
> tamamlandı: Note1/7, Velocity2/Gate3, Pattern Settings4, Microstep5, Probability6.
> Yeni mode6 testi:512 üst pad/64 uç/128 LED/32 zengin Mutate PASS;26 hedefli PASS.
> Önceki147 aynı image'de, tekrar koşulmadı. Genel verifier148/core-only143.
> Firmware3f979b70…/CRC5AB3F54B, üretim ve1088B RAM aynı; M7 NO-GO.
> Sonraki iş: native Play17/Stop17→player/scheduler→1–32 playhead izi.
> STATUS veMIDI-RECOVERY-PROBABILITY-5706.md güncel; altı tarihseldir.

---

> Güncel31 Ekim /Microstep — Native mode5 iki sayfa/8 track/iki mod PASS.
>512 üst-pad eşlemesi,64 uç senaryo,tüm64 maske,128 LED bileşimi ve64 held
> guard sınandı.32 velocity/gate koruması +32 durdurulmuş idle edit PASS.
> Yeni1 paket ve26 hedefli test PASS;önceki146 aynı image'de,tekrar koşulmadı.
> Genel verifier147/core-only143. Firmware3f979b70…/CRC5AB3F54B veüretim aynı.
>1088B rezervasyon/2184B workload payı aynı;M7 NO-GO. Sonraki:native Probability6.
> STATUS veMIDI-RECOVERY-MICROSTEP-5706.md güncel;altı tarihseldir.

---

> Güncel31 Ekim /Pattern Settings — Native mode4 sayfa/Start-End/hız/yön/
> Mutate testi8 track/iki modda PASS:1024 üst +1024 alt pad,64 LED/held guard,
>32 kayıpsız8B-record Mutate. Yeni1 paket ve26 hedefli test PASS;önceki145 aynı
> image'e aittir ve yeniden koşulmadı. Genel verifier146 test içerir.
> Firmware3f979b70…/CRC5AB3F54B,üretim kaynakları ve1088B RAM aynı. M7 NO-GO.
> Düzeltme:eski iç16/17=Clear/Duplicate etiketi yanlış;17 Play,24 Duplicate.
> Kanonik koşu17'yi kullanmaz,transport0'ı denetler. Sonraki iş:native Microstep5.
> STATUS veMIDI-RECOVERY-PATTERN-SETTINGS-5706.md güncel;altı tarihseldir.

---

> Güncel31 Ekim — Note1↔7 asılı nota ve hatalı mod kabulü düzeltildi.
> Native8 track/iki mod/iki sayfa:1536 tuş,512 adım,64 retained release,
>48 native iptal,64 pitch/LED senaryosu PASS. Velocity/Gate yeniden PASS.
> Aynı SYX üzerinde143 core +1 Note +1 Velocity/Gate paket testi;6 ölçüt ve60
> hedefli test PASS (örtüşür). SYX3f979b70…/CRC5AB3F54B;42 patch/7595B.
> Stock ve1088B rezervasyon aynı;proje I/O0/ek tahsis0. M7 NO-GO.
> Sonraki iş:native Pattern Settings4. STATUS veMIDI-RECOVERY-NOTES-5706.md güncel.

---

> Güncel30 Ekim — Native Velocity/Gate testi sekiz track ve iki mod/sayfada PASS.
> 1024 üst-pad eşlemesi,128 parametre/LED senaryosu; stok end15→31 uzatması testli.
> Yeni1 paket native test ve25 hedefli test PASS; önceki142 aynı firmware'e aittir.
> Firmwareafbab4f2…/CRC114DA352 aynı; proje I/O0, ek tahsis0,2184B alan aynı.
> Sonraki iş: native Note1/7 sayfa tuşu ve alt16 pad stok eşlemesi.
> M7 NO-GO; STATUS veMIDI-RECOVERY-VIEWS-5706.md güncel, altı tarihseldir.

---

> Güncel:166 test (13 deneysel)/87 aday regresyonu PASS. Off/Stop recovery
> yalnız emülasyonda çalışıyor; üretime eklenmedi. SysEx bypass/RAM açık; NO-GO.
> Fiziksel cihaz testi için hazır değildir. STATUS.md ilk bölümü önceliklidir.

---

> Güncel: ortak proje ve onaylı test migrasyonu tamamlandı.
> 101 regresyon ve35 packaged test PASS; bekleyen test onayı yok.
> Mod değişiminde dosya erişimi yok. Stok storage hatası onarılmış sayılmaz.
> Kalan3 GO engeli ve güncel hash için STATUS.md ilk bölümü geçerlidir. NO-GO.

---

> Ortak proje kapsamında banka ayrımı ve otomatik Load kaldırıldı.
> Mod değişimi dosya erişimi yapmaz. Eski Load engeli adaydan çıkarıldı.
> Stok storage hata riski onarılmadı. Tam test migrasyonu onay bekliyor.
> Güncel aday ve NO-GO kararı için STATUS.md ilk bölümü önceliklidir.

---

> Güncel: 26 Ekim 2026, Load/New continuation okuma öncesinde kapatıldı.
> Tüm raw proje baytları korunuyor; işlevsel Load ve boot kabul edilmedi.
> NO-GO;131 regresyon. STATUS.md ilk bölümü önceliklidir.
> Aşağıdaki bozulma deneyi koruma kaldırıldığında hâlâ geçerlidir.

---

> Güncelleme: güncel aday, 128 test sonucu ve kritik alias engeli dahil dört engel için
> [STATUS.md](STATUS.md) ilk bölümü ve [GO ölçütleri](PHASE1-GO-GATES.md) önceliklidir.
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

# Faz 1 Donanım Test Protokolü — İncelenmeye Hazır Aday

**25 Ekim 2026:** Tüm Faz 1 izolasyon ve güvenlik engelleri Unicorn ARM emülasyonunda ve bağımsız denetim aracında başarıyla doğrulanmıştır.
Fiziksel cihaza veya MIDI/USB portuna **kullanıcının açık onayı olmadan kesinlikle erişilmeyecektir.**
Bu belge, donanım testi öncesi güvenlik hazırlıklarını ve adım adım test protokolünü tanımlar.

| Parametre | Değer |
|---|---|
| **Aday Firmware Dosyası** | `build/circuitrhythm-5706-phase1-sequencer.syx` |
| **SysEx SHA-256** | `6c4522bfeb56f39441ac478e4fecc2354f111db31bf6ca5b9fc5cea9683beba9` |
| **Image Boyutu** | 371.736 bayt |
| **Image SHA-256** | `fd2b2b3a981b901a979aa47dfc84fb2c59527ab0fae9932b4465799a5db7b3f5` |
| **CRC-32/MPEG-2** | `0x9798a0da` |
| **Manifest** | `build/circuitrhythm-5706-phase1-sequencer.manifest.json` |
| **Yama Sayısı** | 30 Hunk (Toplam 1.758 bayt değişti) |
| **Stok Firmware SHA-256** | `11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf` |
| **Vektör Tablosu** | [0x08010000..0x08010200) %100 özgün korundu (512 bayt) |
| **Doğrulama Kararı** | **REVIEW_REQUIRED (Tüm host/emülasyon testleri PASS; donanım testi için kullanıcı onayı bekleniyor)** |

---

## Donanım Testi Öncesi Zorunlu Hazırlıklar ([RECOVERY.md](RECOVERY.md))

1. **Pack ve Proje Yedeği Alın:**
   - Novation Components (web/standalone) aracılığıyla cihazdaki tüm pack ve projeleri bilgisayara yedekleyin.
2. **Kurtarma Modu Bilgisi:**
   - Cihaz açılırken `Shift + Note + Track 1` basılı tutulduğunda resmi bootloader moduna girer.
   - Resmi `stock/circuitrhythm-firmware-5706.syx` dosyası her zaman orijinal durumuna döndürülebilir.
3. **Güvenli SysEx Aktarımı:**
   - Yükleme için standart MIDI DIN / USB üzerinden Novation Components veya MIDI-OX / SysEx Librarian kullanılabilir.

---

## Adım Adım Donanım Test Sırası

1. **Açılış ve Normal Mod Doğrulaması:**
   - Cihaz normal açılmalı, stok projeler (Banka 0, slotlar 1–32) listelenmeli, sample playback ve normal ses motoru eksiksiz çalışmalıdır.
2. **Sequencer Moduna Geçiş:**
   - `Shift + Sample Rec` kombinasyonuna basıldığında durum makinesi devreye girmeli, dahili ses motoru tamamen susturulmalı (MIDI-Only), LED'ler güncellenmeli.
   - Projede kaydedilmemiş değişiklik varsa (`DIRTY`) geçişin reddedildiği doğrulanmalıdır.
3. **32 Adım Görünümü ve Playhead:**
   - Ana Step görünümünde (`grid_mode == 0`) 32 pad'in tümü adım olarak düzenlenebilmeli, playhead 1'den 32'ye kesintisiz akmalıdır.
   - `1-16` tuşu mod 0'da devre dışı kalmalı; `Note`, `Velocity`, `Gate`, `Microstep`, `Probability` ekranlarında ise alt 16 pad ve `1-16` tuşu tam çalışmalıdır.
4. **Bağımsız Projeler (Banka 1):**
   - Projects görünümüne girildiğinde Sequencer projelerinin (Banka 1, slotlar 33–64) açıldığı doğrulanmalıdır.
   - New, Save, Duplicate ve Clear işlemleri denenmeli, Normal projelere hiçbir veri taşmadığı kontrol edilmelidir.
   - `Packs` görünümüne (`Shift + Projects`) geçişin Sequencer modunda kilitlendiği teyit edilmelidir.
5. **Dahili Sample Susturması ve MIDI Çıkışı:**
   - Pad'lere basıldığında veya sequence çalarken hoparlör/kulaklıktan dahili sample sesi GELMEMELİ; MIDI çıkışından ilgili kanalda Note On/Off ve Clock eksiksiz çıkmalıdır.
   - Sequencer moduna geçildiğinde o anda çalan uzun bir sample'ın anında kesildiği test edilmelidir.
6. **Normal Moda Geri Dönüş:**
   - Tekrar `Shift + Sample Rec` ile Normal moda dönüldüğünde Banka 0 projelerinin ve dahili ses motorunun geri geldiği doğrulanmalıdır.
