> Devam:USB inquiry retry için ayrı cursor/token prototipi17 testle doğrulandı;
> toplam230 PASS. Genel realtime hizmeti ve deferred Note On sırası FAIL,
> DIN input/üretim entegrasyonu açık. Güncel:STATUS.md ve
> MIDI-USB-INQUIRY-RETRY-5706.md. Aşağıdaki213 testlik kayıt önceki deneydir.

# 27 Ekim 2026 — Formatter öncesi kapasite rezervasyonu / NO-GO

Bu çalışma pin'li stok baytları/Capstone ve sentetik RAM'de Unicorn kanıtıdır.
Fiziksel cihaz, MIDI/USB portu veya donanım API'sine erişilmedi. Üretim
firmware'i değişmedi; M7 tamamlanmadı. Normal/Sequencer ortak proje kapsamı,
stok64 slot ve sıfır proje I/O'suyla mod değişimi aynı kaldı.

## Bulunan iki ayrı sınır

Önceki12 doğrudan üretici guard'ı, `4691A` çağrısından önce çalışan üst
formatter'ları korumuyordu. `32120` ailesi payload'ı ortak kaynağa yazar;
ancak sonra `4691A` üzerinden kuyruk kabulünü dener. Kuyruk doluyken veya
nested başka formatter aynı kapasiteyi alırken kaynak önceden değişebilir.

| Üst giriş | Formatter | `4691A` sonrası LR | Stack argümanı sayısı |
|---|---|---|---|
| `08032120` | `08046A54` | `08032151` | 2 |
| `08032154` | `08046B18` | `08032185` | 2 |
| `08032188` | `08046B50` | `080321B9` | 2 |
| `080321BC` | `08046B74` | `080321F1` | 3 |
| `080321F4` | `08046BAC` | `08032225` | 2 |

Diğer sınır native input dağıtımıdır: USB `29BAA` ve DIN `29C64`, tamamlanmış
SysEx mesajını `24B68` registry'sine yollar. Dispatcher listener r0 sonucunu
yok sayar. Genel `26DE8` de `26F0C` inquiry yanıtının sonucunu kullanmaz.
Dolayısıyla formatter'ın güvenli ret1 vermesi, tüketilmiş RX isteğini tutmaz.

Sonucu yok sayan üç response üreticisinin aday çapraz referansları:

- `26F0C`, universal inquiry: tek doğrudan çağrı `26E4C`.
- `2CD60`, nibble response: `2CD1A` üzerinden `2CD58` çağrısı.
- `2D0B0`, update ACK: `43544/435D6` çağrıları native update yan etkilerinden
  sonradır. Bu handler'lar **yalnız disassemble edildi**, yürütülmedi.

Bu tarama bütün dolaylı çağrı grafiği değildir. Read-only trace script'i
`trace_midi_sysex_requests.py`, beklenen callsite listesini pin'li stokta
assert eder ve ilgili pencereleri saklar.

## Deneysel rezervasyon varyantı

`arm_code(notifications=True, reservations=True)` eklenir. Beş üst girişte
özgün prologue baytları assert edilerek yalnız Unicorn overlay kurulur.
Diğer varyantlar aynı1750B/2050B kodu aynı hash ile üretir.

- `sr_request_begin`, formatter'dan önce boş slot/producer durumunu, kayıtlı
  router'ı, seçili port maskesi/context/fault durumunu kontrol eder. PRIMASK=1,
  IPSR!=0 veya dolu/rezerveli kuyruk reddedilir. Bekleme döngüsü ve I/O yoktur.
- Başarılı rezervasyon, beklenen native alt çağrı dönüş PC'sini tek word'de
  tutar. Başka üst formatter, doğrudan `sr_submit` veya native alt producer
  bunu kullanamaz. `4691A` guard'ı çağrı dönüş PC'sini; router submit'i de
  kendi doğrulanmış gate dönüş PC'sini ve producer-busy durumunu denetler.
- Native üst gövde, r0-r3 ve stack'teki5..7. argümanlarıyla yürür. Callback,
  context ve üçüncü stack argümanının yeri korunur. Native r0 sonucu korunur.
  Rezervasyon üst gövde döndüğünde temizlenir; aktif payload slotta kalır.
