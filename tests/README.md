> Güncel31 Ekim /Canlı parametreler — Verifier165/core-only152;13 uzun
> test dışarıda. Yeni komut:scripts/probe_recovery_running_edits.py <out>.
> Native reset/UI canlı mode5/6,iki sayfa,8 track,iki mod;PRNG salt okunur
> ve MIDI Off/player On eşleştirilir. Koşu/sayım STATUS.md'de. Negatif test
> varsayımları firmware hatası diye sayılmaz. Firmware aynı;M7 NO-GO.

---

> Güncel31 Ekim /Gate expiry ve tie — Verifier164/core-only152;12 uzun
> test dışarıda.3 yeni sentetik tie testi80 alt durum içerir. Ayrı native UI
> Gate1/6/95/96 testi doğal Off/Stop'u ayırır;UI tie oluşturma iddiası yoktur.
> Komut:scripts/probe_recovery_gates.py <out>. Güncel koşu/sayım STATUS.md;
> 36 hedefli regresyon paket sayımına tekrar eklenmez. Firmware aynı;M7 NO-GO.

---

> Güncel31 Ekim /64 stok ses Stop — Verifier160/core-only149;11 uzun test
> core-only dışında.149 temel+6 ölçüt ve native IRQ/32-adım regresyonu yeni
> c9a87a9d… adayda PASS. Dört ayrı64-ses senaryosu iki mod × çıkış öncesi/
> sonrası Stop,kapanıştan sonra dirty mod roundtrip/Play–Stop içerir.
> Güncel sayım STATUS.md'de;ortak sentetik timer testi iki kere sayılmaz.
> Yeni komut:scripts/probe_recovery_dense_stop.py <out> <0|1>
> <before-output|after-output>. M7 NO-GO;cihaz erişimi yok.

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

> Güncel29 Ekim (native file queue):45EB6→sync FIFO/wait/2AD40 worker
> yolu8 yerel/8 paket testte PASS;4113A file API RAM sınırı kalır.
> Result credit'ten önce yayımlanır;reset/suspend/nested MSC reader testli.
> Yeni negatif:53E8C short-read hatasını kullanmayıp2046B artık veri yazabilir.
> Fiziksel tekrar/stock patch yok;105 eski kaynak ve firmware aynı.
>518 discovery,tam518 bu oturumda koşulmadı. M7 NO-GO;STATUS ve
> MIDI-USB-FILE-QUEUE-5706.md güncel.

---

> Güncel29 Ekim (uzun sample loop):native53E24/53E8C128 yuva döngüsü,
> dosya/flash/UI/allocator RAM sınırlarıyla10 yeni yerel/10 paket testte PASS.
> Aktif USB okuyucu,worker reentry,semaphore,reset/suspend ve double-buffer
> denetlendi. File-task ömrü/gerçek UI ve main retry/power erişimi açık.
> Önceki101 kaynak/firmware aynı;510 discovery,tam510 bu oturumda koşulmadı.
> Production Off/Stop FAIL,M7 NO-GO. STATUS ve MIDI-USB-LONG-LOOP-5706.md güncel.

---

> Güncel29 Ekim (poll caller):2DE92 ek MSC çağrısının dispatch/adapter /
> callback zinciri ve owner/context kapıları13 yeni yerel/13 paket senaryosunda
> PASS. Worker/IRQ/recursive/factory/clock-stop ve kapanış arası sınırlar testli.
> Callback-only retry/power ilerlemez;native main hâlâ gerekir.53E78 yalnız BL
> kenarı testli,tam53E24 ve43E1C/Packs/RTOS ömrü açık.97 önceki kaynak ve
> firmware/codegen aynı.500 discovery;tüm500 bu oturumda koşulmadı.
> Üretim Off-Stop FAIL,M7 NO-GO. STATUS ve MIDI-USB-POLL-CALLERS-5706.md güncel.

---

