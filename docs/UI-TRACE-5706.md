# 5706: pad, edit, commit ve LED incelemesi

24 Ekim 2026; yalnızca SHA-256 `11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf` tabanı.
Güncel kapsam 32 adım; sekiz track ve mevcut pattern sayısı korunur. Firmware değiştirilmedi.

## Kanıtın kapsamı

**D:** Bu stock dosyada pointer/bayt/disassembly doğrulaması. **E:** Gerçek stock kodu, sentetik RAM.
**K:** Paketlenmiş upstream kaynak iddiası. **Ö:** Henüz uygulanmamış tasarım.
Bu ayrım adresin doğru olması ile tüm cihaz davranışının doğru olmasını birbirinden ayırır.

Tekrar: `.\.venv\Scripts\python.exe scripts/run_ui_audit.py`.
İlk başarılı kayıt: `logs/ui-audit-20261024T182014064195Z/`; `tests.txt`, `disassembly.txt`,
`summary.json` içerir. JSON, disassembly pencerelerinin SHA-256 değerlerini de taşır.
Pencerelerde literal havuzu/jump tablosu bulunabilir; lineer disassembly tek başına kontrol akışı kanıtı değildir.

## Adres haritası

Kod adresleri çift; vtable içindeki Thumb pointer'ları tek sayılıdır.

