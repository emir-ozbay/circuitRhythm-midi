> Güncel 1 Kasım / Taint sonrası Load–New — İki modda native UI erişimi sınandı.
> Projects açılır; controller flags bit1 ve ayrıca dispatcher phase2 Load/New'ü
> engeller. Tanısal tam backend yükleme ve sonraki UI Load/New taint'i temizlemez.
> Bu bir kullanıcı kurtarma yolu değildir. Firmware272a8128… aynı; M7 NO-GO.
> Güncel sayım ve tek sonraki iş STATUS.md'de; ayrıntı
> [MIDI-RECOVERY-LOAD-REENTRY-5706.md](MIDI-RECOVERY-LOAD-REENTRY-5706.md).
> Alt bölümler tarihsel sonuçlardır.

---

> Güncel1 Kasım /Load short-read — Stock köprünün hata4'ü başarı apply'ına
> çevirmesi native reset/file worker ile yeniden üretildi. Yeni guard yanlış
> başarıyı atlar,native Close ve kalıcı taint ile mod geçişini kapatır. Raw alias
> rollback/toparlanma çözülmedi. Yeni aday272a8128… /CRC985753F7;M7 NO-GO.
> Güncel sayım ve tek sonraki görev STATUS.md'de;ayrıntı
> [MIDI-RECOVERY-LOAD-SHORT-READ-5706.md](MIDI-RECOVERY-LOAD-SHORT-READ-5706.md).
> Alt bölümler tarihsel sonuçlardır.

---

> Güncel31 Ekim /Canlı parametreler — Mode5/6 canlı held/no-held/reserved
> girişleri,mask33/5/16,probability3/7/0 ve silme/yeniden oluşturma ayrı testte.
> Native hazırlık batch'i koordinatla eşleşir;PRNG salt okunur,aktif player
> pitch'ine erken MIDI Off denetlenir. Sonuç/sayım STATUS.md'de. M7 NO-GO;
> üretim c9a87a9d… aynı. Native UI/Load tie-bit erişimi ayrı açık kanıttır.

---

> Güncel31 Ekim /Gate expiry ve tie — Native UI Gate süreleri1/6/95/96
> ve0/15/16/31 adım sınırları ayrı testtedir. Byte6 bit0 tie için3 sentetik
> test/80 alt durum PASS;bu bitin UI/Load'dan oluşturulduğu iddia edilmez.
> Native sonuçlar STATUS.md veMIDI-RECOVERY-GATE-TIE-5706.md'de. Üretim
> c9a87a9d… aynı;M7 NO-GO;cihaz erişimi yok.

---

> Güncel31 Ekim /64 stok ses Stop — UI'de8 ayrı pitch/gate96 kurularak
> 8 gerçek player ×8 stok gate slotu doğal biçimde doldu. Stop64 Off+FC
> taşmasındaki gereksiz kilit düzeltildi;sonraki dirty mod geçişi/Play–Stop
> native kodda sınanır. Yeni aday c9a87a9d…;ayrıntılı senaryolar STATUS.md
> veMIDI-RECOVERY-DENSE-STOP-5706.md'de. M7 NO-GO;cihaz erişimi yok.
> Alt raporlar eski SHA'lara aittir.

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

## 29 Ekim 2026 — Ek MSC poll caller ve transfer callback zinciri

D+E:27624 direct caller'ları2587C,2DE92,53E78.273A8→2DE9A callback8B,
vtable69628[0]=25653,function2DE91;43B2C view+48'e bağlar.43FA0..43FAC
dispatch→25652 adapter→2DE90→27624;callback daima0 döner.0 ilerleme kanıtı değil.

Sentetik binding/native dispatch slice ile Normal/Sequencer READ/data/CSW ve
worker/IRQ/masked/recursive/factory/asleep/kapanış arası owner13 senaryoda PASS;
pakette13 PASS. Native poll sayısı2762A continuation'dan ölçülür;enjeksiyonun
2EF5A girişini tekrar ziyaret etmesi ikinci poll değildir. Callback-only
deferred MIDI/power ilerlemez. Tam43E1C/view ömrü/main erişimi açık.
53E78 tek BL leaf testlidir;tam53E24 loop/storage owner sonraki hedeftir.
97 önceki kaynak/firmware/codegen aynı;M7 NO-GO,üretim Off/Stop FAIL.

---

## 29 Ekim 2026 — Retained MAIN ile native factory ve iki direct caller

D+E:mevcut staging carry ile native432A8/class list değişimi,eski MIDI/MSC
reader'lar retire olduktan sonra yürür. MAIN/cursor/slot/ledger değişmeden
host reset/address/configuration bekler;sonra tek USB/DIN byte stream tamamlanır.
35814→3FC58 slot2 bit17:0→1,1→101. View/store sentetik,callback/dallar native.
2CB18→43286→low-byte argument→432A8 de gerçek wrapper üzerinden testli.
Tam Packs ekranı/proje akışı çalıştırılmış değildir.

13 yeni yerel/13 paket PASS. Native factory içi reset IRQ ve ikinci istek için
önceki71000 test trampoline'ine dokunmadan checked71100 test alanı kullanılır.
93 önceki kaynak/üretim/codegen aynı;önceki474 tam PASS yeniden koşulmadı.
Staging1680B/128B state/toplam2712B synthetic;yerel SP/BL/mask audit aynı.
Sonraki iş2DE92→27624 event caller'ının owner/reentry grafiği.53E78 de açık.
Üretim Off/Stop FAIL,M7 NO-GO;PHY/RTOS/flash/UART timing model sınırıdır.

---

## 29 Ekim 2026 — Native format/flush arası IRQ ve MAIN sahipliği

D+E:402FC borrowed SysEx cursor'unu ilerletir;2B460 MAIN'e4B event yazar.
2B498 raw2B3BC üzerinden26880'i çağırıp2B4AE'de MAIN length'i koşulsuz siler;
raw adapter1 döndürdüğünden ss_tx_arm ret1 reddi görünmez. IRQ close bu araya
girince64B hazırlanmış veri hiç submit edilmeden kaybolur:negatifte pin'li.

Yeni optional staging varyantı registered CPU MAIN flush'ında native26880'i
doğrudan kullanır;TX_TICKET değişimi tüketim sınırıdır. Reddedilen submit'te
tampon tutulur. Dolu MAIN ile402FC baştan döndüğünden OPEN rp_poll ön-flush
yapar. Partial cursor yalnız USB-accepted owned retry payload'una bağlanır.
3 maskeli bölüm/max30/SP0/BL8;1680B kod/128B mevcut state/toplam2712B arena.
12 yeni/474 toplam ve paket27 senaryo PASS;native trace/IRQ stream,sentetik
bus/RTOS/PHY/UART sınırı. Üretim aynı/Off-Stop FAIL,M7 NO-GO.

---

## 29 Ekim 2026 — Logical debt carry ve fiziksel reader retirement

D+E:eski ss_step seal'i401AC ile USB yazılım kuyruğunu/borrowed counter'ı,
native staging'i vecl_reset ile RX FIFO/parser/ledger'ı sıfırlar. Bu nedenle
ss_quiet logical debt0 ister;FROZEN consumer debt'i boşaltamaz. Yeni carry
katmanı software nesneleri korur,yalnız HAL transfer objelerini/RX job'ı tam
barrier sonrasında retire eder;physical epoch artar,logical provenance kalır.

Admission:TX_ACTIVE0;driver+12hex count0,+14hex mode0;MAIN/ALT length0,
selected MAIN;port cursor0 veya cursor==total. Parser/held input idle,
producer/worker busy0,USB RP fault0 zorunlu. Native2B3CE ready,planned state4
için0 döndürür. Eski rp_poll SEEN1 ile bunu FAULT'a çeviriyordu;owned
carry CLOSING..SEALED aralığında registered USB poll bekletilir. Genuine
fault veya OPEN normal yol korunur. Native401AC/2B408/2B498 byte pin'leri var.

SS seal BUSY store'undan önce10B detour;ayrı CY BUSY,nested ss_step gate'i
ve generation karşılaştırması native reset IRQ'yu reddetmeden retirement'ı
korur. Resume yalnız pin'li ss_resume caller LR'ından;eski generation açılmaz.
6 overlay(5 generated+main4B);1300B0807CC00..0807D114,128B20048520..200485A0;
toplam2712B sentetik.3 maskeli bölüm/max30 komut/call-loop yok;SP0/BL8.

15 yeni/462 toplam/87 aday PASS;model IRQ completion stream karşılaştırılır,
fiziksel receiver kanıtı değil. All-port admission notice9 ve borrowed
pointer/cursor korunması ek deneyde PASS. Native PHY/ACK/RTOS/flash/UART
drain sınırdır. MIDI-USB-CARRY-5706.md ve logs/usb-carry-20261029/probe.
Üretim aynı/Off-Stop FAIL,M7 NO-GO.

---

## 28 Ekim 2026 — Gerçek main USB slot'u ve native worker çağıranı

D+E:25870 global20006F04→297DE output,25878→29ABC USB/DIN input,
2587C→27624 MSC sırası. Yeni4B BL gate yalnız2587C'de;sr_service ardından
pw_service ve koşullu27624 yürür. IRQ/PRIMASK/reentry/active IO-task-class
owner varken task body çalışmaz. Yerel SP0/BL8/max16B frame;mask/loop yok.

27624 diğer direct caller'ları2DE92 event callback ve53E78 native loop;
bağlam/owner grafikleri kanıtlanmadığı için değişmedi. Gerçek worker çağrıları
648A6/648B0. Backend20006E60 için READ drain→24138 model task switch→native
648AE..648B8 döngüsü→2C278 yürür. Worker wait/return explicit boundary;
host ready/drain bayrağını zorla temizlemez. Tam RTOS scheduler kanıtı yok.

13 yeni/447 toplam/87 aday PASS. Main-only query,READ/CSW,borçsuz power,
ACK eksikliği,nested worker/task ve worker IRQ suspend testli. Eski main
no-hook negatifleri servis erişimsizliğini gösterir. Retained ledger debt
FROZEN cl_poll nedeniyle aktarılamaz;ss_quiet debt/TX boşalmasını bekler.
Wake dahil64 canlı main geçişi de bu çevrimi çözmez:beklenen açık FAIL.
352B0807C800..0807C960;64B20048420..20048460;toplam2584B sentetik.
MIDI-USB-TASK-5706.md/logs/usb-task-20261028/probe;üretim aynı/M7 NO-GO.

