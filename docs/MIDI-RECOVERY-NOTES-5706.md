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

# Native Note1/7 — 31 Ekim 2026

Note1↔7 geçişi, eklediğimiz cleanup kodunda gerçek bir stuck-note hatasını
ortaya çıkardı. Güncel sonuç ve hash paketi `docs/STATUS.md` içindedir.
Bu belge kanıtın mekanizmasını ve sınırlarını açıklar. M7 NO-GO;
fiziksel cihaz veya port kullanılmadı.

## Hata ve düzeltme

Compact Note1 alt16 pad ile expanded Note7 alt16 pad aynı NoteView nesnesini
ve aynı yerel pad numaralarını kullanır. Stock4DAAC bu yüzden o yarıdaki
basılı notayı görünüm değişirken korur. Nota, NoteView+54'teki32 baytlık
sahiplik dizisinde kalır. Grid+228 fiziksel pad maskesi de korunmalıdır:
stock4D7DE release dispatcher'ı ilgili bit yoksa pad bırakma olayını atlar.

Önceki custom cleanup tüm StepView B8/C0/bit3 sahiplerini temizliyor,
stock4DAAC'ı çağırıyor, ardından grid+228'i koşulsuz sıfırlıyordu. Note1'de
pad24 basılıyken Note7'ye geçişte raw nota72 dizide kaldı ama fiziksel maske
sıfır oldu. Shift+SampleRec bu durumda yanlışlıkla kabul edildi. Pad24
bırakılınca native release çalışmadı ve nota dizide asılı kaldı.
Negatif kayıt: `logs/recovery-native-notes-20261031/before-note-held-bug.json`.

`src/seq_Patch.py::emit_grid_mode_cleanup` artık eski görünümden fiziksel
StepView pad maskesini çıkarır. Stock4DC50'ye göre mod0/1/2/3/5/6 üst16
pad'i StepView'a yollar. Sequencer mod0 tüm32 pad'i adım olarak kullanır.
Diğer eski görünümlerde custom step maskesi0'dır. Tüm StepView B8/C0/bit3
temizliği devam eder. Stock4DAAC eski/yeni alt görünümlerin değişen nota
sahiplerini kendi bırakır; çağrıdan sonra yalnız custom step maskesinin
fiziksel bitleri silinir. Böylece stock'un koruduğu Note/Sample sahipleri
release dispatcher ve mod guard tarafından görünür kalır.

Her iki hook'ta R2 eski grid mode'dur; beş stok argüman korunur.
Önceden de saklanan R8 geçici maske için kullanılır;40B frame ve1088B RAM
rezervasyonu büyümez. Callback dönüş değeri0 kalır. Native Note kodu
0805D7A0..0805E380 stokla bayt bayt aynıdır.

## Test katmanları

- `test_note_cleanup.py`: sentetik RAM, stock4DAAC gözlenen leaf sınırıdır.
  Eski görünüm0..10 ×Normal/Sequencer için yalnız doğru fiziksel step
  bitlerinin temizlendiğini, GPR/SP sözleşmesini sınar. Önceki aday22
  alt durumun21'inde başarısızdı; düzeltme sonrası hedefli60 test PASS.
- `test_recovery_notes.py`: yeni adayın resetten kurduğu gerçek nesneler,
  controller vtable pad/button callback'leri ve native Main/IRQ servisleri.
  Başlangıç nesnesi, keymap, sayfa, proje veya sahiplik RAM'i seed edilmez.
  Ayrıntılı sayı ve sonuç, biten koşunun `probe/report.json` dosyasındadır.
- Paket testi kaynak codegen'inin SYX ile aynı image ürettiğini doğrular.
  Velocity/Gate matrisi de düzeltme sonrası aynı SYX üzerinde yeniden sınanır.
  `verify_recovery_candidate.py --core-only` bu iki uzun UI matrisini açıkça
  hariç tutarak diğer paket testlerini ve altı sınırlı Faz1 ölçütünü çalıştırır;
  varsayılan komut tümünü içerir. Ayrı koşuların kapsamları raporda belirtilir.

Native Note matrisi8 track ×Normal/Sequencer ×iki sayfadır. Note1'de üst16
pad'in doğru adımı tuttuğu, uç adımlarda stock pitch writer/same-pitch
toggle, Note1 alt16 ve Note7 tüm32 klavye pad'i, blank tuşlar, iki görünümün
64B LED RAM bileşimi ve1↔7 sırasında tutulan notanın gerçek release'i sınanır.
Tutulan nota mod geçişini reddetmelidir; bırakıldıktan sonra NoteView dizisi
ve fiziksel maske boş kalmalıdır. Klavye MIDI çıktısı native UART53/54 TDR
yazılarından Note On/Off olarak karşılaştırılır.
Track/değişen görünüm ve Note7 üst pad'inin Note1'e geçişte iptal yolları da
aynı native release'i tek kez üretmelidir. Note7'de sayfa tuşu iki yönde
çalıştırılır; yalnız ortak sayfa store'una bakmakla yetinilmez.

## Stok davranışları ve model sınırları

Klavye notası keymap+8 tablosundan, `(pad+(5-window)*stride*8)&255` indeksiyle
gelir.0 girişleri boş pad'dir. Varsayılan window3/stride2'de pad24 raw72
üretir; dış MIDI pitch60'tır. Track numarası varsayılan MIDI kanalını seçer.
Adım basılı değilken geçerli klavye notası seçimi stok5D85E üzerinden varsayılan
nota store'unu günceller; projede yalnız `raw+28CF4+track` baytı değişir.
İlk testin sıfır raw değişimi varsayımı bu yüzden yanlıştı; negatif koşu ve RAM
kaydı korunur. Test bu tek baytı ve store değerini her tuşta doğrular; boş
pad varsayılan notayı değiştirmez. İlk Note görünümüne giriş de stok pitch-mode
alanını değiştirebilir; bunun raw'u her koşulda koruduğu varsayılmaz.
İlk ikinci-sayfa isteği de stok pattern
end15→31 uzatması yapabilir. Mod commit'inin raw/metadata koruması ayrı
sınanır. Basılı adıma pitch yazıları yalnız hedef adımın8B alanında kalmalıdır.

Native Main her16 controller girdisinde ve sınırlı kuyruk boşaltma noktalarında
çalışır. Stock2A37E ring sayımı yalnız gözlem için RAM'den okunur; consumer
indeksleri, FIFO ve sticky fault'lar host'ta değiştirilmez. Sonlu açık802F
yanıtları ve UART TXE kredileri native tüketiciyi ilerletir. Bunlar gerçek
DSP yanıtı, UART hat teslimi, baud/timer/NVIC veya geçen zaman kanıtı değildir.

LED RAM eşleşmesi fiziksel LED ölçümü değildir. Controller callback girdisi
GPIO scan veya gerçek input kuyruğu değildir. NOR/ADC/USB sınır modelleri,
disabled DWT ve non-nested FPU çerçevesi varsayımları sürer. Proje I/O'suz,
ek tahsissiz bu workload'un heap payı genel en kötü durum yeterliliği değildir.
Tam transport/playhead, USB RX/MSC/power, diğer görünümler ve storage riskleri
açıktır. Akor/uzunluk kısayolu Faz2'dir.
