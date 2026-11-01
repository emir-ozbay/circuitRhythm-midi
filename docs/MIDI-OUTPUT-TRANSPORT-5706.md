# 5706 gerçek MIDI çıkış kuyruğu ve Clock/Stop backend kanıtı

Güncelleme: [MIDI-USB-YIELD-5706.md](MIDI-USB-YIELD-5706.md), gerçek main poll
sırasında USB burst kaynaklı Stop kaybını ve12 bayt cave düzeltmesini açıklar.
136/70 test PASS; hazır sürücüde burst PASS, stalled sürücü ve dolu FIFO Off
riski sürer. Aşağıdaki128/62 ve hash önceki aday kaydıdır; NO-GO devam eder.

26 Ekim 2026. Fiziksel cihaz/MIDI/USB erişimi yok; Capstone ve Unicorn.
**Karar: CRITICAL_RUNTIME_PROBE_FAILED / NO-GO.** 128 testin geçmesi,
aşağıdaki negatif güvenlik deneyinin başarısızlığını ortadan kaldırmaz.

## Yeni somut bulgu: dolu stok kuyrukta Note Off kaybı

Önce Note On48, gerçek çıkış worker'ı ile son sürücü sınırlarına teslim edilir.
Sonra consumer poll yapılmadan64 Clock üretilir. Her portun stok64 mesajlık
FIFO'su dolar. Ardından Note Off48 gönderilir ve worker tekrar çalıştırılır:

| Her üç portta | Teslim sayısı |
|---|---:|
| Note On48 |1 |
| Clock |64 |
| Note Off48 |0 |
| Son poll sonrası kuyrukta kalan |0 |

Off tekrar denenmez; sıra boşalınca da geri gelmez. Kuyruk header/buffer baytları
başarısız enqueue sırasında aynıdır; RAM taşması görülmez. Buna rağmen son
alıcıda açık notanın eşleşen Off'u yoktur: harici stuck-note riski.

Bu kontrollü producer-before-consumer sıralamasıdır. Canlı cihaz scheduler'ının
64 Clock boyunca consumer çalıştırmayabildiği henüz kanıtlanmadı. Boot297A8
r2=40h ile gerçekten64 slot ister; deney azaltılmış test kapasitesine dayanmaz.
Biriken output-clock kadar diğer MIDI olayları da aynı sabit FIFO'yu kullanır.

Çıkış adapter/router/port kodunun31F08..3223C,4016C..4042C,2986A..298B4,
468FA..4691A bölgeleri stokla bit-bit aynıdır. Bu yamanın eklediği bir FIFO
değişikliği değildir. Kayıp, FIFO40DC4'ün yer yokken0 dönmesi,401FE'nin bunu
diagnostic23690'a bildirmesi,2986A'nın başarısız portu kaydedip devam etmesi ve
31FC6'nın başarısızlığı tekrar teslimata çevirmemesiyle oluşur.23690 stokta
yalnız push r1-r3; add sp,12; bx lr içerir; fatal assert veya gerçek log değildir.
Deneyde bu fonksiyon değiştirilmedi, çağrıları izlendi; tamamlanan çağrılarda
SP ve r4-r11 korunumu da harness tarafından denetlendi.

scripts/probe_midi_output_queue.py varsayılan olarak paketlenmiş SYX'i açar,
bu karşı deneyi tekrarlar ve kayıp varsa exit1 verir. Sonuç:
logs/output-queue-probe.json. Verifier aynı deneyi doğrudan paket imajıyla yapar;
runtime_safety_probes alanı, testi geçti diye bu kaybı PASS göstermez.

## Çalıştırılan gerçek zincirler

| Bileşen | Bayt/disassembly ve emülasyon |
|---|---|
| MIDI adaptörü |31F08 gerçek ctor; Clock alt nesne+8/vtable6719C ->32084/32088; transport alt nesne+4 ->31FF0/32004/32024; nota31F9C/31FC6 |
| Global dispatch |468FA ->2A666 enable gate ->2986A mask fanout; global router pointer20006F04 |
| Port FIFO |4016C gerçek ctor ->40D9C;64*3+1=193 bayt ring;401FE ->40DC4 enqueue;40DEE ->2A470 dequeue |
| Worker |297DE port poll ->402B4 ->401CA/402FC/403A2/403EC; son sanal driver accept/flush çağrıları |
| Clock backend |3223C ve3328C gerçek ctor;33D30 ->332DE/32964/332EC/329C0; ilk F8 ->32BB6 özel dal ->32A82; Stop33EAE ->33340/32A06 |

