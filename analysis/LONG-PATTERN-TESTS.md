# Uzun pattern sınır testleri — 24 Ekim 2026

## Sonuç

**Stock 32-adım sınırını doğrudan artırmak çalışmıyor.** Gerçek firmware koduyla, 33. nota yazımının gate alanına denk geldiği ve player'ın 33. adım için pattern ayarlarını nota kaydı gibi okuduğu yeniden üretildi. Bu, değiştirilmemiş stock kodun yanlış indeksle çağrılmasının sonucu; normal CR kullanımında keşfedilmiş bir hata değildir.

32-adım sayfalarını tek mantıksal pattern altında adresleyen **bilgisayar tarafı bir adaptör modeli** bu veri çakışmasını önledi. Stock yazma ve oynatma fonksiyonları, doğru backing blok ve 0..31 yerel adım ile çağrıldığında kontrol edilen verileri doğru işledi. Henüz cihaz firmware'ine eklenmiş bir mod veya çalışan pad arayüzü yoktur.

## Kabul edilen ürün hedefi

- Sequencer Only modunda 32 pad = bir sayfanın 32 adımı.
- Oklar adım görünümünde aynı uzun pattern'in sayfaları arasında gezinir. Kullanıcıya sunulan pattern zinciri değildir.
- 1–16/17–32 tuşunu tutup pad'e basmak, o sayfadaki adımı son adım yapar. İkinci sayfa + pad 10 = 42 adım.
- İlgili gate, microstep, mutation, pattern, note page ve pattern settings davranışları korunmalı.
- Sequencer projeleri normal CR projelerinden ayrı olmalı; Packs sayfası bu modda kapalı olmalı.
- Mod geçişi bir tuş kombinasyonuyla olmalı; kombinasyon ve üst adım sınırı henüz seçilmedi.
- Polifoni ve Elektron ek davranışları bu sürümün dışında.

## Yapılan deneyler

| Deney | Sayı | Sonuç | Sınır |
|---|---:|---|---|
| Stock note/gate/flags yazıcılarına 32..63 indekslerini doğrudan verme | 96 | Beklenen veri çakışmaları yeniden üretildi | Bu 96 test başarıyla çalışan uzun adım değildir; yanlış yaklaşımın başarısızlığıdır |
| Stock player'da adım 1,16,17,32,33 adresleri | 5 | Adım 33 pattern+0x100 ayar alanını okuyor | Note scheduler çağrısı yakalanıp durduruldu; MIDI gönderilmedi |
| Sayfalı model → stock player | 128 adım | Adres, nota, velocity, ölçeklenmiş gate ve tie argümanı doğru | Note Off yaşam döngüsü veya gerçek zamanlı sayfa geçişi test edilmedi |
| Sayfalı model → stock note/gate/flags yazıcıları | 384 | Doğru sayfa/alan değişti; diğer sayfa buffer'ları korundu | Commit/notify ve kayıt yok |
| Stock microstep/probability ön geçişi | 3456 | Altı microstep, farklı maskeler ve eşikler doğru işlendi | Clock/RNG dağılımı/tie yaşam döngüsü yok |
| Uzunluk seçimi bilgisayar modeli | 128 uzunluk + 5 geçersiz girdi | Eşleme, sarma aritmetiği ve geçersiz girdi reddi doğru | Fiziksel tuş, debounce ve UI routing test edilmedi |

**128 adım yalnızca test kapasitesi.** Ürünün 128 adımı desteklediği veya bu kapasiteye karar verildiği anlamına gelmez.

### Doğrudan genişletmenin neden başarısız olduğu

Stock edit buffer'ında 32 nota baytından sonra gate grubu gelir. `0x08054A5C` yazıcısına sıfır tabanlı adım 32 verirsek word 8 / buffer baytı 32 yazılır: bu 1. adımın gate alanıdır. Gate yazıcısında aynı hata flags alanına taşar. Flags yazıcısında stock 24-word ST2 düzeninin dışına çıkılır. Testler ayrılmış sentetik bellek içinde yapıldı; gerçek cihaz veya dosya bozulmadı.

Player `0x0804AFBC`, adım adresini `pattern_base + step*8` olarak hesaplıyor. 32×8 = 0x100, stock pattern ayarlarının başlangıcı. Bu nedenle yalnızca son-adım değerini 63 yapmak 64 adımlık sequencer oluşturmaz.

### Sayfa adaptörü neyi gösterdi?

Host modelinde `page, local = divmod(global_step, 32)` yapılıyor. Stock player'a backing blok numarası ve local adım veriliyor; edit yazıcıları ilgili sayfanın sentetik buffer'ıyla çağrılıyor. Sayfa değişimi kullanıcıya yeni pattern olarak gösterilmiyor. Ancak bu testte backing bloklar boş sentetik RAM'e önceden yerleştirildi; mevcut kullanıcı pattern slotları feda edilmedi ve cihazda bu belleğin bulunduğu iddia edilmiyor.

