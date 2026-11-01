> Güncel 1 Kasım / Taint sonrası Load–New — İki modda native UI erişimi sınandı.
> Projects açılır; controller flags bit1 ve ayrıca dispatcher phase2 Load/New'ü
> engeller. Tanısal tam backend yükleme ve sonraki UI Load/New taint'i temizlemez.
> Bu bir kullanıcı kurtarma yolu değildir. Firmware272a8128… aynı; M7 NO-GO.
> Güncel sayım ve tek sonraki iş STATUS.md'de; ayrıntı
> [MIDI-RECOVERY-LOAD-REENTRY-5706.md](MIDI-RECOVERY-LOAD-REENTRY-5706.md).
> Alt bölümler tarihsel sonuçlardır.

---

> Güncel1 Kasım /Load short-read — Stock köprünün hata4'ü başarı apply'ına
> çevirmesi native reset/file worker ile yeniden üretildi. Yeni guard yanlış
> başarıyı atlar,native Close ve kalıcı taint ile mod geçişini kapatır. Raw alias
> rollback/toparlanma çözülmedi. Yeni aday272a8128… /CRC985753F7;M7 NO-GO.
> Güncel sayım ve tek sonraki görev STATUS.md'de;ayrıntı
> [MIDI-RECOVERY-LOAD-SHORT-READ-5706.md](MIDI-RECOVERY-LOAD-SHORT-READ-5706.md).
> Alt bölümler tarihsel sonuçlardır.

---

> Güncel31 Ekim /Canlı parametreler — Üretim/SYX c9a87a9d…/CRC BEB0D013
> değişmedi. Yeni live UI/IRQ testinin sonucu STATUS.md'de;eski158 aynı-image
> test kanıtı korunur. Keşiflerde native RAM/fault temizlenmedi;düzelen test
> yeni reset'ten yürür. M7 NO-GO;cihaz/port erişimi yok,kurtarma planı aynı.

---

> Güncel31 Ekim /Gate expiry ve tie — Üretim/SYX c9a87a9d…/CRC BEB0D013
> değişmedi. Yeni sentetik tie ve native UI Gate süre testlerinin sonucu
> STATUS.md'de;fiziksel cihaz erişimi/yükleme yok. Önceki154 paket kanıtı aynı
> adayda korunur. M7 NO-GO;kurtarma planı ve stock hash pin'i aynı.

---

> Güncel31 Ekim /64 stok ses Stop — Yeni aday c9a87a9d… /CRC BEB0D013.
> Normal64 Off+Stop taşmasını player'lar arasında bounded native servis
> önler;gerçek overflow quarantine/reboot politikası korunur. Stock/vector,
> önceki recovery kodu ve1088B rezervasyon aynı;wrapper16B stack ekler.
> M7 NO-GO;cihaz erişimi/yükleme yok. Güncel sonuçlar STATUS.md;
> eski yerel aday logs/recovery-native-64voice-20261031/before/build altında.
> Alt raporlar eski SHA'lara aittir.

---

> Güncel31 Ekim /Native timer IRQ — Borca host yazısı olmadan IRQ66→
> Main358→slot11/2B750→uygulama370→player zinciri PASS.10690 IRQ/tüketim;
> iki modda1–32–1,544 LED,8 canlı notada Stop ve40 On/40 Off/193 Clock.
> Sonlu DSP recording-idle ve ham ADC referans/pil profilleri;native pil
> hesabı/kapanış kodu korunur.2 yeni exact-SYX +29 örtüşen hedefli test PASS.
> Önceki149 yeniden koşulmadı;verifier151/core-only144. Firmware3f979b70… /
> CRC5AB3F54B,üretim ve1088B rezervasyon aynı. M7 NO-GO;cihaz erişimi yok.
> Sonraki:uzun gate/farklı adım notalarıyla64 aktif stok ses ve native Stop.
> STATUS veMIDI-RECOVERY-TIMER-IRQ-5706.md güncel;altı tarihseldir.

---

