# Cihaz denemesi kayıt şablonu

Bu dosyayı her deneme için logs içine kopyala; varsayımları sonuç diye doldurma.

- Tarih / test eden:
- Git commit / patch sürümü:
- Stock SHA-256 ve çıktı SHA-256:
- Kurulu firmware / bootloader:
- Değişen application adres aralıkları:
- Yedeklerin konumu / test projesi:
- Stock'a dönüş yöntemi kontrolü:
- Bu build için kullanıcının yükleme onayı:
- Host testleri / başarısız veya atlanan kontroller:
- Kesin panel adımları:
- Beklenen LED/MIDI davranışı:
- Gerçek gözlem ve MIDI log:
- Stop/mute/yeniden açma sonrası açık nota var mı:
- Geri dönüş sonucu:
- PASS / FAIL / NOT TESTED ve nedeni:

32-adım görünümü için minimum sıra: 1,16,17,32'ye nota -> playback -> gate/velocity düzenle -> microstep -> probability -> Clear/Duplicate -> Mutate -> 1/16/17/32 uzunluk -> pattern değiştir -> kaydet/yükle -> kapat/aç. Her özellik için önce stock referansını belirle; rastgele işlemlerde notaların/verilerin korunması gibi invariant'ları kontrol et.

MIDI timestamp'leri bilgisayar/sürücü gecikmesini içerir. Mikro-saniye düzeyinde hardware jitter iddiası için donanım ölçümü gerekir. USB ve DIN ayrı değerlendirilir.
