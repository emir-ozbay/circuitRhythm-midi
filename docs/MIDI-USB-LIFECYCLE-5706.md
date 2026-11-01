> Güncel devam:ayrı session deneyi,bu RX guard'ın kaynak/codegen'ini değiştirmeden
> yazılım sahipleri boşken eski TX iptalini ve eski tagged callback reddini
> sentetik MMIO modelinde geçirir. Stok untagged IRQ uyumu FAIL ve gerçek DMA
> iptal kanıtı açık kalır. Bu belgedeki RX-only negatif test aynen korunmuştur.
>306 toplam test PASS,M7 NO-GO. MIDI-USB-SESSION-5706.md ve STATUS.md güncel.

---

# USB RX yaşam döngüsü koruması — 28 Ekim 2026 / deneysel

Ledger'ın kayıtlı RX nesneleri için okuyucu/yazıcı/reset koruması ve boşta
reset→kapalı→yeniden açma protokolü emülasyonda eklendi. Bekleyen işler reset
edilip kaybedilmez. **Aktif USB TX aktarımının yeni bağlantıya sarkması hâlâ
FAIL**;bu çalışma tam disconnect güvenliği veya M7 GO değildir. Cihaz/MIDI/USB
API erişimi yoktur. Üretim firmware'i değişmedi.

## Pin'li stok kanıtı

- `269F0` port pop'un tek bulunan doğrudan çağıranı `29B2A` USB poll'dur.
  Alt yollar `25B1A → 2A470 → 2A426` ayrıca korunur. Bu bir tam dolaylı çağrı
  grafiği veya bütün inline RAM yazarlarının yokluğu kanıtı değildir.
- `2A374` ring write/read indekslerini sıfırlar. Bulunan doğrudan çağrıları
  `401BA/401E2` **MIDI TX** clear/poll yollarıdır. Bunu USB RX disconnect
  cleanup'ı sanmak yanlıştı.
- `5261C`, endpoint listelerini `2C90C` üzerinden kapatıp callback iletir;
  RX ring clear çağrısı içermez. Gerçek5261C testi yalnız hardware-close
  sınırını stub eder;RX header/indeksleri aynı kalır.
- `6668C..666BA` stok statik endpoint kurucu prefix'i native allocator ile
  yürütüldü. TX81 için RX ring yok;RX01 (`20005F94`,controller `20005CC8`)
  için16×64B kayıt ve `(64+2)*16+1 = 1057B` ring kurulur. DMA/staging buffer
  da allocate edilir. Bu prefix'in yürütülmesi tam boot/RTOS/OOM değildir.
- `405D4` parser clear, `40604` window select ve `405F8` buffer bind ayrı
  girişlerdir. Native parser'ın kendi overflow-clear dönüş noktası korunur.

`trace_midi_usb_lifecycle.py`,beklenen callsite/alias listelerini ve özgün
prologue baytlarını stok SHA pin'iyle assert eder;disassembly pencerelerini
saklar. Relative/indirect metadata'nın tamamı çözüldü iddiası yoktur.

## Yeni emülasyon sözleşmesi

`midi_usb_lifecycle_prototype.py`,ledger'ı değiştirmeyen ayrı bir wrapper'dır.
64B sentetik kontrol alanı kuyruk pointer/data/capacity,parser,port,controller,
phase,epoch,publish ve işlem sahipliğini tutar. Toplam sentetik RAM **1496B**
olur;üretimde checked reservation/init yoktur.

15 native giriş ve USB poll girişi yalnız Unicorn'da assert edilmiş overlay
alır. Kayıtlı nesne dışındaki çağrılar özgün prologue/trampoline ile devam eder.

| Girişler | Kayıtlı nesne için davranış |
|---|---|
|269F0,25B1A,2A470,2A426|Yalnız aktif ledger poll'un doğrulanmış native dönüş-PC zinciri okur;başka tüketici ret0 alır.|
|25AEC|Aktif phase'te kısa atomik publish sahipliği alır,özgün RAM producer'ı IRQ'lar açık çalışır;sonra sahipliği bırakır.|
|2A404,2A3BE|Kayıtlı ring'e yalnız bu publish zincirinin pin'li dönüş-PC'lerinden yazar;dışarıdan raw yazım ret0.|
|2A374|Yalnız lifecycle reset transaction'ının kendi dönüş-PC'si temizler;başka reset ret1.|
|25ACC,26828|Kayıtlı ring/port yeniden kurulamaz;borçların üstüne constructor yazımı engellenir.|
|405D4,40604,405F8|Kayıtlı parser'ın dış reset/select/bind çağrıları yalnız quiescent durumda kabul edilir;native iç overflow-clear yolu korunur.|
|269AC,26988|Kapalı/donmuş phase veya configured olmayan/değişmiş controller'da rearm ve RX completion gövdesi yürütülmez.|

`cl_poll` kuyruk pointer'ının yanı sıra data pointer/capacity ve parser/port /
controller kimliğini denetler. Değişiklik veya native configured≠3 durumunda
RX **FROZEN** olur. Sayaç/private marker'lar silinmez;producer ve poll ilerlemez.
Frozen phase,kendiliğinden yeni bağlantı sayılıp açılmaz.

