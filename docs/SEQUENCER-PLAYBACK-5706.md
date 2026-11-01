> Tarihsel sentetik fixture raporu.31 Ekim native reset/player/Play–Stop
> kanıtı için MIDI-RECOVERY-PLAYBACK-5706.md veSTATUS.md günceldir. Aşağıdaki
> eski negatif Stop/FIFO sonucu tek başına güncel3f979b70… adayının sonucu
> değildir. Native koşan player cursor'ı bit6'dır;edit/recorder bit0 ayrıdır.

---

# Gerçek pattern oynatıcı ve Stop patlaması — NO-GO

27 Ekim2026, yalnız dosya/disassembly ve sentetik RAM'de Unicorn. Fiziksel
cihaz/MIDI/USB erişimi yok. Firmware baytları bu çalışmada değişmedi.

**Yeni kritik bulgu:**64 açık player notası, gerçek Stop çağrısında64 Off
üretir ve arkasından gelen FC64-slot kuyruğa sığmaz. Aynı USB buffer içinde
bir F8 ve FC varsa yalnız63 Off teslim edilir; bir nota ve Stop kaybolur.
İki modda ve üç hazır çıkışta aynı sonuç alındı. Önceki USB buffer yield
koruması buffer içindeki bu senkron patlamayı ayıramaz.

## Bayt ve makine kodu kanıtı

Stok SHA256 pin'i11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf.
Yerel upstream drumpat.py player adreslerine işaret etti; bu bir başlangıç
ipucuydu. Aşağıdaki zincir, pin'li stoktan ayrıca Capstone ve Unicorn ile
doğrulandı; upstream RAM adresleri veya davranış iddiaları kanıt sayılmadı.

| Adres | Doğrulanan davranış |
|---|---|
|33124 /boot28BE4 /3C29E|Raw proje+2E4, track stride5140,count8 pattern span'i player+50'ye aktarılır; ek128 ofseti yoktur.|
|3C29E..3C3BC|Sekiz player factory döngüsü;3C376 ->4ADA4. Allocation150 bayt. Callback16+t ve12 modulation lane parametresi.|
|4ADA4..4AED8|player+50 step verisi,+54 çıkış callback'i;8 dört-bayt gate kaydı,+78 çift bağlı liste ve8/9 sentinelleri,+AB nota-slot haritası.|
|4AEEE /4AFBC|Mikroadım/probability/tie hazırlığı ve gerçek pattern/step okuması; byte0=0 için nota48; velocity byte3, gate byte1, tie byte6 bit0.|
|4B0D4 /4B170 /4B19E|Native On, süre kuyruğu, Off ve slot iadesi. Aynı nota tekrarında ve dokuzuncu farklı notada Off önce, yeni On sonra.|
|3B2A0 /4A8CC|Class0/1/2 callback'leri, üç iki-kaynak ownership filtresi, MIDI/sample/recorder çıkışlarının kurulumu.|
|54F30 /54FA8|Nota bazında iki kaynağı birleştiren gerçek filtreler; son sahip bırakıldığında Off.|
|3B7EC /3B8F0|Class0 player -> voice/filter ->32+t MIDI ve24+t sample dalları. Class0 Off ayrıca class2 haritasını kontrol eder.|
|3B270 /3B288 ->31F9C /31FC6|MIDI adaptörü iç notadan12 çıkarır; kanal eşlemesi ve üç port fanout/FIFO/worker gerçek kodla çalışır.|
|33EAE ->3FBEC ->55120 ->552F6 ->4AED8|Transport durdurulurken sekiz player senkron boşaltılır; sonra backend Stop ve32024 üzerinden FC üretilir.|

Adresler0x08000000 tabanlıdır. Disassembly:
logs/seq-player-{machine,queue,bindings}-stock.txt,
seq-voice-callback-stock.txt, seq-off-router-stock.txt,
seq-stop-lifecycle-stock.txt, seq-note-range-stock.txt.

## Emülasyon ve sınırları

scripts/sequencer_playback_test_support.py kuruculara göre sentetik player,
voice, callback ve store RAM'i kurar. Callback/ownership/list yardımcı
kurucuları gerçektir; tam player/root/boot kurucuları çalıştırılmaz. Son sample
engine çağrıları ve final driver hazır/full sınırları stub'dır. Stop backend'i
önceki transport fixture'ındaki stub'dır. Gerçek Stop'un store notify/player
boşaltma/FC sırası ve çıkış kuyrukları stub değildir. İki12-halfword modulation
buffer'ı da Stop sırasında native kodla sıfırlanır (FFFF).

