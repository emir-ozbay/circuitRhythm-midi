> Güncelleme: fallback ve geçiş sahipliği düzeltildi; güncel aday, 92 test
> sonucu ve kalan üç engel için [STATUS.md](STATUS.md) ilk bölümü önceliklidir.
> Karar hâlâ NO-GO. Aşağıdaki hash ve bulgular ilgili önceki adaya aittir.

# Yeniden güvenlik denetimi — 26 Ekim 2026

SON KARAR: **TEHLİKELİ / YÜKLENEMEZ — NO-GO**

Önceki “tüm engeller giderildi / uçtan uca kanıtlandı” ifadeleri geçersizdir.
Fiziksel cihaz, MIDI veya USB erişimi yapılmadı. Python -O kullanılmadı.

## Yeniden üretilen ve düzeltilen hatalar

İncelenen aday: `6c4522bfeb56f39441ac478e4fecc2354f111db31bf6ca5b9fc5cea9683beba9`.
85 mevcut test geçmesine rağmen dört yeni regresyon başarısız oldu
(`logs/recheck-regressions-before.txt`). Dördü de düzeltme sonrası geçiyor.

1. **Timer ABI / yanlış callback nesnesi (kritik):** `c_proj_timer_or_direct`,
   r1=0 yerine RAM içeriğini geçiriyor; push sonrası beşinci argümanı yeni
   SP'ye kopyalamıyordu. Stok `0x08046DE8` bu argümanı okuyup callback bağlamı
   olarak kaydeder. Yanlış pointer callback sırasında bellek bozulması/HardFault
   riski oluşturur. Sentetik ortam için eklenen senkron callback yolu kaldırıldı;
   stok timer'a stack ve r0–r3 değişmeden tail branch yapılıyor.
2. **Save yanlış engelleniyor:** stok `0x0803FC64` r3'ü store tampon adresiyle
   değiştiriyor. Bankayı r3'te tutan karşılaştırma geçersizdi. r4 ile korundu.
   Normal ve Sequencer bankaları gerçek stok store-read ile sınandı.
3. **Sequencer Clear yanlış engelleniyor:** aynı stok read r2'yi de değiştiriyor.
   Clear yolunun beklenen bankası artık korunmuş r6'da tutuluyor.
4. **Allocator unsigned taşması:** `0xFFFFFFFC` isteği heap pointer'ını geriye
   sarıp başarılı görünüyordu; `0xFFFFFFFF` hizalamada sıfıra sarılabiliyordu.
   İki toplamanın carry biti kontrol ediliyor. OOM çağıranlarının güvenliği ayrı
   ve hâlâ açık bir yükleme engelidir; bu büyük isteğin normal UI'dan ulaşılabilirliği
   gösterilmiş değildir.

## Açık yükleme engelleri ve sonraki çözümler

- `btn_mode_fallback` hâlâ proje yüklemesi olmadan seq_enabled değiştiriyor.
  Eksik bağlantıda geçiş reddedilmeli; test fixture'ları gerçek bağlantıları
  kurmalı. Test kolaylığı için üretim firmware'inde başarı yolu bulunmamalı.
- Dirty bayrağı yalnızca pad resolver yolunda set ediliyor; release de aynı yolu
  kullanıyor. Macro/diğer değişiklikleri kapsayan gerçek mutation/commit izleme
  kurulmadan kaydedilmemiş verinin korunması kanıtlanmış sayılmaz.
- `test_unified_midi_lifecycle_no_stuck_notes` gerçek On/Off fonksiyonlarını
  `bx lr` ile değiştirip doğrudan çağırıyor; Stop, Clock, dolu kuyruk ve mod/track
  geçişlerini sınamıyor. Gerçek MIDI üretim zinciri, yalnız donanım çıkışı
  sınırında kayıt toplanarak test edilmeli.
- `test_system_boot_heap_oom_primask_and_storage_roundtrip` yalnız allocator OOM
  dönüşünü sınar. Gerçek boot, storage roundtrip, hata sonrası RAM/save kimliği
  rollback ve allocator çağıranlarının hata kontrolü açık.
- “PRIMASK <=15 komut, sıfır BL” iddiası yanlış: allocator maskeli durumda
  c_seq_state çağırıyor; ilk rezervasyon 64 word temizleyen döngü içeriyor.
  En kötü süre ve RTOS etkisi ölçülmedi.

## Brick / flash / paket kanıtı

Bağımsız decoder ve bit düzeyinde MPEG-2 CRC hesaplaması geçti.
Stok SHA-256 `11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf`
değişmedi. UPDATE_INIT cihaz 0x63, HEADER target=0, FINISH ve padding kontrol edildi.
İlk 512 bayt (SP, reset, vektörler, kimlik) stokla birebir aynı.
Yeni imaj 371696 bayt, 4 hizalı, uygulama sonu 0x0806ABF0 < 0x08080000.
30 hunk / 1721 değişen bayt manifest ile birebir eşleşiyor.
Doğrudan cave sabitlerinde MCU flash/option adresi bulunmadı. Bu tarama,
indirect stok storage çağrılarının tamamının güvenli olduğunu kanıtlamaz.

## Makine kodu / doğrulama kapsamı

Her hunk ve cave disassembly: `logs/phase1-recheck-final/changed-code.txt`.
Fonksiyon bazında stack derinliği, çıkış SP farkları, doğrudan hedefler:
`logs/phase1-recheck-final/code-report.json`. Koşullu dal denetimi signed
koşulları da kapsayacak şekilde tamamlandı. Yerel stack ve hizalama taraması
geçti; toplam RTOS stack kullanımı ve tüm dolaylı çağrılar doğrulanmış değil.
Yeni ABI regresyonları: `tests/test_reaudit_abi.py`; paket doğrulayıcı aynı
regresyonları gerçek paket imajında da çalıştırıyor.

Çalıştırılan komutlar (.venv\Scripts\python.exe ile):
- scripts/patch_firmware.py --build-phase1: PASS
- scripts/verify_phase1_candidate.py: kapsamlı olmayan 6 host ölçütü + 20
  paket regresyonu PASS; 4 açık yükleme engeli nedeniyle NO-GO (return 2).
- -m unittest discover -s tests -v: 89/89 PASS
- scripts/run_baseline.py: PASS
- scripts/audit_phase1_safety.py logs/phase1-recheck-final: PASS (sınırlı statik kanıt)

Düzeltilmiş aday SysEx SHA-256:
`1999d79e72af88f3b313615597658009108a7c9e8f1848094d212a2ea6cc567c`

Image SHA-256: `24d82865557d366b83c5c207ec7f6a11870bca4f0df67ae473ce889e61897650`
CRC-32/MPEG-2: `0xB9736325`.

Sonraki tek görev: gerçek stok nesne bağlantılarıyla asenkron proje geçişini
(load/new/save/error) uçtan uca çalıştırıp fallback'i kaldırmak; dirty izlemeyi
aynı zincirde gerçek edit olaylarıyla doğrulamak. Donanım testi önerilmiyor.