`cl_reset` yalnız main context/PRIMASK0'da,başka publish/poll yokken admission'ı
atomik kapatır. Sonra IRQ'lar açıkken quiescence kontrol edilir:RX ring,sayaç,
SCANNED,parser/short queue,held MIDI sahiplikleri,retry slot/reservation ve
varsa native TX endpoint aktarımı boş olmalıdır. Başarısızsa önceki phase geri
gelir;RX/parser/TX içeriği aynı kalır. Başarılıysa gerçek2A374 ve405D4 çalışır,
ledger read metadata sıfırlanır,epoch bir artar ve phase **CLOSED** olur.
`cl_resume`,aynı bağlama/configured ve boşluk doğrulanınca ACTIVE yapar.
Epoch wrap reddedilir.

Bu epoch yazılım reset işlemine aittir. Donanımdaki her transferi eski/yeni
session'a etiketleyen bir mekanizma değildir. Aktif borçlarla disconnect
durumunda iptal/drain protokolü olmadığı için frozen durum bilerek açılmaz.

## Kapanmayan kritik negatif kontrol

Bir17B yanıt retry slotundaki payload okuyucularını bitirmiş olabilir
(`active=0`),ama native USB endpoint'in buffer'ı hâlâ in-flight olabilir.
Yeni quiescence kontrolü bunu reset için busy sayar. Yine de yalnız RX guard'ı
native TX worker'ını veya eski endpoint transferini iptal etmez. Testte RX
frozen iken bağlantı yeniden configured yapılırsa eski yanıt native output
completion üzerinden teslim edilir. **Aktif TX disconnect/session safety FAIL**.

Benzer şekilde eski RX DMA completion'ının reset/resume sonrasında geldiğinde
hangi hardware session'a ait olduğu bu guard'larla kanıtlanmaz. CLOSED/FROZEN
sırasında callback/rearm reddi testlidir;resume sonrasındaki geç callback
iptali/generation eşleşmesi açık. Tam donanım cancellation ve endpoint sahipliği
kurulmadan production entegrasyonu yapılmamalı.

## Test ve audit

19 yeni test;toplam **281 PASS**. Gerçek paketlenmiş aday üzerine emulator
overlay ile aynı19 test tekrar PASS. Bir test yukarıdaki başarısız ürün
senaryosunu gerekli negatif kontrol olarak doğrular;bu GO anlamına gelmez.

Testler registered/foreign reader-writer ayrımı,publish sırasında ve reset
transaction'ında nested çağrılar,PRIMASK/IPSR korunumu,partial SysEx/nota ve
held ownership,quiescent reset/resume/epoch,kimlik değişimi,closed completion /
rearm,native disconnect callback,RX1057 constructor prefix ve aktif TX negatif
kontrolünü kapsar. Regülatör/peripheral kodu doğrudan çalıştırılmaz.

İlk koşuda iki fixture varsayımı yanlıştı:önceden yürütülmüş constructor'ın
Unicorn translated-block cache'i patch sonrası açıkça invalidate edilmeliydi;
retry slotunun boşalması endpoint completion değildi. Cache fixture'da
temizlendi ve gerçek native in-flight flag'i quiescence kontrolüne eklendi.
Son eklemede yanlış metoda giren birkaç test satırı düzeltildi. Başarısız
çıktılar korundu;ürün negatif kontrolü gevşetilmedi.

Yeni kod **2350B**,SHA256:
`13241d42aebe8d4a9b586932e92239fc67b0cf8df1a2f83d494663acdb121a0b`.
Yerel CFG/ABI:SP delta0,BL noktalarında8B hizalama,max yerel frame32B.
Zorlanan IRQ maskeli yollar max9 komut;call/loop yoktur. Native toplam stack,
cycle,gerçek IRQ/RTOS ve keyfi inline yazarlar kanıtlanmadı. Eski ledger /
ordered/retry/recovery kaynak ve kod hash'leri aynı.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_usb_lifecycle.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_usb_lifecycle.py logs/usb-lifecycle-20261027/probe
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Oturum27 Ekim'de başlayıp28 Ekim yerel tarihte tamamlandı;log kökü
`logs/usb-lifecycle-20261027`. Güncel audit ve native-contract `probe/` altında.
Probe exit2/NO-GO beklenir. Build/baseline/üretim audit ve87 aday regresyonu /
6 sınırlı kriter PASS;aynı üretim adayı Off/Stop kaybeder. Firmware hash'leri
STATUS.md'de. Cihaza yükleme yapılmadı.

**Sonraki tek iş:**native RX/TX endpoint'leri için disconnect/reset sırasında
ortak cancel/drain + transfer-generation sahipliği;eski TX yanıtının ve geç RX
completion'ının yeni bağlantıya taşınmadığını kanıtlamak. Checked1496B RAM/init,
tam boot/OOM,zamanlama,storage,DIN input ve bütün producer/observer kapıları sürer.