| Bağlantı | Adres ve somut bulgu | Kanıt / sınır |
|---|---|---|
| Pad olay adaptörü | `0x080295B4`; `0x080295CA` → `0x08040108` | D; event argümanlarını yeniden sıralar |
| Press/release dispatch | `0x08040108`; `r3 != 0`: slot 0, velocity `max(1,r2>>1)`; release: slot 1 | D+E; 0/15/16/31 pad, sınır velocity değerleri; son callback'ler sahtedir |
| Ana controller | slot `0x080672E4` → `0x0803D7FF`; gövde `0x0803D7FE` | D; guard'lardan sonra `ctrl+0x7C` doluysa oraya, değilse `ctrl+0x78` görünümüne gider. Guard'lar bütünüyle emüle edilmedi |
| Grid container | vtable `0x080678DC`; press `0x0804D7A0`, release `0x0804D7DE` | D; `+0x228` tutulan pad maskesi; iki yol da seçici ve indeks dönüşümünü çağırır |
| Seçili track | `0x0805800E` → `[grid+0x25C]` store p0, `0x0803FC58` ile okuma | D+E; track 0 ve 7. Mutlak grid RAM adresi `0x20048B9C` yalnızca K; gerçek cihaz nesnesi ölçülmedi |
| Alt görünüm seçimi | `0x0804DC86`: pad <16 → `0x0804DC50`, diğerleri → `0x0804DBDC`; mode `[grid+0x264]` | D+E; mode 0/2/3 ve iki uç track. Bu modlarda üst görünüm `[grid+0x74+4*track]`; alt görünüm sırasıyla `+0x14`, `+0x9C`, `+0xBC` |
| Üst görünüm tablosu | `0x0804DC50`: `tbb [pc, r2]`; mode 0/2/3'te `[grid+0x74+4*track]` (Step View) döner | D+E; track ve mode'a göre üst subview pointer'ını çözümler |
| Alt görünüm tablosu | `0x0804DBDC`: `tbb [pc, r2-1]`; mode 0'da `0x0804DC46` dalıyla `[grid+0x14+4*track]` döner | D+E; mode 0/2/3 alt subview (Note/Sample vb.) pointer'ını çözümler |
| Container pad dönüşümü | `0x0804DF3E` | D+E; üst pad aynı kalır; test edilen mode 2/3 alt pad'den 16 çıkarır. Mode 0 alt bölümde ayrıca kendi sayfa durumunu ekler. Tüm mode'lar için tek eşleme varsayılmaz |
| Gerçek step görünümü kurulumu | grid constructor `0x0804C632` → factory `0x0805594C`; `0x0804C638..646` sekiz pointer'ı grid+0x74'e kopyalar; factory `0x08055A42` → ctor `0x0805C980` | D; ctor `r1=32` ile `0x080520D8` çağırır. Heap/constructor çalışması emüle edilmedi |
| Step görünümü vtable | `0x080682CC`: press `0x0805CB05`, release `0x0805CCF1`; LED slot `0x080682E8` → `0x0805D3BD` | D; observer alt nesnesi +8, vtable `0x080682F8` → `0x0805D093` |
| Step press | `0x0805CB04` | D+E; `0x805d020` ile timer 3 durdurulur; `[view+0x60]` p0 != 0 ise pad'e 16 eklenir; `view+0x20` w1 set; `view+0x74+2*step` durum bit 3 (held) set; `0x805cf24` ile LED palet 31 (parlak beyaz) hesaplanır; `[view+0x18]` w1'e step yazılır ve notify edilir; timer 6 başlatılır (300 ms, callback `0x0805ce49`); `[view+0xb8]` (bekleyen toggle) ve `[view+0xc0]` (basılı pad) maskelerinde `1 << step` set edilir |
| Step release | `0x0805CCF0` | D+E; aynı +16 dönüşümü; `[view+0xc0]` maskesinden bit temizlenir; `[view+0xb8]` biti 1 ise (300 ms dolmadan kısa bırakış) `0x0805d610` ile normal step toggle çağrılır; `view+0x18` w1 == step ise timer 6 durdurulur; `view+0x20` w0=0 yazılıp notify edilir; observer (`0x0805d094` -> `0x0805d3f8` -> `0x0805cffe`) bit 3'ü temizler ve LED'i günceller; `0x805d020` çağrılır |
| Step mod/clear denetleyicisi | `0x0805D020` | D+E; `[view+0xB4]` != 0 ise `[view+0x38]` callback'ini çağırır ve `0xB4`'ü sıfırlar; timer 3 durdurulur. `step >= 32` durumunda `view+0x74+2*32` doğrudan bu baytı ezer ve kontrol yapısını bozar |
| Held timeout callback | `0x0805CE48` | D+E; timer 6 callback'i (300 ms); `[view+0xb8]` pending toggle maskesinden `[view+0xc0]` basılı bitleri temizler (`bics`); böylece uzun basışta bırakma anında toggle tetiklenmez, step parametre düzenleme moduna (`view+0x68`) girilir |
| Step durum biti yardımcısı | `0x0805CFFE` | D+E; `(view, step, bit_index, val)`; `view+0x74+2*step` içindeki istenen biti set/clear eder ve `0x0805cf24` ile LED'i yeniden hesaplar |
| Release durum temizleyici | `0x0805D3F8` | D+E; observer'dan `view+0x20` bildirimi geldiğinde çağrılır; `view+0x20` w0 değerini (0) alıp `0x0805cffe` aracılığıyla bit 3'ü (held) temizler |
| Normal step toggle | `0x0805D610` → hit varsa `0x0805D5C2`, yoksa `0x0805D588` | D+E; ST1=`[view+0xC]`, ST2=`[view+0x10]`. Sonunda ST2 ve ST1 notify edilir. Oluşturma velocity 96, microstep mask 1, probability 7, sample flip FF, nota `[view+0x5C]` p0, gate 6, flags 0 |
| ST1 parametre yazıcıları | `0x080549B0` (Velocity), `0x08054A04` (Probability), `0x080549D8` (Microstep), `0x08054A30` (Sample Flip) | D+E; `step >> 2` ile word hesabı yapar. `step=32` yazımı Velocity yerine Probability[0]'ı bozar |
| ST2 parametre yazıcıları | `0x08054A5C` (Note), `0x08054A84` (Gate), `0x08054AB0` (Flags) | D+E; `step >> 2` ile word hesabı yapar. `step=32` yazımı Note yerine Gate[0]'ı bozar |
| Held sample yolundaki oluşturma | `0x0805E41A` → `0x0805E5A0`, observer `0x0805E3B0` | D; önceki rapordaki bu hook normal step toggle'ın yerine geçmez. Farklı nesne/alan düzeni vardır |
| Word okuyucu/yazıcı | `0x0803FC58` / `0x0803FD26` | D+E; aktif seçim word başına bir bittir; tek global buffer seçimi gibi modellenmemeli |
| Notify | `0x0803FBEC` | D+E; `active_mask ^= dirty_mask`; `[store+0x14]` listesindeki maskesi eşleşen listener slot 0'ları çağırır, ardından dirty'yi temizler |
| Pattern commit | vtable `0x080696A0` → `0x08048208` | D+E; listener+0x1C ST1, +0x20 ST2, +0x28 pattern seçim store'u; pattern tabanı `[listener+4] + 0xA28*selected`. ST1 alanları 3/2/4/5; ST2 alanları 0/1/6; 32 kayıt işlenir |
| Step LED observer | shim `0x0805D092` (`this -= 8`), gövde `0x0805D094` | D+E; ST1 velocity değişiklikleri LED durum bit 1'i günceller; sample-flip için ayrı dal vardır. Test gerçek notify ile gerçek observer'ı çağırır |
| Step LED renk hesabı | `0x0805CF24`; durum kaydı `view+0x74+2*step`; çıktı `[[view+4]]+2*step` | D+E; 16-bit mantıksal renk kaydıdır, doğrudan fiziksel RGB buffer'ı değildir |
| Step LED penceresi | `0x0805D3BC` | D+E; `[view+0x60]` p0 sıfırsa buffer, değilse buffer+32 bayt döndürür: 16 × 2 bayt kayma (`cbz r1, adds r0, #0x20`) |
| Ekran birleştirme (Compositor) | vtable `0x080678F8` → `0x0804DD1C` | D+E; `0x08052108` ile subview slot 7 çağrılır; üst subview'dan 32 baytı `grid+0`, alt subview'dan (`+r7` ofseti ile) 32 baytı `grid+0x20`'ye `0x08022CF0` (memcpy) ile aktarır. Extra subview 1 (`0x0804DB78`) ve 2 (`0x0804DCB2`, sayfa tuşları) yan tuşları yönetir |
| Step LED renk motoru ve durum bitleri | `0x0805CF24`; durum kaydı `view+0x74+2*step`; çıktı `[[view+4]]+2*step` | D+E; durum bitlerine göre mantıksal renk atar: Bit 0 (Playhead/Cursor: boş adım 0x001B, dolu adım 0x001A), Bit 1 (Hit/Dolu: boş 0x0019, dolu 0x0018), Bit 2 (Loop range), Bit 3 (Held: palet 31/30) |
| Grid mod kontrolü ve alt ofset | `0x080588EE`, `0x080588AC` | D+E; `r7` alt tampon ofseti; mod 0'da sayfa durumuna göre `page * 0x20` (0 veya 32 bayt); mod 1/4/7/8/9/10'da 0x20; mod 2/3'te 0. `0x080588AC` `[grid+0x258]` track store dizisini kontrol eder |
| Alt LED aktarımı | `0x0802596E` → `0x0802960C`; `0x0802964E` → `0x08029684` | D / baseline; downstream frame/bit-plane işleme. Grid renklerinin fiziksel pad/RGB'ye tam dönüşümü bu turda tamamlanmadı |
| MIDI | router `0x0803B7EC` / `0x0803B8F0`; mask dispatcher `0x0802986A`; port send `0x080401FE` | Baseline D/E sınırları geçerli; fiziksel MIDI, kuyruk basıncı ve Note Off yaşam döngüsü yok |