> Güncel31 Ekim /Native Play–Stop — Tek reset,8 gerçek player,iki modda
>1–32–1 ve193 microstep commit/player/mod PASS;544 LED bileşimi. Mod/iki UART
> portu başına40 On/40 Off ve8 canlı notada native Stop flush PASS.
> Timer borcu sonlu sentetik girdidir;hardware IRQ/geçen zaman kanıtı değildir.
> Yeni1 exact-SYX +28 örtüşen hedefli test PASS;önceki148 yeniden koşulmadı.
> Verifier149/core-only143;firmware3f979b70…/CRC5AB3F54B veüretim aynı.
> Native cursor bit6;eski bit0 etiketi ayrı edit/recorder store'udur.
> M7 NO-GO. Sonraki:40000C00/vector66 IRQ→borç→Main timer zinciri.
> STATUS veMIDI-RECOVERY-PLAYBACK-5706.md güncel;altı tarihseldir.

---

> Güncel31 Ekim /Probability — Native yardımcı görünüm sayfa/pad grubu
> tamamlandı: Note1/7, Velocity2/Gate3, Pattern Settings4, Microstep5, Probability6.
> Yeni mode6 testi:512 üst pad/64 uç/128 LED/32 zengin Mutate PASS;26 hedefli PASS.
> Önceki147 aynı image'de, tekrar koşulmadı. Genel verifier148/core-only143.
> Firmware3f979b70…/CRC5AB3F54B, üretim ve1088B RAM aynı; M7 NO-GO.
> Sonraki iş: native Play17/Stop17→player/scheduler→1–32 playhead izi.
> STATUS veMIDI-RECOVERY-PROBABILITY-5706.md güncel; altı tarihseldir.

---

> Güncel31 Ekim /Microstep — Native mode5 iki sayfa/8 track/iki mod PASS.
>512 üst-pad eşlemesi,64 uç senaryo,tüm64 maske,128 LED bileşimi ve64 held
> guard sınandı.32 velocity/gate koruması +32 durdurulmuş idle edit PASS.
> Yeni1 paket ve26 hedefli test PASS;önceki146 aynı image'de,tekrar koşulmadı.
> Genel verifier147/core-only143. Firmware3f979b70…/CRC5AB3F54B veüretim aynı.
>1088B rezervasyon/2184B workload payı aynı;M7 NO-GO. Sonraki:native Probability6.
> STATUS veMIDI-RECOVERY-MICROSTEP-5706.md güncel;altı tarihseldir.

---

> Güncel31 Ekim /Pattern Settings — Native mode4 sayfa/Start-End/hız/yön/
> Mutate testi8 track/iki modda PASS:1024 üst +1024 alt pad,64 LED/held guard,
>32 kayıpsız8B-record Mutate. Yeni1 paket ve26 hedefli test PASS;önceki145 aynı
> image'e aittir ve yeniden koşulmadı. Genel verifier146 test içerir.
> Firmware3f979b70…/CRC5AB3F54B,üretim kaynakları ve1088B RAM aynı. M7 NO-GO.
> Düzeltme:eski iç16/17=Clear/Duplicate etiketi yanlış;17 Play,24 Duplicate.
> Kanonik koşu17'yi kullanmaz,transport0'ı denetler. Sonraki iş:native Microstep5.
> STATUS veMIDI-RECOVERY-PATTERN-SETTINGS-5706.md güncel;altı tarihseldir.

---

> Güncel31 Ekim — Note1↔7 asılı nota ve hatalı mod kabulü düzeltildi.
> Native8 track/iki mod/iki sayfa:1536 tuş,512 adım,64 retained release,
>48 native iptal,64 pitch/LED senaryosu PASS. Velocity/Gate yeniden PASS.
> Aynı SYX üzerinde143 core +1 Note +1 Velocity/Gate paket testi;6 ölçüt ve60
> hedefli test PASS (örtüşür). SYX3f979b70…/CRC5AB3F54B;42 patch/7595B.
> Stock ve1088B rezervasyon aynı;proje I/O0/ek tahsis0. M7 NO-GO.
> Sonraki iş:native Pattern Settings4. STATUS veMIDI-RECOVERY-NOTES-5706.md güncel.

---

