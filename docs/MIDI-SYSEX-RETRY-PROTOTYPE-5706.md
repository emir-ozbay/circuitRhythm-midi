# Güncel devam — Formatter öncesi rezervasyon / NO-GO

213 toplam test/87 aday PASS. Beş üst formatter için rezervasyon2878B kod/
428B retry RAM kullanır;recovery ile1260B sentetik RAM. Eski1750B/2050B
varyantlar aynı hash'lerdedir. Native USB/DIN isteği tüketip ret'i yok sayar;
otomatik request retry FAIL,üretim aynı,M7 NO-GO. Güncel kanıt:
[MIDI-SYSEX-REQUEST-5706.md](MIDI-SYSEX-REQUEST-5706.md).

---

# Önceki devam — Sahipli native kabul bildirimi / NO-GO

Yeni notifications=True varyantı2050B kod/424B retry RAM,toplam1256B sentetik
RAM kullanır. Event/owner snapshot'ı ve native24B68 ile tek kabul bildirimi
11 yeni testle doğrulandı;202 toplam/87 aday regresyonu PASS. Varsayılan
notifications=False aşağıdaki1750B kodu aynı hash ile üretir ve eski negatif
kontrolleri korur. Bu zincirde ayrı gecikmiş job bildirimi bulunmadı:299B0
event0'ı port kabulünde senkron verir. Önceki job/completion yorumu güncellendi.
Request geri basıncı/upstream formatter ve üretim kapıları açık;M7 NO-GO.
Güncel kanıt:[MIDI-SYSEX-NOTIFICATION-5706.md](MIDI-SYSEX-NOTIFICATION-5706.md).
Aşağıdaki kayıt bildirim kapalı önceki varyantı belgeler.

---

# 27 Ekim 2026 — SysEx çağıranları ve sınırlı tekrar denemesi / NO-GO

Bu çalışma yalnız pin'li stok baytları/Capstone ve sentetik RAM'de Unicorn
kanıtıdır. Fiziksel cihaz, MIDI/USB portu veya donanım API'sine erişilmedi.
Üretim builder'ı ve firmware baytları değişmedi. M7 tamamlanmadı.

Önceki `midi_recovery_prototype.py` (1140B kod/832B RAM) korunur. Yeni
`midi_sysex_retry_prototype.py` ayrı, **açık sözleşmeli deneysel API** ekler;
stok `298B8` router'ın doğrudan üretim karşılığı değildir.

## On iki gerçek çağıran

Adresler tam uygulama adresidir. Pin'li disassembly ve gerçek çağırana router
sonucu 0/1 enjekte edilerek doğrulanır. Hiçbiri yerel retry yapmaz. Sonucu
ileten dokuz çağıranın üst katmanlarının sonucu işlediği iddia edilmez.

| Giriş | Router çağrı noktası | Payload kaynağı | Router sonucu |
|---|---|---|---|
| `08026F0C` | `08026F32` | flash | yok sayılır |
| `0802CBB8` | `0802CBF0` | statik tampon | iletilir |
| `0802CD60` | `0802CDA2` | statik tampon | yok sayılır |
| `0802CDF8` | `0802CE64` | stack | iletilir |
| `0802CEE4` | `0802CF38` | stack | iletilir |
| `0802D0B0` | `0802D0F0` | statik tampon | yok sayılır |
| `0802D0F8` | `0802D12C` | statik tampon | iletilir |
| `0802D134` | `0802D1CC` | statik tampon | iletilir |
| `0802DE84` | `0802DE8C` | ödünç pointer | iletilir |
| `0802ED88` | `0802EDA2` | ödünç pointer | iletilir |
| `08042160` | `080421B0` | statik tampon | iletilir |
| `0804691A` | `08046954` | ödünç pointer + global callback | iletilir |

`46934/46938`, router kabulünden **önce** callback function/context çiftini
`0x20006EE0/+4` adresine yazar. `468EC`, bildirim geldiğinde o anki global
çifti okur. Dolu kuyrukta reddedilen yeni istek, önceki isteğin callback
sahibini değiştirebilir. Negatif test native `468EC` ile yanlış yeni callback
ve context'in çağrıldığını gösterir.

`2629E` kurucusu `0x20000920` callback nesnesini router+20'ye, `24151` wait
yardımcısını +1C'ye bağlar. Native `299B0` başarı yolu router+19'u değiştirir
ve callback slot4'ü r1=0 ile çağırır. Bu bildirimin tam job/request yaşam
döngüsü yeni API'ye bağlanmadı; native başarı bildirimi uydurulmaz.

## Ayrı API ve veri sahipliği

