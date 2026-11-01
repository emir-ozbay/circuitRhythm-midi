# Load/New kurtarma — teknik devir haritası

1 Kasım 2026. Güncel durumun tek ana kaynağı `STATUS.md`; bu dosya yalnız
sonraki işte tekrar keşfi önleyen adres, kaynak ve çalışma sırasıdır.
**M7 NO-GO.** Yeni recovery kaynak kodu ≠ diskteki test edilmiş SYX.

## Kısa okuma sırası

`AGENTS.md` → `START-HERE.md` (tarihsel kurulum talimatlarını tekrarlama) →
`docs/SCOPE.md` → `docs/STATUS.md` → bu dosya → `docs/ROADMAP.md`,
`docs/RECOVERY.md`, `docs/UI-TRACE-5706.md` güncel yönlendirmeleri.
İlgili ayrıntı için yalnız `MIDI-RECOVERY-LOAD-SHORT-READ-5706.md` ve
`MIDI-RECOVERY-LOAD-REENTRY-5706.md`. Bu iki rapor eski adayı anlatır.

## Kaynakların bulunduğu nokta

- `src/midi_recovery_patch.py` yeni `project_load_recovery_patch` modülünü
  entegre ediyor. Eski `src/project_load_guard_patch.py` korunuyor; builder
  scope metadatası/audit/eski testler hâlâ ona bağlı. İki guard'ı birlikte
  patch setine ekleme; aynı site/cave'i kullanıyorlar.
- `src/project_load_recovery_patch.py`: hata bridge'i, Close callback'i,
  controller pad-down/up, New callback ve apply wrapper'ları; yardımcı
  bounded store-read ve admission. Ek rezervasyon istemiyor; mevcut1088B
  içindeki eski pasif alanları kullanıyor. Bu sahiplik varsayımını/audit'i
  tamamla; yeni kaynak için genel stack/zaman kanıtı yok.
- `src/seq_Patch.py`: recovery HELD `+60`, stage `+65`; mevcut taint `+64`.
  `c_midi_inputs_idle` HELD'i de reddediyor. Tam apply bitse bile kurtarma
  pad'i bırakılmadan mod geçişi amaçlanmıyor.
- `tests/test_project_load_recovery.py`: 4 sentetik test; Close descriptor/
  generation/status/duplicate/wrap, admission retleri, iki sayfa/held/release/
  unmasked Load, apply yetkisi. Load/Close stub; apply testi documented son
  store'ları sağlayan stub kullanır. Native test değil. Sohbet çıktısında
  PASS görüldü; kalıcı koşu raporu yok; bu devirde tekrar çalıştırılmadı.
- `scripts/recovery_load_test_support.py`: eski tam read/short-read helper'ı,
  yeni hook'ların tam4B farklarını stock-window beklentisine ekliyor. Bitmiş
  one-shot hook'ları kaldırır; `s.load_uart` aynı peer'ı saklar; UART raporu
  deep-copy'dir. Host RAM onarımı değildir.
- `scripts/recovery_load_recovery_test_support.py`: yazılmış, çalıştırılmamış
  native devam senaryosu. `tests/test_recovery_load_reentry.py` artık bunu
  kullanır. Aynı isimli eski test raporları eski test gövdesine aittir.
  Eski helper `recovery_load_reentry_test_support.py` tanısal tarihçe olarak
  korunur; yeni UI recovery helper'ıyla karıştırma.

## Bilinen native harita (adresler 5706, hex)