> Güncel29 Ekim (factory + debt):Hazırlanmış MAIN/kısmi owned SysEx /
> query ledger borcuyla MIDI-only↔MIDI+MSC geçişi13 yeni yerel ve13 paket
> senaryosunda PASS. Native settings/boot caller,READ iptali,eksik ACK ve
> rebuild içi reset/yeni istek testli. Firmware/93 önceki kaynak/codegen aynı.
> Önceki tam474 PASS korunur;487 toplam discovery,tam487 bu oturumda koşulmadı.
> Tam Packs UI/diğer caller/boot/RAM-init/gerçek timing/integration açık.
> Üretim Off-Stop FAIL,M7 NO-GO. STATUS ve MIDI-USB-FACTORY-DEBT-5706.md güncel.

---

> Güncel29 Ekim (staging):474 toplam/87 aday PASS. Native formatter'ın
> henüz HAL'e kabul edilmemiş MAIN baytları/kısmi owned SysEx cursor'u optional
> carry varyantında uyku/reset boyunca korunur. Reddedilen flush tamponu silmez;
> OPEN poll retained full MAIN'i önce gönderir. Paket adayında27 senaryo PASS.
> Kabul edilmiş TX/raw ALT/parser/held/fault/full boot/RAM-init/integration açık.
> Üretim aynı/Off-Stop FAIL,M7 NO-GO. STATUS ve MIDI-USB-STAGING-5706.md güncel.

---

# Güncel yerel testler — 29 Ekim 2026 / gönderimi başlamamış debt carry

462 PASS;15 yeni test_midi_usb_carry.py. Normal/Sequencer eski debt stall,
sleep/reset/config,360B payload,tekrar epoch,queued Note Off,committed ve
wrapped owed Clock/Stop provenance,ACK yokluğu,retirement/resume reset
yarışları ve owned caller testli. In-flight+debt,partial staging/parser ve
genuine fault eski korumalarda kalır:4 expected-boundary negatifi korunur.
Ek all-port admission/borrowed payload deneyi:9 native notice,tek byte stream.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_usb_carry.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_usb_carry.py logs/usb-carry-20261029/probe
.\.venv\Scripts\python.exe logs/usb-carry-20261029/check_borrowed_debt.py
```

Paket15 PASS,audit/trace PASS;probe exit2/NO-GO. Eski task negatif overlay
olmadan hâlâ geçerlidir. Gerçek bus/host/UART IRQ/timing kanıtı yok;üretim
Off/Stop FAIL. STATUS.md ve MIDI-USB-CARRY-5706.md önceliklidir.

---

# Güncel yerel testler — 28 Ekim 2026 / native main ve worker bağlantısı

447 PASS;13 yeni test_midi_usb_task.py. Native output→input→task sırası /
ABI,manuel service olmadan query/READ/CSW/suspend-wakeup,eksik ACK,nested
worker/task,worker IRQ suspend ve bağlam reddi testli. Gerçek worker loop
648AE..648B8 kullanılır;RTOS wait/return ve bus/flash sınırları sentetik.
Üç zorunlu negatif:main hook yokken power/retry ilerlemez;retained MIDI debt
suspend→wake sonrası64 main geçişinde de toparlanmaz. Sonuncusu çözülmedi.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_usb_task.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_usb_task.py logs/usb-task-20261028/probe
```

Paket13 PASS,audit/trace PASS;exit2/NO-GO beklenir. STATUS.md ve
MIDI-USB-TASK-5706.md güncel. Üretim Off/Stop FAIL ve M7 NO-GO sürer.

---

# Güncel yerel testler — 28 Ekim 2026 / normal USB suspend-wakeup

