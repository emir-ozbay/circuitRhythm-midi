from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
bundle=ROOT/'logs/recovery-load-short-read-20261031'
runs=[json.loads((bundle/f'probe-{name}/report.json').read_text()) for name in ('normal','sequencer')]
assert [r['mode'] for r in runs]==[0,1]
assert all(r['final']['taint']==1 and r['final']['phase']==2 for r in runs)
banner='''> Güncel1 Kasım /Load short-read — Stock köprünün hata4'ü başarı apply'ına
> çevirmesi native reset/file worker ile yeniden üretildi. Yeni guard yanlış
> başarıyı atlar,native Close ve kalıcı taint ile mod geçişini kapatır. Raw alias
> rollback/toparlanma çözülmedi. Yeni aday272a8128… /CRC985753F7;M7 NO-GO.
> Güncel sayım ve tek sonraki görev STATUS.md'de;ayrıntı
> [MIDI-RECOVERY-LOAD-SHORT-READ-5706.md](MIDI-RECOVERY-LOAD-SHORT-READ-5706.md).
> Alt bölümler tarihsel sonuçlardır.

---

'''
for name in ('docs/ROADMAP.md','docs/RECOVERY.md','docs/UI-TRACE-5706.md',
             'docs/PROJECT-LOAD-ALIAS-RISK.md','docs/MIDI-RECOVERY-CANDIDATE-5706.md',
             'docs/PHASE1-GO-GATES.md','docs/PHASE1-HARDWARE-TEST.md'):
    p=ROOT/name;old=p.read_text(encoding='utf-8');before=bundle/'before'/name
    before.parent.mkdir(parents=True,exist_ok=True);assert not before.exists();before.write_bytes(p.read_bytes())
    p.write_text(banner+old,encoding='utf-8')
