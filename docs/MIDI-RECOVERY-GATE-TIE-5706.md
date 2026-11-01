# Gate süresi ve tie bitinin kapanışı — 31 Ekim 2026

Güncel sonuçlar STATUS.md'dedir. Üretim firmware'i c9a87a9d… /CRC BEB0D013
olarak kalır. Bu çalışma yerel byte analizi ve Unicorn testidir;M7 NO-GO.

## Üç ayrı kanıt

**Byte analizi:**5706 stock pin'i doğrulanır. Native56D54 Gate düzenleyicisi
packed store'un8..15 alanına1..96 yazar. Ana kayıt tuple'ında bu byte1'dir.
Player4AFBC byte6 bit0'ı da okuyup4B0D4'e ayrı tie argümanı verir. Aynı
pitch'in sonraki hazırlığında retained bitmap,Off/On yeniden tetiklemesini
bastırabilir. Gate düzenleyicisinin süre yazması,tie bitinin UI'de açıldığı
anlamına gelmez. İncelenen recorder48E70 gate'i96'ya sınırlar ve4901A..49048
flags alanını sıfırlar;bu da ayrı tie gesture'ının kanıtı değildir.
Disassembly `logs/recovery-native-tie-20261031/native-gate-stock.txt` içindedir.

**Sentetik RAM:**`tests/test_recovery_tie.py` mevcut synthetic player/voice
fixture'ını recovery'nin gerçek port kurucusu/kayıtlarıyla kullanır. Pattern
tuple'ı,mode ve nesneler açıkça fixture girdisidir. Native player hazırlama,
commit,gate expiry,ownership,router ve recovery yürür;son sample/final driver
sınırları stub'dır. Üç unittest,iki mod ×8 track ve iki adım sınırında toplam
80 alt durum içerir;80 bağımsız test veya80 native reset diye sayılmaz.

- Aynı pitch,tie1→tie0:16/17 ve32/1'de tek On;ardından doğal gate expiry tek
  Off üretir. Son flush ikinci Off üretmez.32 alt durum.
- Farklı pitch,tie1→tie0:iki On bastırılmaz;flush iki sesi kapatır.16 alt durum.
- Aynı pitch,tie0→tie0:Off önce,yeni On sonra;flush son sesi kapatır.32 alt durum.

Bu üç test geçti. Üç portun paketleri ve firmware context/active/TX baytları
denetlenir. Süre fixture'ın manuel native tick çağrılarıdır;native UI/timer
erişilebilirliği veya fiziksel MIDI iddiası değildir.

**Native reset/UI/IRQ:**Yeni uzun test gerçek reset nesnelerini kullanır.
Controller callback'leriyle8 track'e tek vuruş,note72,velocity96,gate1/6/95/96
yazılır. Kaynak adımlar sırasıyla0,15,16,31,0,15,16,31;gate'ler
1,6,95,96,96,95,6,1'dir. Pattern Start0/End31/sync0/direction0 da UI'de
ayarlanır. Tie flag'i0 kalır;bu test UI tie oluşturma iddiasında bulunmaz.
Tek native reset ömründe iki mod geçti:7114 compare IRQ,7158 tam Main turu,
player/mod başına387 sıralı microstep commit. Gate bitleri/proje aynı kaldı;
context/active/TX000000,proje I/O0,ek tahsis/NOR artışı0.

En hızlı stock sync0 seçimi uzun gate/pattern sınırlarını daha az IRQ girdisiyle
geçmeye yarar;global MIDI Clock hızı değiştirilmez. Native rate tablosu
68D9C'de [2,3,4,6,8,12,16,24]'tür. Sync0'da bir adım iki MIDI Clock ve altı
microstep içerir. Bir Main turu üç microstep commit'ini atomik işleyebilir;
385 ayrı commit'te Main sınırı bulunacağı varsayılmaz. Test385..387 arası
sıralı commit'i ve129 F8'i,iki tam32-adım turu +ilk adımın başlangıcı olarak
denetler. Bu geçen süre/tempo ölçümü değildir.

