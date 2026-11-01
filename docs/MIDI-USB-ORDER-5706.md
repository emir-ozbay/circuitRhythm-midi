> Devam:ayrı ledger,kabul edilmiş tam USB RX kayıtlarında dolu inquiry
> sayacı arkasındaki Clock/Stop hizmetini de korur.18 yeni/262 toplam PASS;
> host pre-admission latency ve lifecycle/IRQ/RAM açık,M7 NO-GO. Güncel
> STATUS.md ve MIDI-USB-LEDGER-5706.md. Aşağıdaki616B ordered kod aynı hash'te.

# USB Note On / Stop sırası düzeltmesi — 27 Ekim 2026

Kullanıcının seçtiği zor engel, bekletilen Note On'un sonraki Stop'tan sonra
çalışmasıydı. `ordered=True` emülasyon varyantında bu hata kapatıldı. Üretim
firmware'ine eklenmedi; M7 hâlâ NO-GO. Fiziksel cihaz/MIDI/USB erişimi yoktur.

## Değişen sözleşme

Önceki `inquiry → Note On → Stop` akışında TX doluyken inquiry token'ı
cursor'u durduruyor; realtime taraması Stop'u öne geçiriyordu. TX açılınca
Note On işleniyordu. Yeni varyantta **realtime bypass yolu üretilmez**.
Byte'lar yalnız bir yoldan, geliş sırasıyla native `404BC` parser'ına gider.
Kısa mesajlar yine native ring pop/`24B68` dispatcher ile işlenir.

`PENDING` artık tek bit yerine `0..8` inquiry yükümlülüğü sayısıdır. Bütün
istekler aynı6B kimlik sorgusu, cable0 ve aynı17B sabit yanıt olduğundan
payload'larını ayrıca saklamak gerekmez. Yinelenen istekler silinmez:8 kabul
edilmiş sorgu8 yanıt demektir. Sorgu sayacı müzikal byte cursor'unu tutmaz.

- Inquiry tamamlanınca sayı bir artar. Nota, Note Off ve transport byte'ları
  aynı turda normal sırayla devam eder; sorgu yanıtı beklemeleri gerekmez.
- Poll sonunda en fazla bir `sr_submit` denemesi yapılır. Yalnız kabul0
  sonrasında sayı bir azalır. Ret/busy/fault yükümlülüğü silmez. Bu yerel TX
  kabulüdür; fiziksel teslim veya bütün producer'lar için uyum iddiası değildir.
-8 sayısı bir64B USB buffer'ına sığan8 tam inquiry'ye karşılık gelen deneysel
  sınırdır; sınırsız kuyruk veya sınırsız trafik garantisi değildir. Var olan
  word kullanılır. Aktif TX slotunda buna ek olarak bir sahipli yanıt bulunabilir.
- Kapasite doluyken yeni `F0`, **parser'a verilmeden** cursor geri alınarak
  tutulur. Daha sonraki hiçbir byte öne geçmez. Aktif bir SysEx parser'ı dışarıdan
  seed edilmişse kapasite doluluğunda onun sonraki byte'ı da tutulur. Kapasite
  açılınca tam tutulduğu byte'tan devam edilir; kabul edilmiş istek kaybolmaz.
- Kapasite dolu olsa bile arada yeni SysEx başlangıcı yoksa channel ve transport
  mesajları ilerler. Tam kapasitedeki yeni SysEx'in arkasındaki Clock/Stop ise
  bekleyebilir. Bu kalan **gecikme engelidir**; sıra koruması kaldırılarak çözülmez.

Gelen akış gerçekten `Stop → Note On` ise bu sıra korunur. Stop'u bir nota
filtresi olarak yorumlamayız. Aynı şekilde `97, note, FC, velocity` gibi
yarım notanın içine giren realtime mesajında native tamamlanma sırası
`FC → Note On` doğrudur. Karşılaştırma stok byte-parser davranışıyla yapılır.

## Kod, bellek ve sınırlar

`src/midi_usb_inquiry_prototype.py:arm_code(ordered=True)` **616B** üretir.
SHA256 `f90f6c6291511fc4e63591c34a2f48050f04de5dea1c073ea3468689a6d5b119`.
172B arena /1432B toplam sentetik RAM değişmez; yeni RAM eklenmedi. Bu adresler
üretimde boş alan değildir ve checked heap/atomik init hâlâ yoktur.

