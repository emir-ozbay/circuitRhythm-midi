# 5706 TX taşma hatasında mod geçişini kilitle

27 Ekim 2026 (test logları UTC26 Ekim21:11). Cihaz/MIDI/USB erişimi yok.
**Karar: NO-GO.** Mesaj teslimi onarılmadı; bilinen FIFO kaybından sonra
mod geçişinin açık kalması düzeltildi. Native USB/DIN formatter kanıtı genişledi.

## Karşı deney ve yeni koruma

Önceki adayda FIFO Note Off'u düşürdükten ve kuyruk boşaldıktan sonra controller,
transport ve input receiver guard'ları idle gördüğü için0->1 ve1->0 mode geçişi
kabul ediliyordu. logs/tx-fault-before.txt iki karşı örneği saklar. Bu deney
çıktı adaptörüne verilen notaları kullanır; fiziksel veya tam sequencer grafiği
kanıtı değildir. Bu tur test modülündeki ilk sınıf import'u ayrıca8 testi
tekrar keşfettiriyordu; module alias kullanılarak gereksiz tekrar kaldırıldı.

Yeni40228 hook'u yalnız401FE'nin FIFO enqueue başarısızlığı dalında çalışır.
Özgün e3f732fa, ITEEE NE bloğunun son BLEQ23690 çağrısıdır. IT prefix'i
11bf012400241748 hem stok hem adayda ayrıca doğrulanır. Başarılı enqueue ve
bağlı/configured olmayan portun ready0 dönüşü bu hook'a girmez.

Cave c_midi_tx_overflow32 bayt frame ile r0-r5,r12,lr saklar; APSR'ı r4'e
alır; c_seq_state ile heap/state geçerliliğini kontrol eder. Geçerli state'te
yalnız+7A OFF_MIDI_TX_FAULT=1 yazar. Sonra APSR_NZCVQG ve register'lar geri
getirilir; değiştirilmemiş23690 no-op'una bir kez tail-call yapılır. Stack
delta0, c_seq_state BL anında8 bayt hizalama ve özgün PRIMASK korunur. Yeni IRQ
kapama döngüsü eklenmez; c_seq_state'in mevcut kısa kritik bölgesi kullanılır.
Eski256 bayt state rezervasyonu büyümez; check_layout yeni baytı da denetler.
Code cave içinde flash kontrolcüsü/option-byte veya dosya API'si eklenmez.

c_midi_inputs_idle bu sticky baytı da kontrol eder. Kuyruğun boşalması veya
sonradan başarılı bir Off gönderilmesi baytı temizlemez. Normal state ömründe
mod geçişi kapalı kalır; yeni boot'taki state initialization sıfırlar. Bu,
harici alıcıdaki asılı notayı temizleyen recovery değildir. Fiziksel reset veya
yeniden yükleme önerisi değildir; aday donanıma hazır değildir.

## Native driver kanıtı ve düzeltilen varsayımlar

scripts/native_midi_driver_test_support.py artık gerçek:

- USB2B3AC parent,2B40864 bayt staging ctor ve2B460/498/4B2/4D8 yöntemleri;
  endpoint26880 submit ve268D0 availability-release yardımcı yolu.
- DIN2B534 parent,2B564 formatter;2B578 running status,2B5CA boş-alan/full;
  gerçek26014 UART byte ring yazımı ve2A470 ring tüketimi.

Yalnız2C9B8 low-level USB gönderimi ve2AC58 UART IRQ-enable emülatör sınır
stub'larıdır. UART ring buffer'ları sentetiktir. USB completion bildirimi
native268D0 yardımcı yoluna enjekte edilir; gerçek IRQ dispatcher/completion
bağlantısı veya DMA/wire zamanı doğrulanmış değildir. Sonuçlar gerçek cihazdan
alınmış ölçüm olarak yorumlanamaz.

