# Native Load short-read ve sınırlı karantina — 5706

1 Kasım 2026. Çalışma 31 Ekim'de başladı;kanıt dizini bu tarihi korur.
Yerel ARM emülasyonu;fiziksel MIDI/USB/SD erişimi yok. **M7 NO-GO.**

## Yeniden üretilen hata

Eski geçerli `c9a87a9d…` adayında gerçek reset,stock constructor'lar,Save,
FatFs/NOR,Content worker ve Main callback zinciri çalıştırıldı. Save slot1'i
169092 bayt olarak oluşturup tamamlandı. Native pad0 düzenlemesi ilk tuple'ı
`0006000007ff0000` → `4806016007ff0000` yaptı.

Stock Load aynı raw adrese okur. `411BE` alt dosya nesnesi çağrısında yalnız
istek uzunluğu741'e sınırlandı. FatFs gerçek kaydedilmiş baytları kopyaladı ve
gerçek sayacı741 yaptı;üst `411C4..CC` özgün169092 ile karşılaştırıp4 döndürdü.
Host bir başarı/hata dönüş değeri veya raw proje baytı yazmadı.

Bu,**sentetik alt-okuma girdisiyle native yürütmedir**. Gerçek dosya169092B'dir;
doğal FatFs EOF,bozuk FAT,zamansal kart arızası veya fiziksel SD olayı değildir.
Save/Load native backend girişleri doğrudan çağrılır;Projects pad/Save tuşunun
tam uçtan uca testi değildir. Düzenleme/mod kısayolları gerçek controller
vtable'ından gelir;GPIO/input kuyruğu modellenmez.

`2AE32` sonucu4,Main `472A8` girişinde r2=4 olarak gözlendi. Stock köprü bu
sonucu kaybeder;`381C8` descriptor'ın tür2 alanına bakıp`37E3C` başarı apply'ını
çağırır. Yalnız raw+740 değişir:tuple `0006016007ff0000` olur. Kalan velocity
96/microstep1 canlı projedendir. Phase/flags0'a döner ve gerçek Shift+Sample Rec
0→1 geçişini kabul eder. Bu emülatör varsayımı değil,yürütülen stock yoludur.

Eski `PROJECT-LOAD-ALIAS-RISK.md` içindeki taint/Save wrapper'ları tarihsel
banka ayrımlı adaya aittir;güncel c9a87a9d adayında aktif değildi.
Karşı örnek:`logs/recovery-load-short-read-20261031/explore-native-v2*`.

## Uygulanan düzeltme ve kesin sınırı

`src/project_load_guard_patch.py`,`472A8` girişini4B B.W ile152B uygulama
cave'ine (`0807C000`) yönlendirir. Native sonuç0 veya başka receiver ise
özgün4B prologue ve devam yürür. Sonuç sıfır değilse,callback vtable'ı
`08066FA0` ve destination==`[callback+8]` ile project Load kimliği doğrulanır.
Pointer sınır/hizalama kontrolleri yeni okumalardan önce yapılır.

Eşleşen hata:

- Ayrılmış state+64 `project_tainted=1` olarak işaretlenir.
- Bridge callback pointer'ı emekliye ayrılır;başarı callback/apply çağrılmaz.
- Stock `460C8` üzerinden Close kuyruğa verilir.
- Native phase2 ve flags3 korunur;idle başarı üretilmez.
- Ortak mod admission helper'ı taint'i de reddeder;dirty kontrolü eklenmez.

Taint bu açılış ömründe kalıcıdır. **Bu bir rollback veya tamamlanmış hata
toparlanması değildir.** Kısmi raw/recorder alias değişikliği hâlâ vardır.
Yeni guard ham buffer'ı eski haline getirmez;diğer reader'ların,Play/Save/New
ve bütün stock UI yollarının bu durumda güvenliği ayrıca doğrulanmalıdır.
Doğrulanmış bir taint temizleme/kurtarma yolu henüz yoktur. Bu nedenle bu
build bir donanım test paketi olarak sunulmaz.

Ek kalıcı RAM0;mevcut1088B rezervasyon aynı. Wrapper stack32B;çağırdığı native
işlevlerin stack'i buna eklenir. Genel en kötü stack/zaman kanıtı değildir.
Stock dosya,vektör/kimlik ilk512B değişmez. Custom filesystem eklenmedi.

## Doğrulama

Her mod ayrı native reset kullanır. Önce native Save tamamlanır;tam Load
kontrolü169092B/status0/tek apply verir ve bütün raw kayda eşittir. Ardından
yeniden düzenlenip741B/status4 enjekte edilir. Prefix kayıtla,suffix hata
öncesi canlı RAM'le tam karşılaştırılır. Hiç RAM onarımı veya fault/queue
temizliği yapılmaz. Hata sonrası Close,phase2/flags3/taint1 ve mod retleri
ölçülür. Başarılı kontrol sonrasında iki yönlü mod geçişi açıktır.

Üç sentetik test ayrıca status2/4/5,başarılı/başka receiver fallback'i,
ABI/stack hizası ve phase zaten0 olan ayrı sentetik fixture'da taint'in iki
mod yönünü reddetmesini denetler. Sentetik phase0 fixture native hata
koşusunun sonradan onarılıp sürdürülmesi değildir.

Güncel koşu/sayım için STATUS.md ve bundle summary.json esas alınır.
Önceki159 ayrı test eski c9a87a9d image'ine aittir;bu yeni image için geçerli
regresyon sayısına taşınmaz. Verifier'a3 core+2 uzun native test eklendi;
suite kurulumu testlerin çalıştırıldığı anlamına gelmez.

31 hedefli paket regresyonu ve6 sınırlı Faz1 ölçütü de çalıştırılır. Eski
`test_primask_restored_and_commit_serialized_voice_calls_outside_lock`,memory-
write hook içinde CPU register okuduğu için bu koşuda dışlanır;PASS sayılmaz.

İlk keşif16 Main turunda Save bitmeden durdu;sonlu IRQ/Main ilerlemesiyle tamamlandı.
Diğer iki kurulum koşusu yetersiz ADC credit ve yanlış adapter metodu nedeniyle
başarısız oldu. Bunlar firmware hatası sayılmadı;loglar saklandı. Asıl kısa
okuma karşı örneğinde native Save tamamlanması görülmeden test ilerlemedi.

## Komutlar

`.venv\Scripts\python.exe` ile,`-O` olmadan:

- `scripts/build_recovery_candidate.py`
- `scripts/probe_recovery_load.py logs/recovery-load-short-read-20261031/probe-normal 0`
- `scripts/probe_recovery_load.py logs/recovery-load-short-read-20261031/probe-sequencer 1`
- `scratch/recovery_load_regression.py`
- `scripts/audit_recovery_candidate.py logs/recovery-load-short-read-20261031/audit-final`

Probe dosyaları mevcut çıktı klasörünü reddeder;tekrar için yeni klasör seç.
PASS sonrası bile M7 NO-GO için SystemExit2 döner;Windows runner exit1
gösterebilir. Eski aday ve manifest/scope `before-build/` altında korunur.

**Tek sonraki iş:**Bu tainted native oturumda stock Projects/Load/New girişlerinin
erişilebilirliğini ve tam başarılı yeniden yükleme için güvenli taint temizleme
sınırını sınamak. RAM'i onararak ilerleme üretme. Tie,RX–MSC–power ve genel
kaynak/tam M7 regresyon gruplarını bu işe karıştırma.
