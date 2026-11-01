# 29 Ekim 2026 — Native senkron dosya kuyruğu / M7 NO-GO

Bu üst bölüm günceldir.53E24/53E8C örnek yüklemesinde45EB6 anlık kopya
sınırı kaldırıldı:gerçek72B request FIFO,sync wait,worker,result/credit
yolu çalışır.8 yeni yerel ve8 paket aday senaryosu PASS. Önceki105 kaynak,
firmware/prototype kodu aynı. Fiziksel MIDI/USB cihazına/API'sine erişilmedi.

Zincir:4603A→45EB6,callback0 için2ACA2→2ACB8→40DC4 (72B kopya).
2CA6C caller credit'i2→1 yapar.2ACF8 gerçek2508C/25056 TCB/TLS0 lookup
ile non-worker caller'ı credit2 olana kadar bekletir. Yalnız2AD12 yield
kenarında explicit task-switch modeli gerçek2AD40 worker'ı çalıştırır.
40DEE paketi worker stack'ine kopyalar;op6→4113A read.2B00C result'u
worker+C'ye yazar;ardından exclusive credit release ile caller açılır.
Sync callback0 yolu result FIFO kullanmaz;önceki async Save sonucu ayrıdır.

Kontroller:Normal/Sequencer128 eksik dosya;native FIFO ring wrap;geçerli
iki4608B örnek/çift tampon/kısmi son chunk/proje RAM;aynı loop'ta MSC
READ/data/CSW;MSC worker içinden senkron sample read;file worker'da reset
ve nested coordinator;file worker'da suspend/MIDI debt;native wrapper'ın
hata sonucunu döndürmesi;short-read negatifi. Request/dequeue byte eşitliği,
native result-before-credit,ABI/canary/native byte hash'leri denetlenir.

Yeni negatif:4113A modelinin4 hata/count2 döndürdüğü ikinci2048B veri
okumasında53E8C sonucu kullanmaz;2048B'nin tamamını sample-flash API'sine
verir.2046B önceden A5 doldurulmuş artık veri testte aynen yazılır. Artık
short/missing read sıfırla doldurulmaz. Native kontrol akışı + sentetik
dosya hatası kanıtıdır;fiziksel arıza veya gerçek kart üzerinde tekrarı yoktur.
Bu oturum stok örnek yükleme davranışını değiştiren patch eklemedi.

Daralan sınır:artık45EB6/queue/wait/worker gerçek;4113A dosya API'si RAM
read/status/count modeli kalır. Mount/open/seek/read/close nesneleri,aynı
alt medya backend'i üzerindeki dosya/MSC arbitration ve gerçek IO beklemesi
henüz çalıştırılmadı. Allocator/progress UI/sample-flash modelleri de kalır.
Native queue worker/TCB test-only22000000..22003000 arena'sında;current-TCB
20006550'e sentetik bağlanır. Bu production RAM/init/RTOS kanıtı değildir.
Özel SD dosya sistemi kodu eklenmedi.

Yeni4 kaynak:tests/test_midi_usb_file_queue.py;scripts/{midi_usb_file_queue_
test_support,trace_midi_usb_file_queue,probe_midi_usb_file_queue}.py.
Yeni belge:docs/MIDI-USB-FILE-QUEUE-5706.md.71300 task-switch cave'i word
hizalı,boşluğu/overlap/app bounds'u denetimli;native2AD12 veya4113A byte'ı
değiştirilmez.71000 stimulus ve71200 UI/allocator test stub'ları korunur.

Başarısız varsayımlar:ilk smoke6 testte,4113A code-hook sınırına CPU detour
eklenmesi dönüşte aynı boundary'yi ikinci kez yürüttü;IRQ stimulus native
2AE2E BL kenarına taşındı. İlk8 koşu7 PASS/1 FAIL:reset içi coordinator
sonucu1(meşgul) sanılmıştı;aktif MSC worker/drain yokken gerçek sonuç0,
frame sayısı1 artıyor. Request/credit ve MCU ABI bozulması yok. Beklenti
owner ayrımına göre düzeltildi. İlk loglar/context failure korunur.
Rapor helper'ında Capstone push.w/pop.w adları da stack hesabına alındı;
ilk finalizer logu korunur. Bu test/firmware değişikliği değildir.

Doğrulama (`.venv\Scripts\python.exe`, `-O` yok):
- `-m unittest discover -s tests -p test_midi_usb_file_queue.py -v`:8 PASS.
- `scripts/probe_midi_usb_file_queue.py logs/usb-file-queue-20261029/probe`:
  paket adayında8 PASS;native trace/code audit/production negatif probe.
- `scripts/audit_phase1_safety.py logs/usb-file-queue-20261029/production-audit`:
  PASS. Diff/hash/vector/MPEG2 CRC/changed-range manifest yeni loglarda.
- Discovery518. Önceki tam474 +13 factory +13 caller +10 long-loop PASS
  aynı105 kaynakla korunur;bu oturum tam518 koşulmadı. Önceki baseline ve
 87/6 sınırlı aday verifier yeniden koşulmadı. Yeni paket probe'unda da
 production Note Off/Stop FAIL. M7 NO-GO;cihaz testi/yükleme önerisi yok.

Stok SHA256:11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.
Aday SYX3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Staging1680B/bc78a69f...,default1300B/f703550d...,
factory732B/2bbb4ab8... ve2712B prototype arena aynı. Test arena veTCB,
checked production rezervasyonuna eklenmiş sayılmaz;flashable çıktı yok.

**Sonraki tek somut iş:**4113A→40E96→2E874 dosya açma/okuma nesnesini
ve456D8/456E0 indeks binding'ini çıkarmak;lower file API sınırını native
dosya nesnesinin read vtable'ına indirip file/MSC isteklerinin aynı native
backend'i kullanırken reader ömrünü reset/suspend altında sınamak.

53E8C short-read artık veri riski,uzun loop main/retry/power erişimi,
tam43E1C/Packs/allocator UI,storage partial-read/live-pattern alias,accepted
TX/raw ALT/partial parser/held/fault recovery,tam RTOS/boot/OOM/checked
RAM-init/integration ve gerçek PHY/flash/DIN timing açık. M7 NO-GO.

---

# 29 Ekim 2026 — Tam128-yuva örnek yükleme döngüsü / M7 NO-GO

Bu üst bölüm günceldir. Önceki tek53E78 BL testi genişletildi: gerçek
53E24 kontrol döngüsü128 yuvanın tamamında,53E8C örnek yükleyicisi ve4603A
dosya okuma wrapper'ıyla çalıştırıldı.10 yeni yerel ve10 paketlenmiş aday
emülasyon senaryosu PASS. Production firmware/prototype kaynakları değişmedi;
önceki101 kaynak hash'i aynı. Fiziksel MIDI/USB cihazına/API'sine erişilmedi.

Gerçek stok kod:40E28/2745A zaten seçili pack yolu;53E24/53E8C;WAV
doğrulama/offset/uzunluk;REV16 ve iki2KB tampon;3172E→26DD6 watchdog;
53E78→27624;mevcut overlay altında native MSC/SCSI/queued worker/HAL/IRQ.
20000A8C depolama okuyucusu değil,progress observer'dır.20006F24 sample
allocator pointer'ıdır. Bu iki nesnenin vtable/binding'i sentetiktir.

Model sınırları:45EB6 file dispatcher anında RAM okuması/zero-fill döndürür;
31228/313D0/3153C/3157E/31608/31626 sample-flash API'leri RAM'e kayıt olur.
Tam dosya-task/queue/callback ömrü,gerçek allocator/UI/pack mount ve flash
arbitration/timing çalıştırılmadı. Özel dosya sistemi kodu eklenmedi.
Dolayısıyla tam stok storage owner grafiği veya gerçek Packs UI kanıtı yok.

Testler:Normal/Sequencer128 yuva;eksik/geçersiz başlık;iki geçerli örnek;
512/2048/2048/512B yazım,byte-swap ve kısmi son blok;proje RAM snapshot'ı;
loop boyunca READ/data/CSW (main çağrısı olmadan,modellenen harici bus
olaylarıyla);aktif USB data-reader/ticket/buffer korunması;native semaphore
tutuluyken poll bastırılması;MSC worker içinde tam128-yuva loop'u;
örnek okuma sonrası suspend;loop içinde reset/iptal ve reconfigure sonrası
yeni READ;geçersiz pack erken dönüşü. Canary/ABI/native-byte denetimleri PASS.
Eksik128 örnekte bile native loop1 döner;bu dönüş içerik başarısı kanıtı değil.

İlerleme negatifi korunur:tam128 tur MSC poll,MIDI retry'ını veya bekleyen
uyku isteğini tek başına ilerletmez. Native main yeniden çalışınca pending
MIDI byte stream ve uyku/uyanma tamamlanır. Bu oturum callsite'ı full-service'e
çeviren firmware patch'i eklemedi;erişim/scheduling hâlâ açık bir sorundur.

Yeni4 kaynak:tests/test_midi_usb_long_loop.py;scripts/{midi_usb_long_loop_
test_support,trace_midi_usb_long_loop,probe_midi_usb_long_loop}.py.
Yeni belge:docs/MIDI-USB-LONG-LOOP-5706.md. Test-only71200..71218 vtable
stub'ları;71000..71100 isteğe bağlı CPU enjeksiyonu. Dosya/flash API'leri
byte değişikliğiyle patch edilmez;assert edilmiş emulator code-hook sınırıdır.

Başarısız varsayımlar/düzeltmeler (firmware sorunu sayılmadı):
- İlk test,harici USB olayları için kullanılan yardımcı çağrının fixed stack'i
  açık loader stack'ini ezdiğini gösterdi;checkpoint CPU + stack korunur.
- Önceki bağımsız MIDI fixture'larının4B00..5000 sentetik vtable/SysEx
  nesneleri,native3F94..4F94 sample tamponuna çakışıyordu. Yalnız yeni
  fixture'da bunlar boşluğu assert edilen E000..E500'e,RAM referanslarıyla
  taşındı;enjeksiyon sonuçları E580'e alındı. B000 ilk denemesi mevcut
  nesne nedeniyle reddedildi. Bu production RAM/init planı değildir.
- Reset detour dönüşü53E78 code-hook'unu iki kez gösteriyordu;tamamlanan
  poll kenarı53E7E'de sayılır.3 hedefli relocation recheck PASS.
first-tests/stack-rechecks/second-tests/relocation-* logları korunur.

Doğrulama (`.venv\Scripts\python.exe`, `-O` yok):
- `-m unittest discover -s tests -p test_midi_usb_long_loop.py -v`:10 PASS.
- `scripts/probe_midi_usb_long_loop.py logs/usb-long-loop-20261029/probe`:
  paket adayında10 PASS;native trace/code audit/negatif aday probe kayıtlı.
- `scripts/audit_phase1_safety.py logs/usb-long-loop-20261029/production-audit`:
  PASS. Diff/hash/CRC/vector/range manifest yeni log klasöründedir.
- Discovery510. Önceki tam474 (usb-staging),13 factory ve13 poll-caller
  PASS kayıtları101 değişmeyen kaynakla korunur;bu oturum tam510 koşulmadı.
  Önceki baseline ve87 regresyon/6 sınırlı kriter verifier da yeniden
  koşulmadı;aynı kaynak/firmware pinleriyle tarihli kanıt olarak tutulur.
  Yeni paket probe'unda da production Note Off/Stop FAIL,M7 NO-GO.

Stok SHA256:11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.
Aday SYX3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Staging1680B/bc78a69f...,default1300B/f703550d...,
factory732B/2bbb4ab8... ve2712B sentetik arena aynı. Yeni test binding'leri
bu production rezervasyonuna eklenmiş veya boot/init ile kanıtlanmış sayılmaz.
Yeni flashable firmware üretilmedi;cihaza yükleme önerisi yok.

**Sonraki tek somut iş:**45EB6→2ACA2 senkron file-operation kuyruğunun
task/descriptor/buffer ömrünü native koddan çıkarmak ve immediate-copy
sınırını gerçek kuyruk/worker emülasyonuna indirerek53E8C sırasında reset /
suspend altında okuyucu ömrünü sınamak. Sonra güvenli main-service erişim
noktası değerlendirilebilir;mevcut RAM-copy testi bu sahipliği kanıtlamaz.

Tam43E1C/Packs/proje UI,main erişimi/MIDI backpressure,diğer indirect
caller'lar,accepted TX/raw ALT/partial parser/held/fault recovery,tam RTOS /
boot/OOM/checked2712B RAM-init,integration,gerçek PHY/flash/DIN timing ve
storage partial-read/live-pattern alias açık. M7 NO-GO.

---

# 29 Ekim 2026 — Ek MSC poll çağrısının sahiplik sınırı / M7 NO-GO

Bu üst bölüm günceldir.2DE92→27624 ek USB depolama poll yolu,mevcut
staging/factory/MSC/storage korumalarıyla13 yeni senaryoda yerel emülasyonda ve
paketlenmiş aday overlay'inde13/13 PASS. Yeniden giriş/kesme/kapanış sırasında
aktif okuyucunun erken serbest bırakılması veya buffer overwrite görülmedi.
Yeni firmware düzeltmesi gerekmedi;önceki97 kaynak/codegen aynı. Fiziksel
MIDI/USB cihazı veya API'si kullanılmadı;production SYX aynı.

Stok byte/disassembly zinciri:273A8→2DE9A8B callback oluşturur;
literal2DEE0=69628 vtable,2DEE4=2DE91 function pointer.43B2C callback'i
view+48'e koyar.43FA0..43FAC→vtable[0]=25653→25652 adapter→2DE90→27624.
Callback27624 sonucunu kullanmaz ve daima0 döner;0 ilerleme/teslim kanıtı
değildir. Test view/callback binding'i sentetik,dispatch slice/adapter/
callback/native poll/READ worker/HAL/IRQ gerçek stok kodudur. Tam43E1C
transfer handler'ı,gerçek view oluşturma/ömür ve UI/RTOS erişimi çalıştırılmadı.

27624 üç direct caller:2587C(main),2DE92(callback),53E78(diğer loop).
Yeni test53E78'in yalnız tek BL kenarında aynı context kapısını doğrular;
çevresindeki53E24 loop'un owner grafiği ve128-iteration gövdesi hâlâ açıktır.

Kanıt:Normal/Sequencer callback dispatch→READ/data/CSW;IRQ/PRIMASK giriş
reddi;aktif worker ve data TX sırasında yeniden çağrı;TASK_BUSY yayınından
sonra recursive callback;kabul ile native poll gövdesi arasına suspend;
worker içi suspend/reset;gerçek native storage completion IRQ içi callback;
clock-stop sırasında MMIO/debt korunması;native factory içinde callback.
Read/cancel/buffer/ticket/canary ve native continuation sayıları denetlenir.
MSC cancel service,TASK_BUSY/ARM_BUSY/IRQ_ACTIVE ve storage quiet kontrolünü
bekler;koruma bu ek çağrı yolundan atlanamadı. Kanıt sentetik RAM/MMIO'dur.

Korunan ilerleme negatifi:bu callback yalnız MSC poll eder. Callback-only32
tur,deferred MIDI yanıtı/uyku isteğini ilerletmez;coordinated native main
yeniden çalışınca kapanış/uyanma/veri tamamlanır. Bu nedenle uzun transfer
handler'larının bütününde main erişimi veya MIDI backpressure çözülmüş değildir.
Başka bir caller'ı körlemesine full-service'e yönlendiren patch eklenmedi.

Yeni4 kaynak:tests/test_midi_usb_poll_callers.py;scripts/{midi_usb_poll_callers_
test_support,trace_midi_usb_poll_callers,probe_midi_usb_poll_callers}.py.
Yeni belge:docs/MIDI-USB-POLL-CALLERS-5706.md. Helper yalnız sentetik RAM
callback binding'i ve native event gözlemi ekler. Yeni production kod/RAM,
kalıcı hook veya forced-mask bölümü yok. Staging carry1680B/bc78a69f...,
default carry1300B/f703550d...,factory732B/2bbb4ab8... ve2712B synthetic arena
aynı. Mevcut yerel SP0/BL8,3 carry maskeli bölüm/max30 audit'i yeniden PASS;
tam stack/RTOS/IRQ latency veya checked production RAM/init kanıtı değildir.

Doğrulama (`.venv\Scripts\python.exe`, `-O` yok):
- `-m unittest discover -s tests -p test_midi_usb_poll_callers.py -v`:
 13 PASS;logs/usb-poll-callers-20261029/final-tests.txt.
- `scripts/probe_midi_usb_poll_callers.py logs/usb-poll-callers-20261029/probe`:
 paket adayında13 PASS;trace/code audit/canary/data+CSW stream PASS;NO-GO.
- Önceki tam474 PASS (usb-staging) ve son13 factory test PASS korunur;
 97 eski kaynak değişmedi. Discovery toplam500;bu oturumda500/500 tam koşu yok.
- `scripts/patch_firmware.py --build-phase1`:aynı21 patch/1376B fark/hash.
- `scripts/audit_phase1_safety.py logs/usb-poll-callers-20261029/production-audit`:
 PASS. `scripts/run_baseline.py`:PASS;baseline-20261029T012318000202Z.
- `scripts/verify_phase1_candidate.py`:87 regresyon/6 sınırlı kriter PASS;
 production Off/Stop FAIL,NO-GO;phase1-verification-20261029T012317Z.
- `git diff --check`:PASS. Diff/hash/CRC/vector/range manifest ve gözlem
 JSON'u logs/usb-poll-callers-20261029 altında. Initial emulator flash önceki
 staging/factory snapshot'ıyla aynıdır;runtime test enjeksiyonları release
 patch'i değildir. Yeni flashable staging/caller firmware üretilmedi.

Başarısız varsayımlar:ilk4 smoke PASS. İlk13 koşuda2 test başarısızdı:
readiness2EF5A hook'u CPU enjeksiyonundan dönüşte tekrar görüldüğünden iki
native poll sanıldı;ölçüm2762A gerçek continuation'a taşındı. Worker reset
stimulus'u sonraki sağlıklı READ'de de tekrar assert ediyordu;tek seferlik
yapıldı. Firmware/prototype guard'ı değiştirilmedi. rechecks3 PASS;final ve
paket13 PASS. first-tests/poll-tests/rechecks logları korunur.

Stok SHA256:11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.
Aday SYX3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B.

**Sonraki tek somut iş:**53E24'ün128-iteration loop'unda53E78→27624 çağrısı
çevresindeki storage/vtable owner'ını çıkarmak;gövdeyi yalnız RAM modelinde
çalıştırıp aktif READ/reset/suspend ile buffer ömrünü kanıtlamak. Tek BL
kenarının context testi,bu uzun loop için tamamlanmış kanıt sayılmaz.

Tam43E1C/Packs/proje UI ve callback ömrü,callback-only MIDI/backpressure /
main ilerlemesi,53E24/diğer indirect caller'lar,accepted TX/raw ALT/partial
parser/held input/fault recovery,tam RTOS/boot/OOM/2712B RAM-init,gerçek PHY /
clock/ACK/IRQ/flash/DIN timing,storage partial-read/live-pattern alias,DIN
input ve production integration açık. Production Note Off/Stop kaybı sürer.
M7 NO-GO;cihaz yükleme önerisi yok.

---

# 29 Ekim 2026 — Bekleyen MIDI verisiyle USB sınıf geçişi doğrulandı / M7 NO-GO

Bu üst bölüm günceldir. Native USB factory,MIDI-only↔MIDI+MSC geçişini
hazırlanmış MAIN baytları,kısmi owned SysEx cursor'u ve query ledger borcu
varken de mevcut staging=True carry ile tamamlıyor.13 yeni senaryo yerel
emülasyonda ve paketlenmiş adayın emulator overlay'inde13/13 PASS.
Yeni firmware düzeltmesi gerekmedi;src/ ve önceki bütün kaynaklar aynı.
Üretim SYX aynı;fiziksel MIDI/USB cihazı veya API'si kullanılmadı.

Kanıt:Normal/Sequencer,360B payload,iki class yönü,staged Note Off,8 pending+
1 owed query ve önceden işlenmiş Clock/Stop,eksik ACK,aktif MSC READ iptali,
factory sırasında yeni istek ve gerçek native reset IRQ,host enumeration
öncesinde101/201/301 tekrarları. MAIN/cursor aynı tutulur;USB completion ve
iki DIN FIFO byte stream tam karşılaştırılır. Class mutation eski MIDI/MSC
reader retirement'ından önce olmaz. Yapılandırma sonrası MIDI-only94B /
2-interface,composite125B/3-interface descriptor ve yeni storage READ/CSW testli.

Native35814 settings callback'i3FC58(slot2) bit17'den1 veya101 seçiyor;
test view/store'u sentetik,callback ve iki dal gerçek stok kodudur. Native
2CB18 boot wrapper'ı current storage mode'u paketleyip gerçek factory kapısına
gider. Bunlar tam Packs UI/proje akışı veya tüm callback erişilebilirliği
kanıtı değildir. İlerleme native25870..25880 main'den;manuel retry/factory /
power pump yok. Host reset/address/configuration ve MMIO olayları stimulus.

Kabul edilmiş MIDI TX hâlâ unsent sayılmaz;factory eski listede bekler.
Staging varyantı çıkarılırsa native2B498 hazırlanmış64B'ı kaybeder ve
factory kapanışı ilerlemez;bu eski karşı örnek negatif kontrol olarak korunur.
Bu çalışma already-submitted teslimat belirsizliğini çözmüş sayılmaz.

Yeni4 kaynak:tests/test_midi_usb_factory_debt.py;scripts/{midi_usb_factory_debt_
test_support,trace_midi_usb_factory_debt,probe_midi_usb_factory_debt}.py.
Yeni belge:docs/MIDI-USB-FACTORY-DEBT-5706.md. Yeni test helper'ı yalnız ikinci
yarış enjeksiyonu için08071100'de256B boş test alanını assert eder;ilk71000
alanını değiştirmez. App bounds/overlap/zero bytes/cache/flash snapshot korunur.
Runtime test instrumentation'ıdır;production patch/hook değildir.

Önceki93 kaynak hash'i ve bütün firmware codegen pin'leri aynı. Default
carry1300B/f703550d...,staging carry1680B/bc78a69f...,factory732B/2bbb4ab8...
değişmedi.128B carry state ve toplam2712B synthetic arena aynı. Yeni kalıcı
kod/RAM veya forced-mask bölümü yok. Mevcut3 carry masked commit/max30 komut,
yerel SP0/BL8 audit'i yeniden PASS;full stack/RTOS/IRQ latency kanıtı değil.

Doğrulama (`.venv\Scripts\python.exe`, `-O` yok):
- `-m unittest discover -s tests -p test_midi_usb_factory_debt.py -v`:
 13 PASS;logs/usb-factory-debt-20261029/final-tests.txt.
- `scripts/probe_midi_usb_factory_debt.py logs/usb-factory-debt-20261029/probe`:
 paket adayında13 PASS;native caller trace/code audit/canary/byte stream PASS;
 scope nedeniyle NO-GO. probe/report.json stream hash ve sonuçlarını içerir.
- Önceki tam takım474 PASS:logs/usb-staging-20261029/full-tests.txt.
 İlgili93 eski kaynak değişmediğinden bu oturumda yeniden koşturulmadı.
 Discovery toplam487 testtir;bu oturumda487/487 tam koşu yapıldığı iddia edilmez.
- `scripts/patch_firmware.py --build-phase1`:aynı21 patch/1376B fark ve hash.
- `scripts/audit_phase1_safety.py logs/usb-factory-debt-20261029/production-audit`:
 PASS. `scripts/run_baseline.py`:PASS;baseline-20261028T235715280172Z.
- `scripts/verify_phase1_candidate.py`:87 regresyon/6 sınırlı kriter PASS;
 production Off/Stop FAIL,NO-GO;phase1-verification-20261028T235735Z.
- `git diff --check`:PASS. session.diff,hashes.json ve exact emulator range /
 SHA/MPEG-2 CRC/vector manifest'i logs/usb-factory-debt-20261029 içindedir.

Başarısız denemeler:ilk3 smoke PASS. Sonraki13 koşuda2 yarış,tek kullanımlık
71000 test trampoline alanını yeniden kayıt etmeye çalışınca fixture assert'inde
durdu;firmware yolu henüz çalışmamıştı. Eski helper gevşetilmedi;71100'de ayrı
checked test trampoline eklendi. race-rechecks.txt2 PASS;final-tests ve paket
13 PASS. İlk loglar first-tests.txt/factory-debt-tests.txt korunur.

Stok SHA256:11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.
Aday SYX3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Emulator snapshot önceki staging ile aynıdır;flashable
staging/factory binary veya yeni SYX üretilmedi.29 Ekim yerel;loglar UTC'dir.

**Sonraki tek somut iş:**native MSC poll27624'ü çağıran2DE92 event callback'inin
çağıran/owner bağlamını çıkarmak;aktif native READ/worker veya IRQ yeniden girişi
varken main service/cancel bariyerini atlayamadığını emülasyonda kanıtlamak.
53E78 diğer caller'ı da açık listededir;ilk hedef2DE92'dir.

Tam Packs UI/proje işlemleri,accepted TX/raw ALT/partial parser/held input /
fault recovery,diğer caller'lar,tam RTOS/boot/OOM/2712B checked RAM-init,gerçek
PHY/clock/ACK/IRQ/flash/DIN timing,storage short-read/live-pattern alias,DIN
input ve production entegrasyonu açık. Byte/disassembly ve sentetik RAM/MMIO /
UART drain sonuçları gerçek host receiver veya timing kanıtı değildir.
Production Note Off/Stop kaybı sürer. M7 NO-GO;cihaz yükleme önerisi yok.

---

# 29 Ekim 2026 — Hazırlanmış MAIN tamponunun korunması / M7 NO-GO

Bu üst bölüm günceldir. Henüz HAL'e kabul edilmemiş,stok formatter tarafından
hazırlanmış USB MAIN baytları artık optional `staging=True` carry varyantında
uyku/uyanma ve reset+host reconfiguration boyunca korunur. Gerçek native main,
402FC SysEx formatter,2B460 event writer ve26880 endpoint adapter yürütülür.
Normal/Sequencer,360B payload,kısmi cursor ve tek Note Off testli.
Üretim SYX aynı;fiziksel cihaz/USB/MIDI API erişimi yoktur.

Yeni karşı örnek:2B498→raw2B3BC→ss_tx_arm,IRQ closure nedeniyle gönderimi
reddeder;raw adapter dönüşü bunu gizler.2B4AE MAIN length'i koşulsuz siler.
Eski carry ile length64→0,cursor48/60 ve hiç TX submission olmadan kilitlenme
yeniden üretildi. Yeni registered CPU MAIN flush,26880 gate'ini doğrudan
çağırır;MAIN ancak TX_TICKET değiştiyse tüketilir. Araya reset/uyku girip
admission reddedilirse aynı bayt/cursor tutulur. Kabul edilmiş TX yeniden
gönderilmez;teslimat belirsizliği hâlâ çözülmüş değildir.

İkinci bulgu:402FC,dolu MAIN ile çağrılırsa kendi flush kenarına ulaşmadan
döner. OPEN registered USB rp_poll bu nedenle retained MAIN'i önce gönderir,
sonra native worker'a devam eder. Ayrı FLUSH_BUSY32 ile yeniden giriş korunur;
stability kapısı producer/flush owner varken seal/resume'a izin vermez.

Admission:TX_ACTIVE0;MAIN length0..64 ve4'ün katı,selected MAIN,64B capacities,
ALT length/pointer0,raw length/mode0. Cursor0..total;0<cursor<total yalnız
USB-accepted immutable retry slot ve eşleşen descriptor/length için kabul.
Gönderilmiş ilk paketten sonra kalan cursor devam eder;ilk paket tekrarlanmaz.
Eski parser/held-input/fault/busy ve full disable/ACK/shared FIFO/AHB/TX flush /
generation koşulları sürer. Raw ALT mode veya in-flight debt carry kazanmaz.

Değişen3 kaynak:src/midi_usb_carry_prototype.py (optional varyant),
scripts/midi_usb_carry_test_support.py (optional kurulum),
scripts/audit_midi_usb_carry_prototype.py (varyant CFG/ABI denetimi).
Yeni:tests/test_midi_usb_staging.py;scripts/{trace_midi_usb_staging,
probe_midi_usb_staging}.py;docs/MIDI-USB-STAGING-5706.md.
Default carry codegen1300B/f703550d... aynı;önceki diğer kaynaklar hash'li.
Yeni varyant1680B0807CC00..0807D290;aynı128B carry state içinde FLUSH_BUSY32;
toplam2712B sentetik arena.7 gate;stock2B4984B yeni gate.3 maskeli bölüm,
max30 komut/call-loop yok;yerel SP0/BL8. Yeni staging/flush frame24B;
copied RP prefix40B ve inherited seal frame24B ayrıca denetlenir.

Doğrulama (Python `.venv\Scripts\python.exe`, `-O` yok):
- `-m unittest discover -s tests -v`:474 PASS (462 önceki+12 yeni).
- `-m unittest discover -s tests -p test_midi_usb_staging.py -v`:12 PASS.
- `scripts/probe_midi_usb_staging.py logs/usb-staging-20261029/probe`:
  paketlenmiş adayda27 PASS (12 yeni+15 eski carry senaryosu yeni varyantla);
  native trace/CFG/ABI/byte/assert/app bounds/canary denetimi PASS;NO-GO.
- `scripts/patch_firmware.py --build-phase1`:aynı21 patch/1376B fark.
- `scripts/audit_phase1_safety.py logs/usb-staging-20261029/production-audit`:
  PASS. `scripts/run_baseline.py`:PASS;baseline-20261028T230604509138Z.
- `scripts/verify_phase1_candidate.py`:87 regresyon/6 sınırlı kriter PASS;
  production Note Off/Stop FAIL,NO-GO;phase1-verification-20261028T230604Z.
- `git diff --check`:PASS. Log klasörü logs/usb-staging-20261029;
  staging-tests/full-tests/probe/build/verify/baseline/production-audit,
  session.diff,hashes.json ve emulator-range-manifest.json içerir.

Başarısız denemeler korunur:first-tests.txt (3 fail),retained full MAIN'in
native formatter başında flush edilmediğini gösterdi. OPEN poll ön-flush'ı
sonrasında second-tests.txt4 PASS. Bir önceki carry'nin default davranışı
değiştirilmedi;gerçek native loss karşı örneği yeni testte negatif kontrol.

Kod SHA256:bc78a69f0b8ee46e1e9e4f8af9bc56c2c32b1d267cfed1812f2a03b13540faf8.
SYX3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Stok SHA256:
11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.
Range manifest tüm emulator farkını/CRC/vector'u kaydeder;flashable paket değil.
Tarih29 Ekim yerel;otomatik log damgaları28 Ekim23:xx UTC olabilir.

**Sonraki tek somut iş:**retained MAIN/kısmi SysEx borcu varken gerçek native
USB factory ile MIDI-only↔MIDI+MSC descriptor değişimini test etmek;Packs
geçişinde eski slot/cursor/tamponun korunmasını ve doğru class sonrası
tek devamı kanıtlamak. Bu henüz tam Packs UI/proje akışı kanıtı değildir.

Already-submitted teslimat belirsizliği/raw ALT mode/partial parser/held input /
genuine fault recovery,diğer caller'lar,tam RTOS/boot/OOM/2712B checked RAM-init,
gerçek PHY/clock/ACK/IRQ/flash/DIN timing,storage partial-read/live-pattern alias,
DIN input ve production entegrasyonu açık. Sadece sentetik RAM/MMIO,IRQ byte
stream ve model UART drain kanıtı var;fiziksel host receiver veya timing değil.
Production Off/Stop kaybı sürer. M7 NO-GO;cihaz yükleme önerisi yok.

---

# 29 Ekim 2026 — Gönderimi başlamamış MIDI borcunun devri / M7 NO-GO

Bu üst bölüm günceldir. Önceki64-frame suspend/wake kilitlenmesi,henüz USB'ye
verilmemiş yazılım borcu için emülasyonda düzeltildi. Logical ledger/SysEx/TX
sahipliği fiziksel reader iptalinden ayrılır. Native main'de uyku/uyanma veya
reset+host reconfiguration sonrası yanıtlar model IRQ completion akışına tam
bir kez ulaşır. Normal ve Sequencer testli. Production syx aynı;cihaz API yok.

