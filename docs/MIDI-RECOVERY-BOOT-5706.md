# Recovery adayı: ilk açılış ve allocator hatası — 5706

29 Ekim 2026. **M7 NO-GO.** Bu kanıt reset vektöründen native main girişine
kadar olan pencereyi kapsar. Main, RTOS, görev yığınları ve tam açılış değildir.
Cihaza veya fiziksel MIDI/USB API'sine erişilmedi.

## Gerçek başlangıç sırası

Güncel SYX doğrudan çözülüp Unicorn'a yerleştirilir. RAM başlangıçta kirletilir;
heap, vtable, nesne veya callback hazırlanmaz, firmware komutu değiştirilmez.
RCC ve SCS adresleri pasif RAM olarak eşlenir. Gerçek saat/PLL, NVIC, watchdog,
interrupt veya elapsed-time modeli yoktur.

| Kenar | Gözlenen davranış |
| --- | --- |
| Vektör SP / Reset | `20050000` / `08069589` |
| Reset → runtime | Native `23F50`, `69764`, `68C2C`, `68E14` yürür |
| `68A54` record walker | RAM hazırlığı **ve** static kurucuları çalıştırır |
| Record `68C50` → `22C5F` | Native zero-initialization handler |
| Record `68C68` → `669DD` | Native sıkıştırılmış veri açılımı |
| Record `68C78` → `68DDD` | Native static initializer listesi |
| İlk allocator girişi | Size64, current`20006F60`, stock limit`2004F760` |
| İlk başarılı bump öncesi | Limit`2004F320`;1088B temiz, iki magic ve varsayılanlar yayımlanmış |
| Native main `25688` girişi | 10 tahsis, current`20007B90`;stock adres/boyut sırası aynı |

Native MIDI/MSC root ve endpoint nesneleri, MIDI RX descriptor/ring ve ilk heap
verisi stock başlangıcıyla byte olarak karşılaştırılır. `0`, `A5`, `FF` RAM
dolguları ve geçerli eski magic/aktif journal kalıntısı testlidir. Eski limit ve
current de resetin veri hazırlığıyla yenilenir;önceki magic init'i atlatamaz.
İlk clear ve publication yazıları PRIMASK1 altında gerçekleşir.

Bu pencerede en düşük SP`2004FF60`, maksimum stack160B;reserved alanın üst
sınırı`2004F760` ile arada2048B vardır. Bu değer main/exception/nested IRQ/task
stack sınırı olarak kullanılamaz. Önceki fixture current`2004EA98` değerinin
tam boot'tan geldiği bu çalışma ile kanıtlanmış değildir.

## Düzeltilen hata

Eski recovery SYX `4c0180e1...` allocator taşmasında`FFFFFFFF` döndürüyordu.
Native `25278` new yalnızca sıfırı başarısız sayar. Gerçek endpoint kurucusu
`6668C` üzerinden bu değer başka kurucuya ulaşıp `25ADA`'da geçersiz adrese
yazdırır. “-1 dönüyor, dolayısıyla çağıran güvenli” varsayımı yanlıştı.
Her çağırana genel bir NULL dönüşü vermek de unchecked kullanımları çözmez.

Recovery profili artık başarısız reservation, alignment/address carry veya
heap sınırı aşımında çağırana dönmez. `0806A654`'te `cpsid i`, ardından
`0806A656`'da self-branch vardır (`72b6fee7`). Fault ucunda RAM/MMIO/flash
yazısı, reset talebi, BKPT veya başka çağrı yoktur. PRIMASK1 kalır;yarım
kurulmuş nesnelerle interrupt/main devam edemez. **Bu terminal hatadır:**
normal çalışmaya dönmek yeniden başlatma gerektirir;watchdog davranışı
modellenmemiştir. Bellek tükenirken kesintisiz çalma veya graceful recovery
vaadi değildir. Bu sonsuz döngü normal bounded kritik bölge olarak sayılmaz.

Native endpoint initializer'ın altı ayrı tahsisinde zorlanan OOM, alignment
ve address overflow, beklenmeyen limit ve reserved alana taşan current testli.
Geçersiz pointer kullanımı yoktur;heap reserved alanı geçmez ve state korunur.
Başarılı son4B tahsisi maskeyi, SP'yi ve callee-saved register'ları korur.
Default/legacy generator ve eski sequencer SYX byte olarak aynıdır;bu
düzeltmenin seçildiği profil yalnızca güncel recovery adayıdır.

## Sonuç ve sınır

- 8 yeni test;103 odaklı ve74 packaged test +6 sınırlı Faz1 ölçütü PASS.
- Exact eski/yeni SYX: `FFFFFFFF` geçersiz yazımı → terminal fault,geçersiz
  erişim yok. Karşılaştırma yalnız sentinel testinden oluşmaz;native caller yürür.
- Native USB IRQ/reset Off/Stop ve eski burst kaybı probe'ları PASS kalır.
- Strict transport/CRC/vektör/range/CFG/ABI ve legacy audit PASS.
- İlk allocator normal yolu1157 komut,1149 maskeli;elapsed timing değildir.
  Core/glue/accepted guard aynı;30 normal maskeli yol,max41 komut aynı.
- Discovery592;tam592 bu turda koşulmadı. Önceki529/98 kayıtları korunur;
  bu sayılar toplanmaz ve tüm eski testler güncel recovery SYX'e ait değildir.

**Sonraki tek iş:** Native main `25688` sonrasındaki açılış tahsislerini gerçek
router/port ve görev kurulumu boyunca izlemek;son heap high-water ve görev /
exception stack sınırlarını kanıtlamak. Sonra Faz1 UI/transport/receiver ve
RX/MSC/power/storage etkilerinin uçtan uca kapıları kalır. Bunlar bitmeden M7
fiziksel test paketi için GO verilmez.

Komutlar ve güncel hash'ler [STATUS.md](STATUS.md) içindedir. Exact diff,
source pin,donmuş önceki/sonraki SYX ve kanıtlar:
`logs/recovery-boot-20261029`. Probe/verifier exit2 NO-GO'yu korur.
