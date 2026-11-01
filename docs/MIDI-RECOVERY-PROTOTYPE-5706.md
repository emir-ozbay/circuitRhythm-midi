# Güncel devam — Üst formatter rezervasyonu / NO-GO

213 toplam/87 aday test PASS. Recovery çekirdeği aynı;retry'nin isteğe bağlı
rezervasyon varyantı2878B kod/428B RAM,toplam1260B sentetik RAM kullanır.
Native RX tüketilmiş isteği tekrar denemez;üretim Off/Stop FAIL/M7 NO-GO.
Güncel kanıt:[MIDI-SYSEX-REQUEST-5706.md](MIDI-SYSEX-REQUEST-5706.md).

---

# Önceki devam — SysEx kabul bildirimi / NO-GO

202 toplam test/87 aday regresyonu PASS. Recovery çekirdeği1140B/832B aynı;
ayrı retry'nin bildirimli varyantı2050B/424B,toplam1256B sentetik RAM kullanır.
Native kabul olayı senkron event0;owner/event snapshot ve callback içinde
reader bitişi/reentry testlidir. Request ret/geri basıncı ve üretim kapıları
açık;aynı aday Off/Stop kaybeder,M7 NO-GO.
Güncel kanıt:[MIDI-SYSEX-NOTIFICATION-5706.md](MIDI-SYSEX-NOTIFICATION-5706.md).

---

# Önceki devam — SysEx çağıranları ve sahipli retry / NO-GO

Önceki recovery kodu1140B/RAM832B olarak korunur. Ayrı deneysel
`midi_sysex_retry_prototype.py` tek360B payload ve port kabul maskeleri,
12 formatter giriş koruması ekler:1750B kod/ek384B sentetik RAM, toplam1216B.
14 yeni testle191 toplam PASS; üretim.syx ve87 aday regresyonu aynı.
Dolu slot yanıt kaybı ve native completion callback sözleşmesi açık kaldığı
için üretim uyumluluğu FAIL, M7 NO-GO. Yeni API stok router karşılığı değildir.
Güncel kanıt/sınırlar: [MIDI-SYSEX-RETRY-PROTOTYPE-5706.md](MIDI-SYSEX-RETRY-PROTOTYPE-5706.md).
Aşağıdaki bölümler önceki recovery katmanını belgeler.

---

# 27 Ekim 2026 — SysEx karantinası ve tampon sahipliği prototipi / NO-GO

Bu bölüm günceldir; aşağıdaki önceki prototip kaydı tarihseldir. Üretim
`.syx` değişmedi. Fiziksel cihaz, MIDI/USB portu veya donanım API'si kullanılmadı.
Recovery artık **1140 bayt Thumb kodu / aynı 832 bayt sentetik RAM** kullanır.
Üç-bayt send/poll yanında SysEx vtable `+0x0C/+0x10` girişleri değiştirilir.
Üst router için iki baytları doğrulanmış **yalnız Unicorn overlay** eklenir:
`0x080298B8` → reentrancy wrapper; `0x08029962` → stok failure dönüşü
`0x08029930`. Dosyadaki firmware veya üretim patch listesi değiştirilmez.

## Stok dönüş, bekleme ve pointer ömrü (bayt/Capstone + sentetik RAM kanıtı)

| Yol | Sözleşme / sonuç |
|---|---|
| `40232`, vtable+C | `r0=port, r1={payload*, uint32 length}*`; 1 kabul, 0 hazır değil. Eski transfer varken `40244..40262` üzerinden vtable+14 poll döngüsü. |
| `40264..40274` | Descriptor'ın iki word'ünü port+8/+C'ye kopyalar; payload kopyalanmaz. port+10'un gösterdiği cursor/total iki 16-bit sayaçtır. Descriptor dönüşte serbest kalabilir; payload tamamlanana kadar sabit kalmalıdır. |
| `4028C`, vtable+10 | Kalan bayt olsa bile driver ready=0 ise 0 döndürür. Bu, payload sahipliğinin bittiği anlamına gelmez. |
| `402FC / 40378` | Sonraki poll sırasında port+8 işaretçisinden payload okunur. Testte descriptor ezilmesi çıktıyı değiştirmez; hâlâ ödünç alınmış payload'ın değiştirilmesi çıktıyı değiştirir. |
| `298B8` router | `r0=router, r1=port mask, r2=descriptor`; 0 tüm seçili portlar kabul, 1 hata. F0/F7 ve ara 7-bit veriyi doğrular. Önce bütün portları bekler; sonra `29978 memcpy` ile ortak tampona kopyalar, portlara bu tamponu bağlar. |
| `29952..2996C` | Herhangi bir port pending ise bütün portları poll eder ve tekrar dener. Seçim maskesi dışındaki portun eski payload'ı da korunmalıdır. |
| `29736`, `29834` | Normal ortak tampon 360 bayt; alternatif tampon span'i router+8'de, mod router+24'tedir. Prototip her iki kapasiteyi kontrol eder. |
| Çağıranlar | `26F32` sonrası `26F36 pop {r0,r1,r4,pc}` sonucu yok sayar; `2CBF0` sonrası `2CBF4/6` sonucu döndürür; `46954` tail-call sonucu iletir. Evrensel retry sözleşmesi yoktur. |

