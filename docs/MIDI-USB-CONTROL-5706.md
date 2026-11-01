> Güncel28 Ekim:363 toplam/87 aday PASS. Gerçek MIDI parent'ın DIN FIFO
> silmesi dar owned caller guard ile düzeltildi. Boşta native MIDI+MSC kurulum /
> teardown ve125B/3-interface descriptor koşullu PASS;storage Init sınırı var.
> Aktif MSC job iptali sonraki iş;class-specific/power/task,1912B checked RAM /
> init,tam boot/storage/gerçek bariyer/timing açık. Üretim aynı/Off-Stop FAIL,
> M7 NO-GO;cihaza erişilmedi. STATUS.md ve MIDI-USB-COMPOSITE-5706.md güncel.

---

# Native USB kontrol/reset ve deferred MIDI class — 28 Ekim 2026

USBRST/ENUMDONE,EP0 SET_ADDRESS/SET_CONFIGURATION(0/1),native class
deinit/init ve MIDI yeniden açma yolu emülasyonda koşullu çalışır. Eski TX
hardware job,bariyer bitmeden yeni class kurulumuna geçemez. **Parent bildirimi
pin'li native no-op sınırıdır.** Gerçek parent/composite MSC,tam power-state /
descriptor/task ve fiziksel iptal bariyeri kanıtlanmadı. Üretim aynı ve M7
NO-GO;cihaz/MIDI/USB API erişimi yoktur.

## Native yollar ve yeni sahiplik

Pin'li stok disassembly ve yürütülen zincir:
`4293E → 2C78C → 425A8 → 44DD8 → 42584/4259A → 2AB08/2AB14 →
40B5A/40B7E → 525B2/5261C`. Bir test native reset→enum→SET_ADDRESS→
SET_CONFIGURATION akışının tamamını yürütür;diğer bazı testler addressed
state'i başlangıç önkoşulu olarak kurar. Native EP0 status ZLP de native
HAL yolundan geçer. Descriptor keşfi ve bütün USB standard request'ler
test edilmiş değildir.

Yeni1464B kontrol kodu `08079C00`,96B state `20047F80` üzerinde durur;
toplam1816B RAM sentetiktir. Üretimde checked reservation/init yoktur.
`midi_usb_irq_prototype.py` optional IRQ maskesi/üst faz parametresi alır.
Default820B kod/hash aynı kalır. Kontrol varyantı SOF/USBRST/ENUMDONE'a ve
sealed fazda kontrol IRQ'suna izin verir;yalnız2 immediate değişir.

Reset/deinit kabulü hemen dondurur;epoch/queue/payload/held ownership silmez.
Class init isteği tek slotta saklanır ve tekrarları idempotenttir. Ana bağlam
service'i mevcut session close/disable-ACK/FIFO-flush protokolünü ilerletir.
Yazılım sahipleri boş ve bariyer sealed olduktan sonra native525B2 çalışır;
sonra oturum fazı/configured/binding/IRQ/FIFO durumu yeniden doğrulanıp
RX açılır. USB status callback'i daha önce dönebilir;MIDI ucu hazır olana
kadar receive kurulmaz. Native parent'ın gerçek uygulama sözleşmesi açık
olduğu için bu tam caller uyumu değildir.

Event generation ve son commit kısa maskeli alanda tutulur. Native init
sırasında veya final commit öncesinde gelen reset kaybolmaz;eski queued
init'in üzerine yeni reset gelirse yeni host configuration beklenir.
Resume beklerken native constructor/parent callback tekrar çalıştırılmaz.
Wrap,IRQ/masked/recursive service reddedilir. Bekleyen software RX borcu,
shared SysEx okuyucusu,partial mesaj,held nota ve Off/fault varsa kapalıda
kalır;sahiplik silinmez. Genel aktif işlem cancel/drain hâlâ yoktur.

## Native bootstrap,flush ve SOF ayrımı

`525FE → 268D0`,wire completion değil availability initialization'dır.
Yalnız owned sealed/init-busy/no-active-TX ve native52603 return PC ile
kabul edilir. Normal runtime completion'ın IRQ snapshot yolu aynı kalır.