---

## 28 Ekim 2026 — Normal USB suspend/wakeup ve clock-stop sırası

D+E:IRQ4293E bit31 wake'i bit11 suspend'den önce işler. Bit11+DSTS808 bit0
42CD0→2C7E6→4279E ile controller+274'ü+275'e kaydeder,+274=4 yapar;ardından
USB+E00 bit0'ı okuyucuları beklemeden set eder. Aktif READ reader ile bu
native yolun clock-stop yapması zorunlu negatifte gösterildi.
Wake42CB0→2C802→427AE önceki state'i doğrudan yükler.2C9F8(handle,0) önce
USB+E00 bit0'ı temizleyip427AE'ye gider;handle+20hex=0 için kullanılır.

Yeni IRQ preflight completion claim'lerinden önce common request ile dondurur.
Ana servis MC/SS SEALED bekler;native4279E sonrası generation atomik kontrol
edilerek yalnız wake/reset maskesi ve DSB sonrası clock-stop yapılır. Native
state-save içi wake varsa stop yapılmaz. Wake önce native ungate/mask restore,
sonra native IRQ ve kontrollü class init yapar. Reset configuration replay'i
engeller. Asleep sırasında factory/native service ve normal USB MMIO yoktur.

1176B kod0807C000..0807C498;96B state20048320..20048380;toplam2520B sentetik.
3 yeni maskeli bölüm,max30 komut,call-loop yok;SP0/BL8/max24B local frame.
16 yeni/434 toplam/87 aday PASS. Normal suspend11/wake31 CPU-FIFO kapsamı;
LPM27/deep stop/DMA kapalı hata. Native çağrılar gerçek,clock/MMIO/IRQ/ACK /
RTOS/flash modeli gerçek PHY wake veya latency kanıtı değil. Üretim aynı /
M7 NO-GO. MIDI-USB-POWER-5706.md ve logs/usb-power-20261028/probe-final.

---

## 28 Ekim 2026 — Native USB factory ve eski class listesinin ömrü

D+E:40A40 ROOT+8..+14 pointer'larını,40A44 class sayısını temizler;ancak
sonra40A48→40B44→40B7E deinit çağrılır. Native factory'yi doğrudan çağıran
negatif testte eski READ TX reader aktif kalır,MSC parent deinit edilmez.
Yeni432A8 gate isteği saklar;MC/SS SEALED ve eski parent deinit sonrası
native432A8→40A30(stop/init)→40AFE(class add)→40B1C(descriptor/start) yürür.
Native ROOT200000D0,MIDI200000F0,MSC200000FC,HAL200054B4 kullanılır.

Direct432A8 çağrıları2CB2E ve35838;ikincisinin sabitleri1/101.2CB18 yalnız
iki stack byte'ı yazar,word yükler;üst16 bit stok gibi yok sayılmalıdır.
101/201/301 storage mode1/3/2 üretir. MIDI-only94B/2-interface ve composite
125B/3-interface descriptor gerçektir. Yeniden enumeration USBRST gerektirir.
İç40B51 deinit yalnız RUNNING/main/root/controller bağında native'e geçirilir;
harici reset/new generation saklanır.16 yeni/418 toplam/87 aday PASS.

732B factory,128B state,toplam2424B sentetik. HAL427FC return0 sınırı;
native2C82A prefix,43196/43158 FIFO setup,stop/start ve3/200ms wait kodu
sentetik24068 tick(+4) ile yürür. NVIC/clock memory gerçek IRQ/timing kanıtı
değildir. Audit2 maskeli bölüm/max11 komut,call-loop yok;SP0/BL8/max32B local.
Tam Packs UI/project/power/task/boot/RAM/init açık. Üretim aynı/M7 NO-GO.
MIDI-USB-FACTORY-5706.md ve logs/usb-factory-20261028/probe güncel.

---

## 28 Ekim 2026 — Stok readonly MSC ve per-read worker sonucu

D+E:statik initializer200038AC→20003888 tablosunu kurar.650E8 write-protect1;
WRITE10 DATA PROTECT alır,65194 çağrılmaz.43264 mod1/2/3 yalnız range seçer.
READ458D0→65128→2C394→2C1CC→2C23A drain→2C278 worker→2C328 sonuç→USB IN82.
65128 backend hatasını0'a çevirebilir;ilgili4KB read sonucu2C328'de ayrı
yakalanır,sonraki başarılı işin ortak last-status'ı bunu örtemez. Başarı
datası yerine failure CSW gönderilir. Data40024000/4096B veCSW20006DD4/13B
reader sahipliği korunur;MSC policy/finalize hook'ları bariyere bağlar.
1452B/128B ek,toplam2296B state;18 yeni/402 toplam/87 aday PASS. Alt flash
RAM kopyası,RTOS wake/yield sınırdır;gerçek flash/scheduler kanıtı yok.
Üretim aynı/M7 NO-GO. MIDI-USB-STORAGE-5706.md ve
logs/usb-storage-20261028/probe/{audit,stock-contract}.

---

## 28 Ekim 2026 — MSC CBW reset, task ve CPU FIFO

D+E:661F8/6624E→2EFF8 eski OUT2'yi beklemeden state sıfırlayıp31B CBW arm
yapar.52EDC close disable ACK beklemez.27624 ready counter tüketip2F014 /
2F04A→458D0 SCSI dispatch çağırır. Yeni2924B/256B katman bu yolları ortak
disable/ACK/AHB/shared FIFO/TX FIFO2 bariyerine bağlar;native teardown/reset
sonra yürür.26988→23CEA counter kapasite+29'a bakar;ready+28 byte clear olmalı.
531CC word-copy CBW bounds guard;bad<=64B private scratch drain/fail-closed.
21 yeni/384 toplam/87 aday PASS.4 ek maskeli bölüm,max29 komut/call-loop yok.
Başlamış SCSI/data/CSW/IN iptali çözülmedi;kapalıda koruma var. Hardware
generation tag'i yok;bozuk bariyer sonrası stale XFRC negatif kalır.
Üretim aynı/M7 NO-GO. MIDI-USB-MSC-5706.md ve
logs/usb-msc-cancel-20261028/probe-final/{audit,stock-contract}.

---

## 28 Ekim 2026 — Gerçek parent, composite ve statik initializer

D+E:68A54 statik initializer walker,6668C endpoint constructor'ını yürütür.
Native root200000D0,MIDI200000F0→80676F4/68A2C,MSC200000FC→8067730/661DC.
MIDI parent68A2C→297C0 tüm çıkış clear→29AB0 rearm:bekleyen DIN Off silinir.
996B/96B composite katmanı40B5A listesini bariyer sonrasına erteler;yalnız
owned sealed68A37 caller clear'ı atlar. MSC OUT2 global RX flush guard'ı,
native selected IN82 flush ve661DC→2F00C→2EFC8 BOT reset/31B CBW arm testli.
Yalnız storage Init(LUN0) callback'i native return0 sınırıdır.40A78,200067E0
buffer'ında125B/3-interface descriptor kurar;native iki-class deinit yürür.
16 yeni/363 toplam/87 aday PASS. Aktif MSC cancel/drain,class-specific /
power/task/full boot ve gerçek bariyer açık;üretim aynı,M7 NO-GO.
logs/usb-composite-20261028/probe-final/{audit,stock-contract};
MIDI-USB-COMPOSITE-5706.md ve STATUS.md öncelikli.

---

## 28 Ekim 2026 — Native EP0/class lifecycle ve SOF yan yolu

D+E:4293E→2C78C→425A8→44DD8→42584/4259A→2AB08/2AB14→40B5A/40B7E→
525B2/5261C. Native reset/enum/SET_ADDRESS/SET_CONFIGURATION yürür.1464B /
96B kontrol katmanı init'i bariyer sonrasına erteler;525FE availability release
wire completion değildir.525C6 OUT flush'u52E22 global RX'tir;yalnız owned
sealed init ve525CB return PC guard'ı bunu atlar.5271A→268EC SOF partial
publish completion'ı bypass eder;registered poll bastırılır,one-MTU64B RX /
66B record-capacity pause/rearm ile sahiplik korunur.8 gate;max38 maskeli
komut/call-loop yok.347 toplam/87 aday PASS. Parent bildirimi native no-op
sınırıdır;composite MSC/task/power/descriptor/gerçek bariyer açık.
Üretim aynı/M7 NO-GO. MIDI-USB-CONTROL-5706.md;
logs/usb-control-20261028/probe/{audit,stock-contract}.

---

## 28 Ekim 2026 — Native USB IRQ sırası ve CPU FIFO bridge

D+E:RX4293E→2C798→42614→2AB42→40C46→526C8→26988;
TX4293E→2C7AC→42690→2AB36→40C22→5268E→268E0→268D0.806776C callback
tablosu/root20006F20 pin'li. Native OUT callback RXFLVL531CC kopyasından
önce gelebilir.820B/96B köprü,IRQ giriş snapshot'ı ve IRQ sonrası yayınla
coalesced/çok FIFO IRQ'sını testten token olmadan işler.4 gate,ek mask yok.
Native2C82A prefix40040000/mode0/6 endpoint doğrular;full boot değildir.
325 toplam/87 aday PASS. Hardware generation taşımayan eski XFRC bariyer
ihlali sonrası yeni job gibi görünebilir;negatif kontrol korunur. Kontrol /
reset/disconnect dönüşü ve gerçek bariyer açık. Üretim aynı/M7 NO-GO.
MIDI-USB-IRQ-5706.md;logs/usb-irq-20261028/probe/{audit,stock-contract}.

---

## 28 Ekim 2026 — USB donanım aktarımı ve callback kimliği ayrımı

D:26880 endpoint availability'yi düşürür,268D0 completion serbest bırakır.
26988 r0=port/r1=byte count ile2691E üzerinden RX publish ve269AC rearm yapar;
epoch/ticket taşımaz.52EDC endpoint mask/CTL AND yapar;SNAK/EPDIS+ACK/flush
bariyeri bu stok gövdede yoktur.52E04 seçili TX FIFO'yu,52E22 ortak RX'i
flush eder;53250 bütün cihazı durdurur. Pin'li disassembly logda saklıdır.

