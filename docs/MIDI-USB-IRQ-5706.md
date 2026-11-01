> Güncel devam:ayrı kontrol katmanı ve optional IRQ policy varyantı,native
> USBreset/enum/EP0 address/configuration ve bariyer sonrası class init'i
> emülasyonda bağlar. Default820B IRQ codegen/hash'i aynı kalır.347 toplam /
>22 yeni kontrol testi PASS. Parent bildirimi native no-op sınırı;gerçek
> parent/MSC/task/power/descriptor ve fiziksel bariyer açık,M7 NO-GO.
> MIDI-USB-CONTROL-5706.md ve STATUS.md güncel;alttaki deney tarihsel kayıttır.

---

# Native USB completion IRQ köprüsü — 28 Ekim 2026 / deney

Stok HAL submit,FIFO,IRQ ve completion callback zinciri,CPU FIFO modunda
emülasyona bağlandı. Test completion token'ını dışarıdan sağlamaz. **PASS
yalnız sentetik register/RAM sözleşmesiyle yürütülen completion alt kümesi
içindir.** Tam USB kontrol/reset/disconnect recovery ve gerçek iptal bariyeri
kanıtlanmadı. Üretim firmware'i aynı,M7 NO-GO;cihaz/MIDI/USB API erişimi yok.

## Native kanıt ve çalışan yollar

Pin'li stok disassembly ve emüle yürütme:

- RX:`4293E → 2C798 → 42614 → 2AB42 → 40C46 → 526C8 → 26988`.
- TX:`4293E → 2C7AC → 42690 → 2AB36 → 40C22 → 5268E → 268E0 → 268D0`.
- `806776C` native callback tablosu ve `20006F20` root global'i kullanılır.
  Sentetik sınıf/endpoint listeleri native walker'ların kendi RAM düzenindedir.
- Önceki `2C9B8`/`42FD8` stub'ları bu fixture'da kaldırılır. Native HAL
  `4301A`/`42FD8` ve `52F52` transfer pointer/count/TSIZ/EPENA kurar.
  `531A6` TX FIFO'ya gerçek payload word'lerini yazar;`531CC` RX FIFO
  word'lerini gerçek native load/store ile staging RAM'e kopyalar.
- `2C82A..2C862` kurulum prefix'i native yürütüldü:handle `200054B4`,
  USBx `40040000`,6 endpoint ve handle+10=0 CPU FIFO modu. `427FC` hardware
  init'inden önce durulur. Bu tam boot veya gerçek MCU/NVIC testi değildir.

`trace_midi_usb_irq.py` stok SHA doğrulaması,direct-call listesi,callback
tablosu/literal ve native pencere hash'lerini assert eder. Dolaylı grafiğin
tamamının çözüldüğünü iddia etmez. Canlı testlerde USBx40040000,sentetik
handle/controller/list binding ve IPSR16 enjeksiyonu vardır;gerçek exception
entry/NVIC öncelik/RTOS/cache yürütülmez.

## IRQ girişinden yayın sonuna sahiplik

`midi_usb_irq_prototype.py`,`08079000` tabanlı820B ayrı Thumb kodudur.
`20047F00` üzerinde96B state kullanır;toplam1720B RAM sentetiktir,üretimde
checked reservation/init yoktur. Önceki session/lifecycle/default codegen
değişmez;4 ek emulator gate kurulur.

1. Bridge IRQ girişinde HAL handle/base/mode ve maskeli cause'u doğrular.
   Halen sahipli RX/TX job kimliklerini,native callback'lerden önce bir kez
   snapshot eder. Yeni transfer henüz kurulamaz;eski job state'i aktif kalır.
2. Native `4293E` gövdesi çalışır. `26988`/`268D0` çağrıları kayıtlı nesne,
   doğru IRQ frame'i ve native return PC ile eşleşirse snapshot'ı bir kez
   claim eder;henüz payload publish/availability release yapmaz. Yanlış
   LR/IRQ dışı/nested çağrı yeni job'ı ödünç alamaz.
3. Native IRQ döndükten sonra TX completion ve uygun RX yayın yapılır.
   Callback anında güncel endpoint epoch/ticket'ı okunmaz;girişteki snapshot
   kullanılır. Session API'si aynı kimliği tekrar doğrular.

