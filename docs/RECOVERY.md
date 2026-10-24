# Cihaz testi ve kurtarma

Bu paket cihaz erişimi yapmaz. Custom firmware henüz yoktur. Brick ihtimali için güvenilir bir yüzde veremiyoruz; bootloader'ın mevcut olması her hatadan kurtulma garantisi değildir.

## İlk yüklemeden önce
Components'ta kurulu firmware'i kaydet; bootloader uyumluluğu gereksinimini ayrıca belirle. İçerikleri Components ile yedekle; SD kartın tamamını kart okuyucuyla kopyala. Yedeğin ikinci kopyasını bu çalışma klasörünün dışında tut. Denemelerde önemli proje kullanma. Güvenilir güç/USB kullan; güncelleme sürerken bağlantı kesme. Uploader, DAW ve MIDI monitor aynı port için yarışmamalı.

Patch yalnızca denetlenmiş application alanını hedeflemeli. Bootloader, flash option bytes, toplu flash silme veya debug unlock işlemi bu projenin normal akışı değildir. Uygulama kodu yazma alanı doğru olsa bile hatalı runtime kodu risk taşır. Ayrı Projects özelliğinin henüz yapılmış olmaması, test projelerinin otomatik izole edildiği anlamına gelmez.

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