Yeni yol koşulludur:SS TX_ACTIVE0;USB staging/main/alt length0,selected MAIN /
mode0;native software TX cursor0 veya cursor==total;idle parser/held input;
producer/worker busy ve gerçek USB RP fault yok. İn-flight+debt,kısmi staging /
cursor/parser,held input veya genuine fault bu carry yolunu almaz. Eski
logical-idle cancellation politikası değişmedi;belirsiz teslimat tekrar edilmez.
Bu,başlamış USB aktarımını veya bütün task/power durumlarını çözmüş sayılmaz.

Disable/ACK/AHB/shared FIFO/TX flush aynen beklenir. Sonra yalnız HAL transfer
pointer/count'ları ve RX job retire edilir;RX capacity byte korunur. RX FIFO /
parser/SCANNED/EXPECTED_READ,owned SysEx payload ve TX FIFO/descriptor/cursor
baytları silinmez. Physical epoch artar;logical marker provenance devam eder.
Native class init eski router clear guard'ıyla kurulur;yalnız pin'li ss_resume
caller'ı lifecycle'ı yeniden açabilir. Yeni IRQ generation seal/resume commit'i
iptal eder. Ayrı CY BUSY,nested ss_step'i engellerken reset IRQ'yu çalıştırır.

Planlı kapanışta registered USB rp_poll bekletilir. Aksi halde controller
state4/ready0,önceden SEEN1 olan queued Note Off'u genuine FAULT'a çevirip
retry slot'unu kalıcı bloke ediyordu. Bu yalnız owned CLOSING..SEALED içindir;
var olan gerçek FAULT silinmez ve OPEN'daki normal hata yolu korunur.

15 yeni test (11 olumlu+4 korunan sınır negatifi):iki mod,eski stall,
reset/config,360B payload,queued Off,committed Clock/Stop,wrapped owed record,
tekrar sleep,missing ACK,retirement ve resume reset yarışı,yanlış caller.
Ek deney:önceden native all-port admission7 almış borrowed pointer/cursor/
total ve NOTICE3 uyku boyunca korunur;9 owned slot için9 native notice,
tek USB model byte stream ve DIN FIFO byte stream. UART drain RAM modelidir;
fiziksel UART IRQ veya host receiver ACK kanıtı değildir.

1300B kod0807CC00..0807D114;128B state20048520..200485A0;toplam2712B sentetik.
6 gate:5 generated(quiet,step,seal10B,resume,poll) ve main call4B. Orijinal
byte/assert/overlap/app bounds/flash snapshot/canary/CFG audit var.3 yeni
maskeli bölüm/max30 komut/call-loop yok. Yeni local frame max32B;copied native
RP prefix40B ve borrowed ss_step frame24B ayrıca doğrulanır. SP delta0/BL8;
tam native stack/cycle/ISR latency veya checked production RAM/init kanıtı yok.

Yeni:src/midi_usb_carry_prototype.py;scripts/{midi_usb_carry_test_support,
audit_midi_usb_carry_prototype,trace_midi_usb_carry,probe_midi_usb_carry}.py;
tests/test_midi_usb_carry.py;docs/MIDI-USB-CARRY-5706.md. Önceki bütün kaynaklar
ve default codegen hash'leri aynı;production builder'a eklenmedi.

Bütün Python komutları `.venv\Scripts\python.exe`, `-O` yok:
- `-m unittest discover -s tests -v`:462 PASS (447 önceki+15 yeni);
  logs/usb-carry-20261029/full-tests.txt.
- `scripts/probe_midi_usb_carry.py logs/usb-carry-20261029/probe`:
  paket overlay15 PASS;audit/native trace PASS;exit2/NO-GO.
- `logs/usb-carry-20261029/check_borrowed_debt.py`:PASS;borrowed-debt-check.json.
- `scripts/patch_firmware.py --build-phase1`:PASS;21 patch/1376B fark aynı.
- `scripts/verify_phase1_candidate.py`:87 regresyon/6 sınırlı kriter PASS;
  production Off/Stop FAIL,exit2;logs/phase1-verification-20261028T224253Z/report.json.
- `scripts/run_baseline.py`:PASS;logs/baseline-20261028T224017816280Z.
- `scripts/audit_phase1_safety.py logs/usb-carry-20261029/production-audit`:
  PASS;stock/vector/app bounds/CRC/manifest aynı. `git diff --check`:PASS.
  Oturum29 Ekim yerel saat;otomatik log timestamp'leri UTC'dir.

Başarısız varsayımlar/loglar:logical debt ile ordinary clear güvenli değildi;
native RX/TX yazılımı preserve edildi. Uzun payload iki DIN FIFO'su drain
edilmeden slot'u pinliyordu;native ring consumer ile açık UART stimulus
eklendi. Wake tek frame'de bitmiyor;reopen gözlenene kadar bounded native
frame yürür. Eski SS BUSY1,retirement içi reset IRQ'yu reddediyordu;ayrı CY
sahipliği/step gate ve generation commit uygulandı. Planned ready0'nun RP
FAULT oluşturması queued Off testinde bulundu ve scoped poll-park ile
düzeltildi. Genuine fault'un yeni slot admission'ını zaten reddettiği
negatifi korunur. İlk başarısız kayıtlar silinmedi.

Kod SHA256:f703550dabc585a6bcdc1025a8cf9f93dc68d2bad1617096947d45db62709636.
Aday SYX3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Stok SHA256:
11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.
Diff/hash/log:logs/usb-carry-20261029/{session.diff,hashes.json,probe,full-tests.txt,
build.txt,verify.txt,baseline.txt,production-audit.txt,emulator-range-manifest.json}.
Emulator manifest'i snapshot farkı/CRC/vector kanıtıdır;flashable SYX değildir.

**Sonraki tek somut iş:**native USB formatter'ın staging'de hazırladığı fakat
HAL'e henüz vermediği baytları da korumaya katmak. Mevcut partial-staging
negatifini gerçek native formatter ile kurup,payload/cursor'un doğru konumdan
devamını kanıtlamak. Already-submitted teslimat belirsizliği ayrı kalır.
İn-flight/partial-parser/held-input/genuine-fault toparlanması,factory/Packs
ile debt kombinasyonları,diğer poll caller'ları,full RTOS/boot/OOM/2712B RAM-init,
gerçek PHY/clock/ACK/IRQ/flash/DIN timing,storage short-read/live-pattern alias,
DIN input ve integration açıktır. Stale XFRC/bozuk bariyer ve production
Off/Stop kaybı sürer. M7 NO-GO;cihaza yükleme önerisi yok.

---

# 28 Ekim 2026 — Native ana döngüde servis erişimi / M7 NO-GO

Bu üst bölüm günceldir. Yeni servis artık emülasyonda gerçek ana döngünün
USB slot'undan çağrılıyor. Query yanıtı,READ/CSW ve borçsuz uyku/uyanma,manuel
power/retry pump olmadan ilerliyor. Ancak task kapısı bütünüyle kapanmadı:
uyku öncesi retained MIDI/ledger borcu,FROZEN consumer ve ss_quiet arasında
ilerlemeyi kilitliyor. Wake dahil64 native main geçişi bunu çözmüyor;bu negatif
korunur. Üretim firmware'i aynı;fiziksel cihaz/MIDI/USB API erişimi yok.

Native sıra25870(global20006F04)→297DE output;25878→29ABC USB/DIN input;
2587C→27624 MSC.4B BL gate yalnız2587C'de352B task katmanına gider. Bir
sr_service,bir pw_service ve en fazla bir korumalı MSC poll yürür. Yerel
döngü/forced IRQ maskesi yok. Aktif READ/SCSI/worker/IRQ/class ownership veya
yeniden girişte task service reddedilir;dış çağrı buffer sahipliğini korur.

Worker kanıtı da genişletildi:READ65128→2C23A drain→24138 model task switch→
gerçek648AE..648B8 backend loop→2C278. Global20006E60 literal'i stoktan pin'li.
Loop'un wait/return kenarı fixture sınırıdır;tam RTOS scheduler/priorities /
wake-dispatch kanıtı değildir. Host kodu ready/drain'i zorla bırakmaz. Alt
flash RAM ve bus ACK/flush/IRQ/clock/NVIC sınırları da sentetiktir.

13 yeni test (10 olumlu+3 beklenen negatif):native sıra/ABI;main-only query /
READ/CSW/power;TX pressure;missing ACK;worker nested service/IRQ suspend;
IRQ/masked giriş reddi. Hook olmayan main'de power ve retry servisleri
ilerlemez. Retained ledger/TX debt ile suspend→wake64-frame recovery FAIL.
Donmuş tüketiciyi açmak veya ss_quiet kontrollerini atlamak çözüm olarak
uygulanmadı;eski payload/reader/admitted musical event ömrü korunmalıdır.

352B kod0807C800..0807C960;64B state20048420..20048460;toplam2584B sentetik.
Yeni kaynaklar:src/midi_usb_task_prototype.py;scripts/{midi_usb_task_test_support,
audit_midi_usb_task_prototype,trace_midi_usb_task,probe_midi_usb_task}.py;
tests/test_midi_usb_task.py;docs/MIDI-USB-TASK-5706.md. Önceki kaynak/default
codegen aynı. Production builder'a eklenmedi;checked RAM/init yok.
Audit:SP delta0,BL8,max16B local frame,0 yeni maskeli bölüm/yerel döngü.
Native READ drain'in gerçek RTOS altında dönüş süresi kanıtlanmadı.

Bütün Python komutları `.venv\Scripts\python.exe`, `-O` yok:
- `-m unittest discover -s tests -v`:447 PASS (434 önceki+13 yeni);
  logs/usb-task-20261028/full-tests.txt.
- `scripts/probe_midi_usb_task.py logs/usb-task-20261028/probe`:
  paket overlay13 PASS;audit/native trace PASS;exit2/NO-GO.
- `scripts/patch_firmware.py --build-phase1`:PASS;21 patch/1376B fark aynı.
- `scripts/verify_phase1_candidate.py`:87 regresyon/6 sınırlı kriter PASS;
  Off/Stop FAIL,exit2;logs/phase1-verification-20261028T195413Z/report.json.
- `scripts/run_baseline.py`:PASS;logs/baseline-20261028T195413229280Z.
- `scripts/audit_phase1_safety.py logs/usb-task-20261028/production-audit`:
  PASS;stock/vector/app bounds/CRC/manifest aynı. `git diff --check`:PASS.

İlk varsayımlar düzeltildi:fixture stale disable-request'lerine her frame
ACK verince yeni interrupt durumu oluşup closure bloke oldu;ACK yalnız doğru
WAIT_DISABLE safhasına sınırlandı. Legacy stall/release helper'ının driver+5
fake-full byte'ı native sürücüde pointer byte'ıdır;full native poll'a taşınınca
unmapped read üretti. Yeni debt negatifi native pointer'ları değiştirmeden,
owned retry slot'u ile kurulur. Bu ilk loglar saklandı. RTOS yield önce doğrudan
worker gövdesini çağırıyordu;şimdi gerçek native worker caller loop'u yürür.

Kod SHA256:31f38af23a9011bc05ed85c17566ec86a07a930b78de4712e586bfab6986df3e.
Aday SYX3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Stok SHA256:
11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.
Diff/hash/log:logs/usb-task-20261028/{session.diff,hashes.json,probe,full-tests.txt,
build.txt,verify.txt,baseline.txt,production-audit.txt,emulator-range-manifest.json}.
Son manifest emulator snapshot farkları/MPEG2 CRC/vector kontrolüdür;flashable
firmware/SysEx değildir. Üretim manifest/CRC ve önceki kaynaklar aynı.

**Sonraki tek somut iş:**uyku/reset kapanışında kabul edilmiş ledger/SysEx/TX
yazılım borcunun ömrünü hardware reader iptalinden ayıran recovery protokolünü
kurmak. Mevcut64-frame negatiften başlayıp native pointer'ları bozmadan,eski
payload/müzikal olayları kaybetmeden veya yinelemeden wake sonrası ilerleme
kanıtlanmalı.27624'ün2DE92/53E78 diğer caller'ları,full scheduler/boot/OOM /
2584B RAM-init,gerçek timing/PHY/iptal,tam Packs/project,storage short-read /
live-pattern alias,DIN input ve entegrasyon açık. Stale untagged XFRC/bozuk
bariyer negatifi ve üretim Off/Stop kaybı sürer. M7 NO-GO;yükleme önerisi yok.

---

# 28 Ekim 2026 — Normal USB suspend/wakeup / M7 NO-GO

Bu üst bölüm günceldir. Normal USB uyku/uyanma emülasyon prototipinde ortak
iptal bariyerine bağlandı. Aktif MIDI/MSC READ reader ve admitted MIDI borcu
bitmeden,sürücü disable/ACK/AHB/shared FIFO/TX flush tamamlanmadan USB saati
durmaz. Erken wake/reset ve native durum kaydı içindeki wake,sonradan gelen
clock-stop'a dönüşmez. Uykuda reset eski configuration'ı tekrar açmaz;host
enumeration/config beklenir. Üretim aynı;fiziksel cihaz/MIDI/USB API erişimi yok.

Native2C7E6→4279E state'i4 yapıp USB+E00 bit0'ı reader beklemeden set eder.
Native2C802→427AE eski state'i doğrudan yükler. Yeni preflight,completion
claim'lerinden önce common request ile MIDI/MSC kabulünü dondurur. Ana servis
barrier sonrası native state save yapar;generation kontrolü ve kısa maskeli
bölümde yalnız wake/reset global maskesi,DSB ve clock-stop uygular. Wake önce
native2C9F8(handle,0) ile saati açar,state/mask restore eder;sonra normal IRQ /
class init yürür. Asleep sırasında normal MMIO/native service/factory çalışmaz.

16 yeni test:aktif READ,MIDI borcu/eksik ACK,erken ve coalesced wake/reset,
native save içi wake,MIDI-only query/composite READ,asleep factory erteleme,
tekrar suspend,DIN Off/project RAM,clock-stopped MMIO guard ve generation wrap.
Korumasız native suspend aktif reader ile clock-stop yapar:beklenen negatif.
LPM27,system deep stop(handle+20hex!=0) ve DMA desteklenmez;hata kapalı kalır.
CPU-FIFO/normal suspend11/wake31 kapsamıdır;tam power/caller grafiği değildir.

1176B kod0807C000..0807C498;96B state20048320..20048380;toplam2520B sentetik.
3 stok gate ve1 generated service overlay;IRQ policy varyantının yalnız
MOVW/MOVT allow-mask immediate'ları değişir. Pin'li byte/overlap/app bounds /
flash snapshot/canary/CFG audit var. SP delta0,BL8,max24B local frame;
3 yeni maskeli bölüm,max30 komut/call-loop yok. Tam native stack/cycle veya
fiziksel ISR latency kanıtı değil. Checked production RAM/init hâlâ yok.

Yeni kaynaklar:src/midi_usb_power_prototype.py;scripts/{midi_usb_power_test_support,
audit_midi_usb_power_prototype,trace_midi_usb_power,probe_midi_usb_power}.py;
tests/test_midi_usb_power.py;docs/MIDI-USB-POWER-5706.md. Önceki bütün kaynaklar
ve default codegen hash'leri korunur. Üretim builder'ına eklenmedi.

Bütün Python komutları `.venv\Scripts\python.exe`, `-O` yok:
- `-m unittest discover -s tests -v`:434 PASS (418 önceki+16 yeni);
  logs/usb-power-20261028/full-tests-final.txt.
- `scripts/probe_midi_usb_power.py logs/usb-power-20261028/probe-final`:
  paket üstünde emulator overlay16 PASS;audit/native trace PASS;exit2/NO-GO.
- `scripts/patch_firmware.py --build-phase1`:PASS;21 patch/1376B fark aynı.
- `scripts/verify_phase1_candidate.py`:87 regresyon/6 sınırlı kriter PASS;
  Off/Stop FAIL,exit2;logs/phase1-verification-20261028T190505Z/report.json.
- `scripts/run_baseline.py`:PASS;logs/baseline-20261028T190440514002Z.
- `scripts/audit_phase1_safety.py logs/usb-power-20261028/production-audit`:
  PASS;stock/vector/app bounds/CRC/manifest aynı. `git diff --check`:PASS.

Başarısız varsayım:alt IRQ köprüsünün BROKEN hatası MSC üst katmanında
CLOSING'e çevrilebiliyordu. Power katmanı başarısız IRQ dönüşünü terminal hata
olarak kaydedip MIDI/MSC'yi BROKEN'da tutar. İlk16 testteki bu tek failure ve
recheck saklandı. Ayrıca ilk sürüm,asleep sırasında native IRQ register erişimi
yapabiliyordu. Son sürüm wake/reset dışını maskeler ve ordinary MMIO read guard
ile testlidir. İlk full-tests/probe kayıtları bu guard öncesidir;final adlı
kayıtlar son kaynağı doğrular. Native erken clock-stop negatifi bilerek korunur.

Kod SHA256:0965c37caf44ea8e5b64e667f02172ce121a7d7f4d98ac460afd0125d71af4bb.
IRQ varyant80a130b0e33ba70eeef52bc3bf3ed0f03a2fa30bda48f42702f6b5abea9ccaf9.
Aday SYX3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Stok SHA256:
11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.
Diff/hash/log:logs/usb-power-20261028/{session.diff,hashes.json,probe-final,
full-tests-final.txt,build.txt,verify.txt,baseline.txt,production-audit.txt}.
emulator-range-manifest.json bütün emülasyon application snapshot farkını,
vector eşitliğini ve yeniden hesaplanmış MPEG2 CRC'leri kaydeder;yüklenebilir
firmware veya SysEx değildir. Üretim manifest/CRC aynı kalır.

**Sonraki tek somut iş:**pw_service'i gerçek USB/MIDI task/main çağrı zincirine
bağlamak;aktif READ ve MIDI reply varken worker/IRQ tekrar girişi,ilerleme ve
starvation durumlarını gerçek native task gövdeleriyle emülasyonda kanıtlamak.
Service şimdi manuel pump'tır. Gerçek clock/PHY wake/ACK/NVIC/RTOS/flash timing,
tam Packs UI/project,boot/OOM/2520B reservation-init,storage short-read/live-
pattern alias,DIN input ve üretim entegrasyonu açık. Eski untagged XFRC,
bozuk bariyerden sonra yeni job'dan ayırt edilemez;negatif kanıt korunur.
Üretim Off/Stop kaybı
devam eder;M7 NO-GO,cihaza yükleme önerisi yok.

---

# 28 Ekim 2026 — Native USB factory sınıf geçişi / M7 NO-GO

Bu üst bölüm günceldir. MIDI-only↔MIDI+MSC factory isteği artık emülasyonda
ortak iptal bariyerine katılır. Eski class listesi,READ/USB reader ve admitted
MIDI borcu bitip native parent teardown yürüyene kadar korunur;sonra stok
factory/stop/init/descriptor/start zinciri çalışır. Geçiş içindeki yeni mod
isteği ve harici reset kaybolmaz. Üretim firmware'i aynı;cihaz API erişimi yok.

Bulunan sorun:40A30,40A40'ta eski class pointer'larını ve40A44'te sayısını
deinit'ten önce siler. Korumasız native factory negatifinde eski MSC READ TX
aktifken liste MIDI-only olur ve MSC parent deinit edilmez. Yeni432A8 gate
isteği saklar;mc_service eski listeyi kapatınca gerçek factory'yi çağırır.
Bilinen native iç deinit yalnız RUNNING/main/root/controller/caller bağında
geçirilir;harici olay yeni request/generation olarak korunur.

16 yeni test:iki yönlü liste geçişi,MIDI-only94B/2-interface ve composite
125B/3-interface descriptor,MIDI inquiry,yeniden storage READ,aktif READ /
MIDI borcu,latest request ve native factory içinde yeni istek/reset,DIN Off /
project RAM,native2CB18 üst stack halfword'ü,storage mod1/2/3,IRQ-context /
yanlış HAL binding reddi. MSC-only/disabled liste desteklenmez;argümanlar
1/101/201/301(low16) ile sınırlı. Tam Packs UI/project akışı kanıtlanmadı.

Factory kod732B:0807BA00..0807BCDC;state128B:20048220..200482A0.
Toplam2424B sentetik state;production checked reservation/init yok. Factory
MSC varyantı2848B,storage varyantı1452B. Optional class policy/config-ready
hook'ları eklendi;default MSC/storage ve diğer eski codegen hash'leri aynı.
Audit:SP delta0,BL8,max32B local frame;2 maskeli bölüm/max11 komut,call-loop
yok. Bunlar tam native stack/cycle/ISR gecikmesi kanıtı değildir.

Gerçek native stop/start,2C82A init prefix ve43196/43158 FIFO setup yürür.
HAL427FC return0 sınırı;3/200ms native beklemeler sentetik24068 tick ile
ilerler. NVIC/clock RAM etkileri vardır;gerçek PLL/PHY/IRQ scheduling yok.
Önceki alt flash RAM/RTOS wake-yield sınırları da sürer. Full power/task /
boot/OOM,gerçek bariyer,tam caller grafiği,DIN input ve storage alias açıktır.

Yeni:src/midi_usb_factory_prototype.py; scripts/{midi_usb_factory_test_support,
audit_midi_usb_factory_prototype,trace_midi_usb_factory,probe_midi_usb_factory}.py;
tests/test_midi_usb_factory.py;docs/MIDI-USB-FACTORY-5706.md. Dört eski kaynak:
src/{midi_usb_msc_prototype,midi_usb_storage_prototype}.py ve bunların iki
audit script'i optional hook için güncellendi. Diğer kaynaklar korunur.

Bütün Python komutları `.venv\Scripts\python.exe` ile,`-O` yok:
- `-m unittest discover -s tests -v`:418 PASS (402 önceki+16 yeni);
  logs/usb-factory-20261028/full-tests.txt.
- `scripts/probe_midi_usb_factory.py logs/usb-factory-20261028/probe`:
  paket üstüne emulator overlay16 PASS;audit/native trace PASS;exit2/NO-GO.
- `scripts/patch_firmware.py --build-phase1`:PASS;21 patch/1376B fark aynı.
- `scripts/verify_phase1_candidate.py`:87 regresyon/6 sınırlı kriter PASS;
  Off/Stop FAIL,exit2;logs/phase1-verification-20261028T173550Z/report.json.
- `scripts/run_baseline.py`:PASS;logs/baseline-20261028T173432370213Z.
- `scripts/audit_phase1_safety.py logs/usb-factory-20261028/production-audit`:
  PASS;stock/vector/app bounds/CRC/manifest aynı. `git diff --check`:PASS.

Başarısız ilk varsayımlar:yalnız200ms factory delay'ini modellemek yetmedi;
stop/start3ms wait de gerçek tick bekler. Tick değeri struct+4'tedir,base'de
değil. Yeni USB enumeration öncesi USBRST gerekir. İç deinit guard'ı RUNNING
okurken R0 root'u ezdiği için saved R0 geri yüklendi. Factory sırasında gelen
reset,pending factory bitmese de control.FLAGS boşalana kadar service ister.
İlk başarısız test logları ve düzeltilmiş negatif kontroller saklandı.

Kod SHA256:2bbb4ab82b1af9609405bbf94e31c31981845f1f1912c822e7cbd2a1fe7fd0e2.
MSC varyant66efc7b861249c4cebc9f1083cfcde9f6ba6ee0121de5a4bd7dc9a569cff383f;
storage varyant0fb30b731592ad818529f4d770df751971f3b44941d0cc0abb81386cc611802b.
Aday SYX3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Stok SHA256:
11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.
Diff/hash/komut kayıtları:logs/usb-factory-20261028/{session.diff,hashes.json,
probe,full-tests.txt,build.txt,verify.txt,baseline.txt,production-audit.txt}.

**Sonraki tek somut iş:**native USB suspend/wakeup IRQ yollarını izleyip
aktif MIDI/MSC READ varken ortak bariyerle kapatma/yeniden açma davranışını
emülasyona bağlamak. Sonra gerçek task/main-service wiring,tam Packs akışı /
boot/RAM/init/OOM,fiziksel timing/iptal,storage short-read/live-pattern alias,
DIN input ve üretim entegrasyonu kapıları sürer. Üretim Off/Stop kaybı açık;
M7 NO-GO,cihaza yükleme önerisi yok.

---

# 28 Ekim 2026 — Native READ10/CSW sahipliği ve okuma hatası / M7 NO-GO

Bu üst bölüm günceldir. Stok MSC READ10, gerçek kuyruk/worker/drain kodu ve
USB FIFO üzerinden emülasyonda yürür. Okuma sırasında reset gelirse işin
tamamlanması beklenir; USB'nin kullandığı 4 KB veri tamponu ve 13 B CSW,
completion veya disable/ACK/shared-FIFO/TX2-flush bariyeri bitmeden yeniden
kullanılmaz. CSW devam ederken gelen sonraki CBW, CSW içeriğini değiştirmez.
Üretim firmware'i aynı; fiziksel cihaz/MIDI/USB API erişimi yoktur.

Önemli hata düzeltmesi: native65128, backend okuma hatasına rağmen sonunda
0 döndürebilir. Yeni katman 2C328'de yalnız ilgili4096B READ işinin sonucunu
yakalar; hata/eksik sonuçta SCSI'ye -1 döndürür. Başarılı veri yerine failure
CSW gönderilir. Daha sonra kuyrukta başarılı olan başka bir iş backend'in
ortak son-status alanını0 yapsa da ilgili READ hatası korunur. Orijinal native
callback'in hatayı yutması negatif kontrolde hâlâ gösterilir.

Önceki genel WRITE10 iptali varsayımı daraltıldı: native initializer sonrası
200038AC→20003888 tablosundaki650E8 write-protect callback'i daima1 döndürür.
WRITE10,65194 yazma callback'ine ulaşmadan DATA PROTECT/failure CSW alır.
Native43264 mod seçicisinin1/2/3 değerleri bu tabloyu değiştirmez; yalnız
range descriptor seçer. Bu pin'li bağlı tablo için kanıttır; bütün runtime
yeniden bağlama/factory grafiğinin kanıtı değildir. Yazmayı açan değişiklik
veya özel SD filesystem kodu eklenmedi.

Gerçek yürüyen yollar: SCSI458D0→READ65128→backend2C394→enqueue2C1CC→
drain2C23A→worker2C278→2C328 sonucu; sonra USB IN82 HAL/FIFO/IRQ ve CSW.
READ callback'inin önceki Init(LUN0) no-op sınırı da stok650D0'a bağlandı.
Backend nesnesi native2C190 ile kurulur;FIFO ve atomic request/ready gövdeleri
gerçektir. **Alt flash erişimi RAM kopyasıdır; RTOS wake/yield sınırdır.**
Yield gerçek worker'ı yürütür,host kodu drain bayrağını zorla temizlemez.
Gerçek flash/SPI/DMA/RTOS zamanlaması veya tam boot kanıtı yoktur.

Yeni storage katmanı1452B:0807B400..0807B9AC; state128B:
20048140..200481C0. Toplam2296B sentetik state; checked production reservation /
init yoktur. Mevcut MSC koduna optional storage-policy/finalize hook eklendi;
default2924B codegen/hash aynı. Storage varyantı2876B,0807A800..0807B33C.
Backend binding,queue boşluğu,pending counter/request word ve IO/task/IRQ
sahipliği doğrulanmadan iptal bitmez. Native READ/CSW producer ve consumer
gate'leri erken buffer reuse'u engeller. 6 stok +1 generated storage gate;
RTOS/lower-driver sınırları fixture'da açıkça kaydedilir. Byte/assert,overlap,
application bounds,full emulator flash snapshot ve RAM canary kontrolleri var.

18 yeni/402 toplam test PASS. Bir/iki blok READ10 veri+CSW,read reset/cancel /
retry,worker içinde reset,missing IN ACK,CSW+CBW birlikte iptal,erken yeni
CBW/direct READ,binding koruması,DIN Off/MIDI inquiry ve per-job read-error
koruması testli. Eski untagged TX XFRC yeni job açıldıktan sonra verilirse
yeni job gibi görünebilir;bozuk bariyer zorunlu negatifi korunur.

Yerel audit:SP delta0,BL8 hizalama,max32B local frame;1 yeni maskeli bölüm,
max25 komut/call-loop yok. MSC varyantının4 bölümü/max29,önceki control
max38 sınırı aynı. Bunlar tam native stack,cycle veya gerçek ISR gecikmesi
kanıtı değildir. Full class/power/task/boot/storage producer grafiği açık.

Yeni:src/midi_usb_storage_prototype.py;
scripts/{midi_usb_storage_test_support,audit_midi_usb_storage_prototype,
trace_midi_usb_storage,probe_midi_usb_storage}.py;
tests/test_midi_usb_storage.py;docs/MIDI-USB-STORAGE-5706.md.
Üç eski kaynak bilinçli güncellendi:src/midi_usb_msc_prototype.py optional
hook'lar;scripts/audit_midi_usb_msc_prototype.py optional hook audit'i;
scripts/native_midi_driver_test_support.py optional foreign-endpoint boundary.
Diğer eski kaynaklar ve kullanıcı değişiklikleri korunur.

Bütün Python komutları `.venv\Scripts\python.exe`, `-O` yok:
- `-m unittest discover -s tests -v`: **402 PASS** (384 önceki+18 yeni),
  logs/usb-storage-20261028/all-tests.txt.
- `scripts/probe_midi_usb_storage.py logs/usb-storage-20261028/probe`:
  paket üzerine emulator overlay18 PASS;audit/native trace PASS;
  exit2/NO-GO beklenir. Üretim Off/Stop FAIL negatifi korunur.
- `scripts/patch_firmware.py --build-phase1`:PASS;21 patch/1376B fark aynı.
- `scripts/verify_phase1_candidate.py`:87 regresyon/6 sınırlı kriter PASS;
  Off/Stop FAIL,exit2;logs/phase1-verification-20261028T163329Z/report.json.
- `scripts/run_baseline.py`:PASS;logs/baseline-20261028T163330021001Z.
- `scripts/audit_phase1_safety.py logs/usb-storage-20261028/production-audit`:
  PASS;stok/vector/app bounds/CRC/manifest aynı. `git diff --check`:PASS.

Düzeltilen varsayımlar:200038C0 önce backend sanıldı;range descriptor
pointer'ıdır. Gerçek backend global'i20006E60,native2C190 kuyruğudur.
MSC'nin varsayılan olarak yazılabilir SD worker kullandığı varsayımı yanlıştı;
pin'li tablo yazma korumalı flash arayüzüdür. Backend'in ortak son-status'ına
bakmak da yetersizdir;sonraki başarılı iş önceki hatayı örtebilir. İlgili
worker sonucu ayrı yakalanır. Negatif kontroller ve ilk tanı kayıtları tutulur.

Kod SHA256:96915c5f0be67e9ff0644ded5b35ba735686b5e58991981b4330086ef1d5f486.
MSC varyant SHA256:4a1792465d819bc125d0f396a24ca8b1a985b30549c33de7616dff3f11837136.
Aday SYX3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Stok SHA256:
11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.
Diff/hash/komut kayıtları:logs/usb-storage-20261028/{session.diff,hashes.json,
probe,build.txt,verify.txt,baseline.txt,production-audit.txt}.

**Sonraki tek somut iş:**native432A8 factory→40A30/40B44 teardown/setup
zincirini MIDI-only ve MIDI+MSC class listesi/Packs mod geçişlerinde ortak
bariyere bağlamak. Mevcut hard-coded iki-class binding'i dışında kuyruğun,
parent ve descriptor sahipliğinin korunmasını emülasyonda kanıtlamak.
Ardından power-state/task wiring,tam boot/RAM/init/OOM,gerçek flash/RTOS /
IRQ bariyeri,storage project short-read/live-pattern alias,DIN input ve
üretim entegrasyonu kapıları sürer. Üretim aynı,M7 NO-GO;yüklenmemeli.

---

# 28 Ekim 2026 — Aktif MSC CBW iptali / M7 NO-GO