`525C6 → 2C928/4312C/52E22` **global RX FIFO flush** yapar. Bu yüzden yalnız
kayıtlı MIDI OUT1,deferred owned init ve pin'li525CB return PC koşulunda
atlanır;bariyer zaten tamamlanmıştır. Diğer native yollar aynen ilerler.
IN81'in seçili TX FIFO1 flush'u native yürür. USBreset'in bütün TX FIFO'larını
flush etmesi stok reset davranışıdır ve native kalır. Bu dar guard,bütün
composite MSC trafiğinin güvenli olduğunun kanıtı değildir.

`SOF5271A → 268EC → 2691E`,completion callback'ini kullanmadan partial RX
yayımlayabilir. Kayıtlı MIDI SOF poll'u bu deneyde bastırılır. RX submit,
tek64B MTU ile sınırlandırılır;SS owned-limit de bu gerçek uzunluğu kaydeder.
66B native ring kaydı sığmıyorsa aktif job ayrılmaz;RX_PAUSED tutulur.
Ana service,consumer alan açınca tekrar arm eder. Bu,sahte RX_ACTIVE job ile
sonsuza dek kapanma sorununu önler. Task wiring ve gerçek throughput/latency
bütçesi kanıtlanmadı. Diğer endpoint'lerin submit/poll yolu bu dar değişikliğin
dışındadır.

## Test sınırları

8 native emulator gate;stok prologue assert,overlap/app-bounds denetimi ve
trampoline'larla kurulur. Bu üretim patch paketi değildir. Yerel ABI/CFG:
SP delta0,BL8 hizalama,max32B frame PASS. Yeni zorunlu maskeli alan max38
komut;call/loop yok. Tam native stack/exception frame veya cycle kanıtı değildir.

Fixture USBx40040000 register/FIFO davranışını ve native flush completion'ını
modeller. EP0,HAL ve class walker kodu native yürür;parent bildirimi80427D2
native no-op sınırıdır. Handle/controller/list'ler sentetik;IPSR enjeksiyonu
gerçek NVIC değildir. Native varsayılan IRQ ve önceki session codegen hash'leri
aynıdır. Optional kontrol/MMIO/EP0 fixture desteği için3 eski kaynak bilinçli
güncellendi;diğer önceki kaynaklar korundu.

Donanım XFRC generation taşımaz. Bariyer sözleşmesi ihlal edilip eski XFRC
yeni RX kurulduktan sonra gelirse yeni job tamamlanmış görünebilir. Bu
negatif test hâlâ vardır. Gerçek disable/FIFO/cache/bus-master/NVIC sırası
kanıtı olmadan reconnect güvenliği iddiası yoktur. Suspend/wakeup ve DMA
unsupported/fail-closed;gerçek parent/MSC/descriptor/task/full boot/OOM /
checked RAM/timing/storage/DIN input kapıları açıktır.

22 yeni/347 toplam test PASS. Packaged candidate üzerine aynı emulator
overlay testleri22 PASS. Build/baseline/production audit/87 regresyon ve6
sınırlı kriter PASS. Üretim adayı Off/Stop kaybını sürdürür;probe/verifier
exit2 ve M7 NO-GO.

Log kökü `logs/usb-control-20261028`,özellikle `probe/report.json`,
`probe/audit/control-code-report.json`,`probe/stock-contract/control-contract.json`.
Kontrol kod SHA256:
`97240c3b615a45755022470af82278fac7db25ebdff9970800f12a05442f76e2`.
IRQ kontrol varyant SHA256:
`8a63d6c5c85574fa362ebff18c9048a1298bedd0202755ad1a1ce0492df8b5b1`.
Üretim SYX SHA256:
`3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d`.
Stok SHA256:
`11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf`.

Sonraki iş:525B2/5261C'nin gerçek MIDI class-parent callback'i ve composite
MIDI+MSC listesinin native kuruluş/teardown'unu no-op sınırı yerine yürütmek;
ertelenmiş init'in parent/status/diğer arayüz sözleşmesini koruduğunu göstermek.
Fiziksel test önerilmez.