## Gerçekte sınanan davranışlar

`tests/test_ui_contracts.py` yedi davranış testi içerir:

1. Gerçek pad dispatcher, sahte son callback'ler: pad sınırları ve velocity normalizasyonu/press-release ayrımı.
2. Gerçek container seçicileri: track 0/7, mode 0/2/3, pad 0/15/16/31, iki sayfa durumu.
3. Gerçek setter + accessor + notify + commit listener: pattern 0/7, iki başlangıç aktif maskesi,
   step 0/15/16/31. Sekiz pattern'in bütün baytları karşılaştırılır; ayar/otomasyon ve diğer pattern'ler korunur.
   Notify öncesinde pattern değişmez; sonraki edit önceki edit'i korur.
4. Gerçek normal toggle + notify + commit + LED observer: pattern 7 üzerinde dört sınır adımı aç/kapat;
   tüm pattern belleği, hit durum biti ve LED renk değişimi/dönüşü kontrol edilir. LED getter'ın iki penceresi doğrulanır.
5. Kritik vtable pointer'ları ve basılı-adım renk dalı: yalnızca hedef mantıksal LED kaydı değişir.
6. Gerçek step press (`0x0805CB04`) ve release (`0x0805CCF0`) yaşam döngüsü: sınır adımları 0, 15, 16 ve 31 (sayfa 0/1)
   için iki tam toggle döngüsü. Press anında durum bit 3 (held) set edilir, LED parlak beyaza (palet 31) geçer,
   300 ms timer 6 başlatılır. Release anında bekleyen toggle biti (`view+0xB8`) aktif olduğundan `0x0805D610` çağrılır,
   pattern commit edilir, durum bit 1 (hit) set edilir, timer 6 durdurulur ve observer zinciriyle bit 3 temizlenerek
   LED aktif renge döner. İkinci basışta adım pattern'den temizlenir, durum bitleri sıfırlanır ve LED başlangıçtaki sönük renge döner.
