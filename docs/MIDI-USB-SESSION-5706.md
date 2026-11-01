> Güncel devam:ayrı820B/96B IRQ bridge,bu session modülünün kaynak/default
> codegen'ini değiştirmeden native CPU FIFO completion zincirini emülasyonda
> bağlar. Test artık completion token'ı sağlamaz;IRQ girişindeki halen sahipli
> job snapshot'ı native callback'i doğrular. Kontrol/reset/disconnect dönüşü
> ve gerçek bariyer açık kalır. Eski hardware XFRC bariyer ihlali sonrası
> yeni job gibi görünebilir;negatif testlidir.325 toplam PASS,M7 NO-GO.
> MIDI-USB-IRQ-5706.md ve STATUS.md güncel;alttaki kayıt önceki deneydir.

---

# USB session iptal sözleşmesi — 28 Ekim 2026 / emülasyon deneyi

Yazılım kuyrukları boşken USB endpoint'te yaşayan eski TX yanıtı için ayrı
bir iptal bariyeri geliştirildi. Tagged eski RX/TX callback'leri yeni oturumu
tamamlayamaz. **PASS, sentetik USB register sözleşmesine ve immutable job
bridge'e bağlıdır.** Stok callback'leri kimlik taşımaz;tam IRQ/DMA/RTOS/cache
entegrasyonu yoktur. Genel aktif transaction iptali çözülmedi. M7 NO-GO;
cihaza/MIDI/USB API'sine erişilmedi. Üretim firmware'i aynı kaldı.

## Stok bayt/disassembly kanıtı

- `26880`,endpoint availability'yi atomik azaltıp native `2C9B8` ile TX başlatır.
  `268D0`,timer'ı durdurup availability'yi native doygun sayaçla serbest bırakır.
  Retry slotunun boşalması bu donanım transferinin bitmesi değildir.
- `26988`:r0=port,r1=alınan byte sayısı. `2691E` staging'i native RX FIFO'ya
  yayımlar;sonra `269AC` yeniden alımı kurar. Callback'te epoch/ticket yoktur.
- Pin'li `52EDC`,endpoint interrupt maskelerini ve CTL'yi `EFF37800` ile
  temizler. Bu stok gövde SNAK/EPDIS isteği,disable ACK bekleme veya FIFO flush
  yapmaz. Bunları yalnız normal endpoint-close çağrısına atfetmek yanlıştır.
- `52E04`,seçili TX FIFO'yu bounded wait ile flush eder. `52E22`,paylaşılan RX
  FIFO'yu flush eder. `53250`,bütün endpoint'leri durdurur ve global flush yapar;
  MIDI'ye özel iptal için kullanılamaz. Diğer USB arayüzleri de etkilenir.
- USB formatter'ın iki descriptor'ı ve aktif staging pointer'ı vardır.
  `401AC` TX sayaç/ring clear'ı tek başına bu staging'i veya donanım reader'ını
  tamamlamaz;borrowed payload pointer alanlarını da açıkça sıfırlamaz.

`trace_midi_usb_session.py`,stok SHA pin'ini doğrulayan `load_image` kullanır;
native pencerelerin SHA256 ve disassembly'sini loglar. Bu tam dolaylı IRQ
grafiği veya MCU kimliği kanıtı değildir.