- `sr_service`, üst formatter rezervasyonu sürerken bildirim/gönderim yapmaz.
  Sonraki poll, önceki port bazında retry ve sahipli event0 davranışını sürdürür.
- Ret1 durumunda kaynak tampon ve global callback sahibi değişmez. Çağıran
  ancak ret'i işleyip daha sonra aynı isteği sunarsa yanıt alınır. Otomatik
  RX retry veya sınırsız tampon eklenmez.

Return-PC kontrolü beş pin'li main-context zinciri içindir. Genel thread
sahipliği veya gerçek NVIC/RTOS task-switch kanıtı değildir. IPSR testi yalnız
Unicorn register değeriyle yapılır. Tam lifecycle/başka yazarlar hâlâ açıktır.

Kod **2878B**, retry arena **428B**; recovery832B ile **1260B sentetik RAM**.
Yeni alan, önceki arena sonundaki4B rezervasyon word'üdür. `20047800/20047000`
üretimde boş RAM değildir; checked heap/atomik init/full boot-OOM yoktur.
Üretim patch listesine veya `.syx` dosyasına hook eklenmez.

## Test edilen davranış

`test_midi_sysex_request_reservation.py`,11 test ve çoklu alt vakalar:

- Beş gerçek üst formatter'ın yeni/eski varyantlarda aynı r0/payload/mask
  ve port baytları; callback/context ve stack argümanı konumları.
- Full slotta kaynağa dokunmadan ret1; geçersiz source/controller pointer'ları
  bile full durumda dereference edilmez. Drain sonrası açık çağıran retry'si
  doğru bir yanıt ve callback üretir.
- Eski yalnız alt guard'da üst source mutasyonu; nested üst formatter'ın
  boş kapasiteyi alıp dış isteği reddettirmesi negatif kontrol olarak kalır.
  Rezervasyonlu varyantta dış istek kabul, nested istek ret olur.
- Formatter penceresinde doğrudan submit/service, alt `4691A`, başka native
  producer ve üst formatter rezervasyonu alamaz; dış payload sahibi korunur.
- Disabled response, PRIMASK/IPSR, bilinmeyen router/token, seçili fault;
  rezervasyon sızıntısı veya yanlış bildirim yok. Seçilmemiş port fault'u
  sağlıklı seçili porta yanıtı engellemez; fault recovery Stop'u korunur.
- Native USB staging ve iki DIN ring doluyken120B yanıt; ikinci istek kaynak
  değişmeden reddedilir. Drain ve açık retry sonrası iki yanıtın tam USB
  packet/DIN byte eşleşmesi, callback sahipleri ve raw proje baytları.
- Native USB ve DIN byte parser/dispatcher'ında universal inquiry
  `F0 7E 7F 06 01 F7`: TX doluyken istek tüketilir, yanıt gelmez ve otomatik
  retry olmaz. Boşaldıktan sonra açık yeniden gönderim17B identity reply
  üretir. Bu pozitif kontrol, kaybın yanlış query/fixture nedeniyle olmadığını
  gösterir; negatif kabul sonucu **FAIL** kalır.

Ingress deneyinde registry'ye yalnız read-only `26F0C` inquiry listener'ı
bağlanır; tam `26DE8` handler zinciri ve storage/update yolları yürütülmez.
USB, zaten alınmış packet baytlarından başlar; DIN, parser'a verilen byte
baytlarından. Native FIFO/driver formatter'ları çalışır; endpoint submit ve
UART IRQ sınırları mevcut fixture ile modellenir. Wire/IRQ/full boot değildir.

Yerel Capstone/CFG audit: tüm2878B decode,17 overlay'de bayt/app/overlap ve
trampoline/BL hedefi kontrolü; SP çıkış deltası0, BL/BLX stack hizası8,
max yerel frame48B. IRQ-mask yollarında call/loop yok,max22 komut. Üst gövde,
native callee ve callback dahil toplam stack/cycle veya PRIMASK süre bütçesi
kanıtlanmaz. Audit artık SP add/sub frame'lerini de izler.

## Komutlar ve sonuçlar

Bütün Python komutları `.\.venv\Scripts\python.exe` ile, `-O` olmadan:

