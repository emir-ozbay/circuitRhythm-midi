# Güncel devam — Üst formatter kapasite rezervasyonu / NO-GO

Yeni reservations=True varyantı beş32120..321F4 girişinde kaynak mutasyonundan
önce kapasite ayırır;2878B kod/428B retry RAM,toplam1260B sentetik RAM.
213 toplam/87 aday regresyonu PASS. Aşağıdaki2050B bildirimli varyant aynı
hash ile korunur. Native USB/DIN consumed-request retry karşı örneği FAIL;
RX cursor/pop/ack sahipliği ve üretim kapıları açıktır. Güncel kayıt:
[MIDI-SYSEX-REQUEST-5706.md](MIDI-SYSEX-REQUEST-5706.md). M7 NO-GO.

---

# 27 Ekim 2026 — İstek sahibine bağlı SysEx kabul bildirimi / NO-GO

Yalnız pin'li bayt/Capstone ve sentetik RAM'de Unicorn kanıtıdır. Cihaz,
MIDI/USB portu ve donanım API'si kullanılmadı. Üretim `.syx` değişmedi;
M7 tamamlanmadı. Önceki recovery ve bildirim kapalı retry deneyi korunur.

## Native sözleşmede düzeltilen varsayım

Önceki kayıttaki ayrı, gecikmiş bir job/wire-completion bildirimi varsayımı
bu zincirde doğrulanmadı. Native `299B0`, bütün seçili portlar kabul ettikten
sonra **aynı çağrı içinde**, payload henüz okunurken event0 bildirir.
Bu, önceki `.md` dosyalarındaki job/completion yorumundan daha güçlü ve güncel
kanıttır; tam firmware'deki bütün dolaylı olayların bulunması iddia edilmez.

| Adres | Pin'li bayt/Capstone ve emülasyon kanıtı |
|---|---|
| `08068A54` | Yalnız scatter-loader yürütüldüğünde `20000920` nesnesi `{08069460,0,0,0,0,0,0,0}` ile kurulur. Peripheral alanı emülatörde map edilmez. Tam boot kanıtı değildir. |
| `08069460` | Event vtable iki girişi: `0802D44D` listener kaydı; `08024B69` bildirim. |
| `0802D44C` | Count byte+4; üç function slotu+8/+C/+10 ve üç context+14/+18/+1C. Native kayıt yordamında kapasite kontrolü yoktur; deneysel snapshot count>3'ü reddeder. |
| `080299B0..BA` | Router+19=1; router+20 event nesnesinin vtable+4'ünü `r1=0, r2=router` ile senkron çağırır. |
| `08024B68` | Her listener'a `(r0=event0,r1=router,r2=listener_context)` gönderir; null function slotu atlanır. |
| `080468EC` | Global `20006EE0` function/context çiftini okur. Owner callback'e event byte'ı ve owner context'i iletir; r2'de function pointer kalır. |
| `0804691A` | Function/context'i kabulden önce yazar; event'in ilk listener'ını `468ED` yapar, context0; count0 ise1 yapar. |
| `080297DE` | Port poll'larını çağırır; bu yordamda ayrı completion bildirimi yoktur. |

Gerçek `4691A -> 298B8 -> 24B68 -> 468EC -> callback` testinde callback
dönüşten önce bir kez çalışır; üç portun payload sayaçları hâlâ pending'dir.
Portlar sonradan bitirilip poll tekrarlandığında ek bildirim oluşmaz.

## İsteğe bağlı deneysel düzeltme

`midi_sysex_retry_prototype.arm_code(notifications=True)` eklenir. Varsayılan
`False`, önceki 1750B makine kodunu **aynı hash ile** üretir. Bu, üretim hook'u
değildir; fixture yalnız Unicorn code/RAM/vtable overlay'lerini kullanır.