Bu üst bölüm günceldir. MSC OUT2'nin31B komut bekleme aktarımı artık
emülasyondaki ortak kapanış bariyerine katılır. Native deconfigure/root
teardown ve Bulk-Only Reset(0xFF) eski job disable/ACK,AHB idle,ortak RX
FIFO drain ve seçili TX FIFO2 flush tamamlanana kadar ertelenir. Eski HAL
pointer/count ve ready ancak bu bariyerden sonra temizlenir;sonra native
class teardown veya BOT reset/tek CBW rearm ve MIDI resume yürür. MIDI/DIN
verisi korunur. Üretim firmware'i aynı;fiziksel cihaz/MIDI/USB API erişimi yok.

Kapsam CBW bekleme,kısmi alınmış CBW ve henüz komut işlenmemiş completion'dır.
Başlamış SCSI/storage komutu,BOT data/CSW veya aktif IN82 varsa durumları
silinmez;kapalıda tutulur. Bunların iptal/drain/recovery'si çözülmedi. Bu
native storage/media I/O ya da gerçek USB donanım bariyeri kanıtı değildir.
Tamamlanmış komutların olası async storage sahipliği de ayrıca izlenmelidir.

Yeni ayrı katman:src/midi_usb_msc_prototype.py,2924B,0807A800..0807B36C;
256B state20048020..20048120,toplam2168B sentetik state.64B private scratch
bu256B'ye dahildir.10 stok giriş ve2 generated control-entry gate;pin'li
orijinal byte,overlap ve application bounds kontrolü var. Üretim builder'ına
eklenmedi;checked production RAM reservation/init yoktur. Önceki composite,
control,IRQ,session codegen aynı. Tek eski kaynak değişikliği IRQ helper'da
optional EP2 disable ve manuel seçili FIFO2 flush-completion sözleşmesidir.

Native kanıt:661F8/6624E→2EFF8 stok reset state'i hemen sıfırlayıp OUT2'yi
yeniden arm eder;iptal bariyeri yoktur.52EDC stok close CTL/mask AND yapar,
disable ACK beklemez.27624 MSC availability counter'larını tüketip2F014 /
2F04A→458D0 SCSI yolunu çağırır. Yeni task entry/handler gate'leri request
geldikten sonra eski CBW'nin storage komutuna dönüşmesini engeller. Zaten
native poll içindeyken TASK_BUSY korunur;main iptal service'i ilerlemez.
Yalnız owned main-context native teardown'un pin'li iç MIDI deinit bildirimi
yutulur;harici reset yeni generation olarak saklanır.

MSC completion native IRQ içinde yalnız claim edilir. CPU FIFO kopyası ve
diğer arayüzlerin ortak RX kayıtları bitmeden native ready yayımlanmaz.
Epoch/ticket barrier modeli altında anlamlıdır;hardware generation tag'i
değildir. Bariyer ihlal edilip eski untagged XFRC yeniden açılıştan sonra
verilirse yeni job gibi görünür;zorunlu negatif testte hâlâ FAIL.

531CC native CPU kopyası byte sayısını word'e yuvarlar.32B padded CBW için
yeni guard gerçek ve yuvarlanmış yazı sınırını kontrol eder;hatalı <=64B
packet private scratch'a drain edilerek kapalıya alınır. Tekrarlanan bozuk
packet scratch sonundaki state'e taşmaz. >64B / DMA ve genel MSC data
buffer güvenliği kanıtı yoktur;bozuk durumda yeniden açılma reddedilir.

21 yeni/384 toplam test PASS. Native USB reset→enum→address→config,aktif
CBW deconfig/reconfig,gerçek Bulk-Only Reset,gecikmiş/missing ACK/flush/AHB,
kısmi CBW/shared FIFO,DIN Off ve admitted MIDI debt korunması,native poll
içinde reset,submit/teardown sırasında yeni reset,ticket wrap,CPU overflow
ve stale XFRC negatifleri testli. Yerel CFG/ABI:SP delta0,BL8 hizalama,
max32B ek local frame;4 yeni maskeli bölüm,max29 komut,call/loop yok.
Inherited control max38 komut sınırı aynı. Bunlar gerçek cycle,tam native
stack,IRQ latency veya scheduler/NVIC/cache/bus-master kanıtı değildir.

Yeni:scripts/{midi_usb_msc_test_support,audit_midi_usb_msc_prototype,
trace_midi_usb_msc,probe_midi_usb_msc}.py;tests/test_midi_usb_msc.py;
docs/MIDI-USB-MSC-5706.md. Eski kaynaklardan yalnız
scripts/midi_usb_irq_test_support.py bilinçli değişti. Önceden var olan
kullanıcı değişiklikleri ve diğer kaynaklar korunur.

Bütün Python komutları `.venv\Scripts\python.exe`, `-O` yok:
- `-m unittest discover -s tests -v`: **384 PASS** (363 önceki+21 yeni),
  logs/usb-msc-cancel-20261028/all-tests-final.txt.
- `scripts/probe_midi_usb_msc.py logs/usb-msc-cancel-20261028/probe-final`:
  paket üzerine emulator-only overlay21 PASS,audit/stock trace PASS;
  exit2/NO-GO beklenir. Üretim Off/Stop FAIL negatifi korunur.
- `scripts/patch_firmware.py --build-phase1`:PASS;21 patch/1376B fark aynı.
- `scripts/verify_phase1_candidate.py`:87 regresyon/6 sınırlı kriter PASS;
  üretim Off/Stop FAIL,exit2;
  logs/phase1-verification-20261028T155342Z/report.json.
- `scripts/run_baseline.py`:PASS;logs/baseline-20261028T155342441203Z.
- `scripts/audit_phase1_safety.py logs/usb-msc-cancel-20261028/production-audit`:
  PASS;stok/vector/app bounds/CRC/manifest aynı. `git diff --check`:PASS.

İlk testte native ready counter artmadı:ready+28'i word ile temizlemek
kapasite+29'u da sıfırlamıştı. Byte clear ile düzeltildi;native atomic23CEA
ve2CA6C gövdeleri stub değildir. Bir kısmi-packet testi EP0 setup'dan önce
CBW'yi FIFO'ya koyduğu için fixture setup sırası bozuldu;eski hardware
packet'i request'ten sonra,bariyerden önce teslim edecek şekilde düzeltildi.
Guard gevşetilmedi. İlk FAIL logları korunur. Native MSC parent submit
hatasını yuttuğundan ticket-wrap ayrıca katman durumuyla fail-closed testli.

Kod SHA256:7915a0ae43b3852ae2ceb49b24a97cde9997755891b13c8ca28f24aa1874d925.
Aday SYX3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Stok SHA256:
11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.
Diff/hash/komut kayıtları:logs/usb-msc-cancel-20261028/{session.diff,
hashes.json,probe-final,build.txt,verify.txt,baseline.txt,production-audit.txt}.

**Sonraki tek somut iş:**native SCSI READ10/WRITE10→stok storage callback /
worker zincirinde data buffer ve async iş sahipliğini izlemek;aktif komut
varken reset/deconfigure için güvenli drain/abort sonucunu kanıtlayıp bugün
kapalıda tutulan MSC data/CSW/TX safhalarını tamamlamak. Özel SD filesystem
yazılmayacak. Sonrasında task/power/class-list wiring,tam boot/RAM/init/OOM,
storage short-read/live-pattern alias,DIN input,gerçek bariyer/timing ve
üretim entegrasyonu kapıları sürer. M7 NO-GO;firmware yüklenmemeli.

---

# 28 Ekim 2026 — Gerçek MIDI parent ve boşta composite MIDI+MSC / M7 NO-GO

Bu üst bölüm günceldir. Gerçek MIDI parent68A2C artık no-op yerine yürür.
Native parent'ın297C0 ile tüm çıkışları temizleyerek bekleyen DIN Note Off
mesajlarını sildiği negatif kontrolde görüldü. Yeni dar guard yalnız owned,
sealed ve pin'li68A37 dönüş PC'sinde bu temizliği atlar;USB temizliği daha
önce bariyerde tamamlanır. Native29AB0 rearm denemesi de çalışır;MIDI RX
ancak ortak kurulum bittikten sonra resume ile açılır. Diğer normal router
clear çağrıları native kalır. Üretim paketi aynı;cihaza erişilmedi.

Yeni996B/96B composite deney katmanı,40B5A'daki kayıtlı iki-class isteğini
erteler;ana service bariyerinden sonra native class-list walker,MIDI525B2
ve gerçek parent,ardından MSC525B2/661DC çalışır. MSC'nin OUT2 global RX
flush'u da yalnız owned sealed constructor/caller bağlamında atlanır.
IN81/IN82 seçili TX FIFO flush'ları native kalır. MSC parent gerçek BOT
reset ve31B CBW arm gövdesini yürütür;yalnız storage Init(LUN0) callback'i
pin'li native return0 sınırıdır. SD/MSC veri aktarımı kanıtı değildir.

Native40A78,200067E0 buffer'ında125B/3-interface descriptor üretir;
MIDI OUT1/IN81 ve MSC IN82/OUT2 kayıtları korunur. Native reset→enum→
SET_ADDRESS→SET_CONFIGURATION→main service→MIDI inquiry yanıtı ve native
iki-class teardown/gerçek MSC deinit koşullu PASS. MSC endpoint aktifse,
completion bekliyorsa veya BOT boş değilse yeni liste kurulumu reddedilir.
Queue sonrası yeni MSC sahibi belirmesi constructor'ı engeller. Aktif MSC
iptali uygulanmadı;native close yürütmek hardware disable/ACK kanıtı değildir.

Parent'lar arasındaki reset sonraki MSC constructor'ını durdurur;MSC arm'dan
sonraki reset MIDI resume'u durdurur ve MSC sahipliğini silmez. Shared RX
borcu veya shared payload okuyucusu varsa önceki kapalıda sahiplik koruma
politikası sürer. Stale untagged XFRC'nin bozuk bariyer sonrası yeni job gibi
görünmesi eski zorunlu negatif testte sürer. Genel cancel/drain açık.

Pin'li native68A54 statik initializer walker'ı taze Unicorn'da çalıştırıldı:
6668C endpoint constructor'ını da yürütür;önceki 'yalnız scatter-load'
tanımı eksikti. Native MIDI/MSC callback tabloları ve endpoint array'leri
doğrulandı. Bu tam reset/boot/RTOS yürütmesi değildir. Deney fixture'ı bilinen
native tabloları sentetik root/controller nesnelerine bağlar;tam boot grafiği
iddiası yoktur. Sadece kayıtlı iki-class liste kapsanır;diğer liste şekilleri,
Packs geçişleri,power-state ve class-specific request uyumu açık.

Yeni kod0807A400..0807A7E4,state20047D80..20047DE0.4 stok gate +1 generated
control-entry overlay;orijinal byte/overlap/app bounds kontrolleri var. Toplam
1912B sentetik state;checked production reservation/init yoktur. Yerel CFG /
ABI:SP delta0,BL8 hizalama,max24B ek frame;zorunlu maskeli bölüm eklenmedi.
Önceki control/default IRQ/session codegen hash'leri aynı. Gerçek cycle /
IRQ latency,tüm native stack ve NVIC/cache/bus-master bariyeri kanıtlanmadı.

Yeni:src/midi_usb_composite_prototype.py;
scripts/{midi_usb_composite_test_support,audit_midi_usb_composite_prototype,
trace_midi_usb_composite,probe_midi_usb_composite}.py;
tests/test_midi_usb_composite.py;docs/MIDI-USB-COMPOSITE-5706.md.
Tek eski kaynak değişikliği:scripts/midi_usb_irq_test_support.py,owned
constructor için optional TX FIFO2 flush ve seçili FIFO model düzeltmesi.
Diğer eski kaynaklar korunur;önceden var olan kullanıcı değişiklikleri durur.

Bütün Python komutları `.venv\Scripts\python.exe`, `-O` yok:
- `-m unittest discover -s tests -v`: **363 PASS** (347 önceki +16 yeni).
  logs/usb-composite-20261028/all-tests-final.txt.
- `scripts/probe_midi_usb_composite.py logs/usb-composite-20261028/probe-final`:
  paket üstünde emulator overlay16 PASS,audit/stock trace PASS;exit2/NO-GO
  beklenir. Üretim Off/Stop FAIL negatifi raporda korunur.
- `scripts/patch_firmware.py --build-phase1`:PASS;21 patch/1376B fark aynı.
- `scripts/verify_phase1_candidate.py`:87 regresyon/6 sınırlı kriter PASS;
  üretim Off/Stop FAIL,exit2;logs/phase1-verification-20261028T005043Z/report.json.
- `scripts/run_baseline.py`:PASS;logs/baseline-20261028T005059338326Z.
- `scripts/audit_phase1_safety.py logs/usb-composite-20261028/production-audit`:
  PASS;stok/vector/app bounds/CRC/manifest aynı. `git diff --check`:PASS.

İlk test hataları ve düzeltilen varsayımlar:descriptor fixture'ı yanlış
buffer'da çağrıldığı için kopya header94B kalmıştı;40B24 literal'iyle native
200067E0 buffer'ına düzeltildi. DIN koruma testi USB kopyasını da FIFO'da
bıraktığından doğru quiet guard kurulumu durdurdu;native USB drain sonrası
eski job iptal edilirken iki DIN FIFO kopyası tutulacak şekilde düzeltildi.
Bu korumalar gevşetilmedi. İlk FAIL logları korunur. Ürün negatifleri silinmedi.

Composite kod SHA256:10d64c5e138fe59210d44e3f614fd5633cd3312d8fc136c925b18cce49533586.
Aday SHA256:3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Stok SHA256:
11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.
Diff/hash/komut çıktıları:logs/usb-composite-20261028/{session.diff,hashes.json,
probe-final,build.txt,verify.txt,baseline.txt,production-audit.txt}.

**Sonraki tek somut iş:**MSC OUT2'nin31B CBW bekleyen aktif job'ını native
BOT/class-specific request ve EP2 disable/ACK yollarıyla izleyip ortak
reset/deconfigure/reconfigure bariyerine katmak;MIDI/DIN sahipliğini ve ortak
RX FIFO'yu koruyarak güvenli yeniden kurulumunu emülasyonda kanıtlamak.
Sonrasında task wiring/power-state,tam boot/RAM/init/OOM,storage short-read /
live-pattern alias,DIN input,gerçek bariyer/timing ve üretim entegrasyonu
kapıları sürer. M7 NO-GO;firmware yükleme veya fiziksel test önerilmez.

---

# 28 Ekim 2026 — Native reset/EP0 ve ertelenmiş class kurulumu / M7 NO-GO

Bu üst bölüm günceldir. USBRST/ENUMDONE,EP0 SET_ADDRESS ve
SET_CONFIGURATION(0/1),native deinit/init ve MIDI yeniden açma yolu artık
emülasyonda koşullu PASS. Yeni1464B/96B kontrol katmanı,reset/deinit'te kabulü
dondurur;native525B2 kurulumunu ana bağlamdaki iptal bariyerinden sonraya
erteler. Başlangıç availability release'i,runtime completion'dan ayrıldı.
**Parent bildirimi pin'li native no-op sınırıdır;gerçek parent/MSC/tam boot
ve donanım bariyeri henüz kanıtlanmadı.** Üretim aynı/Off-Stop FAIL,M7 NO-GO.
Cihaz/MIDI/USB API erişimi yoktur.

Native EP0 zinciri4293E→2C78C→425A8→44DD8→42584/4259A→2AB08/2AB14→
40B5A/40B7E→525B2/5261C yürür. Reset/enum native register ve EP0 kurulum
gövdesi de çalışır. Class init isteği kopyalanır;ACK/flush/boş yazılım sahipliği
gelmeden native endpoint kurulmaz. Yapılandırma isteğinin USB status ZLP'si
native yoldadır;MIDI uçları hazır olana kadar yeni RX kurulmaz. İlk testlerin
bir kısmı addressed state'i fixture önkoşulu olarak verir;bir tam test native
reset→enum→SET_ADDRESS→SET_CONFIGURATION zincirini yürütür.

Native525B2 iki farklı flush yapar:OUT1→2C928/4312C/52E22 ortak RX FIFO'yu,
IN81→52E04 seçili TX FIFO1'i temizler. Bariyer tamamlandıktan sonra yalnız
kayıtlı MIDI OUT1 ve pin'li525CB dönüş PC'si için global RX flush atlanır.
Diğer native yollar korunur;USBreset'in stok all-TX flush'u aynı kalır.
Native525FE availability initialization yalnız sealed/init-busy/no-owned-TX
koşulunda kabul edilir;wire completion sayılmaz.

SOF5271A→268EC partial RX'i2691E ile completion dışından yayımlayabilir.
Bu deney kayıtlı MIDI SOF poll'unu bastırır ve native RX'i tek64B MTU job'a
sınırlar.66B ring kaydı sığmıyorsa sahte aktif job ayrılmaz;RX_PAUSED tutulur.
Ana service,alan açıldığında yeniden arm eder. RTOS/task entegrasyonu ve
throughput/latency fiziksel kanıtı yoktur. Diğer endpoint'ler bu kısıtlamayı
almaz. Default IRQ varyantının820B kodu/hash'i aynı;kontrol varyantında yalnız
izinli GINT maskesi ve sealed üst fazı için2 immediate değişir.

Reset/deinit event generation,queued init ve final commit sahipliği ayrı
tutulur. Kurulum sırasında veya son commit öncesi gelen reset kaybolmaz.
Resume beklerken native constructor/parent bildirimi tekrarlanmaz. Wrap /
yanlış bağlam reddedilir. Kabul edilmiş RX borcu,shared SysEx okuyucusu,
partial/held nota veya Off/fault varsa kapalıda sahiplik korunur;silinmez.
Genel aktif işlem cancel/drain hâlâ yoktur.

8 native emulator gate;1464B ek kod,96B ek RAM/toplam1816B sentetik state.
Yerel SP delta0/BL8 hizalama/max32B frame PASS. Yeni zorunlu maskeli bölüm
max38 komut;call/loop yok. Bu gerçek cycle/IRQ latency veya tüm native stack
kanıtı değildir. Native class-parent bildirimi80427D2 no-op sınırındadır;
tam composite MSC/descriptor/power-state graph ve gerçek parent uygulama
yan etkileri açık. Suspend/wakeup ve DMA hâlâ unsupported/fail-closed.

Kritik negatif korunur:iptal bariyeri ihlal edilip eski hardware XFRC yeni
RX kurulduktan sonra gelirse yeni job gibi görünebilir. Snapshot hardware
generation tag'i değildir. Gerçek disable/FIFO/NVIC/cache/bus-master ve tam
scheduler kanıtı yoktur. Checked1816B RAM/init,full boot/OOM,storage/DIN input
ve üretim entegrasyonu kapıları sürer. Firmware'e eklenmedi.

Yeni:src/midi_usb_control_prototype.py;
scripts/{midi_usb_control_test_support,audit_midi_usb_control_prototype,
trace_midi_usb_control,probe_midi_usb_control}.py;
tests/test_midi_usb_control.py;docs/MIDI-USB-CONTROL-5706.md.
Bilinçli eski kaynak değişiklikleri:src/midi_usb_irq_prototype.py optional
IRQ policy parametreleri;session test helper'da MIDI dışı EP0'ı job sanmama;
IRQ test helper'da optional control/MMIO flush ve6-endpoint modeli. Default
codegen ve diğer eski kaynaklar korunur.8 doküman başlığı güncellendi.

Bütün Python komutları `.venv\Scripts\python.exe`, `-O` yok:
- `-m unittest discover -s tests -v`: **347 PASS** (325 önceki+22 yeni).
- `scripts/probe_midi_usb_control.py logs/usb-control-20261028/probe`:
  paket üzerine yalnız emulator overlay22 PASS;native reset/EP0/deferred
  init koşullu PASS;full parent/lifecycle/task uyumu FAIL,exit2/NO-GO.
- `scripts/patch_firmware.py --build-phase1`:PASS;aynı21 patch/1376B fark.
- `scripts/verify_phase1_candidate.py`:87 regresyon/6 sınırlı kriter PASS;
  üretim Off/Stop FAIL,exit2;logs/phase1-verification-20261027T235647Z/report.json.
- `scripts/run_baseline.py`:PASS;logs/baseline-20261027T235647455648Z.
- `scripts/audit_phase1_safety.py logs/usb-control-20261028/production-audit`:
  PASS;stok/vector/app bounds/CRC/manifest aynı. `git diff --check`:PASS.

İlk hipotez hataları:2C928'i clear-stall sanmak yanlıştı;flush olduğu ve
OUT'ta global RX etkisi pin'li native yoldan görüldü. Native IN constructor
flush'unu manuel bariyer flush'u sanan fixture ilk testte52E10 loop budget'ına
takıldı;yalnız owned init bağlamında hardware flush-complete modeli eklendi.
Native ctor girişindeki nested reset aynı PC'yi tekrar yürütünce fixture
assert'i yanlış tetiklendi;tek çağrı girişine taşındı. Yeni test eklerken DMA
satırları yanlış metoda taşındı;tam koşudan önce düzeltildi. İlk FAIL logları
log kökünde korunur. Ürün negatifleri kaldırılmadı.

Loglar logs/usb-control-20261028:all-tests.txt,probe/{report.json,audit,
stock-contract},build/verify/baseline/production-audit.txt,session.diff,hashes.json.
Kontrol kod SHA256:97240c3b615a45755022470af82278fac7db25ebdff9970800f12a05442f76e2;
IRQ kontrol varyantı8a63d6c5c85574fa362ebff18c9048a1298bedd0202755ad1a1ce0492df8b5b1.
Aday SHA256:3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Stok SHA256:
11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.

**Sonraki tek somut iş:**525B2/5261C'nin gerçek MIDI class-parent callback'ini
ve composite MIDI+MSC class listesinin native kuruluş/teardown'unu no-op
sınırı yerine yürütmek;ertelenmiş kurulumun parent/status/diğer arayüz
sözleşmesini koruduğunu göstermek. Ardından power-state/descriptor ve task
service wiring,genel cancel-drain,gerçek bariyer/timing/RAM/boot/storage /
DIN input ve üretim entegrasyonu kapıları var. Yüklenmemeli.

---

# 28 Ekim 2026 — Native USB completion IRQ köprüsü / M7 NO-GO

Bu üst bölüm günceldir. Önceki deneyde testin sağladığı completion kimliği
yerine,stok HAL submit→FIFO→IRQ→native callback zinciri artık emülasyonda
yürür. Yeni820B/96B köprü,halen sahipli job'ı IRQ girişinde sabitler;stok
callback yalnız bu snapshot'ı claim eder. Yayın/native rearm IRQ turundan
sonra yapılır. **CPU FIFO completion alt kümesi koşullu PASS**. Tam USB
reset/kontrol/disconnect dönüşü ve gerçek iptal bariyeri hâlâ açıktır.
Üretim aynı/Off-Stop FAIL,M7 NO-GO. Cihaz/MIDI/USB API erişimi yoktur.

Native RX zinciri4293E→2C798→42614→2AB42→40C46→526C8→26988;
TX4293E→2C7AC→42690→2AB36→40C22→5268E→268E0→268D0. Callback tablosu
806776C ve root global20006F20 byte pin'li.2C9B8/42FD8 hardware-boundary
stub'ları bu deneyde kaldırıldı;4301A/52F52 submit,531A6 TX FIFO ve531CC RX
CPU kopyası native yürür. Fixture yalnız register/FIFO olaylarını modeller.

Önemli sıralama:stok IRQ gövdesi OUT completion'ını RXFLVL kopyasından önce
işleyebilir. Bridge,26988 çağrısını o anda yayımlamaz. Native IRQ döndükten
ve shared RX FIFO boşaldıktan sonra HAL byte count ile tek yayın yapar.
Çok kayıtlı FIFO birden fazla IRQ gerektirirse aynı eski RX snapshot'ı
tutulur;yeni RX transferi kurulmaz. Cancel epoch'u değişince eski pending
snapshot sayılarak düşürülür. Yanlış LR/IRQ dışı/nested callback snapshot
ödünç alamaz. Callback anında güncel job ticket'ı okunmaz.

Native2C82A..2C862 kurulum prefix'i yürütüldü:HAL handle200054B4,
USBx40040000,6 endpoint ve handle+10=0 CPU FIFO modu. Bu kısmi kurulumdur;
427FC donanım init/tam boot/OOM yürütülmedi. Canlı testler40040000 tabanı
ile sentetik handle/controller/list binding kullanır. IPSR16 enjeksiyonu
gerçek NVIC/exception entry/öncelik veya physical IRQ kanıtı değildir.

Kritik negatif:donanım XFRC bayrağı generation taşımaz. Varsayılan iptal
bariyeri ihlal edilip eski bir XFRC yeni RX kurulduktan sonra gelirse yeni
job tamamlanmış görünebilir. Gerekli negatif test bunu açıkça gösterir.
IRQ girişinde snapshot almak donanım generation tag'i değildir;gerçek
disable/ACK/FIFO ve cache/bus-master kanıtının yerini tutmaz. Önceki geç
DMA buffer bozulma negatifleri de değişmeden geçer.

Kapsam sınırı:yalnız maskeli RXFLVL/IEPINT/OEPINT ve CPU mode0 desteklenir.
DMA veya reset/kontrol IRQ nedeni kapalı hataya geçer. Native5261C doğrudan
disconnect de önce sahipliği dondurur;çalışan reset/disconnect recovery yoktur.
Dolayısıyla native completion uyumu PASS olsa da genel üretim uyumu FAIL.
Genel shared-reader/RX-debt cancel-drain ve bütün inline yazarlar açıktır.

4 ek emülasyon gate;önceki2 callback overlay'i assert edilerek değiştirilir.
Yerel frame max32B,SP delta0,BL8 hizalama PASS;bridge yeni IRQ maskesi koymaz.
Native IRQ yerel frame64B+bridge24B=88B;bu callee/exception frame toplamı
değildir. Toplam1720B sentetik RAM üretimde rezerve/init edilmiş değildir.
Önceki default kaynak/codegen ve firmware hash'leri değişmedi.

Yeni dosyalar:src/midi_usb_irq_prototype.py;
scripts/{midi_usb_irq_test_support,audit_midi_usb_irq_prototype,
trace_midi_usb_irq,probe_midi_usb_irq}.py;
tests/test_midi_usb_irq.py;docs/MIDI-USB-IRQ-5706.md.
STATUS/CHANGELOG,ROADMAP,RECOVERY,UI-TRACE,PHASE1-GO-GATES,
MIDI-USB-SESSION ve tests/README güncellendi.

Bütün Python komutları `.venv\Scripts\python.exe`, `-O` yok:
- `-m unittest discover -s tests -v`: **325 PASS** (306 önceki+19 yeni).
- `scripts/probe_midi_usb_irq.py logs/usb-irq-20261028/probe`:paket üzerine
  emülasyon overlay19 PASS;native completion köprüsü koşullu PASS;reset /
  kontrol/DMA unsupported,gerçek bariyer NOT_ESTABLISHED,exit2/NO-GO.
- `scripts/patch_firmware.py --build-phase1`:PASS;aynı21 patch/1376B fark.
- `scripts/verify_phase1_candidate.py`:87 regresyon/6 sınırlı kriter PASS;
  üretim Off/Stop FAIL,exit2;logs/phase1-verification-20261027T231216Z/report.json.
- `scripts/run_baseline.py`:PASS;logs/baseline-20261027T231216225056Z.
- `scripts/audit_phase1_safety.py logs/usb-irq-20261028/production-audit`:
  PASS;stok/vector/app bounds/CRC/manifest aynı. `git diff --check`:PASS.

Başarısız varsayım:completion geldiğinde RX bytes zaten RAM'dedir varsayımı
coalesced IRQ sırasına uymaz;bu yüzden yayın IRQ sonuna ertelendi. İlk yerel
CFG auditor'ı disconnect trampoline'ına fallthrough'u yeni fonksiyon sanıp
stok adrese kadar yürüdü (KeyError08052620);tail sınırı düzeltildi. Runtime
testleri ilk3/sonraki17/son19 turda PASS;ürün negatifleri kaldırılmadı.

Loglar logs/usb-irq-20261028:all-tests.txt,probe/{report.json,audit,
stock-contract},build/verify/baseline/production-audit.txt,session.diff,
hashes.json. Kod SHA256:
ef45bacef7a218db2a8f2e4798a9bf60e899dbf1b7ffad044df037c3ff5b55d4.
Aday SHA256:3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Stok SHA256:
11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.

**Sonraki tek somut iş:**stok USB reset/kontrol IRQ ve5261C→525B2
deconfigure/reconfigure zincirini native yürütüp close/drain/barrier sonrası
yeniden açma protokolüne bağlamak;normal kontrol IRQ'larının BROKEN'a düşmesi
ve constructor'ın untagged availability release'i üretim uyumu engelleridir.
Sonra gerçek bariyer/cache/NVIC/timing,checked1720B RAM/init,full boot/OOM,
storage,DIN input,genel cancel-drain ve üretim entegrasyonu kapıları var.
Yüklenmemeli.

---

# 28 Ekim 2026 — USB endpoint iptal bariyeri / koşullu deney, M7 NO-GO

Bu üst bölüm günceldir. Yazılım sahipleri boşken USB endpoint'te kalan eski
TX yanıtı, yeni3176B/128B session wrapper'ında iptal ediliyor. Eski transferin
epoch/ticket kimliğiyle gelen RX/TX completion yeni oturuma kabul edilmiyor.
**Bunlar sentetik MMIO sözleşmesi ve immutable job bridge koşuluyla PASS**.
Gerçek DMA'nın durması ve stok IRQ bridge entegrasyonu kanıtlanmadı;tam session
güvenliği çözülmüş değildir. Üretim aynı,Off/Stop FAIL,M7 NO-GO. Fiziksel cihaz,
MIDI veya USB API erişimi yoktur. Önceki kaynaklar/değişiklikler korundu.

Protokol:OPEN→CLOSING→WAIT_DISABLE→WAIT_FLUSH→SEALED→OPEN. RX ve USB TX kabulü
kapanır;yalnız MIDI IN81/OUT01 interrupt maskeleri kapatılır;SNAK/EPDIS isteği,
EPENA=0 ve gereken disable ACK,shared RX FIFO boşluğu ve AHB idle beklenir.
Yalnız TX FIFO1 flush edilir;global RX/all-endpoint stop yoktur. Tamamlanmadan
payload/native staging/HAL pointer'ları serbest bırakılmaz. Sonra native RAM
reset/epoch artırımı yapılır;resume donanım durumunu yeniden kontrol eder.
Her service çağrısı sınırlıdır;eksik ACK/flush tamamlanması kapalıda bekletir.

Sınır:bekleyen RX borcu,partial MIDI,held nota,Off/fault sahipliği veya ortak
SysEx okuyucuları varsa close reddedilir;silinmez. Genel aktif transaction
iptali/drain hâlâ açık. İki yönün ticket ayırması ve completion claim'i atomik;
duplicate/nested callback ikinci kez serbest bırakmaz. Stok26988 r1'de byte
sayısı alır;bu sayı owned RX transfer limitini aşamaz. Native268D0'ın PC-relative
CBZ'si flags korunarak taşındı;timer var/yok ve foreign nesne yolları testli.

11 ek emulator gate;önceki RX rearm/completion overlay'leri assert edilerek
değiştirilir. Generated recovery/lifecycle girişleri de yalnız emülatörde
sarılır;default codegen'leri değişmez. Yerel frame max32B,SP delta0 ve BL8
hizalama PASS. Zorunlu maskeli bölüm max26 komut;call/loop yok. Toplam1624B
sentetik RAM üretimde rezerve değildir. Native toplam stack/cycle/IRQ/cache
ve bütün inline writer'lar kanıtlanmadı.

Kritik negatifler korunur:stok completion callback'leri job kimliği taşımaz;
kayıtlı untagged girişler bu deneyde reddedilir,stok IRQ uyumu FAIL. Kimlik
tek başına DMA bariyeri değildir:iptal sözleşmesi ihlal edilip eski bus-master
yeni RX buffer'a yazdırılınca veri bozulur,callback'in reddi bunu geri alamaz.
`hardware_late_dma_after_barrier=NOT_ESTABLISHED`. Callback anında güncel
endpoint'ten token kopyalamak çözüm değildir. Model gerçek donanım kanıtı sayılmaz.

Yeni dosyalar:src/midi_usb_session_prototype.py;
scripts/{midi_usb_session_test_support,audit_midi_usb_session_prototype,
trace_midi_usb_session,probe_midi_usb_session}.py;
tests/test_midi_usb_session.py;docs/MIDI-USB-SESSION-5706.md.
STATUS/CHANGELOG,ROADMAP,RECOVERY,UI-TRACE,PHASE1-GO-GATES,
MIDI-USB-LIFECYCLE ve tests/README güncellendi.

