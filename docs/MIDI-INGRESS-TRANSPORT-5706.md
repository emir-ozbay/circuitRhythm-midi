# 5706 MIDI giriş parser'ı ve gerçek transport store kanıtı

Devam çalışması: native output adapter/FIFO/worker ve clock backend de yürütüldü.
128/62 regresyon PASS; dolu stok64 slotta ayrı Off güvenlik probe'u FAIL.
[MIDI-OUTPUT-TRANSPORT-5706.md](MIDI-OUTPUT-TRANSPORT-5706.md) güncel kanıt ve
stub sınırlarını açıklar. Aşağıdaki120/54 sonuçları önceki alt çalışma kaydıdır.

26 Ekim 2026. Yerel Capstone/Unicorn; cihaz, MIDI portu veya USB sürücüsüne
erişim yok. Son karar **NO-GO**. Önceki MIDI ownership çalışmasının devamıdır;
stok uygulama kodu bu tur değiştirilmedi.

## Bayt ve disassembly kanıtı

| Yol | Stok adresleri ve bağ |
|---|---|
| DIN byte girişi |29C1A ->404BC byte parser ->25B1A kısa mesaj FIFO okuma ->24B68 registry ->52274 ->5AF94 decoder |
| USB yazılım alımı |29AC8 ->269F0/25B1A alım FIFO'su; CIN uzunluk tablosu ile404BC; ardından aynı24B68 registry |
| Parser kurucusu |4042C gerçek allocator ile16 bayt kısa ring, mesaj descriptor'ları ve SysEx pencerelerini kurar;25ACC ring header'ını başlatır |
| Start/Continue/Stop |5AF94 ->receiver+0C (vtable66654) ->3F746/3F750/3F75A ->receiver+30 ->wrapper69030 ->69734/69740/6974C ->33D30/33E04/33EAE |
| Start reset |33D30 ->34082 ->340AA ->34268/342E0;4709E/470CC/470E8 gerçek raw pattern okuyucuları; sekiz track position/settings store'u güncellenir |
| Clock |5AF94 ->receiver+10 (vtable66670) ->3F78E ->receiver+34 (vtable68EFC) ->32BB6 |

Adresler08000000 tabanlıdır.24B68 bu yolda kuyruğa atmak yerine kayıtlı callback'i
senkron çağırır.25AEC/25B1A uzunluk önekli mesajları,2A404/2A470 byte ring'inde
yazar/okur. Realtime byte, parser'ın yarım channel mesajını/running status'unu
bozmadan ayrı teslim edilir; bu davranış aşağıdaki emülasyonda da yürütülür.

Boot bağları disassembly'de takip edildi:27E4E/27E52'de33578 clock controller;
27E9E..27EA4 controller+90 alt nesnesini saklar.29466 ve294A8, bu alt nesne+1C
(controller+AC) action wrapper'ını3F454 receiver ctor'una taşır.3F518..3F52A
bunu receiver+30'a koyar.337F6..33808 ve47004 wrapper owner'ını controller+0C,
selector'ını0 yapar; bu alt nesnenin vtable'ı66B80'tir.

Clock için27D78,3223C nesnesini kurar;27D7C stack+78'e saklar;28CF4 bunu r4'e
alır;294C6 ctor stack argümanı olarak geçirir; receiver+34'e bağlanır.
3224C..32256 son vtable'ı68EFC yapar; ilk slot32BB6'dır. Bu statik bağların
takibi, tüm boot fonksiyonunun veya tüm nesne ömrünün emülasyonu değildir.

## Emülasyon kapsamı

Yeni scripts/midi_ingress_test_support.py ve tests/test_midi_ingress_transport.py:

- Gerçek4042C kurucusu, allocator guard, byte parser, FIFO, registry, decoder,
  receiver observer, mevcut router/ownership filtreleri ve recorder çalışır.
