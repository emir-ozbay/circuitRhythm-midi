# Çalarken microstep/probability — 31 Ekim 2026

Güncel koşu sonucu ve sayım STATUS.md'dedir. Üretim firmware'i
c9a87a9d… /CRC BEB0D013 olarak kalır. M7 NO-GO;cihaz/port erişimi yoktur.

**Kanonik native koşu PASS:**tek reset,iki mod,726 native IRQ ve951 tam Main
turu.256 canlı edit kontrolü,64 üst adım tutulmayan giriş ve32 çalarken /
adım tutulurken mod kısayolu reddi geçti. Bir uzun exact-SYX unittest'tir;
256 ayrı test veya32 native reset diye sayılmaz.

| Mod | Player On =DIN On/Off /port | Probability adım denemesi |Stop'ta canlı nota |
| --- | --- | --- | --- |
| Normal |66 =66/66 |24:1 kabul/23 ret |9 |
| Sequencer |76 =76/76 |24:6 kabul/18 ret |13 |

Mod/port başına14 F8,Start ve son tekFC;336 commit/mod vardır. Her iki geç
bit5 ve yeniden oluşturulan bit4 sekiz player'da tetiklendi. İkinci adımın
micro0/2 probability cohort'ları aynı native eşik/kararı kullandı.
Bu sonlu örnekler probability dağılımı/kalitesi kanıtı değildir.
Context/active/TX000000;proje I/O0,ek tahsis/NOR artışı0. Heap2004EA98 /
2331 tahsis /476 başlangıç NOR mutation korunur.

## Testin konusu

Önceki yardımcı görünüm testleri transport durmuşken çalışıyordu. Yeni test
tek native reset ömründe,iki runtime modunda8 track'in iki sayfasına çalma
devam ederken controller girdileri gönderir. Pattern Start15/End16/sync0,
iki etkin adım ve gate96 UI'de kurulur. Sıfır tabanlı15/16,iki auxiliary
sayfasının16/17 sınırıdır. Bu iki adımlık çalışma,önceki32-adım tam tur
testinin yerini almaz;parametre değişimini kısa bir döngüde izler.

İlk adım note72;ikinci adımın farklı pitch'i native Note keymap'inden
seçilir. Her ikisinde velocity96,gate96,microstep1,probability7 vardır.
Proje/store/slot/owner/FIFO/fault/timer borcu host'ta yazılmaz. Pattern'i
kurma ve iki mod arasındaki geri hazırlama da native UI girdileridir.

## Canlı senaryolar

- İlk adımın0..2 mikro-adımları çalındıktan sonra mask1→33 yapılır. Sonraki
  native batch'te mikro-adım5 tetiklenmelidir. İkinci sayfada mask1→5,
  gelecekteki mikro-adım2'yi ekler.
- Transport çalışırken üst adım tutulmadan gönderilen alt-pad girişleri
  projeyi değiştirmemelidir. Üst adım tutulurken C0/bit3 tam doğru15/16
  bitini taşır. Seçili ayrılmış alt pad'ler (microstep local14/probability
  local8) değişiklik yapmaz;canlı test bütün ayrılmış hücreleri taramaz.
- İlk sayfada probability3→7;ikinci sayfada0,adım tutulurken yazılır.
  Etkin adımda yalnız byte4 değişir. Aktif player notaları parametre
  düzenlemesi sırasında erken kesilmemelidir.
- Probability0,stock karşılaştırmada en düşük olasılık değeridir;mutlak
  sessiz anlamına gelmez. Native player+4 alt üç biti ve4AF1A karşılaştırma
  girdileri yalnız okunur. Sonlu döngülerde tüm track'lerde ret ve en az bir
  doğal kabul gözlenmesi aranır. PRNG sonucu zorlanmaz,dağılım/istatistik
  doğruluğu iddia edilmez.
- İlk adımın bütün microstep bitleri silinip native boş tuple oluşumu
  denetlenir. Bit4 ile yeniden oluşturulur;Gate96 ve note72 UI'de geri
  verilir. Önceden başlamış nota edit sırasında korunur,sonraki native
  batch'te yalnız yeni bit4 tetiklenir.
- Çalma ve fiziksel adım sahipliği sürerken mod kısayolu reddedilir.
  Bu test sahipliğin tek başına ret nedeni olduğunu iddia etmez:transport
  da çalışmaktadır. Guard'ın diğer koşulları ayrı testlerdedir.
- Son Stop bütün player listelerini ve üç yazılım portunun kapanış borcunu
  boşaltmalıdır. İki native UART akışı aynı olmalı,her On karşılık gelen
  Off ile kapanmalı ve son mesaj tekFC olmalıdır.

## Karar ile Note On eşleştirmesi