E:3176B yeni session wrapper/128B ek state,11 gate;toplam1624B sentetik RAM.
İki MIDI endpoint disable/ACK ve yalnız TX FIFO1 flush modeli;staging'i bariyer
sonuna kadar tutma,epoch/ticket claim ve resume revalidation testli.
306 toplam/87 aday PASS. Tagged eski RX/TX callback modelde reddedilir;
untagged stok callback uyumu FAIL. Kimlik tek başına geç DMA yazısını
engellemez:negatif test bunu korur. Native tamIRQ/cache/RTOS kanıtı değildir.
Üretim aynı/M7 NO-GO. MIDI-USB-SESSION-5706.md ve
logs/usb-session-20261028/probe/{audit,stock-contract}.

---

## 28 Ekim 2026 — RX lifecycle ve native endpoint ayrımı

D+E:269F0 direct29B2A;2A374 direct401BA/E2 TX yolları. Native5261C disconnect
callback'i RX ring clear yapmaz.6668C..666BA constructor prefix RX01 port
20005F94/controller20005CC8 ve16x64B/1057B ring oluşturur;tam boot değil.
2350B wrapper/64B ek RAM,toplam1496B;15 typed gate+poll overlay;quiescent
reset/epoch close-resume testli. Maskeli max9 komut/call-loop yok.
281 toplam/87 aday PASS. Retry active0 iken native endpoint in-flight olabilir;
RX freeze eski TX'i iptal etmez,reconnect safety FAIL;late RX DMA açık.
Üretim aynı/M7 NO-GO. MIDI-USB-LIFECYCLE-5706.md ve
logs/usb-lifecycle-20261027/probe/{audit,stock-contract}.

---

## 27 Ekim 2026 — RX ring borç sahipliği ve committed-window hizmeti

D+E:Native25AEC length/payload'ı byte byte yayımlar;2C71C item-size byte'tır.
Yeni964B ledger,SCANNED provenance ve00/81 tüketici header'larıyla tamamlanmış
inquiry borcunu ring'de tutar. Fresh marker reddedilir;partial publish tüketilmez.
Tek parser yolu,sıra korunumu,borç aktarımı öncesi ack yok,bir pop/submit/tur.
182/192B pencerede29 yanıt ve Clock/Stop PASS;max2048B test157912 komut.
262 toplam/87 aday PASS,üretim aynı/Off-Stop FAIL/M7 NO-GO.
Native lifecycle/IRQ-RAM ve host pre-admission latency açık.
MIDI-USB-LEDGER-5706.md;logs/usb-inquiry-ledger-20261027/probe/audit.

---

## 27 Ekim 2026 — Ordered USB admission ve nota/transport sırası

D+E:616B ordered varyantında tek404BC parser yolu vardır;realtime bypass yok.
Pending word0..8 inquiry sayar;kabul0 sonrası bir azalır,tur başına1 deneme.
Full durumdaF0 parser'dan önce cursor'da tutulur;suffix sırayı geçemez.
Gerçek52274/receiver/adapters/ownership ile On→Stop ve Off kapanışı testli;
96 permütasyon/split,24 karma native karşılaştırma ve64 Off/Stop PASS.
244 toplam/87 aday PASS.172B arena/1432B toplam aynı;üretim değişmedi.
Tam kapasitede9. inquiry arkasındaki Clock/Stop beklemesi FAIL/M7 NO-GO.
MIDI-USB-ORDER-5706.md;logs/usb-inquiry-order-20261027/probe/audit.

---

## 27 Ekim 2026 — USB RX cursor ve inquiry token

D+E:29AC8 ->269F0/25B1A,parser404BC ve24B68 zinciri. Deneysel29AC8 giriş
overlay'i,64B buffer/cursor/token sahipliğiyle busy inquiry'yi host resend
olmadan yanıtlar.722B kod/172B ek RAM,toplam1432B sentetik RAM. Aynı buffer
Clock/Stop tek dispatch ve64 Off kapanışı testli;sonraki queued buffer'daki
realtime bekler,Note On önündeki Stop bypass sırası değişir:iki negatif FAIL.
230 toplam/87 aday PASS,üretim aynı/Off-Stop FAIL/M7 NO-GO.
MIDI-USB-INQUIRY-RETRY-5706.md;logs/usb-inquiry-retry-20261027/probe-final/audit.

---

## 27 Ekim 2026 — Üst formatter ve native request tüketimi

D+E:32120/154/188/1BC/1F4 formatter çağrıları4691A'dan öncedir. Beş erken
guard native stack5..7 argümanlarını koruyarak kapasite rezerve eder;2878B
kod/428B retry RAM,toplam1260B sentetik RAM. Nested alt/direct çağrı rezerve
slotu alamaz;full durumda kaynak değişmez.213 toplam/87 aday PASS.
D+E:USB29BAA ve DIN29C64 ->24B68,listener r0'ı yok sayar;parser istek tüketir.
F07E7F0601F7,TX doluyken yanıt kaybeder;drain sonrası açık resend17B yanıt
üretir. Otomatik retry FAIL. Inquiry listener tek başına bağlandı;26DE8 ve
update/storage handler yürütülmedi.43544/435D6 ACK yan etkilerinden sonradır.
Kanıt:logs/recovery-sysex-request-20261027/probe-final/stock-contract/;
ayrıntı MIDI-SYSEX-REQUEST-5706.md. Üretim aynı,Off/Stop FAIL/M7 NO-GO.

---

## 27 Ekim 2026 — Native senkron SysEx kabul bildirimi

D+E:68A54 scatter-load,20000920 nesnesini8069460 vtable ile kurar;
slot0=2D44D kayıt,slot4=24B69 multicast.299B0 tüm portlar kabul edince aynı
çağrı içinde event0 bildirir;24B68 ->468EC ->global owner callback.
Payload hâlâ pending;297DE poll'da ayrı completion bildirimi yoktur.
Önceki ayrı gecikmiş job yorumu bu zincir için düzeltilmiştir.
Yeni isteğe bağlı2050B/424B retry,owner/event snapshot ve native tek kabul
bildirimini sınar;toplam1256B sentetik RAM. Callback içinde reader bitişi ve
reentry korunur;native USB/DIN360B stall baytları eşleşir.202/87 PASS;
request geri basıncı/üretim açık,aday Off/Stop FAIL/M7 NO-GO.
32120 ->46A54 formatter,4691A girişinden önce çalışır;upstream guard kapsamı açık.
Kanıt:logs/recovery-sysex-completion-20261027/probe/stock-contract/;
ayrıntı MIDI-SYSEX-NOTIFICATION-5706.md. Aşağıdaki kayıtlar tarihseldir.

---

## 27 Ekim 2026 — SysEx formatter ve callback sahibi

D+E:298B8'in12 doğrudan çağıranının üçü r0 sonucunu yok sayar, dokuzu iletir;
yerel retry yoktur.46934/46938 global20006EE0/+4 callback/context'i kabulden
önce değiştirir;468EC güncel çifti çağırır.2629E kurucusu router+20'ye
20000920 nesnesini bağlar;299B0 native success bildirimidir.
Yeni ayrı1750B Thumb/384B sentetik RAM,360B sahipli payload ve port retry
maskeleri ekler.12 giriş guard'ı formatter/global callback yazısından önce
ret verir. Guardsız nested source/owner ezilmesi negatif testte korunur.
191 test/87 aday PASS; native completion ve dolu-slot yanıt politikası açık,
üretim Off/Stop FAIL/M7 NO-GO. Toplam1216B RAM üretimde rezerve değildir.
Kanıt:logs/recovery-sysex-retry-20261027/probe/stock-contract/;
ayrıntı MIDI-SYSEX-RETRY-PROTOTYPE-5706.md. Aşağıdaki kayıtlar tarihseldir.

---

## 27 Ekim 2026 — SysEx dönüş, bekleme ve ödünç payload sahipliği

D+E:40232 (vt+C)1=kabul/0=ret;40264 descriptor alanlarını kopyalar,40378
payload işaretçisini sonraki poll'da okur.4028C ready0 iken pending'i gizler.
298B8 router sonucu tersidir:0=başarı/1=hata.29952 bütün portları bekler;
29978 ortak tampona memcpy;2999A port fanout.26F36 sonucu yok sayar,
2CBF4/6 döndürür,46954 iletir.12 doğrudan router çağrı adayı trace script'inde.
Yeni1140B prototip,832B aynı sentetik RAM: SysEx kabul/pending kancaları ve
yalnız Unicorn298B8/29962 overlay'leri. Bounded ret, nested çağrı ve tampon
sahipliği testlidir; stok çağıran retry politikası/üretim entegrasyonu açık.
177/24 deneysel,87 aday regresyonu PASS; üretim Off/Stop FAIL, M7 NO-GO.
Kanıt:logs/recovery-sysex-20261027/probe-final/stock-contract/;
ayrıntı MIDI-RECOVERY-PROTOTYPE-5706.md. Aşağıdaki kayıtlar tarihseldir.

---

## 27 Ekim 2026 — İzole recovery ve ayrı SysEx girişi

D+E:RPsend/RPpoll yalnız emülatör RAM vtable'larında üç-bayt401FE ve402B4
yollarını sarar;832B sentetik bitmap,774B kod.63/64 ve F8+FC kapanışları,
native USB2B408/DIN2B564 stall ve nested çağrılar kayıpsız. Yerel IRQ-mask
yolları max16 komut, call/loop yok; fiziksel timing/IRQ kanıtı değildir.
D+E:40232 (vt+C) port+8/+C SysEx pointer/length bağlar,+10 counter'ları
kurar;4028C (vt+10) pending/ready okur. Ayrı API fault set iken de SysEx
kabul eder. Native40232 eski transfer bitene kadar vt+14 poll döngüsü yapabilir;
basit busy wrapper burada deadlock riski taşır. Tüm producer karantinası FAIL.
Üretim hook'u/RAM rezervasyonu yok;166 testin13'ü deneysel,87 paket aynı aday.
Ayrıntı MIDI-RECOVERY-PROTOTYPE-5706.md. M7 NO-GO.

---

## 27 Ekim 2026 — Pattern player -> native Stop -> output