- Gerçek Start/Continue/Stop handler'ları çalışır; mode guard'ın okuduğu aynı
  transport store'una running0/1 stok store write/notify ile yazılır. Test
  fonksiyonu running değerini elle ayarlamaz.
- Start'ta tick1234 ve sekiz track'in step17/time100 konumları sıfırlanır;
  sekiz settings store'u raw pattern end31/start0/rate0 ile kurulur.
- Clock32BB6'nın normal dalı, external input açık/source1 iken pending+5C'yi
  artırır ve gerçek sanal çağrısına kadar gider. Özel timer yeniden kurma dalı
  (+56==2) bu testte çalıştırılmaz.
- DIN byte sınırı UART ISR'dan sonradır. USB alımı, sentetik ring'e önceden
  alınmış4 bayt paketler koyar; port armed1 olduğu için269AC rearm çağrılmaz.
  USB ring kapasitesi192 sentetik seçimdir; boot driver kapasitesi kanıtı yoktur.
- Controller, raw proje10000..39484, routerC000 ve transport store'ları3A000+
  çakışmaz. MidiRecordFixture router adresi seçilebilir; mevcut testlerin
  varsayılan nesne adresleri değişmez.
- Yalnız son sample alıcısı, transport backend/source driver ve Clock alıcısı
  BX LR sınır stub'larıdır. Bunlar yalnız emülatör flash'ına yazılır; build'e
  eklenmez. Store listener listeleri boştur. Downstream Stop nota temizliği,
  timer callback'leri ve MIDI output kuyruğu bu kanıtın dışındadır.

7 yeni test: DIN eksik mesaj/running-status velocity0 Off; USB Note On/Off;
gerçek Start reset ve Stop/Continue; iki modda yarım mesaj arasına Clock ve
Stop; iki modda USB realtime; external transport kapalı stok ignore davranışı;
128 notada gerçek enqueue/dequeue ile USB192 ve parser16 ring sarılması.
Stop transport'u durdurur; hâlen sahip olunan nota varken guard kapalıdır.
Son eşleşen Off sonrasında gerçek button dispatch ile mod değişebilir.

## Sonuç ve sınırlar

120 unittest ve54 packaged güvenlik regresyonu PASS;6 sınırlı kriter PASS.
Build, baseline, bağımsız SysEx/CRC/vector/diff/Capstone/yerel CFG stack audit
PASS. Verifier açık yayın engelleri nedeniyle beklenen exit2/NO-GO verir.
Komutlar .venv/Scripts/python.exe ile, optimizasyonsuz çalıştırıldı.
Loglar logs/ingress-final-{build,all-tests,verify,baseline,audit}.txt ve
logs/ingress-final-audit/; stok disassembly logs/transport-*,clock-*,ingress-*.
Paket raporu logs/phase1-verification-20261026T190215Z/report.json.

İlk fixture denemesinde settings start/end bayt beklentisi ters yazıldı; stok
4709E/342E0 düzeni end/start olarak düzeltilip yeniden doğrulandı. İlk test
dosyası düzenlemesinde yanlış metoda kayan assertion NameError verdi;
logs/ingress-transport-tests-first.txt bunu saklar. Bunlar test kurulum hatalarıdır;
firmware kusuru veya üretim düzeltmesi olarak sayılmaz.

SysEx SHA256058feb2ef8921168b9113edc5a3704184cc4a634c2c9838ba3533cbeeab7cdce
ve CRC7F9DE544 değişmedi. Stok pin ve ilk512 bayt aynıdır.

GO için kalanlar: hardware ISR/DMA ve downstream sequencer/Clock/Stop/output
queue/scheduler, receiver lifetime/sayısı; miras stok storage hata/recovery;
tam boot/OOM ve PRIMASK zaman bütçesi. Bir sonraki somut görev32BB6 Clock
alıcısı ile33EAE Stop backend'ini gerçek sequencer/output graph'ına bağlamaktır.
