# Native timer IRQ → Main → player /5706

31 Ekim2026;exact3f979b70…/CRC5AB3F54B;üretim firmware'i değişmedi. M7 NO-GO.

## Kanıt ve gerçek çağrı sırası

Tek native reset;gerçek allocator/driver/timer/player/controller nesneleri.
Timer peer native Main kurulmadan önce yalnız40000C00 SR/EGR modelini kurar.
SR write-zero-to-clear yazıları shadow olarak saklanır,CPU okumadan ve IRQ
dönüş kontrolünden önce yayımlanır. Write hook içinde CPU register'ı okunmaz;
global RAM-write hook yoktur. Henüz elapsed time veya otomatik counter yoktur.

Native yapılandırma:CEN1,DIER2,PSC5999,ARRFFFFFFFF,CCR1=10;driver200001D0,
adım10,borç sınırı254. Sonlu compare olayı CNT=CCR1 veCC1IF sağlar. Vektör66
native64698 üzerinden6480C'ye gider:CCR1 güncellenir,LDREXB/STREXB borcu
artırır veSR bit1 temizlenir. FPU shim frame/context/SP korumasını denetler.

Main2586C→2677A,nesne20000358'i işler. Borç bir azalır,alt tablonun11. slotu
2B750'ye gider. Bu stok işlev üst20000370'in15 slotunu doğrudan sayar;ikinci
borç tüketimi yoktur. UI25958→2677A ayrı364/driver1DC yoludur. Eski sentetik
370 adaptörü bu native lifetime'da override ile reddedilir.

Toplam10690 IRQ üretimi,10690 Main tüketimi,106902B750 dispatch
ve10708 tam Main turu kaydedildi. Üretici64846/exception66 ve
tüketici2679E/exception0 yazıları ayrı izlenir. Boş IRQ değişiklik yapmaz;
tükenen compare kredisi periferiyi/RAM'i değiştirmeden reddedilir.

UI ile8 track'te32-adım sparse pattern kuruldu;iki modda193 microstep
commit/player,0..31..0 cursor,544 native64B LED veiki sayfa-sınır kontrolü
geçti. Çalarken mod reddi,raw/metadata korunumu ve8 açık notada native Stop
flush doğrulandı. Mod/iki UART portu başına40 On/40 Off,193 Clock,FA/FC;
tüm notalar sıralı kapanır. MIDI fault,proje I/O,ek tahsis/NOR artışı0.

## Sonlu ADC ve DSP girdileri

İlk yeniMain koşusu371D5'te strict DSP reddi verdi. Native644CC sonucu
sağa8 kaydırır,128 ve üstünüFFFF yapar.4096 explicitFFFFFF yanıtından
3563 tanesi native idle sonucuna dönüştü.
Bu bir kayıt yapılmayan DSP senaryosudur;DSP kodu/değer doğruluğu değildir.
Mailbox başlangıç script'i aynı;sonraki adres/order/exhaustion reddi korunur.

UniformADC2048,calibration1500 altında kalibre pil1499/pil0 üretir. İlk1000
olayda native düşük-pil shutdown/save gerçekleşti;başarısız koşu korunur.
Kapanış kodu değiştirilmedi. Yeni profile yalnız native DMA tamponuna32 adet
(referans1500,pil3700,mux2048) üçlüsü yazılır. Native IRQ72/27762 kopyalar,
265BA/2BEF4 kalibre eder ve sampler pil verisini üretir.128 ADC kredisinden64
kullanıldı;derived yüzde/store/flag seed edilmedi. Native pil sonuçları:
`[100, 100, 100, 100, 100, 100, 100, 100, 100, 100]`. Bu değerler ölçülmüş fiziksel voltaj değildir.

## Testler ve sınırlar

2 exact-SYX unittest PASS:90 sentetik boundary durumu tek unittest olarak,
IRQ/Main32-step ömrü ayrı native reset unittest'i olarak. Sentetik fixture
RAM/peripheral/debt seed eder ve handler'a direct entry kullanır;native
reset kanıtıyla karıştırılmaz.29 örtüşen hedefli test veaudit PASS.
Önceki149 yeniden koşulmadı;yeni2 ile aynı image üzerinde151 ayrı paket
testinin kanıtı vardır. Verifier151/core-only144;yedi uzun test core-only
dışındadır. Host suite kurulumu emülasyon değildir.

Autonomous clock,duvar zamanı,tempo/jitter,NVIC priority/nesting,physical
MIDI/LED,GPIO scan/input queue,DSP execution ve USB RX/MSC/power kanıtı yoktur.
Existing strict SPI,NOR/ADC/USB ve disabled-DWT/non-nested-FPU sınırları
sürer.2184B workload payı genel worst-case değildir. Sonraki:uzun gate ve
farklı notalarla64 canlı stok ses,sonra kayıpsız native Stop/Off/FC.

Kanıt:`logs/recovery-native-timer-irq-20261031/probe-charged/report.json`;
önceki negatifler/pilot/sentetik dönüştürme raporları aynı klasördedir.