Boot27D72/27E32'deki adapter+8/+4 bağları sentetik grafikte kullanılır.
32BB6 alıcısı artık stub değildir; gerçek31F08 çıkış adaptörüdür.3328C backend'i
aslında clock başlatma/durdurma nesnesidir; tam pattern nota üreticisi değildir.
Native store kurucuları3FB50 ve gerçek listener kayıt/bildirimleri de yürür.

## Test kapsamı ve kalan sınırlar

Yeni8 test; scripts/midi_output_test_support.py ve tests/test_midi_output_transport.py:

- DIN Start/Clock/Stop/Continue'un üç FIFO'ya tam sırayla teslimi.
- Tamamlanmış Note On/Off çifti ve Clock kuyruktayken mode toggle'ın baytları
  koruması; iki modda stok adapter kanal/nota çıktısı.
- Gerçek clock backend'inin ilk Clock dalı ve Stop state temizliği.
- İki modda USB girişinden native worker'ın son sürücü çağrısına mesaj sırası;
  boş kuyruğu yeniden poll etmek ek mesaj üretmez.
- Sürücü full olduğunda worker kuyruğu tüketmez; full kalkınca On/Off sırası korunur.
- Dolu64 slotta Off kaybı ve RAM korunumu karakterizasyonu; ayrı safety probe FAIL.
-8 kanal ve0/60/127 notalarda iki modda ring sarılması.
- Gerçek native Stop +297DE poll; input receiver held notası Off gelene kadar
  mod geçişini kapatır, eşleşen Off guard'ı açar.

Son driver ready/full/accept/flush yöntemleri kontrollü sınır stub'larıdır.
Wire/DMA/ISR yoktur.46DDE/46E2A timer servisi,30B60 tempo donanım çıkışı ve
46E44 clock GPIO çıkışı yalnız emülatörde stub'dır. Clock present flags+54=3
fixture girdisidir; gerçek zamanla kaynak tespitinin doğrulanması değildir.
İlk Clock'ta timer isteği yakalanır, timer callback'inin scheduler tarafından
teslimi çalıştırılmaz. Diğer native store listener'ları çalışsa da bütün boot
listener grafiği yoktur. Nota olayları stok adapter'a doğrudan verilir; gerçek
sequencer adım üreticisinden başlayan Note On/Off sahiplik kanıtı değildir.

İlk native-ctor denemesi eski sentetik store'un listener alanı olmadığı için
null read verdi. Gerçek3FB50 kurucusu/listener alanı kullanılarak düzeltildi.
İkinci hata eksik GPIO sınırındaydı; bu da ayrı hardware stub'ıyla modellendi.
Firmware HardFault'u olarak sayılmadı. logs/output-native-{first,second,
invalid,invalid-second}.txt ara bulguları korur.

## Doğrulama ve sonraki görev

Build,128 unittest,62 packaged regresyon ve6 sınırlı ölçüt PASS. Baseline ve
bağımsız SysEx/CRC/vector/diff/Capstone/yerel CFG stack audit PASS. Negatif MIDI
queue probe FAIL; verifier exit2, CRITICAL_RUNTIME_PROBE_FAILED / NO-GO.
Loglar logs/output-final-{build,all-tests,verify,baseline,audit}.txt ve
logs/output-final-audit/. Paket raporu:
logs/phase1-verification-20261026T194124Z/report.json.

Firmware/SysEx baytları değişmedi: SHA256
058feb2ef8921168b9113edc5a3704184cc4a634c2c9838ba3533cbeeab7cdce,
imaj CRC7F9DE544,19 patch/1319 değişen bayt. Stok pin ve ilk512 bayt korunur.

GO için3 ana kapı sürer; ilkinde artık somut queue-loss karşı deneyi vardır.
Sonraki tek görev:297DE worker poll'unun gerçek task çağrı sırasını ve ISR/DMA
ready/full ömrünü izlemek;64 doluluk durumunun erişilemezliğini kanıtlamak veya
güvenli backpressure/Off recovery politikası geliştirmek. Miras stok storage
hata/recovery ile tam boot/OOM/PRIMASK zaman bütçesi de açık. Kuyruğu büyütmek
tek başına sınırlı consumer gecikmesi veya Off teslim garantisi değildir.