D+E:3C29E/4ADA4, sekiz player ve player başına8 gate kaydı kurar.
4AEEE/4AFBC step hazırlığı/On;4B0D4 duration list,4B170 Off,4AED8 flush.
Player callback16+t ->router+30(class0) ->voice+4 ownership filter ->case3
->sample filter/24+t ve MIDI32+t ->3B270/288(-12) ->31F9C/FC6.
Gate expiry, same-pitch Off/On, oldest steal, tie ve32 step okuması testlidir.
33EAE transport notify ->55120/552F6 ->4AED8 sekiz track Off'ları;32024 FC sonra.
63 nota+Stop PASS;64+Stop FC FAIL; aynı USB buffer F8+FC ile bir Off da FAIL.
Her iki modda üç hazır driver.153/87 PASS, ayrı negatif probe FAIL/NO-GO.
Kurucu/tick RAM'i sentetik; tam boot/IRQ veya canlı64-nota erişilebilirliği
kanıtı değildir.8-slot yapısı bütün UI/tie nota kaynaklarına üst sınır koymaz.
Ayrıntı SEQUENCER-PLAYBACK-5706.md; logs/seq-stop-probe.json.

---

## 27 Ekim 2026 — TX overflow fault ve native driver

D:40228 son BLEQ/ITEEE slotu23690 no-op'una gider. Observer APSR_NZCVQG ve
r0-r5/r12/lr saklar, c_seq_state sonrası+7A=1, no-op'a tail-call; guard bunu okur.
E: iki moddaki kayıptan-sonra-geçiş karşı örnekleri kapandı.144/78 PASS;
Off delivery/stalled Stop FAIL, NO-GO. Native2B408 USB/26880 endpoint ve2B564
DIN formatter/26014 byte-ring de yürür; final submit/IRQ-enable sınırları stub.
27624 adlandırma düzeltmesi: genel event pump değil, USB endpoint hizmetidir.
MIDI-TX-FAULT-5706.md ve STATUS.md güncel kapsamı/sınırları açıklar.

---

## 26 Ekim 2026 — Main poll sırası ve USB RX yield