Bütün Python komutları `.venv\Scripts\python.exe`, `-O` yok:
- `scripts/patch_firmware.py --build-phase1`:PASS;aynı21 patch/1376B fark.
- `-m unittest discover -s tests -v`: **306 PASS** (281 önceki+25 yeni).
- `scripts/probe_midi_usb_session.py logs/usb-session-20261028/probe`:
  paket üzerine yalnız emulator overlay25 PASS;koşullu TX iptali/tagged RX
  callback PASS,raw stock uyumu FAIL,gerçek geç DMA NOT_ESTABLISHED,exit2.
- `scripts/verify_phase1_candidate.py`:87 regresyon/6 sınırlı kriter PASS;
  üretim Off/Stop FAIL,exit2. logs/phase1-verification-20261027T213708Z/report.json.
- `scripts/run_baseline.py`:PASS;logs/baseline-20261027T213708701663Z.
- `scripts/audit_phase1_safety.py logs/usb-session-20261028/production-audit`:
  PASS;stok/vector/app bounds/CRC/manifest korunur. `git diff --check`:PASS.

Başarısız ilk denemeler:RX byte count'unun completion ABI'sinden aktarılmaması;
yeni cave overlay ve nested test trampoline'ın tam-flash fixture kontrolüne
eklenmemesi;henüz TX başlamadan failure beklenmesi. Düzeltildi. Ek timer testi
foreign nesneye capacity1 verilmediği için native counter'ı 0'da doygunlaştırdı;
fixture düzeltildi. İlk FAIL logları saklandı;ürün negatifleri kaldırılmadı.
İlk native trace prologue assert'i yanlış elle yazılmıştı;pin'li stok baytı
70b44d78 ile düzeltildi. Native davranış değiştirilmedi.

Log kökü logs/usb-session-20261028:all-tests.txt,probe/{report.json,audit,
stock-contract},build/verify/baseline/production-audit.txt,session.diff,
hashes.json. Yeni kod SHA256:
fe091ec2e783a8eab3210405df7dcca0302dfea2e7056d20e69c06522cfcbf9d.
Aday SHA256:3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Stok SHA256:
11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.

**Sonraki tek somut iş:**stok USB IRQ/completion/reset/disconnect zincirini
native yürütüp immutable transfer-job bridge'in nerede tutulacağını ve
disable/ACK/FIFO bariyerinin gerçekten bütün eski RX/DMA yazarlarını bitirdiğini
göstermek;önce bu deneyin raw-stock uyum FAIL'ini kapatmak. Sonra genel
shared-reader/RX-debt cancel-drain ve checked1624B RAM/init,tam boot/OOM,
zamanlama,storage,DIN input,üretim entegrasyonu kapıları var. Yüklenmemeli.

---

# 28 Ekim 2026 — RX lifecycle guard ve boşta reset/resume / M7 NO-GO

Bu üst bölüm günceldir. Kayıtlı RX nesnelerinin consumer/producer/reset ve
rearm girişleri emülasyonda korundu;boşta reset→CLOSED→resume protokolü var.
Bekleyen sorgu/partial mesaj/held nota/publish/aktif endpoint varken reset
reddedilir. **Aktif TX disconnect/session güvenliği FAIL kalır**. Fiziksel
cihaz/MIDI/USB API erişimi yok;stok ve üretim aynı;önceki değişiklikler korundu.

Native kanıt:269F0'ın bulunan tek doğrudan çağrısı29B2A. Generic2A374 reset
callsite'ları401BA/E2 TX tarafında;5261C disconnect callback'i RX ring'i
temizlemez. Stok6668C..666BA endpoint constructor prefix'i native allocator
ile yürütüldü:RX01 port20005F94/controller20005CC8,16x64B kayıt ve1057B ring;
TX81'de RX ring yok. Bu kısmi constructor kanıtıdır,tam boot/RTOS değildir.

Yeni2350B wrapper/64B sentetik state;toplam1496B RAM üretimde rezerve değil.
15 native gate+poll overlay,registered pointer ve native LR token'larıyla
consumer/raw writer'ı korur;diğer nesnelerin native yolu sürer. Publish/reset
handshake maskeli bölümde max9 komut,call/loop yok. Yerel frame max32B,SP delta0,
BL8 hizalama PASS;native toplam stack/cycle/gerçek IRQ/inline writers açık.
Kuyruk data/capacity/port/parser/controller kimliği değişir veya configured≠3
olursa RX frozen olur;borçlar silinmez. Epoch wrap reddedilir.

Yeni kritik negatif:retry active0 olsa bile17B yanıt native USB endpoint'te
in-flight kalabilir. Reset bunu busy sayar;fakat RX freeze eski TX aktarımını
iptal etmez. Yeniden configured durumda eski yanıt teslim edilir. Ayrıca
resume sonrası eski RX DMA completion'ının session eşleşmesi kanıtlanmadı.
Bu iki konu çözülmeden tam disconnect/üretim güvenliği iddiası yoktur.

Yeni dosyalar:src/midi_usb_lifecycle_prototype.py;
scripts/{midi_usb_lifecycle_test_support,audit_midi_usb_lifecycle_prototype,
trace_midi_usb_lifecycle,probe_midi_usb_lifecycle}.py;
tests/test_midi_usb_lifecycle.py;docs/MIDI-USB-LIFECYCLE-5706.md.
STATUS/CHANGELOG,ROADMAP,RECOVERY,UI-TRACE,PHASE1-GO-GATES,MIDI-USB-LEDGER ve
tests/README güncellendi. Önceki kaynak ve codegen hash'leri değişmedi.

Bütün Python komutları `.venv\Scripts\python.exe`, `-O` yok:
- `scripts/patch_firmware.py --build-phase1`:PASS;aynı21 patch/1376B fark.
- `-m unittest discover -s tests -v`: **281 PASS** (262 önceki +19 yeni).
- `scripts/probe_midi_usb_lifecycle.py logs/usb-lifecycle-20261027/probe`:
  paket üzerine yalnız emulator overlay19 PASS;RX typed gates/quiescent
  reset/publish interleave PASS;aktif TX disconnect FAIL,late RX DMA /
  gerçekIRQ NOT_ESTABLISHED,production uyumu FAIL,exit2/NO-GO.
- `scripts/verify_phase1_candidate.py`:87 regresyon/6 sınırlı kriter PASS;
  üretim Off/Stop FAIL,exit2. logs/phase1-verification-20261027T210615Z/report.json.
- `scripts/run_baseline.py`:PASS;logs/baseline-20261027T210636534130Z.
- `scripts/audit_phase1_safety.py logs/usb-lifecycle-20261027/production-audit`:
  PASS;stok/vector/app bounds/CRC/manifest korunur. `git diff --check`:PASS.

İlk fixture sorunları:translated-block cache'te eski constructor kodu kalması;
retry slotunun endpoint completion sanılması. Cache invalidate ve native
endpoint in-flight kontrolü eklendi. Son test eklemesindeki yanlış metoda
taşınan satırlar düzeltildi. İlk FAIL logları korundu;ürün negatifleri sürer.

Log kökü logs/usb-lifecycle-20261027 (27'de başladı,28 yerel tarihte tamamlandı):
all-tests.txt,probe/{report.json,audit,stock-contract},build/verify/baseline /
production-audit.txt,session.diff,hashes.json. Kod SHA256:
13241d42aebe8d4a9b586932e92239fc67b0cf8df1a2f83d494663acdb121a0b.
Aday SHA256:3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Stok SHA256:
11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.

Başarısız varsayım:RX indeks eşitliği ve boş retry slotu yeni session için
yeterli değildir. Native TX endpoint ayrı sahibidir;RX guards bunu iptal etmez.
Kontrollü RAM reset protokolü hardware transfer-generation kanıtı değildir.

**Sonraki tek somut iş:**native RX/TX endpoint'leri için ortak cancel/drain ve
transfer-generation sahipliği;eski TX ve geç RX completion'ın yeni bağlantıya
taşınmadığını emülasyonda kanıtlamak. GO için checked1496B RAM/init,tam boot /
OOM,zamanlama,DIN input,tüm producer/observer/mode,stock storage recovery ve
üretim entegrasyonu açık. Yüklenmemeli.

---

# Önceki kayıt — Dolu sayaçta kabul edilmiş USB kayıtları ilerliyor / M7 NO-GO

Bu bölüm önceki ledger deneyinin kaydıdır. Önceki iki engel,**USB yazılım RX kuyruğuna tam olarak
kabul edilmiş kayıtlar için** yeni ledger prototipinde kapandı:sıra korunur,
dolu inquiry sayacının arkasındaki Note On/Stop/Clock işlenir. Donanım/MIDI/USB
API erişimi yok;stok ve üretim firmware aynı. Önceki değişiklikler korundu.

Native RX ring yeni borcun sahibidir:işlenmiş packet header00 olur;counter
dolu inquiry için81 private marker kalır. SCANNED yalnız işlenmiş tam kayıt
sınırını tutar;fresh host81/cable8 reddedilir. Tekrar tarama parser'ı tekrar
çağırmaz. Borç sayaca taşınmadan head ack edilmez;arkadaki kabul edilmiş
musical kayıtlar sırayla yürür. Snapshot dışında/yarım yayımlanmış kayıt
işlenmez. Tur başına en fazla1 native pop ve1 TX kabul denemesi vardır.

**Garanti sınırı:**native ring doluyken yeni kayıt enqueue0 ile reddedilebilir.
Host'ta veya henüz kabul edilmemiş USB verisinde koşulsuz latency garantisi
yoktur. Gerçek IRQ/DMA,task süresi,boot-created ring ve bütün lifecycle
yolları kanıtlanmadı. Private marker'ı native fallback/reset/başka consumer'ın
okuması önlenmeden üretime eklenemez. M7 NO-GO devam eder.

Yeni964B kod,172B arena/toplam1432B sentetik RAM aynı. UIX3 magic,tek endpoint /
cable0,6..2048B ring ve64B item doğrulaması. Native item-size bir byte'tır;
padding kontrol edilmez. Eski722B/616B USB ve recovery/retry kodları aynı.
Yerel CFG/ABI PASS:SP delta0,8B call hizalama,max frame32B,IRQ maskesi yok.
2048B ring/2046B sorgu penceresi testinde157.912 emüle komut ölçüldü;açık
stress bütçesi500.000,diğer küçük çağrılarda100.000 sınırı aynı. Bu fiziksel
cycle/latency veya tüm native callback grafiği için üst sınır değildir.

Yeni kaynaklar:src/midi_usb_ledger_prototype.py;
scripts/{midi_usb_ledger_test_support,audit_midi_usb_ledger_prototype,
probe_midi_usb_ledger}.py;tests/test_midi_usb_ledger.py;
docs/MIDI-USB-LEDGER-5706.md. STATUS/CHANGELOG,ROADMAP,RECOVERY,UI-TRACE,
PHASE1-GO-GATES,MIDI-USB-ORDER ve tests/README güncellendi. Önceki kaynaklar
değiştirilmedi. İlk uygulama kullanım sınırı nedeniyle otomatik onay
incelemesinde yürütülmemişti;devam mesajından sonra normal araçlarla uygulandı.

Bütün Python komutları `.venv\Scripts\python.exe`, `-O` yok:
- `scripts/patch_firmware.py --build-phase1`:PASS;aynı21 patch/1376B fark.
- `-m unittest discover -s tests -v`: **262 PASS** (244 önceki +18 yeni).
- `scripts/probe_midi_usb_ledger.py logs/usb-inquiry-ledger-20261027/probe`:
  gerçek paket üzerine emulator overlay18 PASS;committed-window order /
  Clock-Stop/ownership PASS;host pre-admission latency/IRQ lifecycle
  NOT_ESTABLISHED,DIN input NOT_IMPLEMENTED,production uyumu FAIL,exit2/NO-GO.
- `scripts/verify_phase1_candidate.py`:87 regresyon/6 sınırlı kriter PASS;
  üretim Off/Stop FAIL,exit2. logs/phase1-verification-20261027T204245Z/report.json.
- `scripts/run_baseline.py`:PASS;logs/baseline-20261027T204302627974Z.
- `scripts/audit_phase1_safety.py logs/usb-inquiry-ledger-20261027/production-audit`:
  PASS;stok/vector/app bounds/CRC/manifest korunur. `git diff --check`:PASS.

Kanıt:182/192B kabul edilmiş RX penceresinde21 borç+8 sayaç ve tam29 yanıt;
On/Stop/Clock sırası ve gerçek receiver/ownership;yalnız header yazısı/payload
korunumu;fragment/wrap;partial publication;producer-during-consumer snapshot;
forged marker/provenance/context ret;16 karma native sıra karşılaştırması;
native360B USB-DIN output stall+24 yanıt;her iki modda64 Off/Stop/raw proje;
max2048 ring. Eski negatif kontroller ve karşılaştırma kodları değişmedi.

Log kökü:logs/usb-inquiry-ledger-20261027;all-tests.txt,probe/report.json,
probe/audit,build/verify/baseline/production-audit.txt,session.diff,hashes.json.
İlk audit/ ara guard kaydıdır;güncel kod probe/audit'te. Kod SHA256:
bd43c2b77b861c710e99fc3f81c23bc607ddf9858eab09b6335c7e5310f20fa8.
Aday SHA256:3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Stok SHA256:
11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.

Önceki başarısız varsayım:counter dolduğunda RX cursor'unu tutmak,arkadaki
admitted Clock/Stop'u da durduruyordu. Yeni model borcu mevcut RX kaydında
tutar;musical byte'ları öne atlamadan işler. Kapasite büyütülmedi,kabul edilen
istek silinmedi. Bu,host tarafındaki sınırsız trafik sorununu çözmez.

**Sonraki tek somut iş:**native RX ring'in bütün consumer/reset/flush /
disconnect yollarını çıkarıp private header + SCANNED sahipliğinin yaşam
döngüsünü emülasyonda doğrulamak. GO için ayrıca gerçek boot ring bağlama,
IRQ/DMA/task bütçesi,checked RAM/init,DIN input,tüm producer/observer/mode,
stock storage recovery ve M7 üretim entegrasyonu açık. Yüklenmemeli.

---

# Önceki kayıt — USB Note On / Stop sırası düzeltildi / M7 NO-GO

Bu bölüm önceki ordered deneyinin kaydıdır. Deferred Note On /
Stop sıra bozulması yeni `ordered=True` emülasyon varyantında kapatıldı.
Fiziksel cihaz/MIDI/USB API erişimi yoktur;üretim ve stok firmware değişmedi.
Önceki commit edilmemiş işler ve eski negatif kontroller korundu.

Inquiry yanıtları mevcut word'de0..8 yükümlülük olarak sayılır;aynı istekler
birleştirilip silinmez,8 sorgu8 yanıt üretir. Müzikal byte'lar native parser'a
tek yoldan,geliş sırasıyla gider. Realtime bypass kodu yeni varyantta yoktur.
Poll sonunda en fazla1 submit;kabul0 olmadan sayaç azalmaz. Böylece busy TX
durumunda Note On→Stop anında doğru sırada işlenir;TX açılınca eski On gelmez.
Gerçek Stop→Note On ve yarım mesaj içindeki realtime native sırası korunur.

Kapasite doluysa yeniF0 parser'dan önce tutulur;cursor tam aynı byte'a geri
alınır ve suffix'ten hiçbir mesaj öne geçmez. Tam kapasitede de yeniSysEx
yoksa nota/transport devam eder. Eski2 inquiry+sonraki buffer F8/FC vakası
artık ilerler. **Kalan engel:**8 pending+9. inquiry arkasındaki Clock/Stop
bekleyebilir;genel gecikme kriteri FAIL. Bunu gizleyen bypass eklenmedi.

Yeni kod616B,172B arena/toplam1432B sentetik RAM aynı;ek RAM gerekmedi.
YeniUIX2 magic,eski bit düzenini sayaç gibi okumayı engeller. Eski722B USB
ve recovery/retry kod varyantları aynı hash'lerde. Tek endpoint/cable0 ve
main-context tüketici varsayımı sürer. Checked üretim RAM/init entegrasyonu yok.
Yerel audit PASS:SP delta0,8B BL hizalama,max frame32B,IRQ maskesi yok;
tek parser yolu/tek reply denemesi/bounded buffer döngüleri doğrulandı.

Değişen kaynaklar:src/midi_usb_inquiry_prototype.py;
scripts/{midi_usb_inquiry_test_support,audit_midi_usb_inquiry_prototype}.py.
Yeni:tests/test_midi_usb_order.py,scripts/probe_midi_usb_order.py,
docs/MIDI-USB-ORDER-5706.md. STATUS/CHANGELOG,ROADMAP,RECOVERY,UI-TRACE,
PHASE1-GO-GATES,MIDI-USB-INQUIRY-RETRY ve tests/README güncellendi.

Bütün Python komutları `.venv\Scripts\python.exe`, `-O` yok:
- `scripts/patch_firmware.py --build-phase1`:PASS;aynı21 patch/1376B fark.
- `-m unittest discover -s tests -v`: **244 PASS** (230 önceki +14 yeni).
- `scripts/probe_midi_usb_order.py logs/usb-inquiry-order-20261027/probe`:
  gerçek paket üzerine emulator overlay ile14 PASS;Note On/Stop sırası PASS,
  kapasite gecikmesi FAIL,production_integrated=false,exit2/NO-GO.
- `scripts/verify_phase1_candidate.py`:87 regresyon/6 sınırlı kriter PASS;
  üretim Off/Stop FAIL,exit2. logs/phase1-verification-20261027T175205Z/report.json.
- `scripts/run_baseline.py`:PASS;logs/baseline-20261027T175301577028Z.
- `scripts/audit_phase1_safety.py logs/usb-inquiry-order-20261027/production-audit`:
  PASS;stok/vector/app bounds/CRC/manifest korunur. `git diff --check`:PASS.

Kanıt kapsamı:gerçek note receiver/ownership ve raw proje korunumu;96 sıra /
parçalama kombinasyonu;24 karma akışın stok/native parser ile karşılaştırması;
running status/velocity0/partial mesaj içi realtime;kapasite bariyeri ve9 tam
yanıt;nested/context/invalid count;native360B USB-DIN output stall ve8 tam
yanıt;her iki modda64 Off/Stop. DIN input retry ve tamobserver uyumu yoktur.
İlk testte audit parametresi ve setup-öncesi alan okuması eksikti;düzeltildi,
tests-first.txt korundu. Negatif kabul kriterleri gevşetilmedi.

Log kökü:logs/usb-inquiry-order-20261027;all-tests.txt,probe/report.json,
probe/audit,build.txt,verify.txt,baseline.txt,production-audit.txt,session.diff,
hashes.json. Yeni kod SHA256:
f90f6c6291511fc4e63591c34a2f48050f04de5dea1c073ea3468689a6d5b119.
Aday SHA256:3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Stok SHA256:
11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.

Önceki başarısız varsayım:Stop'u öne almak ve notayı sonra oynatmak güvenli
değildir. Yeni çözümde tek ordered parser yolu vardır;note suppression veya
quarantine reset yoktur. Tam kapasitede gecikmeyi sırasız dispatch ile gizlemez.

**Sonraki tek somut iş:**8 pending+9. SysEx başlangıcı tutulurken sonraki
Clock/Stop için bu sıra garantisini bozmayan kabul/geri basınç ve gecikme
çözümü. Kapasite büyütmek tek başına kabul değildir. GO için ayrıca DIN input,
tüm producer/observer ve lifecycle/mode uyumu,checked RAM/init,boot/OOM,
stock storage recovery,IRQ/DMA/disconnect ve süre bütçesi açık. Yüklenmemeli.

---

# Önceki kayıt — USB inquiry otomatik retry deneyi / NO-GO

Bu bölüm önceki tek-token/bypass deneyinin kaydıdır. M7 tamamlanmadı.
Fiziksel cihaz, MIDI/USB portu veya donanım API'sine erişilmedi. Üretim ve
stok firmware baytları aynı; önceki commit edilmemiş değişiklikler korundu.

Önceki USB inquiry kaybının dar senaryosu aşıldı: tek endpoint/cable0 için
TX meşgulken alınan6B inquiry, sahipli token ve64B RX cursor ile tutulur.
Native parser/pop/short dispatcher çalışır; TX slotu kabul edince token
bırakılır. Host resend olmadan tek17B yanıt gelir. Aynı retained buffer'daki
Clock/Stop bir kez işlenir; yalnız realtime içeren sonraki buffer'lar ilerler.
Native USB/DIN çıkış stall'ı,360B aktarım,8 inquiry burst,split/wrap/reentry
ve her iki modda64 Off+Stop/raw proje korunumu testlidir. DIN girişine retry
eklenmedi. Diğer SysEx/update handler'lar yeniden çalıştırılmadı.

**Genel çözüm değildir:** iki gerekli negatif kontrol FAIL kalır:
1. İlk buffer'ın ikinci inquiry'si cursor'u tutarsa sonraki buffer'daki
   Clock/Stop, TX boşalana kadar bekler.
2. Aynı buffer'da inquiry, Note On, Stop varsa realtime bypass Stop'u öne
   alır; gecikmiş Note On sonra dispatch edilir. Müzikal sıra korunmaz.
Bu nedenle prototip üretime eklenmedi; production_caller_compatibility FAIL.
Exact inquiry multicast observer uyumu ve full/overflow politikası da açık.

Yeni722B Thumb/172B arena, toplam1432B sentetik RAM.20047C00/20047800/20047000
üretimde boş RAM değildir. Yerel CFG/ABI PASS: SP delta0,8B call hizalama,
max yerel frame32B; IRQ maskesi eklenmez, buffer taramaları sınırlıdır.
Native toplam stack/cycle, gerçek IRQ/task-switch/full boot kanıtı değildir.

Yeni dosyalar:src/midi_usb_inquiry_prototype.py;
scripts/{midi_usb_inquiry_test_support,audit_midi_usb_inquiry_prototype,
probe_midi_usb_inquiry}.py;tests/test_midi_usb_inquiry.py;
docs/MIDI-USB-INQUIRY-RETRY-5706.md. STATUS/CHANGELOG,ROADMAP,RECOVERY,UI-TRACE,
PHASE1-GO-GATES,MIDI-SYSEX-REQUEST ve tests/README güncellendi.
Önceki recovery/retry kaynakları ve üç retry kod hash'i değişmedi.

Doğrulama; bütün Python komutları `.venv\Scripts\python.exe`, `-O` yok:
- `scripts/patch_firmware.py --build-phase1`:PASS;aynı21 patch/1376B fark.
- `-m unittest discover -s tests -v`: **230 PASS** (213 önceki +17 yeni).
- `scripts/probe_midi_usb_inquiry.py logs/usb-inquiry-retry-20261027/probe-final`:
  gerçek paket üzerine emulator overlay,17 PASS;iki negatif kriter FAIL,
  DIN input NOT_IMPLEMENTED,production_integrated=false,exit2/NO-GO.
- `scripts/verify_phase1_candidate.py`:87 regresyon/6 sınırlı kriter PASS;
  üretim Off/Stop FAIL,exit2. Rapor:logs/phase1-verification-20261027T170345Z.
- `scripts/run_baseline.py`:BASELINE PASS;logs/baseline-20261027T170425734024Z.
- `scripts/audit_phase1_safety.py logs/usb-inquiry-retry-20261027/production-audit`:
  PASS;stok pin/vector/app bounds/CRC/manifest korunur.
- Yeni yerel kod audit'i PASS;native disassembly ve overlay manifesti
  probe-final/audit altında. `git diff --check`:PASS (mevcut CRLF uyarıları).

İlk fixture beklentilerinin nedenleri ve korunmuş başarısız loglar yeni
MIDI-USB-INQUIRY-RETRY belgesinde. Ürün negatifleri gevşetilmedi.
Log kökü:logs/usb-inquiry-retry-20261027;all-tests-final.txt,probe-final/report.json,
build.txt,verify.txt,baseline.txt,production-audit.txt,session.diff ve hashes.json.
Yeni kod SHA256:b1b24f86615963f3a4cc08366c51a4bade7604cc53b880412877aa54edfe0b0b.
Aday SHA256:3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Stok SHA256:
11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.

Başarısız varsayım: RX cursor'u tutup aynı buffer'daki realtime'ı öne almak
genel Clock/Stop hizmeti ve sıra korunumu sağlamaz. Daha fazla buffer tek
başına çözüm değildir. Recovery fault'unda inquiry token'ı bilerek bekler;
SysEx testi geçsin diye quarantine temizlenmez.

**Sonraki tek somut iş:** inquiry kabul/yanıt yükümlülüğünü müzikal RX
cursor'undan ayıran bounded admission katmanı; yukarıdaki iki negatif
senaryoyu kapasite doluluğu ve sıra testleriyle birlikte kapatmak.
GO için ayrıca DIN input/tüm producer-observer uyumu,üretim entegrasyonu,
checked1432B RAM/atomik init,mode/reset-resume,stock storage recovery,tam
boot/OOM ve IRQ/DMA/USB-disconnect/PRIMASK süre bütçesi açık. Yüklenmemeli.

---

# Önceki kayıt — Üst formatter öncesi kapasite rezervasyonu / NO-GO

Bu bölüm önceki rezervasyon deneyinin kaydıdır. M7 tamamlanmadı.
Yalnız yerel pin'li bayt/Capstone ve sentetik RAM'de Unicorn çalışıldı.
Fiziksel cihaz,MIDI/USB portu veya donanım API'sine erişilmedi. Mevcut commit
edilmemiş değişiklikler/arşivler korundu;üretim firmware'i aynı.

32120/32154/32188/321BC/321F4,4691A'dan önce formatter çalıştırıyordu.
Yeni isteğe bağlı reservations=True varyantı,bu beş girişte kapasiteyi kaynak
mutasyonundan önce rezerve eder. Native r0-r3/stack argümanları5..7 ve dönüş
korunur. Full/PRIMASK1/IPSR!=0/invalid router veya seçili fault durumunda ret1;
ortak source ve callback sahibi değişmez. Beklenen native dönüş PC'siyle
yalnız o alt producer/router kabulü rezervasyonu kullanır. Nested üst/native
alt/direct submit bunu alamaz;service üst gövde dönene kadar ertelenir.
Üst çağrı dönünce rezervasyon bırakılır;payload ve kabul bildirimi önceki
aktif slot sözleşmesini sürdürür. Çağıranın açık retry'si testlidir.

Önemli yeni negatif kanıt: gerçek USB/DIN byte parser ve24B68 dağıtıcısı,
TX doluyken inquiry isteğini tüketir;listener ret'i yok sayılır. Boşaldıktan
sonra otomatik retry yoktur. Açık yeniden gönderim17B yanıt üretir. Dolayısıyla
native_usb_din_consumed_request_retry ve production_caller_compatibility FAIL
kalır. Input registry'sine yalnız read-only inquiry listener'ı bağlandı;
tam26DE8/update/storage handler'ları yürütülmedi. Update ACK'in43544/435D6
çağrıları yan etkilerden sonra bulunur;yalnız bayt/disassembly kanıtıdır.

Yeni kod2878B,retry arena428B;recovery832B ile toplam1260B sentetik RAM.
20047800/20047000 üretimde boş alan değildir. Önceki bildirimli2050B ve
bildirim kapalı1750B varyantları aynı hash'leri üretir. Üretim hook'u yoktur.
Yerel CFG:SP delta0,BL/BLX8 hizalama,max yerel frame48B;maskeli yollarda
call/loop yok,max22 komut. Native toplam stack/cycle,gerçek IRQ/RTOS değildir.

Değişen kaynaklar:src/midi_sysex_retry_prototype.py;
scripts/{midi_sysex_retry_test_support,audit_midi_sysex_retry_prototype}.py.
Yeni:scripts/{trace_midi_sysex_requests,probe_midi_sysex_request_reservation}.py,
tests/test_midi_sysex_request_reservation.py,docs/MIDI-SYSEX-REQUEST-5706.md.
Bu belge/CHANGELOG.md,docs/{MIDI-SYSEX-NOTIFICATION-5706,
MIDI-SYSEX-RETRY-PROTOTYPE-5706,MIDI-RECOVERY-PROTOTYPE-5706,
PHASE1-GO-GATES,ROADMAP,RECOVERY,UI-TRACE-5706}.md ve tests/README.md güncellendi.

Doğrulama;bütün Python komutları `.venv\Scripts\python.exe`,-O yok:

- `scripts/patch_firmware.py --build-phase1`:PASS;aynı21 patch/1376B fark.
- `-m unittest discover -s tests -v`: **213 PASS**;önceki202 +11 yeni.
- `scripts/verify_phase1_candidate.py`:87 aday regresyonu/6 sınırlı kriter
  PASS;Off/Stop probe'ları FAIL,CRITICAL_RUNTIME_PROBE_FAILED,exit2/NO-GO.
- `scripts/run_baseline.py`:BASELINE PASS.
- `scripts/audit_phase1_safety.py logs/recovery-sysex-request-20261027/production-audit`:
  PASS;stok pin,vector/kimlik512B,app bounds,CRC/manifest korunur.
- Önceki `probe_midi_recovery_prototype.py`,`probe_midi_sysex_retry_prototype.py`,
  `probe_midi_sysex_notification.py`,aynı log kökünde24/14/11 testi PASS;
  kendi negatif kontrolleri veNO-GO/exit2 korunur.
- `scripts/probe_midi_sysex_request_reservation.py logs/recovery-sysex-request-20261027/probe-final`:
  paketlenmiş imaj üzerine yalnız emülasyon overlay'leriyle11 test PASS;
  upper rezervasyon/nested sahiplik/açık retry PASS;eski upper source koruması
  ve native USB-DIN consumed request retry FAIL;production_integrated=false,
  production_caller_compatibility FAIL,NO-GO/exit2.

Yeni kapsam:beş gerçek upper formatter/stack callback-context eşleşmesi;
full slotta invalid source'a erişilmemesi;disabled/fault/mask,PRIMASK/IPSR ve
bilinmeyen router/token;nested üst ve direct/native alt çağrı;native USB-DIN
120B stall/tam byte ve raw proje korunumu;iki ingress yolunda inquiry kaybı
ve açık retransmit pozitif kontrolü. İlk geniş koşuda üç fixture beklentisi
yanlıştı:capture native router'ı sayar,direct API'yi saymaz;ilk poll bağlar;
fault recovery Stop ekler. Bu beklentiler düzeltildi;negatif kabul şartları
gevşetilmedi. tests-expanded-first.txt FAIL kaydı korundu.

Loglar:logs/recovery-sysex-request-20261027/{build,all-tests,verify,baseline,
audit,recovery-probe,retry-probe,notification-probe,request-probe}.txt;
probe-final/{report,retry-code-report}.json ve stock-contract/. Oturum farkı
session.diff,hash listesi session-hashes.json. Verifier:
logs/phase1-verification-20261027T163133Z/report.json (UTC).
Rezervasyonlu kod SHA256:321fca8a65d1ef9c99b0cf05ed1e7bd61ccf128ee06d8891ad0fe3e52b53141a.
Aday SHA256:3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Stok SHA256:
11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.

Başarısız varsayım:yalnız4691A guard'ı upstream formatter'ı korumaz. Erken
rezervasyon tested beş girişi korur,ama ret'i yok sayan RX dağıtıcısına retry
eklemez. Finite buffer veya güvenli ret tek başına yanıt teslimi kanıtı değildir.

GO için:native RX cursor/pop/ack ve request/update ACK yaşam döngüsü;
Clock/Off/Stop hizmeti korunarak geri basınç;tüm producer/üretim SysEx-recovery
entegrasyonu;1260B checked heap/atomik init;mode guard/reset-resume;stok storage
hata-kurtarma;tam boot/OOM ve gerçek IRQ/DMA/USB-disconnect/PRIMASK süre bütçesi.
**Sonraki tek somut iş:**native USB RX cursor/pop/ack noktasında,TX doluyken
inquiry sahipliğini tutan bounded retry prototipi ve interleaved Clock/Stop
hizmetinin durmadığı emülasyon. Ayrıntı:MIDI-SYSEX-REQUEST-5706.md.
Donanıma yüklenmemeli.

---

# Önceki kayıt — SysEx kabul bildirimi işlem sahibine bağlandı / NO-GO

Bu bölüm günceldir; aşağıdaki kayıtlar tarihseldir. M7 tamamlanmadı.
Yalnız pin'li bayt/Capstone ve sentetik RAM'de Unicorn çalışıldı. Fiziksel
cihaz, MIDI/USB portu veya donanım API'sine erişilmedi. Mevcut commit edilmemiş
değişiklikler ve arşivler korundu; üretim firmware'i aynı kaldı.

Native sözleşme düzeltildi:299B0 bildirimi ayrı gecikmiş bir job/wire completion
değildir. Bütün seçili portlar kabul ettiğinde aynı çağrı içinde event0 verir;
payload hâlâ pending'dir. Native scatter-loader68A54,20000920 nesnesini
vtable8069460 ile kurar; bu vtable'ın+4'ü24B68 multicast dispatcher'ıdır.
24B68 ->468EC ->global owner callback zinciri gerçek Thumb koduyla sınandı.
Önceki job/completion yorumu bu kanıtla güncellendi; bütün dolaylı olaylar
bulundu iddiası yoktur. Scatter-load, tam boot değildir.

Yeni notifications=True varyantı, event listesi ve owner function/context'i
submit sırasında atomik sahipli kopyaya alır; bütün portlar kabul ettiğinde
native24B68 ile event0'ı bir kez çağırır. Başka listener sırası/context'leri
korunur. Callback bitene ve payload okuyucuları bitene kadar slot tutulur.
Callback penceresinde okuyucular bitirilse de nested request/submit/service
ilk sahibin yerini alamaz. Global owner/event listesi sonradan ezilse de
kabul edilmiş istek doğru callback'i çağırır. Submit0 hâlâ yerel kabul demektir.

Bildirimli kod2050B, retry RAM424B; recovery832B ile toplam1256B sentetik
RAM.20047800/20047000 üretimde boş alan değildir. notifications=False,
önceki1750B kodu aynı hash ile üretir;14 eski retry ve24 recovery testi kalır.
Yeni local CFG:SP delta0/BL-BLX8 hizalama,max yerel frame32B; maskeli yollarda
call/loop yok,max17 komut. Callback süresi, native toplam stack/cycle ve
gerçek IRQ/task grafiği kanıtı değildir.

Değişen kaynaklar:src/midi_sysex_retry_prototype.py;
scripts/{midi_sysex_retry_test_support,audit_midi_sysex_retry_prototype}.py.
Yeni:scripts/{trace_midi_sysex_notification,probe_midi_sysex_notification}.py,
tests/test_midi_sysex_notification.py,docs/MIDI-SYSEX-NOTIFICATION-5706.md.
Bu belge/CHANGELOG.md ve docs/{MIDI-SYSEX-RETRY-PROTOTYPE-5706,
MIDI-RECOVERY-PROTOTYPE-5706,PHASE1-GO-GATES,ROADMAP,RECOVERY,UI-TRACE-5706}.md,
tests/README.md güncellendi. Üretim kaynakları ve recovery çekirdeği aynı.

Doğrulama; bütün Python komutları `.venv\Scripts\python.exe`, `-O` yok:

- `scripts/patch_firmware.py --build-phase1`:PASS;21 patch/1376B fark aynı.
- `-m unittest discover -s tests -v`: **202 PASS**; önceki191 +11 yeni.
- `scripts/verify_phase1_candidate.py`:87 aday regresyonu/6 sınırlı kriter
  PASS; aday Off/Stop FAIL,CRITICAL_RUNTIME_PROBE_FAILED,exit2/NO-GO.
- `scripts/run_baseline.py`:BASELINE PASS.
- `scripts/audit_phase1_safety.py logs/recovery-sysex-completion-20261027/production-audit`:
  PASS;stok pin,vector/kimlik512B,app bounds,CRC/manifest korundu.
- `scripts/probe_midi_recovery_prototype.py logs/recovery-sysex-completion-20261027/recovery-probe`:
  24 eski deneysel test/6 recovery vaka PASS;NO-GO/exit2.
- `scripts/probe_midi_sysex_retry_prototype.py logs/recovery-sysex-completion-20261027/retry-probe`:
  bildirim kapalı14 test PASS; eski full-slot/owner/source negatif kontrolleri
  korunur;production_integrated=false,NO-GO/exit2.
- `scripts/probe_midi_sysex_notification.py logs/recovery-sysex-completion-20261027/probe`:
  gerçek paket üzerine yalnız Unicorn overlay ile11 test PASS; sahipli native
  kabul bildirimi/12 caller/reader bitişinde nested callback PASS; eski bildirim
  teslimi FAIL,wire completion NOT_ESTABLISHED,production_caller_compatibility
  FAIL;production_integrated=false,NO-GO/exit2.

Yeni kapsam:scatter-load/vtable,senkron kabul sırası;12 gerçek çağıran r0 ve
payload/mask/bayt eşleşmesi;partial admission,3 listener/null owner/boş event;
callback içinde reader drain/reentry;native USB-DIN360B stall ve raw proje
baytları;invalid metadata/fault,ABI/SP/canary. İlk7/9/11 test/probe koşuları
korundu;son callback adaptörü native468EC'nin r2 function pointer'ını da korur.

Loglar:logs/recovery-sysex-completion-20261027/{build,all-tests-final,verify,
baseline,audit,recovery-probe,retry-probe,probe}.txt;probe/{report,retry-code-report}.json,
probe/stock-contract/. Kaynak/doküman oturum farkı session.diff,hash'ler
session-hashes.json. Verifier:logs/phase1-verification-20261027T114206Z/report.json.
Bildirimli kod SHA256:c541d9d2c207f8230c75466b52342698e464a2077a7afa426c3bbaee9fb4fbe0.
Bildirim kapalı kod:ae8d859e129a72bb02e6e6916ac7ca6a256b30dc6699ff612eacc84ae617b266.
Aday SHA256:3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Stok SHA256:
11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.

Başarısız varsayım: ayrı gecikmiş job bildirimi bulunmadı; native olay kabul
sırasında senkron. Yalnız global owner veya reader bitişi native bildirimi
korumaya yetmez. Eski bildirim kapalı varyantın callback kaybı ve full-slot
yanıt kaybı negatif kontrolleri saklandı. Yeni callback içi send ret'i de
request geri basıncı olmadan üretim uyumluluğu değildir.

GO için:request/recursive send ret politikası ve tüm upstream formatter/
producer/lifecycle;üretim SysEx/recovery entegrasyonu;1256B checked heap/atomik
init;mode guard/reset-resume;stok storage hata-kurtarma;tam boot/OOM ve gerçek
IRQ/DMA/USB-disconnect/PRIMASK süre bütçesi.
**Sonraki tek somut iş:** sonucu yok sayan response üreticilerinin request
girişlerini izleyip,formatter/source mutasyonundan önce kuyruk kapasitesi
rezervasyonu/geri basıncı doğrulamak.32120 ->46A54,4691A guard'ından önce
payload oluşturur;12 doğrudan giriş bütün upstream yazarları kapsamaz.
Ayrıntı:MIDI-SYSEX-NOTIFICATION-5706.md. Donanıma yüklenmemeli.

---

# Önceki kayıt — On iki SysEx çağıranı, sahipli kopya ve port bazında retry / NO-GO

Bu bölüm günceldir; aşağıdaki kayıtlar tarihseldir. M7 tamamlanmadı.
Yalnız yerel bayt/Capstone ve sentetik RAM'de Unicorn çalışıldı. Cihaz,
MIDI/USB portu veya donanım API'si kullanılmadı. Önceki commit edilmemiş
değişiklikler ve arşivler korundu; üretim kaynaklarına recovery bağlanmadı.

298B8'in 12 doğrudan çağıranı gerçek kodla sınandı: üçü sonucu yok sayar,
dokuzu iletir; hiçbirinde yerel retry yoktur. Yeni ayrı Thumb prototipi tek
360B payload'ı dönüşten önce sahiplenir; WAITING/ACCEPTED maskeleriyle yalnız
henüz kabul etmeyen portu yeniden dener. Servis başına en fazla üç deneme;
reader bitmeden reuse yoktur. Native USB/DIN stall ve kısmi fanout'ta tekrar
ve source/stack ezilmesi test edilen akışlarda önlendi.

Kuyruk kilidi tek başına geç kalıyor: nested formatter statik kaynağı,
4691A ise global callback sahibini router kabulünden önce ezebiliyor.
12 üretici girişine yalnız Unicorn'da özgün baytları doğrulanmış guard'lar
eklendi. Sağlıklı çağıran payload/mask/r0 sonuçları eşleşiyor; aktif işlemde
bu iki ezilme engelleniyor. Korumasız karşı deneyler saklandı.

Önemli sınır: yeni submit0 yalnız yerel kopya kabulüdür; native success/job
callback veya wire completion değildir. Dolu slotta ret'i yok sayan üç
çağıranın yanıtı hâlâ kaybolur. Yerel payload okuyucuları bittikten sonraki
callback sahipliği ve request geri basıncı uygulanmadı. Yeni API üretim
router'ının doğrudan karşılığı olarak sunulmaz; üretim uyumluluğu FAIL kalır.

Yeni kod 1750B, ek sentetik RAM 384B; önceki recovery 1140B/832B ile toplam
1216B test RAM'i. 20047800/20047000 üretimde boş alan değildir; checked heap,
atomik init ve boot/OOM kanıtı yoktur. Yerel audit SP delta0/BL8 hizalama,
max yerel frame32B ve IRQ-mask bölümünde call/loop olmadan max14 komut verir.
Bu, native toplam stack/cycle veya gerçek IRQ/DMA zamanlama kanıtı değildir.

Yeni dosyalar: src/midi_sysex_retry_prototype.py;
scripts/{midi_sysex_retry_test_support,audit_midi_sysex_retry_prototype,
probe_midi_sysex_retry_prototype}.py; tests/test_midi_sysex_retry_prototype.py;
docs/MIDI-SYSEX-RETRY-PROTOTYPE-5706.md. Güncellenenler:
scripts/trace_midi_sysex_contract.py, bu belge, CHANGELOG.md,
docs/{MIDI-RECOVERY-PROTOTYPE-5706,PHASE1-GO-GATES,ROADMAP,RECOVERY,UI-TRACE-5706}.md
ve tests/README.md. Önceki recovery kaynakları ve üretim patch listesi aynı.

Doğrulama; bütün Python komutları `.venv\Scripts\python.exe`, `-O` yok:

- `scripts/patch_firmware.py --build-phase1`: PASS; aynı 21 patch/1376B fark.
- `-m unittest discover -s tests -v`: **191 PASS**, önceki 177 + 14 yeni.
- `scripts/verify_phase1_candidate.py`: 87 aday regresyonu/6 sınırlı kriter
  PASS; aday Off/Stop probe'ları FAIL, CRITICAL_RUNTIME_PROBE_FAILED, exit2.
- `scripts/run_baseline.py`: BASELINE PASS.
- `scripts/audit_phase1_safety.py logs/recovery-sysex-retry-20261027/production-audit`:
  PASS; stok pin, app sınırları, vector/kimlik512B, CRC/manifest korunuyor.
- `scripts/probe_midi_recovery_prototype.py logs/recovery-sysex-retry-20261027/recovery-probe`:
  önceki 24 deneysel test/6 recovery vaka PASS; production_integrated=false,
  all_producer_quarantine=REVIEW_REQUIRED, NO-GO/exit2.
- `scripts/probe_midi_sysex_retry_prototype.py logs/recovery-sysex-retry-20261027/probe`:
  paketlenmiş imaj üzerine izole overlay ile 14 test PASS; owned_payload_and_port_retry
  ve guarded_formatter_reentry_and_active_callback_owner PASS; korumasız iki
  ezilme ve ignored_full_queue_response_delivery FAIL; native_completion_callback_contract
  NOT_IMPLEMENTED, production_caller_compatibility FAIL, NO-GO/exit2.

Loglar: logs/recovery-sysex-retry-20261027/{build,all-tests,verify,baseline,audit,
recovery-probe,probe-first}.txt; probe/{report,retry-code-report}.json,
probe/stock-contract/. İlk koşular ve önceki logs/recovery-sysex-20261027 korunur.
Kaynak/doküman oturum farkı session.diff, hash'ler session-hashes.json.
Verifier: logs/phase1-verification-20261027T100454Z/report.json (UTC).
Yeni deneysel kod SHA256: ae8d859e129a72bb02e6e6916ac7ca6a256b30dc6699ff612eacc84ae617b266.
Aday SHA256: 3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image 38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC 53F96711, 371368B. Stok SHA256:
11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.

Başarısız varsayımlar: kör retry kısmi fanout'u çoğaltır; dönüşten sonra
stack kaynağına güvenilemez. Kuyruk kilidi formatter/global callback için geç
kalır; erken guard bunu test edilen yollarda kapatır. Sonlu buffer, ret'i yok
sayan request'in yanıt kaybını çözmez. Bu karşı deneyler kaldırılmadı.

GO için kalanlar: request geri basıncı ve completion callback yaşam döngüsü;
tüm producer/lifecycle ve üretim SysEx/recovery entegrasyonu; 1216B checked
RAM/atomik init; mode guard/reset-resume; stok storage hata-kurtarma; tam
boot/OOM; gerçek IRQ/DMA/USB-disconnect ve PRIMASK süre bütçesi.
**Sonraki tek somut iş:** router+20 bildirim nesnesi ile 468EC job callback
zincirini izleyip, payload reader bitişinden sonra gecikmiş bildirim/yeni istek
çakışmasında işlem sahibini koruyan yaşam döngüsünü emülasyonda doğrulamak.
Ayrıntı: MIDI-SYSEX-RETRY-PROTOTYPE-5706.md. Donanıma yüklenmemeli.

---

# Önceki kayıt — SysEx bypass deneysel olarak kapandı; üretim hâlâ NO-GO

Bu bölüm günceldir; aşağıdaki günlük kayıtları tarihseldir. M7 tamamlanmadı.
Yalnız yerel bayt/Capstone ve sentetik RAM'de Unicorn çalışıldı. Fiziksel
cihaz, MIDI/USB portu veya donanım API'sine erişilmedi. Mevcut commit edilmemiş
değişiklikler ve arşivler korundu; üretim kaynaklarına recovery bağlanmadı.

SysEx vtable+C kabulü artık fault/busy/PRIMASK=1 altında pointer bağlamaz.
En fazla bir native poll geçişi; eski transfer sürüyorsa ret0. Native40232'nin
bekleme döngüsü çağrılmaz. Native4028C'nin ready=0 iken pending'i gizlemesi
ayrıştırıldı: yeni sorgu payload sahipliğini disconnect/fault boyunca korur.
Üst298B8 router'ın ortak tamponu yeniden giriş kilidiyle korunur;29962 wait
dalı kopyalamadan önce stok ret1'e gider. Bunlar iki asserted-byte **Unicorn
overlay** ve RAM vtable değişimidir; üretim PatchHunk veya .syx yaması değildir.

Stok port sonucu1=kabul/0=ret; router sonucu0=başarı/1=hata. Descriptor sadece
pointer/length taşır; port payload'ı ödünç alır, router ise ortak tampona
kopyalar. 26F36 çağıranı router sonucunu yok sayar;2CBF4 döndürür;46954 iletir.
Busy durumda stok senkron bekleme yerine bounded ret/retry gerekir. Kısmi
fanoutta ret1'e rağmen sağlıklı portlar alabilir; kör retry tekrar yaratabilir.
Bu sözleşme üretim için tamamlanmadan tam stok davranış eşdeğerliği iddia edilmez.

Kod1140B, RAM aynı832B; header boş alanları router pointer/busy için kullanıldı.
Sentetik20047000 adresi hâlâ üretimde boş RAM değildir. Checked heap, atomik
initialization ve tam boot/OOM kanıtı yok. Üretimin256B/2004F660 state'i aynı.

Değişen dosyalar:src/midi_recovery_prototype.py;
scripts/{midi_recovery_prototype_test_support,audit_midi_recovery_prototype,
probe_midi_recovery_prototype,trace_midi_sysex_contract}.py (sonuncusu yeni);
tests/test_midi_recovery_prototype.py; bu belge,CHANGELOG.md ve
docs/{MIDI-RECOVERY-PROTOTYPE-5706,UI-TRACE-5706,PHASE1-GO-GATES,ROADMAP,RECOVERY}.md,
tests/README.md. Bu turun kaynak/doküman farkı session.diff ve hash'ler
session-hashes.json olarak logs/recovery-sysex-20261027 altında saklanır.

Doğrulama; bütün Python komutları `.venv\Scripts\python.exe`, `-O` yok:

- `scripts/patch_firmware.py --build-phase1`: PASS; aynı21 patch/1376 bayt fark.
- `-m unittest discover -s tests -v`: **177 PASS**,24 deneysel (önceki13+11).
- `scripts/verify_phase1_candidate.py`:87 aday regresyonu/6 sınırlı kriter PASS;
  gerçek aday Off/Stop probe'ları FAIL; CRITICAL_RUNTIME_PROBE_FAILED,exit2.
- `scripts/run_baseline.py`: BASELINE PASS.
- `scripts/audit_phase1_safety.py logs/recovery-sysex-20261027/production-audit`:
  PASS; stok pin, app sınırları, vector/kimlik512B, CRC ve manifest korunuyor.
- `scripts/probe_midi_recovery_prototype.py logs/recovery-sysex-20261027/probe-final`:
  6 recovery vaka + paket üzerine izole overlay ile24 deneysel test PASS;
  tested_sysex_quarantine=PASS, all_producer_quarantine=REVIEW_REQUIRED,
  production_integrated=false ve NO-GO/exit2. Eski bypass kontrolü hâlâ true.
  Aynı komut CFG audit ve pin'li stok trace JSON/disassembly'sini de üretir.

Yeni kapsam: üç portta2/3/4/5/6/47/48/49/360B stok SysEx eşleşmesi; gerçek USB
ve iki DIN doluyken200B SysEx+64 Clock+Off+Stop; disconnect/payload ömrü;
nested send/poll/Off/On/Clock/router; ortak tampon kopyası/callback ve kısmi
fanout; length/capacity/PRIMASK/ABI/SP/canary/proje baytları. Yerel IRQ-mask
yollarında call/loop yok, max16 komut; max yerel frame40B. Native callee toplam
stack/cycle, gerçek IRQ/DMA/wire ve tam boot kanıtı değildir.

Başarısız varsayımlar/ilk denemeler: saf busy wrapper native40232 beklemesini
kilitler; ready=0 pointer sahipliğini bitirmez. İkisi negatif testlerle korundu.
İlk geniş testte nested trampoline aynı hook adresinden tekrar geçince callback
iki kez sayıldı. Kayıt hook'u stub'ın dönüş komutuna taşındı; başarı şartı veya
native kod zayıflatılmadı. tests-expanded-first.txt FAIL kaydı saklandı.

Loglar:logs/recovery-sysex-20261027/{build,all-tests-final,verify,baseline,audit,
probe-final}.txt; probe-final/{report,prototype-code-report}.json ve stock-contract/.
Üretim verifier raporu:logs/phase1-verification-20261026T233935Z/report.json (UTC).
Deneysel kod SHA256:c6079ec422adc92717309c6bf61ee30efdc51a7ca207d01a575415092e37ca1b.
Aday SHA256:3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368B. Stok SHA25611d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.

GO için kalanlar: bütün producer/lifecycle ve üretim SysEx/recovery entegrasyonu,
çağıran retry/kısmi fanout/yanıt politikası;832B checked RAM ve atomik boot init;
mode guard/reset-resume; IRQ/DMA/USB/disconnect kabul aralıkları. Ayrıca miras
stok storage hata-kurtarma, tam boot/OOM ve PRIMASK süre bütçesi açık.
**Sonraki tek somut iş:**298B8'in12 çağıranında ret/kısmi fanout/yanıt ömrünü
izleyip bounded retry sözleşmesini emülasyonda doğrulamak. Donanıma yüklenmemeli.

---

# Önceki kayıt — Off/Stop recovery prototipi çalışıyor; SysEx bypass açık / NO-GO

Bu bölüm günceldir. Yalnız dosyalar/Capstone/Unicorn; cihaz/MIDI/USB erişimi yok.
M7 tamamlanmadı. Üretim imajı değişmedi; mevcut.syx hâlâ Off/Stop kaybediyor.
Yeni izole Thumb prototipi aynı63/64 ve USB F8+FC karşı deneylerini iki modda
kayıpsız geçiriyor:1/2/5 poll. Gerçek USB staging/DIN byte ring ile64 On,
80 Clock,64 Off,son Stop baytları da eşleşiyor. Wire/IRQ ölçümü değildir.

src/midi_recovery_prototype.py:774 bayt kod, üç port için832 bayt sentetik
arena; channel/note Off bitmap, pending Stop, kısa atomik busy/fault işlemleri.
Fault sonrası modellenen üç-bayt API'sinde yeni On/Clock reddedilir; tekrar Off
birleşir ve ancak enqueue kabulünde bit silinir. Stop son sıraya konur, fault
kalır. Healthy byte/release-velocity korunur; recovery Off velocity0 kullanır.
Native kuyruk/poll/formatter çalışır. Script yalnız emülatör RAM vtable'larını
değiştirir; patch_firmware/seq_Patch entegrasyonu veya üretim flash hook'u yoktur.

13 deneysel test: iki mod/6 player-Stop vakası;2048 channel-note/tekrar/sınır;
stall/ready ve disconnect arası FIFO korunumu; native USB/DIN byte eşleşmesi;
PRIMASK1'de I/O yok; context-preserving nested Off/On/Clock; invalid pointer,
magic,count,cursor;8 Off denemesi/poll; SP/canary/raw ve yerel CFG audit.
Nested Stop sırasında gelen yeni Off için final Stop tekrar edebilir. Bu
model gerçek NVIC exception/IRQ öncelik kanıtı değildir.

Yeni karşı deney: native bulk SysEx40232/4028C, modellenen401FE üç-bayt
girişinden ayrıdır. Fault varken yeni SysEx kabul edilip gönderilebilir.
Test PASS'i karakterizasyondur; ayrı report all_producer_quarantine=FAIL ve
hardware_release=NO-GO tutar. Bu bypass kapanmadan üretime bağlanmaz.
20047000 test arena'sı stok heap current'in altındadır; üretimde boş sayılamaz.
832 bayt checked heap/boot/OOM rezervasyonu ve mode guard/reset-resume bağlantısı
yoktur. Native FIFO kabulü wire teslimi değildir; disconnect/IRQ/DMA açık.

Doğrulama (.venv/Scripts/python.exe; -O yok):

- --build-phase1 PASS:aynı21 patch/1376 değişen bayt.
- unittest discover -s tests -v:166 PASS; bunun13'ü izole deneysel test.
- verify_phase1_candidate.py:87 gerçek aday regresyonu/6 kriter PASS;
  mevcut aday Off/Stop negatif probe FAIL; CRITICAL_RUNTIME_PROBE_FAILED,exit2.
- run_baseline.py ve audit_phase1_safety.py logs/recovery-final-audit PASS.
- probe_midi_recovery_prototype.py logs/recovery-prototype:6 recovery vaka PASS;
  değişmemiş aday kontrolü FAIL; SysEx quarantine FAIL; deneysel rapor exit2.
- Deneysel CFG:SP delta0, BL8 hizalama, yerel max frame40B; forced PRIMASK
  alanlarında call/loop yok, max16 komut. CPU cycle/süre veya native stack bütçesi
  değildir. İlk audit BICS/branch sınıflandırması düzeltildi; ilk log korundu.

Loglar logs/recovery-final-{build,all-tests,verify,baseline,audit}.txt;
logs/recovery-prototype-{tests,probe,audit}.txt;
logs/recovery-prototype/{report,prototype-code-report}.json.
Güncel aday raporu logs/phase1-verification-20261026T221559Z/report.json (UTC).
Yeni dosyalar:src/midi_recovery_prototype.py,
scripts/{midi_recovery_prototype_test_support,audit_midi_recovery_prototype,
probe_midi_recovery_prototype}.py,tests/test_midi_recovery_prototype.py ve
docs/MIDI-RECOVERY-PROTOTYPE-5706.md; handoff/test/GO belgeleri güncellendi.
Üretim dosyası değişmedi:SysEx SHA256
3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368 bayt. Stok pin,vector/kimlik512 bayt ve app sınırları aynı.

GO için3 ana kapı:1) SysEx dahil bütün girişlerde recovery/karantina, gerçek
heap/boot/lifecycle/IRQ/USB ve hata-reset politikası;2) miras stok storage
hata/recovery;3) tam boot/OOM ve PRIMASK süre bütçesi. Sonraki tek görev:
40232/4028C caller dönüş/bekleme/payload ömrünü çıkarıp SysEx bypass'ını bounded
bir prototiple kapatmak. Sonra native USB/DIN stall ve mevcut aday kontrolünü
yeniden sınamak. Ayrıntı:MIDI-RECOVERY-PROTOTYPE-5706.md. Donanıma yüklenmemeli.

