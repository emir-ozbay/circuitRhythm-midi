> Güncel31 Ekim /Probability — Native yardımcı görünüm sayfa/pad grubu
> tamamlandı: Note1/7, Velocity2/Gate3, Pattern Settings4, Microstep5, Probability6.
> Yeni mode6 testi:512 üst pad/64 uç/128 LED/32 zengin Mutate PASS;26 hedefli PASS.
> Önceki147 aynı image'de, tekrar koşulmadı. Genel verifier148/core-only143.
> Firmware3f979b70…/CRC5AB3F54B, üretim ve1088B RAM aynı; M7 NO-GO.
> Sonraki iş: native Play17/Stop17→player/scheduler→1–32 playhead izi.
> STATUS veMIDI-RECOVERY-PROBABILITY-5706.md güncel; altı tarihseldir.

---

# Native Microstep — 31 Ekim 2026

Güncel aday ve biten koşunun sonuçları `STATUS.md` içindedir. Bu belge
Microstep testinin sözleşmesini ve sınırlarını açıklar. Fiziksel cihaz/port
erişimi yoktur;M7 NO-GO.

## Nesneler ve stok davranışı

Microstep mode5,Gate düğmesinin iç11 numarasıyla açılan ikinci görünümüdür.
Üst16 pad aynı track'in StepView'ına,alt16 pad `grid+DC+4*track` nesnesine
gider. Vtable08067FBC;pad handler08056F7C,release08052116'dır. Alt pad'in
yerel numarası0..15'tir;stok transform fiziksel16'yı çıkarır.

`view+C` ST1,`view+10` ST2,`view+14` seçili adım store'udur. Bu pointer'lar
aynı StepView'ın gerçek store'larıyla karşılaştırılır. `view+24` varsayılan
nota store'udur. Başlangıç nesnesi,store veya page RAM'i host'ta kurulmaz.

Native56F7C yalnız yerel0..5'i düzenler;yerel6..15 işlem yapmaz. Geçerli
girdide maske `old XOR (1<<local)` olur. Altı bit64 kombinasyon üretir;
adım sayısı32'dir. Native54AE0/5E71C aktiflik/maske yolunu belirler.

Seçili ilk pattern'deki adımın raw alanı
`2E4+track*5140+step*8`'dir. Microstep maskesi bu8B kaydın byte2'sidir.
Maske sıfır olmadan değişiyorsa yalnız bu bayt değişmelidir. Böylece mevcut
nota,velocity,gate,probability,sample flip ve bayraklar korunur.

Son bit kapandığında stok70FC temizliği ve56F7C devamı boş adım oluşturur:
`00 06 00 00 07 FF 00 00`. Boş adımda bir bit açmak varsayılan notayla,
gate6,velocity96,probability7,sample flipFF ve flags0 ile kayıt oluşturur.
Bu reset davranışı bozulma olarak yorumlanmaz. Native durdurulmuş görünüm,
üst pad bırakıldıktan sonra da son seçili adımı alt pad'lerle düzenler;
test bu yolda yeni bir C0 sahibi oluşmadığını ayrıca kontrol eder.

## Kapsam

Test8 track ×Normal/Sequencer ×iki sayfayı aynı resetten kurulan nesnelerde
dolaşır. Üst16 pad'in512 fiziksel-pad/adım eşlemesi sınanır. Adresler0..31
aralığındadır;ikinci sayfa son adım32'yi de kapsar.

64 düzenleme senaryosunun ilk uç pad'i Shift'siz,son uç pad'i Shift ile
sınanır. Her senaryoda altı bit sırayla açılır/kapanır,her bit tek başına
açılıp kapatılır ve işlem yapmayan on pad denenir. İki çalışma modunda
track0/ilk sayfa için Gray sırası64 maskenin tamamını dolaşır. Her girdinin
native handler nesnesi/yerel pad numarası ve tüm proje raw farkı denetlenir.
Değişiklik yalnız hedef adımın8B alanında kalmalıdır.

32 ek senaryoda native Velocity/Gate girişleriyle velocity120/gate96
oluşturulur. Microstep bit1 eklenip çıkarıldığında8B kayıt aynen geri
gelmelidir.32 durdurulmuş/üst pad basılı değil senaryosu da son seçili adımın
stok düzenleme davranışını sınar. Physical pad30 geçerli microstep değildir;
buna rağmen basılıyken fiziksel sahipliği mod geçişini reddetmelidir.
Release sonrasında fiziksel ve C0/bit3 sahipleri boşalmalıdır.

Native5709A ilk altı LED'i stok62AB0 tablosunun42/44 renkleriyle oluşturur.
Diğer on LED sıfırdır. Her değişimde bu tampon denetlenir. Her senaryoda
maske0 ve63 için native4DD1C compositor'ının üst32B StepView/page kaynağı
ve alt32B Microstep kaynağı eşleşmelidir;toplam128 bileşimdir. Bu fiziksel
LED veya mikro-adımların zamanlaması ölçümü değildir.

## Yürütme ve sınırlar

Native Main her16 callback girdisinde ve mod sınırında çalışır. Sonlu2048
açık802F=000000 yanıtı ve65536 UART TXE kredisi native tüketiciyi ilerletir.
IRQ53/54,FPU frame ve TDR yazıları kullanılır;FIFO/consumer/fault/owner RAM'i
host'ta temizlenmez. Tam image,canary,metadata,raw pointer,heap,tahsis,
proje I/O ve NOR mutation sayaçları karşılaştırılır. Microstep native kodu
stokla bayt bayt aynıdır.

Controller callback girdisi GPIO/input kuyruğu değildir. Durdurulmuş
transport denetlenir;oynayan sequencer'da mikro-adım/gate/Note Off/Clock
zamanlaması bu testin kanıtı değildir. DSP/NOR/ADC/USB sınır modelleri,
disabled DWT ve non-nested FPU varsayımları sürer.2184B heap payı yalnız bu
workload için gözlemdir. Fiziksel MIDI teslimi ve en kötü durum zaman/RAM
yeterliliği ileri sürülmez.

`scripts/probe_recovery_microstep.py` bir paket unittest'ini kaynak
codegen=image=SYX koşuluyla çalıştırır. Kaynak unittest ile probe aynı
koşudur,iki ayrı başarı sayılmaz. Başarıda da M7 NO-GO nedeniyle exit2
döner. Genel verifier bu testi içerir;`--core-only` dört uzun native UI
matrisini açıkça hariç tutar. Testler `.venv\Scripts\python.exe` ile ve
`-O` olmadan çalıştırılır.