Adreslerin tabanı `0x08000000`. `trace_midi_sysex_contract.py` pin'li stoktan
disassembly ve JSON üretir. İki port API'sinin hizalı pointer referansları
`0x08068AB4/AB8`; yarım-word taramasında doğrudan çağrı bulunmadı. Router için
12 BL/B.W adayı bulundu. Bu tarama bütün dolaylı çağrıların CFG kanıtı değildir.

## Prototip davranışı ve bilinçli sınırlar

- `rp_sysex_send`: fault, PRIMASK=1 veya busy ise 0; yeni pointer bağlanmaz.
  Eski transfer için en fazla **bir native poll geçişi** denenir. Hâlâ pending
  ise 0 döner; `40232` bekleme döngüsünü çağırmaz. Kabul öncesi fault tekrar
  atomik denetlenir; pointer/length/counter birlikte yayınlanır. En az 2,
  en fazla 65535 bayt; 16-bit sayaç taşması reddedilir.
- `rp_sysex_pending`: ham cursor/total sahipliği; disconnect/fault bunu gizlemez.
  Busy/invalid context ve bozuk cursor da tamamlandı sayılmaz. Poll'un native
  driver kopyasını bitirmesi wire ACK veya USB transfer completion demek değildir.
- `rp_sysex_route`: tek kayıtlı router'ın ortak tamponunu yeniden girişten
  korur. Native doğrulama, memcpy, fanout ve success callback çalışır. Pending
  dalı beklemek yerine **kopyalamadan önce 1** döner. Mask dışındaki eski transfer
  korunur. Geçerli payload kapasitesi kontrol edilir; ek heap kullanılmaz.
- Sağlıklı boş girişlerde dönüşler ve SysEx baytları stokla eşleşir. Hazır eski
  port transferi bir geçişte bitiyorsa ardından yeni pointer bağlanır. **Busy
  router'ın senkron bekleme davranışı korunmaz:** sınırlı ret/retry gerekir.
  Bazı stok çağıranlar sonucu yok saydığı için bu değişiklik üretime hazır
  değildir. Kısmi fanout sonrası yeniden deneme de bütün portlara kör tekrar
  olmamalıdır. Çağıran/yanıt politikası sonraki entegrasyon işidir.

Header'ın önceki boş +4/+8 alanları registered router/busy için kullanılır;
RAM boyutu aynı kalır. `0x20047000` hâlâ yalnız test arena'sıdır, stok heap'in
altındadır. Üretim için rezervasyon veya atomik boot initialization yoktur.

## Test kanıtı ve tekrar üretme

24 deneysel test (önceki 13 + 11), gerçek native USB staging/completion-helper
ve DIN byte ring/formatter ile çalışır. Yeni kanıtlar:

- 2/3/4/5/6/47/48/49/360 bayt SysEx; üç portta stok/prototip tam bayt eşleşmesi.
- PRIMASK=1, busy, invalid context, fault sonrası ret ve pointer korunumu.
- Native USB ve iki DIN tamponu doluyken 200 bayt SysEx; ardından 64 Clock,
  Off ve Stop tam teslim. Yeni On/SysEx reddedilir. Off/Stop bitmap'i korunur.
- Disconnect'te eski pointer ve ortak tampon korunur; mask dışındaki port da
  yeni router kopyasını durdurur. Source/descriptor/payload ömürleri ayrılır.
- Ready/poll/copy/callback sınırlarında context-preserving nested SysEx,
  Off/On/Clock/poll/router çağrıları; dönüşler, ABI/SP ve canary denetimi.
- Eski bypass negatif kontrolü **korundu**: yeni SysEx hook'ları kapalıyken
  fault sonrası üç portta SysEx gönderilir. Eski native bekleme de full driver
  ve saf busy wrapper altında 100000 komut test bütçesinde tamamlanmaz.
  Bu bütçe emülatör kaçışıdır; firmware timeout'u değildir.

