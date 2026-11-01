> Güncel29 Ekim (factory + debt):Hazırlanmış MAIN/kısmi owned SysEx /
> query ledger borcuyla MIDI-only↔MIDI+MSC geçişi13 yeni yerel ve13 paket
> senaryosunda PASS. Native settings/boot caller,READ iptali,eksik ACK ve
> rebuild içi reset/yeni istek testli. Firmware/93 önceki kaynak/codegen aynı.
> Önceki tam474 PASS korunur;487 toplam discovery,tam487 bu oturumda koşulmadı.
> Tam Packs UI/diğer caller/boot/RAM-init/gerçek timing/integration açık.
> Üretim Off-Stop FAIL,M7 NO-GO. STATUS ve MIDI-USB-FACTORY-DEBT-5706.md güncel.

---

# USB MAIN staging carry — 5706

Bu prototip yalnız Unicorn ARM emülasyonundadır. Üretim builder'ı bunu kullanmaz;
M7 NO-GO. Fiziksel MIDI/USB cihazı veya API'si kullanılmadı.

## Sorun ve düzeltme

Stok402FC SysEx formatter'ı immutable borrowed kaynaktan okuyup port cursor'unu
ilerletir;2B460 MAIN tamponuna4B USB-MIDI event'leri koyar.2B498→2B3BC→26880
bu tamponu gönderir.2B4AE length'i koşulsuz temizler. IRQ close,ss_tx_arm'ın
admission'ını reddettiğinde raw adapter bunu gizler ve64B hazırlık kaybolur.

`midi_usb_carry_prototype.arm_code(staging=True)` aynı carry katmanını genişletir.
Yeni stock2B4984B detour registered CPU MAIN için native26880 gate'ini doğrudan
çağırır. TX_TICKET değişmediyse MAIN korunur;değiştiyse kabul edilmiş aktarım
sahiptir ve MAIN length tüketilir. Reset/uyku bu kenarın iki yanında testlidir.
Kabul edilmiş aktarımın fiziksel teslimatı hakkında yeni bir varsayım yapılmaz.

Retained full MAIN,native402FC'nin başındaki full testinde çıkışa neden olur.
Bu yüzden OPEN registered USB rp_poll önce mevcut MAIN'i flush eder,sonra stok
worker'a devam eder. Planned close sırasında flush yapılmaz;FLUSH_BUSY32,
nested poll/stability'yi reddeder. IRQ veya maskeli bağlam yeni flush'ı çalıştırmaz.

## Korunan sözleşme

- TX_ACTIVE0;producer/lifecycle/ledger/port/flush owner boş;mevcut fault yok.
- MAIN selected,length0..64 ve4'ün katı;native capacities64;ALT length/pointer0;
  raw length0/mode0. Native binding,pointer ve eski byte koşulları sürer.
- Partial SysEx cursor,total'dan büyük olamaz.0<cursor<total ise USB portu
  immutable retry slot'u kabul etmiş olmalı;pointer/descriptor/length eşleşir.
- RX FIFO/parser/ledger provenance,MAIN baytları ve software cursors korunur;
  cursor geriye alınmaz veya payload yeniden üretilmez.
- Full disable/ACK/AHB/shared RX drain/TX flush ve generation commit şartları
  aynıdır. Eski default carry1300B/f703550d... codegen aynı kalır.

## Kanıt

12 yeni test:iki modda gerçek native formatter içi suspend;guard olmadan kayıp;
actual submit öncesi reset;software debt kalmamış staged Note Off;submit kabulü
sonrası strict negatif;missing ACK;tekrar sleep;tamamlanmış ilk paketi replay
etmeden cursor devamı;foreign borrowed pointer ve invalid MAIN/raw negatifleri;
ledger/query/committed Clock-Stop;default code hash. Pozitif staging RAM'e
elle yazılmaz;native main formatter çalıştırır. IRQ giriş yeri kontrollü enjeksiyondur.

474 unit PASS;paketlenmiş üretim adayının üstüne emulator overlay ile12 yeni+
15 önceki carry senaryosu27 PASS. Native formatter/driver/HAL/IRQ ve main kodu
yürür;ACK/flush/clock/RTOS/flash/UART drain sınırları sentetiktir. USB completion
byte stream ve DIN FIFO byte stream karşılaştırılır;gerçek host ACK/PHY/UART
IRQ veya gerçek zaman kanıtı değildir.

Varyant1680B,0807CC00..0807D290;128B carry state20048520..200485A0 içinde
ek FLUSH_BUSY32;toplam2712B synthetic RAM.7 gate;3 masked commit/max30 komut,
masked call/loop yok. Yerel SP delta0 ve BL8;staging/flush frame24B. Gerçek
native full call stack/cycle/latency veya üretim RAM/init kanıtı değildir.

Loglar:logs/usb-staging-20261029. session.diff,hashes.json ve application-range
manifest SHA/MPEG-2 CRC/vector512B kanıtını içerir;flashable binary/SYX üretilmez.

## Sıradaki sınır

Retained staging borcuyla MIDI-only↔MIDI+MSC native factory/descriptor geçişi
henüz testli değildir. Already-submitted belirsizliği,raw ALT mode,partial
parser/held input/fault toparlanması;diğer caller'lar,full RTOS/boot/RAM-init,
gerçek timing,storage short-read/live-pattern alias,DIN input ve entegrasyon
açıktır. Üretim Note Off/Stop kaybı sürer;cihaz denemesi hazırlanmaz.
