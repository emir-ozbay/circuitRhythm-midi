> Devam28 Ekim:ayrı RX lifecycle wrapper'ı,19 yeni/281 toplam test PASS.
> Native1057B ring constructor prefix ve typed reset/consumer/publish/rearm
> koruması testli;aktif TX disconnect safety FAIL/late RX DMA açık. Güncel
> STATUS.md ve MIDI-USB-LIFECYCLE-5706.md. Aşağıdaki964B ledger aynı hash'te.

# Dolu sorgu sayacında USB hizmeti — 27 Ekim 2026 / deneysel

Önceki `8 pending + 9. inquiry + Note On/Stop/Clock` engeli, **tamamı USB
yazılım alım kuyruğuna kabul edilmiş kayıtlar için** emülasyonda kapatıldı.
Nota/transport sırası korunur ve hiçbir kabul edilmiş sorgu silinmez.
Üretim firmware'ine eklenmedi;M7 NO-GO. Donanım/USB/MIDI API erişimi yoktur.

## Sahiplik ve sıra

Eski ordered varyant yeniF0'ı parser'dan önce tutuyordu;ardındaki Clock/Stop
da bekliyordu. Yeni ayrı `midi_usb_ledger_prototype.py`, native RX ring'ini
isteğin sahibi olarak kullanır. Ek bir sonsuz kuyruk veya kapasite artışı yoktur.

1. Poll başında native ring queued-byte sayısı snapshot alınır. Yalnız bu
   snapshot içinde **tam yayımlanmış** length+payload kayıtları okunur.
   Native25AEC önce2B length,sonra payload'ı byte byte yayımlar. Eksik kayıt
   parser'a verilmez ve ack edilmez. Callback sırasında eklenen kayıt bir
   sonraki snapshot'a kalır.
2. Her yeni cable0 packet'ın anlamlı byte'ları native404BC parser'ına sırayla
   bir kez girer. Note On/Off,Clock veStop için ikinci/bypass yolu yoktur.
3. Tam identity inquiry için0..8 sayaçta yer varsa yükümlülük oraya taşınır.
   Yer yoksa packet başlığı consumer'ın özel `81` işaretine çevrilir:mesaj
   işlenmiştir ama bir sabit17B yanıt borcu hâlâ bu RX kaydına aittir.
   Tam6B inquiry, en fazla3 anlamlı byte'lık bir USB packet'ta en fazla bir
   kez tamamlanabilir. Diğer işlenmiş başlıklar `00` olur.
4. `SCANNED`, işlenmiş **tam kayıtların** byte sınırını tutar. Özel81 yalnız bu
   sınırın içinde kabul edilir. Yeni host girdisindeki81/cable8 reddedilir;
   yeni kaydın bütün başlıkları herhangi bir callback'ten önce doğrulanır.
5. Tekrar taramada müzikal byte'lar parser'a verilmez. Özel borçlar, kapasite
   açıldığında sayaca taşınır ve başlık00 yapılır. Parser'ın arada bekleyen
   running status/kısmi notası bu işlemden etkilenmez.
6. Ring'in head kaydı ancak bütün packet'ları işlenmiş ve bütün borçları
   sayaca taşınmışsa native269F0 ile pop/ack edilir. Tur başına en fazla1 pop
   ve1 TX kabul denemesi vardır. Sayaç yalnız `sr_submit == 0` olunca azalır.

Borçlu head kaydı tutulurken arkasındaki **kabul edilmiş** kayıtlar okunup
müzikal sırayla işlenebilir. Producer,ack edilmemiş verinin alanını tekrar
kullanamaz. Ring read-index'i dışarıdan değişmişse wrapper reddeder.
Payload baytları değiştirilmez;yalnız işlenmiş packet başlıkları yazılır.

Bu sözleşme tek main consumer/tek SPSC producer varsayar. Gerçek IRQ/DMA ve
bütün diğer ring okuyucuları henüz kanıtlanmadı. Tam reset/flush/disconnect
sırasında eski private başlıkların yeni `SCANNED` ile yanlış yorumlanmaması
üretime geçişin zorunlu kapısıdır. Native fallback bu başlıkları okuyamaz.

## Sonlu kapasitenin anlamı

Garanti,cihazın yazılım RX ring'ine **kabul ettiği tam kayıtlar** içindir.
Ring doluyken native enqueue0 verir ve yeni kaydı kabul etmez. Bu sınırın
ötesindeki host/USB bekleme süresini veya sınırsız sorgu kabulünü çözmüş
saymıyoruz. Admitted-window testinin geçmesi koşulsuz fiziksel latency GO
anlamına gelmez. Native rearm/backpressure ve gerçek task süresi ayrıca gerekir.

## Kod ve denetim

