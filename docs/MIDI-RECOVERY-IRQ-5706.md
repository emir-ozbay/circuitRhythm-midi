# Güncel recovery adayı:native USB IRQ/reset/EP0

29 Ekim 2026. Offline emülasyon/register modelidir. **M7 NO-GO**;fiziksel
MIDI/USB/NVIC/PHY/DMA veya elapsed timing testi yoktur. Güncel hash STATUS'ta.

## Aynı negatifte FAIL→PASS

Dondurulmuş5dc7fd8a... adayında native646D0→4293E USBRST,TX FIFO'yu flush eder
ama5261C class-deinit'i çağırmaz. Guard JOB=ACTIVE,PHASE=OPEN kalır. Native
enum/address/configuration sonrası journal ilerlemez;Off0/Stop0 elde edilir.
Yeni aday aynı native akış/model/128 poll bütçesinde iki moddaOff1/Stop1 verir.
On daha önce gerçekten native TX FIFO/completion zincirinden geçirilir.

Aktif iş sırasında GPIO/device API yoktur. Native2C9B8 donanım stub'ı özgün
bytes'a döndürülür;4301A/52F52 gerçek register yazımlarını ve531A6 gerçek FIFO
word'lerini üretir.646D0 gerçek statik200054B4 handle'ını seçer.4293E→2C7AC→
42690→2AB36→40C22→5268E→268E0→268D0 completion yolu yürür. Setup packet'leri
native RX FIFO/setup IRQ→425A8/44DD8/42584/4259A→2AB08/2AB14→40B5A/40B7E
yolunu kullanır. Recovery kodu overlay'i veya sentetik completion token'ı yoktur.

## Üretim değişikliği

| Native yer /original | İşlev |
| --- | --- |
|4293E /2de9f04f |IRQ entry owner,generation snapshot,USBRST freeze |
|42D20 /69684908 |IRQ başladıktan sonra gelen USBRST freeze;APSR/original shift korunur |
|40B5A /f8b50446 |MIDI'yle başlayan native sınıf listesini retirement sonrasına ertele |

Önceki37 patch'e bu3 asserted/disjoint app detour eklendi. İlk512B vektör
değişmedi;646D0 adaptörü halen stock'tur. Native reset dalı kontrolü aynı IRQ
içindeki reseti iki kez saymaz. Nested IRQ snapshot'ı değiştiremez. Completion
IRQ içindeyse journal GEN'i giriş snapshot'ıyla eşleşmelidir.

Son20B state kuyruğu INIT root/config/busy,IRQ active/reset-seen veGEN snapshot
alanıdır;mevcut128B journal içinde kalır. WAIT_CONFIG eski kullanılmayan
header word'üdür. Ek heap rezervasyonu yoktur;seq layout çakışma kontrolü sürer.

USBRST yeni host configuration bekler ve önceki pending config'i iptal eder.
Native40B5A sınıf listesinin tamamı kuyruklanır;yalnız MIDI525B2'yi ertelemek
sonraki MSC constructor'ını öne geçirip MIDI global RX flush sırasını bozabilirdi.
Native liste ancak disable/ACK/AHB/FIFO1 retirement sonrası main poll lease'i
altında yürür. Stock MIDI→sonraki sınıf sırası korunur. İkinci parent testte
native ret0 boundary'dir,MSC/SCSI
transaction başarılı iddiası yoktur. RX ring canary ve iki DIN Off byte'ları korunur.

Public init queue ve constructor dönüşü generation karşılaştırır. Constructor
içinde yeni reset/eski configuration gelirse eski sonuç commit edilemez.
Bootstrap268D0 eski aktif journal'ı bitiremez;release retirement commit'inde
yapılır. On/Clock/SysEx replay edilmez;yalnız unconfirmed kapatmalar tekrar edilir.

## Test ve kanıt

17 yeni test:iki modda native vector/HAL/FIFO/completion;reset/enum/address /
config;coalesced reset+XFRC;geç USBRST;host config yokluğu;eksikACK/flush;
deconfig→config;constructor vepublic queue içinde reset;nested/duplicate IRQ;
64 Off;RX ring/DIN;quiescent reset vecompound list sırası. Bir test emeklilik
sözleşmesinden sonra zorla uydurulan eski XFRC'nin hâlâ ayırt edilemediğini tutar.

95 odaklı ve66 packaged test+6 sınırlı Faz1 ölçütü PASS. Önceki FIFO/parent /
MAIN/accepted-cancel/native USB-DIN probe'ları PASS. Strict decode/CRC/vector /
range/CFG/ABI PASS. Discovery584;tam584 tekrar koşulmadı. Önceki tam529 ve98
helper suite hash'leri tutulur;hepsi güncel SYX üstünde çalışmış değildir.

Kod3620B,0807F000..0807FE24;128B journal/1088B total reservation aynı.
30 maskeli yol,max41 komut,masked call/loop yok. IRQ wrapper24B/native
IRQ prefix64B;toplam88B,exception/nested callees toplamı değildir. Trampoline
delta'ları ayrı(-36 IRQ,-24 list-init);BL hizası8B. İlk init1155/1147 maskeli
komut değişmedi. Gerçek stack/RTOS/elapsed zaman kanıtı değildir.

## Sınır ve sonraki iş

FIFO olayları,ACK,flush/AHB,host config/cancel/completion veUART drain modeldir.
Başlangıç handle/list/RX-ring bağlaması sentetik RAM'dir;full boot değildir.
RX ring dolu olduğundan rearm native no-capacity dalındadır;gerçek app RX
payload teslimi bu17 testin konusu değildir. Tam MSC/SCSI,power/suspend,
fiziksel IRQ/PHY ve emeklilik sözleşmesi Faz1 uçtan uca/M7 doğrulamasında kalır.

Stock callback ABI'sinde hardware epoch yoktur. Model sözleşmesi ihlal edilip
eski XFRC yeni job'dan sonra üretilirse software bunu ayıramaz. Host kısmi
teslimi belirsizse Off/Stop tekrarı olabilir;exactly-once iddiası yoktur.
Bu sınırlar yeni özellik veya cihaz denemesi onayı olarak yorumlanmaz.

Sıradaki tek yerel iş,native başlangıç allocator/kurucuları üzerinden checked
RAM rezervasyonu,temizleme veOOM çağıranlarını doğrulamaktır. Stok dosya
sistemi araştırması bu oturumda genişletilmedi. Loglar `logs/recovery-irq-20261029`:
before/after SYX+manifest,comparison,tests/audit,session.diff vehashes.json.