---

# 27 Ekim 2026 — Gerçek player Stop patlamasında Off/Stop kaybı / NO-GO

Bu bölüm günceldir; M7 tamamlanmadı. Cihaz/MIDI/USB erişimi yapılmadı.
Pattern oynatıcıdan MIDI çıkışına gerçek kod zinciri eklendi. Yeni kritik
karşı deney: 64 açık player notası -> native Stop içinde 64 Off -> FC kaybı.
Aynı USB buffer'daki tek F8+FC ile 63 Off/0 FC teslim edilir: bir nota da
asılı kalabilir. Her iki modda üç hazır driver'da aynı sonuç vardır.
63-nota kontrolünde 63 Off+1 FC geçer; fault oluşmaz. Mevcut overflow fault
mod geçişini kapatır ama mesajı kurtarmaz. USB yield bu buffer içi patlamayı
çözmez. Firmware bu tur değiştirilmedi; yeni koruma uygulanmış sayılmamalı.

D+E: 3C29E factory ->4ADA4 player, 4AEEE/4AFBC gerçek step hazırlama/çalma,
4B0D4/4B170 gate kuyruğu ve Off; voice/filter/router üzerinden sample ve
MIDI ayrılır. 33EAE ->FBEC ->55120/552F6 ->4AED8 sekiz player'ı senkron
boşaltır; sonra32024 FC üretir. Stock8 gate kaydı/player tüm UI/preview/tie
kaynakları için64-nota üst sınırı değildir. Kurucu RAM'i ve tick sırası
sentetiktir; tam player/root constructor, boot/IRQ ve canlı erişilebilirlik
kanıtı değildir. Son sample engine/final driver ve Stop backend sınırları
stub'dır. Yerel upstream ipuçları pin'li binary ile bağımsız doğrulandı.

Yeni9 test: iki mod,8 track, pattern0/7, step0/16/31, gerçek gate expiry;
son track/pattern'de32 step; MIDI-only sample mute +MIDI korunumu; aynı pitch
Off/On; dokuzuncu pitch oldest steal; tie retrigger/flush;63/64 notalı Stop
ve USB F8+FC kaybı. Native ABI/SP, player canary ve Stop boyunca169092 bayt
proje korunur. İlk fixture class2 map null okuması ve store/stack çakışması
düzeltildi; firmware hatası değildir. Son çapraz kontrolde ST1 cache'inden
yanlış taşınan+128 pattern ofseti de çıkarıldı:33124 native span ctor'u artık
doğrudan kullanılır. İlk/son raw step tuple'ı ayrıca denetlenir. Eski loglar
seq-playback-pre-span-correction-* altında korundu; bütün testler tekrarlandı.

Komutlar .venv/Scripts/python.exe ile, -O olmadan:
- patch_firmware.py --build-phase1 PASS;21 patch/1376 değişen bayt, aynı aday.
- unittest discover -s tests -v:153 PASS; yeni9 test dahil.
- verify_phase1_candidate.py:87 packaged regresyon/6 sınırlı kriter PASS;
  ayrı native sequencer Off/Stop probe FAIL; exit2, CRITICAL_RUNTIME_PROBE_FAILED.
- run_baseline.py ve audit_phase1_safety.py logs/seq-playback-final-audit PASS.
- probe_sequencer_stop.py beklenen exit1; iki modda63/64/F8+FC altı vaka.
Loglar logs/seq-playback-final-{build,all-tests,verify,baseline,audit}.txt;
logs/seq-stop-probe.json. Güncel paket raporu:
logs/phase1-verification-20261026T215338Z/report.json (UTC).

Değişenler: yeni scripts/sequencer_playback_test_support.py,
tests/test_sequencer_playback.py, scripts/probe_sequencer_stop.py;
verify_phase1_candidate.py yeni testleri paketlenmiş gerçek imajda çalıştırır
ve ayrı negatif probe'u kararına katar. SEQUENCER-PLAYBACK-5706.md,
STATUS/UI-TRACE/ROADMAP/GO-GATES/HARDWARE-TEST/RECOVERY ve testREADME güncellendi.
Üretim ARM kodu değişmedi. SysEx SHA256:
3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368 bayt. Stock pin/512 bayt vector-kimlik/app sınırları aynı.

GO için3 kapı sürer:1) Off/Stop recovery ve tam runtime/timer/IRQ/USB service
kanıtı;2) miras stock storage kısa-okuma/hata/recovery;3) tam boot/OOM ve
PRIMASK süre bütçesi. Sonraki tek görev: channel/note anahtarlı, port başına
deferred Off bitmap +pending Stop prototipini native FIFO/driver emülasyonuna
bağlayıp yeni karşı deneyleri kayıpsız geçirmek. Yalnız bitmap üç portta768
bayt ister; mevcut256-bayt state'e sığmaz. Ek heap, sıralama, yeni On kabulü,
disconnect ve kritik bölüm politikası kanıtlanmadan üretim hook'u eklenmez.
Tasarım ve kapsam sınırı: docs/SEQUENCER-PLAYBACK-5706.md. Donanıma yüklenmemeli.

---

# 27 Ekim 2026 — TX taşmasından sonra mod geçişi kilitlenir / NO-GO

Bu bölüm önceki kayıtların önündedir. M7 tamamlanmadı; cihaz/MIDI/USB erişimi yok.
Önceki aday, Off kaybı ve kuyruk drain sonrasında iki modda da geçişe izin
veriyordu: logs/tx-fault-before.txt. Yeni40228 BLEQ observer, gerçek FIFO enqueue
loss dalında state+7A sticky fault set eder; c_midi_inputs_idle geçişi kapatır.
Kuyruk boşalması/başarılı Off baytı temizlemez. Disabled USB ready0 ve başarılı
enqueue latch oluşturmaz. Kaybolan mesajın kendisi kurtarılmış değildir.

Wrapper32 bayt frame; r0-r5/r12/lr ve APSR_NZCVQG korunur. c_seq_state geçerlilik
kontrolü/özgün PRIMASK korunur; yalnız geçerli256 bayt state içinde+7A yazılır.
Sonra özgün23690 no-op'una bir kez tail-call. IT bloğunun son BL slotu, byte
assert/Capstone ile denetlenir. Yeni heap rezervasyonu veya file API yok.

Gerçek USB2B408 staging/endpoint availability, DIN2B564 running-status ve UART
26014 byte ring yazımı da çalıştırıldı.2C9B8 USB hardware submit/2AC58 IRQ-enable
sınırları stub; completion native268D0'a enjekte edilir, IRQ/DMA dispatch veya
wire zamanlaması değildir. Native full'da Off kaybı ve ardından mode kilidi
testlidir. Native configured0 USB401CA FIFO temizliği bu fault'un kapsamı dışıdır.

Düzeltilen varsayımlar:27624 genel event pump değil USB endpoint hizmetidir.
İlk native modelde endpoint+1D capacity1 eksikti; gerçek kurucuya göre düzeltildi
(native-driver-tests-first.txt). Firmware hatası sayılmadı. İlk test sınıfı
import'u8 tekrar keşfe yol açıyordu; module alias ile kaldırıldı. Eski kanıtlar
silinmedi. Ayrıntı docs/MIDI-TX-FAULT-5706.md.

Doğrulama (.venv/Scripts/python.exe; -O yok):
- patch_firmware.py --build-phase1 PASS;21 patch/1376 değişen bayt.
- unittest discover -s tests -v:144 PASS; yeni4 fault ve4 native driver testi.
- verify_phase1_candidate.py:78 packaged regresyon ve6 sınırlı kriter PASS;
  Off probe FAIL ama mode admission BLOCKED/fault1; Stop ready PASS/stalled FAIL;
  CRITICAL_RUNTIME_PROBE_FAILED / NO-GO, exit2.