Bildirimli varyant **2050B kod/424B sentetik RAM** kullanır. Recovery'nin
832B RAM'i ile toplam **1256B**. Eski retry arena'sına40B eklenir: owner
function/context8B ve native event nesnesi32B. Header'ın önceki boş+15 byte'ı
NOTICE durumu olur. `20047800/20047000` üretimde boş RAM sayılamaz.

Submit, geçerli router+20'nin sabit `20000920` nesnesini gösterdiğini doğrular.
Vtable/count ile event ve owner çiftini kısa atomik bölümde kopyalar; callback
ve native I/O bu bölümde çağrılmaz. Snapshot'taki yalnız `468ED` listener'ları
işlem sahibini okuyan `sr_owned_callback` adaptörüne bağlanır. Diğer
function/context slotları ve dinleyici sırası korunur. Global çiftin veya
native event listesinin daha sonra değişmesi kabul edilmiş isteği yönlendiremez.

`sr_service`, WAITING sıfır olunca NOTICE=2 yapıp **native `24B68`** dispatcher'ını
özel event kopyasıyla event0 olarak bir kez çağırır. Router+19 stokta olduğu
gibi1 olur. Callback döndüğünde NOTICE=3; payload okuyucuları da bitmişse slot
boşalır. Bildirim ve okuyucu bitişi sırasında BUSY/ACTIVE korunur. Callback
içindeki yeni submit/service/formatter girişleri slotu tekrar kullanamaz.

Bu, submit0'ın anlamını değiştirmez: 0 yerel payload kopyası kabulüdür.
Servis bildirimi bütün seçili portların kabulüne ertelenir. Wire teslimi veya
USB transfer-complete ACK değildir. Kısmi fanout/fault başarı bildirimi
üretmez. Geçersiz private event count/vtable/NOTICE, I/O öncesi BAD_STATE verir.

Native callback'in recursive send bekleyebileceği üst çağıranlar tamamlanmadı.
Callback devam ederken yeni istek reddedilir; bu ret'in request tarafında
işlenmesi gerekir. Body süresi, bütün call stack/IRQ grafiği, listener
ekleme/silme yaşam döngüsü ve başka global yazarlar üretim kabulü değildir.

## Doğrulama

11 yeni test, `test_midi_sysex_notification.py`:

- Native scatter-load/vtable pin'leri ve kabul sırasında senkron bildirim.
- Bildirim kapalı eski kuyrukta eksik callback negatif kontrolü.
- On iki gerçek çağıranın iki varyantta aynı payload/mask/r0 üretmesi ve doğru
  port baytları; önceki formatter branch/selector stub sınırları korunur.
- Owner ve native listener listesi submit'ten sonra ezilse de ilk sahibin
  callback'i; üç dinleyici sırası/context, null owner ve boş event listesi.
- Tek port hazır değilken bildirim yok; son port kabulünde bir bildirim;
  payload bitmeden yeni istek ret, sonraki işlem doğru yeni sahibine gider.
- Callback girişinde native port poll'ları payload'ı bitirirken nested yeni
  request/submit/service reddi; ilk callback bir kez, slot/canary/ABI korunur.
- Native USB/DIN tamponlarında360B SysEx stall; kabul bildirimi USB completion
  öncesinde, gerçek formatter/ring baytları ve raw proje baytları korunur.
- Geçersiz event pointer/vtable/count, private metadata ve işlem sırasında
  fault; yanlış başarı bildirimi yok. Bounds ve yerel CFG/ABI/PRIMASK audit.

Yerel audit: bütün2050B decode; SP çıkış deltası0, BL/BLX stack hizası8,
max yerel frame32B. Tek BLX, sahipli callback çağrı yerindedir. Callback ve
native dispatcher zorunlu IRQ-mask alanı dışındadır. Maskeli yollarda call/
loop yok; en fazla17 komut. Callback'in süresi veya native toplam stack/cycle
bütçesi kanıtlanmaz. Source/IRQ eşzamanlılığı context-preserving nested
çağrılarla modellenir; gerçek exception/DMA testi değildir.