> Güncel30 Ekim — Native Velocity/Gate testi sekiz track ve iki mod/sayfada PASS.
> 1024 üst-pad eşlemesi,128 parametre/LED senaryosu; stok end15→31 uzatması testli.
> Yeni1 paket native test ve25 hedefli test PASS; önceki142 aynı firmware'e aittir.
> Firmwareafbab4f2…/CRC114DA352 aynı; proje I/O0, ek tahsis0,2184B alan aynı.
> Sonraki iş: native Note1/7 sayfa tuşu ve alt16 pad stok eşlemesi.
> M7 NO-GO; STATUS veMIDI-RECOVERY-VIEWS-5706.md güncel, altı tarihseldir.

---

> Güncel29 Ekim (native file queue):45EB6→sync FIFO/wait/2AD40 worker
> yolu8 yerel/8 paket testte PASS;4113A file API RAM sınırı kalır.
> Result credit'ten önce yayımlanır;reset/suspend/nested MSC reader testli.
> Yeni negatif:53E8C short-read hatasını kullanmayıp2046B artık veri yazabilir.
> Fiziksel tekrar/stock patch yok;105 eski kaynak ve firmware aynı.
>518 discovery,tam518 bu oturumda koşulmadı. M7 NO-GO;STATUS ve
> MIDI-USB-FILE-QUEUE-5706.md güncel.

---

> Güncel29 Ekim (uzun sample loop):native53E24/53E8C128 yuva döngüsü,
> dosya/flash/UI/allocator RAM sınırlarıyla10 yeni yerel/10 paket testte PASS.
> Aktif USB okuyucu,worker reentry,semaphore,reset/suspend ve double-buffer
> denetlendi. File-task ömrü/gerçek UI ve main retry/power erişimi açık.
> Önceki101 kaynak/firmware aynı;510 discovery,tam510 bu oturumda koşulmadı.
> Production Off/Stop FAIL,M7 NO-GO. STATUS ve MIDI-USB-LONG-LOOP-5706.md güncel.

---

> Güncel29 Ekim (poll caller):2DE92 ek MSC çağrısının dispatch/adapter /
> callback zinciri ve owner/context kapıları13 yeni yerel/13 paket senaryosunda
> PASS. Worker/IRQ/recursive/factory/clock-stop ve kapanış arası sınırlar testli.
> Callback-only retry/power ilerlemez;native main hâlâ gerekir.53E78 yalnız BL
> kenarı testli,tam53E24 ve43E1C/Packs/RTOS ömrü açık.97 önceki kaynak ve
> firmware/codegen aynı.500 discovery;tüm500 bu oturumda koşulmadı.
> Üretim Off-Stop FAIL,M7 NO-GO. STATUS ve MIDI-USB-POLL-CALLERS-5706.md güncel.

---

> Güncel29 Ekim (factory + debt):Hazırlanmış MAIN/kısmi owned SysEx /
> query ledger borcuyla MIDI-only↔MIDI+MSC geçişi13 yeni yerel ve13 paket
> senaryosunda PASS. Native settings/boot caller,READ iptali,eksik ACK ve
> rebuild içi reset/yeni istek testli. Firmware/93 önceki kaynak/codegen aynı.
> Önceki tam474 PASS korunur;487 toplam discovery,tam487 bu oturumda koşulmadı.
> Tam Packs UI/diğer caller/boot/RAM-init/gerçek timing/integration açık.
> Üretim Off-Stop FAIL,M7 NO-GO. STATUS ve MIDI-USB-FACTORY-DEBT-5706.md güncel.

---

> Güncel29 Ekim (staging):474 toplam/87 aday PASS. Native formatter'ın
> henüz HAL'e kabul edilmemiş MAIN baytları/kısmi owned SysEx cursor'u optional
> carry varyantında uyku/reset boyunca korunur. Reddedilen flush tamponu silmez;
> OPEN poll retained full MAIN'i önce gönderir. Paket adayında27 senaryo PASS.
> Kabul edilmiş TX/raw ALT/parser/held/fault/full boot/RAM-init/integration açık.
> Üretim aynı/Off-Stop FAIL,M7 NO-GO. STATUS ve MIDI-USB-STAGING-5706.md güncel.

---

