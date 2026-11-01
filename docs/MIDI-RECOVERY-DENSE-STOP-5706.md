# 64 stok ses /native Stop — 31 Ekim 2026

Güncel aday ve geçerli test sayımı STATUS.md'dedir. M7 NO-GO;bu belge
yerel byte analizi ve Unicorn kanıtıdır,fiziksel test veya yükleme izni değildir.

## Hata ve düzeltme

Önceki3f979b70… adayın Normal modunda,sekiz farklı notalı/gate96 pattern
ile her player'ın sekiz stok gate slotu doğal olarak doldu:toplam64 ses.
Host player/step/store/ownership/FIFO RAM'i yazmadı. Pattern'ler controller
callback'leri üzerinden UI'de kuruldu;zaman sonlu native IRQ66/Main zinciridir.

Stop,tek callback içinde64 Off veFC üretir. Native FIFO64 mesaj taşır;
çıktı fazından hemen önce sonF8 ve8 On da kuyruktaysa her DIN portunda27B
başlangıç vardır. Eski adayda Stop sonrası FIFO192B,deferred9,flags3;
drain sonrasında FIFO/deferred0 ama flags1 ve TX fault1 kalır.64 Off ileFC
teslim edilir;sonraki müzikal gönderimler reboot'a kadar reddedilir.
Bu sıradan yoğun Stop için yanlış bir kilitlenmedir. Pilotun bu durumu
beklenen karakterizasyon olarak geçen unittest'i,hatanın düzeldiği anlamına gelmez.

Yeni hook080552FE'deki `blx r2;movs r0,0` dört baytını BL ile değiştirir.
0807FE40'taki248B wrapper orijinal sanal flush'ı aynı R0–R3 ile çalıştırır.
Hedef4AED9 ise ve aşağıdakiler sağlanırsa native router poll297DE'yi bir
kez çağırır;ardından orijinal R0=0 sonucunu ve callee-save bankasını döndürür:

- IPSR,PRIMASK veBASEPRI sıfırdır.
- Global20006F04 router ve port-list pointer'ı hizalı,geçerli RAM aralığındadır.
- Recovery magic doğrudur;router3 port taşır ve üçü de kayıtlı owner ile eşleşir.

Her player en fazla8 Off üretir. Araya mevcut output worker girerek hazır
sürücüye aktarır;bu bounded servis bekleme/yeniden deneme döngüsü değildir.
Gerçek full/not-ready/nested-send fault'ları ve reboot politikası aynıdır.
Fault temizlenmez;On/Clock/SysEx replay edilmez;USB reset bariyeri değiştirilmez.
Stop sonFC'si bütün player flush'larından sonra üretilir.

## Bayt ve kaynak sınırı

- SYX `c9a87a9d4c4849e854114d57ea56320591d653eee274c10b68796c4895beaf96`
- Image `00fd098286cf1370f297616d3448a0c4a115d27f15b849d87638035d648aebd0`
- CRC MPEG2 `BEB0D013`;44 patch/7847 değişen bayt;458552B image/630565B SYX.
- Eski adaya göre yalnız4B hook +248B kod değişti;8B cave aralığı FF kalır.
- Son adres0807FF38;uygulama flash'ında200B kalır. Vector/identity512B aynı.
- Ek heap/kalıcı RAM0;wrapper16B stack. İç içe native poll/driver frame'leri
  ayrıca vardır;16B toplam çağrı zincirinin stack üst sınırı değildir.
- Core/glue/accepted-TX/CTRL_SYNC bytes/SHA'ları aynı. Stok player'ın
  4ADA4..4B1D0 ve55008..5552C aralıkları dört bayt dışında aynıdır.

## Test tasarımı ve gerçekleşen kanıt

Beş sentetik unittest:hazır router'ın bir kez işlenmesi/ABI;IRQ ve maskeli
bağlamın atlanması;başka sanal flush hedefinin korunması;bozuk pointer/magic/
port kaydının atlanması;gerçek overflow quarantine'in asla temizlenmemesi.
Bunlar tam reset/doğal64-ses kanıtının yerine sayılmaz.

Tam reset testi iki runtime modu × Stop'un Main çıkış fazı öncesi/sonrası
olmak üzere dört ayrı senaryo olarak paketlenir. UI her track'e8 ayrı pitch,
velocity96,gate96 ve32-adım uzunluğu yazar. Native commit'lerde aktif
slotlar track başına1..8 büyür.64 ses için43 microstep commit/player olur.
Stop bütün8 gerçek player'ı flush eder;native bounded router servisi8 kez
gözlenir. İki UART'ta Start,43 Clock,64 On/64 eşleşen Off ve en son tekFC
aranır. Ardından dirty proje korunarak iki mod geçişi ve yeni Play/8 On/
Stop/8 Off kontrol edilir. FIFO/fault/ownership RAM'i temizlenmez.