434 PASS;16 yeni test_midi_usb_power.py. Aktif READ/MIDI borcu/eksik ACK
sırasında clock-stop reddi,erken/coalesced wake/reset,native save içi wake,
MIDI-only query/composite READ,asleep factory erteleme,DIN Off/project RAM,
tekrar suspend,clock-stopped MMIO guard,wrap/LPM/deep-stop/DMA reddi testli.
Korumasız native suspend aktif reader varken clock-stop yapar:beklenen negatif.
Üretim aynı/Off-Stop FAIL,M7 NO-GO. Clock/IRQ/ACK/RTOS/alt flash sentetik.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_usb_power.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_usb_power.py logs/usb-power-20261028/probe-final
```

Paket16 PASS,audit/trace PASS;exit2/NO-GO beklenir. STATUS.md ve
MIDI-USB-POWER-5706.md güncel. Full-tests-final.txt son kaynak sürümünü içerir;
önceki full-tests/probe kayıtları clock-stopped MMIO guard öncesidir.

---

# Güncel yerel testler — 28 Ekim 2026 / native USB factory geçişi

418 PASS;16 yeni test_midi_usb_factory.py. MIDI-only↔MIDI+MSC,descriptor,
MIDI query/storage READ,aktif READ ve admitted MIDI debt bariyeri,latest
generation,geçiş içi yeni istek/reset,native2CB18 ABI,storage modları,DIN Off /
project RAM,IRQ-context ve yanlış HAL binding reddi testli. Korumasız native
factory'nin eski listeyi erken silmesi zorunlu negatifte gösterilir.
HAL init,tick/NVIC/clock ve RTOS/alt flash sınırları sentetik;full boot /
Packs/power/task/physical timing kanıtı yok. Üretim aynı/Off-Stop FAIL,M7 NO-GO.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_usb_factory.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_usb_factory.py logs/usb-factory-20261028/probe
```

Paket probe16 PASS,audit/trace PASS;exit2/NO-GO beklenir. STATUS.md ve
MIDI-USB-FACTORY-5706.md öncelikli;aşağısı tarihsel kayıttır.

---

# Güncel yerel testler — 28 Ekim 2026 / readonly MSC READ10 ve CSW

402 PASS;18 yeni test_midi_usb_storage.py. Native queued READ/drain/worker,
bir/iki blok veri ve CSW,read-error failed CSW/per-job result,worker içinde
reset,tampon/CSW erken reuse reddi,cancel/retry/ACK,DIN Off/MIDI inquiry,
readonly WRITE10 ve bozuk bariyer/stale TX XFRC negatifleri testli.
Alt flash RAM kopyasıdır;RTOS wake/yield modellenir. Media donanımı veya
full boot/scheduler kanıtı değildir. Üretim aynı/Off-Stop FAIL,M7 NO-GO.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_usb_storage.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_usb_storage.py logs/usb-storage-20261028/probe
```

Paket probe18 PASS,exit2/NO-GO beklenir. STATUS.md ve
MIDI-USB-STORAGE-5706.md öncelikli;aşağısı tarihsel kayıttır.

---

# Güncel yerel testler — 28 Ekim 2026 / aktif MSC CBW iptali

384 PASS;21 yeni test_midi_usb_msc.py. Native class Bulk-Only Reset,aktif
CBW deconfig/reconfig,missing ACK/AHB/flush,kısmi CBW ve ortak FIFO,DIN Off /
admitted MIDI debt,CPU-copy publication,native task/submit/teardown reset
yarışları,ticket wrap,CBW overflow guard ve stale XFRC negatifi testli.
Başlamış SCSI/storage/CSW/TX iptali uygulanmadı;kapalıda tutulur. Tüm testler
sentetik RAM/MMIO'da;cihaz API erişimi yok. Üretim aynı/Off-Stop FAIL,M7 NO-GO.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_usb_msc.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_usb_msc.py logs/usb-msc-cancel-20261028/probe-final
```

Paket probe21 PASS;exit2/NO-GO beklenir. MIDI-USB-MSC-5706.md ve STATUS.md
öncelikli;aşağıdaki bölümler tarihseldir.

