> Güncel28 Ekim:434 toplam/87 aday PASS. Normal USB suspend/wakeup artık
> emülasyonda ortak reader/ACK/flush bariyerini bekler. Erken wake/reset geç
> clock-stop yapmaz;reset eski configuration'ı otomatik açmaz. Saat durmuşken
> yalnız wake/reset açık,normal USB MMIO/servis çalışmaz. Native save/restore /
> ungate gerçek;clock/IRQ/timing ve RTOS/flash sınırları sentetik. LPM/deep
> stop/DMA desteklenmez.2520B checked RAM/init,task/boot/tam Packs/gerçek
> bariyer açık. Üretim aynı/Off-Stop FAIL,M7 NO-GO. STATUS.md ve
> MIDI-USB-POWER-5706.md güncel.

---

# Native USB factory geçişi — 28 Ekim 2026

Emülasyon prototipi432A8 factory çağrısını mevcut MIDI/MSC iptal bariyerine
bağlar. MIDI-only ve MIDI+MSC listeleri arasında eski reader/parent ömrü
korunur. Üretime eklenmedi;M7 NO-GO. Cihaz/MIDI/USB API erişimi yapılmadı.

## Stok sıra ve ABI

Native40A30,ROOT+8..+14 pointer'larını40A40'ta ve sayıyı40A44'te sıfırlar;
deinit40A48→40B44→40B7E daha sonradır. Aktif READ varken doğrudan native
factory negatifinde liste değişir,eski TX reader aktif kalır ve MSC parent
deinit edilmez. Yeni gate eski liste teardown bitmeden bu kodu çalıştırmaz.

Direct432A8 çağrıları2CB2E ve35838;35838 sabitleri1/101'dir.2CB18 yalnız
stack'in alt iki byte'ını yazar,word argüman yükler;üst16 bit belirsizdir.
Prototip UXTH ile stok low16 ABI'yi korur. Arg1 MIDI-only;101/201/301
MIDI+MSC ve storage mode1/3/2'dir. MSC-only/disabled listeler reddedilir.
Direct scan tam indirect/caller veya Packs UI akışı kanıtı değildir.

## Yeni sıra

1.432A8 isteği binding ve argüman kontrolünden geçer;generation/desired /
  pending atomik saklanır. Liste değişmez;mc_deinit_list ortak kapanışı ister.
2. Ana service önce eski MIDI/MSC READ/USB okuyucularını ve admitted borcu
  bitirir. Native eski parent teardown yürür;MC ve SS SEALED beklenir.
3. Native432A8 prologue'u pinned ROOT200000D0 ile relocate edilir. Gerçek
 40A30 stop/init,40AFE class add,40B1C descriptor/start yürür.
4. Yalnız native40B51 boş-liste iç deinit çağrısı RUNNING/main/root/controller
  bağında native'e geçirilir. Mevcut pin'li MIDI add-deinit guard'ı aktiftir;
  harici reset yeni control request olarak korunur.
5. Generation aynıysa pending temizlenir. Factory içi yeni mod isteği ikinci
  geçişte yürür;harici reset/control.FLAGS boşalmadan service tamamlanmaz.

Gerçek literal nesneler ROOT200000D0,MIDI200000F0,MSC200000FC,HAL200054B4.
Fixture bunları native adreslere bağlar;controller/task/heap diğer RAM
bağlamları sentetiktir. Yanlış HAL binding request'i değiştirmeden reddeder.

## Kanıt ve sınırlar

- D:stock prologue/literal/direct-caller byte assert'leri ve disassembly;
  factory4B+deinit4B+generated service6B gate,relocated prologue/app bounds.
- E:16 Unicorn testi;MIDI-only94B/2-interface ve composite125B/3-interface
  descriptor,MIDI inquiry,composite'e dönüşte storage READ,aktif READ/MIDI
  debt,latest request/reset,DIN Off ve project RAM korunması. Yeniden kurulum
  ardından USBRST/ENUMDONE/address/config sequence gerçek kontrol yolundadır.
- E sınırı:HAL427FC return0;native stop/start/init prefix ve FIFO setup
  yürür.3ms stop/start ve200ms factory beklemeleri sentetik24068 tick(+4) ile
  ilerler. NVIC/clock register memory gerçek IRQ/PLL/PHY/timing modeli değildir.
  Önceki RTOS wake/yield ve RAM alt flash sınırları sürer.
- H:418 toplam test,87 aday regresyon/6 sınırlı kriter,baseline/build /
  production byte/CRC/vector/manifest denetimi PASS. Paket probe16 PASS;
  exit2/NO-GO. Fiziksel test yok. Üretim Off/Stop kaybı değişmedi.

## Kod

| Katman | Kod / SHA256 | Ek sentetik RAM |
|---|---|---|
| Factory | 732B /2bbb4ab82b1af9609405bbf94e31c31981845f1f1912c822e7cbd2a1fe7fd0e2 |128B |
| MSC factory varyantı |2848B /66efc7b861249c4cebc9f1083cfcde9f6ba6ee0121de5a4bd7dc9a569cff383f |Önceki256B |
| Storage factory varyantı |1452B /0fb30b731592ad818529f4d770df751971f3b44941d0cc0abb81386cc611802b |Önceki128B |

Factory0807BA00..0807BCDC,state20048220..200482A0;toplam2424B sentetik.
MSC/storage optional class-policy/config-ready hook'larıyla yeniden üretilir;
varsayılan hash'leri aynı. Önceki overlay'ler yeni varyant entry adreslerine
byte assert'leriyle bağlanır. Snapshot/canary ve gate overlap kontrolü vardır.
Yerel CFG audit SP delta0,BL8,max32B frame;2 yeni maskeli bölüm/max11 komut,
call-loop yok. Tam native call stack/ISR latency/cycle kanıtı değildir.

İlk instruction-budget hataları stock wait/tick alanı modelindeki eksikten
kaynaklandı. Sonra eksik USBRST ve iç deinit R0 clobber düzeltildi. Son düzeltme
factory sırasında gelen harici reset için service'in erken0 dönmesini önler.
Başarısız loglar da logs/usb-factory-20261028 altında korunur.

Kaynaklar:src/midi_usb_factory_prototype.py;scripts/{midi_usb_factory_test_support,
audit_midi_usb_factory_prototype,trace_midi_usb_factory,probe_midi_usb_factory}.py;
tests/test_midi_usb_factory.py. Komutlar,production pin'leri ve kanıt diff/hash
dosyaları STATUS.md'de. Sonraki somut iş USB suspend/wakeup IRQ yollarıdır.
Tam Packs UI/project,task/power/boot/OOM,checked RAM/init,gerçek backend/IRQ
bariyeri,storage project short-read/live-pattern alias,DIN input ve üretim
entegrasyonu açık. Stok syx değişmedi;özel SD filesystem eklenmedi.