- run_baseline.py ve audit_phase1_safety.py logs/tx-guard-final-audit PASS.
- probe_midi_output_queue.py ve probe_midi_task.py beklenen negatif exit1;
  logs/tx-guard-{queue,task}-probe.json.
Loglar logs/tx-guard-final-{build,all-tests,verify,baseline,audit}.txt.
Paket raporu logs/phase1-verification-20261026T211547Z/report.json (UTC).

Değişenler: src/seq_Patch.py; audit/verify/probe_midi_{output_queue,task}.py;
yeni native_midi_driver_test_support.py, test_midi_tx_fault.py,
test_native_midi_drivers.py; test_midi_output_transport.py observer'ı hesaba
katarak diğer tüm çıktı baytlarını denetlemeyi sürdürür; belgeler/scope metni.
SysEx SHA2563c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
Image SHA25638d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,371368 bayt; stok pin/512 bayt vector-kimlik ve app sınırları aynı.

GO için3 ana kapı:1) kayıp Off/Stop recovery, gerçek sequencer sahipliği,
callback/IRQ/DMA/USB-service ömrü ve gecikme;2) stok storage hata/recovery;
3) tam boot/OOM ve PRIMASK zaman bütçesi. Sonraki tek görev: gerçek sequencer
Note On/Off üreticilerinin maksimum eşzamanlı nota/callback sırasını çıkarıp
bu sınıra dayalı deferred delivery/recovery tasarlamak. Donanıma yüklenmemeli.

---

# 26 Ekim 2026 — USB burst kaynaklı Stop kaybı düzeltildi / NO-GO

Bu bölüm önceki kayıtların önündedir. M7 tamamlanmadı; cihaz/MIDI/USB erişimi yok.
25870..2587C gerçek main sırası output poll ->USB/DIN'dir. DIN turda port başına
1 bayt tüketir; stok USB aynı turda bütün RX FIFO'yu tüketir. Boot USB RX16*64
paket kapasitesi,64 Clock + Stop'un aynı input turuna sığdığını gösterir.
Yalnız yeni hook stok4 baytına döndürülen kontrolde üç portta Stop kaybı üretildi.

Yeni29B62 B.W ->c_usb_rx_yield, bir portta alınmış1 buffer tamamlanınca stok
sonraki-port yoluna gider. Kalan buffer'lar FIFO'da kalır. Böylece sonraki
buffer'dan önce ana döngü output worker ve diğer görevlere döner. Cave12 bayt;
BL/push/pop/store/heap/literal/PRIMASK işlemi yok. LT yolunda özgün LDR replay;
GE yolunda yalnız loop continuation değişir. LR/SP/APSR ve register ABI testli.
İki modda etkilidir; fiziksel gecikme ve rearm/IRQ akışı henüz kanıtlanmadı.

Hazır sürücü modelinde64 Clock + Stop ve tam RX16 buffer'ında255 Clock + Stop
kayıpsızdır; ölçülen64-Clock deneyinde TX tepe doluluğu64->16 olur. Stalled
driver modelinde Stop, dolu stok FIFO'da Off kaybı hâlâ vardır. Bu yüzden genel
güvenlik kabulü veya GO yoktur. Ayrıntı docs/MIDI-USB-YIELD-5706.md.

Doğrulama (.venv/Scripts/python.exe; -O yok):
- patch_firmware.py --build-phase1 PASS;20 patch/1335 değişen bayt.
- unittest discover -s tests -v:136 PASS; yeni8 task/parser/ABI testi.
- verify_phase1_candidate.py:70 packaged regresyon ve6 sınırlı kriter PASS;
  task ready-driver PASS, stalled-driver FAIL; ayrı FIFO Off probe'u FAIL;
  CRITICAL_RUNTIME_PROBE_FAILED / NO-GO, exit2.
- probe_midi_task.py ve probe_midi_output_queue.py: negatif kapsamları nedeniyle
  exit1; logs/usb-yield-{task,queue}-probe.json.
- run_baseline.py ve audit_phase1_safety.py logs/usb-yield-final-audit PASS.
Loglar logs/usb-yield-final-{build,all-tests,verify,baseline,audit}.txt.
Paket raporu logs/phase1-verification-20261026T205106Z/report.json.

Yeni testlerin ilk iki beklentisi eski tek-tur drain davranışı içindi; stok
kontrolü saklanıp adayın çok-turlu Stop teslimi test edildi. Ara loglar
task-schedule-before.txt ve task-yield-first.txt içinde. Önceki raw queue
karşı deneyi kaldırılmadı veya güvenlik PASS'i olarak yorumlanmadı.
SysEx fragment/parser state ve sonraki On/Off da korunur; consumer stub'dır.

Değişenler: src/seq_Patch.py; scripts/audit_phase1_safety.py,
scripts/verify_phase1_candidate.py; yeni scripts/midi_task_test_support.py,
scripts/probe_midi_task.py, tests/test_midi_task_schedule.py ve belgeler.
SysEx SHA2560fa75262c3cf580fa1e9d4f88431d013dddb2fffc8edb1baeb0caa5c28c2d6b9;
Image SHA256c15efacf589b1ea381fa5f96e7236cca0119c1e1587d93ff81482f69d5c3940f;
CRC93CA2E51,371332 bayt; stok pin ve512 bayt vector/kimlik aynı. Yeni RAM yok.

GO için3 ana kapı:1) driver backpressure/Off-Stop recovery, gerçek sequencer
sahipliği, event pump/ISR/DMA/receiver ömrü ve ek giriş gecikmesi;2) stok storage
hata/recovery;3) tam boot/OOM ve PRIMASK zaman bütçesi.
Sonraki tek görev: gerçek port driver ready/full/flush ve27624 event pump
sırasını bağlayıp stall sınırını veya güvenli Off/Stop recovery'yi doğrulamak.
Donanıma yüklenmemeli.

---

# 26 Ekim 2026 — Native MIDI çıkışı; dolu kuyrukta Off kaybı / NO-GO

Bu bölüm önceki kayıtların önündedir. M7 tamamlanmadı; cihaz/MIDI/USB erişimi yok.
Gerçek31F08 MIDI çıkış adaptörü,4016C/40D9C port/FIFO kurucuları ve297DE ->402B4
worker poll çalıştırıldı.3223C/3328C clock backend ve native store/listener
kurucuları eklendi. İlk Clock'un özel dalı, Start/Stop state ve MIDI çıkışı
gerçektir. Final driver ready/full/accept/flush, timer/tempo/GPIO sınırları stub;
clock present flags fixture girdisidir. Tam boot, ISR/DMA ve sequencer nota
üreticisi kanıtı değildir. Ayrıntı docs/MIDI-OUTPUT-TRANSPORT-5706.md.

Yeni somut risk: boot297A8'deki gerçek64 slot kapasitesinde, consumer poll'dan
önce64 Clock biriktirince Note Off kaybolur. Önce teslim edilmiş On48'e karşı
üç portun her birinde On1/Clock64/Off0; son worker poll sonrası kuyruk0.
Başarısız enqueue header/buffer'ı taşırmaz. İlgili dört kod aralığı stokla
aynıdır; miras kuyruk davranışıdır.23690 fatal assert değil, stok no-op'tur.
Bu kontrollü sıralamanın canlı scheduler'da erişilebilirliği henüz kanıtlanmadı.
Kuyruk büyütülmedi veya kör teslim politikası eklenmedi; risk onarılmış değildir.

Doğrulama (.venv/Scripts/python.exe; -O yok):
- patch_firmware.py --build-phase1 PASS; source firmware/hash değişmedi.
- unittest discover -s tests -v:128 PASS; yeni8 test mevcut stok davranışını da
  karakterize eder, Off teslim güvenliği kabulü değildir.
- verify_phase1_candidate.py:62 packaged regresyon ve6 sınırlı kriter PASS;
  negatif runtime probe FAIL, CRITICAL_RUNTIME_PROBE_FAILED / NO-GO, exit2.
- probe_midi_output_queue.py: paketlenmiş imajda FAIL, beklenen exit1;
  logs/output-queue-probe.json.
- run_baseline.py ve audit_phase1_safety.py logs/output-final-audit PASS.
Loglar logs/output-final-{build,all-tests,verify,baseline,audit}.txt.
Paket raporu logs/phase1-verification-20261026T194124Z/report.json.

İlk fixture null read: listener'sız model store'u native constructor'a uygun
değildi; gerçek3FB50 kullanıldı. İkinci null read eksik GPIO sınırındaydı.
Firmware kusuru sayılmadı. İlk diagnostic-trap varsayımı da23690 disassembly'si
ile düzeltildi; son deney gerçek no-op'tan normal döner. Ara output-native logları
korundu. Production src/ ve stok dosya bu tur değiştirilmedi.

Değişenler: yeni scripts/midi_output_test_support.py,
scripts/probe_midi_output_queue.py, tests/test_midi_output_transport.py;
scripts/verify_phase1_candidate.py ve kanıt/durum/GO/recovery/changelog belgeleri.
SysEx SHA256058feb2ef8921168b9113edc5a3704184cc4a634c2c9838ba3533cbeeab7cdce;
Image SHA256e88848b93f85e4f7d9feea10bafbac20e8ec6b330c17840fc2dfcc7df15ee048;
CRC7F9DE544,371320 bayt,19 patch,1319 değişen bayt; vector/kimlik512 bayt aynı.

GO için3 ana kapı:1) kuyruk Off kaybı, gerçek scheduler/ISR/DMA, sequencer nota
sahipliği ve receiver ömrü;2) stok storage hata/recovery;3) tam boot/OOM ve
PRIMASK zaman bütçesi. Sonraki tek görev:297DE worker poll'unun gerçek task
sırasını ve driver ready/full ömrünü bağlayıp64 doluluğun erişilemezliğini veya
güvenli Off recovery politikasını kanıtlamak. Donanıma yüklenmemeli.

---

# 26 Ekim 2026 — MIDI parser ve gerçek transport store zinciri / NO-GO

Bu bölüm önceki kayıtların önündedir. M7 tamamlanmadı; cihaz/MIDI/USB erişimi yok.
Yeni7 testle DIN byte parser'ı ve USB yazılım paket FIFO'su gerçek decoder,
receiver/ownership ve Start/Continue/Stop handler'larına bağlandı. Running store
testte elle değiştirilmez; stok handler yazar. Start gerçek340AA/342E0 ile
sekiz track konumunu sıfırlar. Clock32BB6 normal dalı pending counter ve sanal
çağrısına kadar yürür. Running status, araya giren Clock/Stop, iki mod ve128
notada FIFO sarılması geçer. Held nota varken Stop sonrası da geçiş reddedilir;
eşleşen son Off guard'ı açar. Parser4042C kurucusu/allocator da gerçektir.

Sınır: RAM nesneleri sentetik; USB driver armed/receive ring'i hazırlanır.
UART/USB ISR/DMA, özel timer dalı, dolu listener listeleri ve gerçek downstream
sequencer/source-driver/Clock alıcıları çalıştırılmadı. Son alıcılar emülasyon
stub'larıdır. Tüm boot ve output queue kanıtı değildir.

Doğrulama (.venv/Scripts/python.exe; -O yok):
- patch_firmware.py --build-phase1 PASS; makine kodu/hash önceki adayla aynı.
- unittest discover -s tests -v:120 PASS.
- verify_phase1_candidate.py:54 packaged regresyon ve6 kriter PASS;
  HOST_CHECKS_PASS / NO-GO, beklenen exit2;3 yayın engeli sürüyor.
- run_baseline.py ve audit_phase1_safety.py logs/ingress-final-audit PASS.
Loglar logs/ingress-final-{build,all-tests,verify,baseline,audit}.txt.
Paket raporu logs/phase1-verification-20261026T190215Z/report.json.
Ayrıntılı adres/boot bağları: docs/MIDI-INGRESS-TRANSPORT-5706.md.
İlk fixture'da ters start/end byte beklentisi ve yanlış metoda kayan assertion
NameError düzeltildi; üretim firmware kusuru sayılmadı. İlk başarısız test logu
logs/ingress-transport-tests-first.txt içinde korunur.

Değişenler: scripts/midi_record_test_support.py (router relocation), yeni
scripts/midi_ingress_test_support.py ve tests/test_midi_ingress_transport.py,
scripts/verify_phase1_candidate.py ve güncel kanıt/durum/changelog belgeleri.
Production src/ ve stok baytları bu tur değişmedi.
SysEx SHA256058feb2ef8921168b9113edc5a3704184cc4a634c2c9838ba3533cbeeab7cdce;
Image SHA256e88848b93f85e4f7d9feea10bafbac20e8ec6b330c17840fc2dfcc7df15ee048;
CRC7F9DE544,371320 bayt,19 patch,1319 değişen bayt; vector/kimlik512 bayt aynı.

GO için kalan3 kapı:1) gerçek ISR/DMA, downstream transport/Clock/output queue,
scheduler yarışları ve receiver lifetime/sayısı;2) miras stok storage
kısa-okuma/hata/recovery;3) tam boot/OOM ve PRIMASK zaman bütçesi.
Sonraki tek görev:32BB6 Clock alıcısı ve33EAE Stop backend'ini gerçek
sequencer/output graph'ına bağlayıp çalıştırmak. Donanıma yüklenmemeli.

---

# 26 Ekim 2026 — Harici MIDI sahipliği guard'ı güçlendirildi / NO-GO

Bu bölüm önceki kayıtların önündedir. M7 tamamlanmadı; cihaz/MIDI/USB erişimi yok.

Gerçek MIDI decoder/receiver/recorder graph'ı, ortak-proje controller fixture'ıyla
çakışmayan RAM'de birleştirildi. Önceki aday receiver+74 maskesi doluyken32 alt-
vakada mode değişimine izin veriyordu (logs/midi-mode-before.txt). Bu sentetik
RAM karşı örneğidir; fiziksel cihaz veya tam boot bağlantısı kanıtı değildir.

Yeni3F5A8 observer, receiver pointer'larını state+68'de4 slotta izler; nested
active-call byte+79 ve sticky context fault+78 ile henüz maskesi yazılmamış
Note On penceresini kapatır. Mode guard her receiver'da160 bayt maskeyi okur.
Stok callback ve Note Off değiştirilmeden yürür; r0-r3 stok çıktı değerleri,
r4-r11, SP ve gerekli prologue MOVS bayrak davranışı korunur. Bookkeeping IRQ
maskesini geri getirerek callback'i bir kez çağırır. Stok/all-notes-off drain ve
iki kaynak Note Off testleri geçer. Geçiş projeyi yüklemez veya değiştirmez.

Beşinci farklı receiver/invalid context/counter saturation mode geçişini
fail-closed kapatır; nota teslimatı sürer. Cache lifetime ve maksimum receiver
sayısı tam bootta henüz kanıtlanmadı. Stop/Clock testi gerçek decoder ve
receiver thunk'larından SON transport stub'ına kadardır; task/ISR/çıkış kuyruğu
kanıtı değildir. Stop, halen basılı notayı bu sınır modelinde kendiliğinden
silmiyor; Off/drain gelene kadar guard kapalıdır.

Doğrulama (.venv/Scripts/python.exe; -O yok):
- patch_firmware.py --build-phase1 PASS.
- unittest discover -s tests -v:113 PASS.
- verify_phase1_candidate.py:47 packaged regresyon ve6 kriter PASS;
  HOST_CHECKS_PASS / NO-GO;3 yayın engeli sürüyor.
- run_baseline.py PASS.
- audit_phase1_safety.py logs/midi-owner-audit PASS; bağımsız SysEx/CRC,
  stok pin/vector/diff ve Capstone/yerel CFG stack hedef analizi.
Loglar logs/midi-owner-{build,guards,all-tests,verify,baseline,audit}.txt.
Paket raporu logs/phase1-verification-20261026T182645Z/report.json.
probe_shared_project.py de güncel source ile raw169092 bayt/metadata/P
korunumu veI/O0 gösterir: logs/midi-owner-project-probe.json.

Ara bulgular: realtime fixture'daki temel vtable yanlışlığı son derived
66654/66670 ile düzeltildi; firmware kusuru sayılmadı. İlk observer cleanup
r1-r3'ü AAPCS'nin izin verdiği şekilde değiştiriyordu; daha korumacı stok çıktı
eşitliği için wrapper düzeltildi.4 farkı saklayan log midi-observer-abi-before.txt.
Detay ve sınırlamalar docs/MIDI-MODE-OWNERSHIP-5706.md içinde.

Aday SysEx SHA256 058feb2ef8921168b9113edc5a3704184cc4a634c2c9838ba3533cbeeab7cdce
Image SHA256 e88848b93f85e4f7d9feea10bafbac20e8ec6b330c17840fc2dfcc7df15ee048
CRC0x7f9de544; imaj371320 bayt;
19 patch,1319 değişen bayt. Stok pin/ilk512 bayt vector ve kimlik korunur.
Yeni RAM rezervasyonu yok; mevcut256 bayt alan kullanılır.

Değişenler src/seq_Patch.py, tests/test_midi_mode_ownership.py,
scripts/audit_phase1_safety.py, scripts/verify_phase1_candidate.py,
STATUS/UI-TRACE/GO/recovery/changelog ve yeni MIDI kanıt belgesi; yerel build/loglar.

Kalan3 GO kapısı: dış UART/USB/transport/scheduler/receiver lifetime/output queue;
miras stok storage hata/recovery; tam boot/OOM ve PRIMASK zaman bütçesi.
Sonraki tek görev:5AF94'e giden UART/USB byte/packet parser yollarını ve receiver
nesnesinin boot sahibini bağlayıp gerçek Stop transport callback'ini stub
sınırının ötesinde çalıştırmak. Bu kanıtlar olmadan donanıma yüklenmemeli.

---

# 26 Ekim 2026 — Ortak proje ve test geçişi tamamlandı / NO-GO

Bu bölüm önceki onay-bekliyor/başarısız test kayıtlarının önündedir.
Kullanıcı eski kapsam testlerinin arşivlenip yeni beklentilerle değiştirilmesine
açıkça onay verdi. Ortak proje modeli bu tur tam regresyonla doğrulandı.
M7 donanım çıkışı tamamlanmadı; cihaz/MIDI/USB erişimi yok.

Yeni davranış: aynı açık projede Shift + Sample Rec ile Normal/MIDI-only geçişi;
mod değişiminde hiçbir Load/New/Save/file API çağrısı yok. Stok64 slot, sayfa
tuşları, Packs ve proje işlemleri korunur. Dirty edit engel değildir. Transport
durmuş, proje I/O idle, controller nota ve grid held sahiplikleri boş olmalı.
Aday18 patch ve1027 değişen bayt; önceki40 patch/2650 bayttan sadeleşti.

Test migrasyonu: eski kaynak/verifier ve üç test dosyası
analysis/historical-bank-isolation/ altında eksiksiz saklandı. Hash eşleşmeleri
önceden doğrulandı. Onay ve39 arşivlenen metot approved-test-migration.json
içinde;4 eski Safety,32 Reaudit ve3 Projects sözleşmesi arşivlendi. Bunlar
banka/otomatik-Load/dirty-tracker/containment beklentileriydi. Test skip yok.
Mevcut grid, ABI, allocator, overflow, MIDI ownership/decoder/recording,
seçili/seçili olmayan pattern canary ve parametre yazma testleri korunur.
Private dirty-tracker yan etkileri artık beklenmez; pattern verisi kontrolleri
korundu. Parametre editinden sonra mod değişiminde tüm pattern korunumu eklendi.

Sonuçlar (.venv/Scripts/python.exe; -O yok):
- scripts/patch_firmware.py --build-phase1: PASS.
- -m unittest discover -s tests -v:101 test PASS,0 failure/error.
- scripts/verify_phase1_candidate.py:6 güncel sınırlı ölçüt ve35 packaged
  güvenlik regresyonu PASS; HOST_CHECKS_PASS, hardware_release NO-GO,3 engel.
- scripts/run_baseline.py: BASELINE PASS.
- scripts/audit_phase1_safety.py logs/shared-final-audit: PASS; bağımsız
  SysExdecode/MPEG2CRC, stok pin, vector, changed-range/diff, Capstone ve
  yerel CFG stack/hedef denetimi.
Loglar logs/shared-migrated-tests.txt; logs/shared-final-{build,verify,
baseline,audit}.txt. Verifier raporu:
logs/phase1-verification-20261026T171154Z/report.json.

Ek kanıt: scripts/probe_shared_project.py PASS; raw169092 bayt, metadata ve
Project Controller aynı; mode dizisi1,0; proje I/O çağrısı0; nota60 korunur.
logs/shared-final-project-probe.json. Eski probe_project_alias.py değiştirilmedi;
arşiviyle SHA25624b40a63e7a2827d3aed391c7fda1e080f4fdab770d6f2c17d0eea53c8b3f7af
aynıdır. scripts/run_historical_alias_probe.py, eski kaynak ve probe ile
korumasız karşı deneyi yeniden üretti: nota60->34, apply0; exit1 kasıtlıdır.
logs/shared-historical-alias-probe.json. Bu tarihsel adayı RAM'de kurar, güncel
build dosyasını değiştirmez. Stok I/O hata davranışı onarılmış sayılmaz.

Başarısız ara deneme: eski probe'u güncel mod deneyine dönüştürme işlemi
otomatik inceleme tarafından kanıt kaybı riskiyle reddedildi. Güvenli çözüm
ayrı probe_shared_project.py ve ayrı tarihsel replay runner oldu; eski kanıt
kaybolmadı. Test migrasyonu onay engeli kullanıcı yanıtıyla kapandı.

Aday SysEx SHA256 c765196362e191eec857ce29bf79f01c67aeb43fa7da0dd462874a2c7964449b
Image SHA256 3c57eda77fada91c5165a038b557886df2342c6e2e7e63a14fd051e6c982ea2d
CRC0x86b2d210;imaj371028 bayt.
Stok SHA25611d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf
ve ilk512 bayt vector/kimlik aynı; bootloader/option-byte müdahalesi yok.

Bu tur değişenler: tests/test_phase1_safety.py,test_reaudit_abi.py,
test_projects_and_mode.py,tests/README.md,verify_phase1_candidate.py,
probe_shared_project.py,run_historical_alias_probe.py, arşiv hash/onay kayıtları,
durum/GO/recovery/changelog belgeleri. Firmware makine kodu bu tur değişmedi.

Kalan3 GO kapısı:1) dış UART/USB/MIDI/Stop/Clock, tüm sahiplik filtreleri ve
scheduler yarışları;2) miras stok storage kısa-okuma/callback/recovery riski;
3) tam boot/OOM çağıranları ve PRIMASK zaman bütçesi.
Sonraki tek görev: controller nota store'larının yanında MIDI router ownership
filtrelerini izleyerek dış Note On sürerken mod geçişinin güvenle reddedildiğini,
Note Off/Stop sonrasında açıldığını gerçek çağrı zinciriyle kanıtlamak.
Bu tur kalan fazlara geçilmedi; ortak-proje değişikliği tamamlandı.

---

# 26 Ekim 2026 — Ortak proje uygulandı; test migrasyonu onay bekliyor / NO-GO

Kullanıcı ayrı bankalardan vazgeçti; AGENTS.md ve SCOPE.md güncellendi.
M7 tamamlanmadı. Cihaz/MIDI/USB erişimi yok; Python optimizasyonsuz.

Üretim kodu: Shift + Sample Rec mevcut proje üzerinde yalnız seq_enabled
değiştirir. Otomatik Load/New ve callback/state-machine akışı kaldırıldı.
Banka/sayfa kilitleri, Packs engeli, Save/Load callback yamaları,
dirty/recording hook'ları ve geçici Load engeli adayda artık yoktur.
Proje/storage/recorder/knob kodu incelenen tam aralıklarda stokla bit-bit aynı.
Bu, stok storage hatalarını onarmaz; kısmi okumanın canlı pattern alias riski
miras kalır. Mode toggle o yola hiç girmez.

Kabul: ctrl+18 transport store byte0=0; Projects ready bit3 ve busy0..1;
phase word1 byte0=0; ctrl+1C0..1DC nota sahiplik word0'ları0; grid+228,
sekiz Step View+B8/C0 maskeleri ve32 durumdaki held bit3 boş.
Eksik bağlam reddedilir. Unsaved edit engel değildir. Kontrol+mode commit
PRIMASK altında; zaten maskeli gelen çağrı reddedilir. Sample force-off
çağrıları maskeyi geri getirdikten sonra yürür. Tam dış MIDI kanıtı yok.

Yeni test_shared_project.py: gerçek button ownership/dispatch ve recorder
kurucuları; tüm169092 bayt raw proje+metadata/P korunumu; hiçbir Load/Save/file
API çağrısı olmaması; tekrarlı basış, busy/stopped/held retleri; iki modda64
slot ve4 proje işlemine yönlendirme; stok byte korunumu; PRIMASK/voice sırası.
9 test PASS; completion injection yok. Diğer güncel hedefli testler de PASS:
{"step":"Ran 15 tests in 1.588s\r","led":"Ran 9 tests in 0.438s\r","state":"Ran 8 tests in 0.246s\r","ui":"Ran 7 tests in 0.272s\r","contract":"Ran 9 tests in 0.511s\r"}

Build, bağımsız SysEx/CRC/vector/diff/Capstone/CFG stack audit ve baseline PASS.
Loglar logs/shared-{build,contract-tests,step-tests,led-tests,state-tests,
ui-tests,audit,baseline,verify}.txt; audit logs/shared-audit/.

TAM REGRESYON PASS DEĞİLDİR: eski banka/dirty/Load-containment sözleşmeleri
değiştirilmedi.140 testte99 failure ve44 error (alt-vakalar dahil);
logs/shared-all-tests-before-migration.txt. Verifier6 güncel sınırlı ölçütü
geçer; eski başarısızlıkları gizlemeden NO-GO raporlar:
logs/phase1-verification-20261026T164033Z/report.json.

Test değişikliği otomatik onay incelemesince reddedildi. Üç eski test dosyası,
önceki kaynak/verifier analysis/historical-bank-isolation altında tam kopyalı;
SHA256 eşleşmeleri doğrulandı. Eski testleri kaldırmak için açık kullanıcı
onayı istendi; async soru bekliyor. Eski test dosyaları korunuyor; skip yok.
Yeni testler eklendi. Bu bir test-kapsamı onay engelidir; firmware GO değildir.

SysEx SHA256 c765196362e191eec857ce29bf79f01c67aeb43fa7da0dd462874a2c7964449b
Image SHA256 3c57eda77fada91c5165a038b557886df2342c6e2e7e63a14fd051e6c982ea2d
CRC0x86b2d210;18 patch,1027 değişen bayt.
Stok pin ve512 bayt vector/kimlik korunur.
Değişenler: AGENTS.md,SCOPE.md,src/seq_Patch.py,shared_project_test_support.py,
test_shared_project.py,verify_phase1_candidate.py, belgeler, yerel build ve
eski kaynak/test arşivi. Yerel refaktör yardımcıları scratch/ altında.

Sonraki tek görev: kullanıcı onayıyla eski banka/otomatik-Load/dirty test
sözleşmelerini ortak-proje beklentilerine uyarlamak; grid/ABI/heap ve MIDI
veri-canary testlerini koruyup tam suite/verifier çalıştırmak.
Sonraki GO kapıları: UART/USB/MIDI/Stop/Clock ve tüm sahiplik filtreleri,
stok storage hata/recovery sınırı, tam boot/OOM ve PRIMASK zaman bütçesi.

---

# 26 Ekim 2026 — Load öncesi koruma / NO-GO

SON KARAR: TEHLİKELİ / YÜKLENEMEZ - NO-GO. Bu bölüm önceki kayıtların önündedir.
İşlevi koruyan tam çözüm bulunmadı. 0x08037BD6 Load/New continuation girişi
okuma, busy-bit değişimi ve boş proje oluşturma öncesinde reddedilir. Aynı P
sahibinin geçişi iptal edilir; stok37DD0 phase temizliği yürür. Mode, dirty,
taint, Save owner ve mevcut proje baytları korunur. Bu yol üzerinden Load/New
ve mod geçişi çalışmaz. Boot yükleme davranışı da kabul edilmedi.

Kanıt: gerçek span/sekiz recorder kurucusu + gerçek kuyruk fixture'ında tüm
169092 bayt raw alanı aynı, nota60 ->60, file-read0, apply0, transition0,
taint0. Dört hook baytını yalnız Unicorn RAM'inde stok haline getiren karşı
deney read1 ve nota60 ->34 bozulmasını yeniden üretir. Bu, fiziksel medya
ve tam scheduler kanıtı değildir.

131 regresyon PASS. Eski read/Close bileşen testleri açıkça
bypass_containment=True kullanır; üretimde Load kabul kanıtı değillerdir.
Yeni testler tüm proje korunumu, karşı deney, mode0/1, geçerli/geçersiz heap,
aynı/yabancı sahip için state ve phase temizliğini kapsar. Harness SP ve
r4-r11'i kontrol eder. Ek cave32 bayt; yeni RAM tamponu/Flash yazımı yok.

Komutlar (.venv/Scripts/python.exe, optimizasyonsuz):
- scripts/patch_firmware.py --build-phase1: PASS.
- -m unittest discover -s tests -v: 131 PASS.
- scripts/verify_phase1_candidate.py: NO-GO; 62 packaged regresyon ve6 sınırlı
  bileşen ölçütü geçer. Yeni rapor durumu CONTAINED_FEATURE_DISABLED.
- scripts/run_baseline.py: PASS.
- scripts/audit_phase1_safety.py logs/containment-audit: PASS; bağımsız
  SysEx/CRC/vector/diff, Capstone hedefleri ve yerel CFG stack analizi.
Loglar logs/containment-{build,tests,verify,baseline,audit}.txt.

SysEx SHA256 557a9364b65c4ae053aaf2817289492d880b89aa8caceaa27b59a167ae1a25c4
Image SHA256 d113af0473707deeab293417be01bbebbc44b6053a81598a377410253de96635
CRC F204A2B9;40 patch,2650 değişen bayt; imaj372596 bayt.
Stok hash pini/ilk0x200 bayt korunur. Cihaz/MIDI/USB erişimi yok.

Değişenler: src/seq_Patch.py, scripts/storage_queue_test_support.py,
scripts/probe_project_alias.py, scripts/verify_phase1_candidate.py,
tests/test_reaudit_abi.py, güncel durum/risk belgeleri ve build.
Başarısız çözüm adayları: iki tam buffer ana SRAM'e sığmıyor; parça-parça
okumada sonraki hata önceki parçaları geri alamıyor. Kanıtsız audio/harici
RAM veya kalıcı Flash yedeği kullanılmadı. Sonraki tek görev: stok bellek
sahipliği ve proje formatını izleyerek sınırlı bellekli, işlevi koruyan
transaction tasarımının mümkün olup olmadığını kanıtlamak. Koruma ancak
hata deneyleriyle doğrulanmış uygulamadan sonra kaldırılabilir.
GO için ayrıca storage yaşam döngüsü, MIDI/Stop, boot/OOM ve zaman bütçesi açık.

---

# 26 Ekim 2026 — KRİTİK: hatalı Load canlı pattern'i bozuyor / NO-GO

SON KARAR: TEHLİKELİ / YÜKLENEMEZ - NO-GO. Bu bölüm önceki kayıtların önündedir.
M7 tamamlanmadı. Cihaz/MIDI/USB erişimi yok; Python optimizasyonsuz çalıştırıldı.

**Kanıtlanmış sorun:** P+14 raw project alanı ile recorder+50 pattern alanları
ayrı tamponlar değildir. Stok33120 span'i raw+2E4, stride5140, count8 kurar.
36950 factory ve48AE0 gerçek recorder kurucuları sekiz recorder+50 pointer'ını
bu raw alanına bağlar. Main281C2 ve283F2 aynı r6 raw tabanını factory/Project
Controller kurucusuna verir;36FDC raw pointer'ı P+14'e yazar.