Yeni state magic `UIX2`, eski bit düzeninin yeni sayaç gibi okunmasını engeller.
PRIMASK/IPSR, nested poll, invalid magic ve count>8 girişleri hiçbir RX
tüketimi olmadan reddedilir. Tek main-context tüketici/tek endpoint/cable0
varsayımı sürer; gerçek RTOS task-switch/IRQ kanıtı değildir.

Varsayılan `ordered=False` eski722B kodu aynı
`b1b24f86615963f3a4cc08366c51a4bade7604cc53b880412877aa54edfe0b0b`
hash'iyle üretir. Eski17 test ve iki negatif kontrol değiştirilmedi.
Yeni varyant emülatör fixture'ında açıkça seçilir. `29AC8` girişindeki4B
overlay, beklenen prologue/app bounds/çakışma kontrolü ile kurulur.

Audit: SP delta0, çağrılarda8B hizalama, en büyük yerel frame32B; yeni IRQ
maskesi yok. Tek parser delivery yolu, realtime scan bulunmaması, tek reply
denemesi ve kapasite hold dalının delivery'den önce çıkması ayrıca denetlenir.
Buffer döngüleri sınırlıdır; native toplam stack/cycle/USB rearm kanıtı yoktur.

## Emülasyon kanıtı

14 yeni test; toplam **244 PASS**. Aynı14 test paketlenmiş aday üzerine
yalnız emulator overlay ile tekrar PASS:

- Her iki modda gerçek receiver/adapters/ownership üzerinden Note On→Stop;
  Off ile sahiplik kapanır, TX açıldıktan sonra eski Note On tekrar çalışmaz.
  Raw proje baytları değişmez.
- Gerçekten Stop'tan sonra gelen Note On korunur. Running status, velocity0
  Off ve kısmi notanın içindeki realtime native parser sırasıyla eşleşir.
- Note On/Off/Stop permütasyonları × inquiry konumları × USB parçalanmaları:
  96 kombinasyon.24 deterministik karma akışta stok/native poll ile birebir
  kısa mesaj izi karşılaştırılır; farklı kanal/status/RT/SysEx ve kayıt sınırları.
-8 yükümlülük doluyken channel/RT devamı;9. inquiry'nin F0/packet-içi cursor
  bariyeri ve seed edilmiş partial SysEx;sonra tam9 yanıt, tekrar/kayıp yok.
- Eski iki inquiry + sonraki buffer'daki F8/FC senaryosu artık TX açılmadan
  ilerler. Tam kapasite + yeni inquiry arkasındaki F8/FC beklemesi gerekli
  negatif kontroldür; genel latency kriteri FAIL kalır.
- Native USB/DIN çıkış sürücülerinin360B stall'ı ve tam8 yanıtın USB baytları;
  tur başına en fazla1 kabul denemesi. DIN **giriş** retry'si yapılmadı.
- Her iki modda64 aktif player sesi:64 Off/1 Stop/1 Clock çıkar; raw proje
  korunur. Recovery fault'u bilerek kalır ve2 inquiry yükümlülüğü silinmez.

İlk yeni test koşusunda iki test altyapısı eksikliği vardı: audit henüz
`ordered` parametresi almıyordu ve bir test setup öncesi `self.inquiries`
okuyordu. İkisi düzeltildi; ürün beklentileri gevşetilmedi. İlk çıktı saklandı.

## Komutlar ve devir

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_usb_order.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_usb_order.py logs/usb-inquiry-order-20261027/probe
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Probe14 PASS, `deferred_note_on_stop_order=PASS`, kapasitedeki koşulsuz realtime
gecikmesi FAIL, üretim uyumu FAIL; exit2/NO-GO beklenir. Kod audit/native
disassembly/overlay manifesti `probe/audit/`;oturum diff/hash ve loglar aynı
`logs/usb-inquiry-order-20261027` kökündedir.

Build/baseline/üretim audit PASS;87 aday regresyonu/6 sınırlı kriter PASS.
Üretim Off/Stop probe'ları değişmeden FAIL, verifier exit2. Firmware/stok
hash'leri STATUS.md'de. Yeni runtime'ı üretime eklemek için RAM/init, bütün
producer/observer uyumu, DIN input, lifecycle/mode, boot/OOM, storage recovery
ve IRQ/DMA/disconnect kapıları hâlâ gereklidir.

**Sonraki tek iş:**8 yükümlülük dolu ve9. SysEx başlangıcı tutulurken sonraki
Clock/Stop için, bu byte sırası garantisini bozmayan kabul/geri basınç ve
gecikme çözümünü geliştirmek. Kapasiteyi artırmak tek başına kabul ölçütü değildir.