| İşlev / alan | Adres / davranış |
| --- | --- |
| Read/result bridge | `0804113A` üst read; `080411BE` alt read; `0802AE32` sonuç; `080472A8→080381C8→08037E3C` eski başarı zinciri |
| Short-read girdisi | Alt çağrıda yalnız R2=741; gerçek dosya169092B. FatFs byte/count sağlar, üst read hata4 üretir. Raw+740 karışık tuple sınırı |
| Native Load | `08037B8C(P,slot,flag)`; recovery controller girişinden flag1. Eski doğrudan flag0 backend probe UI kanıtı değil |
| New/defaults/apply | `08037C84→08032DB2→080378C6→08037E3C`; tüm apply sonrası `08038798` continuation da dönmeli |
| Close | `080460C8(descriptor,callback,cookie)`; `08041906/08041916` file Close; `0802B064` Main callback ABI. Cookie callback entry SP+4 arg6; yeni protokolde native doğrulaması açık |
| Controller pad girişleri | Down `0803D7FE`, up `0803D896`; native bitmap down/up `08051B7A/08051BB8` |
| Eski UI retleri | Controller `0803D814` flags bit1; direct Projects `0804F09E` sonrası dispatcher `080385FE→080386D6` phase2 reddi |
| Aktif store word adresi | `0803FC58`; sonucu değer değil aktif-bank word pointer'ı |
| Native nesneler (önceki resetlerde) | P=`20042FF4`, raw=`20012C48`, ctrl=`200487C8`, Projects=`2004DA10`; testte nesneleri session'dan al, sabit RAM seed yapma |
| Project alanları | P+44 metadata store, +48 phase store, +4C flags store, +64 bridge; operation word0 opcode4/slot byte1, phase word1 byte0; metadata word11 byte0 aktif slot |
| Controller alanları | +0C Shift store, +14 activeview (Projects6), +18 transport, +8C project flags store, +9C native pad bitmap |
| Projects alanları | +20 metadata, +24 ready (önce14, bit3), +28 phase, +36 page byte; +18/+1C/+2C modifier store'ları |
| Girdiler | Projects26, Shift27, SampleRec18; Projects page1 button19; pad1/page1 mantıksal slot33 |
| Kimlikler | Project vt=`08066F64`, Load callback vt=`08066FA0`, controller vt=`080672E4` |
| Yeni hook original4B | `472A8:10b5039a`, `3D7FE:70b50646`, `3D896:38b50446`, `37C84:10b50c46`, `37E3C:f8b50446` (adreslerde `080` öneki) |
| Cave / state | `[0807C000,0807D400)`; recovery RAM base=`2004F320`, seq state=`2004F660` |

Yeni seq alanları: OWNER44, DESCRIPTOR48 (12B), EPOCH54, SLOT58, BRIDGE5C,
HELD60, TAINT64, STAGE65. CLEAN0/CLOSING1/READY2/RETRY3/READ_OK4/NEW_OK5/
DEAD6. Bunlar yeni kod tasarımıdır; native çalışma sonucu diye aktarılmaz.
Close descriptor+epoch eşleşmesi READY verir; taşma/hata kapalı kalır.
Admission atomik bölümünden çıkıp IRQ'ları açtıktan sonra native Load çağrılır.
Phase/flags'ı sahte idle yaparak retry açılmaz. Normal Load busy sırasında
pad-up'ı kaybetmemek için ek release yolu da yazıldı; taint0 normal akışa
etkisi ayrıca regresyonla denetlenmeli.

## İlk tek teknik hedef ve bağımlılık sırası

STATUS kapanış1a: **mevcut dar kurtarma kodunu entegre edip doğrula**.
Yeni özellik veya bağımsız araştırma açma.

1. Kısa hash/diff kontrolü. `logs/handoff-20261101-load-recovery/` source
   snapshot/pin'leri ve `work-in-progress.diff` ile başla. Kaynakları geri
   alma, checkout temizleme, kurulumu yeniden başlatma. Stock pin uyuşmazsa dur.
2. Builder metadata/audit/verifier/eski Load guard ve shared-stock byte
   testlerini yeni davranışa bağla. Audit'i yalnız sayıları değiştirerek
   geçirme: beş hook/original byte, cave sınırı, branch/call hedefleri,
   CFG/ABI ve8B stack hizası, PRIMASK restorasyonu, state write sınırları ve
   ham proje RAM'ine doğrudan yazı olmaması incelensin. Admission'ın CPSID
   süresini ve native I/O'nun kilit dışında kaldığını kanıtla.
3. Önce `.venv\Scripts\python.exe -m unittest discover -s tests -p
   test_project_load_recovery.py -v` ve etkilenen eski testler. Yeni sonucu
   yeni klasöre kaydet. Busy stock pad-up, stale/mismatched/duplicate Close,
   Close queue/failure ve pointer/IRQ-context sınırlarının mevcut testlerdeki
   boşluklarını değerlendir; gerçek güvenlik açığı varsa uygun testi ekle.
4. Sonra `scripts/build_recovery_candidate.py` ile yeni SYX/manifest/scope;
   `scripts/audit_recovery_candidate.py <YENI_KLASOR>` ve etkilenen packaged
   testler. `scratch/recovery_load_regression.py` sınıf seçimi örnektir;
   eski sabit çıktı klasörüne yazmak için çalıştırma. `scratch/count_load_reentry_suite.py`
   de eski yollara/sayılara bağlıdır; güncellemeden çalıştırma.
