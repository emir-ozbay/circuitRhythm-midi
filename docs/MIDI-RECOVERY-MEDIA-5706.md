# Native NOR/FatFs ve CTRL_SYNC scratch düzeltmesi — 5706

30 Ekim 2026. **M7 NO-GO.** Bu tur aday firmware değişti. Stock dosya aynı;
fiziksel MIDI/USB/cihaz API'sine erişilmedi.

## Kapanan iki sorun

Eski QSPI modeli DMA transfer verisini RAM'e taşımadan TC bildiriyordu.
İlk23B okumadan sonra DMA stream7 EN/NDTR de açık kalıyordu; sonraki4096B
okumalar eski descriptor/veriyle tamamlanmış görünüyordu. Yeni model veri
aktarır, EN/NDTR'yi bitirir, native DMA2 stream7 ve QSPI IRQ yollarını yürütür.
TCIE ve SMIE ayrı ele alınır;auto-poll match için transfer IRQ'su üretilmez.
Bu host model düzeltmesidir, firmware yaması değildir.

Native bölüm tanımı `20000AA8`: NOR offset `D4000`, sektör4096B. Scripted
JEDEC `EF4018` ile16MiB NOR modellenir. Sentetik FAT12 girişinde yalnız
`Rhythm/00_INIT` dizinleri vardır. Native FatFs mount/scan/create/save kodu
çalışır; dosya API dönüşleri veya ownership nesneleri host tarafından verilmez.
Native `2E2F6` owner `2000E98C+3C` alanını `2000D8D8` root'una bağlar.
Silinmiş NOR'da bağlama olmaz;eksik DMA verisi tamamlanma öncesi reddedilir.

Geçerli medya sonraki gerçek hatayı ortaya çıkardı: FatFs `CTRL_SYNC0`,
`buff=NULL` ile `23168` disk_ioctl adaptörünü çağırır. Adaptör bunu fiziksel
query1'e iletir. Native `41AA2` sıfır adrese bayt yazar;ayrıca adaptörün
`231C8` diagnostic yolu aynı buffer'dan word okur. Stock ve önceki recovery
aynı sentetik geçerli medya üzerinde ilk yazıda durur.

## Firmware düzeltmesi

`23168`'deki asserted4B prologue, `7FE24` adresindeki20B helper'a gider.
Helper orijinal24B frame'i kurar. Yalnız command0/bufferNULL için frame'in
kullanılmayan R3 word'ünü sıfırlayıp R2'ye bu adresi verir. Native Storage
isteği tamamlanana kadar frame yaşar;query ve diagnostic aynı geçerli sink'i
kullanır. Sonra tamamen native gövde/epilogue devam eder.

- Ek stack/heap/reserved RAM:0. Ek maskeli bölüm,loop veya çağrı yoktur.
- Non-NULL CTRL_SYNC ve diğer sorguların output,callee-saved register,SP,
  NZCV ve PRIMASK davranışı stock ile kıyaslanır.
- Çıktı gerektiren başka sorgudaNULL hâlâ başarısızdır;genel başarı zorlanmaz.
- Native `41A80..41AC2` query gövdesi ve ioctl'nin kalan gövdesi aynıdır.
- İlk query-store'u tek başına atlayan prototip diagnostic NULL okumasını
  çözmedi;final aday bu prototipi içermez. Page-zero mapping yapılmadı.

Bu uygulama adaptörü korumasıdır;FatFs/SD filesystem uygulaması değiştirilmedi.
Yamanın fiziksel davranışı henüz cihazda doğrulanmadı.

## NOR modeli ve kanıt

NOR program/erase için WEL gerekir;program en fazla256B ve tek sayfadır.
0→1 program reddedilir;4KiB silme1'leri geri getirir. Sınır dışı erişim
reddedilir. Değişiklikler yalnız emüle NOR bytearray'ine uygulanır.
DMA veri adresi/sayısı/yönü ve gerçek descriptor ile eşleşir;native kontrol
bayraklarına yalnız native IRQ yazar. QSPI IRQ'larında önceki context/MSP
adaptörü kullanılır;tam exception-frame/NVIC/timing kanıtı değildir.