> Güncel29 Ekim:462 toplam/87 aday PASS. Henüz USB'ye verilmemiş yazılım
> MIDI borcu artık fiziksel reader iptalinden ayrı korunur. Önceki suspend /
> wake kilitlenmesi yeni carry overlay ile Normal/Sequencer'da geçer;reset
> sonrası host config ile yanıtlar kayıp/tekrar olmadan model IRQ akışına çıkar.
> 360B payload,Note Off,Clock/Stop,wrapped owed kayıt ve generation yarışları
> testli. In-flight/staged/partial-parser/gerçek port fault carry almaz;eski
> politika değişmez.2712B checked RAM/init/boot/gerçek timing ve entegrasyon
> açık. Üretim aynı/Off-Stop FAIL,M7 NO-GO. STATUS.md ve MIDI-USB-CARRY-5706.md.

---

> Güncel28 Ekim:447 toplam/87 aday PASS. Native main25870..25880 artık
> SysEx retry ve power service'e ulaşır;query,READ/CSW ve borçsuz uyku/uyanma
> manuel pump olmadan çalışır. Worker648AE..648B8 de gerçek native döngüdür;
> RTOS wait/return,ACK/IRQ/flash sınırları sentetik. Önemli açık:uyku öncesi
> retained MIDI debt,FROZEN consumer/ss_quiet döngüsünde wake sonrası64 main
> geçişinde de ilerlemez. Task kapısı bütünüyle kapanmadı.2584B checked RAM /
> init,diğer caller/boot/timing/Packs/storage alias/DIN açık. Üretim aynı /
> Off-Stop FAIL,M7 NO-GO. STATUS.md ve MIDI-USB-TASK-5706.md güncel.

---

> Güncel28 Ekim:434 toplam/87 aday PASS. Normal USB suspend/wakeup artık
> emülasyonda ortak reader/ACK/flush bariyerini bekler. Erken wake/reset geç
> clock-stop yapmaz;reset eski configuration'ı otomatik açmaz. Saat durmuşken
> yalnız wake/reset açık,normal USB MMIO/servis çalışmaz. Native save/restore /
> ungate gerçek;clock/IRQ/timing ve RTOS/flash sınırları sentetik. LPM/deep
> stop/DMA desteklenmez.2520B checked RAM/init,task/boot/tam Packs/gerçek
> bariyer açık. Üretim aynı/Off-Stop FAIL,M7 NO-GO. STATUS.md ve
> MIDI-USB-POWER-5706.md güncel.

---

> Güncel28 Ekim:418 toplam/87 aday PASS. Native432A8 USB factory artık
> eski MIDI/MSC reader ve parent teardown bitmeden class listesini değiştirmez.
> MIDI-only↔MIDI+MSC descriptor/query/READ ve geçiş içi yeni istek/reset koşullu
> emülasyon testli. HAL init,tick/NVIC/clock ve RTOS sınırları sentetiktir.
> 2424B checked RAM/init,USB power/task/full boot/gerçek bariyer ve tam Packs
> akışı açık. Üretim aynı/Off-Stop FAIL,M7 NO-GO. STATUS.md ve
> MIDI-USB-FACTORY-5706.md güncel.

---

> Güncel28 Ekim:402 toplam/87 aday PASS. Native READ10→queued backend /
> drain/worker→USB veri/CSW ve reset iptali emülasyonda testli. İlgili READ
> hatasının sonraki başarılı iş tarafından örtülmesi engellendi. Pin'li stok
> MSC yazma korumalı;WRITE10 media yazmasına ulaşmaz. Alt flash RAM,RTOS
> wake/yield sınırdır.2296B checked RAM/init ve full factory/class/power/task /
> boot/gerçek bariyer açık. Üretim aynı/Off-Stop FAIL,M7 NO-GO.
> STATUS.md ve MIDI-USB-STORAGE-5706.md güncel.

---

> Güncel28 Ekim:384 toplam/87 aday PASS. Aktif31B MSC CBW bekleme aktarımı
> disable/ACK/AHB/shared FIFO/TX2 flush modeliyle iptal edilip native deconfig /
> Bulk-Only Reset sonrası tek job ile yeniden açılır. MIDI/DIN korunur.
> Başlamış SCSI/storage,data/CSW/TX iptali hâlâ açık;durumları kapalıda tutulur.
>2168B checked RAM/init,task/power/full boot ve gerçek bariyer/timing açık.
> Üretim aynı/Off-Stop FAIL,M7 NO-GO. STATUS.md ve MIDI-USB-MSC-5706.md güncel.