---

# Güncel yerel testler — 28 Ekim 2026 / gerçek parent ve composite

363 test PASS;16 yeni test_midi_usb_composite.py. Gerçek MIDI parent'ın DIN
Off silmesi negatifi,owned guard ile koruma,iki-class bariyer sonrası native
kurulum/teardown,125B/3-interface descriptor,reset/enum/EP0/inquiry zinciri,
eski USB job iptali,borç varken kapalıda tutma,aktif MSC/pending completion
reddi,parent arası/MSC arm sonrası reset,yanlış caller ve foreign class testli.
Storage Init(LUN0) return0 sınırıdır;MSC veri aktarımı/fiziksel iptal kanıtı yok.
Üretim aynı/Off-Stop FAIL,M7 NO-GO. Paket probe16 PASS,exit2 beklenir.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_usb_composite.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_usb_composite.py logs/usb-composite-20261028/probe-final
```

docs/MIDI-USB-COMPOSITE-5706.md ve STATUS.md güncel;aşağısı tarihseldir.

---

# Güncel yerel testler — 28 Ekim 2026 / native USB kontrol

347 test PASS;22 yeni test_midi_usb_control.py. Native reset/enum/EP0
SET_ADDRESS/SET_CONFIGURATION,direct deinit ve bariyer sonrası class init;
init/commit reset yarışları,single parent notification,bootstrap ayrımı,
global RX flush guard,SOF bypass/MTU64 ve66B kapasitede pause/rearm testli.
Shared payload/RX debt/held nota varsa sahiplik kapalıda korunur.

Parent bildirimi pin'li native no-op sınırıdır. Eski hardware XFRC bariyer
ihlali sonrası yenisinden ayırt edilemez;negatif test korunur. Suspend/wakeup /
DMA,full MSC/descriptor/parent/task ve gerçek bariyer/NVIC/cache/timing açık.
Paket probe22 PASS,exit2/NO-GO beklenir;üretim aynı/Off-Stop FAIL.
docs/MIDI-USB-CONTROL-5706.md ve logs/usb-control-20261028/probe/report.json.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_usb_control.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_usb_control.py logs/usb-control-20261028/probe
```

Aşağıdaki bölümler önceki deney kayıtlarıdır.

---

# Güncel yerel testler — 28 Ekim 2026 / native USB IRQ

325 test PASS;19 yeni test_midi_usb_irq.py. Gerçek stok HAL submit/FIFO/IRQ /
callback zinciri native yürür;test completion token'ı vermez. Coalesced OUT /
RXFLVL,çok kayıtlı FIFO'nun birden fazla IRQ'da boşalması,aynı anda RX/TX,
IRQ dışı/yanlış LR/nested claim reddi,close sırasında CPU drain,epoch discard,
foreign endpoint/handle,partial native init ve fail-closed lifecycle testli.

Zorunlu negatif:iptal bariyeri ihlal edilip eski donanım XFRC'si yeni RX
kurulduktan sonra gelirse yeni job gibi görünebilir. Bridge hardware
generation tag'i değildir. Reset/kontrol IRQ/DMA unsupported;gerçek NVIC /
cache/barrier/timing kanıtı yok. Paket probe19 PASS,exit2/NO-GO beklenir.
Üretim aynı/Off-Stop FAIL. docs/MIDI-USB-IRQ-5706.md ve
logs/usb-irq-20261028/probe/report.json.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_usb_irq.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_usb_irq.py logs/usb-irq-20261028/probe
```

Aşağıdaki bölümler önceki deney kayıtlarıdır.

---

# Güncel yerel testler — 28 Ekim 2026

306 test PASS;25 yeni USB session testi. test_midi_usb_session.py eski TX
iptalini,immutable epoch/ticket,eski/duplicate/nested completion reddini,
RX byte count sınırını,endpoint ACK/AHB/shared RX/flush beklemesini,resume
revalidation,driver identity,DIN devamı ve borç/held/Off sahipliğinin close
reddiyle korunmasını sınar. Native timer var/yok ve foreign callback yolu da
korunur. Model dışında eski DMA'nın reused buffer'a yazabildiği negatif test
özellikle vardır;tagged callback reddi bu yazıyı geri alamaz.

Packaged probe25 PASS;yalnız emülasyon overlay'leri,üretim entegrasyonu yok.
Raw stok callback uyumu FAIL;native IRQ job bridge ve gerçek DMA bariyeri
NOT_ESTABLISHED. Probe exit2/NO-GO beklenir. Ayrıntı:
docs/MIDI-USB-SESSION-5706.md,logs/usb-session-20261028/probe/report.json.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_usb_session.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_usb_session.py logs/usb-session-20261028/probe
```

