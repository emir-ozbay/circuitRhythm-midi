# Güncel kapsam — 32 adım şimdi, 64 daha sonra

Bu belge önceki raporlardaki uzun pattern hedefinin uygulama sırasını günceller.

## İlk sürüm
- Ek Sequencer Only modu; cihaz harici cihazlara MIDI sequence/controller işlevi sunacak. Dahili sample çalma bu modun amacı değil.
- Adım görünümünde 32 pad, aynı stock pattern'in 1–32 adımlarını birlikte gösterecek.
- 1–16/17–32 düğmesinin kısa basışı bu görünümde sayfa değiştirmeyecek; basılı tut + pad, son adımı 1–32 arasında seçecek.
- İlgili Gate, Velocity, Microstep, Probability, Tie, Mutate, Pattern, Note ve Pattern Settings işlevlerinin kullanıcı davranışları korunacak. Mevcut stok davranışı değiştirilecekse açıkça gerekçelendir ve kullanıcıya belirt.
- Note ve parametre görünümleri kendi ihtiyaç duydukları düzeni koruyabilir; her görünümde 32 pad zorunlu adım düğmesi değildir.
- Tek adım sayfasında oklarla sayfa değiştirme gerekmiyor. Diğer görünümlerde oktav vb. mevcut görevler korunacak.
- Mod geçişi bir tuş kombinasyonuyla; kombinasyon henüz seçilmedi, çakışma incelemesi gerekli.
- Sequencer Projects normal CR projelerinden ayrı olacak. Packs sayfası yalnızca bu modda devre dışı olacak. Bu iki özellik ilk ekran prototipinden sonra geliştirilecek; hedef dışına çıkarılmadı.
- Normal moda dönüşte normal işlevler ve projeler korunacak. Ayrı proje alanı yalnızca UI filtresi değil, kalıcılık ve yanlış yere yazmayı önleme tasarımı gerektirir.

## Sonraki hedef
Tek mantıksal pattern'de 64 adım; 32-pad sayfaları arasında oklarla gezinme. Kullanıcıya pattern zinciri olarak sunma ve pattern sayısını izinsiz azaltma. Pad/local-step/logical-step/playback-cursor kavramlarını şimdiden ayır; gelecekte 64'e geçişin yalnızca UI değişikliği olduğunu iddia etme.

## Kapsam dışı
Şimdilik 128 adım, polifoni, Elektron ek özellikleri, yeni synth/sampling/DSP motoru.

## Açık kararlar
Mod tuş kombinasyonu; uzunluk kısalınca dışarıda kalan notaların korunması; start-point ile son-adım seçimi ilişkisi; kaydedilmemiş projeyle mod geçişi; ayrı proje alanının disk biçimi/yolu; gerçek MIDI çıkış aralığı ve gate davranışı. Stock davranış mümkünse önce ölçülüp korunmalı. İlk 32-pad testi için bütün açık kararları çözmek gerekmez.