---

> Güncel28 Ekim:363 toplam/87 aday PASS. Gerçek MIDI parent'ın DIN FIFO
> silmesi dar owned caller guard ile düzeltildi. Boşta native MIDI+MSC kurulum /
> teardown ve125B/3-interface descriptor koşullu PASS;storage Init sınırı var.
> Aktif MSC job iptali sonraki iş;class-specific/power/task,1912B checked RAM /
> init,tam boot/storage/gerçek bariyer/timing açık. Üretim aynı/Off-Stop FAIL,
> M7 NO-GO;cihaza erişilmedi. STATUS.md ve MIDI-USB-COMPOSITE-5706.md güncel.

---

> Güncel28 Ekim:347 toplam/87 aday PASS. Reset/deinit sonrası ana bağlam
> bariyeri,ertelenmiş class init ve native EP0 yeniden kurulum emülasyonda
> koşullu testli. Gerçek class-parent bildirimi no-op sınırıdır;MSC/task /
> power/descriptor ve fiziksel iptal bariyeri açık. Üretim aynı/Off-Stop FAIL,
> M7 NO-GO;cihaza erişilmedi. Checked1816B RAM/init,boot/OOM/storage/timing
> kapıları sürer. Hardware test/yükleme önerisi yok. STATUS.md ve
> MIDI-USB-CONTROL-5706.md güncel.

---

> Güncel28 Ekim:325 toplam/87 aday PASS. CPU FIFO completion IRQ köprüsü
> yalnız sentetik register/RAM'de native yürür;test dışarıdan token vermez.
> Native reset/kontrol ve disconnect dönüşü tamamlanmadı;gerçek iptal bariyeri
> açık. Üretim aynı/Off-Stop FAIL,M7 NO-GO;cihaza erişilmedi. Hardware test
> veya yükleme önerisi yok. Checked1720B RAM/init,full boot/storage/NVIC/cache /
> timing kapıları sürer. STATUS.md ve MIDI-USB-IRQ-5706.md güncel.

---

> Güncel28 Ekim:306 toplam/87 aday PASS. USB iptal bariyeri yalnız sentetik
> MMIO + tagged-job bridge sözleşmesiyle testli;stok IRQ uyumu FAIL,gerçek
> DMA durması kanıtlanmadı. Üretim aynı/Off-Stop FAIL,M7 NO-GO;cihaza erişilmedi.
> Yeni session modülü üretim paketine eklenmedi. Checked1624B RAM/init,boot /
> storage/timing ve genel cancel-drain açık. STATUS.md ve
> MIDI-USB-SESSION-5706.md güncel. Hardware test/yükleme önerisi yok.

---

> Güncel28 Ekim:281 toplam/87 aday PASS. RX ownership/reset guard testli,
> fakat eski TX yanıtı reconnect'e taşınabiliyor;late RX DMA açık. Üretim
> aynı/Off-Stop FAIL,NO-GO.1496B checked RAM/init,boot/storage/IRQ kapıları
> sürer;cihaza erişilmedi. STATUS.md ve MIDI-USB-LIFECYCLE-5706.md güncel.

> Önceki:262 toplam/87 aday PASS. Ledger yalnız emülasyonda kabul edilmiş
> USB penceresinde full-capacity Clock/Stop ve sırayı korur. Private marker
> reset/flush/disconnect sahipliği,IRQ/RAM/boot/storage kapıları açık.
> Üretim aynı/Off-Stop FAIL,NO-GO;cihaza erişilmedi. STATUS.md ve
> MIDI-USB-LEDGER-5706.md öncelikli.

> Önceki:244 toplam/87 aday PASS. Note On/Stop sırası yalnız emülasyonda
> düzeltildi;kapasite doluluğunda Clock/Stop gecikmesi açık. Aynı üretim adayı
> Off/Stop kaybeder,NO-GO. RAM/init/boot/storage/IRQ kapıları sürer,cihaza
> erişilmedi. STATUS.md ve MIDI-USB-ORDER-5706.md öncelikli.