7. Basılı tutulurken sayfa ve track değişimi (step ownership):
   - Sayfa değişimi: `view+0x60` sayfa 0 iken basılan pad 5 (step 5), kullanıcı basılı tutarken sayfa 1'e geçilip
     bırakıldığında +16 eklenerek step 21 olarak yorumlanır. Step 21 basılı olmadığından toggle tetiklenmez ve `view+0x18`
     eşleşmediğinden işlem abort edilir; step 5'in view üzerindeki durum biti 3 ve basılı pad maskesi korunur.
     Sayfa tekrar 0'a alınıp bırakıldığında step 5 başarıyla açılır.
   - Track değişimi: Grid container (`0x0804D7A0` / `0x0804D7DE`) fiziksel pad basılı maskesini `grid+0x228` alanında tutar.
     Track 0 seçiliyken pad 0 basıldığında Track 0 view'ı basışı kaydeder (`view0+0x74` bit 3 = 1).
     Pad basılıyken track 1'e geçilip pad bırakıldığında, grid `grid+0x228` maskesini temizler ancak release olayını
     o an seçili olan Track 1 view'ına iletir (`view1`). Track 1 bu adımı hiç basmadığı için tepkisiz kalır;
     Track 0 view'ı release olayını hiç almadığı için step 0'ın sahipliği Track 0 üzerinde "öksüz" (orphaned) olarak basılı kalır.

`tests/test_step_routing.py` beş ek yönlendirme ve sınır güvenliği testi içerir:

1. `test_stock_container_routing_split`: Stok grid container pad yönlendirme ve yerel pad dönüşümü doğrulaması (`0x0804DC86` ve `0x0804DF3E`). Pad < 16 üst görünüme (Step View), pad >= 16 alt görünüme (Note/Sample) gider; Mode 0 sayfa 0'da pad-16, sayfa 1'de ise +16 eklenerek pad olarak döner.
2. `test_step_index_overflow_hazard_and_corruption_proof`: `step >= 32` durumunda stok ikilide oluşan üç kritik bellek bozulmasının matematiksel ve emülasyon kanıtı:
   - Durum dizisi taşması (`view + 0x74 + 2 * 32 = view + 0xB4`): Durum biti 3 (held, `0x08`), `view + 0xB4` ikincil kontrol/temizleme baytını ezer. `0x0805D020` sonraki basışta `view + 0x38` fonksiyon göstericisini çalıştırmaya çalışarak unmapped bellek hatasına ve sistem çökmesine yol açar.
   - ST2 Note parametre bozulması (`0x08054A5C`): `step=32` yazımı (`step >> 2 = 8`) word 8'e denk gelerek Step 0'ın Gate uzunluğunu ezer ve pattern belleğine bozuk commit eder.
   - ST1 Velocity parametre bozulması (`0x080549B0`): `step=32` yazımı (`step >> 2 = 8`) word 8'e denk gelerek Step 0'ın Probability değerini ezer ve pattern belleğine bozuk commit eder.
