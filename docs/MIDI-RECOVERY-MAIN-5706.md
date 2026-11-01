# Native main ve ilk görev penceresi — 5706

30 Ekim 2026. **M7 NO-GO.** Firmware ve üretim kaynakları bu turda değişmedi.
Çalışma önceki reset/static init kanıtını native main ve görev kurulumuna
genişletir. Cihaza veya fiziksel MIDI/USB API'sine erişilmedi.

## Ölçülen pencere

Exact recovery SYX resetten başlatılır. Heap limit/current,nesneler,kurucu
dönüşleri veya görevler hazırlanmaz. Native main`25688`,kurucular,allocator,
FreeRTOS görev oluşturma ve idle kurulumu çalışır;`25430` port/scheduler
girişinde durulur. Stock ile **129 tahsisin boyut/adres sırası aynıdır**.
İlk heap`20006F60` → static init sonu`20007B90` → scheduler girişi`2000B618`.
Checked limit`2004F320`,state üstü`2004F760` korunur.

Global router`20009FBC`;native üç port`2000A168`,`2000A254`,`2000A340`.
Recovery core entry'leri bu üç gerçek portla native ctor hook'unda bağlanır.
State'te init sonrası yalnız bu üç pointer yazılır;seq/journal geri kalanı
değişmez. Önceki hazır heap/router/driver fixture'ına dayanmayan boot kanıtıdır.

| Native görev | Entry | Stack başlangıcı | Stack sonu = TCB başlangıcı | Kapasite |
| --- | --- | --- | --- | --- |
| Main |08025771 |20007B9C |2000879C |3072B |
| UI |08025941 |2000891C |2000911C |2048B |
| Storage |0806487D |20009184 |20009684 |1280B |
| Content |0802AD29 |200096F8 |20009BF8 |1280B |
| IDLE |08025005 |2000B1BC |2000B5BC |1024B |

Aralıklar `[başlangıç,son)` biçimindedir;TCB92B ayrıca denetlenir. Beş stack /
TCB birbirine ve reserved alana taşmaz. Native17-word frame içindeki argüman,
entry,xPSR,EXC_RETURN ve register dolgusu byte olarak testlidir. Bu beş görevin
tam çalışma ömrü veya maksimum stack kullanımı kanıtı değildir.

Main kurulumu penceresinde minimum MSP`2004FF08`,gözlenen stack248B,state
üstünden1960B aralık vardır. Sonra native ready-list selector`24F84`,IDLE'dan
Main TCB'sine geçer. Model,Main'in kendi native frame'ini unstack eder;task /
current-TCB RAM'i yazmaz. PSP`20008798` → min`200086B8`:bu ilk görev
penceresinde224B kullanım. Bir8B tahsisle heap`2000B620` olur;`2C23A` işçi
isteği girişinde durulur. İşçi henüz çalışmadığından **son heap high-water ve
Main initialization tamamlandı denmez**. Eski fixture`2004EA98` hâlâ ölçüm değildir.

## Açık model sınırları

- RCC on/ready ve clock-switch yanıtları anlıktır;PLL/saat zamanı modellenmez.
- QSPI registerları host RAM'idir. Scripted ID cevabı`EF4018`,diğer veri0;
  gerçek flash içeriği veya cihaz modeli kanıtı değildir. Dört native
  `645E0 → 2AA8A` IRQ adaptörü yürür.
- SDIO CMD0 gönderilir;CMD8 ve100 CMD55 için response timeout üretilir.
  Native`64762 → 24968` bunu işler. Yanıt veren kart,filesystem veya pack /
  project açılışı bu fixture'da yoktur.
- Native SysTick adaptörü,time/yield sınırlarında kontrollü çağrılır. İstek
  aralığı komut gözlemine bağlı sentetiktir;elapsed timing değildir.
- IRQ adaptörleri CPU context save/restore ile normal native çağrı olarak
  yürür. NVIC öncelikleri,nesting,hardware/FPU exception frame'leri ve gerçek
  scheduler/PendSV geçişleri modellenmez. Görev seçimi native olsa da ilk
  frame'in unstack işlemi model sınırıdır. `25430` port başlangıcı çalıştırılmaz.

Clock ACK veya QSPI completion verilmezse native kurulum ilerlemez;test modeli
allocation/constructor sonuçları uydurmaz. Bu negatifler korunur.

## Düzeltilen test izleyicisi

Global `UC_HOOK_MEM_WRITE`,boş callback ile bile Unicorn2.1.4 M-class'ta
stock IT/conditional-STM zeroer'ının bayrak/ITSTATE davranışını bozabiliyor.
48B temizleme dönmeyip tampon dışına taşar. Aynı firmware,sınırlı izleyiciyle
tam48B temizleyip döner. Bu bir **emülasyon izleme hatasıdır;firmware hatası
diye yamalanmadı**. Heap pointer ve checked state için yalnız iki gerekli
adres aralığı izlenir;register okumaları code callback'te tutulur. Snapshot
ilk bump'ın sonraki instruction boundary'sinde alınır;bump yalnız current
alanını yazdığından reserved state'in bump öncesi değeri de aynıdır.

İlk “callback içinde register okumak tek neden” hipotezi yanlış çıktı;boş
callback de sorunu üretir. Yalnız register cache etmek yetmez;adres kapsamı
daraltılır. Ayrıca her komut sınırında timer dispatch,tahsis girişini kesip
yeniden ziyaret ederek sayımı130'a şişirebiliyordu. Timer dispatch artık
time/yield sınırındadır. Gerçek129 heap-current publication ve aligned byte
toplamı ayrı doğrulanır. Artık stock/candidate sıra ve boyutları eşleşir.

8 yeni test;111 odaklı/82 packaged +6 sınırlı Faz1 ölçütü PASS. Bu sayılar
örtüşür. Discovery600;tam600 bu turda koşulmadı. Önceki529/98 kayıtları
korunur. Eski allocator OOM negatif/yeni terminal fault karşılaştırması,
strict transport/CRC/vector/range/CFG/ABI ve mevcut IRQ testleri PASS kalır.

**Sonraki tek somut iş:** Main'in `2C23A → 2C260` işçi isteğini native worker /
PendSV zinciriyle tamamlatıp Main'i`25864` çalışma döngüsüne kadar izlemek;
runtime/controller/project kurulumunun kalan tahsislerini ve görev stack'lerini
ölçmek. RX/MSC/power/storage ve Faz1 uçtan uca kapıları da kapanmadan M7 GO yoktur.

Komutlar/hash'ler:[STATUS.md](STATUS.md). Kaynak diff/pin,donmuş aynı firmware,
probe ve test kayıtları:`logs/recovery-main-20261029` (çalışma29→30 Ekim).
