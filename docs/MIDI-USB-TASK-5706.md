> Güncel29 Ekim:462 toplam/87 aday PASS. Henüz USB'ye verilmemiş yazılım
> MIDI borcu artık fiziksel reader iptalinden ayrı korunur. Önceki suspend /
> wake kilitlenmesi yeni carry overlay ile Normal/Sequencer'da geçer;reset
> sonrası host config ile yanıtlar kayıp/tekrar olmadan model IRQ akışına çıkar.
> 360B payload,Note Off,Clock/Stop,wrapped owed kayıt ve generation yarışları
> testli. In-flight/staged/partial-parser/gerçek port fault carry almaz;eski
> politika değişmez.2712B checked RAM/init/boot/gerçek timing ve entegrasyon
> açık. Üretim aynı/Off-Stop FAIL,M7 NO-GO. STATUS.md ve MIDI-USB-CARRY-5706.md.

---

# Native main USB slot'u ve backend worker — 28 Ekim 2026

Emülasyon prototipi,power ve SysEx retry servisini native ana döngüye bağlar.
Manuel service çağrısı olmadan query,READ/CSW ve borçsuz suspend/wakeup ilerler.
Retained MIDI debt ile recovery hâlâ bloke olur. M7 NO-GO;production'a
eklenmedi. Fiziksel cihaz/MIDI/USB API erişimi yapılmadı.

## Native akış ve bağlantı

25870 global20006F04'ten router yükler;297DE output poll çalışır.25878
29ABC USB/DIN input poll,2587C27624 MSC poll çağırır. Yeni4B BL gate yalnız
2587C'dedir. Task başına bir sr_service ve bir pw_service çağrılır;MSC açık,
OP0 ve saat çalışırsa en fazla bir27624 mevcut storage/MSC gate'lerinden geçer.
MIDI output/input sırası ve callee-saved register/SP korunur.

Yeni giriş IRQ/masked/reentrant bağlamı ve storage/SCSI/worker/IRQ/class
owner varken reddedilir. READ worker içinde yeni task service1 döner;dış READ
buffer'ı bırakılmaz. Worker sırasında native IRQ suspend isteğini dondurur;
clock-stop dış READ/worker dönüp ortak bariyer tamamlandıktan sonra gerçekleşir.

Direct27624 caller'ları2587C,2DE92,53E78'dir. Son ikisinin callback/loop
bağlamları ve bütün owner grafiği kanıtlanmadığı için yalnız main patch edildi.
Native main'in geri kalanı/UI/timer/RTOS bekleme ve full task giriş/boot kapsam
dışıdır;test edilen ana pencere25870..25880'dir.

## Worker kanıtı ve model sınırı

READ65128 native enqueue/drain2C23A çalıştırır.24138 RTOS yield sınırı
stock648AE..648B8 worker loop'una geçer. R6,stok648C8 literal'inden pin'li
20006E60 global'idir;648B0 gerçek2C278 kuyruk worker'ını çağırır,dönüş nonzero
ise döngü sürer. Host ready/drain field'ını zorla temizlemez.

Loop wait/return kenarı648B8 açık bir emulator patch'idir. RTOS wake/yield,
priority/preemption ve task stack/context gerçek scheduler kanıtı değildir.
Alt flash RAM kopyası,bus ACK/flush/TXFE/XFRC ve IRQ register'ları modeldir.
MIDI IRQ ve MSC TXFE/XFRC callback'leri gerçek native kodla yürür. Test helper
service çağırmaz;her frame gerçek main penceresini çalıştırıp harici olay
stimulus'unu uygular. Checked RAM/boot ve gerçek silicon timing kanıtı yoktur.

## Test ve önemli açık

13 yeni testin10'u olumlu koruma/ilerleme senaryosudur;3'ü zorunlu negatiftir:

- Main hook yokken power request ve owned retry slot'u periyodik servis almaz.
- Hook varken normal query tam bir kez wire callback'e ulaşır;native READ /
  CSW,active-read suspend/cancel/wake,missing ACK ve reentry testlidir.
- Retained ledger debt kabul edildikten sonra suspend/FROZEN cl_poll bunu
  retry'ye aktaramaz. ss_quiet de ledger/TX borcu sıfırlanmadan kapanmaz.
  Wake dahil64 canlı main geçişi hâlâ pending bırakır. Bu protokol çözülmedi.

Son negatif,yalnız daha sık pump çağırmanın yeterli olmadığını gösterir.
Hardware reader iptali ile logical/admitted debt ayrı ömürler gerektirir;
queue/parser sıfırlamak veya kontrolleri atlamak veri kaybı/tekrar doğurabilir.
Sonraki somut iş,bu64-frame vakada payload/müzikal olay sahipliğini koruyarak
yeniden kurulumdan sonra debt'in ilerlemesini sağlamaktır.

447 toplam/87 aday regresyon/6 sınırlı kriter,baseline/build/production audit
PASS. Paket13 test/audit/trace PASS;probe/verifier exit2,NO-GO. Bu sayılar
beklenen negatifleri de içerir;tam runtime güvenliği anlamına gelmez.

## Kod ve kayıtlar

352B0807C800..0807C960;64B20048420..20048460;toplam2584B sentetik state.
SHA25631f38af23a9011bc05ed85c17566ec86a07a930b78de4712e586bfab6986df3e.
Yerel audit SP delta0,BL8,max16B frame,0 yeni maskeli bölüm/yerel loop.
Native çağrıların wall-time/cycle/latency sınırı kanıtlanmadı.

Kaynaklar src/midi_usb_task_prototype.py;scripts/{midi_usb_task_test_support,
audit_midi_usb_task_prototype,trace_midi_usb_task,probe_midi_usb_task}.py;
tests/test_midi_usb_task.py. Önceki kaynak/default codegen değişmedi.
Komutlar,hash/diff ve emulator-range/CRC manifest'i STATUS.md'dedir.

İlk test modeli stale disable-request'lerini fazla ACK'liyordu;ACK safhaya
sınırlandı. Legacy fake driver+5 full helper native pointer byte'ını bozuyordu;
debt vakası artık gerçek owned retry slot'u ile kurulur. İlk failure/error
logları saklıdır. Üretim Off/Stop kaybı,storage project short-read/live-pattern
alias,DIN input,gerçek USB clock/wake/iptal ve stale XFRC,diğer poll caller'ları,
full RTOS/Packs/project/boot/OOM/RAM-init ve production entegrasyonu açıktır.
Stok/candidate syx aynı;özel SD filesystem eklenmedi. M7 NO-GO.
