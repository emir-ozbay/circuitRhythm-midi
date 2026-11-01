"""Write current handoff only after both native re-entry reports exist."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'logs/recovery-load-reentry-20261101'
runs=[json.loads((B/f'{name}/report.json').read_text()) for name in ('probe-normal-final','probe-sequencer-final')]
assert [r['mode'] for r in runs]==[0,1] and all(r['packaged_tests']==1 for r in runs)
cycles='/'.join(str(r['total_cycles']) for r in runs)
extensions='/'.join(str(r['cycles']) for r in runs)
syx=runs[0]['syx_sha256'];image=runs[0]['image_sha256']
assert all(r['syx_sha256']==syx and r['image_sha256']==image for r in runs)
status=f'''# Güncel durum — 1 Kasım 2026 / Taint sonrası Load–New erişimi

**Karantinadan stock UI ile Load/New kurtarması şu anda mümkün değil.**
Projects görünümü açılıyor; pad isteği controller'da flags bit1 nedeniyle
kesiliyor. Controller'ı tanısal olarak aşan native Projects çağrısı da
dispatcher'da phase2 nedeniyle reddediliyor. İki modda doğrulandı.
**M7 NO-GO; fiziksel cihaz/port erişimi yok.**

## Geçerli aday — değişmedi

- `build/circuitrhythm-5706-phase1-recovery.syx`
- SYX SHA256: `{syx}`
- Image SHA256: `{image}`
- CRC MPEG2: `985753F7`; 46 patch, stock'a göre 8009 değişen bayt.
- Stock SHA256: `11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf`.
- Stock, ilk 512 bayt, tüm firmware kaynakları ve build dosyaları aynı.
  1088B rezervasyon aynı; ek firmware RAM veya kod değişikliği yok.

## Bu tur uygulanan ve doğrulanan

Yeni re-entry testi önce mevcut native Save/tam Load/741B short-read
senaryosunu aynı reset ömründe çalıştırır. Bitmiş tek seferlik hata hook'u
kaldırılır; uygulama RAM'i, taint, phase, kuyruk veya fault onarılmaz.
Aynı UART peer ve native IRQ/Main akışıyla devam edilir.

| Kontrol | Sonuç |
| --- | --- |
| Yeni exact-SYX testleri | 2 PASS; Normal ve Sequencer ayrı reset |
| Projects tuşu | Görünüm6 açılır; ready14, phase2, flags3, taint1 |
| Dolu slot1 / boş slot2 pad isteği | Controller `3D814` busy bit1'de ikisini de keser |
| Tanısal doğrudan Projects handler | İki slot da `385FE→386D6` phase2 kontrolünde reddedilir |
| Bu dört ret sırasında | Raw/metadata/I/O/NOR değişmez |
| Tanısal doğrudan Load backend | 169092B/status0; raw kayıtla tamamen aynı; native apply |
| Başarılı backend Load sonrası | Gözlem aralığında ayrı Close çağrısı yok; phase0 dosya retirement kanıtı değil |
| Backend sonrası | Phase0/flags0; taint1 kalır, mod geçişi hâlâ reddedilir |
| Ardından stock UI Load | Tam okuma ve native apply; taint1 kalır |
| Ardından stock UI New | Boş slot2; native timer/defaults/apply, dosya read yok; taint1 kalır |
| Alias'lar | 8 recorder + 8 player aynı raw pattern adreslerine bağlı |
| IRQ / tam Main, Normal–Sequencer | {cycles}; her birinde 216 kurulum + {extensions} devam |
| Heap / tahsis | `2004EA98` / 2331; ek tahsis yok |
| Devam aşamasında NOR / MIDI fault | Ek NOR yazımı yok; context/active/TX fault `000000` |
| Bayt/range/CRC denetimi | PASS; aday değişmedi |

Doğrudan backend çağrısı controller ve dispatcher korumalarını aşan **tanısal
test girdisidir**. Kullanıcıya açık kurtarma veya ürün düzeltmesi sayılmaz.
Sonraki UI Load/New kontrolleri ancak bu native tam yükleme phase/flags'ı
sıfırladıktan sonra yapılır. Host RAM sıfırlaması kullanılmaz.

Bu tur **2 yeni ayrı test PASS**; son canonical koşular iki modu kapsar.
Aynı iki testin önceki PASS raporları aşağıdaki snapshot düzeltmesiyle yenilendi;
bu tekrarlar ayrı test sayısına eklenmez. Aynı image üzerindeki önceki 33 ayrı testle
birlikte toplam **35 ayrı paket testi** kanıtı vardır; 35'inin tamamı bu tur
yeniden koşulmadı. Önceki 6 sınırlı Faz1 ölçütü yeniden koşulmadı.
Verifier **172**, core-only **155** test içerir; 17 uzun test core-only dışında.
Bu sayılar suite'in çalıştırıldığı anlamına gelmez. Eski image'deki 159 test
bu adayın sayımına taşınmaz; tam M7 regresyonu açık.

## Başarısız varsayım ve kanıt sınırı

İlk pilot, controller pad'inin doğrudan Projects handler'a ulaşacağını
varsaydı. Native controller'ın daha erken flags-bit1 reddi görüldü; test
düzeltildi. Pilot ve çalıştırılan kaynakları saklandı; firmware hatası veya
PASS sayılmadı. İkinci pilot çifti başarılı Load sonrası ayrı Close beklediği
için durdu. Bu pencerede native başarı yolu Close çağırmaz; bu gözlem tek
başına kaynak sızıntısı değildir. Üç başarısız pilot korundu.

Ardından iki test PASS oldu; ancak setup UART IRQ listesi aynı peer'ın sonraki
olaylarıyla uzuyordu (setup credit96, listede328 olay). Test helper'ı raporu
deep-copy ile sabitleyecek şekilde düzeltildi; snapshot tutarlılığı assertion'ı
eklendi ve iki mod yeni `*-final` klasörlerinde tekrar geçti. Önceki PASS
raporları ve kaynak sürümü saklandı; native sonuç değişmedi.

Başlangıç, worker, FatFs, byte/count, apply, defaults ve Close native ARM'dır.
741B alt-okuma sınırı sentetik girdidir; doğal EOF/kart arızası kanıtı değildir.
Controller vtable girişi GPIO/event-queue testi değildir. Tanısal handler ve
backend girişleri UI kanıtından ayrıdır. Sonlu TIM/ADC/DSP/UART/NOR modeli;
gerçek zaman, NVIC arbitrajı, birleşik USB–MSC–power ve fiziksel kanıt yoktur.

## Açık kalan ve tek sonraki görev

Tam okuma sonrası raw eşitliği, native apply ve native idle yayını gözlendi;
**taint temizleyen güvenli bir protokol henüz uygulanmadı veya kanıtlanmadı.**
Taint bu boot ömründe kalıcıdır. Kısmi alias geri alınmaz. Diğer reader'lar,
Play/Save güvenliği, tie UI/Load, birleşik RX–MSC–power, genel en kötü
RAM/stack/zaman ve tam M7 bundle açıktır. Faz2 kapsam dışıdır.

**Tek sonraki somut iş:** Native Close tamamlanması doğrulandıktan sonra
karantinada yalnız stock Load/New kurtarma isteğini kabul eden dar yolu
uygulayıp sınamak; tam okuma/defaults ve apply tamamlanmadan taint'i
temizlememek, tekrar hata alındığında karantinayı korumak. RAM onarımı yok.

## Dosyalar, komutlar ve kanıt

Yeni: `scripts/recovery_load_reentry_test_support.py`,
`scripts/probe_recovery_load_reentry.py`, `tests/test_recovery_load_reentry.py`.
Load test helper'ına hook ömrü/sabit rapor snapshot'ı, verifier'a iki uzun
test eklendi. Firmware kaynakları değişmedi. STATUS, CHANGELOG ve güncel
yönlendirme başlıkları yenilendi.

`.venv\\Scripts\\python.exe` ile, `-O` olmadan:

- `scripts/probe_recovery_load_reentry.py logs/recovery-load-reentry-20261101/probe-normal-final 0`
- `scripts/probe_recovery_load_reentry.py logs/recovery-load-reentry-20261101/probe-sequencer-final 1`
- `scripts/audit_recovery_candidate.py logs/recovery-load-reentry-20261101/audit`
- `scratch/count_load_reentry_suite.py` — yalnız collection.

Probe PASS olsa da M7 NO-GO için SystemExit2 üretir; Windows exit1 gösterebilir.
Tekrar için yeni kanıt klasörü seç. Yeni bundle:
`logs/recovery-load-reentry-20261101/{{hashes.json,summary.json,apply-boundaries.json}}`.
Önceki 112 kanıt dosyasının hash'i korundu. Ayrıntı:
[MIDI-RECOVERY-LOAD-REENTRY-5706.md](MIDI-RECOVERY-LOAD-REENTRY-5706.md).
'''
(ROOT/'docs/STATUS.md').write_text(status,encoding='utf-8')
detail=f'''# Taint sonrası native Load/New erişimi — 5706

1 Kasım 2026. Firmware aynı: SYX `{syx}`, CRC `985753F7`.
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

Normal/Sequencer toplam IRQ ve tam Main sayısı `{cycles}`; her birinde 216
kurulum ve `{extensions}` devam turu. İki yeni exact-SYX test PASS. Ek heap
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
'''
(ROOT/'docs/MIDI-RECOVERY-LOAD-REENTRY-5706.md').write_text(detail,encoding='utf-8')
entry=f'''## 2026-11-01 — Characterize tainted native Load/New re-entry

- Added two exact-SYX native reset tests, one per runtime mode. They continue
  the Save/full Load/short-read quarantine session without RAM repair and
  retire only the completed one-shot fault hooks, reusing the UART peer.
- Projects opens, but stock controller flags bit1 blocks pads before the
  Projects handler. Separate direct-handler probes confirm dispatcher phase2
  rejection. An initial contrary test assumption failed; pilot and sources
  are retained and are not classified as a firmware defect.
- A labeled diagnostic backend retry restores all saved raw bytes through
  native FatFs/apply, while taint remains latched. Successful Load has no
  separate Close in the observed window; an initial contrary assertion failed
  in two retained pilots. This does not itself establish a leak. Subsequent controller
  UI Load and empty-slot New complete and still reject mode changes. These
  controls do not provide user-accessible quarantine recovery.
- Two new distinct tests PASS; {cycles} IRQ/Main iterations, stable 8 recorder and
  8 player aliases, no additional allocations/NOR writes/MIDI faults in the
  continuation. Byte/range/CRC audit PASS. Same-image cumulative evidence is
  35 distinct tests; not all rerun. Verifier172/core155 is collection only.
- Fixed setup telemetry aliasing: its UART IRQ list must be a deep-copy
  snapshot before reusing the peer. Added a consistency assertion and reran
  both modes; superseded passing reports and their sources are retained.
- Firmware sources and SYX272a8128…/CRC985753F7 are unchanged. Safe taint
  clearing and UI recovery remain open; next is a Close-confirmed narrow
  Load/New recovery path with repeated-error containment. M7 NO-GO.
  See docs/MIDI-RECOVERY-LOAD-REENTRY-5706.md.

'''
p=ROOT/'CHANGELOG.md';p.write_text(entry+p.read_text(encoding='utf-8'),encoding='utf-8')
banner='''> Güncel 1 Kasım / Taint sonrası Load–New — İki modda native UI erişimi sınandı.
> Projects açılır; controller flags bit1 ve ayrıca dispatcher phase2 Load/New'ü
> engeller. Tanısal tam backend yükleme ve sonraki UI Load/New taint'i temizlemez.
> Bu bir kullanıcı kurtarma yolu değildir. Firmware272a8128… aynı; M7 NO-GO.
> Güncel sayım ve tek sonraki iş STATUS.md'de; ayrıntı
> [MIDI-RECOVERY-LOAD-REENTRY-5706.md](MIDI-RECOVERY-LOAD-REENTRY-5706.md).
> Alt bölümler tarihsel sonuçlardır.

---

'''
for name in ('ROADMAP.md','RECOVERY.md','UI-TRACE-5706.md'):
    p=ROOT/'docs'/name;p.write_text(banner+p.read_text(encoding='utf-8'),encoding='utf-8')
print('STATUS, CHANGELOG and re-entry report updated from two passing reports')