Stok IRQ sırası önemlidir:OUT completion loop'u,aynı turdaki RXFLVL CPU
kopyasından önce çalışabilir. Anında26988 dispatch etmek byte count0 veya
henüz kopyalanmamış staging'i kullanır. Bridge,native IRQ sonunu ve shared
RX FIFO boşluğunu bekleyip HAL count ile bir kez publish eder. FIFO birden
fazla RX status içerirse sonraki IRQ'ya aynı pending RX snapshot'ı taşır;
MIDI job yeniden kurulmaz. Cancel/resume epoch'u değişirse eski pending
snapshot sayılarak atılır;yenisine etiketlenmez.

Close sırasında halen sahipli eski CPU FIFO verisi native IRQ ile RAM'e
boşaltılabilir;LC frozen olduğu için yeni MIDI RX yayını yapılmaz. Ardından
önceki session bariyeri cleanup/epoch/resume akışını uygular. Bu yine model
disable/ACK/FIFO sözleşmesine bağlıdır.

## Negatifler ve üretim sınırı

**Snapshot donanım generation tag'i değildir.** Native XFRC bayrağında
epoch/ticket yoktur. İptal bariyeri ihlal edilip eski bir XFRC yeni transfer
kurulduktan sonra gelirse IRQ girişi bunu yeni job'a ait sanabilir. Zorunlu
negatif test yeni RX ticket'ının bu sahte eski olayla tamamlandığını gösterir.
Dolayısıyla gerçek disable/ACK/FIFO,CPU kopyası/cache/bus-master ve tam IRQ
sırası kanıtı olmadan reconnect güvenliği iddiası yoktur. Önceki deneyin
stale DMA buffer bozulma negatifleri de aynen korunur.

Bu bridge yalnız maskeli RXFLVL/IEPINT/OEPINT completion alt kümesini ve
CPU mode0'ı destekler. Reset/kontrol/DMA IRQ'ları fail-closed olur. Doğrudan
native5261C disconnect,endpoint-close öncesinde SS BROKEN/LC FROZEN yapar;
eski sahipleri temizlemez ve otomatik dönüş sağlamaz. Bu nedenle normal
USB kontrol/reset/reconfigure kullanımıyla üretim uyumu **FAIL** kalır.
Başlangıç constructor'ının untagged availability release'i de ayrı entegrasyon
gerektirir. Diğer endpoint'in native CPU RX kopyası testte MIDI job'ını
tamamlamaz;bu bütün MSC/control arayüzlerinin doğrulandığı anlamına gelmez.

Yerel ABI/CFG:SP delta0,BL8 hizalama,max32B yerel frame PASS;bridge yeni
PRIMASK bölgesi eklemez. Native IRQ gövdesinin yerel frame'i64B,bridge24B ile
88B'dir. Bu native callee/exception frame/IRQ nesting toplamı değildir.
Gerçek NVIC/cache/RTOS/cycle/latency ve bütün inline yazarlar açık kalır.

19 yeni/325 toplam test PASS. Packaged image üzerinde aynı emulator overlay
testleri19 PASS. Build/baseline/production audit/87 regresyon ve6 sınırlı
kriter PASS. Üretim adayı Off/Stop kaybını sürdürür;probe/verifier exit2,
hardware release NO-GO.

Log kökü `logs/usb-irq-20261028`;özellikle `probe/report.json`,
`probe/audit/irq-code-report.json`,`probe/stock-contract/irq-contract.json`.
Kod SHA256:
`ef45bacef7a218db2a8f2e4798a9bf60e899dbf1b7ffad044df037c3ff5b55d4`.
Üretim SYX SHA256:
`3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d`.
Stok SHA256:
`11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf`.

Sonraki iş:native reset/kontrol IRQ ve5261C→525B2 deconfigure/reconfigure
zincirini close/drain/barrier/resume'a bağlamak;bu fail-closed kısıtını
kapatmak. Sonra gerçek bariyer/NVIC/cache/timing,checked RAM/init,full boot /
OOM,storage,DIN input,genel cancel-drain ve üretim entegrasyonu gerekir.
Fiziksel test önerilmez.