16/17 sınırında source15/gate95;32/1 sınırında source31/gate96 için native
aktif liste kontrol edilir. Off'un yalnız yeniden tetikleme veya Stop ile
gelmiş olması yeterli değildir:caller4AF9F doğal gate expiry ile caller4AEE5
Stop flush ayrı sayılır. Per-mode beklenen15 doğal Off +3 Stop Off,18 On,
Start/129 F8/son tekFC'dir. Stop öncesi aktif player sayıları
[1,0,0,1,1,0,0,0] olmalıdır. İki native UART akışı eşleşir;sonda tüm player
listeleri boş,proje aynı,context/active/TX000000 olmalıdır.
Bu beklentilerin tamamı iki modda geçti. Native Gate1/6/95/96 için doğal
Off'a kadar compare-event sayıları27–28,55–56,861,889 oldu. Aynı On'daki
encoded gate clock unit'leri1,2,31,32'dir. Bu ölçümler
`expiry-timeline.json` içindedir;gerçek saniye/baud/jitter diye sunulmaz.
Heap2004EA98/2331 tahsis ve476 başlangıç NOR mutation aynı kaldı.

## Deney düzeltmeleri

İlk iki keşif koşusu tamamlanmadan durduruldu. Eski test planı hızlı pattern
sync'ine rağmen385 MIDI Clock ve tam385-commit Main sınırı istiyordu. Bu
beklentiler stock rate tablosuyla gerekçelendirilemiyordu. Başarı veya firmware
hatası diye sayılmadılar;cancelled.json ve önceki helper saklandı. Yeni test
global clock/pattern microstep ayrımını ve atomik batch sınırını denetler.
Windows Ctrl-C bu iki yardımcı süreci sonlandırdı;VM/RAM düzeltilip sürdürülmedi.

## Kapsam ve tekrar üretim

Native test sonlu TIM CNT/CC1IF/SR girdileri,IRQ66/FPU frame adaptörü,tam Main,
UART TXE IRQ'ları,ADC1500/3700/2048 ve DSP recording-idle cevapları kullanır.
Pattern/store/FIFO/fault/owner/timer borcu host'ta seed/repair edilmez.
GPIO/input kuyruğu,NVIC arbitration/nested IRQ,gerçek DSP ve fiziksel MIDI/
baud/tempo/jitter kanıtı yoktur. USB note yönlendirmesi bu native projede
kapalıdır;iki UART bayt akışı USB64-ses teslimi yerine sunulmaz.

Tie bitini native UI'den veya stock proje yüklemesinden1 yapan yolun
erişilebilirliği açıktır;onu kapandı diye saymıyoruz. Çalarken çeşitli
microstep/probability,partial Load/short-read,birleşik RX/USB/MSC/power ve
genel en kötü RAM/stack/zaman bütçesi de ayrı işlerdir.

`.venv\Scripts\python.exe` ile,`-O` olmadan:

- `scripts/probe_recovery_gates.py logs/recovery-native-tie-20261031/probe-final`
- `scripts/audit_recovery_candidate.py logs/recovery-native-tie-20261031/audit`
- `PYTHONPATH=scripts;src;tests` ile `-m unittest test_recovery_tie
  test_dense_stop_patch test_step_routing test_led_compositor test_note_cleanup
  test_projects_and_mode -v` —36 hedefli test PASS;hepsi exact-SYX koşusu diye
  sunulmaz ve paket test sayımına tekrar eklenmez.

Genel verifier164/core-only152 olarak kurulur;core-only12 uzun testi dışlar.
Suite kurulum sayımı emülasyon çalıştırması değildir. Önceki154 test aynı
firmware'dedir;bu tur hepsi yeniden çalıştırılmadı. Yeni4 exact-SYX test
PASS ile aynı image üzerinde158 ayrı paket testinin kanıtı vardır.36 hedefli
tekrar ve80 alt durum bu sayıya eklenmez.198 source/dependency pin'i,
18 güncel dosya ve61 evidence dosyası bağlandı;önceki bundle'ın81 immutable
kanıt dosyası doğrulandı. Probe başarılı olsa bile
M7 NO-GO için SystemExit2 verir;Windows runner exit1 gösterebilir.

Resmî [sample tracks kılavuzu](https://userguides.novationmusic.com/hc/en-gb/articles/25494393500562-Using-Circuit-Rhythm-sample-tracks)
microstep/live record bağlamı için incelendi. [2.0 ek belgesi](https://fael-downloads-prod.focusrite.com/customer/prod/downloads/circuit_rhythm_2.0_firmware_update_addendum_v1_english_en.pdf)
de incelendi;orada tie hareketi bulunmamasından5706'da erişilemez olduğu sonucu
çıkarılmadı. Bu belgeler emülasyon veya5706 byte kanıtının yerine geçmez.

Orijinal5706 SYX ve geçerli build değiştirilmedi. Önce/sonra kopyaları,diff,
başarılı/iptal keşif logları ve hash'ler yerel evidence klasöründedir.
Cihaz değiştirilmedi;RECOVERY.md'deki fiziksel kurtarma planı aynıdır.