Aşağıdaki bölümler önceki deney kayıtlarıdır.

---

# Yerel testler

Güncel28 Ekim:281 test PASS;19 yeni RX lifecycle testi.
test_midi_usb_lifecycle.py registered reader/writer/reset/rearm guard'ları,
quiescent close/resume/epoch,partial/held sahiplik,producer/reset interleave,
native disconnect callback ve1057B stock constructor prefix'ini sınar.
Aktif TX endpoint retry slotunu aşabilir:reconnect'te eski yanıt teslimi
gerekli negatif kontroldür. Tam RX/TX session cancellation çözülmüş değildir.
Probe19 PASS,quiescent reset/gates PASS,TX session FAIL,late RX DMA
NOT_ESTABLISHED;production uyumu FAIL,exit2/NO-GO. Ayrıntı:
docs/MIDI-USB-LIFECYCLE-5706.md,logs/usb-lifecycle-20261027/probe.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_usb_lifecycle.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_usb_lifecycle.py logs/usb-lifecycle-20261027/probe
```

Önceki27 Ekim:262 test PASS;18 yeni native RX ledger testi.
test_midi_usb_ledger.py,dolu inquiry counter'ı arkasındaki kabul edilmiş
Clock/Stop/nota sırası ve borç sahipliğini sınar. Partial publication,
producer-during-consumer snapshot,forged marker/header-only yazı,wrap,
native USB-DIN output ve64 Off/Stop testlidir. Native ring dışında henüz
kabul edilmemiş veriye latency garantisi verilmez.2048B stres157912 komut,
500000 açık test bütçesi;gerçek cycle/latency kanıtı değildir.
Probe18 PASS,admitted-window service/order PASS;host/IRQ lifecycle
NOT_ESTABLISHED,production uyumu FAIL,exit2/NO-GO. Ayrıntı:
docs/MIDI-USB-LEDGER-5706.md,logs/usb-inquiry-ledger-20261027/probe.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_usb_ledger.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_usb_ledger.py logs/usb-inquiry-ledger-20261027/probe
```

Önceki27 Ekim:244 test PASS;14 yeni ordered USB admission testi.
test_midi_usb_order.py gerçek note receiver/sahiplik,On/Stop ve running status
sırası;96 permütasyon/parçalama;24 karma native karşılaştırma;kapasite/cursor,
reentry/magic/invalid count;native USB-DIN output stall ve64 Off/Stop'u sınar.
İki inquiry'den sonra queued realtime ilerler;tam8 pending+9. inquiry arkasında
gecikme negatif kontroldür. Eski17 test ve iki eski negatif kontrol değişmedi.
Yeni probe14 PASS,order PASS,full latency FAIL,üretim uyumu FAIL,exit2/NO-GO.
Ayrıntı:docs/MIDI-USB-ORDER-5706.md,logs/usb-inquiry-order-20261027/probe.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_usb_order.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_usb_order.py logs/usb-inquiry-order-20261027/probe
```

Önceki27 Ekim:230 test PASS;17 yeni USB inquiry/cursor testi.
test_midi_usb_inquiry.py host resend olmadan retry,owned RX buffer,split/wrap,
native USB/DIN output stall,tam baytlar,reentry/ABI ve64 Off/Stop'u sınar.
İki gerekli negatif kontrol:sonraki queued buffer'da Clock/Stop beklemesi ve
deferred Note On/Stop sıra değişimi. Bunların testte doğrulanması GO değildir.
Probe gerçek paket üzerine emulator overlay ile17 PASS;iki kriter FAIL,
DIN input NOT_IMPLEMENTED,production_integrated=false,exit2/NO-GO.
Üretim87 regresyon/6 kriter PASS;Off/Stop probe FAIL. Ayrıntı:
docs/MIDI-USB-INQUIRY-RETRY-5706.md,logs/usb-inquiry-retry-20261027/probe-final.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_usb_inquiry.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_usb_inquiry.py logs/usb-inquiry-retry-20261027/probe-final
```