Native AEEE hazırlık çağrısında ilgili8B kayıt ve player'ın mevcut eşiği
okunur. Gerçek4AF1A'daki R1/R2 değerleri bununla çapraz kontrol edilir.
AFBC commit'leri,gerçek4B0D4 On çağrılarıyla tek tek eşleştirilir;seçilmemiş
mask biti veya reddedilen probability için fazladan On kabul edilmez.
UI preview notaları player'ın4B0D4 zinciriyle karıştırılmaz;toplam UART
akışında ise preview dahil açık nota kalmaması denetlenir.
Native MIDI Off31FC6 çağrısındaki etkin output/channel map ve pitch de
okunur. Canlı microstep/probability/silme-yeniden oluşturma girdileri sırasında
ilgili player'ın hâlâ tuttuğu pitch'e Off gönderilmesi reddedilir. Bu guard
yalnız player listesi korunumu ile yetinmez;gerçek MIDI çıkış çağrısını izler.
Bu koşudaki canlı UI edit aşamalarında MIDI Off31FC6 çağrısı0 idi;guard'ın
hata enjeksiyonuyla tetiklendiği iddia edilmez. IRQ çalmasında ve Stop'ta
Off çağrıları vardır ve UART kapanış eşleştirmesi bunları denetler.

En hızlı sync0'da üç hazırlık önce,üç commit sonra gelebilir. İlk pilot
izleyici yalnız son hazırlığı sakladığı için ilk commit'te durdu. Bu
firmware hatası değildi. İzleyici player/pattern/step/microstep anahtarıyla
bütün bekleyen hazırlıkları tutup commit'te tüketir. İlk negatif log,RAM ve
helper saklandı;RAM onarılarak sürdürülmedi,yeni native reset başlatıldı.

İlk pilotta ana view0'a tekrar Sample8 gönderilmesi stock secondary mode9'u
açıyordu. Yeni giriş view0 zaten seçiliyse aynı tuşa tekrar basmaz;source
scope'undaki ana başlangıç açıkça denetlenir. Bu da test planı düzeltmesidir.

İkinci keşifte yeniden oluşturulan adım zaten note72 iken72 tuşuna tekrar
basılmıştı. Note görünümünde aynı pitch'e basmak stock toggle'dır;gate6 /
mask1 varsayılan tuple'ı oluştu. Önceki Note suite'inde de bu davranış vardır.
Test,idempotent setter varsayımını bırakarak zaten doğru pitch varsa bu
gereksiz tuş vuruşunu yapmaz. Firmware değişmedi;negatif ve bir iptal edilen
tekrar ayrı tutulur. Kanonik koşu yeni reset'ten başlar.

## Kanıt düzeyi ve açık sınırlar

Native reset/RTOS nesneleri,controller callback'leri,sonlu TIM CNT/CC1IF ve
SR girdileri,IRQ66/FPU frame adaptörü,tam Main,Uart TXE IRQ'ları kullanılır.
ADC1500/3700/2048 ve DSP kayıt-idle cevapları model girdisidir. GPIO tarama /
tam input kuyruğu,NVIC arbitration/nested IRQ,gerçek DSP,baud/tempo/jitter
ve fiziksel teslim bu deneyin kanıtı değildir. Native projede USB note
yönlendirmesi kapalıdır;iki UART sonucu USB kablosu teslimi diye sunulmaz.

Controller editleri arasına otomatik duvar zamanı eklenmez. Timer yalnız
sonlu explicit IRQ olaylarında ilerler;UI girdileri sırasında tam Main
çıkış işlemesi çalışır. Bu kontrollü olay sırası,gerçek insan hareketi süresi
veya en kötü latency testi değildir. Açık süre/stack/RAM bütçesi korunur.

Tie bitinin native UI/stock Load erişilebilirliği,partial Load/short-read,
birleşik MIDI/USB RX–MSC–power ve tam M7 regresyon/bundle ayrı işlerdir.
Bağımsız polifoni veya yeni müzikal özellik eklenmedi.

## Tekrar üretim

`.venv\Scripts\python.exe` ile,`-O` olmadan:

- `scripts/probe_recovery_running_edits.py logs/recovery-running-edits-20261031/probe-pass`
- `scripts/audit_recovery_candidate.py logs/recovery-running-edits-20261031/audit`

Probe exact-SYX ile kaynak codegen eşitliğini denetler. Başarılı testte de
M7 NO-GO için SystemExit2 üretir;Windows runner exit1 gösterebilir. Generic
verifier165/core-only152;core-only13 uzun testi dışlar. Suite kurulum
sayımı emülasyon koşusu değildir. Önceki158 test aynı image üzerindedir;
bu tur bütün suite'in yeniden çalıştırıldığı iddia edilmez.
Yeni1 PASS ile aynı image üzerinde159 ayrı paket testinin kanıtı vardır.
201 source/dependency pin'i:197 eski aynı,verifier değişti,3 yeni.
17 güncel dosya/70 evidence dosyası,before/after,diff,cohort analizi ve
hash'ler bağlandı;önceki bundle'ın61 immutable kanıt dosyası doğrulandı.

Üç yeni kaynak:recovery_running_edit_test_support.py,
test_recovery_running_edits.py,probe_recovery_running_edits.py.
Verifier genişletilir;üretim ve üç build çıktısı aynı kalır. Yerel loglar,
before/after,diff ve hash'ler recovery-running-edits-20261031 klasöründedir.
Stock5706 hash pin'i ve RECOVERY.md'deki fiziksel kurtarma planı değişmez.
