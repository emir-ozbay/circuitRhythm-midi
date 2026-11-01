# 5706 USB giriş turu sınırı ve Stop kaybı düzeltmesi

Güncelleme27 Ekim: [MIDI-TX-FAULT-5706.md](MIDI-TX-FAULT-5706.md), TX loss
sonrası mode kilidini ve native driver kanıtını ekler.144/78 PASS; recovery açık,
NO-GO. Düzeltme: aşağıdaki27624 “event pump” adı hatalıydı; USB endpoint service
yapar. Eski sonuçlar ve hash bu alt çalışmanın adayı içindir.

26 Ekim 2026. Capstone/Unicorn, fiziksel cihaz veya port erişimi yok.
**Karar NO-GO.** Hazır çıkış sürücüsüyle USB burst kaynaklı Stop kaybı bu adayda
düzeltildi; uzun süre full kalan sürücü ve dolu kuyrukta Off teslimi çözülmedi.

## Gerçek görev sırası ve karşı deney

25870..2587C gerçek ana döngü talimatları önce297DE çıkış worker poll'unu,
sonra29ABC USB/DIN giriş poll'unu çağırır. Sonraki27624 event pump bu emülasyon
aralığının dışındadır.29ABC önce29AC8 USB, sonra29BDA DIN işini yapar.

DIN29BDA her porttan tur başına en fazla1 bayt alır; FIFO'yu aynı turda sonuna
kadar boşaltmaz. USB29AC8 ise stokta bir portun bütün alım FIFO'sunu tüketip
sonra sonraki porta geçer.666A6..666B6 endpoint1 kurucusu64 bayt paket boyutu,
16 alım slotu verir;26828/2C71C ring kapasitesi16*(64+2)+1=1057 bayttır.
Dolayısıyla64 Clock + Stop içeren5 alım paketi bu tampon sınırlarına sığar.

Yeni model bu alım header/kapasitesini sentetik RAM'de kurar ve25870..2587C
talimatlarını değiştirmeden çalıştırır. Final driver/timer/tempo/GPIO sınırları
önceki fixture'daki gibi kontrollüdür. Başlangıç Start/ilk Clock tesliminden
sonra USB'ye64 Clock + Stop biriktirilir; çıktı aşağıdadır:

| Durum | Clock/port | Stop/port | Ölçülen tepe TX doluluğu |
|---|---:|---:|---:|
| Yeni hook stok4 baytına döndürülmüş kontrol |64 |0 |64 |
| Yeni aday, hazır sürücü |64 |1 |16 |
| Yeni aday,5 tur full bırakılan sürücü |64 |0 |64 |

Bu, önceki yalnız elle sıralanan Clock deneyini gerçek main-poll sırasına
bağlar. Tüm RTOS/IRQ/DMA grafiği veya donanım zamanlaması doğrulanmış değildir.
Başlangıç clock-present flags girdisi ve alıcı/sürücü nesneleri sentetiktir.

## Küçük makine kodu düzeltmesi

29B62'deki `cfda4068` (BGE29B04; LDR r0,[r0,#4]) doğrulanıp4 bayt B.W hook
ile değiştirilir. Cave helper c_usb_rx_yield12 bayttır:

```text
0806AA74  bge  0806AA7C
0806AA76  ldr  r0,[r0,#4]
0806AA78  b.w  08029B66
0806AA7C  b.w  08029AF2
```

29B60'ın CMP r5,r1 bayrakları kullanılır. Paket işlenmesi bitmediyse çalınan
LDR aynen yürür. Bitmişse stokta aynı porttan yeni RX buffer almak yerine
29AF2'deki sonraki-port yoluna geçilir. Her portta her turda en fazla1 alınmış
buffer işlenir; o buffer'ın tüm baytları işlenir. Diğer RX buffer'ları FIFO'da
kalır. Böylece bir sonraki buffer'dan önce ana döngü çıkış worker'ına ve diğer
görevlere dönebilir. Stok rearm mekanizmasına erişim sonraki poll'larla sürer;
bu çalışmada fiziksel rearm/DMA zamanlaması çalıştırılmaz.