Önceki27 Ekim:213 test PASS;11 yeni üst formatter rezervasyon testi.
test_midi_sysex_request_reservation.py,beş gerçek upper çağrıda kaynak/stack
argümanı/dönüş koruması;full/nested/context/fault;native USB-DIN120B stall ve
explicit retry'yi sınar. Native USB/DIN consumed-request retry negatif kontrolü
FAIL kalır;açık resend17B yanıt pozitif kontrolüdür. Probe gerçek paket üzerine
yalnız Unicorn overlay ile11 testi tekrar koşar;production_integrated=false,
production_caller_compatibility FAIL,NO-GO/exit2. Önceki24/14/11 deneysel ve
87 aday regresyonu/6 kriter PASS;üretim Off/Stop FAIL.
Ayrıntı:docs/MIDI-SYSEX-REQUEST-5706.md,logs/recovery-sysex-request-20261027.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_sysex_request_reservation.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_sysex_request_reservation.py logs/recovery-sysex-request-20261027/probe-final
```

Önceki27 Ekim:202 test PASS;24 recovery+14 retry+11 kabul bildirimi deneyi.
test_midi_sysex_notification.py native scatter-load/vtable ve senkron kabul
callback'ini;owner/event snapshot,12 caller eşleşmesi,partial admission,
callback içinde reader bitişi/reentry ve USB-DIN360B stall'ı sınar.
Eski bildirim kapalı varyant aynı kod/hash ile korunur;eksik callback ve
full-slot yanıt kaybı negatif kontrollerdir. Yeni probe native kabul bildirimi
PASS,production_caller_compatibility FAIL,wire-completion NOT_ESTABLISHED,
production_integrated=false ve NO-GO/exit2 verir. Üretim87 regresyon/6 kriter
PASS;Off/Stop FAIL. Ayrıntı:docs/MIDI-SYSEX-NOTIFICATION-5706.md ve
logs/recovery-sysex-completion-20261027.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_sysex_notification.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_sysex_notification.py logs/recovery-sysex-completion-20261027/probe
```