Bütün Python komutları `.\.venv\Scripts\python.exe` ile, `-O` olmadan:

```powershell
.\.venv\Scripts\python.exe scripts/patch_firmware.py --build-phase1
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/verify_phase1_candidate.py
.\.venv\Scripts\python.exe scripts/run_baseline.py
.\.venv\Scripts\python.exe scripts/audit_phase1_safety.py logs/recovery-sysex-completion-20261027/production-audit
.\.venv\Scripts\python.exe scripts/probe_midi_recovery_prototype.py logs/recovery-sysex-completion-20261027/recovery-probe
.\.venv\Scripts\python.exe scripts/probe_midi_sysex_retry_prototype.py logs/recovery-sysex-completion-20261027/retry-probe
.\.venv\Scripts\python.exe scripts/probe_midi_sysex_notification.py logs/recovery-sysex-completion-20261027/probe
```

202 toplam test PASS: önceki191 +11. Aday87 regresyon/6 sınırlı kriter PASS;
Off/Stop negatif probe'ları FAIL; verifier exit2/NO-GO. Build/baseline/binary
audit PASS. Önceki24 recovery ve14 retry testi kendi probe'larında PASS;
iki probe da exit2. Yeni probe paketlenmiş gerçek imaj üzerine yalnız
emülasyon overlay'leriyle11 testi koşar; event sahipliği PASS, eski bildirim
kapalı kuyruk kontrolü FAIL, production_caller_compatibility FAIL ve exit2.

Güncel loglar `logs/recovery-sysex-completion-20261027/` altında:
`build.txt`, `all-tests-final.txt`, `verify.txt`, `baseline.txt`, `audit.txt`,
`recovery-probe.txt`, `retry-probe.txt`, `probe.txt`, `probe/report.json`,
`probe/retry-code-report.json`, `probe/stock-contract/`. İlk incelemeler ve
ilk7/9/11 test/probe sonuçları korunur. Verifier raporu:
`logs/phase1-verification-20261027T114206Z/report.json` (UTC).
Oturum farkı `session.diff`, dosya hash'leri `session-hashes.json`.

- Bildirimli kod SHA256: `c541d9d2c207f8230c75466b52342698e464a2077a7afa426c3bbaee9fb4fbe0`.
- Bildirim kapalı kod SHA256: `ae8d859e129a72bb02e6e6916ac7ca6a256b30dc6699ff612eacc84ae617b266`.
- Değişmeyen aday SHA256: `3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d`.
- Image SHA256: `38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf`.
- CRC `53F96711`,371368B image,21 patch,1376B fark.
- Stok SHA256: `11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf`.

## Kalan kapılar ve sonraki iş

Başarısız varsayım: bu callback ayrı gecikmiş job/wire tamamlanması değildir;
native kod kabul sırasında senkron çağırır. Yalnız reader bitişini veya global
owner çiftini takip etmek native bildirim sözleşmesini sağlamaz. Snapshot ve
tek kabul bildirimi yeni varyantta testlidir; eski negatif kontrol kalır.

**Sonraki tek somut iş:** sonucu yok sayan response üreticilerinin request
girişlerini izleyip, formatter/source mutasyonundan önce kuyruk kapasitesini
rezerve eden geri basıncı emülasyonda doğrulamak. Özellikle `32120` gibi üst
katmanlar `46A54` formatter'ını `4691A` guard'ından önce çağırır; yalnız12
doğrudan giriş koruması bütün upstream kaynak yazarlarını kapsamaz.

GO için request/recursive send politikası, tüm producer/lifecycle ve üretim
SysEx/recovery entegrasyonu;1256B checked heap/atomik init; mode guard/reset-
resume; stok storage hata-kurtarma; tam boot/OOM ve gerçek IRQ/DMA/USB-
disconnect/PRIMASK süre bütçesi açık. Donanıma yüklenmemeli.
