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

> Güncel31 Ekim /Canlı parametreler — İki runtime modu,8 track ve iki auxiliary
> sayfada microstep/probability/silme-yeniden oluşturma testi eklendi. Native
> PRNG yalnız okunur;gerçek player On ve MIDI Off denetlenir. Güncel koşu ve
> sayım STATUS.md'de. Firmware c9a87a9d… aynı;M7 NO-GO. Sonraki:partial
> Load/short-read ve alias/taint yolu. Alt raporlar tarihsel sonuçlardır.

---

> Güncel31 Ekim /Gate expiry ve tie — Aynı/farklı pitch ve retrigger için
> 3 sentetik test/80 alt durum PASS. Native UI Gate1/6/95/96 sınır koşusu ve
> güncel sayım STATUS.md'de. Tie bitini native UI/Load ile1 yapan yol henüz
> kanıtlanmadı. Firmware c9a87a9d… aynı;M7 NO-GO. Sonraki:çalarken
> microstep/probability. Alt raporlar tarihsel milestone sonuçlarıdır.

---

> Güncel31 Ekim /64 stok ses Stop — Yoğun normal Stop'un gereksiz MIDI
> quarantine nedeni bulundu;her stock player flush'ından sonra tek native
> output servisi eklendi. Yeni aday c9a87a9d… /CRC BEB0D013;149 temel test,
> 6 ölçüt ve native iki-mod IRQ/32-adım regresyonu PASS. Dört64-ses senaryosu
> ve güncel sayım STATUS.md'de. M7 NO-GO;fiziksel cihaz erişimi yok.
> Sonraki:Gate tie/sustain kapanışı. Alt raporlar eski SHA'lara aittir.

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

> Güncel28 Ekim:347 toplam/87 aday PASS. Native USB reset/enum,EP0 address /
> configuration ve main-context bariyer sonrası MIDI class kurulumu koşullu
> PASS. Bootstrap release/global RX flush/SOF partial yolları ayrıldı;
> RX tek64B MTU,66B kapasitede pause/rearm testli. Gerçek parent callback /
> composite MSC sonraki iş;power/descriptor/task ve fiziksel bariyer açık.
>1816B checked RAM/init,boot/storage/timing kapıları sürer. Üretim aynı,
> Off-Stop FAIL,M7 NO-GO. STATUS.md ve MIDI-USB-CONTROL-5706.md öncelikli.

---

> Güncel28 Ekim:325 toplam/87 aday PASS. Stok HAL submit/FIFO/IRQ/callback
> zinciri artık testten token olmadan,CPU FIFO modunda koşullu PASS.
> Reset/kontrol IRQ ve disconnect recovery FAIL/unsupported;gerçek iptal
> bariyeri ve stale hardware XFRC ayrımı açık. Sonraki iş native reset /
> deconfigure/reconfigure zincirini close/barrier/resume'a bağlamak.
>1720B RAM/init,boot/storage/NVIC/cache/timing kapıları açık. Üretim aynı,
> Off-Stop FAIL,M7 NO-GO. STATUS.md ve MIDI-USB-IRQ-5706.md öncelikli.

---

> Güncel28 Ekim:306 toplam/87 aday PASS. Yazılım sahipleri boşken eski USB TX
> iptali ve eski tagged callback reddi sentetik MMIO modelinde PASS. Stok IRQ
> untagged olduğundan uyum FAIL;gerçek geç DMA iptali NOT_ESTABLISHED.
> Sonraki iş native IRQ/reset/disconnect zinciri ve immutable job bridge.
> Shared-reader/RX-debt cancel-drain,checked1624B RAM/init,boot/storage/timing
> kapıları açık. Üretim aynı/Off-Stop FAIL,M7 NO-GO. STATUS.md ve
> MIDI-USB-SESSION-5706.md öncelikli;aşağısı tarihseldir.

---

> Güncel28 Ekim:281 toplam/87 aday PASS. RX native gate'leri ve boşta reset /
> close/resume testli;stok constructor prefix RX1057B ring'i doğruladı.
> Aktif TX disconnect/session safety FAIL,late RX DMA açık. Sonraki iş ortak
> endpoint cancel/drain+generation sahipliği. Üretim aynı,M7 NO-GO.
> STATUS.md ve MIDI-USB-LIFECYCLE-5706.md öncelikli.