Native USB full, sahte full byte'ı yerine64 bayt staging kapasitesi ve endpoint
available+1C'den türetilir. In-flight buffer, availability iade edilene kadar
değişmez; sonra sıradaki FIFO mesajları yeni transferle devam eder. DIN kodu,
tekrarlanan Note On/Off status baytlarını bastırır; aradaki F8 status'u bozmaz.
Üretilen byte dizileri ve On/F8/Off sırası testlidir.

İlk native endpoint modelinde+1D capacity1 unutulmuştu.268D0 ->23CEA bu üst
sınır nedeniyle availability'yi artıramıyordu.26828 kurucusundaki+1C/+1D=1,1
eşleşmesiyle düzeltildi; firmware hatası sayılmadı. İlk başarısız deneme
logs/native-driver-tests-first.txt, düzelenler logs/native-driver-tests.txt.

Önceki notlardaki27624 için “genel olay pompası” adı yanlıştı. Fonksiyon,
2EF5A durumunu ve iki USB endpoint available byte'ını kontrol eder;268E2/26A02
ve2F014/2F04A USB hizmet yollarını çağırır. Genel RTOS/event dispatch kanıtı
değildir. Güncel scope adlandırması düzeltildi; eski loglar değiştirilmedi.

Native configured0 USB'de401CA yazılım kuyruğunu temizler; bu overflow dalı
değildir ve+7A kilidi set edilmez. Dolayısıyla koruma bütün bağlantı/teslimat
hatalarını algılıyor iddiası yoktur. Kaybolan mesajlara dair garanti hâlâ açık.

## Testler ve güvenlik kararı

4 yeni fault testi: iki modda kayıptan sonra kuyruk boşalsa da ret; başarılı/
disabled portta false positive olmaması; valid/invalid heap, iki PRIMASK ve
NZCVQ/GE kombinasyonlarında r0-r12/LR/APSR/SP stok no-op'uyla aynı; yalnız
state+7A byte yazısı ve raw169092 bayt korunumu.

4 native driver testi: USB frame/DIN running status; in-flight değişmezliği ve
availability sonrası FIFO drain; native USB stall'da gerçek Off kaybı +mode
kilidi; configured0 USB'de yanlış overflow fault oluşmaması.

Toplam144 unittest,78 packaged regresyon ve6 sınırlı host kriteri PASS.
Build, baseline ve bağımsız SysEx/MPEG-2 CRC/vector/diff/Capstone/CFG stack
audit PASS. Negatif probe'da Off delivery FAIL, mode_admission_after_loss
BLOCKED ve fault_latched=true. Stop ready-driver PASS/stalled-driver FAIL.
Verifier CRITICAL_RUNTIME_PROBE_FAILED / NO-GO ve exit2 verir.

Loglar logs/tx-guard-final-{build,all-tests,verify,baseline,audit}.txt,
logs/tx-guard-final-audit/; logs/tx-guard-{queue,task}-probe.json.
Paket raporu logs/phase1-verification-20261026T211547Z/report.json.

SysEx SHA256 3c793d96c3748afec722d647d5b6c9f982513d04b6f49e31601c648619f0ec7d
Image SHA256 38d2234f172789518dadd5f1239b47ac5a752a0b1ee4c6aa977fbaecf885d8bf
CRC53F96711; imaj371368 bayt;21 patch,1376 değişen bayt. Stok SHA256 pin'i,
vector/kimlik ilk512 bayt ve uygulama sınırları korunur. Çıkış çekirdeği,
bu doğrulanmış4 bayt diagnostic observer hook'u dışında stokla aynıdır.

GO için üç ana kapı sürer. Sonraki somut görev, gerçek sequencer Note On/Off
üreticilerinin eşzamanlı açık nota ve callback sırası sınırını çıkarmaktır;
güvenli deferred Off/Stop recovery politikası bu sınıra dayanmalıdır. IRQ/DMA,
tam boot/OOM/zaman bütçesi ve stok storage hata/recovery de açık. Yeni guard,
kayıp mesajı geri gönderen veya kendi başına GO sağlayan bir çözüm değildir.