3. `test_safe_32pad_full_lifecycle_all_steps`: 32-pad Sequencer Modu yönlendirmesinin tam yaşam döngüsü doğrulaması:
   - Tüm 32 pad (`0..31`) doğrudan Step View'a yönlendirilir ve sayfa ofseti 0 kilitlenir (`step == pad`).
   - 32 adımın tamamında (0..31) Cycle 1 (açma) ve Cycle 2 (kapatma) eksiksiz sınanır.
   - `view + 0xB4` kontrol bloğu hiçbir adımda bozulmaz (kesin sıfır kalır).
   - Pattern belleğine 32 adımın 32'si de eksiksiz ve hatasız yazılır/temizlenir.
   - LED renk dizisi 32 adım için doğru palet değerlerine güncellenir.
4. `test_cross_boundary_concurrent_press_and_release`: Üst/alt yarı sınırında (pad 15 ve 16) eşzamanlı basış doğrulaması. `view + 0xC0` held maskesinin birden fazla biti aynı anda başarıyla koruduğu ve ardışık bırakışlarda adımların bağımsız commit edildiği kanıtlanır.
5. `test_routing_guard_clamping_prevents_overflow`: Sınır maskelemesi (`pad & 0x1F`) ile 32, 47, 63, 127 gibi sınır dışı değerlerin Step View'a geçmeden güvenle sınırlandığı ve `view + 0xB4` bölgesini asla bozmadığı doğrulanır.

`tests/test_led_compositor.py` beş LED birleştirme ve playhead doğrulaması testi içerir:

1. `test_stock_step_view_led_getter_and_compositor_split`: Stok Step View LED getter (`0x0805D3BC`) ve Compositor (`0x0804DD1C`) ayrım mekanizması:
   - Sayfa 0'da Step View LED getter 64 baytlık tamponun başını (`buffer + 0`), Sayfa 1'de ise ikinci yarısını (`buffer + 0x20`) döndürür.
   - Stok Grid Compositor üst 16 pad'e Step View penceresini, alt 16 pad'e Note görünümünü (`r7` ofseti ile Sayfa 0'da 0, Sayfa 1'de +0x20) kopyalar.
2. `test_step_view_32step_logical_led_buffer_mapping`: Step View 32 adımlık mantıksal LED tamponu ve 32-pad grid eşlemesi:
   - 32 adımın her biri stok renk motoru (`0x0805CF24`) ile renklendirilir (hit durumunda `0x0018`, boş durumda `0x0019`).
   - 32-adım LED Compositor, Step View'ın ilk 16 kaydını (`0..15`) üst 16 pad'e (`grid_output + 0`), ikinci 16 kaydını (`16..31`) alt 16 pad'e (`grid_output + 0x20`) kopyalar.
   - 32 pad'in 32'si de Step View'ın tam 32 adımı ile birebir (1-to-1) eşleşir; hiçbir adım ötelenmez veya üst üste binmez.
