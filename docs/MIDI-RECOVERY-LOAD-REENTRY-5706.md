# Taint sonrası native Load/New erişimi — 5706

1 Kasım 2026. Firmware aynı: SYX `272a8128ba159e32c7457f0f123cb148c9e2d93a7803cbd9be327dccc5bb5cc1`, CRC `985753F7`.
Yerel native ARM emülasyonu. **M7 NO-GO.**

## Soru ve sonuç

Short-read karantinasından sonra kullanıcı Projects üzerinden yeniden
Load/New başlatabilir mi? **Mevcut adayda hayır.** Projects görünümü açılır
ama controller proje-busy bayrağı pad'i handler'a göndermeden reddeder.
Controller'ı aşan ayrı tanısal çağrı da dispatcher phase2 kontrolüne takılır.
Başarılı bir native backend retry bütün raw veriyi geri yükler; taint ise
kalır. Böylece veri yenileme ve mod koruması birbirinden ayrılmış olur.

## Native zincir ve iki kapı

Her mod ayrı reset kullanır. Mevcut `exercise_load` önce slot1 Save, tam
169092B Load kontrolü ve bir 741B alt-okuma hatasını üretir. Sonuçta native
Close çalışmış, bridge callback emekli olmuş, phase2/flags3/taint1 kalmıştır.
Bu 216 IRQ/Main turu bitince yalnız gözlem/enjeksiyon hook'ları kaldırılır.
CPU veya uygulama RAM'i geri sarılmaz. Aynı UART peer ile devam edilir.

1. Button26 Projects'i açar (`ctrl+14` görünüm6, page0). Controller'daki
   `ctrl+8C` store pointer'ı proje `P+4C` flags store'u ile aynıdır.
2. Slot1 ve slot2 controller pad girdilerinde `3D7FE→3D814→3D858` izlenir.
   `3D814`, flags bit1 nedeniyle return'e gider. `4F09E` çağrılmaz.
3. Ayrı tanısal `4F09E(projects,slot)` çağrısında action argümanı slot+64,
   receiver `[P+38]` olur. `385FE` phase2'yi görüp `386D6` ret yoluna gider.
   Load/New backend'e girilmez. Bu adım controller girdisi değildir.
4. Dört reddin tamamında raw, metadata, slot, I/O sayısı ve NOR aynı kalır.

## Tam yükleme ve New sınırları

Yalnız tanısal amaçla `37B8C(P,1,0)` çağrılır. Bu, UI engellerini aşan
backend adapter'ıdır; kullanıcı kurtarması olarak raporlanmaz. RAM'e proje,
phase, flags, taint, count, callback sonucu veya kuyruk yazılmaz.

Native FatFs 169092B okur ve status0 döner. Başarı `37E3C→379B2` üzerinden
uygulanır; raw SHA256 önce kaydedilen bütün buffer ile eşleşir. `37E7E`
öncesinde phase2/flags3/taint1; stock yayınları sonrasındaki `38798` girişinde
phase0/flags0/taint1 gözlenir. Başarılı retry'da phase0 sonrası sekiz tam Main
turunu içeren bu pencerede ayrı `41906` Close çağrısı yoktur. Başarı bridge'i
`472A8→381C8→37E3C` Close çağırmaz. Phase0, dosyanın emekli edildiğini
kanıtlamaz; ayrı Close görülmemesi de tek başına sızıntı değildir. Sekiz recorder ve
sekiz player alias adresi değişmez. Mod kısayolu taint nedeniyle reddedilir.

Native backend'in tamamlanmasından sonra gerçek controller pad girdileri
yeniden kullanılır: slot1 Load tam okuma/apply yapar; boş slot2 New ise
`37C84→32DB2→378C6→37E3C` timer/defaults zincirini yürütür, dosya read yapmaz.
Her ikisi phase0/flags0 ile biter; taint1 ve mod reddi korunur.

Bu gözlemler, tam veri yenileme ve apply sonrası bir noktanın nerede olduğunu
belirler. **İşlem kimliği, Close tamamlanması ve tekrarlanan hata koşullarıyla
taint temizleme protokolünün güvenli olduğunu kanıtlamaz.** Firmware'e böyle
bir değişiklik yapılmadı. UI recovery hâlâ yoktur.

## Doğrulama ve kapsam

Normal/Sequencer toplam IRQ ve tam Main sayısı `360/360`; her birinde 216
kurulum ve `144/144` devam turu. İki yeni exact-SYX test PASS. Ek heap
tahsisi, devam aşamasında NOR yazımı veya MIDI context/active/TX fault yok.
Stack guard'ları ve image baytları korunur. Bayt/range/CRC audit PASS.
Güncel toplam 35 ayrı test kanıtı aynı image'e aittir; bu tur iki yeni ayrı
test ve rapor düzeltmesi nedeniyle bunların tekrarları çalıştırıldı.
Tam suite172/core155 collection'dır, tam regresyon değildir.

İlk pilot Projects handler'a ulaşılacağını varsaydığı için test assertion'ında
durdu. Daha erken stock controller busy koruması gözlenince test düzeltildi.
`probe-normal/` ve `sources/` saklıdır; bu firmware hatası sayılmaz.
İkinci Normal/Sequencer pilot çifti başarılı Load sonrasında ayrı Close
beklediği için durdu. `probe-normal-v2/` ve `probe-sequencer/` korunur;
ikisi `probe-normal-v2/sources/` sürümünü çalıştırdı. Bu da test varsayımıdır.

Sonraki iki PASS koşusunda native sonuçlar doğruydu; setup raporunun UART IRQ
listesi peer'ın sonraki olaylarını da içeriyordu (96 credit/328 olay). Helper
deep-copy snapshot ve tutarlılık assertion'ı ile düzeltildi; iki mod final
klasörlerinde yeniden geçti. Ara PASS raporları `probe-normal-v3/` ve
`probe-sequencer-v2/` altında, çalıştırılan kaynaklar ilk klasörün `sources/`
dizininde saklıdır. Bunlar canonical sonuç değildir; ayrı test sayılmaz.

741B sınırı sentetik alt-read girdisidir; doğal EOF/FAT/SD olayı değildir.
Native reset, RTOS worker ve dosya kodu çalışır; GPIO/input kuyruğu, NVIC
arbitrajı, gerçek zaman ve fiziksel MIDI/USB teslimi kanıtlanmaz. Sonlu
TIM/ADC/DSP/UART/NOR modeli kullanılır. RAM onarımı yoktur.

## Kanıt ve sonraki iş

`logs/recovery-load-reentry-20261101/`: `probe-normal-final/report.json`,
`probe-sequencer-final/report.json`, `apply-boundaries.json`, `summary.json`,
`hashes.json`, `changes.diff` ve byte audit. Önceki evidence klasörlerine
yazılmadı. Komutlar ve güncel durum STATUS.md'dedir.

Tek sonraki iş: Close tamamlanması doğrulanmış karantinadan yalnız stock
Load/New kabul eden, tam read/defaults ve apply sonrası taint'i temizleyen,
tekrar hatada kapalı kalan dar kurtarma yolunu uygulayıp native sınamak.
Diğer açık gruplar bu göreve karıştırılmayacak.