Sayfa başına gate/velocity/tie alanlarını doğru okumak, sayfalar arasında tie veya uzayan notaların doğru sürmesiyle aynı şey değildir. Test, note scheduler `0x0804B0D4` çağrısının argümanlarını yakalar ve başarıyla dönmesini taklit eder. Gerçek nota kuyruğu, Note Off, MIDI portları ve DSP çalıştırılmaz.

Microstep testinde stock `0x0804AEEE` ve sentetik player belleği kullanıldı; fonksiyon çağrıları mock edilmedi. Rastgele sayı üretimi yerine player'daki önceden üretilmiş eşik kontrol edildi. Tutulan tie yok ve beşinci argüman sıfır olduğundan gate yaşlandırma yolu bu deneyin dışında kaldı. Bu nedenle 3456 geçiş, gerçek cihazda bütün özelliklerin korunduğu anlamına gelmez.

## Bellek hesabı: şu anki asıl engel

8 track × track başına 8 pattern korunursa, yalnızca ek 8-baytlık adım kayıtları:

| Pattern uzunluğu | Ek adım verisi | Otomasyon dahil stock blokları kopyalamanın ek maliyeti |
|---|---:|---:|
| 32 | 0 | 0 |
| 64 | 16384 bayt | 166400 bayt |
| 128 | 49152 bayt | 499200 bayt |

İkinci sütun ek otomasyon ve edit buffer'larını içermez. Üçüncü sütun her ek sayfaya tam 0xA28 baytlık stock pattern bloğu ayıran kaba yöntemi gösterir; daha verimli bir tasarımın maliyeti değildir.

Önceki kaynak incelemesinde bildirilen 3272 baytlık stock heap payı, kullanıcının cihazında doğrulanmadı. Yine de bu tahminle bile mevcut heap'e ilave sayfaları doğrudan ekleme yaklaşımını seçemeyiz. 64 adım için tüm tam blokların toplamı 332800 bayt olur; bu yalnızca pattern verisidir, stock sistemin geri kalanı ve stack hariçtir.

**Çıkarım:** Uzun pattern için uygun bir RAM/kayıt mimarisi henüz kanıtlanmış değildir. Daha sıkı veri/otomasyon kodlaması, yeniden kullanılabilir RAM alanları veya cache'li erişim araştırılmalı. Sample kullanılmaması ilgili belleği otomatik olarak ARM sequencer'a kazandırmaz. Pattern sayısını azaltmak ya da kullanıcıya zincirlenmiş pattern sunmak, kabul edilen şartı sessizce değiştirmek olur; bu test böyle bir değişiklik yapmıyor.

## Henüz doğrulanmamış kabul maddeleri

| Madde | Durum |
|---|---|
| Gerçek pad/ok/uzunluk düğmesi etkileşimi | Uygulanmadı/test edilmedi |
| 32→33 ve son→ilk geçişinde gate/tie | Yaşam döngüsü test edilmedi |
| Mutate'ın tüm uzun pattern'i işlemesi | Uygulanmadı/test edilmedi |
| Uzun pattern otomasyonu | Uygulanmadı/test edilmedi |
| Pattern/Note/Pattern Settings görünümü entegrasyonu | Uygulanmadı/test edilmedi |
| Ayrı Projects alanı, Packs'in kapatılması | Uygulanmadı/test edilmedi |
| Mod tuş kombinasyonu ve normal moda dönüş | Uygulanmadı/test edilmedi |
| Fiziksel cihaz, SD, kalıcılık, gerçek MIDI zamanlaması | Test edilmedi |

Bu maddeleri test edilebilir hale getirmek için önce firmware uygulaması gerekir. Bu turda yüklenebilir bir mod yapılmadı. Önceki 'mümkün' değerlendirmesi temel MIDI yönlendirmesi ve 32 adım görünümü içindi; uzun pattern, tüm mevcut pattern sayıları ve ayrı proje alanını birlikte koruma hedefi için ilave mimari çalışma gerekmektedir.

## Tekrar çalıştırma

Önce README.md'deki Python ortamını kur. Ardından:

```powershell
.\.venv\Scripts\python.exe test_long_pattern.py C:\dosyalar\circuitrhythm-firmware-5706.syx
```

Sonuç `long-pattern-results.json` dosyasına yazılır. Testler Linux analiz ortamında çalıştırıldı; Windows komutları henüz Windows'ta denenmedi. Python `-O` kullanma. Stock firmware dosyası salt okunur kullanılır; MIDI portu açılmaz, cihaz aranmaz, firmware yüklenmez.