Yeni scripts/project_alias_test_support.py span ve sekiz recorder kurucusunu
gerçek kodla yürütür; Project Controller'ın pointer bağlama prefix'i yürür.
Tam boot değildir; diğer store argümanları sentetiktir. Relocate edilmiş gerçek
request/result FIFO grafiği, bu raw alanını gerçekten read destination yapar.
Kısmi-read stub'ı741 bayt yazar ve short-read4 döndürür. Close/error cleanup
sonrasında apply hiç çağrılmadan canlı pattern nota60 ->34 olur. Stok API'nin
kısa okuma dönüşü4 disassembly'de doğrulandı. Bu, fiziksel SD olayı iddiası
olmayan fakat kurucu pointer'ları ve kuyruklarla çalışan somut emülasyon
karşı örneğidir. logs/project-alias-probe.json live_pattern_corrupted_without_apply=true.

**Uygulanan sınırlı koruma:** owned Load error, state+64 project_tainted ve
dirty/save-edited set eder. Tainted projede native Save dispatch ve doğrudan
37ED0 Save/Duplicate serialization girişi reddedilir. Geçerli state elde
edilemiyorsa Save girişi de reddedilir. Başarıyla tamamlanmış apply sınırı taint'i
temizleyebilir. Bu, şüpheli RAM'in test edilen Save yollarından kalıcılaştırılmasını
engeller; RAM bozulmasını geri almaz ve diğer tüm I/O yollarının güvenliği değildir.

**Temel yer kısıtı:** proje169092 bayttır; iki tam tampon338184 bayt eder.
Bunlar320KiB (327680 bayt) ana SRAM modeline birlikte sığmaz; diğer nesneler
hesaba katılmadan dahi. İncelenmemiş harici RAM, yığın veya audio alanı staging
alanı olarak seçilmedi. Bağımsız staging/rollback mimarisi doğrulanmadan GO yok.

Yeni verifier, tam paket imajı üzerinde alias probe'unu da çalıştırır:
critical live_pattern_corrupted_on_failed_load; overall_status artık
CRITICAL_RUNTIME_PROBE_FAILED.125/128 gibi geçen regresyon sayısı bu engeli
örtmez. Ayrı probe exit1/NO-GO; verifier exit2/NO-GO ve4 engel döndürür.

Komutlar (.venv\Scripts\python.exe): build-phase1 PASS; unittest discover128
regresyon PASS; paket verifier'da6 sınırlı host ölçütü ve59 güvenlik regresyonu
PASS fakat kritik probe FAIL; audit_phase1_safety.py logs/alias-audit ve
run_baseline.py PASS. Aynı komutlar yerel Node execFile üzerinden çalıştırıldı.
Loglar logs/alias-{build,guard-tests,all-tests,verify,baseline,audit}.txt;
probe logs/project-alias-probe.json; disassembly logs/project-alias-constructors.txt.
Başlangıç factory fixture'ında allocation alanı stack argümanlarıyla çakışıyordu;
heap41000'e taşınarak düzeltildi. Bu fixture hatası firmware ABI kusuru sayılmadı.

SysEx SHA-256 4cd3ff79def431afe9df1ad052f83c61eeb2feb0596e924e9ab82da12d7a4206
Image SHA-256 b7cf055eabb275517f982f270544e005d1ac2d7472f37a17173fbb1b41ce1e3d
CRC0xEC580D7A;39 patch,2614 değişen bayt. Stok pin/ilk0x200 bayt korunur.
Değişenler: src/seq_Patch.py, scripts/project_alias_test_support.py,
scripts/probe_project_alias.py, scripts/storage_queue_test_support.py
(taşınabilir/çakışmayan RAM), scripts/verify_phase1_candidate.py,
tests/test_reaudit_abi.py, docs/STATUS.md, docs/UI-TRACE-5706.md,
docs/PROJECT-LOAD-ALIAS-RISK.md, docs/PHASE1-GO-GATES.md,
docs/PHASE1-HARDWARE-TEST.md, CHANGELOG.md; yerel build çıktıları.

Sonraki tek görev: stok allocator ve çalışma tamponlarının sahipliğini izleyip
ana SRAM dışı doğrulanmış bağımsız staging alanı veya kapsam içi güvenli rollback
stratejisi için bellek/scheduler sınırlarını kanıtlamak. Kanıtsız tampon seçimi
veya custom SD filesystem katmanı eklenmemeli. MIDI/boot/OOM/zamanlama ve diğer
storage yolları da açık. Donanıma yüklenmemeli.

---

# 26 Ekim 2026 — Load okuma/Close hata köprüsü korundu / NO-GO

Bu bölüm önceki kayıtlardan önceliklidir. M7 tamamlanmadı. Cihaz/MIDI/USB
portlarına erişilmedi; Python optimizasyonsuz çalıştırıldı.

Yeni test gerçek Load başlangıcı -> 0x08037BD6 read request -> request FIFO ->
worker -> result FIFO -> read bridge -> Close -> üst callback zincirini kurdu.
Başarısız ilk fixture'da eksik P+68 notification-router nesnesi vardı; portları
kapalı geçerli sentetik router eklenerek düzeltildi, firmware hatası sayılmadı.

**Yeniden üretilen hata:** stok0x080472A8 read result r2'yi kaybedip kopya
file-key kind2'yi status gibi üst Load callback'ine geçiriyordu. Yeni geçerli
fixture ile16 alt-vakada uygulama sınırına erken ulaşma FAIL gözlendi
(logs/load-queue-before.txt).

**Düzeltme:** owned Project Load sonucu state+54 callback ve +58..+63 status
kopyasında tutulur; orijinal key ile stok Close isteği gönderilir. Yeni
c_load_close_result, heap/context/owner/slot/transition-target kontrolünden
sonra read veya Close hatasını status3'e çevirir; ikisi başarılıysa üst Load
callback'ine geçer. Callback bir kez tüketilir. Diğer read alıcıları stok
ABI/path'i korur ve onlara ek Close gönderilmez. Load error cleanup yalnız
ilgili controller'ın low2 busy bitini temizler, ready bitlerini/dirty/modu korur.

**Kanıt ve sınır:** iki mod x read0/2/4/5 x Close0/6 olmak üzere16 senaryo.
Error cleanup gerçek stok kodla yürür; success 0x08037E3C apply sınırında stub
ile gözlenir. Hata mod/dirty/aktif slotu değiştirmez; success deserialization
ve canlı pattern güncellemeleri bu testte yoktur. Kısmi-read stub'ı raw tamponun
ilk16 baytını gerçekten değiştirir; hata sonrası apply çağrılmaz. Raw tampon
önceki haline geri yüklenmez. P+14 raw-buffer ile canlı pattern pointer'larının
alias ilişkisi ve rollback hâlâ kanıtlanmalıdır. Ayrıca Close41906 global dosya
alıcısını kullanır; diğer I/O işleriyle araya girme/scheduler garantisi açıktır.
Bu testler gerçek SD, tam serialization veya fiziksel veri bütünlüğü kanıtı değildir.

Ek testler: generic read ABI/path, yanlış hedef ve duplicate Close,
geçersiz context/heap altında state yazmama. State layout +63'te biter;256 bayt
rezervasyon sınırı korunur. Stack ve callee-saved register kontrolleri geçer.

Komutlar (.venv\Scripts\python.exe):
- scripts/patch_firmware.py --build-phase1: PASS.
- -m unittest discover -s tests -v:124 test PASS.
- scripts/verify_phase1_candidate.py:6 sınırlı host ölçütü ve55 packaged
  güvenlik regresyonu PASS; üç açık engel nedeniyle exit2/NO-GO (mevcut kodda
  bu çıkış engelleri belirtir, başarısız unit test değildir).
- scripts/audit_phase1_safety.py logs/load-queue-audit: PASS.
- scripts/run_baseline.py: PASS.
Standart komut aracı yanıt vermeyince yerel Node execFile ile aynı venv Python
komutları çalıştırıldı. Loglar logs/load-queue-{before,tests,build,all-tests,
verify,baseline,audit}.txt; Capstone/stack/diff logs/load-queue-audit/.
Stok disassembly logs/load-queue-stock.txt ve load-commit-stock.txt.

SysEx SHA-256 aa5e3f581caf66bce9dacda188f81939b82201a44ff2144cee1116ec2db7e3d3
Image SHA-256 42c297e8675c4f7afe92be8332656100e25a48bcdd3558a07d21b68e1e6e835d
CRC 0x65989C5A;39 patch,2574 değişen bayt. Stok pin ve ilk0x200 bayt korundu.
Değişenler: src/seq_Patch.py, scripts/storage_queue_test_support.py,
scripts/audit_phase1_safety.py (Load deferred Thumb callback ADR kontrolü),
scripts/verify_phase1_candidate.py (engel kapsamı), tests/test_reaudit_abi.py,
docs/STATUS.md, docs/UI-TRACE-5706.md, docs/PHASE1-GO-GATES.md,
docs/PHASE1-HARDWARE-TEST.md, CHANGELOG.md; yerel build çıktıları.

GO için açıklar: raw-buffer/canlı RAM alias ve rollback; Load success apply,
New/Duplicate/Clear; global callback/handle/scheduler ömrü; diğer mutation
sıraları; MIDI giriş/çıkış/Stop/Clock; boot/OOM ve kritik bölge zaman bütçesi.
Sonraki tek görev: P+14 raw project buffer ile recorder+50 pattern tabanlarının
kurucu bağlantılarını kanıtlayıp kısmi okuma hatasında canlı projenin korunması
ve gerekli rollback/staging tasarımını gerçek RAM sınırlarıyla doğrulamak.
Donanıma yüklenmemeli.

---

# 26 Ekim 2026 — Save onayı Close sonucuna bağlandı / NO-GO

Bu bölüm önceki kayıtların önündedir. M7 tamamlanmadı. Cihaz/MIDI/USB erişimi
yok; Python optimizasyonsuz çalıştırıldı.

**Hatalar yeniden üretildi:** logs/close-before.txt içindeki8 alt-vakada üst
Save callback'i Close sonucu gelmeden çağrılıyordu. Close bekletilince ikinci
kusur görüldü: hata sonrası Save busy biti açık kalıyordu; logs/close-ready-before.txt
içindeki7 hata senaryosu FAIL verdi.

**Düzeltme:** yakalanmış Project Save write sonucu üst callback'i hemen
çağırmaz. State+44'te callback pointer'ı ve +48..+53'te12 bayt status kopyası
tutulur; orijinal file key ile stok Close request'i kuyruğa verilir. Yeni
c_save_close_result gerçek Close event'inden r2 sonucunu alır; yazma veya
Close hatalıysa status3, ikisi de başarılıysa status2 ile üst callback'e gider.
Phase bu zamana kadar busy kaldığından ikinci Save reddedilir. Context tüketimi
uygulama callback'inden önce yapılır. Başka stock callback alıcıları eski yolu
korur. Heap rezervasyonu Close completion'da tekrar kontrol edilir; geçersiz
bağlam/rezervasyonda state yazılmadan güvenli ret yapılır.

Owned Save error cleanup yalnız Save busy bitini (P+4C store bit1) temizler;
diğer bitler ve dirty korunur. Yabancı error callback bu işlemi yapmaz.

**Kanıt:** write0/2/3/5 x Close0/6 kombinasyonları gerçek request/result FIFO,
worker, Close köprüsü ve üst Save callback'iyle çalıştı. İlk write event'inde
callback yok; Close work sonrasında event tüketilene kadar hâlâ yok; terminal
teslimatta bir callback var. Edit while Close pending, duplicate Close,
geçersiz context/heap ve busy-store diğer bitlerinin korunması test edildi.
Dosya read/write/close ve OS wakeup/semaphore çağrıları stub'dır; full project
serialization, scheduler, SD/güç kesintisi dayanıklılığı kanıtlanmadı.

Komutlar (.venv\Scripts\python.exe): build-phase1 PASS; unittest discover119
test PASS; verify_phase1_candidate.py paket regresyonları/6 sınırlı host ölçütü
PASS ama açık engellerle exit1/NO-GO; audit_phase1_safety.py logs/close-audit
ve run_baseline.py PASS. Loglar logs/close-{before,ready-before,build,tests,
all-tests,verify,baseline,audit}.txt; Capstone/diff/stack logs/close-audit/.

SysEx SHA-256 `4e5de2f55896c37fc326eba93985f087775c444befe2e0a0da626a99bddd9fb4`
Image SHA-256 `f191a5180ce6af24d78be6f0e6d08608a43becf60ee5eacd0ba3b9999e703da9`
CRC `0xCA225F6E`;38 patch,2378 değişen bayt. Stok pin ve ilk0x200 bayt korundu.
Değişenler: src/seq_Patch.py, scripts/storage_queue_test_support.py,
scripts/audit_phase1_safety.py (incelenen deferred Thumb callback ADR kontrolü),
scripts/verify_phase1_candidate.py (engel kapsamı), tests/test_reaudit_abi.py,
docs/STATUS.md, docs/UI-TRACE-5706.md, docs/PHASE1-GO-GATES.md,
docs/PHASE1-HARDWARE-TEST.md, CHANGELOG.md; yerel build çıktıları.

GO için açıklar: gerçek dosya/rollback/güç kesintisi, Load/New/Duplicate/Clear
ve global callback/işlem ömrü, diğer mutation yarışları, MIDI input/output/
Stop/Clock, boot/OOM, kritik bölge zaman bütçesi. Sonraki tek görev: aynı FIFO
grafiğinde Load read-error/Close-result yollarını çalıştırıp hatalı okumanın
aktif proje/mod/dirty bilgisini başarı gibi değiştirmediğini doğrulamak.
Donanıma yüklenmemeli.

---

# 26 Ekim 2026 — Gerçek FIFO zincirinde Save yazma hatası düzeltildi / NO-GO

Bu bölüm önceki kayıtların önündedir. M7 tamamlanmadı. Cihaz/MIDI/USB
erişimi yok; Python optimizasyonsuz çalıştırıldı.

Yeni scripts/storage_queue_test_support.py gerçek stok request FIFO,
worker, result FIFO ve callback köprüsünü çalıştırır: 0x080472E2 -> 45EB6 ->
2ACB8 -> 40DC4 / 2AD40 -> 419CC -> 25B1A -> 2B064 -> 47304 -> Save callback.
FIFO kopyalama/indeksleri/result oluşturma gerçektir. OS wakeup/semaphore
çağrıları ve dosya API'leri stub'dır; scheduler/SD/serialization gövdesi yoktur.
Save başlangıcı gerçek stok kodla phase set edilene kadar yürütülür, sonra
request köprüsüne geçilir. Başarı/error callback'i ve metadata/store cleanup
gerçek kodla çalışır.

**Yeni hata ve düzeltme:** worker yazma API sonucunu event r2'sinde taşır;
stok0x08047304 köprüsü bu sonucu kaybedip kopyalanmış file-key kind2'yi
üst Save callback'ine status olarak geçiriyordu. API hata enjeksiyonunda dirty0
gözlendi (logs/queue-error-before.txt). Yeni c_save_storage_result yalnız
yakalanmış Save owner'ın P+10 callback'i için, stok Close request'ini kurduktan
sonra hata durumunu callback'in result kopyasına3 olarak aktarır. Başlangıç
file key değişmez. Diğer callback'ler stok ABI/veri davranışını korur.

**Kuyruk sırası kanıtı:** sonuç tüketilmeden ikinci Save, worker işini bitirmiş
olsa da gerçek action dispatcher'da reddedilir. Başarı0 ve hata2/3/5 denendi:
hata dirty'yi korur ve snapshot iptal edilir; başarı dirty'yi temizler. Sonuç
FIFO'dan bir kez tüketilir, bridge pointer sıfırlanır. Sonraki Close sonucu Save
callback'ini ikinci kez çağırmaz. Bu sınırlı modelde eski probe'un ikinci
snapshot'ı erkenden başlatması gerçek dispatcher'dan geçemez. Global queue/
scheduler tüm iş akışları için kimlik garantisi henüz kanıtlanmadı.

**Açık önemli sınır:** üst Save onayı, Close sonucu dönmeden veriliyor.
Close/flush hata yolu test edilip onaya bağlanmadı. Load/New/Duplicate/Clear,
gerçek depolama rollback ve callback yarışları hâlâ açık; NO-GO sürer.

Komutlar (.venv\Scripts\python.exe): build-phase1 PASS; unittest discover117
test PASS; verify_phase1_candidate.py paket regresyonları/6 sınırlı host ölçütü
PASS fakat açık engellerle exit1/NO-GO; bağımsız audit_phase1_safety.py
logs/queue-audit ve run_baseline.py PASS. Loglar logs/queue-{build,tests,
all-tests,verify,baseline,audit}.txt; makine kodu/diff/stack logs/queue-audit/;
stok queue disassembly logs/queue-stock.txt ve queue-worker-stock.txt.

SysEx SHA-256 `0d7e419e91de7ab94fa4910fa2b564e2ca2697cfa5930d51ab2717c9649317cb`
Image SHA-256 `71b7436eb058ef65e01c3fd4795f428b7f68eafd2a3e01b54db1cb776e69a0ef`
CRC `0xF0E9968E`;38 patch,2252 değişen bayt. Stok pin ve ilk0x200 bayt korundu.
Değişenler: src/seq_Patch.py, scripts/storage_queue_test_support.py,
scripts/audit_phase1_safety.py (incelenen Close enqueue hedefi),
scripts/verify_phase1_candidate.py (engel kapsamı), tests/test_reaudit_abi.py,
docs/STATUS.md, docs/UI-TRACE-5706.md, docs/PHASE1-GO-GATES.md,
docs/PHASE1-HARDWARE-TEST.md, CHANGELOG.md; yerel build çıktıları.

GO için kalanlar: Close/flush onayı ve diğer storage hata/rollback yolları,
kimlik/scheduler yarışları, MIDI input/output/Stop/Clock, boot/OOM, kritik bölge
zaman bütçesi. Sonraki tek görev: Close hatasını aynı gerçek FIFO grafiğinde
enjekte edip Save onayının Close tamamlanmasına bağlanmasını doğrulamak.
Donanıma yüklenmemeli.

---

# 26 Ekim 2026 — Geçiş sahipliğini ezme düzeltildi; işlem kimliği açık / NO-GO

Bu bölüm önceki kayıtların önündedir. M7 tamamlanmadı; cihaz/MIDI/USB erişimi
yok, Python optimizasyonsuz çalıştırıldı.

İki yeni hata gerçek stok dispatch ve sentetik RAM ile yeniden üretildi:
- Başka kontrolcünün reddedilen Load isteği OFF_PROJ_CTRL_PTR'ı değiştiriyordu.
  Owner artık yalnız kabul edilen Load/New veya state1->2 kabulünde yazılır.
- Yabancı Projects görünümüne yeniden giriş aktif owner/view bağlamını eziyordu.
  Projects enter, trans_state sıfır değilken bu bağlamı yeniden yakalamaz.
İkisi eski adayda FAIL (logs/identity-before.txt ve reentry-before.txt), yeni
adayda PASS. İlk geçiş yabancı ret sonrasında kendi completion'ını kabul eder.

**İşlem kimliği karşı örneği:** yeni scripts/probe_operation_identity.py,
Save A -> gerçek dirty hook -> aynı P/slot için Save B snapshot -> enjekte
eski ack sırasını completion sınırında çalıştırır. İki kimlik de P=20006000,
slot7; ack sonrası dirty0 olur. logs/identity-probe.json hazard_at_boundary=true
ve NO-GO döndürür. Script bilerek exit1 üretir;115 geçen testin parçası değildir.
Bu enjeksiyon serialization devamını/kuyruğu çalıştırmaz; dizinin gerçek stok
kuyrukta mümkün olduğu kanıtlanmadı. Dolayısıyla cihazda doğrulanmış stale-ack
hatası veya generation probleminin çözümü iddia edilmiyor.

Disassembly: Save 0x08037FC2 P+10 callback nesnesini taşır; Load P+0C kullanır.
0x080472E2 / 0x08047288 köprüleri callback nesnesini ortak alanlara kaydeder;
0x08047344 / 0x080472A8 tüketim sırasında pointer'ı sıfırlar. Bu yalnız bir
katmanın davranışıdır; queue terminal olayının tam-bir-kez/seri teslimat kanıtı
değildir. Sadece yerel sayaç eklenirse sabit P/slot/status callback'inin hangi
işleme ait olduğu anlaşılmaz. İncelenmemiş transport değişikliği yapılmadı.

Komutlar (.venv\Scripts\python.exe): build-phase1 PASS; unittest discover115
test PASS; verify_phase1_candidate.py paket regresyonları/6 sınırlı host ölçütü
PASS ama açık engellerle exit1/NO-GO; audit_phase1_safety.py logs/identity-audit
ve run_baseline.py PASS. Probe ayrıca exit1/NO-GO.
Loglar logs/identity-{build,tests,all-tests,verify,baseline,audit}.txt ve
logs/identity-audit/; stok analiz logs/operation-identity-stock.txt.

SysEx SHA-256 `39288ca3f9035df943e545ed7009a07366b84030673f8b08d9bce1896aaf9642`
Image SHA-256 `55587ebc16722c53e0f35b5c5a7b9e80c558a2d32dc7ebd92e994c40a7f9a0e9`
CRC `0xFFDD33EC`;37 patch,2184 değişen bayt. Stok pin ve ilk0x200 bayt korundu.
Değişenler: src/seq_Patch.py, tests/test_reaudit_abi.py,
scripts/probe_operation_identity.py, scripts/verify_phase1_candidate.py (açık
engel metni), docs/STATUS.md, docs/UI-TRACE-5706.md, docs/PHASE1-GO-GATES.md,
docs/PHASE1-HARDWARE-TEST.md, CHANGELOG.md; yerel build çıktıları.

GO için açıklar: queue/işlem kimliği ve storage rollback, diğer mutation/geçiş
yarışları, MIDI giriş/çıkış/Stop/Clock, boot/OOM, kritik bölge zaman bütçesi.
Sonraki tek görev: 0x08045EB6 -> 0x0802ACA2/0x0802ACB8 request kuyruğunu
ve terminal callback tüketimini emülasyonda kurup aynı kontrolcü için yeni
işlem kabulünden önce önceki terminal olayın kesin tüketildiğini sınamak.
Donanıma yüklenmemeli.

---

# 26 Ekim 2026 — Load/Save callback sahipliği düzeltildi / NO-GO

Bu bölüm önceki durum kayıtlarından önceliklidir. M7 tamamlanmadı.
Cihaz/MIDI/USB erişimi yok; Python optimizasyonsuz çalıştırıldı.

Üç hata sentetik RAM ve gerçek stok/patch makine koduyla yeniden üretildi:

- Beklenen32 yerine slot0/31/33/64/255 Load completion gelince dirty ve Save
  snapshot temizleniyor, geçiş iptal ediliyordu. Slot sınırı, kontrolcü ve hedef
  eşleşmesi artık patch durumu değiştirilmeden kontrol edilir. Yanlış slotta
  geçiş beklemede kalır; güvenli ret tercih edilir, tam recovery kanıtı değildir.
- Başka kontrolcüden Load status3 hatası aktif geçişi iptal ediyordu.
  İptal artık yalnız trans_state2 ve eşleşen kontrolcü için yapılır. Stok cleanup
  ilgili callback'in kendi phase store'unu/observer listesini işlemeye devam eder.
- Save status3 hatası başarısız işlemin snapshot owner'ını bırakıyordu.
  0x080381D6 callback girişine guard eklendi: yalnız eşleşen Save owner atomik
  olarak sıfırlanır, PRIMASK geri yüklenir, stok0x08037DD0 cleanup yürütülür.
  Sonradan gelen completion patch dirty bayrağını temizleyemez. Status2 başarı
  0x08038078'e orijinal argümanlarla iletilir; diğer status'lar no-op kalır.

Eski adaydaki kanıtlar: logs/load-errors-before.txt (6 alt-vaka FAIL),
logs/save-error-before.txt (1 FAIL). Yeni adayda tamamı PASS. Foreign/owned
Save error, status0/1/3/4 ve PRIMASK0/1 denendi; cleanup'un gerçek store değişimi
ve SP/r4-r11 korunması kontrol edildi. Başarı yönlendirmesi stok fonksiyon
sınırına kadar test edildi. Bu, gerçek SD serialize/read/write roundtrip değildir;
patch completion testleri callback sınırını enjekte eder. Aynı kontrolcü/slotta
yeni işlem başlarken eski callback'in gelmesi henüz ayırt edilmiş değildir.

Komutlar (.venv\Scripts\python.exe):
- scripts/patch_firmware.py --build-phase1: PASS.
- -m unittest discover -s tests -v: 113 test PASS.
- scripts/verify_phase1_candidate.py: paket regresyonları ve6 sınırlı host ölçütü
  PASS; üç açık engel nedeniyle exit1/NO-GO.
- scripts/audit_phase1_safety.py logs/storage-callback-audit: PASS.
- scripts/run_baseline.py: PASS.
Loglar: logs/storage-callback-{build,tests,all-tests,verify,baseline,audit}.txt;
stok disassembly logs/storage-callback-stock.txt; paket disassembly/stack/diff
logs/storage-callback-audit/.

SysEx SHA-256 `0b4192d470b9abafbe46989661f4daab014abc712c27c080ee79d576155f4bb2`
Image SHA-256 `d92fa3c0bd21858fa3ed856e6fa311778f4f432ac5623594d81645382f52bc26`
CRC `0x541CC381`;37 patch,2180 değişen bayt. Stok pin ve ilk0x200 bayt korunur.
Değişenler: src/seq_Patch.py, scripts/audit_phase1_safety.py (incelenen Save
başarı hedefi), tests/test_reaudit_abi.py, docs/STATUS.md, docs/UI-TRACE-5706.md,
docs/PHASE1-GO-GATES.md, docs/PHASE1-HARDWARE-TEST.md, CHANGELOG.md; build çıktıları.

Açıklar: gerçek storage/rollback, ardışık işlem kimliği, diğer mutation yarışları,
MIDI giriş/queue/Stop/Clock, boot/OOM ve kritik bölge zaman bütçesi.
Sonraki tek görev: aynı kontrolcüde ardışık Save/Load işlemlerinde eski
callback'in yeni işlemi onaylayabilmesini yeniden üretip işlem kimliği ve
dispatch sahipliğini birlikte incelemek. Cihaza yüklenmemeli.

---

# 26 Ekim 2026 — Bekleyen kayıt / mod geçişi açığı düzeltildi / NO-GO

Bu bölüm önceki kayıtların önündedir. Cihaz/MIDI/USB erişimi yapılmadı;
Python optimizasyonsuz çalıştırıldı. M7 henüz tamamlanmadı.

**Yeniden üretilen hata:** Note On sonrası pending kayıt oluşmasına rağmen
dirty yalnız pattern finalizer'ında set ediliyordu. Shift+Sample Rec bu aralıkta
mod geçişini başlatıp trans_state=2 yapıyordu. logs/pending-before.txt testinde
beklenen0 yerine2 gözlendi. Bu, sentetik grafikte kanıtlı kabul hatasıdır;
SD yükleme sonrası fiziksel veri bozulması gerçekleştiği iddia edilmiyor.

**Düzeltme:** 0x08036ABC kayıt grubu callback noktasına yeni guard eklendi.
trans_state1/2 veya state rezervasyonu başarısızsa yeni kayıt başlamaz.
Kabul edilen kayıt başlangıcı dirty/save-edited set eder ve track'in recorder
pointer'ını state+24..+43 alanına kaydeder. Kontrol ve stok pending oluşturma
PRIMASK korunarak birlikte yapılır; çıkışta önceki maske geri yüklenir.
Çağıranın kalan BLX'i no-op'a gider, gerçek callback iki kez çağrılmaz.

Save completion, dirty temizlemeden önce sekiz yakalanmış recorder'ın current
notasını ve note1..139 pending bitlerini tarar. Pending varsa dirty korunur.
Pointer hizalama/RAM sınırı hatasında dereference yapılmadan pending kabul
edilir. Recorder pointer'ları boot nesne grafiğine dayanır; tam boot ve nesne
ömrü kanıtı hâlâ açık olup yeni guard'ın kesme gecikmesi de doğrulanmalıdır.

**Testler:** Hata veren senaryo artık PASS. Pending sırasında mod geçişi yok;
Save ack dirty'yi korur; Note Off/flush sonrası yeni Save ack temizleyebilir.
Geçiş state0/1/2 ve PRIMASK0/1, sekiz track'in ilk/son pending word'u ve
geçersiz pointer'larda güvenli ret test edildi. Tüm paket 108 test PASS.
Build, bağımsız binary/Capstone/stack denetimi ve baseline PASS.
Verifier 6 sınırlı host ölçütü/paket regresyonları PASS; üç açık engel nedeniyle
çıkış1 ve NO-GO. Komutlar .venv\Scripts\python.exe ile önceki dört zorunlu
komut ve scripts/audit_phase1_safety.py logs/pending-audit şeklinde çalıştırıldı.
Loglar logs/pending-{before,build,tests,all-tests,verify,baseline,audit}.txt;
makine kodu kanıtı logs/pending-audit/.

Yeni SysEx SHA-256:
`0100bf4fc3bd266d4e7ba5c4533264675d06d6593b8564cab1a07bbb8fd23ab6`
Image SHA-256:
`c68c47b2e05ad5e61e7095658f2bc9aa74b05237647f4360c766f7dc28b675c3`
CRC `0xEF571959`; 36 patch, 2102 değişen bayt. Stok pin ve ilk0x200 bayt korundu.

Değişenler: src/seq_Patch.py, scripts/phase1_test_support.py (çakışmayan
sentetik adres seçimi), scripts/audit_phase1_safety.py (yalnız doğrulanmış
Thumb no-op ADR hedefi için dar kontrol), tests/test_reaudit_abi.py,
docs/STATUS.md, docs/UI-TRACE-5706.md, docs/PHASE1-GO-GATES.md,
docs/PHASE1-HARDWARE-TEST.md, CHANGELOG.md ve yerel build çıktıları.

Açıklar: diğer mutation/geçiş sıraları, SD completion/hata/rollback,
UART/USB ve MIDI output queue/Clock/Stop, boot/OOM, yeni kritik bölgenin zaman
bütçesi. Sonraki tek görev: stock Save/Load callback hata yollarını hata
enjeksiyonuyla doğrulamak; eşleşmeyen/geç tamamlanan işlemin aktif proje ve
dirty durumunu bozmamasını test etmek. Donanıma yüklenmemeli.

---

# 26 Ekim 2026 — Kısa MIDI mesajından pattern'e zincir tamamlandı / NO-GO

Bu bölüm önceki durum kayıtlarından önceliklidir. M7 tamamlanmadı. Cihaz,
MIDI/USB portu erişimi yok; Python optimizasyonsuz çalıştırıldı.

Önceki eksik bağlantı çözüldü: 0x0803B31E..324 çağrısında r1 üçüncü,
r2 ikinci, r3 ilk allocation'dır. 0x0804A8CC bunları voice+1C/+20/+24'e
koyar. Kayıt alıcısı +24'tür; +1C kabulü yanlıştı. Firmware kusuru değil,
test nesne grafiğinin kurulmasına ilişkin analiz düzeltmesidir.

Yeni scripts/midi_record_test_support.py gerçek stok vtable'ları, router,
nota adaptörleri ve iki sahiplik filtresini birbirine bağlar. Filtrelerin
0x08054F10 constructor'ı gerçekten yürütülür. Decoder 0x0805AF94 ->
router -> filtreler -> kayıt grubu -> recorder -> flush -> pattern zinciri
artık kesintisiz gerçek makine koduyla çalışır. Yalnız son sample alıcısı stub;
nesnelerin geri kalanı sentetik RAM'de kurulur. Bu, tam boot/UART/USB/SD veya
sample ses motoru kanıtı değildir; scheduler yerine flush açıkça çağrılır.

Kanıtlar:
- 8 track x 2 mod x 2 Note Off biçimi = 32 entegrasyon senaryosu.
  Pattern7 step31 dışında pattern baytları korunur, dirty/save-edited set edilir.
  Release sonrası receiver ve iki filtre sahiplik maskesi temizdir.
- MIDI note0/127 -> iç nota12/139; recorder+294 sonrası canary korunur.
- Aynı kaynak tekrarı yeni Note On üretmez; ikinci kaynak retrigger yapar;
  bir kaynak bırakıldığında diğer kaynak tutuluyorsa terminal Note Off gönderilmez.
  Son kaynak bırakılınca tek Note Off; tekrar release etkisizdir.