İlk Normal/çıkış öncesi koşu ve ardından dört ayrıntılı senaryo geçti:

| Mod /Stop fazı |Stop sonrası DIN FIFO |Fault |Yeni Play/Stop |
| --- | --- | --- | --- |
| Normal /çıkış öncesi |144B/port |000000 |PASS |
| Normal /çıkış sonrası |108B/port |000000 |PASS |
| Sequencer /çıkış öncesi |144B/port |000000 |PASS |
| Sequencer /çıkış sonrası |108B/port |000000 |PASS |

Her senaryoda flags/deferred0;kapanışta FIFO da0. Her biri1168 ilk çalma
IRQ'sı ve yeniden Play için1 IRQ kullanır;toplam1169 sonlu olay.
Mod roundtrip,8 On/8 Off/sonFC ve tüm8 native output servis çağrısı geçti.
İlk Normal koşu tekrar olduğu için sayımda ikinci kez yer almaz.

Yeni adayda149 paketlenmiş temel test +6 sınırlı Faz1 ölçütü ve ayrı timer
probe'u geçti. Timer probe'u2 unittest'tir;sentetik timer testi core'da da
olduğundan tek sayılır. Native IRQ regresyonu10690 compare,10708 Main,
iki modda1–32–1,544 LED ve mod/port başına40 On/40 Off/193 F8 içerir.
149 temel +2 timer +4 yoğun Stop koşusundan ortak sentetik timer bir kez
sayılır:154 ayrı paket testi +6 sınırlı Faz1 ölçütü PASS. Genel verifier
160/core-only149'dur;11 uzun testi core-only dışlar.160'ın tamamı bu tur
çalıştırılmadı;suite kurulum sayımı emülasyon koşusu diye sunulmaz.
Beş durmuş yardımcı görünüm ve direct-debt playback uzun testi yeni adaya
yeniden koşulmadı;önceki3f979b70… sonuçları yeni SHA'ya taşınmaz.

## Model ve açık sınırlar

Native reset,2331 gerçek tahsis,heap2004EA98 ve2184B workload payı;
sonlu TIM CNT/CC1IF +SR W0C/EGR,ADC1500/3700/2048 ve371D5=FFFFFF girdileri.
Unicorn ARM firmware'i çalıştırır;DSP firmware'i ve gerçek çevrebirim zamanı
çalışmaz. Native FPU IRQ frame adaptörü nested IRQ/NVIC arbitration kanıtı
değildir.25870'de Stop callback'i CPU context'i korur,RAM'i geri almaz ve
Main talimatı atlamaz. Diğer senaryo normal25864 sınırındadır.

UART TDR baytları fiziksel teslim/baud/tempo/jitter kanıtı değildir.
USB bu native proje düzeninde note portu olarak yönlendirilmedi;64 Off'un
USB kablosunda teslimi iddia edilmez. USB core/accepted-TX regresyonları ayrı
sentetik testlerdir. Gate tie,çeşitli çalışan microstep/probability,partial
Load/short-read,MIDI/USB RX–MSC–power ve genel en kötü stack/zaman açıktır.

## Tekrar üretim ve kurtarma

STATUS.md'deki komutlar `.venv\Scripts\python.exe` ile,`-O` olmadan çalışır.
Probe/verifier başarılı testte de M7 NO-GO için SystemExit2 verir;Windows
runner exit1 gösterebilir. Başarı JSON/test sonuçlarıyla doğrulanır.

`logs/recovery-native-64voice-20261031` altında eski aday/pilot,önce/sonra
kopyaları,değişiklik diff'i,manifest,kod denetimi,loglar ve hash'ler tutulur.
Kaynak önceki baytlarının dördü inverse diff ile çıkarılıp189-pin baseline
SHA'larıyla birebir doğrulanmıştır;sonuç source-reconstruction.json'dadır.
194 güncel kaynak/dependency pin'i:184 eski aynı,5 değişti,5 yeni. Önceki
timer bundle'ının89 immutable kanıt dosyası da doğrulandı. Diff,before/after,
summary.json ve hashes.json aynı klasördedir.
Orijinal5706 SYX pin'i değişmez. Yerel adaydan geri dönüş before/build
kopyasıdır. Cihaz hiç değiştirilmedi;fiziksel kurtarma prosedürü
RECOVERY.md'de kalır. M7 tamamlanmadan cihaz denemesi önerilmez.