Testler: iki mod, sekiz track, pattern0/7 ve step0/16/31, nota12/127 ve stok
default48; gerçek gate countdown; son track/pattern'de32 step'in tamamının
okunması; aynı pitch Off/On sırası; dokuzuncu nota için oldest-slot steal;
aynı pitch tie'da gereksiz retrigger olmaması;64 açık nota ve Stop sınırı.
Normalde sample On çağrılır, MIDI-only'de bastırılır; MIDI On/Off aynen kalır.
Player canary/ABI/SP ve Stop boyunca169092 bayt proje korunumu da denetlenir.

| Sentetik başlangıç ve gerçek Stop | Her portta Off | Her portta FC | Sonuç |
|---|---:|---:|---|
|63 player notası|63|1|PASS; fault0|
|64 player notası|64|0|FAIL; fault1|
|64 player notası; tek8-bayt USB buffer'da F8+FC|63|0|Off ve Stop FAIL; fault1|

On'lar gerçek4AEEE/4AFBC kodundan gelir; output.note() doğrudan çağrılmaz.
On aralarında output poll yapılıp kuyruk boşaltılır. Uzun gate96 ve manuel
step/tick çağrıları sentetik girdidir. Gerçek cihazın timer ilerlemesi, bütün
boot grafiği, bu64-nota durumunun canlı UI/timer ile erişilebilirliği ve IRQ
zamanlaması bu deneyle kanıtlanmış değildir. Kaybın Stop içindeki sırası ise
native kodla ve63-nota kontrolüyle ayrıştırılmıştır.

**Sekiz kayıt/player, bütün sistemde en fazla64 MIDI notası garantisi değildir.**
UI/preview kaynakları ve bütün tie/microstep yollarının küresel sınırı açık.
Bu bulgu polyphony eklemez; stokta çalışan yolları ortaya çıkarır.

İlk fixture denemesinde class0 Off'un kontrol ettiği class2 map pointer'ları
eksikti;3BB14 null okuması oluştu. Ayrıca transport store'larının altındaki
stack boşluğuna25 ek store sığmıyordu. Ayrı sentetik RAM ve tüm boş class2
haritaları kurularak düzeltildi. Bunlar firmware hatası değildir. İlk loglar
seq-playback-tests-first.txt /seq-playback-model-debug.txt korunur.

Son çapraz kontrolde ilk fixture'daki gereksiz+128 pattern ofseti de bulundu.
ST1 cache alanı, ham adım başlangıcıyla karıştırılmıştı.33124 gerçek span
kurucusu ve3C29E argüman akışıyla düzeltildi;32-step testi ayrıca ham dosya
düzenindeki ilk/son tuple'ı bağımsız okur. Önceki loglar
seq-playback-pre-span-correction-* adlarıyla korunur; güncel sonuçlar düzelen
modelle yeniden üretildi. Bu model hatası da firmware hatası sayılmadı.

## Recovery için somut tasarım sınırı

Yalnız FIFO büyütmek veya USB poll sıklığını artırmak, süresiz driver stall'ı
ve hazır sürücüdeki Stop patlamasını birlikte çözmez. Native player kendi
kaydını/ownership bitini Off teslim edilmeden boşaltır; sonra player listesine
bakarak kayıp Off'u yeniden üretmek mümkün değildir.

Sonraki prototip, **port başına channel/note anahtarlı deferred Off bitmap'i
ve ayrı pending Stop** tutmalı.16 kanal*128 nota =256 bayt/port; üç port için
yalnız bitmap768 bayt. Bu, mevcut256-bayt state içindeki boş alanı aşar.
Ek heap rezervasyonu için tam boot/OOM ve atomik initialization kanıtı gerekir;
adres/boyut henüz üretim koduna eklenmedi.

Kuyruk kabul edene kadar Off biti silinmemeli; Stop bütün önceki Off'lardan
sonra gönderilmeli. Pending Off varken yeni On'un aynı anahtarı tekrar açması
ve Clock'un boşalan slotları tüketmesi için açık bir kabul/karantina politikası
gerekir. Kritik bölüm yalnız kısa bitmap/state güncellemesi yapmalı; USB/UART
I/O veya kuyruk taraması IRQ kapalı yürütülmemeli. Port pointer ömrü, disconnect
ve reset politikası ayrıca doğrulanmalı. CC120/123 broadcast'i teslim garantisi
yerine kullanılmamalı. Bu paragraf tasarımdır; uygulanmış recovery değildir.

Tek sonraki görev: bu ledger'ın sınırlı bir prototipini gerçek native FIFO ve
hazır/stalled USB/DIN fixture'larında sınamak;63/64 ve F8+FC karşı deneylerini
teslim kaybı olmadan geçirmek, ABI/heap/zaman sınırlarını kanıtladıktan sonra
üretim hook'u hazırlamak. Yeni hata giderildi denmeyecek; aday hâlâ NO-GO.