Tek işlem yuvası, en fazla 360B payload. Yeni kod 1750B, ek sentetik RAM 384B;
recovery ile toplam **1216B sentetik RAM**. `0x20047800` ve recovery'nin
`0x20047000` adresleri üretimde boş alan değildir. Checked heap rezervasyonu,
atomik boot initialization ve OOM davranışı kanıtlanmadan kullanılmaz.

- `sr_submit(router, mask, descriptor)`: 0 yalnız yerel sahipli kopya kabulü,
  1 ret. Bütün portların kabulü, native callback veya wire tamamlanması değildir.
  Mask stok broadcast için `&7`; boş seçim reddedilir. Length 2..360, F0/F7,
  ara 7-bit veri ve seçili recovery context/fault doğrulanır. Çağıranın geçerli
  descriptor/payload adresleri sağlaması gerekir; keyfî pointer güvenliği yoktur.
- Payload dönüşten önce IRQ açıkken native `22CF0` ile kopyalanır. Metadata
  kısa atomik bölümde yayınlanır. Sonraki stack/source değişimleri sahipli
  payload'ı etkilemez. Busy/full/PRIMASK=1 girişleri reddedilir.
- `sr_service(router)`: her bekleyen port için en fazla bir bağlama denemesi,
  toplam en fazla üç; kabul edilmiş port tekrar gönderilmez. Dış poll daha
  sonra yeniden çağırır. Yeni kuyrukta senkron bekleme döngüsü yoktur.
- WAITING/ACCEPTED/FAILED maskeleri kısmi fanout sahipliğini tutar. Slot ancak
  bütün seçili portlar kabul edip native payload okuyucuları bitince boşalır.
  USB staging'in kendi kopyası hâlâ in-flight olabilir; bu wire teslimi değildir.
- Fault kalan yükümlülüğü pin'ler; otomatik cancel/reset/resume yoktur. Bozuk
  aktif metadata I/O yapmadan BAD_STATE üretir. REJECTED/REENTRANT/PORT_FAULT
  tanıları kalıcıdır. `sr_service` busy iken 0 dönebildiğinden dönüş değeri tek
  başına tamamlanma değildir; status/ACTIVE esas alınır.

## Formatter girişinden önce koruma

Yalnız kuyruk girişini kilitlemek yeterli değildir: nested native formatter,
ilk isteğin statik kaynağını kopya başlamadan ezebilir. Buna karşı 12 üretici
girişine isteğe bağlı **yalnız Unicorn overlay** eklenir. Guard; aktif işlem,
kopya/üretici busy, PRIMASK=1 veya kayıtlı router uyuşmazlığında formatter ve
global callback yazılarından önce reddeder. Native sonuç korunur.

Her girişte özgün dört bayt assert edilir; overlay çakışmaları/app sınırı
kontrol edilir. Native prologue trampoline'de tekrar yürütülür. `DE84` ve
`ED88` PC-relative literal yükleri açıkça taşınır ve stok literal değerleri
assert edilir. Yeni kod/recovery code cave ve RAM çakışmaları reddedilir.
Bu overlay'ler PatchHunk listesine veya `.syx` dosyasına eklenmez.

Guard aktif işlem sırasında önceki callback sahibini korur. **Native payload
okuyucularının bitmesiyle job bildiriminin bitmesi aynı olay değildir.** Slot
yeniden kullanımı sonrası callback sahibi ve bildirim sırası hâlâ açık kapıdır.
Dolaylı üreticiler, bütün kaynak yazarları ve gerçek IRQ/task grafiği kanıtlanmadı.

## Testler ve negatif kontroller

`test_midi_sysex_retry_prototype.py`: 14 test, çoklu alt vakalar:

- On iki gerçek çağıranın 0/1 dönüşü; stack/ödünç/statik kaynağın dönüşten
  sonra ezilmesine rağmen üç portta doğru sahipli baytlar.
- Bir port hazır değilken diğer ikisine tek teslim; yalnız kalan porta retry.
  Full slot ret, reader bitişine kadar reuse yasağı, fault yükümlülüğü.
- Native memcpy/port-send sınırında nested submit/service; PRIMASK, SP,
  metadata, canary ve geçersiz bounds kontrolleri.
- Gerçek native USB/DIN sürücü kodunda önceki 200B SysEx ile stall; yeni
  360B payload ve sonra 3B mesaj. USB hâlâ in-flight iken güvenli sahiplik
  devri; tam USB packet/DIN byte eşleşmesi ve raw proje baytlarının korunması.
- Guardlı/guardsız on iki çağıranın sağlıklı payload, mask ve r0 eşleşmesi.
  Nested formatter ezilmesi ve aktif callback sahibinin değişmesi, guard
  kapalıyken yeniden üretilir; guard açıldığında önlenir.
- Sonucu yok sayan üç çağıranın dolu slot yanıtı **kaybolur**. Bu karşı deney
  kaldırılmadı; testin PASS olması teslim güvenliğinin PASS olması değildir.

