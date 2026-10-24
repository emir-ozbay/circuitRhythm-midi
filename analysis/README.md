# Circuit Rhythm MIDI modu — ilk teknik fizibilite

Tarih: 24 Ekim 2026. Hedef: resmî Circuit Rhythm build 5706 üzerinde, ilgili stock sequencer davranışlarını koruyarak harici cihazlara MIDI gönderen ek mod. Kullanıcının bilgisayarı Windows 11. Fiziksel cihaz bu analiz ortamına bağlı değil.

**Yeni kapsam ve testler:** Kullanıcı tek uzun pattern ve ayrı proje alanını seçti. Sonraki sınır testleri için [LONG-PATTERN-TESTS.md](LONG-PATTERN-TESTS.md) dosyasına bak. Aşağıdaki ilk fizibilite, 32-adım temelinden hareket eder; uzun pattern belleğinin çözüldüğü anlamına gelmez.

## Sonuç

MIDI sequencer modu ve 32-pad adım görünümü için somut, doğrulanmış kod bağlantıları mevcut. Sıfırdan firmware veya ses motoru yazmak gerekmiyor. Bu çalışma kullanılabilir bir mod üretmedi; dosya çözümleme, kaynak incelemesi, statik adres doğrulaması ve seçilmiş stock fonksiyonların emülasyonunu tamamladı.

Öneri: stock 5706 + küçük, bağımsız bir yama. Circuit Remix veya Arrhythmia'nın bütün özelliklerini almak yerine ihtiyaç duyulan yöntem ve araçları kullanmak. Modun kapalı olduğu durumda stock davranışa geri geçiş tasarlanmalı. Yeni sequencer davranışları henüz kararlaştırılmış değildir.

## Kanıt seviyeleri

- **D — Dosyada doğrulandı:** Kullanıcının gönderdiği dosyada hash, CRC, bayt, pointer veya disassembly kontrolü.
- **E — Kısmi emülasyonda doğrulandı:** Gerçek stock makine kodu, belirtilen sentetik RAM koşullarında çalıştırıldı. Donanım ve gerçek zamanlama testi değildir.
- **K — Kaynakta belgelenmiş:** Topluluk kaynaklarından alınmış, bu çalışmada cihaz üzerinde yeniden doğrulanmamış bilgi.
- **Ö — Öneri/çıkarım:** Henüz uygulama ve test gerektiren tasarım.

## 1. Dosya ve taşıma biçimi

| Kontrol | Sonuç |
|---|---|
| Girdi | circuitrhythm-firmware-5706.syx, 508861 bayt |
| SHA-256 | 11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf |
| Çözülmüş görüntü | 370032 bayt / 0x5A570 |
| Görüntü SHA-256 | d5b9ff5dadf2e284f80d69ecb7087486cf0df315a697bed8272af9de0e90df15 |
| CRC-32/MPEG-2 | 9EEE802C, eşleşti |
| Ürün | 0x63, Circuit Rhythm |
| Görüntüde build | 0x1CA konumundaki little-endian uint16 = 5706 |
| Kimlik metni | DR1.1.5143.5706 |
| Mesaj sayısı | 1 INIT + 1 HEADER + 11563 WRITE + 1 FINISH |
| Üç çözümleyici | Aynı görüntüyü üretti |
| İki yeniden paketleyici | Orijinal SysEx ile bayt bayt aynı çıktı |

**D:** UPDATE_FINISH dosyanın sonunda olsa da görüntünün ilk 32 baytını içeriyor. Her veri paketi 37 adet 7-bit bayttan 32 görüntü baytı üretiyor; son 3 bit padding. Paketleri sırayla birleştirmek yanlış sonuç verir.

Taşıma sürüm alanı `00 00 00 07 03 01`. cr_stereo çözücüsünün `version: 1841` çıktısı bu alanı 0x731 olarak sayıya çevirmesidir; uygulama build'i 1841 değildir. Build, görüntü içindeki ayrı alandan 5706 olarak doğrulandı. Bu dosya cihazda hangi sürümün yüklü olduğunu göstermez.

## 2. Müdahale noktaları

Aşağıdaki adresler yalnızca bu hash'e sahip stock 5706 içindir. Thumb fonksiyon pointer'ları tek sayılıdır; tabloda kod başlangıçları çift adresle gösterilir.