Bu kodda BL, push/pop, RAM store veya flag değiştiren talimat yoktur.
SP delta0; LR ve register'lar korunur; yalnız LT yolundaki özgün LDR r0'ı yazar.
Heap/state rezervasyonu değişmez, PRIMASK'e dokunulmaz. Yeni çağrı, callback,
flash-controller/option-byte adresi veya dosya erişimi yoktur. İki modda etkilidir.
Literal okuması eklenmez. Her iki Thumb hedefi geçerli stok komut başlangıcıdır.
Bağımsız Capstone/yerel CFG raporu bunu doğrular; exit SP delta[0], local stack0.

## Testler, başarısız varsayımlar ve sınırlamalar

Yeni tests/test_midi_task_schedule.py içindeki8 test:

- Yalnız yeni hook'u stok baytına çeviren kontrol ile orijinal Stop kaybı korunur.
- İki modda64 Clock + Stop kayıpsız, RX'de bekleyen mesajlar kaybolmaz.
- Tam16 RX buffer'ında255 Clock + Stop kayıpsız teslim edilir.
-63 Clock + Stop ve ana döngünün callee-saved/SP korunumu.
- LT/GE branch'lerinde r0-r12, LR, SP, APSR ve PRIMASK stokla eşittir;
  hook yolu RAM'e hiç yazmaz.
- DIN her turda port başına1 bayt tüketir;64 Clock sırayla teslim edilir.
- İki buffer'a bölünmüş96 bayt SysEx, yalnız tamamlanınca tek callback üretir;
  sonraki Note On/Off parser/receiver sahipliğini doğru kapatır. Final SysEx
  consumer stub'dır; dosya veya proje komutu çalıştırılmaz.
- Sürücü full tutulduğunda Stop kaybı hâlâ üretilir; çözüldüğü iddia edilmez.

İlk iki yeni test stokun tek turda bütün RX'i bitirmesini bekliyordu. Hook
sonrasında Stop'un sonraki turda kalması beklenen davranıştır; stok kontrolü
saklanıp adayın çok turlu teslim beklentisi eklendi. logs/task-schedule-before.txt
stok kaybını, logs/task-yield-first.txt bu ara beklenti farkını korur.
Görevler arasındaki gerçek süre ve ek giriş gecikmesi ölçülmedi. Paket başına
16 USB-MIDI frame sınırı, bütün sequencer callback'lerinin ürettiği toplam
çıkış olayına genel16 sınırı anlamına gelmez. Bütün boot listener grafiği,
sequencer adım üreticisi, timer/IRQ, port ready/full ömrü hâlâ açıktır.

## Güncel paket ve kalan işler

.venv/Scripts/python.exe ile optimizasyonsuz build,136 unittest,70 packaged
regresyon ve6 sınırlı host ölçütü PASS. Baseline ve bağımsız SysEx/MPEG-2 CRC,
vector/diff/Capstone/CFG stack audit PASS. Ayrı task probe'da ready-driver PASS,
stalled-driver FAIL; önceki dolu FIFO Off probe'u da FAIL. Verifier exit2,
CRITICAL_RUNTIME_PROBE_FAILED / NO-GO verir; genel güvenlik kabulü yoktur.

Loglar logs/usb-yield-final-{build,all-tests,verify,baseline,audit}.txt,
logs/usb-yield-final-audit/; ayrı probe'lar logs/usb-yield-{task,queue}-probe.json.
Paket raporu logs/phase1-verification-20261026T205106Z/report.json.

SysEx SHA256 0fa75262c3cf580fa1e9d4f88431d013dddb2fffc8edb1baeb0caa5c28c2d6b9
Image SHA256 c15efacf589b1ea381fa5f96e7236cca0119c1e1587d93ff81482f69d5c3940f
CRC93CA2E51; imaj371332 bayt;20 patch,1335 değişen bayt. Stok pin ve ilk512
bayt vector/kimlik aynıdır; uygulama sınırları korunur.

Sonraki tek görev: gerçek port driver ready/full/flush yaşam döngüsünü ve
27624 event pump sırasını bağlayarak consumer stall sınırını veya güvenli
Note Off/Stop recovery politikasını doğrulamak. Diğer iki GO kapısı stok storage
hata/recovery ile tam boot/OOM/PRIMASK zaman bütçesidir. Bu aday yüklenmemeli.