Register isimleri/bit karşılaştırması için birincil kaynaklar:
[ST USB LL kaynak kodu](https://github.com/STMicroelectronics/stm32f7xx-hal-driver/blob/master/Src/stm32f7xx_ll_usb.c),
[ST CMSIS STM32F745 başlığı](https://raw.githubusercontent.com/STMicroelectronics/cmsis-device-f7/master/Include/stm32f745xx.h).
Bu karşılaştırma,cihazın kesin işlemcisini veya stok build'in güncel HAL ile
aynı sürüm olduğunu göstermez. Çalışan fiziksel iptal sonucu sayılmaz.

## Deneyin sözleşmesi

`src/midi_usb_session_prototype.py`:3176B Thumb,`08078000` tabanı;128B sentetik
state `20047E00`. Önceki varsayılan module/codegen'leri aynı kalır. Toplam1624B
RAM üretimde checked reservation/init almış değildir.

`OPEN → CLOSING → WAIT_DISABLE → WAIT_FLUSH → SEALED → OPEN`:

1. Main context,PRIMASK0,doğru binding/epoch ve boş yazılım sahipliği doğrulanır.
   RX publish ve USB TX kabulü kapanır. Başka producer araya girerse sahiplik
   tekrar kontrol edilir;dolu kalırsa kapalı beklenir.
2. Yalnız endpoint1 IN/OUT maskeleri kapatılır;IN81 ve OUT01 için gerekiyorsa
   SNAK/EPDIS istenir. EPENA=0 ve başta aktif olan yönlerin disable ACK'i
   gelmeden ilerlenmez. Diğer endpoint maskeleri korunur.
3. Ortak RX FIFO boş ve AHB idle olmalıdır. Global RX flush kullanılmaz.
   Yalnız MIDI IN TX FIFO1 flush edilir;tamamlanması beklenir. Eski hardware
   okuyucusunun bu bariyerde bittiği **model varsayımıdır**.
4. Ancak bundan sonra native TX RAM clear,driver descriptor/staging reset,
   HAL transfer pointer/count cleanup ve endpoint availability kurulumu yapılır.
   Native quiescent RX reset epoch'u artırır;state SEALED olur.
5. Resume,binding/configured ve endpoint/FIFO/interrupt durumunu yeniden
   doğrular;ilgili maskeleri geri koyar ve yeni RX transferini kurar.

Her `ss_step` çağrısı sınırlı tek faz ilerletir. ACK/flush gelmezse CPU'da
sonsuz loop yoktur;oturum kapalıda bekler. Genel bir timeout/recovery policy
ve tam USB reset graph'ı bu deneyin parçası değildir.

Sorgu borcu,partial mesaj,held nota,sticky fault/Off sahipliği veya aktif ortak
SysEx payload reader'ı varsa begin reddedilir. Borçlar/payload silinmez;
dirty project veya proje I/O'suna bu deney dokunmaz. Aktif işlemler için genel
cancel/drain hâlâ açık. USB kapalıyken kayıt dışı DIN native yolu devam eder.

## Completion sahipliği

Her job `(epoch,ticket)` değerini submit sırasında değişmez olarak alır.
Ticket ayırması ve completion claim'i kısa maskeli bölümde atomiktir.
Completion sırasında state2,callback'in payload publish/native rearm'ını
korur;yalnız doğru native dönüş token'ı RX'i yeniden kurabilir. Eski,yanlış,
duplicate veya nested completion state'i ikinci kez serbest bırakmaz.
RX byte count,gerçek alt submit'te tutulan owned transfer limitini aşamaz.
Ticket/epoch wrap yeni kimlik olarak kullanılamaz.

Stok `268D0`/`26988` girişleri kayıtlı nesne için untagged olduğundan reddedilir;
deneyin `ss_tx_done(epoch,ticket)` ve `ss_rx_done(epoch,ticket,length)` API'leri
ayrı job bridge gerektirir. **Bu bridge stok IRQ zincirine henüz kurulmadı.**
Callback geldiğinde güncel endpoint'ten epoch/ticket okumak eski olayı yeni
işlem gibi etiketler;bu bir çözüm değildir. Kaydedilmiş değişmez job sahipliği
ve gerçek iptal bariyeri birlikte gerekir.

Özellikle korunan negatif:gerçek iptal sözleşmesi ihlal edilip eski DMA'nın
yeniden kullanılan RX buffer'a yazmasına izin verilirse veri bozulur. Eski
callback kimliğinin reddi bu yazıyı önleyemez veya geri alamaz. Dolayısıyla
`hardware_late_dma_after_barrier=NOT_ESTABLISHED` kalır.

## Kontroller ve sınırlar

11 ek gate,stok/generated prologue assert'i ve overlap/app bounds denetimiyle
yalnız Unicorn'da kurulur. İki önceki lifecycle overlay'i açıkça değiştirilir.
Native TX completion CBZ'si flags korunarak taşınır;timer var/yok ve foreign
native counter yolu testlidir. Tam flash snapshot ve bütün RAM canary'leri
çağrılardan sonra doğrulanır;testin sabit nested trampoline alanı ayrıca kaydedilir.

Yerel CFG/ABI:SP delta0,BL8 hizalama,max32B yerel frame PASS. Zorunlu maskeli
yollar max26 komut;call/loop yok. Bunlar tam native stack,IRQ latency veya
gerçek cycle ölçümü değildir. Model,ACK/flush'un DMA reader'ını bitirdiğini
tanım gereği uygular;gerçek USB IRQ/DMA/cache davranışını ispatlamaz.

25 yeni/306 toplam test PASS. Packaged candidate üzerine aynı emulator overlay
testleri25 PASS. Build/baseline/production audit/87 aday regresyon ve6 sınırlı
kriter PASS. Üretim adayı Off/Stop kaybını sürdürür;probe/verifier exit2/NO-GO.
Loglar `logs/usb-session-20261028`,özellikle `probe/report.json`.

Kod SHA256:`fe091ec2e783a8eab3210405df7dcca0302dfea2e7056d20e69c06522cfcbf9d`.
Üretim SYX SHA256:
`3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d`.
Stok SHA256:
`11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf`.

Sonraki iş:tam stok IRQ/completion/reset/disconnect zincirini native yürütüp
immutable job bridge ve gerçek disable/ACK/FIFO bariyeri için kanıt kurmak.
Ardından aktif borç/reader cancel-drain,checked RAM/init,full boot/OOM,timing,
storage,DIN input ve üretim entegrasyonu gerekir. Fiziksel test önerilmez.
