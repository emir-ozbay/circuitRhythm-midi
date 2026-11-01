> Güncel28 Ekim:418 toplam/87 aday PASS. Native432A8 USB factory artık
> eski MIDI/MSC reader ve parent teardown bitmeden class listesini değiştirmez.
> MIDI-only↔MIDI+MSC descriptor/query/READ ve geçiş içi yeni istek/reset koşullu
> emülasyon testli. HAL init,tick/NVIC/clock ve RTOS sınırları sentetiktir.
> 2424B checked RAM/init,USB power/task/full boot/gerçek bariyer ve tam Packs
> akışı açık. Üretim aynı/Off-Stop FAIL,M7 NO-GO. STATUS.md ve
> MIDI-USB-FACTORY-5706.md güncel.

---

# Native MSC READ10, readonly binding ve per-read sonuç — 28 Ekim 2026

Emülasyon prototipi native READ10/veri/CSW yolunu ortak iptal bariyerine
bağlar. Gerçek queued backend,drain ve worker kodu çalışır;alt flash RAM
kopyası,RTOS wake/yield sınırdır. Üretime eklenmedi;M7 NO-GO.

## Doğrulanan stok bağ ve düzeltilen hata

Native initializer200038AC→20003888 storage tablosunu kurar. Callback'ler
650D0 Init,650D4 capacity(4096B block),650E4 ready,650E8 write-protect,
65128 read ve65194 write'tır.650E8 daima1 döndürür;WRITE10 native SCSI
yolunda DATA PROTECT/failure CSW alır,write callback çağrılmaz.43264 mod
seçicisinin1/2/3 değerleri tabloyu değiştirmez. Bu pin'li tablo için kanıttır;
bütün yeniden bağlama/factory grafiği için değildir. Yazma açılmadı.

READ65128,backend vtable+0C2C394 ile24B read işi kuyruklar;vtable+1C2C23A
drain request'ini bekler. Native2C278 işi tüketir,alt flash sonucunu2C328'de
yazar ve kuyruğun sonunda drain bitini temizler. Fixture gerçek2C190
constructor/FIFO/atomic/worker gövdelerini kullanır. Yalnız alt flash ve
RTOS wake/yield sınırları değiştirilmiştir;host kodu ready/drain'i zorla bırakmaz.

65128 alt read başarısız olsa da0 döndürebilir. Yeni katman yalnız ilgili
4096B read işinin sonucunu2C328'de kaydeder. Hata veya eksik sonuç SCSI'ye
-1 döndürülerek failed CSW üretir;başarılı data yollanmaz. Başka bir başarılı
iş shared last-status'ı0 yapsa da ilgili hata kaybolmaz. Orijinal hatayı
yutan callback ayrı negatif kontrolde yürütülür.

## Reader ömrü ve iptal

| Alan | Koruma |
|---|---|
| Stok data buffer40024000/4096B | Native read/worker bitmeden veya USB kullanırken yeniden read yok |
| CSW20006DD4/13B | IN82 sürerken sonraki CBW'nin poll/parse işlemi durur |
| Backend | Pin'li nesne/vtable/queue,pending counter,request word,FIFO boşluğu ve IO/task/IRQ sahipliği kontrol edilir |
| USB | Epoch/ticket claim,native FIFO/IRQ completion veya disable/ACK/AHB/shared FIFO/TX2 flush |
| Reset | Read sürerse iş ve drain beklenir;eski data/CSW reader ancak bariyer sonrasında bırakılır |
| MIDI/DIN | DIN Off ve USB inquiry yanıtları emülasyonda korunur |

Lower flash error,CSW+next-CBW cancel,iki blok read,worker içinde reset,
erken direct read/CBW ve missing ACK testli. Eski untagged XFRC bozuk bariyer
sonrasında yeni job'ı claim edebilir;zorunlu negatif korunur. Gerçek controller
iptali,NVIC/cache/DMA/scheduler veya flash/SPI davranışı kanıtlanmadı.

## Kod ve sınırlar

1452B storage kodu0807B400..0807B9AC;128B state20048140..200481C0;
toplam2296B state sentetiktir. MSC optional-hook varyantı2876B;
default2924B MSC ve önceki codegen hash'leri aynı. Production checked RAM /
init yoktur.6 stok +1 generated storage gate,byte/overlap/app bounds/full
flash snapshot/canary kontrolleri var. RTOS boundary patch'leri fixture'da
ayrı kaydedilir. Yerel audit SP delta0,BL8 hizalama,max32B local frame;
1 yeni maskeli bölüm,max25 komut/call-loop yok. Tam native stack/timing kanıtı değil.

402 tüm test/18 yeni paket deneyi/87 aday regresyon/6 sınırlı kriter PASS.
Paket probe ve candidate verifier exit2 verir;üretimde Off/Stop kaybı sürer.
Build/baseline/production safety audit PASS. Diff/hash/log:
logs/usb-storage-20261028;güncel komutlar ve SHA256 STATUS.md'dedir.

Sonraki iş native432A8→40A30/40B44 factory/teardown/setup zincirini
MIDI-only/composite class listeleri ve Packs mod geçişlerinde bariyere
bağlamaktır. Şimdiki binding bilinen iki-class listeyle sınırlı. Full power /
task/boot/OOM,2296B reservation/init,gerçek backend/IRQ bariyeri,storage
project short-read/live-pattern alias,DIN input ve üretim entegrasyonu açık.
Özel SD filesystem eklenmedi;fiziksel cihaz API erişimi yok. Yüklenmemeli.