> Önceki:230 toplam/87 aday PASS. USB inquiry retry yalnız emülasyonda;genel
> Clock/Stop hizmeti ve Note On sırası FAIL. Üretim aynı ve Off/Stop kaybeder.
> Checked1432B RAM/boot/storage/IRQ kapıları açık,NO-GO. Cihaza erişilmedi.
> STATUS.md ve MIDI-USB-INQUIRY-RETRY-5706.md öncelikli.

> Önceki:213 toplam/87 aday PASS. Üst formatter rezervasyonu yalnız emülasyonda
> testlidir;native USB/DIN isteği tüketip retry yapmaz. Aynı aday Off/Stop
> kaybeder,NO-GO. Checked1260B RAM/boot/storage/IRQ kapıları açık;cihaza
> erişilmedi. STATUS.md ve MIDI-SYSEX-REQUEST-5706.md geçerli.

> Önceki:202 test (24 recovery+14 retry+11 bildirim deneyi)/87 aday PASS.
> SysEx kabul callback'i işlem sahibine yalnız emülasyonda bağlandı. Request
> geri basıncı ve üretim entegrasyonu açık;aynı aday Off/Stop kaybeder,NO-GO.
> Checked1256B RAM/boot/storage/IRQ kapıları açık;cihaza erişilmedi.
> STATUS.md ve MIDI-SYSEX-NOTIFICATION-5706.md geçerli;aşağısı tarihseldir.

> Önceki:191 test (24 recovery +14 retry deneysel)/87 aday regresyonu PASS.
> SysEx sahipli retry/erken üretici koruması yalnız emülasyondadır. Native
> callback ve full-slot yanıt politikası tamamlanmadı. Üretim aynı ve Off/Stop
> kaybeder; yükleme NO-GO. Checked1216B RAM/boot/storage/IRQ kapıları açık.
> Cihaza erişilmedi. STATUS.md ve MIDI-SYSEX-RETRY-PROTOTYPE-5706.md geçerli;
> aşağıdaki sayılar önceki kayıtlardır. Kurtarma planı yükleme yetkisi değildir.

> Önceki:177 test (24 deneysel)/87 aday regresyonu PASS. SysEx/recovery koruması
> yalnız emülasyondadır; aynı üretim adayı Off/Stop kaybeder. Donanım yüklemesi
> için NO-GO. Çağıran retry/RAM/boot/storage/IRQ kapıları açık. Cihaz erişilmedi.
> STATUS.md ilk bölümü geçerlidir; aşağıdaki sayılar tarihsel kayıttır.

> Önceki:166 test (13 deneysel)/87 aday regresyonu PASS. Off/Stop recovery
> yalnız emülasyonda çalışıyor; üretime eklenmedi. SysEx bypass/RAM açık; NO-GO.
> Fiziksel cihaz testi için hazır değildir. STATUS.md ilk bölümü önceliklidir.

---

> Güncel: ortak proje ve onaylı test migrasyonu tamamlandı.
> 101 regresyon ve35 packaged test PASS; bekleyen test onayı yok.
> Mod değişiminde dosya erişimi yok. Stok storage hatası onarılmış sayılmaz.
> Kalan3 GO engeli ve güncel hash için STATUS.md ilk bölümü geçerlidir. NO-GO.

---

> Ortak proje kapsamında banka ayrımı ve otomatik Load kaldırıldı.
> Mod değişimi dosya erişimi yapmaz. Eski Load engeli adaydan çıkarıldı.
> Stok storage hata riski onarılmadı. Tam test migrasyonu onay bekliyor.
> Güncel aday ve NO-GO kararı için STATUS.md ilk bölümü önceliklidir.

---

> Güncel: 26 Ekim 2026, Load/New continuation okuma öncesinde kapatıldı.
> Tüm raw proje baytları korunuyor; işlevsel Load ve boot kabul edilmedi.
> NO-GO;131 regresyon. STATUS.md ilk bölümü önceliklidir.
> Aşağıdaki bozulma deneyi koruma kaldırıldığında hâlâ geçerlidir.

---

# 26 Ekim 2026 — Kritik Load RAM bozulması / NO-GO

Kısmi Load hatasında canlı pattern baytının değişmesi emülasyonda yeniden üretildi.
Save karantinası kalıcılaştırmayı test edilen yollarda engeller; RAM rollback
çözülmedi. Bu aday cihaz testine hazır değildir. PROJECT-LOAD-ALIAS-RISK.md ve
STATUS.md ilk bölümü önceki değerlendirmelerin önündedir.