5. `scripts/probe_recovery_load_reentry.py <YENI_KLASOR> 0` ve ayrı klasörde1:
   açıklamasını yeni kapsama uyarla veya açık isimli yeni wrapper kullan.
   Test sınıfı zaten yeni senaryoya bağlı. Önce packaged image==source image
   denetimi; aynı sabit SYX, bağımsız resetler. Bağımsız süreçler paralel
   çalışabilir; aynı çıktı klasörü kullanılmaz. Eski canonical süreler241.128s/
   243.052s idi; yeni senaryonun süresi ölçülmedi.
6. Yeni hata/varsayım varsa kanıtı ve çalıştırılan kaynak/image'i koru;
   RAM/fault/phase/queue onarıp aynı koşudan PASS üretme. Düzeltme sonrası
   etkilenen testleri yeni klasörlerde çalıştır. STATUS ve CHANGELOG'u gerçek
   sonuç, sınır ve tek sonraki görevle güncelle.

Native senaryo: eski setup Save/tam Load/741B hata → matching Close READY →
Shift/uygunsuz pad/mod retleri → UI retry'da ikinci741B hata ve karantina →
UI tam Load (pad basılıyken taint apply sonrası temizlenir ama mod reddedilir)
→ gerçek pad-up/mod roundtrip → normal UI'den üçüncü short-read → page1 boş
slot33 New/defaults/apply → mod roundtrip. Helpers IRQ66 `timer.deliver()` ve
tam Main `s.cycle()` kullanır; borç/RAM düzeltmez, aynı UART peer korunur.

Kapanış: iki modda native sonuçlar; read/count/status ve Close identity izi;
taint'in yalnız yetkili tam apply dönüşünde temizliği; tekrar hatada
phase2/flags3/taint1; gerçek release; raw/saved eşitliği ve alias geçerliliği;
istenmeyen I/O/NOR/ek tahsis/MIDI fault yok; stack/image ve patch audit PASS.
Sentetik/native/fiziksel sınırlar raporda ayrılır. **Bu1a'nın kapanması1b'yi
veya M7'yi otomatik kapatmaz.**

## Tekrarlanmaması gerekenler ve araç seçimi

- Başarılı Load'dan sonra ayrı Close arama; bu pencerede görülmedi ve
  bekleyen pilotlar test varsayımı yüzünden durdu. Başarısız Load Close'u
  ve yeni identity callback'i ayrı kanıtlanmalı.
- Stock UI'nin phase2/flags3'te backend'e erişeceğini varsayma; iki ayrı ret
  zaten kanıtlandı. Backend adapter çağrısını UI recovery diye sunma.
- UART setup snapshot'ını canlı listeye bağlama; önceki deep-copy düzeltmesini
  koru. `probe-*-final` dışındaki eski PASS raporları canonical değil.
- Unicorn memory-write hook içinde CPU register okuma. Eski shared test
  `test_primask_restored_and_commit_serialized_voice_calls_outside_lock`
  bunu yapıyor ve önceki dar koşudan dışlanmıştı. Tam M7 öncesi güvenli
  gözleme uyarlanmalı veya açıkça çözüme bağlanmalı; sessizce PASS sayılmaz.
- Şimdiki darboğaz yeni tersine mühendislik değil, yazılmış kodun entegrasyon/
  native doğrulaması. Mevcut Capstone/Unicorn ve harita yeterli. Belirli bir
  ABI/xref bilinmeyeni kalırsa Ghidra'yı dar değerlendirmek mümkün; kurulum/
  tüm-image analizi başlatma. Decompiler hipotezdir, komut/native iz doğrular.
- Dış kaynak şimdi gerekli görünmüyor. Belirli açık fonksiyon için gerekirse
  önce sabitlenmiş `analysis/sources/` ve `analysis/provenance.json`; sonra
  Rhythm/sürüm/adres/RAM sahipliği/lisans denetimiyle dış kaynak. Tracks
  adreslerini taşıma, Circuit Remix/Arrhythmia özelliklerini kapsama ekleme.

`.venv\Scripts\python.exe`, assertions açık; Python -O yok. Yerel geri
alınabilir iş yetkili; ajan/başka sohbete mesaj/fiziksel MIDI–USB erişimi yok.
Git sahiplik uyarısı olursa salt okunur komutta bu repo için `git -c
safe.directory=C:/Users/emiro/Desktop/circuitRhythm-midi ...` kullanıldı;
global güven ayarı değiştirilmedi. Büyük kirli/untracked çalışma ağacını koru.