status='''# Güncel durum — 1 Kasım 2026 /Load short-read karantinası

**Kısa okumanın yanlış başarıya ve mod kabulüne dönüşmesi düzeltildi.**
İki modda ayrı native reset/stock Save/tam Load kontrolü/741B kısa okuma
geçti. Kısmi raw alias değişikliği hâlâ vardır;başarı apply'ı artık çağrılmaz,
native Close çalışır,phase2/flags3/taint1 mod geçişini kapalı tutar.
Bu sınırlı korumadır;rollback veya güvenli toparlanma değildir.
**M7 NO-GO;fiziksel cihaz/port erişimi yok.**

## Geçerli aday

- `build/circuitrhythm-5706-phase1-recovery.syx`
- SYX SHA256:`272a8128ba159e32c7457f0f123cb148c9e2d93a7803cbd9be327dccc5bb5cc1`
- Image SHA256:`dcc89001f753947acf8873c10b594b9386c5389b2d7e76c1097a6a6082e1791e`
- CRC MPEG2 `985753F7`;46 patch/8009 değişen bayt;458552B image/630565B SYX.
- Stock SHA256:`11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf`.
- Stock/ilk512B korunur;1088B rezervasyon aynı,ek kalıcı RAM0.
- Önceki c9a87a9d adayı ve manifest/scope bundle `before-build/` içinde saklıdır.

## Bu tur kapanan doğrulama

Eski adayda native Save tamamlandıktan sonra ilk adım düzenlendi. Stock
`4113A`169092B ister;alt read isteği741B'ye sınırlandığında gerçek FatFs
byte/count üretir ve native üst API4 döndürür. `472A8` hatayı kaybedip
`381C8→37E3C` başarı apply'ını çağırıyordu. Raw+740 nota72→0;velocity96 ve
microstep1 canlı projeden kalır. Phase/flags0,taint0 ve mod0→1 kabulü görüldü.

Yeni152B guard,project Load receiver/destination kimliği eşleşen hatada
apply'ı atlar,bridge callback'i emekliye ayırır,native Close kuyruğa verir
ve state+64 taint'i set eder. Mode admission taint'i reddeder. Stock başarılı
Load ve diğer receiver fallback'i korunur. Wrapper stack32B;genel en kötü
stack/zaman iddiası yoktur.

| Kanıt | Sonuç |
| --- | --- |
| Yeni sentetik guard testleri |3 PASS;status2/4/5,ABI,fallback,iki yönlü taint reddi |
| Yeni exact-SYX native Load testleri |2 PASS;her mod ayrı reset |
| Tam okuma kontrolü /mod |169092B,status0,tek apply,tüm raw aynı;mode roundtrip açık |
| Kısa okuma /mod |741B,status4,apply0,Close1,phase2/flags3/taint1 |
| Hata sonrası raw |Yalnız offset740 değişir;prefix/suffix tam karşılaştırıldı |
| Mod retleri /mod |3;I/O sırasında ve hata sonrası;RAM onarımı yok |
| IRQ /tam Main /mod |216 /216 |
| Heap /tahsis |2004EA98 /2331;sabit |
| MIDI context/active/TX fault |000000 |
| Hedefli exact-SYX regresyon |31 PASS;3 yeni guard testiyle örtüşür |
| Sınırlı Faz1 ölçütleri |6 PASS |
| Bayt/range/CRC/CFG denetimi |PASS;46 patch/original-byte/vector kontrolleri |

**Yeni image üzerinde33 ayrı paket testi** ve6 sınırlı ölçüt çalıştırıldı.
Önceki159 test c9a87a9d image'ine aittir;yeni image'e taşınmaz ve tamamı
yeniden koşulmadı. Verifier170/core-only155 test içerir;15 uzun native test
core-only dışında. Bu suite sayıları çalıştırılma sonucu değildir.
Eski bir shared-project testi memory-write hook'ta CPU register okuduğu için
hedefli koşuda dışlandı;PASS sayılmadı. Tam M7 regresyonu açık.

## Kanıt sınıfı ve başarısız varsayımlar

Başlangıç nesneleri,worker,store,alias,Save/Load/FatFs/Close/callback ve
mod kısayolu ARM kodudur. **741B sınırı sentetik alt-okuma girdisidir**;
gerçek dosya169092B olarak kalır. Doğal EOF/FAT/kart arızası kanıtı değildir.
Save/Load backend girişleri doğrudan çağrılır;Projects UI/GPIO akışı değildir.
Sonlu TIM/ADC/DSP/UART/NOR modeli;NVIC/nested IRQ/DSP firmware/gerçek zaman,
USB RX–MSC–power ve fiziksel teslim kanıtı yoktur.

16 turda bitmeyen Save'i tamamlandı sayma varsayımı reddedildi. Bir kurulumda
ADC kredisi yetersizdi;birinde yanlış timer adapter metodu çağrıldı. Üç keşif
logu saklandı;ürün hatası/PASS sayılmadı. RAM onarılarak devam edilmedi.

## Açık işler ve tek sonraki görev

Taint bu boot ömründe kalıcıdır. Kısmi raw veri geri alınmaz;diğer reader,
Play/Save/New/Projects davranışı ve güvenli hata toparlanması doğrulanmadı.
Hata sonrası I/O fazı bilinçli olarak meşgul tutulur;tam ürün çözümü değildir.
Tie'nin native UI/Load erişimi,birleşik RX–MSC–power,genel en kötü RAM/stack/
zaman ve yeni image'in tam M7 regresyon/bundle grupları açıktır. Faz2 ayrıdır.

**Tek sonraki somut iş:**Tainted native oturumda stock Projects/Load/New
girişlerinin erişilebilirliğini ve tam başarılı yeniden yüklemenin güvenli
taint temizleme sınırını sınamak;RAM'i onararak ilerleme üretmemek.

## Dosyalar ve komutlar

Yeni:`src/project_load_guard_patch.py`,`scripts/recovery_load_test_support.py`,
`scripts/probe_recovery_load.py`,`tests/test_project_load_guard.py`,
`tests/test_recovery_load.py`. seq mode guard,recovery builder/audit/verifier,
shared-project byte kontrolü ve belgeler güncellendi. Tam diff/hash/kanıtlar:
`logs/recovery-load-short-read-20261031`.

`.venv\\Scripts\\python.exe` ile,`-O` olmadan:

- `scripts/build_recovery_candidate.py`
- `scripts/probe_recovery_load.py logs/recovery-load-short-read-20261031/probe-normal 0`
- `scripts/probe_recovery_load.py logs/recovery-load-short-read-20261031/probe-sequencer 1`
- `scratch/recovery_load_regression.py`
- `scripts/audit_recovery_candidate.py logs/recovery-load-short-read-20261031/audit-final`

Probe PASS olsa da M7 NO-GO için SystemExit2 üretir;Windows exit1 gösterebilir.
Tekrar için yeni kanıt klasörü seç. Ayrıntı:
[MIDI-RECOVERY-LOAD-SHORT-READ-5706.md](MIDI-RECOVERY-LOAD-SHORT-READ-5706.md).
'''
assert all(r['cycles']==216 for r in runs)
(ROOT/'docs/STATUS.md').write_text(status,encoding='utf-8')
change='''## 2026-11-01 — Contain native project Load short-read false success

- Reproduced on the previous exact SYX with native reset objects,Save,FatFs,
  Content worker and Main result delivery:4113A returns4 after a741B lower-read
  limit,but472A8 discards it and381C8 calls successful apply. The first live
  pattern tuple becomes mixed and the mode shortcut is admitted. This is
  explicit lower-read fault input,not a physical EOF/card failure claim.
- Added a152B project-receiver/destination guard at472A8. Failed reads retire
  the callback,queue native Close and latch existing state+64 taint,retaining
  stock busy phase/flags. Mode admission rejects taint;successful and foreign
  callbacks retain stock behavior. No extra reserved RAM;32B wrapper stack.
  Live alias mutation is NOT rolled back and recovery is NOT complete.
- Both modes pass fresh native-reset complete-read controls and short-read
  containment,216 IRQ/Main cycles each,with no RAM repair or instruction stub.
  Three synthetic guard tests and31 overlapping packaged regressions pass,
  plus six scoped criteria and byte/range/CRC audit.33 distinct tests on the
  NEW image;the prior159 are not carried forward. Full suite170/core155 is
  collection only. One historical register-reading write-hook test excluded.
- New SYX272a8128… /CRC985753F7:46 patches,8009 changed bytes. Stock and
  vector/identity are unchanged. Previous candidate/evidence retained.
  Native failed-Load UI/recovery,alias rollback and full M7 remain open.
  No physical device access;M7 NO-GO. See MIDI-RECOVERY-LOAD-SHORT-READ-5706.md.

'''
p=ROOT/'CHANGELOG.md';p.write_text(change+p.read_text(encoding='utf-8'),encoding='utf-8')
