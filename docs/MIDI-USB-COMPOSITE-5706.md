> Güncel28 Ekim:384 toplam/87 aday PASS. Aktif31B MSC CBW bekleme aktarımı
> disable/ACK/AHB/shared FIFO/TX2 flush modeliyle iptal edilip native deconfig /
> Bulk-Only Reset sonrası tek job ile yeniden açılır. MIDI/DIN korunur.
> Başlamış SCSI/storage,data/CSW/TX iptali hâlâ açık;durumları kapalıda tutulur.
>2168B checked RAM/init,task/power/full boot ve gerçek bariyer/timing açık.
> Üretim aynı/Off-Stop FAIL,M7 NO-GO. STATUS.md ve MIDI-USB-MSC-5706.md güncel.

---

# Gerçek MIDI parent ve boşta MIDI+MSC kurulumu — 28 Ekim 2026

Gerçek native class parent'ları ve composite liste artık sentetik RAM/MMIO'da
çalışır. Bu ayrı emulator overlay'idir;üretime eklenmedi,M7 NO-GO.

## Bulgu ve düzeltme

MIDI callback tablosu80676F4'ün init'i68A2C'dir.297C0 tüm çıkış portlarını
temizler;bekleyen iki DIN Note Off kopyasının kaybolması negatif testte
doğrulandı. Ardından29AB0 MIDI RX rearm dener. Composite guard yalnız
RUNNING/init-busy,aynı request generation,SS SEALED,USB RX/TX sahibi yok,
kayıtlı router/MIDI class ve LR68A37 bağlamında clear'ı atlar. USB zaten
session bariyerinde temizlenmiştir. Normal router clear native kalır.

Native root40B5A'yı MIDI525B2 gate'inde tek başına ertelemek,MSC kurulumunu
IRQ içinde öne geçirirdi. Yeni katman kayıtlı iki-class isteğini root girişinde
kuyruklar;cc_service native-init girişinden aynı40B5A listesini bir kez yürütür.
MIDI parent,sonra gerçek MSC parent661DC çalışır;ancak sonra MIDI resume olur.
MSC OUT2 constructor'ının ortak RX FIFO flush'u,owned sealed525CB caller'ında
atlanır;IN81/FIFO1 ve IN82/FIFO2 native flush'ları yürür. Diğer flush'lar önceki
guard/native yolda kalır. IRQ fixture optional FIFO2 seçimini modeller;
seçili başka FIFO flush'u MIDI TX FIFO içeriğini silmez.

## Kanıtın kapsamı

| Kanıt | Sonuç ve sınır |
|---|---|
| Byte/disassembly | Stok hash'i,callback tabloları,çağrı PC'leri ve prologue'lar pin'li |
| Statik initializer emülasyonu | Native68A54 ve6668C,RAM class nesneleri/endpoint array'leri;tam boot değil |
| MIDI gerçek parent |68A2C/297C0/29AB0 gövdeleri;DIN Off koruma ve native clear kontrolü |
| MSC gerçek parent |661DC/2F00C/2EFC8,31B OUT2 CBW arm;storage Init(LUN0) pin'li native return0 sınırı |
| Descriptor | Native40A78,200067E0:125B,3 interface,MIDI OUT1/IN81 ve MSC IN82/OUT2 |
| Kontrol/lifecycle | Native reset/enum/EP0 address/configuration,main service,inquiry yanıtı,iki-class deinit |
| Yarışlar | Parent'lar arası reset sonraki class'ı durdurur;MSC arm sonrası reset resume'u durdurur,sahibi tutar |
| Aktif MSC | EP2 EPENA/pending IRQ veya BOT busy varken init reddedilir;iptal uygulanmadı |
| Donanım | Test yok;fiziksel USB/MIDI/device API erişimi yok |

Fixture native MIDI/MSC callback tablolarını kullanır;MSC endpoint nesneleri
native26828 ile oluşturulur. Root/controller ve MIDI endpoint bağları bilinen
native şekle göre sentetik RAM'dedir. Tüm boot ve initializer grafiğinin bu
nesnelerle runtime'a bağlandığı kanıtı değildir. Önceki 'yalnız scatter-load'
tanımı eksikti:68A54 endpoint constructor'larını da çalıştıran statik initializer
walker'ıdır;eski raporlar tarihsel olarak korunur.

## Kod ve testler

src/midi_usb_composite_prototype.py:996B,kod0807A400..0807A7E4;
96B state20047D80..20047DE0,toplam1912B sentetik state.4 stok gate ve1 generated
control-entry overlay;byte assert/overlap/app bounds kontrollü. Yerel audit:
SP delta0,BL8 hizalama,max24B ek frame,ek maskeli bölüm yok. Bu tüm native
stack veya cycle/IRQ latency kanıtı değildir. Default control/IRQ/session
codegen değişmedi. Üretim state reservation/init yapılmadı.

363 tüm test/16 yeni composite test/87 aday regresyon/6 sınırlı kriter PASS.
Paket probe ve aday verifier exit2 verir:bilinen üretim Off/Stop kaybı ve
diğer M7 engelleri sürer. Build/baseline/production safety audit PASS.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/probe_midi_usb_composite.py logs/usb-composite-20261028/probe-final
.\.venv\Scripts\python.exe scripts/patch_firmware.py --build-phase1
.\.venv\Scripts\python.exe scripts/verify_phase1_candidate.py
.\.venv\Scripts\python.exe scripts/run_baseline.py
```

Kod SHA25610d64c5e138fe59210d44e3f614fd5633cd3312d8fc136c925b18cce49533586.
Firmware SYX SHA2563c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d;
image38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf;
CRC53F96711,21 patch/1376B fark. Diff/hash/loglar:logs/usb-composite-20261028.

## Açık kapı ve sonraki iş

Yalnız bilinen iki-class listesinde boşta kurulum kanıtlandı. Aktif MSC data /
CBW job iptali,class-specific request'ler,Packs/MIDI-only liste değişimi,
power-state/task wiring,genel software cancel/drain açık. Native MSC close
gövdesini çalıştırmak hardware EPDIS/ACK/late DMA iptali kanıtı değildir.
Eski untagged XFRC'nin bozuk bariyer sonrası yeni job gibi görünmesi inherited
zorunlu negatif testte sürer. Gerçek NVIC/cache/timing/bus-master,tam boot /
OOM,1912B checked RAM/init,storage short-read/live-pattern alias,DIN input
ve üretim entegrasyonu tamamlanmadı. Firmware yüklenmemeli.

Sonraki iş:MSC OUT2'nin31B CBW bekleyen job'ını native BOT/class-specific
request ve EP2 disable/ACK yollarıyla izleyip ortak reset/reconfigure
bariyerine katmak;MIDI/DIN ve ortak RX FIFO sahipliğini koruyarak yeniden açmak.