Yeni kod **964B**,SHA256:
`bd43c2b77b861c710e99fc3f81c23bc607ddf9858eab09b6335c7e5310f20fa8`.
UIX3 magic;172B arena/toplam1432B sentetik RAM aynı. Buffer ve kullanılmayan
alanlar yeniden kullanılır. Bu RAM üretimde rezerve değildir. Eski722B/616B
USB varyantları ve recovery/retry kaynakları aynı hash'lerde korunur.

Tek endpoint/cable0,ring item-size64 ve kapasite6..2048 doğrulanır. Native
2C71C item-size alanını **bir byte** olarak yazar;komşu padding reddetme
koşulu değildir. Bu ayrıntı ayrıca testlidir. Native constructor pencereleri
disassemble edildi;bu,boot'un gerçek endpoint/ring grafiğini yürütmek değildir.

Yerel CFG/ABI PASS:SP delta0,8B call hizalama,max yerel frame32B;IRQ maskesi
yok. Parser teslimi tek yol, pop/reply denemeleri tur başına1. Döngüler
ring/buffer boyutuna bağlı ve sınırlı;en fazla1536 parser-byte çağrısı/tur.

2048B maksimum sentetik ring'de2046B commit edilmiş sorgu penceresi ve en
sondaki F8/FC için **157.912 emüle komut** ölçüldü. Bu testin açık bütçesi
500.000 komuttur;diğer küçük çağrıların100.000 sınırı değiştirilmedi.
Bu ölçüm tüm callback grafiği için üst sınır veya gerçek CPU cycle/latency
kanıtı değildir. Gerçek scheduler/IRQ süresi hâlâ açık.

## Testler ve sonuç

18 yeni test,toplam **262 PASS**. Gerçek paketlenmiş aday üzerine yalnız
Unicorn overlay ile aynı18 test tekrar PASS:

- Dolu sayaç+9. sorgu ardından gerçek note receiver/ownership üzerinden
  On→Stop ve sonraki buffer Clock/Off;TX boşalmadan doğru sıra,tekrar yok.
-192B ring'de182B kabul edilmiş pencere:21 private borç+8 sayaç;Clock/Stop
  hizmeti sürer ve sonra tam29 yanıt gelir. Sığmayan yeni kayıt atomik ret0
  alır;kabul edilmiş istekler veya callback'ler kaybolmaz.
- Inquiry'nin her byte sınırında parçalanması,native ring wrap,partial note /
  running status sürerken private borcun sayaca aktarılması.
- Native producer'ın tek tek length/payload yayımı ve parser içinde ekleme;
  eksik/yeni snapshot verisine erken erişim yok. Nested poll reddedilir.
- Private marker taklidi,invalid context/count/RAM/capacity ve değişmiş
  read-index reddi. Yalnız uygun RX header adreslerine1B00/81 yazılır;
  payload'lar korunur.16 karma akışta native parser ile sıra karşılaştırması.
- Native USB/DIN output360B stall'ı:24 ek yanıtın bütün USB baytları ve
  DIN'deki ilk360B aynen korunur. DIN **giriş** retry'si uygulanmadı.
- Her iki modda64 aktif player:64 Off/1 Stop/1 Clock,raw proje korunur.
  Recovery fault'unda9 sorgu yükümlülüğü korunur;quarantine temizlenmez.
- Maksimum2048B ring ve yerel CFG/ABI/bounds manifesti.

İlk9/sonraki15/16 testlik ara koşular PASS olarak saklandı. Son guard,
constructor disassembly'sine göre halfword yerine item-size byte'ını okur;
komşu padding için yeni test eklendi. Ürün kriterleri gevşetilmedi.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_usb_ledger.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_usb_ledger.py logs/usb-inquiry-ledger-20261027/probe
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Probe18 PASS,committed-window Clock/Stop/order/ownership PASS. Pre-admission
host latency ve gerçek IRQ/DMA/lifecycle NOT_ESTABLISHED;production uyumu FAIL;
exit2/NO-GO. Güncel kod audit'i `probe/audit/` altındadır;ilk `audit/` önceki
guard sürümünün ara kaydıdır. Diğer loglar aynı oturum kökünde.

Build/baseline/üretim audit PASS;87 aday regresyonu/6 sınırlı kriter PASS.
Üretim Off/Stop probe'ları aynı adayda FAIL,verifier exit2. Stok/üretim
hash'leri STATUS.md'de;üretime entegrasyon veya fiziksel test yapılmadı.

**Sonraki tek iş:**native USB RX ring'in bütün consumer/reset/flush/disconnect
yollarını pin'li bayt/disassembly ile çıkarıp private header + SCANNED
sahipliğinin yaşam döngüsünü emülasyonda doğrulamak. Gerçek boot ring bağlama,
IRQ/DMA/task bütçesi,checked RAM/init,DIN input,bütün producer/observer,
storage ve M7 entegrasyon kapıları açık kalır.