Önceki27 Ekim:191 test PASS;24 recovery +14 ayrı SysEx retry deneyi. Yeni
test_midi_sysex_retry_prototype.py,12 native caller dönüş/kaynak ömrü,
tek360B sahipli kopya, kısmi fanout/port retry, USB-DIN stall/nested çağrı,
erken formatter/global callback guard'ı ve CFG/ABI/PRIMASK sınırlarını sınar.
Korumasız source/callback ezilmesi ve full-slot yanıt kaybı negatif kontrol
olarak kalır. Test PASS'i native completion uyumluluğu veya üretim GO değildir.
Yeni probe paket üzerine yalnız Unicorn overlay ile14 testi tekrar koşar:
owned_payload_and_port_retry=PASS, native_completion_callback_contract=
NOT_IMPLEMENTED, ignored_full_queue_response_delivery=FAIL,
production_caller_compatibility=FAIL, production_integrated=false ve NO-GO/exit2.
Üretim87 regresyon/6 kriter PASS; Off/Stop FAIL. Güncel kaynak:
docs/MIDI-SYSEX-RETRY-PROTOTYPE-5706.md, logs/recovery-sysex-retry-20261027.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_sysex_retry_prototype.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_sysex_retry_prototype.py logs/recovery-sysex-retry-20261027/probe
```

Önceki27 Ekim:177 test PASS;24'ü izole recovery/SysEx deneyidir. Üretim adayı
aynı;87 aday regresyonu/6 kriter PASS, Off/Stop probe'ları FAIL/NO-GO exit2.
Yeni11 test; SysEx baytları/pointer ömrü, native USB/DIN stall, nested çağrı,
ortak router tamponu, kapasite/ABI/PRIMASK ve kısmi fanout. Eski bypass ve
native sonsuz-bekleme negatif kontrolleri kaldırılmadı. Probe paketlenmiş
imaj üzerine yalnız Unicorn overlay ile24 testi tekrar koşar:
tested_sysex_quarantine=PASS, all_producer_quarantine=REVIEW_REQUIRED,
production_integrated=false,hardware_release=NO-GO ve exit2. Busy ret/retry
politikası stok çağıranlarda tamamlanmadı. logs/recovery-sysex-20261027 ve
MIDI-RECOVERY-PROTOTYPE-5706.md günceldir; aşağıdaki kayıtlar tarihseldir.

Önceki27 Ekim:166 test PASS; bunun13'ü test_midi_recovery_prototype.py içindeki
izole Thumb deneyidir. --build-phase1 bu kodu içermez. Paket verifier'ı87 aday
regresyonunu çalıştırır; mevcut aday Off/Stop probe'ları FAIL/exit2 kalır.
Deneysel prototype probe da SysEx bypass/üretim engelleri nedeniyle exit2
verir; JSON'da tested_off_stop_recovery=PASS, all_producer_quarantine=FAIL,
production_integrated=false ve hardware_release=NO-GO ayrı alanlardır.
MIDI-RECOVERY-PROTOTYPE-5706.md güncel kapsamdır; aşağıdaki sayılar tarihseldir.

Güncel27 Ekim:153 test/87 packaged regresyon PASS. test_sequencer_playback.py
gerçek player/voice/Stop zincirini kapsar;9 yeni test vardır. Karakterizasyon
testi PASS, teslim güvenliği PASS demek değildir: probe_sequencer_stop.py
63/64 nota ve tek USB F8+FC sınırında Off/Stop kaybını FAIL/exit1 verir.
Verifier aynı probe'u paketlenmiş imajda çalıştırıp NO-GO/exit2 tutar.
SEQUENCER-PLAYBACK-5706.md güncel kanıt/sınırdır; aşağıdakiler tarihsel sayılardır.

Güncel27 Ekim:144 test/78 packaged regresyon PASS. test_midi_tx_fault.py ve
test_native_midi_drivers.py overflow sonrası mode kilidi, gerçek USB/DIN
formatlama ve availability yollarını sınar. Off/Stop delivery negatif probe'ları
FAIL kalır; bu containment'tır. Verifier CRITICAL_RUNTIME_PROBE_FAILED / NO-GO.
MIDI-TX-FAULT-5706.md güncel kanıttır; aşağıdaki sayılar önceki alt çalışmalardır.

Güncel:136 test/70 packaged regresyon PASS. test_midi_task_schedule.py gerçek
25870..2587C sırasıyla stok kontrolü ve yeni USB buffer yield'ını sınar.
probe_midi_task.py hazır sürücüde Stop PASS, stalled sürücüde FAIL verir;
probe_midi_output_queue.py dolu FIFO Off kaybı FAIL'i korur. Verifier kararı
CRITICAL_RUNTIME_PROBE_FAILED / NO-GO. MIDI-USB-YIELD-5706.md güncel kanıttır;
aşağıdaki test sayıları önceki alt çalışmaların kayıtlarıdır.

26 Ekim 2026: güncel kapsam ortak projedir. `test_shared_project.py`, aynı
projede sıfır dosya erişimiyle mod geçişini ve stok64 slot yönlendirmesini
doğrular. Kaldırılan banka/otomatik Load/dirty-tracker sözleşmelerinin tam
test kaynakları `analysis/historical-bank-isolation/` altında korunur.
Kullanıcı test geçişini açıkça onayladı; snapshot hash'leri ve39 arşivlenen
metot `approved-test-migration.json` içinde kayıtlıdır. Test skip edilmez.
Pattern/MIDI canary, ABI, heap ve grid güvenlik testleri güncel pakette kalır.

Tam paket:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/verify_phase1_candidate.py
```

