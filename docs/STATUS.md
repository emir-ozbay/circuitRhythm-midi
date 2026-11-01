# Güncel durum — 1 Kasım 2026 / Yeni sohbete devir

**M7 NO-GO. Kaynaklar diskteki test edilmiş adaydan ileride; yeni Load/New
kurtarma yolu henüz paketlenmedi veya native emülasyonla doğrulanmadı.**
Bu belge güncel durumun ana kaynağıdır. Diğer raporların tarihsel başlıkları
bu durumu geçersiz kılmaz. Faz1 kapsamı `SCOPE.md`; teknik devam haritası
[HANDOFF-LOAD-RECOVERY-5706.md](HANDOFF-LOAD-RECOVERY-5706.md).

## Kaynak, paket ve kanıt ayrımı

| Katman | Gerçek durum |
| --- | --- |
| Diskteki SYX | `build/circuitrhythm-5706-phase1-recovery.syx`; önceki karantina adayı, değişmedi |
| SYX SHA256 | `272a8128ba159e32c7457f0f123cb148c9e2d93a7803cbd9be327dccc5bb5cc1` |
| Image SHA256 | `dcc89001f753947acf8873c10b594b9386c5389b2d7e76c1097a6a6082e1791e` |
| CRC / manifest | MPEG2 `985753F7`; 46 patch, stock'a göre 8009 değişen bayt |
| Diskteki adayın davranışı | Short-read yanlış başarı apply'ı engellenir; native Close, phase2/flags3 ve kalıcı taint. Kullanıcıya açık kurtarma yok |
| Güncel kaynak | Close kimliğiyle bağlı Projects Load/New kurtarması yazıldı; tamamlanmamış entegrasyon |
| Yeni kaynak için kanıt | Sohbet tool çıktısında 4 sentetik test PASS; kalıcı koşu raporu bulunamadı. Yeni exact-SYX/native sonuç yok |
| Son native kanıt | Eski diskteki adayda Normal/Sequencer iki canonical re-entry testi; yeni kurtarma kodunu içermez |

Stock SHA256 sabit:
`11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf`.
Devirde stock/SYX/image hash, paket CRC ve ilk512B eşitliği tekrar okuma ile
doğrulandı. Firmware build veya test çalıştırılmadı; fiziksel erişim yok.

## Bu sohbette tamamlananlar

- Native alt-read741B girdisiyle stock `472A8` köprüsünün hata4'ü başarı
  apply'ına çevirdiği kanıtlandı. Önceki düzeltme bunu engelledi; kısmi raw
  alias değişikliği geri alınmadı. Ayrıntı ve kanıt:
  `MIDI-RECOVERY-LOAD-SHORT-READ-5706.md`,
  `logs/recovery-load-short-read-20261031/{summary.json,hashes.json}`.
- Eski adayda Projects açılır; controller flags bit1 ve ayrıca dispatcher
  phase2 nedeniyle Load/New pad'i reddedilir. Tanısal backend tam Load raw'ı
  geri getirir; sonraki UI Load/New çalışır, taint yine kalır. Bu kullanıcı
  kurtarması değildir. Kanonik sonuçlar:
  `logs/recovery-load-reentry-20261101/probe-normal-final/report.json` ve
  `probe-sequencer-final/report.json`; bağlayıcı `summary.json`, `hashes.json`
  ve `apply-boundaries.json`. Her mod360 IRQ/tam Main, heap/tahsis sabit,
  devam aşamasında ek NOR yazımı/MIDI fault yok. Eski adayın audit'i PASS.
- Yeni kaynakta yalnız eşleşen Close sonrası durmuş/sahipsiz Projects
  Load/New kabulü; tekrar hatada karantina; tam read/defaults ve native apply
  dönüşünden sonra taint temizliği; gerçek pad-up'a kadar mod reddi yazıldı.
  **Bunlar uygulanmış kaynak niyetidir; native başarı iddiası değildir.**

Eski aday için tarihsel toplam35 ayrı paket testi vardır; hepsi son koşuda
yeniden çalıştırılmadı. Tarihsel verifier172/core155 yalnız collection'dır.
Bu sayılar yeni kaynaklara taşınmaz. Eski `c9a87a9d…` adayındaki159 test de
yeni adayın sayımı değildir. Güncel suite sayısı yeniden ölçülmedi.

## Tamamlanmamış entegrasyon

Değişen4 dosya: `src/midi_recovery_patch.py`, `src/seq_Patch.py`,
`scripts/recovery_load_test_support.py`, `tests/test_recovery_load_reentry.py`.
Yeni3 dosya: `src/project_load_recovery_patch.py`,
`scripts/recovery_load_recovery_test_support.py`,
`tests/test_project_load_recovery.py`.

Üretim builder'ının kullandığı `midi_recovery_patch` yeni guard'ı seçiyor;
fakat `scripts/build_recovery_candidate.py` rapor metadatası ile
`scripts/audit_recovery_candidate.py` hâlâ eski guard'ı kullanıyor. Audit'in
46 patch/152B/eski çağrı-yazı varsayımları yeni kodu denetlemiyor.
`tests/test_project_load_guard.py`, `tests/test_shared_project.py` byte
beklentileri ve `scripts/verify_recovery_candidate.py` test bağlantıları/
kapsam metni de uyarlanmalı. Yeni4 test henüz verifier'a bağlı değil.
Mevcut probe yeni test sınıfını çağırıyor ama eski açıklama taşıyor; mevcut
SYX ile kaynak image eşitliği beklenmemeli. Bu karışık durumda build/audit
başarısı veya yeni native PASS iddia edilmez.

