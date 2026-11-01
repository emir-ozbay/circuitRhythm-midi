# Native5706 Play/Stop ve32-adım player akışı

31 Ekim2026;yerel Unicorn emülasyonu,aynı3f979b70… firmware. M7 NO-GO.

Tek native reset,2331 tahsis,2004EA98 heap/2184B kalan workload payı.8 player
`08068D24` ve raw span'leri gerçek factory'den gelir;player+8 ile StepView+1C
aynı store'dur. Host player/proje/store/page/LED/owner/FIFO seed etmez.

UI ile Sequencer moduna geçilir;her track'te Pattern Settings4/page21/pad15
End31 ayarlar. Main8'de1/16/17/32 notaları kurulup tam8B kayıtları doğrulanır.
Sonra aynı açık proje Normal ve Sequencer modlarında sırayla çalıştırılır.

Play17 transportu1 yapar. Mevcut service_timer_ticks adaptörüne sonlu1/16
birim AppTimer borcu verilir. Native2677A,boot'ta kurulmuş timer slotlarını ve
46DBC dispatch/clock/store listener zincirini işletir. Native551DE/5526E→
4AEEE/4AFBC gerçek player'a ulaşır. Her player/modda193 commit tam sırayla
`(pattern0,step=i//6%32,microstep=i%6)` olur. Timer/input/Main adapter'larının
CPU/FPU/SP/stack sınır kontrolleri yürür;firmware talimatı değiştirilmez.

Her adımda8 track seçilir ve4DD1C compositor çağrılır. Toplam544 adet64B
görüntü ve32H durum alanı kontrol edilir. Native5D458/5D290 player zamanını
bit6'ya bağlar;tek cursor biti/LED indeksi1 gerçek veriden gelir. Eski bit0
etiketi edit/recorder zamanını bununla karıştırıyordu;eski sentetik test kendi
renk dalını sınamayı sürdürür,koşan player kanıtı olarak kullanılmaz.

Normal üst16 sayfa ve stok alt16 düzeni korunur. Sequencer tam32 kaynak
hücreyi aynı anda birleştirir. Yardımcı görünümün hatırlanan sayfası1 kalabilir;
ana görünümün etkin ofsetinin0 oluşu ve32 doğru adım kaydı esas alınır. İlk
yanlış saklanan-sayfa=0 varsayımı probe-first/tests.txt ve failure-RAM ile
korunur. İkinci koşunun saklanan sayfa değişmez varsayımı da probe/ altında
korunur. Son koşu etkin ofset/full-grid kontrolüyle ayrı resetten geçmiştir.

İki modda da16→17 ve32→1 kesintisizdir. Çalarken Shift+SampleRec modu
değiştirmez. Wrap sonrası8 canlı nota varken Stop17,native552F6→4AED8'i her
player'da bir kez çağırır;aktif gate listeleri boşalır. İki UART TDR akışı
aynıdır;mod/port başına40 On/40 Off ve Start/Clock/Stop çözülür. Running status
ve realtime ayrılır;her On sırayla tek Off ile kapanır,Stop son mesajdır.

Runtime raw proje SHA `12cdf0322cd35cf2c1428b7d4b8373e23805deb0b0f56d8dd2cd73cfb5dbd4e5` çalma/Stop/mod
geçişlerinde aynıdır. Proje I/O,ek tahsis,NOR artışı0;metadata/canary/image
korunur,invalid erişim ve MIDI fault yoktur. Byte/range/CRC/CFG/ABI audit ve28
örtüşen hedefli test PASS. Yeni1 exact-SYX unittest ile aynı image'de149 ayrı
paket testinin kanıtı vardır;önceki148 bu tur tekrar koşulmadı.

## Sınırlar ve devam

Timer borcu doğrudan sentetik test girdisidir;donanım counter/status/IRQ
üretimi veya geçen fiziksel zaman değildir. Main 688 tur,sonlu
DSP802F=0 veUART TXE/native IRQ53/54 hizmetiyle yürür. Fiziksel hat teslimi,
USB RX/NVIC önceliği,jitter,gerçek DSP/sample süresi,Gate tie ve olasılık
istatistiği bu sonuçtan çıkarılamaz. Önceki strict SPI,NOR/ADC/USB,disabled
DWT ve non-nested FPU varsayımları sürer.

Sonraki adım:40000C00/vector66 native IRQ'sının borcu üretmesini sonlu
peripheral olaylarıyla modellemek;Main'in borcu tüketmesini aynı testte
göstermek. `timer-boundary.json` yalnız stock vektör/native RAM okumasıdır,
IRQ yürütme kanıtı değildir. Üretim kodu/firmware değişmedi;cihaza erişilmedi.
`probe_timer_boundary.py` ayrı sentetik RAM önkontrolüdür:90 SR/DIER/CNT/CCR1 /
borç durumu PASS. Gerçek vektör/handler çalışır;RAM ve peripheral girdileri
seed edilmiştir,direct entry kullanılır. Native reset/FPU IRQ/NVIC veya
geçen zaman kanıtı değildir ve149 testin üzerine ek unittest sayılmaz.

Kanıt:`logs/recovery-native-playback-20261031/probe-final/report.json` ve hash bundle.
