> Güncel29 Ekim (poll caller):2DE92 ek MSC çağrısının dispatch/adapter /
> callback zinciri ve owner/context kapıları13 yeni yerel/13 paket senaryosunda
> PASS. Worker/IRQ/recursive/factory/clock-stop ve kapanış arası sınırlar testli.
> Callback-only retry/power ilerlemez;native main hâlâ gerekir.53E78 yalnız BL
> kenarı testli,tam53E24 ve43E1C/Packs/RTOS ömrü açık.97 önceki kaynak ve
> firmware/codegen aynı.500 discovery;tüm500 bu oturumda koşulmadı.
> Üretim Off-Stop FAIL,M7 NO-GO. STATUS ve MIDI-USB-POLL-CALLERS-5706.md güncel.

---

# Bekleyen MIDI verisiyle native USB factory — 5706

Yalnız emülasyon kanıtıdır. Production builder'a yeni kod eklenmedi;M7 NO-GO.
Fiziksel MIDI/USB cihazı veya API'si kullanılmadı.

## Doğrulanan geçiş

Önceki staging=True carry,stok native formatter'ın hazırladığı fakat HAL'e
henüz kabul edilmemiş MAIN baytlarını ve immutable owned kısmi SysEx cursor'unu
korur. Bu çalışma o veri varken native432A8 factory'yi çalıştırır:eski MIDI ve
MSC reader'ları tam disable/ACK/AHB/shared RX/TX flush bariyerinden geçer;
sonra native root/class list değişir. MAIN,slot ve RX ledger yerinde kalır.
Yeni host reset/address/configuration sonrası veri tam bir kez devam eder.

Native25870..25880 main,retry/power/factory/MSC ilerlemesini sağlar. Test dışarıdan
retry/factory service pump çağırmaz. Host olayları ve MMIO ACK/flush/completion /
UART drain açık model stimulus'udur. Native driver/formatter/HAL/IRQ/class/
descriptor/stop-start yürür;gerçek PHY/RTOS/timing veya alıcı ACK kanıtı değildir.

## Test matrisi

| Durum | Kanıt |
|---|---|
| Composite→MIDI-only | Normal/Sequencer,360B payload,MAIN64/cursor48 korunur;94B/2-interface |
| MIDI-only→composite |125B/3-interface;sonra gerçek READ/backend worker/data/CSW |
| Ledger borcu |8 pending+1 owed reply;committed Clock/Stop replay olmaz |
| Staged Note Off |Borrowed SysEx olmadan4B event kayıp/tekrar olmadan çıkar |
| Eski MSC READ |Reader iptali class-list mutation'dan önce biter |
| Eksik ACK |Eski root listesi ve MAIN/cursor değişmez |
| Yeni istek/reset IRQ |Native rebuild içindeki yeni generation kaybolmaz;eski config açılmaz |
|101/201/301 tekrar |Enumeration öncesi cursor geriye alınmaz |
| Native caller'lar |35814 settings bit17 ve2CB18 boot wrapper gerçek stok kodudur |
| Accepted MIDI TX |Unsent sayılmaz;strict bekleme negatifi korunur |
| Staging varyantı yok |Native flush kaybı ve ilerlemeyen factory negatifi yeniden üretilir |

35814 view/store'u sentetiktir;3FC58 slot2 bit17=0 için1,bit17=1 için101 seçer.
Bu,Tam Packs UI/proje işlemleri veya her callback'in gerçek erişilebilirliğini
kanıtlamaz. Yeni testlerde yalnız bu dar callback ve iki dalı yürütülür.

## Değişiklik ve doğrulama

Önceki93 kaynak,default/staging/factory codegen ve production firmware hash'leri
aynıdır. Yeni source code/tests yalnız test helper'ı,13 senaryo,native trace ve
packaged probe'dur. İkinci yarış enjeksiyonu71100'de ayrı256B sıfır test alanını
assert eder;ilk71000 alanı değiştirilmez. App bounds/overlap/cache ve full-flash
snapshot kontrolü vardır. Instrumentation release patch'i değildir.

13 yerel ve13 packaged test PASS. Önceki474 tam takım PASS logu ve değişmeyen
kaynak hash'leri referans alınır;487 discovery toplamıdır,bu oturumda tam487
koşu yapılmadı. Audit/baseline/production87 regresyon/6 sınırlı kriter PASS;
üretim Off/Stop FAIL,NO-GO. Staging1680B/128B state/toplam2712B synthetic RAM,
carry3 maskeli bölüm/max30 komut ve yerel SP0/BL8 audit'i aynıdır. Tam stack /
RTOS/IRQ latency veya checked production RAM/init kanıtı değildir.

Loglar:logs/usb-factory-debt-20261029. probe/report.json tam USB stream SHA ve
iki DIN byte sayısını kaydeder. session.diff,hashes.json ve emulator range
manifest'i byte/SHA/MPEG-2 CRC/vector kanıtıdır;flashable yeni SYX değildir.

## Kalan sınır

Sonraki somut iş2DE92→27624 event callback'inin çağıran/owner ve yeniden giriş
grafiği.53E78 diğer poll caller'ı,tam Packs UI/proje akışı,accepted TX/raw ALT /
partial parser/held input/fault recovery,full boot/RTOS/OOM/2712B RAM-init,
gerçek PHY/flash/UART timing,storage partial-read/live-pattern alias,DIN input
ve production integration açıktır. Production Note Off/Stop kaybı sürer.
