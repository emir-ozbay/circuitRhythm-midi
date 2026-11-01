# Native port, görev geçişi ve işçi dönüşü — 5706

30 Ekim 2026. **M7 NO-GO.** Firmware ve üretim kaynakları aynı;bu tur host
emülasyonunu genişletir. Cihaza veya fiziksel MIDI/USB API'sine erişilmedi.

## Kapanan pencere

Exact SYX,önceki reset/main modeli üzerinden başlatılır. Sonra stock
`25430 → 25C88` port başlangıcı da yürür. NVIC priority probe'u4 uygulanan
bit varsayımıyla modellenir. Native kod kritik bölge sayacını`AAAAAAAA`'dan
`0`'a getirir,MSP/CONTROL ve timer/FPU ayarlarını kurar;`25CA6` SVC kenarına
ulaşır. Sayaç veya current-TCB RAM'i test tarafından hazırlanmaz.

Mimari temel exception frame'i modelde stack'e konur;native`25C6C` SVC handler
gerçek ilk IDLE TCB'sini restore eder. Native`25C10` PendSV handler outgoing
R4–R11/LR'yi kaydeder,`24F84` ready-list selector'ını çağırır ve incoming
bankayı restore eder. Model,handler'ın gerçek PSP'sindeki temel frame'i
unstack eder. Her geçişte kaydedilen register/stack frame ve geri yüklenen
banka byte olarak kontrol edilir;ready list veya görev sonucu verilmez.

İlk sıra IDLE→Main→UI→Storage→Content→IDLE'dır. Storage'ın native
`6487C/648A4/648AE → 2C278` worker yolu isteği işler. Main'in`2C23A` isteği
bit0'ı yükseltir;Storage'ın native kodu temizler. Main kendi PSP/PC/register
bağlamına dönüp`2C274`'ten çıkar. İlk talebin caller devamı`26F72`'dir.
Hem bayrağın temizliği hem gerçek Main dönüşü ayrı gözlenir.

| Ölçüm | Sonuç |
| --- | --- |
| Port başlangıcı öncesi heap /tahsis |`2000B618` /129 |
| İlk Main worker caller dönüşü |`26F72`,heap`2000B620` |
| Yeni pencere sonu |Main`26596` giriş hazırlığı kontrolü |
| Heap /tahsis |`20010BEC` /203;stock boyut/adres sırası aynı |
| İstek /native Main completion |9 /9 |
| Native worker çağrısı /PendSV geçişi |29 /128 |
| Modellenen WFI timer wake |39 |
| Minimum MSP |`2004FF08`;yalnız bu model/pencere |
| İlk SVC'nin kalan MSP frame'i |`2004FFE0`,32B |
| Reserved1088B |Router/3-port kaydı sonrasındaki state aynen korunur |

Gözlenen en düşük task stack adresleri,temel context save alanı dahil:

| Görev | Stack başlangıcı | Gözlenen alt adres |
| --- | --- | --- |
| Main |`20007B9C` |`200085E8` |
| UI |`2000891C` |`200090B4` |
| Storage |`20009184` |`200095B4` |
| Content |`200096F8` |`20009B74` |
| IDLE |`2000B1BC` |`2000B564` |

Her frame kendi görev aralığında kalır;ilk16B canary korunur. Bunlar görevlerin
tam ömrü,gerçek IRQ nesting/FPU veya fiziksel maksimum stack iddiası değildir.

## Sonraki kapı artık belirli

Native`26596`,üç giriş örnekleyicisinin`+2A` halfword sayacını en az2 bekler.
Root`20000834`;nesneler`2000AA08`,`2000AA78`,`2000AF80`. Bu modelde sayaçlar
`0/0/0`,gerçek fonksiyon dönüşü0'dır. Hazır dönüşü veya sayaçlar zorlanmaz.
Main`25864` çalışma döngüsüne henüz ulaşmaz;`20010BEC` son heap high-water
değeri sayılamaz. Eski fixture`2004EA98` hâlâ boot ölçümü değildir.

**Sonraki tek somut iş:** Native giriş örneği/IRQ producer'ını ve
`265BA → 2BB64/2BC28/2BEE2` sayaç güncellemesini izleyip,gerçek native
producer üzerinden`26596` kapısını açmak;Main'i`25864`'e kadar sürdürmek.

## Sınırlar ve negatifler

- Mimari temel8-word frame,STKALIGN padding ve native software bankası
  modellenir. Dört priority-bit varsayımı ve kontrollü IRQ teslimi kullanılır.
  Tam NVIC/priority/nesting/timing kanıtı değildir;PendSV IT dışına ertelenir.
- Thread FP/coprocessor komutu yürütülmeden hata verir;extended FP frame'i
  sessizce atlanmaz. Native FPSCR setup çağrısı bu fail-closed testte kullanılır.
- RCC/QSPI/scripted ID/response-timeout SDIO ve diğer IRQ adaptörü sınırları
  önceki main modeliyle aynıdır. Gerçek kart/flash/pack verisi,ADC/DMA örnek
  akışı ve bütün IRQ adaptörlerinin mimari exception entry'si modellenmez.
- PendSV dispatch kapalıysa istek pending kalır;completion uydurulmaz.
  WFI wake kapalıyken worker bayrağı temizlense de Main'e dönüş gerçekleşmez.
  Wake verilince native devam tamamlanır. Bu iki sonuç ayrı testlidir.

İlk prototip,geçişten sonra eski caller PC'sini kullanıp yeni görevi yanlış
adreste sürdürüyordu;runner artık native restore edilmiş PC'den devam eder.
Port başlangıcı atlanınca`AAAAAAAA` kritik sayaç kaldığı için worker beklemesi
ilerlemiyordu;native port yürütülür. Unicorn WFI sonrası doğal duruş da timer
wake sınırı olarak ele alınır. Bu model eksikleri firmware hatası diye yamalanmadı.
Caller checkpoint'i`26F6E` istekten önceydi;gerçek dönüş`26F72` olarak düzeltildi.

8 yeni test;119 odaklı/90 packaged +6 sınırlı Faz1 ölçütü PASS. Bu sayılar
örtüşür. Discovery608;tam608 bu turda koşulmadı. Önceki529/98 kayıtları korunur.
Strict CRC/vector/range/CFG/ABI PASS. Firmware/stock/default/codegen aynı.

Güncel karar ve komutlar:[STATUS.md](STATUS.md). Exact kaynak diff/pin,aynı
önceki/sonraki SYX ve kanıtlar:`logs/recovery-worker-20261030`.