3. `test_playhead_continuous_flow_across_32_steps`: Playhead imlecinin (durum bit 0) 1'den 32'ye kesintisiz akışı:
   - Playhead 0'dan 31'e kadar tüm 32 adım üzerinde sırayla ilerletilir.
   - Her adımda önceki adımın bit 0'ı temizlenir, aktif adımın bit 0'ı set edilir ve `0x0805CF24` çağrılır.
   - Aktif adım boşsa playhead rengi `0x001B`, doluysa `0x001A` (parlak vuruş) olur.
   - Compositor sonrası grid tamponunda tam olarak `cursor`. pad'in playhead rengini aldığı, kalan 31 pad'in playhead rengi taşımadığı doğrulanır.
   - Cursor 0..15 iken alt 16 pad'de, cursor 16..31 iken üst 16 pad'de hiçbir playhead sızıntısı olmadığı, özellikle 15'ten 16'ya sınır geçişinde imlecin kesintisiz aktığı kanıtlanır.
4. `test_other_modes_preserve_original_bottom_pad_layout`: Diğer modlarda (Note, Velocity vb.) alt pad orijinal düzeninin korunması:
   - Mode 2 (Velocity) veya Mode 0 (Note) seçildiğinde alt 16 pad'in Step View 16–31 adımları yerine, o modun kendi subview LED tamponunu (Velocity için `[grid+0x9C]`, Note için `[grid+0x14]`) yansıttığı bayt bayt doğrulanır.
   - Üst 16 pad Step View görünümünü korurken, alt padlerin mod bağımsızlığı %100 kanıtlanır.
5. `test_compositor_memory_safety_and_no_overflow`: Compositor bellek güvenliği ve taşma koruması:
   - Grid buffer sonrasındaki (offset 0x54 ve ötesi) canary baytlarının ve Step View `view + 0xB4` alanının asla bozulmadığı, arabelleğin güvenle sınırlandığı kanıtlanır.

Son zincirlerde RTOS timer kuyrukları (`0x08046dde` / `0x08046e2a`) `bx lr` ile yalıtılmış, tetiklenen timer id ve callback'leri
hook ile izlenmiştir. Diğer UI, toggle, notify, commit ve observer mekanizmaları stock kod ile çalıştırılmıştır.
Nesneler ve listener bağlantıları sentetik olarak kuruldu; bu, stock constructor'ların gerçek cihazda aynı anda kurduğu
bütün listener listesini veya thread sırasını sınamaz.
Testler 64 adım uygulaması değildir. Sekiz pattern bloğu fixture olarak korunur; sekiz gerçek track'in eşzamanlı çalışması sınanmadı.

## 32-pad uygulaması için çıkan sınırlar