Stock ve eski recovery:189 QSPI event/51 NOR mutation sonrası `41AA2` NULL
yazımı. Yeni aday:972 event/338 DMA IRQ/306 native NOR mutation;4 NULL-sync
çağrısı scratch ile tamamlanır.1296 tahsis/heap `20043D78`;eski sıra/adresler
aynı. Yeni boot'ta emüle NOR korununca32 event,0 yeni mutation ile bağlama
yeniden yapılır;RAM nesnesi veya TCB seed edilmez.

| NOR girdisi | SHA256 |
| --- | --- |
| Sentetik başlangıç |8e963d1c1b63273c1a563fccee483f92bbb6c8a2539cfcd29a1af35b8eecc1a8 |
| Native yazımlar sonrası /reboot |b8ade7b2b1bded4c8e2ea97c092107702eef680c4ada4bfe3de5247af35e9f5a |

Aday minMSP `2004FF08`;Main alt adres `200081D8`,UI `200090B4`,Storage
`200095A4`,Content `20009938`,IDLE `2000B564`. Canary/firmware bütünlüğü
korunur. Tam boot/son heap/fiziksel maksimum stack ölçümü değildir.

## Yeni sınır

Medya ownership NULL ve CTRL_SYNC hataları bu fixture'da kapandı. Native
`3150C` bellek selector'u `8B7300` gönderir;dönüşü kullanılmaz ve bu ayrıca
static proof'a eklenir. Sonraki `31516` sorgusu `400000` yanıtını `3151A`'da
kullanır. Yardımcı işlemci belleği `37300` henüz modellenmedi;wire/RAM/TC
yazısından önce durulur. **Main25864 henüz yoktur.**

**Sonraki tek iş:** Native yardımcı işlemci memory37300 okumasının tüketicisini
ve önceki yazımlarını izlemek. Keyfi sıfır/ready yanıtı verme;DSP programı
yürütülmüş sayılmaz. Önceki802B-ready ve takılı host olmayan USB core ACK
varsayımları,ADC/calibration ve no-response SDIO sınırları sürer.

## Aday ve test

- SYX SHA256: `07c2305d9eaf8c3e8d55981fd6e6d0fa81ab3c20c42294c6d26c124a02dd6e07`
- Image SHA256: `a32b3239bfa03c24e67ddac177d69da639f03d78ea5c0629fc849b5da05cfb94`
- CRC MPEG2 `0CD0D008`;image458296B/SYX630213B;42 patch/7546 değişen bayt.
- Default/legacy seq/core/glue/accepted guard ve reserved1088B boyutu aynı.

4 query/ABI ve6 media testi;141 odaklı/112 packaged ve6 sınırlı Faz1 ölçütü
PASS. Sayılar örtüşür. Discovery630;tam630 koşulmadı. Strict CRC/vector/range /
CFG/ABI ve helper'ın4/5/8 komutluk üç yolu denetlendi. Önceki529/98 kayıtları
korunur;tamamı güncel SYX değildi.

`.venv\Scripts\python.exe` (`-O` yok):

- `scripts/build_recovery_candidate.py`
- `scripts/probe_recovery_media.py logs/recovery-media-20261030/probe`
- `-m unittest test_flash_query test_recovery_media -v` (`PYTHONPATH=scripts;src;tests`)
- `scripts/audit_recovery_candidate.py logs/recovery-media-20261030/audit`
- `scripts/verify_recovery_candidate.py logs/recovery-media-20261030/packaged`

Probe/verifier exit2 NO-GO'yu korur. Before/after SYX,153 source pin,exact
diff/hash/kanıt: `logs/recovery-media-20261030`. [STATUS.md](STATUS.md).
