# İlk küçük firmware denemesi: teknik kapsam taslağı

24 Ekim 2026. **Tasarım hazır; yama uygulanmadı, derleme/paketleme yapılmadı, yükleme dosyası yok.**
Bu belge cihaz testi onayı istemez. M1 kanıtları `UI-TRACE-5706.md` içindedir.

## Aday davranış

Stock step görünümünde basılan adımın gösterge rengini farklı bir mevcut palette index'iyle göstermek.
Bu ilk tanılama denemesi yeni Sequencer Only modu değildir; tüm track'lerin stock step görünümündeki aynı renk dalını etkiler.
Mod kısayolu, veri biçimi, nota/gate, pattern sayısı, DSP veya kayıt kodu değiştirilmez.

| Alan | Kesin aday |
|---|---|
| Girdi SHA-256 | `11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf` |
| Application base / stock sonu | `0x08010000` / `0x0806A570` (son adres hariç) |
| Komut adresi / image ofseti | `0x0805CF68` / `0x4CF68` |
| Beklenen orijinal komut | `1f 22` = `movs r2, #31` |
| Önerilen komut | `1e 22` = `movs r2, #30` |
| İzinli komut aralığı | `[0x0805CF68, 0x0805CF6A)`; gerçek bayt farkı yalnızca `[0x0805CF68, 0x0805CF69)` |
| Kaynak palet | `0x08062AB0`; index 31 word `0x0055`, index 30 word `0x001E` |

Kanıt: step press `0x0805CB46..4E` durum bit 3'ü set eder. Renk fonksiyonu `0x0805CF24`,
bit 5 yokken bit 3 set ise `0x0805CF68` dalını seçer. Bu dal `0x080555C0` üzerinden sadece
ilgili 16-bit mantıksal LED kaydını yazar. Renklerin insan gözüyle adı/fiziksel parlaklığı burada ölçülmedi.
Bit 5 daha yüksek önceliklidir; bu aday her basışın her modifier durumunda renk değiştireceğini vaat etmez.
Stock dal sentetik RAM'de 1/16/17/32 için çalıştırıldı; **önerilen değiştirilmiş kod henüz sınanmadı.**

## Paket üretmeden önce yapılacaklar

1. Sadece bu komutu üreten sabit sürümlü assembler/toolchain veya denetlenmiş sabit-width patch yöntemi seçilir;
   komut baytları bağımsız disassembly ile karşılaştırılır. ARM toolchain henüz kurulmadı. Upstream tam build çalıştırılmaz.
2. Yerel patch aracı input hash, uygulama hedefi (`0x63`, HEADER target 0), image hash/CRC, komutun eski baytları,
   uygulama sınırları ve aralık çakışmalarını zorunlu kontrol eder. Yanlış taban/overlap/bounds testleri yazılır.
   Stock dosyaya yazmak reddedilir. Initial vector table ve ilk kimlik bölümü korunur; bu aday için
   ilk `0x200` image baytı dahil aday dışındaki **bütün** image baytları aynı olmalıdır.
3. Stock ve aday kod sentetik RAM'de aynı durumlar altında karşılaştırılır: yalnızca hedef LED word'ü palette 31'den 30'a
   değişmeli; diğer 31 LED, edit buffer'ları ve pattern belleği aynı kalmalı. Diğer öncelik dalları değişmemeli.
4. SysEx CRC-32/MPEG-2 yeniden hesaplanır; tekrar decode/encode sonucu, ürün/target, boyut ve ilk FINISH/vector bloğu
   doğrulanır. Image diff ve taşıma diff'i ayrı raporlanır; checksum değişikliği taşıma farkının bir parçasıdır.
   Old/new bytes, aralıklar, girdi/çıktı hash'leri, tool sürümleri ve test log'ları `build/`/`logs/` içine çıkar.
5. Build/transport kimliği konusu çözülür: upstream, aynı kimlik bloğunun yüklemeyi engelleyebileceğini iddia ediyor.
   Bu kullanıcı cihazında doğrulanmadı. Aday kimliği değiştirmiyor; yükleme kabulünü varsaymıyoruz.
   Gerekli olursa kimlik değişikliği ayrı, açıkça incelenmiş aralık olarak tasarlanır; sessizce eklenmez.

Yeni kod alanı, heap rezervasyonu veya runtime flash yazma yolu yoktur. Bu küçük kapsam riski azaltır;
cihaz uyumluluğu veya kurtarma garantisi değildir.

## Ayrı cihaz testi teklifinin zorunlu içeriği

Onay ancak kesin aday dosya üretildikten sonra istenir. Teklif, tam dosya yolu ve SHA-256,
diff/manifest, kullanılan uploader ve kaynak incelemesi, mevcut cihaz firmware/bootloader bilgisi,
tam yedeklerin iki kopyası ve doğrulanmış stock'a dönüş yolunu içerir. Şu anda bunların cihazla ilgili kısmı bilinmiyor.
`RECOVERY.md` prosedürü bu oturumda fiziksel olarak denenmedi; tarihsel destek bağlantıları yeniden doğrulanmadan
güncel recovery kanıtı sayılmamalı. İlk testten önce resmî yönerge ve Components reinstall erişimi ayrıca doğrulanmalı.

Planlanan kabul: önemsiz test projesinde, stock referansıyla aynı koşullarda 1/16/17/32. adımların basılı renkleri,
release sonrası eski renge dönüş, sayfa/track değişimi, çalma/durdurma ve normal görünüme dönüş kaydedilir.
Beklenmeyen nota, takılma, kayıt hatası veya giriş kaybında test sonlandırılır; başarısız yazım kesinleşmeden güç kesilmez.
Gerekirse `RECOVERY.md` içindeki resmî reinstall yolu kullanılır; erase/unlock/debug işlemi yapılmaz.
Stock'a dönüş ve veri bütünlüğü ayrıca kaydedilir. MIDI ölçümü istenirse pasif capture için ayrı açık izin ve kayıt gerekir.

Kesin dosya/hash ve recovery hazırlığı olmadığı için şu an cihaz yükleme aşamasına geçilemez.