## Başarısız varsayımlar ve açık sınırlar

- Controller pad'inin Projects handler'a ulaşacağı varsayımı yanlış çıktı;
  erken flags-bit1 reddi kanıtlandı. Başarılı Load sonrası ayrı Close
  bekleyen iki pilot da yanlış beklentiyle durdu: gözlenen başarı yolunda
  ayrı Close yok; bu tek başına sızıntı değildir.
- Setup UART listesi devam koşusuyla uzuyordu. Deep-copy snapshot ve
  tutarlılık assertion'ı ile düzeltildi; iki `*-final` raporu kanoniktir.
  Eski başarısız/superseded raporlar korunur; ayrı PASS sayılmaz.
- İlk short-read keşfinde erken Save bekleme sınırı, yetersiz ADC credit ve
  yanlış adapter metodu sorunları test kurulumuydu; firmware hatası değildi.
- Yeni Close cookie ABI'si, gerçek UI retry/New, busy sırasında gerçek
  pad-up, tüm apply dönüşü ve yeniden hata çevrimi birlikte native olarak
  henüz kanıtlanmadı. Sentetik apply stub'ı bunun yerine geçmez.
- 741B sınırı sentetik hata girdisidir. Native ARM/FatFs/worker yürütmesi
  fiziksel EOF/kart arızası, GPIO/event queue, gerçek zaman veya NVIC
  arbitrajı kanıtı değildir. RAM onarılarak başarı üretilmez.

## M7 kapanış listesi

İlerleme yeni rapor/test sayısıyla değil, kabul koşulu sağlanan engelle ölçülür.

| Engel / sıra | Somut çıktı ve kabul koşulu |
| --- | --- |
| 1a — Şimdiki tek hedef: Close sonrası Load/New kurtarması | Entegre kaynak + aynı hash'e bağlı SYX/manifest/audit; iki modda gerçek controller girdisiyle tekrar hata, tam Load, ikinci sayfada New, stale Close reddi ve held release. Taint yalnız tamamlanan native apply sonrası temizlenir; hata/uygunsuz girişte kapalı kalır; RAM onarımı yok |
| 1b — Kısmi alias güvenliğinin kalan sınırı | 1a sonrası tainted raw'ı kullanabilen Play/Save/ilgili reader girişlerinin dar erişim/etki kanıtı; karışık verinin güvensiz çalınması veya kaydı engellenmiş olmalı. Raw rollback varsayılmaz |
| 2 — Tie bitine native UI/stock Load erişimi | Desteklenen giriş zincirinden tie oluşturma/yükleme ve native Off/Stop kanıtı; sentetik bit yazısı erişilebilirliği kapatmaz |
| 3 — Birleşik MIDI/USB RX–MSC–power | Aynı native yaşam döngüsünde ilgili çakışma/iptal senaryoları, ownership ve kuyruk/nota kapanışı; izole eski PASS'ler birleşik kanıt sayılmaz |
| 4 — Genel RAM/stack/zaman bütçesi | 1–3 sonrası sabit adayda gerekçeli üst sınırlar, ölçülen paylar ve emülatörün ölçemediği fiziksel zaman sınırları açık; yalnız workload minimumu yeterli değil |
| 5 — Tam M7 regresyon ve donanım deneme paketi | Önceki engeller kapandıktan sonra tek sabit aday üzerinde gerekli tam suite, hash/CRC/range/vector denetimi, diff, test talimatı ve recovery planı; istisnalar açıkça karara bağlı. Ardından yalnız açık kullanıcı izniyle belirli fiziksel test |

**Tek sonraki somut iş:** Yazılmış dar Load/New kurtarmasının builder/audit/
test entegrasyonunu tamamla ve iki modda native kanıtla (1a). Diğer gruplara
atlama. Önce hızlı sentetik/ABI kontrolleri; sonra yeni adayın etkilenen
regresyonları ve native testleri. Ayrıntılı sıra/adresler HANDOFF dosyasında.

## Devir dosyaları ve bu turun komutu

Bu tur yalnız devir hazırlığıdır: STATUS, kısa teknik HANDOFF ve CHANGELOG
güncellendi; firmware/test kaynakları ve build çıktıları değiştirilmedi.
`.venv\Scripts\python.exe scratch/prepare_handoff_20261101.py` çalıştı;
test veya build başlatmaz. Kanıt:
`logs/handoff-20261101-load-recovery/reconciliation.json`,
`work-in-progress.diff`, `snapshot/` (düzenleme öncesi STATUS dahil).
218 önceki snapshot ve286 tarihsel evidence hash'i doğrulandı.
Kaynak fingerprint'i ve dosya bazında pin'ler reconciliation JSON'dadır.
`logs/recovery-load-recovery-20261101/` yalnız `before/`, `before.json`,
`previous-evidence.json` içeriyordu; yeni native rapor yoktu.
Eski kanıtlar yeniden yazılmadı. Yeni koşularda yeni çıktı klasörü kullan.