---

# Cihaz testi ve kurtarma

Bu paket cihaz erişimi yapmaz. Yerel Faz 1 adayı var, fakat 25 Ekim 2026 güvenlik denetimi sonucu **NO-GO**: cihaza yüklemeyin. Ayrıntı: [PHASE1-SAFETY-AUDIT.md](PHASE1-SAFETY-AUDIT.md). Brick ihtimali için güvenilir bir yüzde veremiyoruz; bootloader'ın mevcut olması her hatadan kurtulma garantisi değildir.

## İlk yüklemeden önce
Components'ta kurulu firmware'i kaydet; bootloader uyumluluğu gereksinimini ayrıca belirle. İçerikleri Components ile yedekle; SD kartın tamamını kart okuyucuyla kopyala. Yedeğin ikinci kopyasını bu çalışma klasörünün dışında tut. Denemelerde önemli proje kullanma. Güvenilir güç/USB kullan; güncelleme sürerken bağlantı kesme. Uploader, DAW ve MIDI monitor aynı port için yarışmamalı.

Patch yalnızca denetlenmiş application alanını hedeflemeli. Bootloader, flash option bytes, toplu flash silme veya debug unlock işlemi bu projenin normal akışı değildir. Uygulama kodu yazma alanı doğru olsa bile hatalı runtime kodu risk taşır. Projects sayfa kilidi uygulanmış olsa da aktif proje/RAM/Save kimliğinin mode geçişinde izolasyonu tamamlanmamıştır; normal projeler korunuyor varsayılmamalıdır.

## Yalnızca proje yükleme sorunu
Cihaz kapalıyken Shift + Clear basılı tutarak açmak, boş proje yükleyerek başlatır. Bu Novation'ın proje açılış sorunları için belgelendirdiği yöntemdir. Firmware onarımı veya kapsamlı fabrika reseti değildir.

## Uygulama firmware'i açılmıyorsa
1. Devam eden firmware yazımını kesme. Yazım tamamlandıktan/başarısızlığı kesinleştikten sonra cihazı kapat.
2. **Sample Rec + Sample + Note** basılıyken aç. Resmî destek sayfası 'Samples' yazabilir; Rhythm panelindeki Sample düğmesidir. Tracks'in Scales/Preset kombinasyonu kullanılmaz.
3. Novation Components'ta cihaz bootloader olarak algılanırsa ana sayfa/Updates içindeki **Reinstall firmware** yolunu kullan. Resmî firmware'i yeniden yükle.
4. Menü sunulmuyorsa veya cihaz algılanmıyorsa başka USB portu/kablo, Windows Novation sürücüsü ve Components standalone ile bağlantıyı kontrol et. Devam ediyorsa Novation desteğine başvur; rastgele erase/unlock deneme.

Normal bootloader çıkışı Play düğmesidir; bozuk uygulama için Play tek başına firmware'i onarmaz. USB kablosunu çıkarmak dahili bataryalı cihazın mutlaka kapandığı anlamına gelmez. Donmuş cihaz için doğrulanmamış uzun-basış süresi tahmin etmeyin; resmî desteğe danışın.

Bootloader üzerinden reinstall, veri bozulmasını otomatik geri almaz. Modlanmış sürümün build/transport kimliği Components'ın sunacağı işlemleri etkileyebilir; bu yolun her custom build için çalışacağı garanti değildir. İlk patch tasarımında stock'a dönüş prosedürü doğrulanmalı. Bu paket uploader içermediğinden yerel bir alternatif uploader'ın doğrulanmış olduğu varsayılmaz.

## Resmî kaynaklar — 24 Ekim 2026'da kontrol edildi
- https://support.novationmusic.com/hc/en-gb/articles/360002211360-Updating-firmware-using-Novation-Components
- https://userguides.novationmusic.com/hc/en-gb/articles/25494352755730-Circuit-Rhythm-appendix
- https://components.novationmusic.com/

Dokümanların kendileri paketlenmedi. Novation appendix'i bootloader için destek yönergesini önerir; genel resmî güncelleme makalesi yukarıdaki kombinasyonu ve reinstall yolunu açıklar.
