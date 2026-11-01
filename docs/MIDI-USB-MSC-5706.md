> Güncel28 Ekim:402 toplam/87 aday PASS. Native READ10→queued backend /
> drain/worker→USB veri/CSW ve reset iptali emülasyonda testli. İlgili READ
> hatasının sonraki başarılı iş tarafından örtülmesi engellendi. Pin'li stok
> MSC yazma korumalı;WRITE10 media yazmasına ulaşmaz. Alt flash RAM,RTOS
> wake/yield sınırdır.2296B checked RAM/init ve full factory/class/power/task /
> boot/gerçek bariyer açık. Üretim aynı/Off-Stop FAIL,M7 NO-GO.
> STATUS.md ve MIDI-USB-STORAGE-5706.md güncel.

---

# MSC CBW iptali ve native Bulk-Only Reset — 28 Ekim 2026

Yeni emülasyon katmanı31B CBW bekleyen MSC OUT2 aktarımını ortak USB
bariyerine katıyor. MIDI/DIN kuyruklarını veya shared RX FIFO'yu silmeden
native deconfigure ve Bulk-Only Reset sonrası yeniden kurulum testli.
Bu üretim firmware'i değildir;M7 NO-GO. Fiziksel cihaz API erişimi yoktur.

## Akış ve sahiplik

Root40B7E teardown ve native2EFF8 BOT reset artık ertelenir. Request hemen
MSC/MIDI admission'ı dondurur. MSC native poll27624 ve2F014/2F04A handler'ları
eski ready CBW'nin yeni storage komutuna dönüşmesini önler;zaten poll içinde
olan görev TASK_BUSY ile korunur. Yeni main service sırasıyla:

1. MSC job'ının31B CBW olduğunu,BOT komutunun başlamadığını ve IN82'nin
   aktif olmadığını doğrular. Diğer safhaları silmeden kapalıda tutar.
2. Yalnız EP2 IRQ maskelerini kapatır,SNAK/EPDIS ister,gereken ACK ve EPENA0
   koşullarını bekler. Shared RX FIFO CPU tarafından boşalmadan ilerlemez.
3. AHB idle ve seçili TX FIFO2 flush-complete bekler. Global RX flush yapmaz.
4. Ancak sonra HAL transfer pointer/count ve ready byte+28'i bırakır;counter
   kapasite+29 korunur. CBW buffer içeriği silinmez;epoch ilerler.
5. Önceki MIDI session bariyerini tamamlar;native class teardown veya gerçek
   BOT reset/tek CBW rearm ve MIDI resume uygular. Yeni request generation'ı
   eski commit ile kaybolmaz. Kısa maskeli commit/reservation blokları kullanır.

MSC RX callback'i native IRQ içinde snapshot claim eder. Native CPU FIFO
kopyası ve diğer interface kayıtları bitmeden ready yayımlanmaz. Bu,hardware
generation tag'i değildir:iptal sözleşmesi bozulup eski untagged XFRC yeni
job'dan sonra gelirse yeni job gibi görünür;zorunlu negatif test korunur.

## Kanıtın kapsamı

| Alan | Kanıt / sınır |
|---|---|
| Native kod |661F8/2EFF8,27624/2F014/2F04A,HAL/IRQ/531CC ve ready atomic gövdeleri yürür |
| İptal |31B CBW bekleme,kısmi CPU RX,henüz işlenmemiş completion;sentetik ACK/AHB/flush sözleşmesi |
| Koruma | DIN Off,admitted MIDI debt,ortak RX FIFO,CBW içeriği ve deferred job sahipliği |
| Reset | Native EP0 Bulk-Only Reset(0xFF),USB reset/enum/address/config ve deferred native teardown |
| Overflow |32B padded CBW word-copy sınırı;bad<=64B private scratch drain ve fail-closed |
| Storage | Init(LUN0) önceki pin'li native return0 sınırı;media I/O kanıtı yok |
| Açık | Başlamış SCSI/async storage,data/CSW/TX cancel-drain,power/task/class-list/full boot |
| Donanım | Test yok;gerçek disable/NVIC/cache/bus-master/cycle kanıtı yok |

Native531CC tam word yazar;31B CBW32B padded alanda sınırlandırılır. Tekrarlanan
hatalı64B packet scratch'ın dışına taşmaz. >64B bozuk status ve DMA modları
güvenli normal servis olarak desteklenmez;fail-closed durumdan reopen yoktur.
Genel MSC data buffer'ları için aynı güvenlik kanıtı ileri sürülmez.

## Kod, doğrulama ve kalan iş

src/midi_usb_msc_prototype.py:2924B,0807A800..0807B36C;state256B
20048020..20048120,64B scratch dahil. Toplam2168B state sentetiktir;production
checked reservation/init yapılmadı.10 stok +2 generated control-entry overlay,
byte/assert/overlap/app bounds kontrolleri var. Yerel audit SP delta0,BL8
hizalama,max32B local frame,4 yeni maskeli bölüm/max29 komut/call-loop yok.
Inherited control max38 komut aynı. Tam native stack/timing kanıtı değildir.

21 yeni/384 toplam test PASS. Paket probe21 PASS,audit/stock trace PASS;
exit2/NO-GO beklenir.87 aday regresyon ve6 sınırlı kriter PASS;üretimde
bilinen Off/Stop kaybı sürer. Build/baseline/production safety audit PASS.
Önceki prototip codegen'leri ve üretim SYX aynı;tek eski helper değişikliği
optional EP2 disable ve manuel TX2 flush-complete MMIO modelidir.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/probe_midi_usb_msc.py logs/usb-msc-cancel-20261028/probe-final
.\.venv\Scripts\python.exe scripts/verify_phase1_candidate.py
```

Log/diff/hash:logs/usb-msc-cancel-20261028. Native counter kapasitesini word
clear ile bozma hatası byte clear'a düzeltildi. Kısmi-packet fixture'ının EP0
setup sırası düzeltildi;ilk FAIL logları saklı. Native parent submit hatasını
yuttuğundan wrapper ticket-wrap'te ayrıca kapalı durumu doğrular.

Sonraki iş:native SCSI READ10/WRITE10→stok storage callback/worker zincirinde
buffer ve async işlem sahipliğini izlemek;reset/deconfigure sırasında güvenli
drain/abort sonucu ile bugün kapalıda tutulan data/CSW/TX safhalarını çözmek.
Özel SD filesystem yazılmayacak. Üretim entegrasyonu,tam boot/RAM/init/OOM,
storage short-read/live-pattern alias,DIN input,power/task ve gerçek
bariyer/timing kapıları tamamlanmadı. Firmware yüklenmemeli.