```powershell
.\.venv\Scripts\python.exe scripts/patch_firmware.py --build-phase1
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/verify_phase1_candidate.py
.\.venv\Scripts\python.exe scripts/run_baseline.py
.\.venv\Scripts\python.exe scripts/audit_phase1_safety.py logs/recovery-sysex-request-20261027/production-audit
.\.venv\Scripts\python.exe scripts/probe_midi_recovery_prototype.py logs/recovery-sysex-request-20261027/recovery-probe
.\.venv\Scripts\python.exe scripts/probe_midi_sysex_retry_prototype.py logs/recovery-sysex-request-20261027/retry-probe
.\.venv\Scripts\python.exe scripts/probe_midi_sysex_notification.py logs/recovery-sysex-request-20261027/notification-probe
.\.venv\Scripts\python.exe scripts/probe_midi_sysex_request_reservation.py logs/recovery-sysex-request-20261027/probe-final
```

**213 toplam test PASS**, önceki202 +11. Aday87 regresyon/6 sınırlı kriter
PASS; Off/Stop probe'ları FAIL, verifier exit2/NO-GO. Build/baseline/üretim
binary audit PASS. Önceki24/14/11 deneysel testler kendi probe'larında PASS;
hepsi NO-GO/exit2 kalır. Yeni probe paketlenmiş imaj üzerinde11 testi yalnız
Unicorn overlay ile tekrar koşar:

| Alan | Sonuç |
|---|---|
| tested_upper_reservation_before_source_mutation | PASS |
| reserved_capacity_not_stolen_by_nested_calls | PASS |
| explicit_caller_retry_after_drain | PASS |
| legacy_upper_source_preservation | FAIL |
| native_usb_din_consumed_request_retry | FAIL |
| production_caller_compatibility | FAIL |
| production_integrated / hardware_release | false / NO-GO |

Loglar `logs/recovery-sysex-request-20261027/` altında; `all-tests.txt`,
`verify.txt`, `build.txt`, `baseline.txt`, `audit.txt`, üç eski probe log'u,
`request-probe.txt`, `probe-final/{report,retry-code-report}.json` ve
`probe-final/stock-contract/`. Verifier:
`logs/phase1-verification-20261027T163133Z/report.json` (UTC).
Oturum farkı `session.diff`, hash listesi `session-hashes.json`.

İlk genişletilmiş koşuda üç fixture beklentisi yanlıştı: native-router capture,
doğrudan `sr_submit` girişini saymaz; ilk poll yalnız transferi bağlar;
fault recovery portuna Stop ekler. Capture1, ikinci poll ve beklenen Stop
baytı ile düzeltildi. Native/full-slot/negatif başarı şartları gevşetilmedi;
`tests-expanded-first.txt` FAIL kaydı korunur.

- Rezervasyonlu kod SHA256: `321fca8a65d1ef9c99b0cf05ed1e7bd61ccf128ee06d8891ad0fe3e52b53141a`.
- Bildirimli önceki kod SHA256: `c541d9d2c207f8230c75466b52342698e464a2077a7afa426c3bbaee9fb4fbe0`.
- Bildirim kapalı kod SHA256: `ae8d859e129a72bb02e6e6916ac7ca6a256b30dc6699ff612eacc84ae617b266`.
- Değişmeyen aday SHA256: `3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d`.
- Image SHA256: `38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf`.
- CRC `53F96711`,371368B image,21 patch,1376B fark.
- Stok SHA256: `11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf`.

## Sonraki somut iş ve açık kapılar

**Sonraki tek iş:** native USB RX cursor/pop/ack noktasında, TX doluyken
universal inquiry isteğinin sahipliğini tutan sınırlı retry prototipi kurmak;
aynı girişte interleaved Clock/Stop hizmetinin durmadığını emülasyonda
doğrulamak. İsteği tüketip listener ret'ini yok saymak bu davranışı sağlamaz.

GO için ayrıca DIN RX ve bütün request/response/update ACK yaşam döngüsü;
tüm producer ve üretim SysEx/recovery entegrasyonu;1260B checked heap/atomik
init; mode guard/reset-resume; stok storage hata-kurtarma; tam boot/OOM ve
gerçek IRQ/DMA/USB-disconnect/PRIMASK süre bütçesi açık. Donanıma yüklenmemeli.