| İşlev / aday | Kod veya veri adresi | Kanıt ve sınır |
|---|---|---|
| Note On router | 0x0803B7EC; vtable slot 0x080694B0 | D: slot 0x0803B7ED içeriyor; girişte kaynak gruplarını ayıran dallar görüldü. Tam uçtan uca nota yolu emüle edilmedi. |
| Note Off router | 0x0803B8F0; slot 0x080694B4 | D: pointer eşleşti. Note Off yaşam döngüsü cihazda henüz sınanmadı. |
| MIDI çıkış maskesi dağıtıcısı | 0x0802986A | D+E: port maskesine göre çıkış callback'lerini seçiyor. 0..7 maskelerinin tamamı test edildi; backend'ler sahte başarı döndürüyor. |
| MIDI port send | 0x080401FE; slot 0x08068AB0 | D: pointer ve kuyruğa ileten kod incelendi. Fiziksel USB/DIN çıkışı test edilmedi. |
| Track step player | 0x0804AFBC; slot 0x08068D2C | D: pattern stride 0xA28, adım stride 8, note/velocity/gate/flags okumaları görüldü. |
| Step note byte setter | 0x08054A5C | E: tüm 32 adımda mevcut çift buffer accessor'ıyla test edildi. |
| Step gate byte setter | 0x08054A84 | E: aynı kontrol, ikinci 8-word grubu. |
| Step flags byte setter | 0x08054AB0 | E: aynı kontrol, üçüncü 8-word grubu. Her bitin anlamı bu testle doğrulanmış sayılmaz. |
| Değiştirilebilir parametre accessor'ı | 0x0803FD26 | D+E: aktif buffer'dan diğerine word kopyalama ve dirty maskesi. |
| Sample-view pad press | 0x0805C1AC; slot 0x08068294 | D: pointer ve başlangıç kodu incelendi. Tam 32-pad UI yolu henüz çıkarılmadı. |
| Step oluşturma çağrısı | 0x0805E41A → 0x0805E5A0 | D: BL hedefi eşleşti; seçim/notify davranışları ayrıca izlenmeli. |
| Pad / button / encoder giriş dalları | 0x080295CA / 0x080295D8 / 0x080295FC | D: sırasıyla 0x08040108 / 0x0804012A / 0x0804015E hedefleri eşleşti. |
| Pulse işleme çağrısı | 0x08033384 → 0x080333AA | D: adres doğrulandı; zamanlama semantiği ve frekansı bu çalışmada ölçülmedi. |

Arrhythmia build script'indeki toplam **77** BL, B.W ve vtable kontrolü geçti. Bu, adres uyumluluğunu kanıtlar; her upstream hook'un davranışını veya güvenilirliğini kanıtlamaz.

## 3. Gerçek stock koduyla emülasyon

`verify_stock.py`, Unicorn üzerinde ARM Thumb/M-class kodunu çalıştırır. Tam cihazı boot etmez; sentetik SRAM nesneleri yerleştirir. İşlemci modeli seçimi gerçek MCU parça numarasının doğrulandığı anlamına gelmez.

### Adım yazma: 1536 senaryo

3 alan × 32 adım × 2 aktif buffer seçimi × 2 dirty durumu × 4 değer = 1536.

Değerler 0, 1, 127, 255; düşük seviyeli bayt yazıcının test girdileridir. Örneğin 255'in her alan için geçerli kullanıcı değeri olduğu iddia edilmez.

Her senaryoda note/gate/flags yazıcısı ve **gerçek stock accessor** çalıştırıldı; fonksiyon çağrıları mock edilmedi. Hedef bayt, komşu baytların korunması, iki buffer'ın tamamı, dirty maskesi ve fonksiyon dönüşü kontrol edildi.

**Sonuç:** Bu düşük seviyeli fonksiyonlar 0..31 adımlarını işleyebiliyor. Ancak test üst seviye bildirim/commit, LED, fiziksel pad, kayıt, mutate veya transport işleyişini kapsamıyor. Setter'ı tek başına çağırıp tamamlanmış bir UI düzenlemesi olduğunu varsayamayız.

### MIDI port maskesi: 8 senaryo

Gerçek 0x0802986A dağıtıcısı çalıştırıldı. Üç sahte port nesnesi ve callback yerleştirildi. Her maskede yalnızca seçilen callback'lerin, doğru nesne ve mesaj pointer'ıyla çağrıldığı doğrulandı.

**Sınır:** Callback'ler başarı döndürür. MIDI mesajının gerçek kuyrukta kopyalanması/ömrü, kuyruk taşması, DIN seri iletim süresi, USB sürücüsü ve clock jitter test edilmedi. Maskedeki fiziksel port eşlemesi topluluk kaynağına dayanır; burada fiziksel port yoktur.

## 4. 32 pad = 32 adım görünümü

**D:** Pattern player 0xA28 baytlık pattern bloklarına erişiyor ve adımı `step << 3` ile seçiyor. Dolayısıyla 32 adım için yeni bir büyük pattern yapısı oluşturmak başlangıçta gerekmiyor.

**K, kısmen D:** Topluluk kodundaki step şeması:

| Bayt | Alan |
|---|---|
| 0 | Nota; player'da 0 için 0x30 fallback görüldü |
| 1 | Gate; player bunu rate tablosuyla ölçekliyor |
| 2 | Altı microstep için hit maskesi |
| 3 | Velocity |
| 4 | Probability |
| 5 | Sample flip; 0xFF özel değeri |
| 6 | Tie bit 0 ve diğer bayrak alanı |
| 7 | Bu çalışmada anlamı doğrulanmadı; boş alan sayılmamalı |

**Ö:** Yeni görünüm fiziksel pad 0..31'i ilgili 0..31 adıma yönlendirmeli; seçili track/pattern ve mevcut düzenleme nesneleri kullanılmalı. Pad press, release, pressure, Clear, Duplicate, tutulan adım, sayfa düğmesi ve LED playhead aynı indeks uzayında çalışmalı. Özellikle 15/16 ve 31/0 sınırları test edilmeli.

Gate/Velocity/Pattern Settings ekranlarının mevcut yollarına geri geçiş korunabilir. Tüm ekranları aynı anda yeniden tasarlamak gerekmiyor. Yeni görünümün hangi tuşla açılacağı bu analizde kararlaştırılmadı.

Mevcut düzenleme verisi buffer'lıdır. Pattern dosyasındaki tek baytı doğrudan değiştirmek, sonraki UI düzenlemesinde eski kopyanın geri yazılması gibi sorunlar yaratabilir. Mevcut setter + uygun commit/notify zincirinin bütünü çıkarılmalı.

## 5. MIDI-only ve polifoni

**K:** Arrhythmia `notetap.c`, note router'ı sarmalarken stock router çağrısını koruyor; yorumları bunun recorder, MIDI out, LED ve choke yolunu sürdürdüğünü belirtiyor. Track 8'in sample engine girişini ayrı bir hook ile kesiyor. Bu, MIDI modunda sample tetiklemelerini ayrı bir katmanda engellemek için iyi bir başlangıç örneği. Aynı davranışın tüm track'lere yayılması henüz test edilmedi.

**Ö:** İlk yaklaşım DSP'yi sökmek değil, MIDI modundaki track'in sample note yolunu kontrollü biçimde devre dışı bırakmak. Router'dan önce tüm olayı yutmak MIDI çıkışını ve recorder'ı da kaybettirebilir. Stop, mute, proje yükleme, MIDI kanalı değiştirme ve tekrar eden aynı nota için cleanup ayrıca gerekli.

**D+K:** Stock adım yapısında tek nota baytı var. Bu yüzden mevcut veriye dokunmadan gerçek, bağımsız çok notalı adım kaydını vaat edemeyiz. Kök nota + akor parametresinden MIDI notaları üretmek daha küçük bir genişleme; bağımsız pitch/velocity/gate taşıyan polifoni ayrı veri tasarımı gerektirir.

Arrhythmia'nın dahili dört sesli synth'i MIDI OUT polifonisinin hazır olduğu anlamına gelmez. MIDI-out chord voice lifecycle ve Note Off sahipliği ayrı uygulanmalı. Ayrıca polifoni için yeni kayıtlar eklenirse Duplicate/Clear/Mutate/Save işlemleri o kayıtları da taşımalıdır.

## 6. Bellek ve kalıcılık

**K:** Topluluk donanım ölçümlerinde stock heap üzerinde yalnızca 3272 bayt pay bildirilmiş. Kullanıcının cihazında ölçülmedi; kesin genel sınır olarak sunulmamalı. Sample kullanmamak bu RAM'i kendiliğinden serbest bırakmaz.

**K:** Arrhythmia proje dosyasının sonundaki 880 baytı ek ayarlar için kullanıyor; sonraki 4 bayt korunuyor. Circuit Remix de proje sonundaki alanları ve pattern ayar alanındaki bazı baytları kullanıyor. Aynı bölgeleri kullanan modlar otomatik uyumlu değildir.

Örnek kapasite hesabı (Ö): yalnızca track 8'in 8 pattern × 32 adımına üç ek nota için pitch/velocity/gate = 3 bayt ayırsak 2304 bayt gerekir. Bu, 880 baytlık alandan büyük; geçerlilik, tie ve ek koşullar dahil değil. Bu hesap bir tasarım kararı değil, serbest polifoninin neden ayrı kalıcılık tasarımı gerektirdiğini gösterir.

**D:** Stock görüntü 0x0806A570'te bitiyor. **K:** Projeler uygulama üst sınırı olarak 0x08080000 kullanıyor. İkisinin farkı 88720 bayt (~86.6 KiB); bu yalnızca teorik ek flash kod bütçesidir, bootloader/donanım onayı veya boş çalışma RAM'i değildir. Bu turda bootloader okunmadı.

## 7. İlk patch için önerilen kapsam ve kabul testleri

İlk cihaz patch'inde polifoni, Elektron koşulları veya yeni proje biçimi eklememek; önce mevcut davranışı koruyan küçük değişiklikle entegrasyon sınırlarını doğrulamak önerilir.

