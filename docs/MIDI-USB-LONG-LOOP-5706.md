> Güncel29 Ekim (native file queue):45EB6→sync FIFO/wait/2AD40 worker
> yolu8 yerel/8 paket testte PASS;4113A file API RAM sınırı kalır.
> Result credit'ten önce yayımlanır;reset/suspend/nested MSC reader testli.
> Yeni negatif:53E8C short-read hatasını kullanmayıp2046B artık veri yazabilir.
> Fiziksel tekrar/stock patch yok;105 eski kaynak ve firmware aynı.
>518 discovery,tam518 bu oturumda koşulmadı. M7 NO-GO;STATUS ve
> MIDI-USB-FILE-QUEUE-5706.md güncel.

---

# Stok5706 —128-yuva örnek yükleme döngüsü

29 Ekim 2026. Bounded native kod + sentetik RAM emülasyonu;M7 NO-GO.

53E24,pack seçimi başarılıysa sample manager'ın+10 metodunu ve progress
observer'ın0/C/8 metodlarını çağırır;128 turda progress(n,128),watchdog,
53E8C(n),27624 sırasını yürütür. Son progress+10 ile1 döner. Eksik/geçersiz
örnek başlıkları da loop başarısını0 yapmaz;üst seviye dönüş içerik kanıtı değildir.

53E8C,4603A wrapper'ıyla type4/slot/packFE descriptor'ı için64B header okur.
Native WAV kontrolü48kHz,mono,16bit koşullarını sınar. Geçerli dosyada
iki2KB tamponu değiştirir,her seferinde1024 halfword REV16 yapar,istenen
gerçek byte sayısını sample-flash write API'sine verir. Test512B ve4608B
örneklerle512/2048/2048/512B çıktıyı byte-byte karşılaştırır. Kısmi son
chunk dışındaki RAM'in byte-swap edilmesi,boundary modelinde ayrılmış tam
2KB içinde kalır. Dosya hatası/short-read davranışı bu kanıtın dışında.

| Binding | Adres / kanıt sınırı |
| --- | --- |
| Progress observer |20000A8C,sentetik vtable |
| Sample manager |20006F24 pointer,sentetik allocator/vtable |
| Header |20006AD8..20006B18 |
| Sample scratch |20003F94..20004F94,iki2048B tampon |
| Media semaphore |20003F8C,native2EF6A/2EF98;2EF5A readiness |
| MSC READ buffer |40024000..40025000,mevcut pinned READ overlay'i |
| Fixture MIDI nesneleri |4B00..5000→E000..E500 (yalnız test) |
| CPU stimulus sonuçları |E580;sample tamponunun dışında |

27624,2EF5A ile media semaphore presence kontrol eder;dönen3F94 pointer'ını
yalnız nonzero kontrolü için kullanır. Semafor native acquire ile tutulunca
128 poll READ'i başlatamaz;native release ve main sonrası tamamlanır.
READ overlay'i ayrıca buffer40024000'a sabitlidir. Bu okuma senaryosundaki
ayrıklık,diğer file/MSC işlemleri veya gerçek flash ownership için genellenmez.

Gerçek stok53E24/53E8C/4603A/WAV/watchdog/MSC/SCSI/queued worker/HAL/IRQ
çalışır.45EB6 hemen RAM dosyası kopyalayan bir code-hook sınırıdır;sample
flash API'leri RAM write kaydı üretir;loglama modellenir. Full file task,
native allocator,UI callback ömrü,pack mount/IO errors,flash arbitration ve
RTOS/hardware timing açık. Özel SD dosya sistemi eklenmedi.

10 senaryo:iki modda128 eksik örnek;geçerli çokchunk/kısmi örnek ve proje
RAM;iki modda main'siz READ/data/CSW;aktif data TX buffer ömrü;semaphore;
worker içinden full loop;suspend;reset sonrası yeni READ;MIDI retry negatif;
packFF erken dönüş. Harici bus olayları slot checkpoint'inde yürütülür,
loader CPU ve yardımcı fixed-stack çakışmasına karşı stack korunur.

İlk fixture denemelerinin stack,izleme kenarı ve sentetik yerleşim hataları
STATUS'ta kayıtlıdır. Özellikle4B00 vtable'larının native sample buffer ile
çakışması stock/prototype alias bug'ı sayılmadı. Production RAM planı değişmedi.

Bu uzun loop,MIDI retry/power coordinator'ını çağırmaz.128 poll sonrasında
debt/pending sleep kalır;main yeniden erişince tamamlanır. Üst seviye
main erişimi/backpressure çözülmedi;full-service patch eklenmedi.

Kanıt:logs/usb-long-loop-20261029/{final-tests.txt,probe/report.json,
probe/tests.txt,probe/stock-contract/long-loop-contract.json,
emulator-range-manifest.json,hashes.json,session.diff}. Yerel10 ve paket10
PASS. Previous full474+13factory+13caller aynı101 kaynakla korunur;510
discovery için bu oturumda tam suite yok. Production SYX aynı,Off/Stop FAIL.
Sonraki iş45EB6→2ACA2 native file queue/worker/buffer ownership emülasyonu.
