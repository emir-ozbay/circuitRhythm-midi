# Native SPI DMA ve koşullu yardımcı işlemci modeli — 5706

30 Ekim 2026. **M7 NO-GO.** Üretim kaynakları ve firmware değişmedi.
Fiziksel cihaz/MIDI/USB API'sine erişilmedi.

## Doğrulanan taşıma zinciri

Exact SYX önceki reset/main/port/worker/ADC akışından yürür. Native DMA1
stream3 RX ve stream4 TX ayarları doğrulanır: byte genişliği, normal transfer,
PAR `4000380C`, eşit pozitif NDTR, gerçek native RAM/flash adresleri.
Tamamlanmada model stream EN'i kapatır, NDTR'yi0 ve TC bayraklarını1 yapar.
Native IRQ30 `64732 → 41EE6` RX completion'ı; IRQ31 `64708 → 41EE2` TX
completion'ı atomik artırır. Native LIFCR/HIFCR yazıları W1C olarak işlenir.
Host completion RAM'ine veya native dönüş register'ına yazmaz.

RX memory increment kapalıysa native dummy hedef `20000184` üzerine yalnız
**bir bayt** yazılır. İlk30B transferin30 ardışık RAM baytına yazılmaması
regresyonla kontrol edilir. Flash DMA okuması vector/identity alanını da
içerebilir; patch yazı sınırını okuma sınırı saymak yanlış varsayımdı.
Firmware'in hiçbir instruction/vector baytı değiştirilmez.

`46510` paketinin dönüşünü kullanan caller izlenir. Yedi native dönüş noktasında
R0'ın okunmadan önce üzerine yazıldığı Capstone register-use analiziyle
doğrulanır; `31416 → 46414` için callee'nin ilk LDR R0 komutu da denetlenir.
Bu paketlerin MISO baytları program kararı üretmez. Kullanılmayan baytları
00 yerine A5 vermek bütün TX paketlerini, tahsisleri ve sonraki sınırı değiştirmez.

IRQ adaptörü temel PSP frame'ini kurup C gövdesini MSP üzerinde çalıştırır;
R4–R11/MSP/frame doğrulanıp CPU context'i host tarafından geri yüklenir.
Tam NVIC, exception return, nesting, FPU veya gerçek bus timing kanıtı değildir.

## Birbirinden ayrı iki sonuç

| Model | Sonuç ve kanıt sınırı |
| --- | --- |
| Varsayılan **strict** |3605 transfer/7210 native IRQ tamamlanır. Kullanılan ilk MISO yanıtında, RAM/DMA/flag yazısından önce durur.203 tahsis/heap20010BEC. |
| **busy** yardımcı işlemci | `bank0/register802B` için000000 döner. Native `312AC/312C8` döngüsü bekler; hazır olmaz. |
| **ready**, açık çevre birimi varsayımı | Native80802B selector sonrası400000 sorgusuna iki000000, sonra000001 yanıtı verilir. Native kod bunu yorumlayıp açılışı sürdürür.3819 transfer/7638 IRQ,1296 tahsis/heap20043D78. |

Ready yanıtı gerçek yardımcı işlemciden ölçülmedi ve o işlemcinin programı
emüle edilmedi. Bu, **koşullu boot ölçümüdür**; gerçek DSP hazır olma kanıtı
değildir. Farklı bank/register/caller/paket sessizce yanıtlanmaz. Yalnız wire
baytları modellenir; R0 hazır sonucu veya completion RAM'i verilmez.

Bu sonraki pencere için ayrıca takılı host olmayan USB core RAM modeli vardır:
GRSTCTL AHB idle ve reset/FIFO flush ACK'i anında verilir. Enum/EP trafiği veya
gerçek USB zamanlaması yoktur. Önceki no-response SDIO ve zero-data QSPI
sınırları sürer. Bu varsayımlar M7 fiziksel uyum kanıtına çevrilmez.

## Sonraki yer artık Content görevi

Stock/aday/A5 varyantında TX bayt dizileri, tahsis boyut/adres sıraları ve aynı
sonraki sınır eşleşir. Main25864'e henüz ulaşılmaz. İlk iki `2E4C0` çağrısı
geçerli nesneyle çalışır. Content görevinde `2E8B4` owner `+3C` alanından0
yükleyip `2E4C0`'a verir. `2E4CC LDRB [R0,#4]` öncesi guard durdurur:
R0=0, caller LR=`2E8BB`. Page-zero mapping veya yapay medya nesnesi verilmez.
Guard sayesinde canonical probe'da geçersiz erişim gerçekleşmez. Önceki
keşif yürütmesinde aynı okuma gerçekten unmapped-access üretmişti.

Koşullu aday penceresinde minimum MSP `2004FF08`, Main stack alt adresi
`200081D8`, Content `200099D8`; UI `200090B4`, Storage `200095B4`, IDLE
`2000B564`. Stock Main `200081F0`/MSP `2004FF20`; ek patch stack maliyeti
gözlemlenir. Canary korunur; bunlar tam/fiziksel maksimum stack değildir.

Recovery core832B ve seq ilk128B korunur. Reserved alanın tamamı aynı kalmaz:
native cold USB close accepted-TX journal PHASE/EP/CTRL/GEN alanlarını değiştirir
(başlangıca göre8 bayt). Native writer kayıtları probe'dadır; host yazısı değildir.

**Sonraki tek iş:** Content `2E8B4` owner `+3C` alanının üreticisini ve medya
bağlamını izlemek. Yanıtsız SDIO/zero-data QSPI altında stokta da aynı NULL
oluşur. Doğrulanmış medya girdisi/modeli olmadan firmware hatası diye yama yapma;
Main25864 ve son heap/stack ölçümü açık kalır. DSP-ready varsayımını koru.

## Testler ve yeniden üretim

6 yeni test: strict transactional ret, missing RX IRQ, masked IRQ, MINC0 dummy
sınırı, yanlış DMA ayarı ve native busy döngüsü.131 odaklı/102 packaged ve6
sınırlı Faz1 ölçütü PASS; sayılar örtüşür. Discovery620;tam620 koşulmadı.
Strict transport/CRC/vector/range/CFG/ABI PASS. Firmware hash'i hâlâ
`6b188671fa8b6cc765b618ffe01aabddb4a3b4c116389c26864ecccf842d3e19`.

Unicorn'un önceden çevrilmiş Thumb bloğunda değişen `emu_start(until)` adresi
atlanabildi. Requested checkpoint ayrıca CODE sınırında durdurulur; firmware
breakpoint komutu yazılmaz. Bu host runner düzeltmesi testlidir.

`.venv\Scripts\python.exe` (`-O` yok):

- `scripts/probe_recovery_spi.py logs/recovery-spi-20261030/probe`
- `-m unittest test_recovery_spi -v` (`PYTHONPATH=scripts;src;tests`)
- `scripts/audit_recovery_candidate.py logs/recovery-spi-20261030/audit`
- `scripts/verify_recovery_candidate.py logs/recovery-spi-20261030/packaged`

Probe/verifier exit2 NO-GO'yu korur. Exact diff,148 source pin ve öncesi/sonrası
aynı firmware `logs/recovery-spi-20261030` altındadır. [STATUS.md](STATUS.md).