Verifier'da host testlerinin geçmesi fiziksel GO anlamına gelmez; açık yayın
engelleri varsa araç2 koduyla çıkar ve raporda NO-GO yazar.

Güncel:128 test ve62 packaged regresyon PASS. Yeni test_midi_output_transport.py
native adapter/FIFO/worker ve clock backend'i çalıştırır. Dolu stok64 slotta Off
kaybını karakterize eden testin geçmesi güvenlik kabulü değildir. Ayrı
scripts/probe_midi_output_queue.py paketlenmiş adayda bu kaybı FAIL/exit1 olarak
raporlar; verifier CRITICAL_RUNTIME_PROBE_FAILED / NO-GO verir. Final driver,
timer/tempo/GPIO sınırları ve canlı scheduler erişilebilirliği ayrıca açıktır.
MIDI-OUTPUT-TRANSPORT-5706.md güncel kapsamı açıklar; aşağıdaki120/54 öncekidir.

Proje kökünde, `-O` kullanmadan:

```powershell
.\.venv\Scripts\python.exe scripts/run_baseline.py
.\.venv\Scripts\python.exe scripts/run_ui_audit.py
```

Baseline tarihsel sonuçları tekrar üretir. UI audit, `test_ui_contracts.py` testlerini ve stock disassembly pencerelerini yeni bir `logs/ui-audit-*` klasörüne kaydeder.
Tek test: `.\.venv\Scripts\python.exe tests/test_ui_contracts.py Contracts.test_toggle_commit_and_led_observer`.

Testler stock makine kodunu sentetik RAM'de çalıştırır; dispatcher testindeki son callback'ler sahtedir.
Cihaz boot edilmez; fiziksel MIDI/USB/pad/LED erişimi yoktur. Uçtan uca cihaz doğrulaması veya firmware build'i değildir.
Kapsam: [UI-TRACE-5706.md](../docs/UI-TRACE-5706.md).

Güncel bağımsız deney: python scripts/probe_shared_project.py. Eski
probe_project_alias.py tarihsel kaynakla çalıştırılmalıdır: python
scripts/run_historical_alias_probe.py; bu karşı deney exit1 ile beklenen
bozulmayı raporlar. Güncel adayın hata geçişi olarak sayılmaz.

MIDI mode ownership: test_midi_mode_ownership.py içindeki12 test gerçek kısa
mesaj decoder/receiver/recorder graphını controller ile birleştirir.
test_midi_ingress_transport.py içindeki7 test gerçek parser kurucusu/DIN byte
parser/USB yazılım FIFO'sunu ekler. Start/Continue/Stop store yazıları,8-track
Start reset ve normal Clock32BB6 pending/callback dalı da gerçektir.
120 toplam test geçer;54 alt-küme testi packaged imajda tekrar çalışır.
Son sequencer/driver/Clock alıcıları stub; ISR/DMA, özel timer dalı, listener ve
output queue/scheduler kanıtı değildir. MIDI-INGRESS-TRANSPORT-5706.md ayrıntılıdır.