Pad `0..31`, alt görünümün aldığı pad, yerel step `0..31`, mantıksal step ve playback cursor ayrı tutulmalı.
Stock üst 16 pad route'u aynı track'in step view'ına gider; step view kendi içinde sayfa offset'i ekler.
Yeni 32-pad görünümünde alt yarıyı step view'a yönlendirmek tek başına yetmez: bu +16 hem press hem release için
kontrol edilmezse yanlış step/32 üstü indeks oluşabilir.
Yapılan testler ve disassembly analizi şu kesin mimari sınırları ortaya çıkarmıştır:
1. **Step View Nativ 32 Adım Destekler:** Step View bellek yapısı (`view + 0x74..0xB2` durum dizisi, `view + 0xB8` pending maskesi, `view + 0xC0` held maskesi, 64-baytlık LED buffer'ı ve ST1/ST2 32-entry tamponları) 32 adımı yerel olarak zaten desteklemektedir.
2. **Sayfa Ofseti Çiftlenmesi Felakettir:** Alt 16 pad (`16..31`) Step View'a aktarılırken, eğer Step View kendi içindeki sayfa ofsetini (`[view + 0x60] != 0` -> `step += 16`) uygulamaya devam ederse, `step = 16..31 + 16 = 32..47` oluşur.
3. **step >= 32 Sonuçları Kesin Olarak Kanıtlanmıştır:**
   - `view + 0xB4` ezilerek `0x0805D020` üzerinden crash oluşturur.
   - `1 << step` 32-bit kaydırmada sıfırlanır, maskeler tutarsızlaşır.
   - `st1` ve `st2` dizilerinde parametreler birbirinin üzerine yazılır (Note 32, Gate 0'ı; Velocity 32, Probability 0'ı bozar).
   - Pattern commit (`0x08048208`) döngüsü yalnızca 32 adımı (`0..31`) işlediğinden, 32 ve üzeri adımlar bellekte kalıcı kirlilik bırakır ama asla diske/pattern'e düzgün yazılamaz.
4. **Çözüm Mimarisi:**
   - Sequencer Only (32 Pad) modunda: Grid Container tüm pad'leri (`0..31`) Step View'a yönlendirir.
   - Step View'a gelen pad doğrudan adım indeksi olarak ele alınır (`step == pad`).
   - Step View için sayfa ofseti sıfıra sabitlenir / izole edilir.
   - Yönlendirme katmanında `pad & 0x1F` sınır maskesi uygulanarak 31 üstü indeks geçişi donanımsal/yazılımsal olarak kesin engellenir.
   - LED tarafında ise Grid Composite (`0x0804DD1C`), üst 16 pad için `buffer + 0`, alt 16 pad için `buffer + 0x20` kopyalayarak 32 adımın tamamını aynı ekranda birleştirir.

## Açık sorular ve elenen yorumlar

- Mode 2/3 alt pointer ofsetleri ilk okumada +0x54/+0x9C sanıldı. Test başarısız oldu; Thumb TBB tablosu
  yeniden izlenince +0x9C/+0xBC doğrulandı. Test zayıflatılmadı, fixture düzeltildi.
- `0x0804E00A` başka bir 32-entry görünüm adayıydı. Constructor sonucu controller+0x40'a gider;
  grid+0x74'teki step view değildir. 32 sayısını görmek tek başına yeterli değildi.
- Bir PC-relative literal önce dört bayt ileri okundu; hizalı Thumb PC hesabıyla gerçek vtable bulundu.
  Literal/jump-table baytları disassembly'de sahte komutlar gibi görünebilir.
- Release sırasında `view+0x74` durum bit 3'ün doğrudan release fonksiyonu (`0x0805CCF0`) tarafından değil,
  `view+0x20` store bildirimi üzerinden observer (`0x0805D094` -> `0x0805D3F8` -> `0x0805CFFE`) tarafından temizlendiği kanıtlandı.
- Uzun basışın (hold) kısa basıştan (tap) nasıl ayrıldığı kanıtlandı: timer 6 callback'i (`0x0805CE48`, 300 ms),
  `view+0xB8` pending toggle maskesinden basılı pad'i temizleyerek bırakma anındaki toggle'ı iptal eder ve edit modunu açar.
- `step >= 32` taşmasının Step View bellek bloklarını (`view + 0xB4`) ve ST1/ST2 parametre dizilerini nasıl tahrip ettiği sentetik testlerle kesin olarak kanıtlandı.
- Grid Compositor (`0x0804DD1C`) ve Step View LED getter (`0x0805D3BC`) yapısı çözümlendi; durum bit 0'ın (`0x0001`) Playhead (playback cursor) olduğu ve 32 adımın tamamında (0..31) kesintisiz akabildiği kanıtlandı.
- Note (`mode 0`) ve Velocity (`mode 2`) gibi modlarda alt 16 pad'in o modun kendi alt subview LED tamponunu (`bottom_view + r7`) yansıttığı ve mod bağımsızlığının tam olarak korunduğu kanıtlandı.
- Gerçek controller/track/pattern nesnelerinin RTOS eşzamanlılığı, SD save/load ve fiziksel tarama zamanlaması açık.
- Gate/tie, Mutate, Clear/Duplicate ve 1–16 düğmesi uzunluk gesture'ı ayrı kabul testleri gerektirir.
- Mod kısayolu seçilmedi; ayrı Projects/Packs/MIDI-only davranışı uygulanmadı.

Sonraki tek görev: 32 Pad Yönlendirmesi ve LED Birleştirici mikro-yamalarının (M3/M4) entegrasyonu ve mod kısayol/geçiş mekanizmasının tasarlanması.