`probe_midi_recovery_prototype.py` paketlenmiş gerçek aday üzerine yalnız
Unicorn overlay ekleyerek aynı 24 testi ve 6 player/Stop vakasını çalıştırır.
`tested_sysex_quarantine=PASS`, `hooked_sysex_accepted_while_quarantined=false`;
negatif kontrol true kalır. `all_producer_quarantine=REVIEW_REQUIRED`,
`production_integrated=false`, `hardware_release=NO-GO`, exit2.
Her producer/lifecycle yolunun kapandığı iddia edilmez.

Yerel CFG: SP delta0, BL/BLX hizalama8, max yerel frame40B; native router
trampoline stok32B prologue'u tekrarlar. Explicit IRQ-mask yolları max16 komut,
call/loop yok. Bütün native callee stack'i, CPU cycle ve IRQ süre bütçesi değildir.
Kod SHA256 `c6079ec422adc92717309c6bf61ee30efdc51a7ca207d01a575415092e37ca1b`.
Log/rapor/diff: `logs/recovery-sysex-20261027/`.

İlk geniş testte callback hook'u, trampoline'den aynı adrese dönülmesini ikinci
callback sandı (2 yerine 1). Kayıt hook'u stub'ın dönüş komutuna taşındı;
native callback sayısı veya başarı ölçütü değiştirilmedi. İlk FAIL logu saklandı.
Saf busy wrapper'ın yeterli olduğu ve ready=0'ın pointer'ı serbest bıraktığı
varsayımları reddedildi; negatif deneyler testte kaldı.

GO engelleri: checked RAM/atomik initialization, çağıran ret/retry ve kısmi
fanout politikası, üretim hook/lifecycle/mode guard/reset-resume, gerçek IRQ/DMA
ve disconnect kabul aralığı; ayrıca stok storage hata-kurtarma, tam boot/OOM,
PRIMASK zaman bütçesi. Sonraki tek iş: **298B8'in 12 çağıranında ret/kısmi
fanout/yanıt ömrünü izleyip bounded retry sözleşmesini emülasyonda doğrulamak.**

---

# Önceki kayıt — Off/Stop yeniden teslim prototipi

27 Ekim 2026. Yeni Thumb-2 mekanizması, önceki player Stop karşı deneylerini
Unicorn'da kayıpsız geçiriyor. **Dağıtılabilir firmware'e eklenmedi.** Gerçek
adayda kayıp hâlâ vardır. Ayrı bulk SysEx API'si prototip kilidini atlayabildiği
için üretime bağlamak güvenli kabul edilmedi. Cihaz/MIDI/USB erişimi yok.

## Uygulanan deney

src/midi_recovery_prototype.py, 774 bayt makine kodu üretir. Patcher'a hunk
vermez; seq_Patch veya --build-phase1 tarafından import edilmez. Fixture yalnız
Unicorn içinde kodu08070000'e, üç portun kopya vtable'larını RAM'e yerleştirir.
Paket imajı ve stok baytları değişmez. Yeni13 test ayrı deneysel testlerdir;
paket verifier'ının87 aday regresyonuna recovery varmış gibi eklenmemiştir.

Her portun 16 kanal ×128 nota için256-bayt pending Off bitmap'i, count/cursor,
busy/seen/fault ve pending Stop alanı var. Toplam832 bayt:16 başlık +3×272.
Tekrarlanan Off'lar aynı bit altında birleşir; velocity0 Note On da Off sayılır.
Normal sağlıklı gönderimde mesaj baytları ve release velocity korunur.
Recovery Off'larının release velocity'si0 olur; hata davranışı bayt eşdeğeri
veya müzikal kesintisizlik garantisi olarak sunulmaz.

Known failure/reentrant send sonrası modellenen üç-bayt API'sinde yeni On,
Clock, Start/Continue ve CC reddedilir. Önceden kabul edilmiş FIFO korunur;
pending Off ancak native enqueue başarılı olunca silinir. Bütün bilinen Off'lar
ardından Stop kuyruğa alınır. Yeni On kabulü yeniden açılmaz; fault kalıcıdır.
Otomatik resume/reset ve mode-admission bağlantısı üretim için tasarlanmamıştır.
CC120/123 broadcast veya özel dosya/flash işlemi yoktur.

Bir poll en fazla8 bitmap-word incelemesi/Off enqueue denemesi ve count0 ise
bir Stop denemesi yapar. Native FIFO worker ve driver kodu gerçektir; bunların
toplam süresi bu8 sınırından türetilemez. Özellikle SysEx/timer/IRQ süresi açıktır.
Caller PRIMASK1 ise native I/O'ya girilmez; Off ertelenir. Busy alanda nested
poll kuyruğa girmez; nested Off korunur, yeni On/Clock reddedilir.

## Kanıt ve sonuç

logs/recovery-prototype/report.json, paketlenmiş aynı imaj üzerinde negatif
aday kontrolünü ve ayrı RAM/vtable overlay deneyini birlikte kaydeder.