- Çağrılarda SP ve r4-r11 korunması denetlenir. Yeni firmware hatası saptanmadı.

Komutlar (.venv\Scripts\python.exe): build-phase1 PASS; unittest discover
105 test PASS; verify_phase1_candidate.py paket regresyonları ve 6 sınırlı
host ölçütü PASS, üç açık engel nedeniyle exit1/NO-GO; bağımsız
audit_phase1_safety.py ve run_baseline.py PASS.
Loglar: logs/ownership-{build,tests,all-tests,verify,baseline,audit}.txt,
logs/ownership-audit/; disassembly: logs/ownership-disassembly.txt.

Firmware aynı: SysEx SHA-256
`e39be1725b1afa875571807229c5cf0e3eecfe4ff30c04f9223449aec9dff36e`,
CRC `0x2FA08805`; stok pin ve ilk0x200 bayt korunuyor.
Değişenler: scripts/midi_record_test_support.py, tests/test_reaudit_abi.py,
scripts/verify_phase1_candidate.py (engel açıklaması; engel kaldırılmadı),
docs/STATUS.md, docs/UI-TRACE-5706.md, docs/PHASE1-GO-GATES.md,
docs/PHASE1-HARDWARE-TEST.md, CHANGELOG.md.

GO için kalanlar ve kabul ölçütleri: PHASE1-GO-GATES.md. Sonraki tek görev:
bekleyen MIDI kaydı varken mode/proje geçişi ve Save completion yarışını aynı
sentetik grafikte sınamak; geç tamamlanan kaydın başka projeye yazmamasını
ve dirty'nin erken temizlenmemesini doğrulamak. Donanıma yüklenmemeli.

---

# 26 Ekim 2026 — MIDI kanal dönüşümü ve kayıt track seçimi / NO-GO

Bu bölüm önceki kayıtlardan önceliklidir. M7 tamamlanmadı. Fiziksel cihaz,
MIDI/USB portu kullanılmadı; Python optimizasyonsuz çalıştırıldı.

Yeni iki Unicorn testi, sentetik RAM üzerinde gerçek stok makine kodunu sınar:

- 0x0805AF94 kısa MIDI mesaj decoder'ı -> 0x0803F5A8/0x0803F660 receiver ->
  0x0803EC10/0x0803EC2A nota adaptörü -> 0x08069140/0x08024AB2 track adaptörü.
  Son router alıcısı gözlem stub'ıdır; recorder ile yapay olarak bağlanmadı.
  Ters kanal haritasıyla sekiz track, Note On/Off ve velocity=0 Note On denendi.
  Nota 48 -> 60, track kimliği 16..23; release sonrası receiver nota maskeleri
  sıfırlanıyor. Eşleşmeyen kanal ve kapalı note-input bayrağı olay iletmiyor.
- Bağımsız kayıt katmanı: 0x08036A80/0x08036AC4 -> gerçek recorder vtable ->
  pending -> flush -> pattern. Sekiz track ve durum store'u word0/1/2 için
  (1,1,0), (0,1,0), (1,0,0), (1,1,1) denendi. Yalnız ilk durumda pattern7
  step31 yazıldı; hedef dışı pattern baytları korundu. Çağrılarda SP/r4-r11
  korunması kontrol edildi.

Çürütülen varsayım: MIDI router sınırı doğrudan recorder alıcısı değildir.
İlk birleşik fixture 0x0804AA32'de eksik +0x0C yan-dal nesnesini okurken
UC_ERR_READ_UNMAPPED verdi. Bu test-fixture eksikliğidir; firmware HardFault
kanıtı değildir. 0x0803B7EC -> 0x0803B9F8 class2 -> 0x0804A9D8 case2
hem +8 hem +0x0C alt nesnesine yönlenir. Tam bağlantı kanıtlanmadan testte
bu yol recorder'a kestirme bağlanmadı. UART/USB parser ve gerçek nesne kurulumu
da hâlâ bu testlerin dışındadır.

Komutlar (.venv\Scripts\python.exe):
- scripts/patch_firmware.py --build-phase1: PASS; aynı firmware baytları.
- -m unittest discover -s tests -v: 102 test PASS.
- scripts/verify_phase1_candidate.py: paket regresyonları ve 6 sınırlı host
  ölçütü PASS; üç açık engel nedeniyle çıkış1 / NO-GO.
- scripts/audit_phase1_safety.py logs/ingress-audit: PASS.
- scripts/run_baseline.py: PASS.

Loglar: logs/ingress-{build,all-tests,verify,baseline,audit}.txt,
logs/ingress-audit/; disassembly: logs/ingress-disassembly.txt,
ingress-constructor.txt ve ingress-routing.txt.
SysEx SHA-256 `e39be1725b1afa875571807229c5cf0e3eecfe4ff30c04f9223449aec9dff36e`,
CRC `0x2FA08805`; stok pin ve vektör tablosu korundu.
Değişenler: tests/test_reaudit_abi.py, docs/STATUS.md,
docs/UI-TRACE-5706.md, CHANGELOG.md. Firmware kaynakları değiştirilmedi.

Açık riskler: kesintisiz MIDI giriş/kayıt zinciri ve diğer mutation yolları,
asenkron Save hata/rollback, MIDI queue/Stop, gerçek boot, OOM çağıranları.
Sonraki tek görev: 0x0804A9D8 case2'nin +8/+0x0C nesnelerini ve
0x08054F30/0x08054FA8 nota sahipliği katmanını kurup router sonrası gerçek
alıcıları doğrulamak. Cihaza yüklenmemeli.

---

# 26 Ekim 2026 — Recorder callback zinciri doğrulandı / NO-GO

Bu bölüm önceki durum kayıtlarından önceliklidir. M7 tamamlanmadı.
Fiziksel cihaz/MIDI/USB erişimi yapılmadı; Python optimizasyonsuz çalıştırıldı.

- Gerçek vtable 0x08067864 ile 0x080492A8 Note On, 0x0804933E Note Off ve
  0x08048D2A flush zinciri Unicorn'da çalıştırıldı. Pending yapı test tarafından
  doldurulmadı; stok callback'ler tarafından oluşturuldu.
- Pattern 0/7, step 0/31, note 60, velocity 96 ve 24 tick süre denendi.
  Seçili olmayan pattern'e yalnız hedef step yazıldı; dirty/save-edited set edildi.
  Tekrarlanan Note Off/flush ek değişiklik veya dirty üretmedi. Her çağrıda SP ve
  r4-r11 korunması kontrol edildi.
- Bu, sentetik RAM ve recorder arayüzünden başlayan testtir. UART/USB MIDI
  parser'ı, kanal/track yönlendirmesi, seçili pattern callback zinciri ve tüm
  quantize/timing varyantları için uçtan uca kanıt değildir.

Komutlar (.venv\\Scripts\\python.exe): build-phase1 PASS; unittest discover
100 test PASS; verify_phase1_candidate.py paket regresyonları ve 6 kapsamlı
olmayan host ölçütü PASS, açık engeller nedeniyle çıkış kodu 1 / NO-GO;
audit_phase1_safety.py ve run_baseline.py PASS.
Loglar: logs/callback-all-tests.txt, callback-verify.txt, callback-baseline.txt,
callback-audit.txt ve logs/callback-audit/.

Firmware değişmedi: SysEx SHA-256
`e39be1725b1afa875571807229c5cf0e3eecfe4ff30c04f9223449aec9dff36e`,
CRC `0x2FA08805`. Stok pin ve vektör tablosu korundu.
Değişenler: tests/test_reaudit_abi.py, docs/STATUS.md,
docs/UI-TRACE-5706.md, CHANGELOG.md. Yeni firmware hatası saptanmadı.
Yanlış genelleme önlendi: Note Off tek başına pattern commit anlamına gelmiyor;
bu senaryoda commit flush sırasında oluyor.

Açık riskler: MIDI ingress/diğer mutation yolları, asenkron Save hata/rollback,
MIDI kuyruk/Stop, gerçek boot ve OOM çağıranları. Sonraki tek görev: MIDI
dispatcher'dan recorder vtable slot 0/1'e kanal/track yönlendirmesini izleyip
girişten callback'e entegrasyon testi kurmak. Donanıma yüklenmemeli.

---

# 26 Ekim 2026 — Doğrudan kayıt yazmaları korundu / NO-GO

Önceki durum kayıtlarından önceliklidir. Fiziksel cihaz/MIDI/USB erişimi yok;
Python optimizasyonsuz çalıştırıldı.

## Somut düzeltme

Stok 0x08048E70 kayıt finalizer'ı pending kayıttan pattern/step/velocity/microstep
çıkarır. 0x08048F02 microstep alanını yazar; 0x0804904E devamı note/gate/velocity
ve flag alanlarını günceller. Seçili olmayan pattern'de ST1/ST2 notify yapılmadığı
için önceki commit dirty kancası bu düzenlemeyi kaçırıyordu.
0x08048F02'ye argümanları koruyan dirty/save-edited kancası eklendi.

0x0804909C fonksiyonunun seçili olmayan pattern dalı 0x080490F4'te step+5
(delay) baytını doğrudan yazar. 0x080490F0 adres hesabına ikinci dirty kancası
eklendi; orijinal makine kodu tekrar yürütülür. Tüm bellek yazmaları stok
kodda kalır. Bu kancalar pending kayıtları iptal etmez ve MIDI Note Off kesmez.

## Test ve kanıt

- Eski adayda iki regresyon FAIL, yeni adayda PASS:
  logs/record-regressions-before.txt.
- Pattern 0/7, step 0/31, seçili olmayan pattern'e gerçek stok kayıt finalizer'ı
  çalıştırıldı. Note=60, velocity=96, microstep maskesi=8; diğer adım/pattern
  baytları korunuyor. Dirty ve save-edited set ediliyor.
- Aynı pending kayıt tüketildikten sonra ikinci çağrı yazmıyor/dirty set etmiyor.
- Seçili pattern 7'nin son adımı için gerçek record -> store -> notify -> commit
  zinciri çalıştırıldı; hedef dışı pattern baytları korunuyor.
- Doğrudan delay yazımı yalnız hedef baytı değiştiriyor.
- Bu testler stok kayıt finalizer'ının sentetik RAM testidir. Fiziksel veya
  emüle edilmiş MIDI byte girişinden uçtan uca kayıt testi değildir.

Komutlar (.venv\Scripts\python.exe):
- scripts/patch_firmware.py --build-phase1: PASS
- -m unittest discover -s tests -v: 99 test PASS
- scripts/verify_phase1_candidate.py: 6 kapsamlı olmayan host ölçütü ve paket
  regresyonları PASS; açık engeller nedeniyle NO-GO
- scripts/audit_phase1_safety.py logs/record-audit: PASS
- scripts/run_baseline.py: PASS
Loglar: logs/record-tests.txt, record-verify.txt, record-baseline.txt;
Capstone/stack/manifest kanıtı: logs/record-audit/.

SysEx SHA-256: `e39be1725b1afa875571807229c5cf0e3eecfe4ff30c04f9223449aec9dff36e`
Image SHA-256: `f54373faade49f05061a9170b3f71d2aeac83168e7c6e236c06524400336513f`
CRC-32/MPEG-2: `0x2FA08805`; 35 hunk, 1937 değişen bayt.
Stok pin, vektör tablosu ve uygulama sınırları korunuyor.

Değişenler: src/seq_Patch.py, tests/test_reaudit_abi.py,
scripts/verify_phase1_candidate.py, docs/STATUS.md, docs/UI-TRACE-5706.md,
CHANGELOG.md. Önceki varsayım çürütüldü: her record yazımı store notify üzerinden
geçmiyor. Playback-only 0x0804AFBC akışı kayıt yazma noktası sanılmadı;
disassembly ile farklı kayıt finalizer'ı ayrıldı.

Açık riskler: MIDI ingress ve diğer mutation yolları, asenkron Save hata/rollback,
MIDI kuyruk/Stop, gerçek boot ve OOM çağıranları. Sonraki tek görev: MIDI giriş
callback'inden kayıt pending yapısına giden bağlantıyı kurup aynı kayıt
finalizer'ını tam giriş zincirinden test etmek. Donanıma yüklenmemeli.

---

# 26 Ekim 2026 — Dirty koruması genişletildi; NO-GO sürüyor

Bu bölüm eski durum kayıtlarından önceliklidir. Cihaz/MIDI/USB erişimi yok;
Python -O kullanılmadı.

## Uygulanan düzeltmeler

- Stok pattern commit girişi 0x08048208 artık ST1 (+1C), ST2 (+20) ve pattern
  settings (+24) kaynaklarından gelen güncellemeleri dirty işaretler. Selection
  ve diğer kaynaklar bu yeni kanca tarafından dirty işaretlenmez. Stok prologue
  ve tüm argümanlar korunur; veri yazma işlemleri stok kodda kalır.
- 0x0803DDE0 controller knob girişinde sıfır olmayan delta dirty işaretler;
  proje geçişi sırasında knob düzenlemeleri iletilmez. Bu konservatif bir
  input korumasıdır: saturasyonda veya veri değiştirmeyen görünümde dahi
  kaydetme gerektirebilir. Gerçek macro veri commit zincirinin tamamı kanıtlanmadı.
- Save/Duplicate başlangıcı 0x08037ED0 kontrolcü ve slot kimliğini yakalar.
  Sonraki pad/knob/pattern değişiklikleri save_edited bayrağını set eder.
  Tamamlanma yalnız eşleşen snapshot'ı onaylar; sonradan edit varsa dirty
  korunur. Tamamlanma bir kez tüketilir. Yeni proje yüklenince eski save
  snapshot'ı iptal edilir. Kontrol ve dirty temizliği PRIMASK korunarak yapılır.

## Kanıt ve sınırlar

Yeni pad dışı parametre ve knob testleri önceki paket üzerinde 15 alt-vakada
başarısızdı (logs/dirty-regressions-before.txt), yeni adayda geçti.
Note, Gate, Velocity, Microstep, Probability, Gate ile ilişkili diğer ST alanları
setter/notify/gerçek vtable commit zincirinde; ilk ve son adım, pattern 7 için
sınandı. Parametre baytı doğrulandı ve sonraki mod isteğinin reddi gözlendi.
Sekiz knob için delta 0/+1/-1, argümanlar, ABI ve geçişte teslimat engeli sınandı.
Save yarışı testi gerçek snapshot girişini ve pattern dirty kancasını çalıştırır;
tamamlanma elle enjekte edilir. SD roundtrip testi değildir. Aynı completion'ın
tekrarı ve PRIMASK 0/1 korunumu sınandı. Başarısız save'in tüm stok yolları açık.

Komutlar .venv\Scripts\python.exe ile:
- scripts/patch_firmware.py --build-phase1: PASS
- -m unittest discover -s tests -v: 96 test PASS
- scripts/verify_phase1_candidate.py: host ölçütleri ve paket regresyonları PASS;
  açık engeller nedeniyle NO-GO
- scripts/audit_phase1_safety.py logs/dirty-final-audit: PASS
- scripts/run_baseline.py: PASS
Loglar: logs/dirty-final-*.txt. Disassembly ve fonksiyon stack raporu:
logs/dirty-final-audit/. Stock pin, ilk 512 bayt, SysEx ve CRC doğrulamaları geçti.

SysEx SHA-256: `8d6d6f0c2609510cdb24b824312204546ddb4c6f7439473fff8e499185d61518`
Image SHA-256: `dad4b0f71764819943b660586b89b9e8bd5ba80339f146c663cdab80f5ed2dcd`
CRC-32/MPEG-2: `0x9F4AE824`; 33 hunk, 1879 değişen bayt.

Değişen dosyalar: src/seq_Patch.py, tests/test_reaudit_abi.py,
scripts/audit_phase1_safety.py, scripts/verify_phase1_candidate.py ve belgeler.
Yanlışlanan varsayım: tüm düzenlemeler pad resolver'dan geçmez; stock setter
üzerinden pad olayı olmadan pattern RAM değiştirilebiliyor.

Açık riskler: doğrudan record/MIDI mutation, save hata/rollback ve asenkron
bildirim sıralaması, gerçek storage/MIDI/boot, allocator OOM çağıranları.
Sonraki tek görev: record ve gelen MIDI'nin pattern RAM'e doğrudan yazma
noktalarını izleyip dirty kapsamına eklemek. Dirty engeli henüz kapatılmadı.

---

# 26 Ekim 2026 — Proje geçişi düzeltmeleri / NO-GO

Eksik proje bağlantısında doğrudan mod açan fallback kaldırıldı. Eksik action,
ready, phase veya metadata pointer'ı artık isteği reddeder. Slot sınırları
kontrol edilir; yalnız gerçek dispatcher'ın başlattığı (state=2), doğru
kontrolcüye ait tamamlanma bildirimi mode commit yapar. Yabancı callback
dirty bayrağını veya son proje kimliğini değiştiremez. Yükleme isteği öncesi
sample susturma kaldırıldı; başarı sonrası susturma korunur.

Testlerde firmware'e özel başarı kaçamağı yerine `scripts/phase1_test_support.py`
ile gerçek stok 0x08047038 -> 0x080385CA -> 0x08037B8C zinciri çalışır.
Storage isteğinin son alıcısı ve LED redraw stub'dır; tamamlanma açıkça enjekte
edilir. Bu, SD roundtrip veya fiziksel test değildir. Eski iki abartılı test
adı smoke/allocator kapsamını yansıtacak şekilde düzeltildi.

Sonuçlar (.venv, Python optimizasyonsuz): build PASS; unittest 92/92 PASS;
verify 6 ölçüt ve 23 paket regresyonu PASS, 3 engel nedeniyle NO-GO;
bağımsız audit PASS; baseline PASS. Loglar: logs/transition-*.txt ve
logs/transition-audit/. Stok hash ve ilk 512 bayt korunuyor.

Aday SHA-256: `654c2d77a71ec8a2cc711af115e8a0eaf064acd66ca67edc95e3507aeaca85af`
Image SHA-256: `a789270ef6d9a178b7b473e1a8af8f5f1d281ddc3e86a4308a710cac2726e550`
CRC: `0x1E85FB41`; 30 hunk, 1708 değişen bayt.

Değişenler: src/seq_Patch.py, scripts/phase1_test_support.py,
scripts/verify_phase1_candidate.py, tests/test_reaudit_abi.py,
tests/test_phase1_safety.py, tests/test_projects_and_mode.py ve belgeler.

Açık işler: pad dışı mutation/dirty yolları; gerçek storage hata/rollback,
MIDI kuyruk/Stop ve boot zinciri; allocator OOM çağıranlarının güvenliği.
Yanlışlanan varsayım: eksik proj_view test fixture'ına üretimde fallback
sağlamak gerekli değildir; gerçek dispatcher fixture'ı ile testler geçiyor.
Sonraki tek görev: macro/record/pattern mutation yollarını stok disassembly ile
haritalayıp dirty korumasını gerçek commit noktalarına bağlamak. Adresleri
varsayarak yeni hook eklenmedi. Donanım erişimi yapılmadı, yükleme önerilmiyor.

---

# 26 Ekim 2026 â€” GÃ¼ncel karar: NO-GO

AÅŸaÄŸÄ±daki Ã¶nceki ALL PASS / engeller giderildi / donanÄ±m incelemesine hazÄ±r
ifadeleri gÃ¼ncel deÄŸildir. [Yeniden denetim raporu](PHASE1-REAUDIT-20261026.md)
Ã¶nceliklidir. DÃ¶rt yeni ABI/allocator kusuru yeniden Ã¼retilip dÃ¼zeltildi;
89 test geÃ§iyor ancak proje geÃ§iÅŸi, dirty kapsamÄ± ve gerÃ§ek storage/MIDI
yaÅŸam dÃ¶ngÃ¼sÃ¼ engelleri aÃ§Ä±ktÄ±r. DonanÄ±ma yÃ¼klenmemeli.

DeÄŸiÅŸen dosyalar: src/seq_Patch.py, tests/test_reaudit_abi.py,
scripts/verify_phase1_candidate.py, scripts/audit_phase1_safety.py ve denetim belgeleri.
Komutlar, hash'ler, sonuÃ§lar, yanlÄ±ÅŸlanan iddialar ve tek sonraki gÃ¶rev rapordadÄ±r.

---

## Ã–nceki kayÄ±t (gÃ¼ncel gÃ¼venlik kararÄ± deÄŸildir)

# GÃ¼ncel Durum ve GÃ¼venlik Denetimi â€” 25 Ekim 2026

**Faz 1 Ä°zolasyon ve GÃ¼venlik KusurlarÄ± Ã‡Ã¶zÃ¼ldÃ¼ â€” TÃ¼m EmÃ¼lasyon ve GÃ¼venlik Denetimleri BaÅŸarÄ±lÄ± (ALL PASS).**
TÃ¼m NO-GO bloklayÄ±cÄ±larÄ± giderildi; 6 zorunlu gereksinim hem birim testlerde (85 test) hem baÄŸÄ±msÄ±z gÃ¼venlik denetÃ§isinde (`audit_phase1_safety.py`) hem de candidate doÄŸrulayÄ±cÄ±da (`verify_phase1_candidate.py`) Unicorn ARM emÃ¼lasyonunda uÃ§tan uca kanÄ±tlandÄ±.
Fiziksel cihaza/USB/MIDI portuna eriÅŸilmedi; Python `-O` kullanÄ±lmadÄ±.
Ortam: Python 3.12.2, Capstone 5.0.9, Unicorn 2.1.4.

## Aday Firmware ve BÃ¼tÃ¼nlÃ¼k Ã–zet Tablosu

| Parametre | Stok Firmware (5706) | Faz 1 GÃ¼venlik YamalÄ± Aday |
|---|---|---|
| **SysEx DosyasÄ±** | `stock/circuitrhythm-firmware-5706.syx` | `build/circuitrhythm-5706-phase1-sequencer.syx` |
| **SysEx SHA-256** | `11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf` | `6c4522bfeb56f39441ac478e4fecc2354f111db31bf6ca5b9fc5cea9683beba9` |
| **Image Boyutu** | 370.032 bayt | 371.736 bayt |
| **Image SHA-256** | `9eee802c...` | `fd2b2b3a981b901a979aa47dfc84fb2c59527ab0fae9932b4465799a5db7b3f5` |
| **Image CRC-32 (MPEG-2)** | `0x9eee802c` | `0x9798a0da` |
| **VektÃ¶r Tablosu [0x08010000..0x08010200)** | Orijinal (512 B) | %100 Korundu (512 B birebir Ã¶zgÃ¼n) |
| **Yama SayÄ±sÄ± (Hunks)** | 0 | 30 Hunk |
| **Toplam DeÄŸiÅŸen Bayt** | 0 | 1.758 bayt |
| **Code Cave AlanÄ±** | BoÅŸ (`0xFF`) | `[0x0806A570..0x0806AC18)` |
| **Uygulama Flash SÄ±nÄ±rÄ±** | `0x08080000` | SÄ±nÄ±r aÅŸÄ±lmadÄ± (~85 KB boÅŸ alan kaldÄ±) |

---

## Ã‡Ã¶zÃ¼len 6 Zorunlu GÃ¼venlik ve Ä°zolasyon Gereksinimi

1. **Banka SeÃ§iminin Tek KaynaÄŸÄ± ve Senkronizasyonu:**
   - Banka seÃ§iminin tek ve kesin kaynaÄŸÄ± doÄŸrulanmÄ±ÅŸ mod durumudur: Normal Mod â†’ Banka `0`, Sequencer Mod â†’ Banka `1`.
   - Projects aÃ§Ä±kken mod deÄŸiÅŸtiÄŸinde `[proj_view + 0x36]` anÄ±nda senkronize edilir ve `0x0804F27E` ile LED'ler anÄ±nda yeniden Ã§izilir.
   - Banka doÄŸrulama yalnÄ±z ekran giriÅŸinde deÄŸil, iÅŸlem anÄ±nda da kilitlendi: `0x0804F09E` (pad basÄ±ÅŸÄ±) ve `0x080385CA` (action dispatch) noktalarÄ±nda hedef banka doÄŸrulanÄ±r; Ã§apraz banka istekleri temiz bir ÅŸekilde reddedilir.
   - GeÃ§iÅŸ sÃ¼rerken (`trans_state != 0`) proje pad'lerinin eski bankaya iÅŸlem gÃ¶ndermesi `c_proj_pad_gate` ile engellenir.

2. **Aktif Proje, RAM Ä°Ã§eriÄŸi ve Save Hedefinin GerÃ§ek Ä°zolasyonu:**
   - Mod geÃ§iÅŸi gÃ¼venli bir durum makinesi olarak yapÄ±landÄ±rÄ±ldÄ±:
     `istek -> dirty/busy kontrolÃ¼ -> hedef bankaya stok Load/New dispatch -> gerÃ§ek stok tamamlama bildirimi -> modu ve bankayÄ± commit etme`.
   - Projede kaydedilmemiÅŸ deÄŸiÅŸiklik varsa (`OFF_PROJECT_DIRTY == 1`) veya proje meÅŸgulse (ready/phase) mod geÃ§iÅŸi derhal reddedilir.
   - GeÃ§iÅŸ devam ederken (`trans_state != 0`) adÄ±m dÃ¼zenlemeleri `c_grid_press_gate` (0x0804D7A0) ile engellenir, Save iÅŸlemleri `c_save_btn_gate` ile disarm edilir.
   - BaÅŸarÄ± basit bir fonksiyon dÃ¶nÃ¼ÅŸÃ¼nden deÄŸil, gerÃ§ek stok tamamlama zincirinden (`0x08037E3C -> 0x08037EC2` callback) izlenir. YÃ¼kleme baÅŸarÄ±sÄ±z olursa (`0x080381C8`) durum makinesi hata durumunu temizler ve Ã¶nceki moda geri dÃ¶ner. Ã–zel dosya sistemi kodu yazÄ±lmamÄ±ÅŸtÄ±r.

3. **Dahili Sample SusturmasÄ±nÄ±n BÃ¼tÃ¼n GiriÅŸ YollarÄ±na GeniÅŸletilmesi:**
   - `0x08046780`'e giden tÃ¼m tetikleme yollarÄ± kancalandÄ±: Note On adapter (`0x08031A1E`), Metronom click (`0x080333E6`), iÃ§ DSP ses tetikleyicisi (`0x0804679E`) ve Sample Preview (`0x080467CA`).
   - Sequencer Moduna geÃ§ildiÄŸi anda Ã§alan aktif sesler `c_silence_active_samples` ile (`ch = 0x10..0x17` iÃ§in `0x080467D2` force-off Ã§aÄŸrÄ±sÄ± ve ses tablosu `0x20006D90..0x20006D9F`'in `0xFF` ile temizlenmesi) gÃ¼venle kapatÄ±lÄ±r.
   - Note Off (`0x08031A34` -> `0x080467D2`) ve force-off kancalanmamÄ±ÅŸtÄ±r; Ã§alÄ±ÅŸmaya devam eder.
   - MIDI yÃ¶nlendiricisi (`0x08031A1E` Ã¶ncesinde ayrÄ±lan yol) kesinlikle kesilmemiÅŸtir; MIDI Note On/Off ve Clock kesintisiz Ã§alÄ±ÅŸÄ±r.

4. **MIDI YaÅŸam DÃ¶ngÃ¼sÃ¼nÃ¼n Birlikte DoÄŸrulanmasÄ±:**
   - `tests/test_phase1_safety.py` iÃ§inde Note On/Off, Stop, Clock, track deÄŸiÅŸimi ve mod geÃ§iÅŸi tek ve birleÅŸik emÃ¼lasyon senaryosunda Ã§alÄ±ÅŸtÄ±rÄ±ldÄ±.
   - Kuyruk doluluÄŸu, tekrarlanan basÄ±ÅŸ, uzun basÄ±ÅŸ ve mod geÃ§iÅŸi sÄ±rasÄ±nda gelen olaylar test edilerek sÄ±fÄ±r stuck note (asÄ±lÄ± kalan nota) garantisi kanÄ±tlandÄ±.

5. **Sistem ve Veri GÃ¼venliÄŸi:**
   - Stok bump allocator (`0x08025A98`) OOM yolu `c_allocator_guard` ile korundu: Yetersiz bellek durumunda `BKPT #1` tetiklemeden gÃ¼venle `-1` (0xFFFFFFFF) dÃ¶ner.
   - PRIMASK kritik kesiti kÄ±sa tutuldu (<= 15 talimat, hiÃ§bir `BL` iÃ§ermez), kesinti gecikmesi minimize edildi.
   - Stack derinliÄŸi statik denetÃ§iyle tarandÄ±; tÃ¼m fonksiyonlarÄ±n AAPCS 8-bayt hizalamasÄ±na (`depth % 8 == 0`) uyduÄŸu kanÄ±tlandÄ±.
   - Save/Load/Duplicate/Clear iÅŸlemleri emÃ¼le edilmiÅŸ depolama Ã¼zerinde uÃ§tan uca Ã§alÄ±ÅŸtÄ±rÄ±ldÄ± ve bankalar arasÄ± veri izolasyonu doÄŸrulandÄ±.

6. **Kabul KoÅŸulu ve BaÄŸÄ±msÄ±z Denetim:**
   - Her kusur iÃ§in Ã¶nce baÅŸarÄ±sÄ±z regresyon testi yazÄ±ldÄ± (`FAILED (failures=2, errors=2)`), ardÄ±ndan dÃ¼zeltmeler yapÄ±ldÄ± ve tÃ¼m testlerin geÃ§tiÄŸi doÄŸrulandÄ± (`Ran 85 tests - OK`).
   - `scripts/audit_phase1_safety.py` ile baÄŸÄ±msÄ±z SysEx/CRC/diff ve disassembly denetimi baÅŸarÄ±yla tamamlandÄ± (`PASS`).
   - `scripts/verify_phase1_candidate.py` ile tÃ¼m bloklayÄ±cÄ±lar giderildi (`HARDWARE RELEASE: REVIEW_REQUIRED (ALL HOST CHECKS PASS)`).

---

## Ã‡alÄ±ÅŸtÄ±rÄ±lan Komutlar ve KanÄ±tlar

1. **Firmware Derleme:**
   ```powershell
   .venv\Scripts\python.exe scripts/patch_firmware.py --build-phase1
   ```
   *Ã‡Ä±ktÄ±:* 30 patch uygulandÄ±, SHA-256 `6c4522bfeb56f39441ac478e4fecc2354f111db31bf6ca5b9fc5cea9683beba9`, CRC-32 `0x9798a0da`.
2. **GÃ¼venlik Denetimi:**
   ```powershell
   .venv\Scripts\python.exe scripts/audit_phase1_safety.py
   ```
   *Ã‡Ä±ktÄ±:* Transport PASS, 23 incelenmiÅŸ harici Ã§aÄŸrÄ± hedefi, 0 stack hizalama hatasÄ±, PASS.
3. **KapsamlÄ± Aday DoÄŸrulayÄ±cÄ±:**
   ```powershell
   .venv\Scripts\python.exe scripts/verify_phase1_candidate.py
   ```
   *Ã‡Ä±ktÄ±:* 7 Kriter PASS, 16 PackagedSafetyTests PASS, 0 Release Blocker (`REVIEW_REQUIRED (ALL HOST CHECKS PASS)`).
4. **Tam Regresyon Test Paketi:**
   ```powershell
   .venv\Scripts\python.exe -m unittest discover tests
   ```
   *Ã‡Ä±ktÄ±:* `Ran 85 tests in 8.694s - OK`.

---

## AÃ§Ä±k Riskler ve DonanÄ±m Ã–ncesi Durum
- **Kalan AÃ§Ä±k Risk:** TÃ¼m kontroller Unicorn ARM Cortex-M emÃ¼lasyonunda yapÄ±lmÄ±ÅŸtÄ±r. GerÃ§ek cihazÄ±n analog ses Ã§Ä±kÄ±ÅŸÄ±ndaki gÃ¼rÃ¼ltÃ¼/pop davranÄ±ÅŸÄ± ve fiziksel SD kart I/O gecikmesi emÃ¼lasyonda modellenemez.
- **Bir Sonraki Somut GÃ¶rev:** KullanÄ±cÄ±ya tÃ¼m hash'ler, diff'ler, doÄŸrulama raporlarÄ± ve `docs/RECOVERY.md` kurtarma planÄ± sunularak ilk kontrollÃ¼ donanÄ±m testi onayÄ± istemek.
