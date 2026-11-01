# 5706 MIDI alıcısı sahipliği ve mod geçişi

Güncelleme: parser/FIFO ve gerçek Start/Continue/Stop store yazıları ile normal
Clock dalı da çalıştırıldı;120 toplam/54 packaged test PASS. Yeni kapsam ve kalan
stub sınırları [MIDI-INGRESS-TRANSPORT-5706.md](MIDI-INGRESS-TRANSPORT-5706.md)
içindedir. Aşağıdaki113/47 sonuçları önceki alt çalışmanın kaydıdır. NO-GO sürer.

26 Ekim 2026; yalnız hash'i sabit stok5706 ve yerel Unicorn. Cihaz/port erişimi yok.
Karar NO-GO. Bu çalışma storage, tam boot veya tam UART/USB testini kapatmaz.

## Yeniden üretilen eksik kontrol

Önceki c_mode_can_switch yalnız controller ve grid alanlarını okuyordu.
Gerçek5AF94 short-message decoder ->3F5A8 receiver -> adaptor/router/ownership
filters -> recorder graph'ı, sentetik controller ile ayrı, çakışmayan RAM'de
birleştirildi. Receiver+74..+113 doluyken32 alt-vakada mode değişebiliyordu.
logs/midi-mode-before.txt. Bu sentetik nesne grafiği karşı örneğidir; fiziksel
cihazda olay veya bütün boot pointer bağlarının doğrulandığı iddiası değildir.

## Bayt/disassembly kanıtı

- Root receiver vtable665E4 slot0 ->3F5A8, slot1 ->3F660.
-3F5A8..3F65A,8 track için20'şer bayt receiver+74 maskesi set eder;
  3F660..3F6E0 eşleşen Note Off sonrasında bit temizler.
-3F454 ctor maskeleri3F55E..3F568'de160 bayt sıfırlar.
-3F7D8..3F836 stok drain, her track'in5 word'ündeki notaları gerçek
  receiver vtable Note Off slotuyla bırakır.
-5AF94..5B018, F8/FA/FB/FC mesajlarını receiver+10/+0C subobject'lerine verir.
  Derived ctor'un son vtable'ları receiver+0C=66654 ve+10=66670'tir.
- Raw image'da3F454'e tam BL encoding taraması294CC adayını buldu;
  disassembly bunu boot kurucu çağrısı olarak doğruladı. Bu, bütün dolaylı
  çağrıların yokluğu veya receiver lifetime/maximum sayısı için tam kanıt değildir.
- Yeni hook3F5A8 orijinal f8b51d00'ı doğrular; B.W cave observer'a gider.
  c_midi_receive_on_stock aynı push veMOVS'i tekrarlar,3F5AC'ye döner.
  MOVS velocity0 dalının bayraklarını bookkeeping sonrasında yeniden kurar.

## Düzeltme ve sınırları

State+68..+77, en fazla4 farklı receiver pointer'ını saklar. +78 sticky context
fault; +79 nested active-call counter. Mevcut256 bayt rezervasyonu değişmedi.
c_midi_receive_on argümanları korur, receiver'ı kaydeder ve busy counter'ı
artırır; stok fonksiyonu tam bir kez çağırır, sonra counter'ı azaltır.
Stok r0-r3 dönüş değerleri aynı stack slotlarında saklanıp aynen geri getirilir;
r4-r11 ve SP harness ile denetlenir. Bu, standart AAPCS'nin zorunlu kıldığı
callee-saved korunuma ek, dolaylı çağıranlara karşı korumacı eşleştirmedir.

Observer bookkeeping kısa PRIMASK bölgelerindedir. Stok callback girişindeki IRQ
maskesi çağıranın özgün maskesidir; observer sırf kayıt tutmak için callback'i
maskeli çalıştırmaz. UI'nin check+commit'i zaten IRQ altında olup busy counter
başlamış Note On ile maskenin henüz yazılmadığı aralığı kapatır. Nesting ve
counter255 saturation testlidir. Saturation sticky fault set eder.

c_midi_inputs_idle dört receiver'ın40 word'ünü okur. Nonzero mask veya active
call/fault varsa mode değişmez. Pointer alignment ve okuma aralığı kontrol edilir:
20000000 <=ptr <=2004F660-114; okuma state sınırına taşmaz. Beşinci farklı
receiver teslimatı engellenmez; fault ile mod geçişi kapatılır ve yeniden
başlatmaya kadar otomatik açılmaz. Cache slotları yeniden kullanılmaz.
Receiver sayısı/lifetime tam boot grafiğinde kanıtlanmalıdır; bu bilinmeyen
yayın engelinde açıkça tutulur.

## Testler ve dürüst kapsam

12 yeni test:
-2 mode *8 track *2 uç nota/Off biçimi; Note On sonrası ret, eşleşen Off sonrası geçiş.
- Gerçek stok multi-note drain; son nota bırakılmadan guard açılmaz.
- İki decoder/receiver kaynağı; ikisi de bırakılmadan guard açılmaz.
- Gerçek5 receiver ile overflow; nota teslimatı sürer, guard kapalı kalır.
- Direct velocity0; stok bayrak dalı ve dönüşü korunur.
- Stok prologue geri yüklenmiş kontrol fixture'ına karşı r0-r3 bit-bit eşitliği.
-40 mask word'ü; state sınırındaki magic'e taşmama.
- Stok callback bir kez, busy1, çağıranın özgün PRIMASK değeri.
- Invalid pointer/context, nested call/saturation ve invalid heap.
- F8/FA/FB/FC gerçek decoder + receiver thunk üzerinden teslim edilir.
  SON transport callback'leri stub'dır; tam Stop/Clock task/ISR testi değildir.

Stop tek başına bu sınır modelindeki fiziksel basılı nota sahipliğini silmez;
guard Note Off veya gerçek mask drain'e kadar kapalı kalır. UART/USB byte
girişleri, output queue, transport task'ları, scheduler ve gerçek saat zamanlaması
henüz modellenmedi. Mevcut maskelerin stale/freed receiver belleğinden okunmaması
için boot lifetime kanıtı da açık.

İlk realtime fixture temel-sınıf vtable'ını kullandığı için unmapped read verdi.
Derived ctor'un son66654/66670 tabloları kullanılarak düzeltildi; firmware hatası
olarak sayılmadı. Observer cleanup ilk sürümde r1-r3'ü değiştiriyordu (AAPCS
izin verir); daha sıkı stok çıkış eşitliği testi4 fark üretti. Wrapper24 bayt
frame ve ortak input/output stack slotlarıyla hepsini koruyacak şekilde düzeltildi.
logs/midi-observer-abi-before.txt bu ara bulguyu saklar.

Sonuç:113 regresyon PASS;47 packaged güvenlik regresyonu ve6 sınırlı kriter PASS.
Baseline ve bağımsız binary/SysEx/CRC/Capstone/yerel stack audit PASS.
Loglar logs/midi-owner-{build,guards,all-tests,verify,baseline,audit}.txt;
logs/midi-owner-audit/; disassembly logs/midi-*.txt.
Paket raporu logs/phase1-verification-20261026T182645Z/report.json.