| İki modda her port | Mevcut aday | İzole prototip |
|---|---|---|
|63 nota +Stop|63 Off /1 Stop|63 Off /1 Stop;1 poll|
|64 nota +Stop|64 Off /0 Stop|64 Off /1 Stop;2 poll|
|64 nota +tek USB F8+FC buffer|63 Off /0 Stop|64 Off /1 Stop;5 poll|

Native USB2B408 staging/268D0 completion-helper ve DIN2B564/26014 byte ring
testinde64 On,80 Clock,64 Off,1 Stop'un USB frame ve DIN running-status baytları
tam eşleşti. USB endpoint transferi bekletilip FIFO dolduruldu; daha sonra
completion native yardımcıya enjekte edilince bütün kapanışlar teslim edildi.
Gerçek IRQ/DMA/wire veya uzak cihaz onayı kanıtı değildir.

2048 farklı channel/note Off, tekrarlar, üst sınırlar, invalid pointer/magic,
count2049/cursor255, iki PRIMASK, raw proje/canary korunumu testlidir. En fazla8
Off denemesi/poll ayrıca native enqueue girişleri sayılarak doğrulandı.
Modellenen context-preserving preemption, Off veya Stop enqueue öncesinde yeni
Off/On/Clock çağırır. Yeni Off kaybolmaz; On/Clock açılmaz. Stop sırasında yeni
Off gelirse ilk Stop ardından o Off ve son bir Stop daha çıkabilir. Bu test
NVIC exception stacking veya gerçek ISR öncelik/timing kanıtı değildir.

Capstone/yerel CFG: bütün doğrudan branch hedefleri komut başlangıcı; tüm
çıkışlarda SP delta0; BL/BLX anında8 hizalama; en büyük yerel frame40 bayt.
MOVW/MOVT adresleri ve üç native dış çağrı denetlidir. Explicit CPSID ->MSR
arasında loop/call yok; en uzun yol16 komut. Bu16 komut ölçülmüş CPU cycle veya
mikrosaniye değildir. Native callee stack/timing kapsam dışıdır.
Deneysel code SHA256:
e57d9c5ae4d11c3847b60142286533830839c03d0c24ef6e24f1b4a86fe84946.

İlk audit walker BICS'i adına bakarak branch sayıyordu ve KeyError68 verdi.
Gerçek koşullu branch listesiyle düzeltildi; bu prototip/firmware hatası değildir.
İlk log logs/recovery-prototype-audit-first.txt olarak korunur.

## Kalan somut engeller

**Bulk SysEx bypass:** native40232 descriptor bağlama ve4028C pending API'si,
üç-bayt401FE yolundan ayrıdır. Prototip yalnız send/poll vtable slotlarını
değiştirdiği için fault set iken bile yeni bir6-bayt SysEx kabul edilip gönderilir.
Bu karşı deney testte karakterize edilir; ayrıca JSON'da
all_producer_quarantine=FAIL ve native_sysex_accepted_while_quarantined=true
yazılır. Testin PASS'i bypass'ın düzeldiği anlamına gelmez. Report runner kalan
engeller nedeniyle exit2 verir. 40232'nin native bekleme/poll döngüsü ve pointer
ömrü anlaşılmadan basit busy wrapper eklemek yeni kilitlenme riski yaratır.

**RAM rezervasyonu yok:**20047000 yalnız test modelindeki arena adresidir.
Stok heap current2004EA98'in altındadır; üretimde boş varsayılamaz. Bu adres
firmware'e kopyalanmamalı.832 bayt için checked allocator rezervasyonu, başarısız
rezervasyonda fail-closed davranış, tam boot/OOM ve initialization kanıtı gerekir.
Mevcut256-bayt state büyütülmedi veya taşınmadı.

**Lifecycle ve politika:** port context ömrü, bütün producer girişleri,
disconnect'in native hazır kontrolü/enqueue/driver kabulü arasında gelmesi,
USB completion kaybı ve gerçek task/IRQ sırası açıktır. Bit native FIFO
kabulünde silinir; wire ACK anlamına gelmez. Üretim mod guard'ı bu deneysel
flags alanını okumaz. Hata sonrası Clock/On ret ve reset/resume politikası ayrıca
tamamlanmalıdır. Miras storage hata/recovery ve genel boot/PRIMASK kapıları sürer.

Sonraki tek görev:40232/4028C caller dönüş, bekleme ve payload pointer ömrünü
izleyip bulk SysEx bypass'ını kapatan, sağlıklı stok davranışını koruyan bounded
bir giriş kancası prototipi hazırlamak. Ardından aynı negatif kontrol ve native
USB/DIN stall deneyleri tekrar çalıştırılmalı. Henüz üretim hook'u eklenmemeli.