Fixture yalnız response formatter'larını yürütür; storage/flash-update
request handler çalıştırmaz. `CDF8` için palette yazan branch2 yerine branch3
kullanılır. `D134` version response, sentetik boot header okur; `43A94`
selector boundary stub'dır. Gerçek boot, bütün branch'ler veya native callback
eşdeğerliği kanıtı değildir. Poll sırası sentetik scheduler'dır; native USB
endpoint submit/DIN IRQ-enable sınırları önceki fixture ile modellenir.

Yerel Capstone/CFG audit: bütün kod decode edilir; doğrudan hedefler ve
trampoline baytları doğrulanır; SP çıkış deltası 0, BL stack hizası 8,
en büyük yerel frame 32B. Zorunlu IRQ-mask yollarında call/loop yok, en fazla
14 komut. Bu sayı cycle/süre veya native callee toplam stack bütçesi değildir.

## Tekrar üretme ve sonuçlar

Bütün Python komutları `.\.venv\Scripts\python.exe` ile, `-O` olmadan:

```powershell
.\.venv\Scripts\python.exe scripts/patch_firmware.py --build-phase1
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/verify_phase1_candidate.py
.\.venv\Scripts\python.exe scripts/run_baseline.py
.\.venv\Scripts\python.exe scripts/audit_phase1_safety.py logs/recovery-sysex-retry-20261027/production-audit
.\.venv\Scripts\python.exe scripts/probe_midi_recovery_prototype.py logs/recovery-sysex-retry-20261027/recovery-probe
.\.venv\Scripts\python.exe scripts/probe_midi_sysex_retry_prototype.py logs/recovery-sysex-retry-20261027/probe
```

191 toplam test PASS: önceki 177 + 14 yeni. Üretim adayı 87 regresyon ve
6 sınırlı kriter PASS; Off/Stop probe'ları FAIL, verifier exit2/NO-GO.
Build/baseline/üretim binary audit PASS. Eski recovery probe'un 24 testi ve
6 recovery vakası PASS, exit2. Yeni probe paketlenmiş imaj üzerinde 14 testi
overlay ile tekrar koşar; exit2:

| Rapor alanı | Sonuç |
|---|---|
| owned_payload_and_port_retry | PASS |
| guarded_formatter_reentry_and_active_callback_owner | PASS |
| unguarded_formatter_source_preservation | FAIL |
| unguarded_active_callback_owner_preservation | FAIL |
| ignored_full_queue_response_delivery | FAIL |
| native_completion_callback_contract | NOT_IMPLEMENTED |
| production_caller_compatibility | FAIL |
| production_integrated / hardware_release | false / NO-GO |

Loglar `logs/recovery-sysex-retry-20261027/` altında. `probe/report.json`,
`probe/retry-code-report.json`, `probe/stock-contract/`, `all-tests.txt`,
`verify.txt`, `build.txt`, `baseline.txt`, `audit.txt`, `recovery-probe.txt`
ve mevcut ilk denemeler korunur. Verifier raporu
`logs/phase1-verification-20261027T100454Z/report.json`.
Session kaynak/doküman farkı `session.diff`, hash listesi `session-hashes.json`.

- Yeni deneysel kod SHA256: `ae8d859e129a72bb02e6e6916ac7ca6a256b30dc6699ff612eacc84ae617b266`.
- Değişmeyen aday SHA256: `3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d`.
- Image SHA256: `38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf`.
- CRC `53F96711`, image 371368B, 21 patch, 1376 değişen bayt.
- Stok SHA256: `11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf`.

## Başarısız varsayımlar ve sonraki iş

Kör router retry kısmi fanout'u çoğaltır; dönüşten sonraki stack kaynağı
geçerli değildir. Kuyruk giriş kilidi formatter/global callback yazıları için
çok geçtir; erken giriş korumaları test edilen ezilmeyi kapatır. Sonlu tampon
tek başına, reddi yok sayan isteğin yanıtını koruyamaz. Bu karşı örnekler test
ve raporda kalır; üretim kabulü olarak sunulmaz.

**Sonraki tek somut iş:** native router+20 bildirim nesnesi ile `468EC`
job callback zincirini izleyip callback function/context'i işlem sahibine
bağlayan yaşam döngüsünü emülasyonda doğrulamak. Test, payload okuyucuları
bittikten sonra gecikmiş bildirim ve yeni istek çakışmasını da kapsamalıdır.

GO için ayrıca request tarafında ret/geri basınç, tüm producer/lifecycle ve
üretim recovery/SysEx entegrasyonu; 1216B checked RAM/atomik init; mode
guard/reset-resume; miras stok storage hata-kurtarma; tam boot/OOM ve gerçek
IRQ/DMA/USB-disconnect/PRIMASK süre bütçesi gerekir. Donanıma yüklenmemeli.