> Önceki:262 toplam/87 aday PASS. Ledger prototipi,dolu sayaçta kabul edilmiş
> USB kayıtlarının nota/Clock/Stop hizmetini ve sorgu sahipliğini korur.
> Üretim aynı,M7 NO-GO. Sonraki iş native RX consumer/reset/flush/disconnect
> yaşam döngüsü. Host pre-admission latency/gerçek IRQ-RAM kapıları açık.
> STATUS.md ve MIDI-USB-LEDGER-5706.md öncelikli.

> Önceki:244 toplam/87 aday PASS. Ordered USB varyantında Note On/Stop sırası
> düzeltildi;ek RAM yok. Tam inquiry kapasitesi+9. başlangıç arkasındaki
> Clock/Stop gecikmesi açık. Üretim aynı,M7 NO-GO. Sonraki iş bu dolulukta
> sırayı bozmayan gecikme/geri basınç çözümü. STATUS.md ve MIDI-USB-ORDER-5706.md.

> Önceki:230 toplam/87 aday PASS. USB inquiry otomatik retry yalnız emülasyonda
> testli;sonraki buffer'daki Clock/Stop ve deferred Note On sırası FAIL.
> Üretim aynı,M7 NO-GO. Sonraki iş inquiry yükümlülüğünü müzikal RX cursor'undan
> ayıran bounded admission katmanı. STATUS.md ve MIDI-USB-INQUIRY-RETRY-5706.md.

> Önceki:213 toplam/87 aday PASS. Beş üst SysEx formatter için erken kapasite
> rezervasyonu testli;native USB/DIN consumed-request retry FAIL. Sonraki iş
> USB RX inquiry sahipliği/Clock-Stop hizmeti. Üretim aynı,M7 NO-GO;
> checked1260B RAM/boot/storage/IRQ kapıları açık. STATUS.md ve
> MIDI-SYSEX-REQUEST-5706.md öncelikli;aşağısı tarihseldir.

> Önceki:202 test (24 recovery+14 retry+11 bildirim deneyi)/87 aday PASS.
> Native kabul bildirimi senkron event0;sahipli event/owner kopyası ve callback
> reader/reentry Unicorn'da doğrulandı. Sonraki iş formatter mutasyonundan
> önce request kapasite rezervasyonu/geri basınç. Üretim aynı,M7 NO-GO.
> Checked1256B RAM/boot/storage/IRQ kapıları açık. STATUS.md ve
> MIDI-SYSEX-NOTIFICATION-5706.md öncelikli;aşağısı tarihseldir.

> Önceki:191 test (24 recovery +14 retry deneysel)/87 aday regresyonu PASS.
> 12 SysEx çağıranı, tek sahipli360B payload ve erken formatter guard'ları
> Unicorn'da testli. Full-slot yanıt kaybı ve native completion açık; üretim
> aynı, M7 NO-GO. Sonraki iş router+20/468EC callback sahipliği yaşam döngüsü.
> Checked1216B RAM/boot/storage/IRQ kapıları açık. STATUS.md ve
> MIDI-SYSEX-RETRY-PROTOTYPE-5706.md öncelikli; aşağısı tarihseldir.

> Önceki:177 test (24 deneysel)/87 aday regresyonu PASS. SysEx bypass Unicorn
> prototipinde kapandı; üretim aynı, M7 NO-GO. Sıradaki iş298B8 çağıranlarının
> bounded retry/kısmi fanout sözleşmesi. RAM/boot/storage/IRQ kapıları açık.
> STATUS.md ve MIDI-RECOVERY-PROTOTYPE-5706.md öncelikli; aşağısı tarihseldir.

> Önceki:166 test (13 deneysel)/87 aday regresyonu PASS. Off/Stop recovery
> prototipi çalışıyor; üretime eklenmedi. Bulk SysEx bypass ve checked RAM açık.
> M7 NO-GO; sıradaki iş40232/4028C girişleri. MIDI-RECOVERY-PROTOTYPE-5706.md.

