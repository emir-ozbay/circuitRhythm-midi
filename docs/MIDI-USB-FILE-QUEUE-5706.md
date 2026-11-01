# Stok5706 — Senkron dosya kuyruğu

29 Ekim 2026. Native byte/disassembly + sentetik RAM emülasyonu;M7 NO-GO.

Sample loader53E8C,4603A ile op6 read ister.45EB6 callback0 olduğunda
2ACA2'ye senkron gider;worker+C'yi temizler,2ACB8/40DC4 ile72B packet'ı
FIFO'ya kopyalar. Paket içinde key(type4/slot/packFE),offset,dest,length ve
callback/count pointer alanları bulunur. Kaynak stack descriptor'ının
byte'ları worker'da40DEE ile alınan kopyayla birebir karşılaştırılır.

2CA6C,worker+10 credit'ini2→1 azaltır;2ACF8 native2508C/25056 ile TCB
TLS0'ı okur. Caller worker değilse2AD12 yield/credit2 beklenir. Test
71300 cave'inde register/APSR/TLS korunarak native2AD40 çalıştırılır.
Bu explicit task-switch sınırıdır;tam scheduler veya gerçek task-stack
switch kanıtı değildir. FIFO constructor/ring allocation,enqueue/dequeue,
byte semaphore ve worker'ın tamamı native kalır.

Worker op6,4113A read API'sini çağırır. Sonuç2B00C'de worker+C'ye yazılır,
sonra exclusive byte credit serbest bırakılır;2ACA2 sonucu döndürür.
Native4603A wrapper'ın3 hata döndürdüğü doğrudan testlidir. Sync callback0
yolu result FIFO'ya gitmez;async Save result/callback yolu ayrı kanıttır.

| Katman | Durum |
| --- | --- |
|53E24/53E8C/WAV/watchdog |Native,önceki UI/allocator/sample-flash modelleriyle |
|4603A/45EB6/2ACA2/2ACB8/2ACF8 |Native |
|40D9C FIFO ctor/ring/40DC4/40DEE |Native |
|2AD40 op6/status/credit |Native |
|2508C/25056/2CA6C/23CEA |Native,TCB binding'i sentetik |
|2AD12 yield |Checked71300 cave,native worker çalıştıran task-switch modeli |
|4113A |RAM file read/status/count sınırı;short-read zero-fill yok |
|Mount/open/seek/read/close/lower media |Henüz native graph'a alınmadı |

Worker/TCB objeleri22000000..22003000 test arena'sındadır. Native request
FIFO ring'i mevcut checked allocator'dan ayrılır;proje RAM snapshot'ı
korunur. Current-TCB20006550 sentetik bağlanır;gerçek boot/production RAM
rezervasyonu değildir. Önceki MIDI fixture E000 rebind'i korunur.

8 senaryo:iki modda128 missing-file read;iki4608B örnekte FIFO wrap /
2048+2048+512B double buffer;loop'ta MSC READ/data/CSW;MSC worker içinde
file worker;file worker'ın read BL kenarında reset+nested main;aynı kenarda
suspend+retained MIDI debt;native sync hata sonucu;short-read negatifi.
Reset örneğinde yalnız eski MSC TX vardır,aktif MSC worker/drain yoktur;
coordinator0 döndürüp çalışabilir. Request copy/credit yine native worker
tamamlanana kadar korunur. Bu,lower media arbitration kanıtı değildir.

Yeni negatif:ikinci2048B read,4 status/count2 ile yalnız2B yazar;53E8C
sonucu kontrol etmez ve2048B sample-flash write çağırır. Önceden A5 olan
2046B artık veri yazılır. Bu native kontrol akışı ve sentetik API hatası
kanıtıdır;gerçek kart/cihaz arızası tekrarı yoktur. Önceki immediate-copy
fixture'ın zero-fill'i bu riski gizliyordu;bu fixture short-read'i korur.
Stock örnek yüklemesini değiştiren firmware/prototype patch'i eklenmedi.

İlk detour4113A boundary'yi dönüşte yeniden yürütmüştü;stimulus2AE2E BL'e
taşındı. Reset'te nested main'in meşgul1 olacağı varsayımı da0+frame artışı
kanıtıyla düzeltildi. Hata logları korunur;STATUS ayrıntıları içerir.

Kanıt:logs/usb-file-queue-20261029/{final-tests.txt,probe/tests.txt,
probe/report.json,probe/stock-contract/file-queue-contract.json,
emulator-range-manifest.json,hashes.json,session.diff}.8 yerel/8 paket PASS.
Previous474+13+13+10 aynı105 kaynakla korunur;518 tam suite yeniden koşulmadı.
Firmware aynı;Off/Stop FAIL,M7 NO-GO. Sonraki iş native4113A file nesnesi,
40E96→2E874/456D8/456E0 bağları ve ortak alt medya okuyucu ömrüdür.