D:25874 output297DE;25878 input29ABC ->USB29AC8/DIN29BDA. DIN1 byte/port/tur.
666A6..666B6/26828/2C71C USB RX16*64, ring1057 bayt. Stok USB bütün RX'i tüketir.
Yeni29B62 hook cfda4068 ->c_usb_rx_yield: GE29AF2, LT LDR r0,[r0,#4] +29B66.
Cave12 bayt; BL/store/stack/flag değişimi yok. E: stok kontrol Stop kaybı;
adayda64/255 Clock + Stop, iki mod, SysEx fragment ve ABI PASS.136/70 PASS.
Stalled-driver Stop/dolu-FIFO Off probe FAIL; NO-GO. Fiziksel task/IRQ ve
gecikme bütçesi kanıtı değil. MIDI-USB-YIELD-5706.md ve STATUS.md öncelikli.

---

## 26 Ekim 2026 — Native MIDI çıkışı ve queue loss

D: boot297A8 ->4016C slot64;31F08 Clock/transport alt nesneleri ->468FA ->2986A
->401FE/40DC4;297DE ->402B4 worker ->403EC ->driver accept.23690 stok no-op.
E:3223C/3328C gerçek clock backend ctor'ları ve store/listener'ları; ilk Clock
özel dalı ve Stop; iki modda FIFO/worker çıkış sırası.128/62 PASS.
Negatif E: consumer poll öncesi64 Clock ile üç portta On1/Clock64/Off0; ilgili
kod stokla aynı. Paket verifier CRITICAL_RUNTIME_PROBE_FAILED / NO-GO.
Sınır: final drivers/timer/tempo/GPIO stub; clock present fixture girdisi;
gerçek task/ISR erişilebilirliği ve sequencer adım üreticisi henüz açık.
MIDI-OUTPUT-TRANSPORT-5706.md ve STATUS.md öncelikli.

---

## 26 Ekim 2026 — MIDI parser ve gerçek transport store

D:29C1A DIN ->404BC ->24B68/52274 ->5AF94;29AC8 USB packet FIFO aynı yola gider.
Receiver+30, boot294CC/ctor3F454 ile clock controller+AC action wrapper'ına;
wrapper owner+0C/vtable66B80 ->33D30/33E04/33EAE. Start34082/340AA/342E0.
Receiver+34 boot27D78/28CF4/294C6 üzerinden3223C nesnesi/vtable68EFC ->32BB6.
E: gerçek parser ctor/FIFO ve handler store yazıları;8-track reset; normal
Clock pending/callback; iki mod, running status ve ring wrap.120/54 PASS.
Son sequencer/driver/Clock alıcıları stub, ISR/DMA/scheduler kanıtı değil.
MIDI-INGRESS-TRANSPORT-5706.md ve STATUS.md öncelikli; NO-GO.

---

## 26 Ekim 2026 — MIDI receiver ownership + mode guard

D: receiver3F454 ctor maskeyi+74'te160 bayt sıfırlar; root vtable665E4:
On3F5A8, Off3F660.3F7D8 drain5word/track gerçek Off çağırır. Final subobject
vtable'ları+0C=66654,+10=66670;5AF94 realtime F8/FA/FB/FC bunlara gider.
294CC direct ctor çağrısı bulundu; tüm indirekt lifecycle kanıtı değildir.
E:32 alt-vakada receiver held maskesine rağmen mode değişimi yeniden üretildi.
Yeni observer/cache/busy ve160 bayt scan bunu kapatır.113 test/47 packaged PASS.
Clock/Stop teslimatı son transport stub'ına kadar; gerçek ISR/task/output queue
açık. Ayrıntı MIDI-MODE-OWNERSHIP-5706.md; STATUS.md öncelikli.

---

## 26 Ekim 2026 — Ortak proje kabulü ve kanıtların korunması

E:101 test ve35 packaged güvenlik testi PASS. probe_shared_project.py gerçek
span/sekiz recorder ctor'u + button dispatch ile169092 bayt raw/metadata/P
korunumu, mode1->0 ve I/O0 gösterir. Tarihsel alias probe değiştirilmedi;
run_historical_alias_probe.py eski kaynakla60->34/apply0 karşı deneyi üretir.
Güncel mod geçişi ve stok depolama hata riski ayrı kanıt sınıflarıdır.
Kalan görev dış MIDI ownership filtreleri ve Stop/Clock/scheduler sınırıdır.

---

## 26 Ekim 2026 — Ortak proje: stopped/ownership guard

D: ctrl+18 store3D3C0 üzerinden501B4 ctor r3 argümanı;501E8 bunu
play-view+14'e yazar.50270..502A0 word0 byte0 ile start/stop seçer.
3E448..3E478 ctrl+1C0..1DC store word0'larını nota sahipliği temizliğinde
sıfırlar. Helper committed store'ları ve grid held alanlarını okur.
E: gerçek3D8B8 +51B7A ile0->1->0; dosya çağrısı0, raw169092 bayt aynı.
Maskeli caller reddedilir. Voice kapama IRQ maskesi geri getirildikten sonra
olur. Projects/Save/Packs/recorder bölgeleri stoktur. Harici clock/MIDI
yarışları, tüm sahiplik filtreleri ve tam zaman bütçesi kanıtlanmadı.

---

## 26 Ekim 2026 — Load öncesi geçici ret

D: 08037BD6 stok30b585b0 (push r4,r5,lr; sub sp,#20) yerine B.W
c_project_load_containment. 8B frame, c_seq_state; aynı P owner ise trans=0.
Frame geri alınıp37DD0 phase-cleanup tail-call. 37C66 read request ve37C84
New callback bu continuation üzerinden ulaşılmaz.
E: tüm raw169092 bayt aynı, read0; bypass karşı deneyinde nota60 ->34.
Geçersiz heap/yabancı owner state'i korunur. Tam boot kanıtı değildir.

---

## 26 Ekim 2026 — Raw project ve canlı recorder pattern alias kanıtı

D: Main281C2 r1=r6 ->33120, output span r1/r2/r3 ->36A02 ->36950.
Main283F2 r1=r6 ->36FA8;36FDC [P+14]=r1.33120..3148 gerçek span'i
(stride5140,count8,raw+2E4) kurar.36950 her track için pattern pointer'ını
stack arg6 olarak48AE0'ye taşır;48B58 [recorder+50]=r6 yapar.
E: gerçek span/factory/sekiz recorder kurucusu aynı tabloyu üretir; Project
Controller pointer-prefix'i ayrıca yürütülür. Tam boot/main kurucusu çalıştırılmış
sayılmaz. logs/project-alias-constructors.txt ve project_alias_test_support.py.

E: relocate edilen gerçek FIFO grafiğinde raw'ı read destination yapınca
short-read4 ve Close/error cleanup sonrasında live nota60 ->34; apply_calls0.
Ayrı probe ve paket verifier bunu kritik NO-GO sayar. State+64 taint flag'i,
owned error sonrası Save dispatch/direct serialization girişini kapatır; sadece
başarı apply sınırı açar. Bu koruma staging/rollback değildir.

---

## 26 Ekim 2026 — Load read bridge ve Close sonucuna bağlı apply

D+E: gerçek0x08037BD6, metadata'da mevcut slot için0x08047288 read request
kurar. Worker type6 dalı0x0804113A return0/2/4/5 sonucunu result event r2'sine
koyar. Stok0x080472A8 bunu kaybediyordu. Yeni c_load_storage_result owned P+0C
alıcısını state+54/+58..63 context'inde saklayıp stok Close kuyruğuna verir.
Close handler entrySP+4 context, r2 Close sonucudur. Slot<64 ve aktif geçişte
hedef eşleşmesi apply callback'inden önce doğrulanır. Status3 hata kendi busy
maskesini temizler; status2 success 0x08037E3C'ye gider.

Testte success apply fonksiyonu boundary stub'dır; failure cleanup gerçek stok
koddur. Read/write/close API'leri ve OS wakeup'ları stub; read stub'ı byte-count
ve kısmi raw-data değişimini modelleyebilir. Raw buffer alias/rollback ve
Close'un global file-handle kullanımı henüz sistem bütünleştirme kanıtı değildir.
logs/load-queue-stock.txt, load-commit-stock.txt, load-queue-tests.txt ve
load-queue-audit/ yeni kanıtları içerir.

---

## 26 Ekim 2026 — Save Close completion ve busy temizliği

D+E: c_save_storage_result owned Save için state+44 callback ve state+48..53
status kopyası tutar. Close460C8 callback=c_save_close_result|1,
userdata=SEQ_STATE_ADDR olarak gerçek kuyruğa gönderilir. Worker2B064 context'i
altıncı argümanda (entrySP+4), Close API sonucunu r2'de taşır. Close handler
pointer/heap/owner doğrulaması yapar, write/Close sonucunu birleştirir, context'i
bir kez tüketip üst Save callback'ini çağırır. File-key kopyası ayrı tutulur.
State layout bütünlüğü ve Thumb callback ADR hizalaması denetlenir.

Save error callback'i owned snapshot için P+4C store bit1'i temizleyip notify
eder; dirty ve diğer ready bitleri korunur. Sekiz write/Close alt-vakası ve
Close beklerken edit/duplicate/invalid-context regresyonları logs/close-tests.txt
ve close-all-tests.txt içindedir. File API ve OS stubları nedeniyle gerçek
medya, scheduler ve global callback generation kanıtı hâlâ açık.

## 26 Ekim 2026 — Storage worker ve iki FIFO / Save hata köprüsü

D+E: 45EB6 type7 isteğini 72-bayt paket olarak2ACB8'e verir. Request FIFO
40DC4/40DEE, ring buffer2A37E..2A490 kullanır. Worker2AD40 type7 dalında
411D8 dosya yazma API'sini çağırır; sonucu event payload+11'e yazar.
419CC, handler+30-bayt payload'ı result FIFO'ya kopyalar. 25B1A tüketir,
2B064 unpack ile r2=file-result, stack arg6=bridge olarak bridge47304'ü çağırır.

Stok47304 r2'yi kaybeder, Close460C8 enqueue sonrasında üst callback'i kopya
file-key pointer'ıyla çağırır. Yeni c_save_storage_result, Save snapshot owner
ile eşleşen P+10 alıcısında write error!=0 ise result copy word0'ı3 yapar.
Dosya anahtarının orijinali ve Close request key'i korunur. Generic alıcı ABI'si
r0=callback,r1=result copy,r2=0 aynı kalır.

Testte411D8 return0/2/3/5 enjekte edilir; başarı/hata gerçek stok Save cleanup'a
gider. Request/result FIFO ve callback bir kez tüketimi gerçektir; OS wakeup'ları,
dosya API'si ve Close41906 stub'dır. Üst onayın Close sonucu öncesinde olması
ayrı açık engeldir. logs/queue-error-before.txt, queue-tests.txt, queue-audit/.

## 26 Ekim 2026 — Dispatch/Projects bağlamı ve kimlik sınırı

D+E: c_proj_dispatch_guard, artık aktif state2 ret yolunda owner yazmaz;
idle Load/New bank kontrolünden ve state1 hedef kabulünden sonra owner yakalar.
c_proj_enter_page trans_state!=0 iken aktif owner/view pointer'larını korur.
İki önce/sonra regresyon logs/identity-before.txt ve reentry-before.txt içindedir.

D: Load callback nesnesi P+0C, Save callback nesnesi P+10'dur. Save request
0x080472E2 bridge+4'e nesneyi kaydeder. 0x08047344 -> 0x08047350..360
tüketimde bu alanı sıfırlayıp nesnenin vtable slot0'ını çağırır. Load köprüsü
0x08047288, tüketimi 0x080472A8 aynı deseni bridge+0'da yapar.
0x08045EB6 request'i 0x0802ACA2/0x0802ACB8 üzerinden kuyruğa teslim eder.
Tam queue/terminal seri teslimat modeli henüz yoktur.

E (sınır enjeksiyonu): scripts/probe_operation_identity.py aynı P/slot için
iki snapshot arasında edit yaptıktan sonra eski ack enjekte eder; dirty0 olur.
Bu scriptin NO-GO sonucu gerçek kuyrukta bu sıranın ulaşılabilirliği kanıtı
değildir. Kimlik eklemek, onu request ile değişmez biçimde taşımadan bu sınırı
çözmez. logs/identity-probe.json ayrıntılı gözlemi saklar.

## 26 Ekim 2026 — Load/Save hata callback'leri

D+E: stok0x080381D6 giriş10380968 = subs r0,#0x10;ldr r1,[r1].
r0=P+10, r1=status word pointer. Status2 -> 0x08038078 Save başarı;
status3 -> 0x08037DD0 cleanup; diğer değerler dönüş. Yeni c_proj_save_cb aynı
dispatch'i korur; error'da eşleşen snapshot owner'ını PRIMASK altında iptal eder.
0x08037DD0 phase store word1 byte0=0 yapıp notify eder ve P+6C observer listesine
olay iletir. Testler bu cleanup'u gerçek stok kodla yürütür; observer listesi boş.

Load completion hook'unda r4=P,r5=slot. Slot<64 ve aktif geçişte owner/target
eşleşmesi dirty temizliğinden önce yapılır. c_proj_load_cb error yalnız kendi
trans_state2 geçişini iptal edebilir. Ardışık işlemlerin generation kimliği ve
stok başarı fonksiyonunun hook öncesi RAM etkileri bu kanıtın dışındadır.
Kanıt: logs/storage-callback-stock.txt, storage-callback-audit/ ve regresyonlar.

## 26 Ekim 2026 — Kayıt başlangıcı ve Save koruması

D+E: 0x08036ABC orijinal04682568 = ldr r4,[r0];ldr r5,[r4]. Bu noktada
r0 recorder, r1 nota, r2 velocity, r7 track16..23. Guard callback'i kilit altında
bir kez yürütür; çağıranın 0x08036AC0 BLX r5 komutu için Thumb no-op döndürür.
Stok prologue'un kaydettiği r4/r5 caller sonunda geri yüklenir.
State+24'te sekiz recorder pointer'ı; Save completion current byte+60 ve
pending words+68..+290 bit0 taramasından sonra dirty temizleyebilir.
Kanıt: logs/pending-before.txt, pending-all-tests.txt, pending-audit/.
Zaman bütçesi, tam boot nesne ömrü ve tüm eşzamanlı storage yolları açık.

## 26 Ekim 2026 — Router / sahiplik / kayıt birleşimi

D+E: 0x0803B2A0 ilk üç callback allocation'ını 40+t,24+t,32+t ile kurar,
fakat 0x0803B31E..324 çağrısı r1=32+t,r2=24+t,r3=40+t sırasındadır.
0x0804A8CC voice+1C/+20/+24 alanlarına bu sırayla yazar. Önceki +1C kayıt
varsayımı yanlıştır; +24 kayıt alıcısıdır.
MIDI class2 -> voice case2 -> +8/+0C ownership filters -> callback4/5 ->
voice+20/+24 -> router class24+t/40+t -> sample/recorder alıcıları.
0x08054F30 iki kaynak için nota bitlerini tutar, 0x08054FA8 son kaynak
bırakılınca Off iletir. Kurucu 0x08054F10 iki20-bayt maskeyi temizler.

scripts/midi_record_test_support.py bu grafiği kurar; yalnız son sample alıcısı
stub'dır. Kısa MIDI mesajından pattern7 step31'e gerçek kod zinciri 8 track,
2 mode ve iki Off biçimiyle geçmiştir. Nota0/127 sınırı ve iki kaynak sahipliği
ayrı test edilmiştir. UART/USB, scheduler, gerçek boot/storage ve sample ses
motoru bu kanıtın dışındadır. logs/ownership-disassembly.txt, ownership-tests.txt.

## 26 Ekim 2026 — MIDI decoder ve kayıt grubu sınırları

D+E: 0x0805AF94(r0=decoder, r1=3-byte mesaj) note-enable decoder+1C bit0'ı
ve decoder+4..+B kanal tablosunu kullanır. 0x0805F86C eşleşmeyi 16..23 track
kimliğine çevirir. Kanal15 özel FE dönüşü bu testin kapsamında değildir.
Receiver vtable0x080665E4 slot0=0x0803F5A8, slot1=0x0803F660;
velocity0 Note On'u Note Off'a çevirir, +74'ten başlayan nota maskelerini izler.
Receiver+24 alıcısı vtable0x080694D0 adaptörüne gider:
0x0803EC10/0x0803EC2A nota+12 dönüşümü yapar. Sonraki vtable0x08069510
adaptörü +8 ofsetini track kimliğine ekleyip16 çıkarır (stok kurulumda ofset16).
Test bu gerçek zinciri son router callback gözlem sınırına kadar çalıştırır.

D+E: kayıt grubu vtable0x08068CE4 slot0=0x08036A80, slot1=0x08036AC4.
Group+8 store word0 ve word1 sıfırdan farklı, word2 sıfırsa
group+0C+4*(track-id-16) recorder seçilir. Sekiz track ve üç ayrı kapalı
durum bağımsız test edildi. Bu test ile MIDI decoder testi arasında henüz
uçtan uca bağlantı kanıtı yoktur.

D: ana router 0x0803B7EC track16..23 için 0x0803B9F8 class2'yi seçer;
0x0804A9D8 case2, +8 ve +0C alt nesnelerine yönlenir. Bu katmanı atlayıp
MIDI decoder'ı doğrudan kayıt grubuna bağlamak stok akışını temsil etmez.
Kanıt: logs/ingress-disassembly.txt ve test_reaudit_abi.py içindeki iki yeni test.

## 26 Ekim 2026 — Recorder callback zinciri

D+E: recorder vtable 0x08067864 slot0=0x080492A8 (Note On),
slot1=0x0804933E (Note Off), slot2=0x08048CCA (rate),
slot3=0x08048B78 (pending başlangıcı), slot4=0x08048C58 (pending bitişi).
0x0804937C pozisyon/zaman store'larından callback argümanlarını çıkarır.
0x08048D2A flush -> 0x08048D7E -> 0x08048E70 gerçek pattern yazımını yapar.
test_recorder_callbacks_through_pending_to_pattern bu zinciri stok kodla
çalıştırır; pending verisi elle üretilmez. Kapsam: quantize kapalı, subtick0,
note60/velocity96, pattern0/7 ve step0/31, seçili pattern1.
Bu kanıt MIDI parser/dispatcher'ın recorder'a doğru ulaştığını göstermez.

## 26 Ekim 2026 — Kayıt finalizer haritası

D+E: 0x08048E70(recorder, note, time) pending word'u
[recorder+0x64+4*note] üzerinden okur. Bit0 pending, bit1..5 step,
bit6..8 pattern, bit9..15 velocity, bit16..26 zaman, bit27..29 microstep.
Pattern tabanı [recorder+0x50], seçim store'u [recorder+0x14], ST1/ST2
[recorder+0x54/+0x58]. 0x08048F02 ilk doğrudan pattern yazımıdır.
0x0804908C pending bitini temizler. Seçili pattern'de return1, diğerinde0;
bu dönüş dirty değil, store notify gereksinimidir.
0x0804909C(recorder, pattern, step, value) seçili pattern'de store word24+
üzerinden, diğer pattern'de step+5 baytına doğrudan yazar.
Kanıt: logs/record-disassembly.txt ve test_reaudit_abi.py. MIDI giriş
kaynağına kadar tam zincir henüz doğrulanmış değildir.

## 26 Ekim 2026 dirty izleme ilavesi

Stok 0x08048208 prologue 2de9f84f (40 bayt push) ve callback r1 karşılaştırmaları
+1C/+20/+24 veri yazma dallarını ayırıyor. 0x0803DDE0 prologue 70b50446;
controller+8C gate kontrolünden sonra aktif görünüm slot 4'e knob/delta aktarılır.
Save başlangıcı 0x08037ED0 prologue 2de9f847; r0=P, r1=slot. Tamamlama
0x08038176 noktasında r5=P, r6=slot. Yeni kancalar bu ABI'leri korur.
Bu bilgiler hash'i sabit stok dosyanın disassembly'sinden doğrulandı.
Testlerin kapsamı ve kalan bilinmeyenler: STATUS.md ilk bölümü.

# 5706: pad, edit, commit ve LED incelemesi

**25 Ekim 2026 denetim düzeltmesi:** Note On `0x080685E0 → 0x08031A19 → 0x08046780`; `0x08031A34 → 0x080467D2` force-off yoludur, Note On değildir. Gerçek track değişimi `0x0804D662`, cancellation çağrısı `0x0804D680`; mode çağrısı `0x0804D6E0`. Güncel yama ikisini de kapsar. Projects hazır biti bit 3, aktif proje kimliği store word 11’dir. Aşağıdaki eski M1 kayıtları için güncel kapsam sınırı `PHASE1-SAFETY-AUDIT.md` dosyasıdır.

24 Ekim 2026; yalnızca SHA-256 `11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf` tabanı.
Güncel kapsam 32 adım; sekiz track ve mevcut pattern sayısı korunur. Firmware değiştirilmedi.

## Kanıtın kapsamı

**D:** Bu stock dosyada pointer/bayt/disassembly doğrulaması. **E:** Gerçek stock kodu, sentetik RAM.
**K:** Paketlenmiş upstream kaynak iddiası. **Ö:** Henüz uygulanmamış tasarım.
Bu ayrım adresin doğru olması ile tüm cihaz davranışının doğru olmasını birbirinden ayırır.

Tekrar: `.\.venv\Scripts\python.exe scripts/run_ui_audit.py`.
İlk başarılı kayıt: `logs/ui-audit-20261024T182014064195Z/`; `tests.txt`, `disassembly.txt`,
`summary.json` içerir. JSON, disassembly pencerelerinin SHA-256 değerlerini de taşır.
Pencerelerde literal havuzu/jump tablosu bulunabilir; lineer disassembly tek başına kontrol akışı kanıtı değildir.

## Adres haritası

Kod adresleri çift; vtable içindeki Thumb pointer'ları tek sayılıdır.

| Bağlantı | Adres ve somut bulgu | Kanıt / sınır |
|---|---|---|
| Pad olay adaptörü | `0x080295B4`; `0x080295CA` → `0x08040108` | D; event argümanlarını yeniden sıralar |
| Press/release dispatch | `0x08040108`; `r3 != 0`: slot 0, velocity `max(1,r2>>1)`; release: slot 1 | D+E; 0/15/16/31 pad, sınır velocity değerleri; son callback'ler sahtedir |
| Ana controller | slot `0x080672E4` → `0x0803D7FF`; gövde `0x0803D7FE` | D; guard'lardan sonra `ctrl+0x7C` doluysa oraya, değilse `ctrl+0x78` görünümüne gider. Guard'lar bütünüyle emüle edilmedi |
| Grid container | vtable `0x080678DC`; press `0x0804D7A0`, release `0x0804D7DE` | D; `+0x228` tutulan pad maskesi; iki yol da seçici ve indeks dönüşümünü çağırır |
| Seçili track | `0x0805800E` → `[grid+0x25C]` store p0, `0x0803FC58` ile okuma | D+E; track 0 ve 7. Mutlak grid RAM adresi `0x20048B9C` yalnızca K; gerçek cihaz nesnesi ölçülmedi |
| Alt görünüm seçimi | `0x0804DC86`: pad <16 → `0x0804DC50`, diğerleri → `0x0804DBDC`; mode `[grid+0x264]` | D+E; mode 0/2/3 ve iki uç track. Bu modlarda üst görünüm `[grid+0x74+4*track]`; alt görünüm sırasıyla `+0x14`, `+0x9C`, `+0xBC` |
| Üst görünüm tablosu | `0x0804DC50`: `tbb [pc, r2]`; mode 0/2/3'te `[grid+0x74+4*track]` (Step View) döner | D+E; track ve mode'a göre üst subview pointer'ını çözümler |
| Alt görünüm tablosu | `0x0804DBDC`: `tbb [pc, r2-1]`; mode 0'da `0x0804DC46` dalıyla `[grid+0x14+4*track]` döner | D+E; mode 0/2/3 alt subview (Note/Sample vb.) pointer'ını çözümler |
| Container pad dönüşümü | `0x0804DF3E` | D+E; üst pad aynı kalır; test edilen mode 2/3 alt pad'den 16 çıkarır. Mode 0 alt bölümde ayrıca kendi sayfa durumunu ekler. Tüm mode'lar için tek eşleme varsayılmaz |
| Gerçek step görünümü kurulumu | grid constructor `0x0804C632` → factory `0x0805594C`; `0x0804C638..646` sekiz pointer'ı grid+0x74'e kopyalar; factory `0x08055A42` → ctor `0x0805C980` | D; ctor `r1=32` ile `0x080520D8` çağırır. Heap/constructor çalışması emüle edilmedi |
| Step görünümü vtable | `0x080682CC`: press `0x0805CB05`, release `0x0805CCF1`; LED slot `0x080682E8` → `0x0805D3BD` | D; observer alt nesnesi +8, vtable `0x080682F8` → `0x0805D093` |
| Step press | `0x0805CB04` | D+E; `0x805d020` ile timer 3 durdurulur; `[view+0x60]` p0 != 0 ise pad'e 16 eklenir; `view+0x20` w1 set; `view+0x74+2*step` durum bit 3 (held) set; `0x805cf24` ile LED palet 31 (parlak beyaz) hesaplanır; `[view+0x18]` w1'e step yazılır ve notify edilir; timer 6 başlatılır (300 ms, callback `0x0805ce49`); `[view+0xb8]` (bekleyen toggle) ve `[view+0xc0]` (basılı pad) maskelerinde `1 << step` set edilir |
| Step release | `0x0805CCF0` | D+E; aynı +16 dönüşümü; `[view+0xc0]` maskesinden bit temizlenir; `[view+0xb8]` biti 1 ise (300 ms dolmadan kısa bırakış) `0x0805d610` ile normal step toggle çağrılır; `view+0x18` w1 == step ise timer 6 durdurulur; `view+0x20` w0=0 yazılıp notify edilir; observer (`0x0805d094` -> `0x0805d3f8` -> `0x0805cffe`) bit 3'ü temizler ve LED'i günceller; `0x805d020` çağrılır |
| Step mod/clear denetleyicisi | `0x0805D020` | D+E; `[view+0xB4]` != 0 ise `[view+0x38]` callback'ini çağırır ve `0xB4`'ü sıfırlar; timer 3 durdurulur. `step >= 32` durumunda `view+0x74+2*32` doğrudan bu baytı ezer ve kontrol yapısını bozar |
| Held timeout callback | `0x0805CE48` | D+E; timer 6 callback'i (300 ms); `[view+0xb8]` pending toggle maskesinden `[view+0xc0]` basılı bitleri temizler (`bics`); böylece uzun basışta bırakma anında toggle tetiklenmez, step parametre düzenleme moduna (`view+0x68`) girilir |
| Step durum biti yardımcısı | `0x0805CFFE` | D+E; `(view, step, bit_index, val)`; `view+0x74+2*step` içindeki istenen biti set/clear eder ve `0x0805cf24` ile LED'i yeniden hesaplar |
| Release durum temizleyici | `0x0805D3F8` | D+E; observer'dan `view+0x20` bildirimi geldiğinde çağrılır; `view+0x20` w0 değerini (0) alıp `0x0805cffe` aracılığıyla bit 3'ü (held) temizler |
| Normal step toggle | `0x0805D610` → hit varsa `0x0805D5C2`, yoksa `0x0805D588` | D+E; ST1=`[view+0xC]`, ST2=`[view+0x10]`. Sonunda ST2 ve ST1 notify edilir. Oluşturma velocity 96, microstep mask 1, probability 7, sample flip FF, nota `[view+0x5C]` p0, gate 6, flags 0 |
| ST1 parametre yazıcıları | `0x080549B0` (Velocity), `0x08054A04` (Probability), `0x080549D8` (Microstep), `0x08054A30` (Sample Flip) | D+E; `step >> 2` ile word hesabı yapar. `step=32` yazımı Velocity yerine Probability[0]'ı bozar |
| ST2 parametre yazıcıları | `0x08054A5C` (Note), `0x08054A84` (Gate), `0x08054AB0` (Flags) | D+E; `step >> 2` ile word hesabı yapar. `step=32` yazımı Note yerine Gate[0]'ı bozar |
| Held sample yolundaki oluşturma | `0x0805E41A` → `0x0805E5A0`, observer `0x0805E3B0` | D; önceki rapordaki bu hook normal step toggle'ın yerine geçmez. Farklı nesne/alan düzeni vardır |
| Word okuyucu/yazıcı | `0x0803FC58` / `0x0803FD26` | D+E; aktif seçim word başına bir bittir; tek global buffer seçimi gibi modellenmemeli |
| Notify | `0x0803FBEC` | D+E; `active_mask ^= dirty_mask`; `[store+0x14]` listesindeki maskesi eşleşen listener slot 0'ları çağırır, ardından dirty'yi temizler |
| Pattern commit | vtable `0x080696A0` → `0x08048208` | D+E; listener+0x1C ST1, +0x20 ST2, +0x28 pattern seçim store'u; pattern tabanı `[listener+4] + 0xA28*selected`. ST1 alanları 3/2/4/5; ST2 alanları 0/1/6; 32 kayıt işlenir |
| Step LED observer | shim `0x0805D092` (`this -= 8`), gövde `0x0805D094` | D+E; ST1 velocity değişiklikleri LED durum bit 1'i günceller; sample-flip için ayrı dal vardır. Test gerçek notify ile gerçek observer'ı çağırır |
| Step LED renk hesabı | `0x0805CF24`; durum kaydı `view+0x74+2*step`; çıktı `[[view+4]]+2*step` | D+E; 16-bit mantıksal renk kaydıdır, doğrudan fiziksel RGB buffer'ı değildir |
| Step LED penceresi | `0x0805D3BC` | D+E; `[view+0x60]` p0 sıfırsa buffer, değilse buffer+32 bayt döndürür: 16 × 2 bayt kayma (`cbz r1, adds r0, #0x20`) |
| Ekran birleştirme (Compositor) | vtable `0x080678F8` → `0x0804DD1C` | D+E; `0x08052108` ile subview slot 7 çağrılır; üst subview'dan 32 baytı `grid+0`, alt subview'dan (`+r7` ofseti ile) 32 baytı `grid+0x20`'ye `0x08022CF0` (memcpy) ile aktarır. Extra subview 1 (`0x0804DB78`) ve 2 (`0x0804DCB2`, sayfa tuşları) yan tuşları yönetir |
| Step LED renk motoru ve durum bitleri | `0x0805CF24`; durum kaydı `view+0x74+2*step`; çıktı `[[view+4]]+2*step` | D+E; durum bitlerine göre mantıksal renk atar: Bit 0 (Playhead/Cursor: boş adım 0x001B, dolu adım 0x001A), Bit 1 (Hit/Dolu: boş 0x0019, dolu 0x0018), Bit 2 (Loop range), Bit 3 (Held: palet 31/30) |
| Grid mod kontrolü ve alt ofset | `0x080588EE`, `0x080588AC` | D+E; `r7` alt tampon ofseti; mod 0'da sayfa durumuna göre `page * 0x20` (0 veya 32 bayt); mod 1/4/7/8/9/10'da 0x20; mod 2/3'te 0. `0x080588AC` `[grid+0x258]` track store dizisini kontrol eder |
| Alt LED aktarımı | `0x0802596E` → `0x0802960C`; `0x0802964E` → `0x08029684` | D / baseline; downstream frame/bit-plane işleme. Grid renklerinin fiziksel pad/RGB'ye tam dönüşümü bu turda tamamlanmadı |
| Buton -> Grid Mode eşlemesi | `0x0803E2D8` | D; Button 8 (`Sample`) -> `mode 0` (`9`); Button 9 (`Note`) -> `mode 1` (`7`); Button 10 (`Velocity`) -> `mode 2`; Button 11 (`Gate`) -> `mode 3` (`5`); Button 12 (`Pattern Settings`) -> `mode 4` (`6`) |
| Projects ve Packs butonu | `0x0803DB2E` (Button 26 = `0x1A`); Packs dalı `0x0803DB54` | D; `Shift == 0` ve aktif görünüm `6` değilse `[ctrl+0x50]` (`0x0804F080`) ile Projects açılır; `Shift != 0` veya ikinci basışta `0x0803DB54` üzerinden Packs (`mode 5`, `[ctrl+0x40]`) açılır |
| Projects görünümü (32x2 sayfa) | Giriş `0x0804F080`; Pad press `0x0804F09E`; Up/Down `0x0804F12C`; LED `0x0804F27E` | D; `[proj_view+0x36]` baytı 64 projeyi iki sayfaya böler (`0`: Proje 0..31, `1`: Proje 32..63; `add.w r5, r5, r0, lsl #5`). Load/New (`0x08047038`), Clear (`+0x18`), Duplicate (`+0x1C`) ve Save (`+0x2C`) bu sayfa ofsetiyle çalışır |
| Dahili Sample Motoru Girişi | vtable `0x080685E0` → `0x08031A19` (`0x08031A1E` → `b.w 0x08046780`); Note Off `0x080685E4` → `0x08031A23` | D+K; MIDI çıkışından ve kayıtçıdan bağımsız olarak sadece dahili sample tetiklemesini susturma noktası |
| Güvenli Heap Durum Alanı | Allocator `0x08025A98`; limit `[0x20002B54]` (`0x2004F760`), current `[0x20002B58]` | D+K; `0x2004F660` (`HEAP_LIMIT - 256`) adresinde 256 baytlık güvenli çalışma zamanı durum bloğu (`c_rst` modeli) |
| MIDI | router `0x0803B7EC` / `0x0803B8F0`; mask dispatcher `0x0802986A`; port send `0x080401FE` | Baseline D/E sınırları geçerli; fiziksel MIDI, kuyruk basıncı ve Note Off yaşam döngüsü yok |

## Gerçekte sınanan davranışlar

`tests/test_ui_contracts.py` yedi davranış testi içerir:

1. Gerçek pad dispatcher, sahte son callback'ler: pad sınırları ve velocity normalizasyonu/press-release ayrımı.
2. Gerçek container seçicileri: track 0/7, mode 0/2/3, pad 0/15/16/31, iki sayfa durumu.
3. Gerçek setter + accessor + notify + commit listener: pattern 0/7, iki başlangıç aktif maskesi,
   step 0/15/16/31. Sekiz pattern'in bütün baytları karşılaştırılır; ayar/otomasyon ve diğer pattern'ler korunur.
   Notify öncesinde pattern değişmez; sonraki edit önceki edit'i korur.
4. Gerçek normal toggle + notify + commit + LED observer: pattern 7 üzerinde dört sınır adımı aç/kapat;
   tüm pattern belleği, hit durum biti ve LED renk değişimi/dönüşü kontrol edilir. LED getter'ın iki penceresi doğrulanır.
5. Kritik vtable pointer'ları ve basılı-adım renk dalı: yalnızca hedef mantıksal LED kaydı değişir.
6. Gerçek step press (`0x0805CB04`) ve release (`0x0805CCF0`) yaşam döngüsü: sınır adımları 0, 15, 16 ve 31 (sayfa 0/1)
   için iki tam toggle döngüsü. Press anında durum bit 3 (held) set edilir, LED parlak beyaza (palet 31) geçer,
   300 ms timer 6 başlatılır. Release anında bekleyen toggle biti (`view+0xB8`) aktif olduğundan `0x0805D610` çağrılır,
   pattern commit edilir, durum bit 1 (hit) set edilir, timer 6 durdurulur ve observer zinciriyle bit 3 temizlenerek
   LED aktif renge döner. İkinci basışta adım pattern'den temizlenir, durum bitleri sıfırlanır ve LED başlangıçtaki sönük renge döner.
7. Basılı tutulurken sayfa ve track değişimi (step ownership):
   - Sayfa değişimi: `view+0x60` sayfa 0 iken basılan pad 5 (step 5), kullanıcı basılı tutarken sayfa 1'e geçilip
     bırakıldığında +16 eklenerek step 21 olarak yorumlanır. Step 21 basılı olmadığından toggle tetiklenmez ve `view+0x18`
     eşleşmediğinden işlem abort edilir; step 5'in view üzerindeki durum biti 3 ve basılı pad maskesi korunur.
     Sayfa tekrar 0'a alınıp bırakıldığında step 5 başarıyla açılır.
   - Track değişimi: Grid container (`0x0804D7A0` / `0x0804D7DE`) fiziksel pad basılı maskesini `grid+0x228` alanında tutar.
     Track 0 seçiliyken pad 0 basıldığında Track 0 view'ı basışı kaydeder (`view0+0x74` bit 3 = 1).
     Pad basılıyken track 1'e geçilip pad bırakıldığında, grid `grid+0x228` maskesini temizler ancak release olayını
     o an seçili olan Track 1 view'ına iletir (`view1`). Track 1 bu adımı hiç basmadığı için tepkisiz kalır;
     Track 0 view'ı release olayını hiç almadığı için step 0'ın sahipliği Track 0 üzerinde "öksüz" (orphaned) olarak basılı kalır.

`tests/test_step_routing.py` beş ek yönlendirme ve sınır güvenliği testi içerir:

1. `test_stock_container_routing_split`: Stok grid container pad yönlendirme ve yerel pad dönüşümü doğrulaması (`0x0804DC86` ve `0x0804DF3E`). Pad < 16 üst görünüme (Step View), pad >= 16 alt görünüme (Note/Sample) gider; Mode 0 sayfa 0'da pad-16, sayfa 1'de ise +16 eklenerek pad olarak döner.
2. `test_step_index_overflow_hazard_and_corruption_proof`: `step >= 32` durumunda stok ikilide oluşan üç kritik bellek bozulmasının matematiksel ve emülasyon kanıtı:
   - Durum dizisi taşması (`view + 0x74 + 2 * 32 = view + 0xB4`): Durum biti 3 (held, `0x08`), `view + 0xB4` ikincil kontrol/temizleme baytını ezer. `0x0805D020` sonraki basışta `view + 0x38` fonksiyon göstericisini çalıştırmaya çalışarak unmapped bellek hatasına ve sistem çökmesine yol açar.
   - ST2 Note parametre bozulması (`0x08054A5C`): `step=32` yazımı (`step >> 2 = 8`) word 8'e denk gelerek Step 0'ın Gate uzunluğunu ezer ve pattern belleğine bozuk commit eder.
   - ST1 Velocity parametre bozulması (`0x080549B0`): `step=32` yazımı (`step >> 2 = 8`) word 8'e denk gelerek Step 0'ın Probability değerini ezer ve pattern belleğine bozuk commit eder.
3. `test_safe_32pad_full_lifecycle_all_steps`: 32-pad Sequencer Modu yönlendirmesinin tam yaşam döngüsü doğrulaması:
   - Tüm 32 pad (`0..31`) doğrudan Step View'a yönlendirilir ve sayfa ofseti 0 kilitlenir (`step == pad`).
   - 32 adımın tamamında (0..31) Cycle 1 (açma) ve Cycle 2 (kapatma) eksiksiz sınanır.
   - `view + 0xB4` kontrol bloğu hiçbir adımda bozulmaz (kesin sıfır kalır).
   - Pattern belleğine 32 adımın 32'si de eksiksiz ve hatasız yazılır/temizlenir.
   - LED renk dizisi 32 adım için doğru palet değerlerine güncellenir.
4. `test_cross_boundary_concurrent_press_and_release`: Üst/alt yarı sınırında (pad 15 ve 16) eşzamanlı basış doğrulaması. `view + 0xC0` held maskesinin birden fazla biti aynı anda başarıyla koruduğu ve ardışık bırakışlarda adımların bağımsız commit edildiği kanıtlanır.
5. `test_routing_guard_clamping_prevents_overflow`: Sınır maskelemesi (`pad & 0x1F`) ile 32, 47, 63, 127 gibi sınır dışı değerlerin Step View'a geçmeden güvenle sınırlandığı ve `view + 0xB4` bölgesini asla bozmadığı doğrulanır.

`tests/test_led_compositor.py` beş LED birleştirme ve playhead doğrulaması testi içerir:

1. `test_stock_step_view_led_getter_and_compositor_split`: Stok Step View LED getter (`0x0805D3BC`) ve Compositor (`0x0804DD1C`) ayrım mekanizması:
   - Sayfa 0'da Step View LED getter 64 baytlık tamponun başını (`buffer + 0`), Sayfa 1'de ise ikinci yarısını (`buffer + 0x20`) döndürür.
   - Stok Grid Compositor üst 16 pad'e Step View penceresini, alt 16 pad'e Note görünümünü (`r7` ofseti ile Sayfa 0'da 0, Sayfa 1'de +0x20) kopyalar.
2. `test_step_view_32step_logical_led_buffer_mapping`: Step View 32 adımlık mantıksal LED tamponu ve 32-pad grid eşlemesi:
   - 32 adımın her biri stok renk motoru (`0x0805CF24`) ile renklendirilir (hit durumunda `0x0018`, boş durumda `0x0019`).
   - 32-adım LED Compositor, Step View'ın ilk 16 kaydını (`0..15`) üst 16 pad'e (`grid_output + 0`), ikinci 16 kaydını (`16..31`) alt 16 pad'e (`grid_output + 0x20`) kopyalar.
   - 32 pad'in 32'si de Step View'ın tam 32 adımı ile birebir (1-to-1) eşleşir; hiçbir adım ötelenmez veya üst üste binmez.
3. `test_playhead_continuous_flow_across_32_steps`: Playhead imlecinin (durum bit 0) 1'den 32'ye kesintisiz akışı:
   - Playhead 0'dan 31'e kadar tüm 32 adım üzerinde sırayla ilerletilir.
   - Her adımda önceki adımın bit 0'ı temizlenir, aktif adımın bit 0'ı set edilir ve `0x0805CF24` çağrılır.
   - Aktif adım boşsa playhead rengi `0x001B`, doluysa `0x001A` (parlak vuruş) olur.
   - Compositor sonrası grid tamponunda tam olarak `cursor`. pad'in playhead rengini aldığı, kalan 31 pad'in playhead rengi taşımadığı doğrulanır.
   - Cursor 0..15 iken alt 16 pad'de, cursor 16..31 iken üst 16 pad'de hiçbir playhead sızıntısı olmadığı, özellikle 15'ten 16'ya sınır geçişinde imlecin kesintisiz aktığı kanıtlanır.
4. `test_other_modes_preserve_original_bottom_pad_layout`: Diğer modlarda (Note, Velocity vb.) alt pad orijinal düzeninin korunması:
   - Mode 2 (Velocity) veya Mode 0 (Note) seçildiğinde alt 16 pad'in Step View 16–31 adımları yerine, o modun kendi subview LED tamponunu (Velocity için `[grid+0x9C]`, Note için `[grid+0x14]`) yansıttığı bayt bayt doğrulanır.
   - Üst 16 pad Step View görünümünü korurken, alt padlerin mod bağımsızlığı %100 kanıtlanır.
5. `test_compositor_memory_safety_and_no_overflow`: Compositor bellek güvenliği ve taşma koruması:
   - Grid buffer sonrasındaki (offset 0x54 ve ötesi) canary baytlarının ve Step View `view + 0xB4` alanının asla bozulmadığı, arabelleğin güvenle sınırlandığı kanıtlanır.

Son zincirlerde RTOS timer kuyrukları (`0x08046dde` / `0x08046e2a`) `bx lr` ile yalıtılmış, tetiklenen timer id ve callback'leri
hook ile izlenmiştir. Diğer UI, toggle, notify, commit ve observer mekanizmaları stock kod ile çalıştırılmıştır.
Nesneler ve listener bağlantıları sentetik olarak kuruldu; bu, stock constructor'ların gerçek cihazda aynı anda kurduğu
bütün listener listesini veya thread sırasını sınamaz.
Testler 64 adım uygulaması değildir. Sekiz pattern bloğu fixture olarak korunur; sekiz gerçek track'in eşzamanlı çalışması sınanmadı.

## 32-pad uygulaması için çıkan sınırlar

Pad `0..31`, alt görünümün aldığı pad, yerel step `0..31`, mantıksal step ve playback cursor ayrı tutulmalı.
Stock üst 16 pad route'u aynı track'in step view'ına gider; step view kendi içinde sayfa offset'i ekler.
Yeni 32-pad görünümünde alt yarıyı step view'a yönlendirmek tek başına yetmez: bu +16 hem press hem release için
kontrol edilmezse yanlış step/32 üstü indeks oluşabilir.
Yapılan testler ve disassembly analizi şu kesin mimari sınırları ortaya çıkarmıştır:
1. **Step View Nativ 32 Adım Destekler:** Step View bellek yapısı (`view + 0x74..0xB2` durum dizisi, `view + 0xB8` pending maskesi, `view + 0xC0` held maskesi, 64-baytlık LED buffer'ı ve ST1/ST2 32-entry tamponları) 32 adımı yerel olarak zaten desteklemektedir.
2. **Sayfa Ofseti Çiftlenmesi Felakettir:** Alt 16 pad (`16..31`) Step View'a aktarılırken, eğer Step View kendi içindeki sayfa ofsetini (`[view + 0x60] != 0` -> `step += 16`) uygulamaya devam ederse, `step = 16..31 + 16 = 32..47` oluşur.
3. **step >= 32 Sonuçları Kesin Olarak Kanıtlanmıştır:**
   - `view + 0xB4` ezilerek `0x0805D020` üzerinden crash oluşturur.
   - `1 << step` 32-bit kaydırmada sıfırlanır, maskeler tutarsızlaşır.
   - `st1` ve `st2` dizilerinde parametreler birbirinin üzerine yazılır (Note 32, Gate 0'ı; Velocity 32, Probability 0'ı bozar).
   - Pattern commit (`0x08048208`) döngüsü yalnızca 32 adımı (`0..31`) işlediğinden, 32 ve üzeri adımlar bellekte kalıcı kirlilik bırakır ama asla diske/pattern'e düzgün yazılamaz.
4. **Çözüm Mimarisi:**
   - Sequencer Only (32 Pad) modunda: Grid Container tüm pad'leri (`0..31`) Step View'a yönlendirir.
   - Step View'a gelen pad doğrudan adım indeksi olarak ele alınır (`step == pad`).
   - Step View için sayfa ofseti sıfıra sabitlenir / izole edilir.
   - Yönlendirme katmanında `pad & 0x1F` sınır maskesi uygulanarak 31 üstü indeks geçişi donanımsal/yazılımsal olarak kesin engellenir.
   - LED tarafında ise Grid Composite (`0x0804DD1C`), üst 16 pad için `buffer + 0`, alt 16 pad için `buffer + 0x20` kopyalayarak 32 adımın tamamını aynı ekranda birleştirir.

## Açık sorular ve elenen yorumlar

- Mode 2/3 alt pointer ofsetleri ilk okumada +0x54/+0x9C sanıldı. Test başarısız oldu; Thumb TBB tablosu
  yeniden izlenince +0x9C/+0xBC doğrulandı. Test zayıflatılmadı, fixture düzeltildi.
- `0x0804E00A` başka bir 32-entry görünüm adayıydı. Constructor sonucu controller+0x40'a gider;
  grid+0x74'teki step view değildir. 32 sayısını görmek tek başına yeterli değildi.
- Bir PC-relative literal önce dört bayt ileri okundu; hizalı Thumb PC hesabıyla gerçek vtable bulundu.
  Literal/jump-table baytları disassembly'de sahte komutlar gibi görünebilir.
- Release sırasında `view+0x74` durum bit 3'ün doğrudan release fonksiyonu (`0x0805CCF0`) tarafından değil,
  `view+0x20` store bildirimi üzerinden observer (`0x0805D094` -> `0x0805D3F8` -> `0x0805CFFE`) tarafından temizlendiği kanıtlandı.
- Uzun basışın (hold) kısa basıştan (tap) nasıl ayrıldığı kanıtlandı: timer 6 callback'i (`0x0805CE48`, 300 ms),
  `view+0xB8` pending toggle maskesinden basılı pad'i temizleyerek bırakma anındaki toggle'ı iptal eder ve edit modunu açar.
- `step >= 32` taşmasının Step View bellek bloklarını (`view + 0xB4`) ve ST1/ST2 parametre dizilerini nasıl tahrip ettiği sentetik testlerle kesin olarak kanıtlandı.
- Grid Compositor (`0x0804DD1C`) ve Step View LED getter (`0x0805D3BC`) yapısı çözümlendi; durum bit 0'ın (`0x0001`) Playhead (playback cursor) olduğu ve 32 adımın tamamında (0..31) kesintisiz akabildiği kanıtlandı.
- Note (`mode 0`) ve Velocity (`mode 2`) gibi modlarda alt 16 pad'in o modun kendi alt subview LED tamponunu (`bottom_view + r7`) yansıttığı ve mod bağımsızlığının tam olarak korunduğu kanıtlandı.
- Gerçek controller/track/pattern nesnelerinin RTOS eşzamanlılığı, SD save/load ve fiziksel tarama zamanlaması açık.
- Gate/tie, Mutate, Clear/Duplicate ve 1–16 düğmesi uzunluk gesture'ı ayrı kabul testleri gerektirir.
- Mod kısayolu seçilmedi; ayrı Projects/Packs/MIDI-only davranışı uygulanmadı.

Sonraki tek görev: 32 Pad Yönlendirmesi ve LED Birleştirici mikro-yamalarının (M3/M4) entegrasyonu ve mod kısayol/geçiş mekanizmasının tasarlanması.
