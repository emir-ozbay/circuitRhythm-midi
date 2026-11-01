# Pad bırakıldıktan sonra mod geçişi — 5706

30 Ekim 2026. Yerel emülasyon; M7 NO-GO. Fiziksel cihaz veya port erişimi yok.
Güncel test sonuçları ve sonraki görev `STATUS.md` içindedir.

## Hata ve native kanıt

Önceki guard `view+B8 | view+C0` sıfır değilse mod geçişini reddediyordu.
Pad31 bırakıldığında grid+228, C0 ve adımların bit3 alanı sıfırlanıyor;
B8'de bit31 kalıyordu. Bu nedenle kullanıcı bir adımı düzenledikten sonra
Shift + Sample Rec ile dönemiyor, önce track değiştirmek zorunda kalıyordu.

B8 kısa basışta adımın değiştirilip değiştirilmeyeceğini belirleyen kayıttır:

- Press `5CB24..5CB2C` ilgili B8 bitini önce temizler, `5CC8A..5CC90` kurar.
- `5CC86`, timer6'yı 300 tick ve callback `5CE49` ile kurar; C0 canlı basılı
  maskesi ayrıca `5CCEA`'da yazılır.
- Release `5CD14` C0 bitini temizler. `5CD28..5CD32` B8 bitini test edip gerçek
  adım değiştirme işlevi `5D610`'u çağırır; bu dal B8 bitini temizlemez.
- Native kısa basış izinde `5CD66→46E2A(6)` timer6'yı iptal eder; `5D040`
  timer3'ü de iptal eder. Timer slotundaki active alanı gerçekten sıfırdır.
- Uzun basış callback'i `5CE48..5CE5A`, `B8 &= ~C0` yapar. C0 ve bit3 canlı
  kalırken B8 silinir. Bu, B8'in tek başına canlı sahiplik olmadığını gösterir.
  Callback C0 sıfırken yeni pad veya adım sahipliği yaratamaz.

## Düzeltme

`c_mode_can_switch`, C0 ve 32 adımın bit3 alanını kontrol eder. Grid+228,
sekiz nota sahibi, MIDI giriş durumu, transport, readiness ve gerçek proje
I/O phase kontrolleri korunur. B8 kontrolü kaldırılmıştır; B8 verisi silinmez.
Başarılı veya reddedilmiş mod geçişi adım görünümünün RAM'ini değiştirmez.
Track/görünüm değişimindeki mevcut B8/C0/bit3 temizliği aynen devam eder.

Bu düzeltme için yeni timer, proje I/O, RAM tahsisi veya kritik bölüm yoktur.
Guard kodu altı bayt kısalır; sonraki cave etiketleri ve ilgili branch'ler
assembler tarafından yeniden yerleştirilir. Önceki recovery image'a göre
499 bayt farklıdır; tam changed-range manifest ayrı üretilir. Core, glue,
accepted-TX guard ve CTRL_SYNC helper aynı kalır. Stock hash'i ve ilk512B
vector/identity korunur; uygulama sınırı, özgün baytlar, çakışma ve CRC
denetimleri strict çalışır.

## Test kapsamı

Kaynak testleri sekiz track'te iki mod yönünü, B8 kaydının korunmasını,
C0/bit3 sahipliğinin ve transport busy durumunun reddini sınar.

Native test resetten kurulan aynı nesnelerle 32 pad'in her birine basıp bırakır.
Her pad yalnız kendi sekiz baytlık adım aralığını değiştirir. Her bırakmadan
sonra track değişmeden iki yönde mod geçişi denenir; commit sırasında raw proje
ve metadata bankları karşılaştırılır. Basılı pad hâlâ reddedilir.

Uzun basış testi timer6 slotunu veya callback pointer'ını host'ta kurmaz.
255+44+1 sentetik tick borcu, gerçek `2677A` countdown/dispatch yoluna verilir;
299 tick'te kalan süre1, 300'de callback `5CE48` ve tek seferlik timer iptali
kontrol edilir. Bu elapsed-time veya fiziksel zamanlama kanıtı değildir.
Diğer kurulu native timer'lar da bu dispatch sırasında yürür.

İlk keşif sürümünün `2677A`'nın bütün tick borcunu bir çağrıda tükettiği
varsayımı yanlıştı. Native işlev her çağrıda yalnız bir tick tüketir. Test
adapter'ı buna göre düzeltildi; kanonik koşu yeni paketle resetten başlar.
Keşif kayıtları kanonik testlerin yerine kullanılmaz.

## Paket ve tekrar üretim

- SYX SHA256: `afbab4f2bb30b955aa369f9f2cdf062235b04c3aaf915e30fa7a8559fda26f64`
- Image SHA256: `5fa9e337ede28176f485911f43eedc63e5091e0a8d686901dd36b28a6947e8cd`
- MPEG2 CRC: `114DA352`; 42 patch, stock'a göre7540 değişen bayt.
- Image458296B, SYX630213B; RAM rezervasyonu1088B olarak kalır.

`.venv\Scripts\python.exe` kullanılır; `-O` yoktur:

- `scripts/build_recovery_candidate.py`
- `scripts/probe_recovery_live_mode.py logs/recovery-mode-latch-20261030/probe`
- `scripts/verify_recovery_candidate.py logs/recovery-mode-latch-20261030/packaged`
- `scripts/audit_recovery_candidate.py logs/recovery-mode-latch-20261030/audit`
- Önce `$env:PYTHONPATH='scripts;src;tests'`, ardından `-m unittest
  test_shared_project test_step_routing test_projects_and_mode test_reaudit_abi
  test_midi_mode_ownership test_sequencer_playback -v`.

Before/after firmware, manifest, kaynak diff'i, native timer izi ve hash'ler
`logs/recovery-mode-latch-20261030` içindedir. Probe/verifier başarıda da M7
NO-GO nedeniyle uygulama düzeyinde exit2 döner.

Sonlu DSP girdileri, sentetik NOR/ADC/USB yanıtları, disabled DWT ve non-nested
FPU modeli sınırları sürer. GPIO/input kuyruğu, tam görünüm/page/playhead,
uçtan uca MIDI/USB/MSC/power, fiziksel timing, partial Load alias ve short-read
riskleri bu düzeltmeyle kapanmış sayılmaz. Akor ve uzunluk kısayolu Faz2'dir.
