# Yardımcı işlemci durum alanı — 5706

30 Ekim 2026. M7 NO-GO. Firmware, stock ve fiziksel cihaz değişmedi.
Bu kayıt yerel ARM yürütmesi ile açık dış işlemci test girdilerini ayırır.

## Native sözleşme

`314D6`, bank R0 /18-bit adres R1 için `88..8B` selector ve `400000`
sorgusu gönderir. Üç MISO baytı native `46510` dönüşünde üst24 bite yerleşir:
`000001` wire yanıtı R0=`00000100` olur. CPU dönüşü host tarafından yazılmaz.

İlk tüketici `6439E` değil, `6441E`/dönüş `64422`'dir. `64416` fonksiyonu:

| İşlem | Adres /davranış |
| --- | --- |
| Ön bekleme |`37300` nonzero iken tekrar oku;`3172E` yield |
| Komut |`372FB` adresine native `31228` ile R1=`100` yaz;wire `000001` |
| İlk komut sorgusu |`372FB` oku |
| Nonzero ise sonraki sorgular |R5=`37300` kaldığı için `37300` oku |
| Zero olduğunda |`6455C` pop ile çağırana dön |

İlk script denemesi komutun sonraki sorgularını da `372FB` bekledi;native
`37300` sorgusu bunu reddetti. Loop firmware'de değiştirilmedi. Bu adres
değişiminin gerçek DSP için doğru/yanlış olduğu kanıtlanmış değildir.

Literal adresleri ARM PC hizalamasıyla çözüldü: `64588=37300`,
`6458C=372FB`. `6438C`'deki128 yuvalı uzunluk sorgusunun tabanı ise
`64574=30001`;adres `30001+4*slot` olur. İlk okumanın uzunluk tablosu olduğu
ön yorumu bu yüzden reddedildi.

İlk kullanılan bellek yanıtından önce516 MCU RAM-word yazımı vardır;
`37300` bunların arasında değildir. Byte-stream/register yazımları ayrı
tutulur. Dört native program indirme girdisinin header/count/hash kayıtları
`uploads.json`'dadır. Bunlar yardımcı işlemcide yürütülmedi;yüklenmiş program
baytları bu RAM alanına sıfır yanıtı verme kanıtı sayılmaz.

## Sınırlı dış girdi modeli

`scripts/recovery_dsp_test_support.py`, varsayılan SPI modelini değiştirmeyen
ayrı bir `DSPStartup` katmanıdır. Peer verilmezse ilk kullanılan DSP bellek
yanıtı yine RAM/DMA/TC değişikliğinden önce reddedilir.

`ScriptedDSPPeer` yalnız sonlu, sıralı `(bank,address,value)` girdilerini kabul
eder. Varsayılan sıfır, sınırsız RAM veya otomatik komut temizleme yoktur.
Komut yanıtı gerekli native RAM yazımının tamamlanmış wire değerine bağlanır.
Native `31228` girişindeki argümanlar selector/veri paketiyle karşılaştırılır;
peer yazım kaydı ancak DMA verisi taşındıktan sonra oluşur. Yanlış bank/adres,
eksik/farklı komut, tükenmiş liste ve reset öncesi kayıt yanıt sağlamaz.

Bu turdaki açık senaryo altı yanıttır:

1. `37300`: `000001`, `000001`, `000000`.
2. Native `372FB←000001` tamamlanır.
3. `372FB`: `000001`.
4. `37300`: `000001`, `000000`.

Bu değerler test girdisidir;gerçek DSP'nin reset/komut davranışından elde
edilmiş değildir. Native karşılaştırmalar, döngüler, yield, SPI DMA/IRQ ve
çağırana dönüş ARM emülasyonunda yürür. Böylece hep hazır yanıtıyla polling
yolu atlanmaz. IRQ/NVIC/FPU/gerçek zaman, medya uyumu ve fiziksel DSP kanıtı
oluşmaz. Önceki ADC, sentetik NOR,802B-ready ve unattached USB ACK sınırları
aynen sürer.

Uzatılmış koşu `803C03A` adresindeki `VPUSH {d8}` komutuna ulaşır. Mevcut
`BasicFrameOnly` koruması bunu çalıştırmadan reddeder. Native PendSV aslında
EXC_RETURN bit4'e göre `25C22 VSTMDBEQ {s16-s31}` ve `25C5E VLDMIAEQ`
yollarını içerir. Host adaptörü ise yalnız basic frame ve9 kayıtlı word
bekler;bu yüzden FPU komutunu atlamak veya korumayı kapatmak geçerli değildir.
Sonraki iş bu iki frame türünün, FP register/FPSCR ve IRQ/task bağlamlarının
yerel korunmasını modelleyip test etmektir. Tam Main25864 hâlâ kanıtlanmadı.

`empty_sample_lengths()` ayrıca128 sıfır uzunluğunu sonlu girdi olarak
tanımlar;gerçek DSP başlangıcı olduğunu ileri sürmez. Native mailbox testi
ve kanonik probe bu girdiyi kullanmaz. Keşif koşusunda da listeye eklenen
uzunluk girdilerinin hiçbiri tüketilmedi.

## Yeniden üretim ve kanıt

`.venv\Scripts\python.exe` kullanılır;`-O` kullanılmaz.

- `scripts/probe_recovery_dsp.py logs/recovery-dsp-20261030/probe`
- `scripts/verify_recovery_candidate.py logs/recovery-dsp-20261030/packaged`
- `scripts/audit_recovery_candidate.py logs/recovery-dsp-20261030/audit`

Probe/verifier NO-GO nedeniyle exit2 döner. Önce strict duruş ve tekrarlanan
başarısız aktarımın RAM/MMIO atomikliği ölçülür;sonra açık altı girdi eklenir.
Uzatılmış yürütmede komut dönüşü sonrası talimat bütçesi ve gerçek PC ayrıca
kaydedilir. Talimat bütçesinin bitmesi yeni bir firmware hatası sayılmaz.

Kaynak/hash/diff ve çalışma sonuçları `logs/recovery-dsp-20261030` altındadır.
Son sayımlar ve tek sonraki görev için `STATUS.md` önceliklidir.
