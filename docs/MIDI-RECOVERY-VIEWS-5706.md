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

# Native Velocity/Gate görünüm testi — 5706

30 Ekim 2026. Emülasyon kanıtıdır; fiziksel cihaz veya port erişimi yoktur.
Güncel sonuçlar ve sonraki görev `STATUS.md` içindedir. M7 NO-GO.

## Giriş ve nesneler

Resetten oluşturulan controller ve grid kullanılır. Velocity button10,
Gate button11, `1–16` button21 ile açılır. Native `3E2D8` görünüm2/3 eşlemesini,
`3DC86→controller+28→4B8C4` sayfa girişini sağlar. Sayfa durumu gerçek Step View
`+60` store'undan native aktif bank seçimiyle okunur; host'ta yazılmaz.

Alt görünümler grid+9C+4*track ve grid+BC+4*track adreslerinden çözülür.
Native press işlevleri sırasıyla `56ABA` ve `56D54`'tür. Her alt pad için
gerçek callback pointer'ı, alıcı nesne ve yerel pad0..15 CODE hook'uyla izlenir.
Parametre işlevleri ve observer'ların `56A00..56F80` aralığı stock ile aynı
baytlardadır. Callback sonucu veya terminal instruction stub'ı kullanılmaz.

İlk keşifte page için16/17 tahmini yanlıştı; doğru giriş21 statik dispatch ve
native store değişimiyle bulundu. Keşif ayrıca kapsam dışı Play girişine
ulaştığı için ana kanıt olarak kullanılmaz. Kanonik test resetten yeniden
başlar ve yalnız track, görünüm, sayfa, mod ve pad girişlerini kullanır.

İlk ikinci-sayfa isteği raw veriyi değiştirmeyebilir varsayımı da yanlıştı:
stock `4BA82..4BA98`, başlangıçtaki16-step pattern'in end baytını15→31 yapar.
Test yalnız `raw+2E4+track*5140+100` adresindeki bu tek bayt değişimine izin
verir; sonraki sayfa geçişleri raw'u korur. Bu stock uzunluk davranışı custom
bir kısayol eklenmesi değildir. Pattern Settings RAM'i host'ta hazırlanmaz.

## Sınanan sözleşme

Sekiz track × Normal/Sequencer × Velocity/Gate × iki sayfa birlikte sınanır.
Her sayfadaki16 üst pad'in C0 ve bit3 sahipliği beklenen adıma bağlanır:
0..15 veya16..31. Toplam1024 pad/adım eşlemesi vardır. Her bırakma sonunda
canlı sahiplik boşalır; raw verideki değişiklik kendi sekiz baytlık adımıyla
sınırlanır.

Her sayfanın ilk ve son adımında alt16 pad gerçek parametreleri düzenler.
Toplam128 parametre senaryosu şunları içerir:

- Velocity: 8,16,…,120,127; en üst pad127'de doyar.
- Gate: 6,12,…,96 tick. Son pad tekrarlarında95,94,93,92,91,96 döngüsü;
  altı tick'lik adımın kesirli değerleri ve sonraki tam değer kontrol edilir.
- Her basışın raw değişimi yalnız hedef adımın8B aralığında kalır.
- Gerçek `4DD1C` compositor çağrısından sonra alt32B LED alanı native alt
  görünüm tamponuyla eşleşir. Düşük/yüksek parametre görüntüleri farklıdır.

Gate boş adıma yazmaz: `5E71C` aktif adım baytını kontrol eder. Üst pad
eşleme testi adımı kapatabildiği için Gate senaryosu önce Velocity görünümüne
girip gerçek pad girişiyle adımı oluşturur. Test bunu RAM seed'iyle aşmaz.
Başlatılan ilk kanonik koşu bu kurulum düzeltilmeden önce kesildi; kesik log
saklanır. Tam koşu güncel helper ile resetten tekrarlanır.

Main sınırındaki callback adapter'ı CPU context'ini dönüşte korur; firmware
RAM'i geri sarılmaz. Aynı yaşam süresinde track, görünüm, sayfa ve mod
değişimleri yürür. Her adımın değişimi projenin169092B raw alanıyla
karşılaştırılır. Metadata, heap, allocation ve NOR mutation sayıları izlenir.