1. Mevcut stok MIDI çıktısını Windows üzerinde referans olarak kaydet: nota, gate, mute/stop, pattern değişimi.
2. Pad → aktif görünüm → adım düzenleme → notify → LED zincirini tamamla; yeni görünüm kapalıyken tüm stock girişler eski yola gitmeli.
3. Aynı pattern'i mevcut görünüm ve yeni 32-adım görünümünde düzenle. MIDI olaylarının içerik ve sırası eşdeğer olmalı; 1/16/17/32 özellikle sınanmalı.
4. Gate, velocity, microstep, probability, tie, Clear, Duplicate ve Mutate için eşdeğerlik testleri. Rastgelelikte birebir olay dizisi yerine uygun invariant'lar ve mümkünse kontrollü RNG kullanılmalı.
5. Kaydet, yeniden yükle, kapat/aç, pattern ve pack değiştir. Canlı RAM ve dosya kalıcılığı ayrı sınanmalı.
6. Sonra MIDI-only sample engellemesi, CC eşlemesi ve en son polifoni/koşullar gibi yeni semantik.

MIDI testinde USB ve DIN ayrı ölçülmeli. Bilgisayar timestamp'leri OS/arayüz gecikmesi içerir; bunlar CPU cycle veya fiziksel jitter garantisi değildir. MIDI test aracı tek portu açmalı; yükleyici ve diğer MIDI uygulamaları test sırasında kapalı tutulmalı.

## 8. Açık araştırmalar

- 32-step görünümünün tam dispatch/selection/notify zinciri ve uygun görünüm anahtarı.
- Stock gate → gerçek MIDI Note Off yolu ve sample playback modlarının bu yola etkisi.
- Clock kuyruğu, notalar ve yoğun CC otomasyonunun sıralama/kapasite sınırları.
- Kullanıcı cihazında RAM/bootloader sürümü ve geri dönüş yöntemi.
- Proje örnekleriyle kayıt alanları, kopyalama ve Mutate davranışının bağımsız kontrolü.
- Modların aynı extension alanlarını paylaşması için versiyonlama/uyumluluk politikası.

Bu analizde fiziksel cihaza hiçbir veri gönderilmedi ve değişiklik içeren firmware üretilmedi.

## 9. Tekrar çalıştırma — Windows 11

Python 3.10 veya üzeri gerekir. ZIP'i açıp bu klasörde PowerShell kullan:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe verify_stock.py C:\dosyalar\circuitrhythm-firmware-5706.syx
```

Beklenen sonuç: `round_trip: PASS`, `hook_sites_passed: 77`, `step_setter_cases_passed: 1536`, `midi_dispatch_cases_passed: 8`, `build: 5706`.

Bu komutlar bu turda Linux analiz ortamında çalıştırıldı; Windows üzerinde henüz çalıştırılmadı. Doğrulayıcı MIDI portu açmaz, yükleme yapmaz ve girdi dosyasını değiştirmez. `verification.json` ve `selected-disassembly.txt` üretir. Python `-O` kullanma: doğrulamalar assert ifadeleri içerir.

ZIP orijinal/çözülmüş Novation firmware'i ve kurulu üçüncü taraf paketleri içermez. Tekrar çalıştırmak için kendi orijinal `.syx` dosyan gerekir. `sources/` tam repo değil, analize alınmış dosya snapshot'larıdır; içindeki diğer build araçlarının bağımlılıkları tam değildir. Çalıştırılması hedeflenen giriş noktası `verify_stock.py` dosyasıdır.

## Kaynaklar ve sürümler

- Arrhythmia: https://github.com/llcoolkm/arrhythmia/tree/a1d7a3f2bdfdf8045ddbb2a4b26fef73b29b6ff2 — özellikle `tools/build_lightshow.py`, `patches/src/notetap.c`, `patches/src/trackmodes.c`, `docs/dev/hardware.md`, `docs/dev/design/project-extension-block.md`.
- Circuit Remix: https://github.com/Ghillermo/CIRCUIT-REMIX/tree/928318078742d09617107b75c103a53d83dd08ef — özellikle `tools/rh_fw.py`, `tools/quant.py`, `tools/drumpat.py`, `tools/midithru.py`, `tools/rhstate.py`.
- cr_stereo: https://github.com/jsmith13/cr_stereo/tree/e88a11e772de80804015c34693658e497e4e890b — `tools/extract_firmware.py`.

Kaynak lisansları ilgili `sources/` klasörlerinde korunmuştur. Kaynak dosyaların hash ve commit kayıtları `provenance.json` içindedir. Topluluk belgelerindeki HW/EMU iddiaları bu raporda K olarak sınıflandırılmıştır; bizim cihaz testimiz olarak sunulmaz.