> 26 Ekim 2026: M6 ortak proje modeline geçti. Bağımsız banka ve Packs kilidi
> kapsamdan çıkarıldı; eski satırlar tarihsel. M7 NO-GO; STATUS.md öncelikli.

# Geliştirme Sırası ve Kilometre Taşları

**25 Ekim 2026 denetimi: M7 donanım çıkışı NO-GO.** Host kontrollerinin geçmesi tam kabul değildir; aktif proje/banka geçişi ve sistem bütünleştirme kanıtları açık. Öncelik `PHASE1-SAFETY-AUDIT.md` ve `STATUS.md` dosyalarının güncel bölümleridir.

Geliştirmenin %95'i bilgisayar üzerindeki Unicorn ARM Cortex-M emülatöründe doğrulanır. Fiziksel cihaza her adımda yükleme yapılmaz; yalnızca emülatörde tamamlanmış ve tüm testlerden geçmiş toplu paketler cihazda sınanır.

| Aşama | İş | Durum / Çıkış Ölçütü |
|---|---|---|
| **M0** | Ortam, hash, baseline, yerel Git | **TAMAMLANDI** — Beklenen sonuçlar tekrar üretildi; donanım erişimi yok |
| **M1** | Pad/view/edit/notify/LED ve Projects yollarını incele | **TAMAMLANDI** — Kod ve bayt kanıtlı adres haritası (`docs/UI-TRACE-5706.md`) |
| **M2** | Güvenli Patcher aracı ve tek baytlık kanıt yaması | **TAMAMLANDI** — `scripts/patch_firmware.py` ve 32 testlik Unicorn doğrulaması |
| **M3** | Genişletilmiş Patcher (`Code Cave` `0x0806A570+`) ve Güvenli Heap Durum Bloğu (`0x2004F660`) | **TAMAMLANDI** — Patcher'ın `0x0806A570..0x08080000` arasına Thumb-2 kod eklemesi ve `c_seq_state` RAM bloğu (`46 test PASS`) |
| **M4** | Mod Geçişi + 32-Pad Step Yönlendirmesi + Sayfa Kilidi + Sahiplik Temizliği | `grid_mode == 0`'da 32 pad -> Step View (`step == pad`), `grid_mode != 0`'da `1–16` tuşu aktif; makine kodu Unicorn'da doğrulandı |
| **M5** | 32-Adım LED Compositor Makine Kodu Yaması | `0x0804DD1C` kancasıyla `grid_mode == 0`'da 32 adım LED + Playhead birleştirme; diğer modlarda alt pad korunumu |
| **M6** | Bağımsız 32 Sequencer Projesi (`[proj_view + 0x36]`) + Packs Kilidi + Sample Susturma (MIDI-Only) | Normal modda Proje 1–32 (`sayfa 0`), Sequencer modunda Proje 33–64 (`sayfa 1`), Packs kapalı, dahili sample tetikleme susturulmuş |
| **M7** | **1. Gerçek Cihaz Testi Hazırlığı ve Doğrulaması (Faz 1 Paketi)** | M3–M6 birleşik `.syx` üretimi, tam Unicorn regresyon testi, SHA-256/CRC-32 manifesti ve kullanıcı onayıyla ilk fiziksel cihaz testi |
| **M8** | Faz 2: Root Nota + Knob ile Akor/Triad Üretici ve Hızlı Uzunluk Kısayolu | Akor tablosu, Note On/Off ses takibi ve 2. gerçek cihaz testi |

## Temel Kurallar
- **64 adım kapsam dışıdır:** Tüm geliştirmeler stok 32 adım (`0..31`) sınırları içinde kalır.
- **Emülatör Öncelikli Doğrulama:** Hiçbir yama cihaza yüklenmeden önce Unicorn üzerinde gerçek makine koduyla test edilmezse "hazır" kabul edilmez.
- **Kurtarma Hazırlığı:** M7'deki ilk fiziksel cihaz yüklemesinden önce `docs/RECOVERY.md` adımları ve proje yedekleri kontrol edilir.