Her16 UI girdisinden sonra ve mod commit'inden önce gerçek native Main turu
çalışır. Aksi halde binlerce callback, gerçek output consumer çalışmadan
birikir; ilk çok-track koşusu guard tarafından reddedildi. Bu karşı örnek ayrı
saklanır. Hiçbir kuyruk veya sticky güvenlik bayrağı host'ta temizlenmez.
Main için en fazla1024 açık `802F=000000` girdisi tanımlıdır; kullanılanlar
raporda tek tek sayılır. Varsayılan veya tükenmiş SPI yanıtı yine strict'tir.
Bu girdiler gerçek DSP yanıtı veya geçen zaman kanıtı değildir.

Main tek başına da yeterli değildi: UART FIFO'ları donanım TXE interrupt'ı
gelmeden dolu kalıyordu. Bu koşu1886'ncı UI girdisinde TX fault ile durdu.
Karşı örnekte `c_midi_tx_overflow` gerçek `40228` enqueue-failure dalından
çağrıldı; context/active/TX baytları `000001` oldu. Bu bayrak temizlenmedi.

Yeni sınırlı UART peer, native boot'un iki `68C84` driver'ından USART1/2
register bağlarını bulur. Vector53/54 ve native646FC/64702→26042 pin'lenir.
CR1.TXEIE açıkken yalnız ISR.TXE girdisi verilir; native IRQ/FPU frame yolu
kendi FIFO'sunu tüketir ve TDR+28'e yazar. FIFO boşalınca native kod TXEIE'yi
kapatır. Bir serviste port başına en fazla65 IRQ, toplam131072 açık TXE
kredisi vardır. Native kuyruk/cursor, handler veya dönüş değeri host'ta
değiştirilmez. TDR yazıları scoped MMIO hook'uyla kaydedilir; global write
hook'u veya write callback içinde CPU register okuması yoktur.

UART peer yalnız TXE girdisini modeller. RX, hata, gerçek NVIC pending /
öncelik, baud süresi, pin/hat ve fiziksel alıcı kanıtı değildir. Çıkan baytlar
emülasyondaki register yazılarıdır. Bu katman üretim firmware'ine eklenmez.

## Paket ve kapsam sınırları

Firmware değişmedi:

- SYX SHA256: `afbab4f2bb30b955aa369f9f2cdf062235b04c3aaf915e30fa7a8559fda26f64`
- Image SHA256: `5fa9e337ede28176f485911f43eedc63e5091e0a8d686901dd36b28a6947e8cd`
- MPEG2 CRC `114DA352`;42 patch, stock'a göre7540 değişen bayt.
- Stock SHA256 `11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf`.

Yeni test, derlenmiş kaynak image'ının bu SYX image'ıyla aynı olduğunu da
doğrular. Önceki142 paket testi aynı firmware'e aittir; bu oturumda tüm paket
kümesinin yeniden çalıştırıldığı iddia edilmez. Genel verifier yeni native
testi de içerecek şekilde genişletilir.

LED RAM karşılaştırması gerçek LED taraması/renk/parlaklık ölçümü değildir.
GPIO/input kuyruğu, geçen zaman, tüm timer/NVIC/interrupt nesting, harici
MIDI/USB/MSC/power ve fiziksel medya kapsam dışındaki kanıt sınırlarıdır.
Sonlu DSP mailbox girdileri, sentetik NOR/ADC/USB, disabled DWT ve non-nested
FPU modeli aynıdır. Diğer görünümler, playhead ve stock storage hata riskleri
bu testle kapanmış sayılmaz. Tie davranışı ayrıca uçtan uca sınanmalıdır.

## Tekrar üretim

`.venv\Scripts\python.exe` kullanılır; `-O` yoktur:

- `scripts/probe_recovery_views.py logs/recovery-native-views-20261030/probe`
- `scripts/audit_recovery_candidate.py logs/recovery-native-views-20261030/audit`
- `$env:PYTHONPATH='scripts;src;tests'` ardından `-m unittest
  test_step_routing test_ui_contracts test_projects_and_mode -v`.

Probe, yeni native unittest'i bir kez doğrudan paket image'ıyla çalıştırır ve
sonucunu JSON olarak kaydeder; ayrı bir başarılı koşu gibi iki kez sayılmaz.
Başarıda da M7 NO-GO nedeniyle uygulama düzeyinde exit2 döner. Before/after,
diff, hash ve kesik/keşif kayıtları `logs/recovery-native-views-20261030` içindedir.
