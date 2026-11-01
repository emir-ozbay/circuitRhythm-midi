# Native giriş örnekleme kapısı — 5706

30 Ekim 2026. **M7 NO-GO.** Firmware ve üretim kaynakları değişmedi.
Cihaza veya fiziksel MIDI/USB API'sine erişilmedi.

## Kapanan iş ve kanıt türü

Exact SYX reset/main/port/worker modeli üzerinden yürür. Native `26596`
gerçekten1 döner ve Main'in koşullu dalı `2582E` adresine geçer. Üç örnek
sayacı `0/0/0 → 2/2/2` olur. Sayaçlara, completion RAM'ine veya R0 hazır
sonucuna host tarafından değer verilmez; firmware komutu değiştirilmez.

| Kanıt türü | Yapılan iş ve sınırı |
| --- | --- |
| Bayt/disassembly | Vektör72, `646E8 → 27762`, `265BA`, sampler güncellemeleri ve `26596` kontrolü exact image üzerinden okunur. |
| Çevre birimi modeli | Native DMA2 stream0 CR=`52C15` (CT hariç), NDTR=96, PAR=`40012308`, iki halfword tamponu. CT/TCIF0 ve native LIFCR W1C modellenir. |
| Sentetik giriş | Sabit ADC2048 ve native literal `1FF0F44A` için salt okunur calibration1500. Bunlar cihazdan ölçülmedi; gerçek pad/knob veya kalibrasyon doğruluğu iddiası yoktur. |
| Native yürütme | IRQ örnekleri kopyalar ve pending yayımlar; Main tüketicisi filtre/ortalama fazlarını ve sayaçları ilerletir. |
| Fiziksel test | Yapılmadı. ADC zamanı, DMA bus yarışları, tam NVIC/nesting/FPU ve fiziksel maksimum stack kanıtı değildir. |

Native stream0 tamponları `20000488` ve `20000548` olur. Model yalnız bu
192B DMA hedeflerine örnek yazar. `20000334` bir embedded driver'dır;
`+4` alanı raw input context `200003C4` adresidir. IRQ `646E8`, native
`27762` üzerinden tamamlanmış tamponu raw context `+4` alanına kopyalar;
`+244` tampon seçimini değiştirir, `+2` pending baytını native kod artırır.

Main `265BA` raw pending'i tüketir. Readiness root'u ayrı `20000834`
adresidir. `2000AA08`, `2000AA78`, `2000AF80` nesnelerinin `+2A` sayaçları
native sampler yollarında artar. En yavaş32 örnekli pencere iki kez
tamamlanınca üçü hazırdır:64 aktarım/64 IRQ/65 readiness kontrolü.

ADC IRQ adaptörü temel PSP frame'ini kurar; native C gövdesini MSP üzerinde
exception72 bağlamında çalıştırır. R4–R11, MSP ve frame kontrol edilir;
CPU context'ini host geri yükler. Mimari BX EXC_RETURN/NVIC arbitration
emüle edilmez. Diğer peripheral/worker model sınırları da geçerlidir.

## Ölçüm ve negatifler

- Stock ve adayın tahsis boyut/adres sırası, örnek hedefleri, sayaç geçişleri
  ve task stack alt adresleri aynı. Başarı dalında203 tahsis, heap `20010BEC`,
  320 PendSV geçişi ve önceki9/9 Storage completion korunur.
- Aday minimum MSP `2004FF08`; task alt adresleri Main `200085E8`, UI
  `200090B4`, Storage `200095B4`, Content `20009B74`, IDLE `2000B564`.
  Bunlar bu model/pencere ölçümüdür. Canary, reserved1088B ve tüm emüle
  instruction image korunur. Tam boot/son heap ölçümü değildir.
- DMA tamamlanıp IRQ teslim edilmezse raw pending ve sayaçlar sıfır kalır;
  Main hazır dalına geçmez. Native IRQ sonradan verilince pending yayımlanır.
- Tüketici çalışmadan64 IRQ verilirse pending1'de birleşir; sayaçlar0/0/0
  ve native hazır sonucu0 kalır. Tek tüketim de hazır olmak için yetmez.
- Maskeli IRQ teslim edilmez. Yanlış stream enable/count/PAR/hedef ayarı,
  herhangi bir örnek RAM yazısından önce reddedilir.

6 yeni test;125 odaklı/96 packaged test ve6 sınırlı Faz1 ölçütü PASS. Sayılar
örtüşür. Discovery614;tam614 koşulmadı. Önceki529/98 kayıtları korunur.
Strict transport/CRC/vector/range/CFG/ABI PASS; firmware hash'i hâlâ
`6b188671fa8b6cc765b618ffe01aabddb4a3b4c116389c26864ecccf842d3e19`.

## Sonraki somut sınır

Main25864'e henüz ulaşılmaz. İlk `2B66C` fonksiyon girişini bloklanma saymak
yanlıştı: ilk iki çağrı completion1 ile native döner. Probe bunları geçip
gerçek boş completion dalını `2B67A` adresinde bulur:

- Caller dönüşü `31101`, zincir `31110 → 310B0 → 46414 → 2B66C`.
- Driver `20000318`, SPI context `20000170`, `+2` completion baytı0.
- DMA1 stream3 RX: CR=`10015`, NDTR=30, PAR=`4000380C`, hedef `20000184`.
- DMA1 stream4 TX: CR=`10455`, NDTR=30, PAR=`4000380C`, kaynak `08031638`.
- RX memory increment kapalıdır;30B transferi30 ardışık RAM baytına yazmak
  model hatasıdır. Keşif prototipindeki bu hata firmware hatası sayılmadı.

**Sonraki tek iş:** Bu native SPI başlangıç aktarımının DMA1 stream3/4
completion ve yanıt sözleşmesini izlemek; completion/yanıtı zorlamadan
Main25864'e ilerlemek. Sıfır SPI yanıtı denemesi tam açılışı kanıtlamadı ve
canonical modele alınmadı. ADC kapısı kapandı.

## Yeniden üretim

`.venv\Scripts\python.exe` ile (`-O` yok):

- `scripts/probe_recovery_input.py logs/recovery-input-20261030/probe`
- `-m unittest test_recovery_input -v` (`PYTHONPATH=scripts;src;tests`)
- `scripts/audit_recovery_candidate.py logs/recovery-input-20261030/audit`
- `scripts/verify_recovery_candidate.py logs/recovery-input-20261030/packaged`

Probe/verifier exit2 NO-GO'yu korur. Exact diff,145 source pin, öncesi/
sonrası aynı firmware, çıktılar ve hash'ler `logs/recovery-input-20261030`
altındadır. Güncel karar/kalan kapsam: [STATUS.md](STATUS.md).
