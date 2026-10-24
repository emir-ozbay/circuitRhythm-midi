# M2 İlk Mikro Yama Adayı: Cihaz Testi Teklifi ve Kurtarma Kontrol Listesi

25 Ekim 2026. **DİKKAT: Bu aşamada fiziksel cihaza yükleme YAPILMAMIŞTIR ve cihaza hiçbir komut iletilmemiştir. Cihaz testi yalnızca kullanıcının açık onayı ile yürütülür.**

Bu belge, [docs/FIRST-PATCH-SCOPE.md](FIRST-PATCH-SCOPE.md) belgesinde tanımlanan ve sentetik olarak tüm sınırlarıyla kanıtlanan M2 tanı mikro yamasının olası bir fiziksel cihaz testi için gerekli diff, hash, önkoşul ve kurtarma kontrol listesini sunar.

---

## 1. Kesin Üretilen Test Dosyası ve Bütünlük Bilgileri

| Parametre | Orijinal Stok (5706) | Üretilen M2 Adayı |
|---|---|---|
| **Dosya Yolu** | `stock/circuitrhythm-firmware-5706.syx` | `build/circuitrhythm-5706-m2-candidate.syx` |
| **SysEx Boyutu** | 508.861 bayt | 508.861 bayt |
| **SysEx SHA-256** | `11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf` | `8c6996e22eec4848e31696f512ff4a9c0f151a76e37eb05837553c25743cc356` |
| **İmaj Boyutu** | 370.032 bayt | 370.032 bayt |
| **İmaj SHA-256** | `d5b9ff5dadf2e284f80d69ecb7087486cf0df315a697bed8272af9de0e90df15` | `55d42a5b0ed12312e402eb0c14f4a538eda1ef3f77add726baa95cd700ed7b86` |
| **MPEG-2 CRC-32** | `0x9EEE802C` | `0x2DBD7611` |
| **Manifest Dosyası** | — | `build/circuitrhythm-5706-m2-candidate.manifest.json` |

---

## 2. Kesin İkili Değişiklik (Binary Diff) ve Güvenlik Sınırları

Yama, firmware imajında **tam olarak 1 baytlık** bir değişiklik gerçekleştirir:

- **Hedef Adres:** `0x0805CF68` (İmaj içi ofset: `0x4CF68`)
- **Orijinal Komut (Stok):** `1f 22` (`movs r2, #31`) — Palet indeksi 31 (`0x0055`)
- **Yamanmış Komut (Aday):** `1e 22` (`movs r2, #30`) — Palet indeksi 30 (`0x001E`)
- **Değişen Bayt Sayısı:** 1 bayt (`0x1F` -> `0x1E`)
- **Kalan İmaj Baytları:** 370.031 bayt stok 5706 ile **%100 bayt bayt aynıdır**.
- **Vektör Tablosu Koruması:** `[0x08010000, 0x08010200)` aralığındaki ARM Cortex-M vektör tablosu ve kimlik metni (`DR1.1.5143.5706`) kesinlikle değiştirilmemiştir.
- **Bootloader Koruması:** `0x08010000` altındaki bootloader alanına ve donanım koruma bayraklarına dokunulmamıştır.

---

## 3. Sentetik Emülasyon ve Doğrulama Kanıtları

`tests/test_patcher.py` ve `scripts/verify_m2_candidate.py` araçları ile Unicorn emülatöründe 32 adımın tamamı (adım 0..31) sentetik RAM ortamında çalıştırılmış ve şu hususlar matematiksel kesinlikle kanıtlanmıştır:

1. **LED Renk Değişimi:** Adım basılı tutulduğunda (`0x0805CB04`), yalnızca basılan adımın 16-bit LED kaydı stok palet 31'den (`0x0055`) palet 30'a (`0x001E`) geçer.
2. **Kalan LED'lerin İzolasyonu:** Geriye kalan 31 adımın LED kayıtları basıştan kesinlikle etkilenmez ve stok ile bayt bayt aynı kalır.
3. **Pattern Belleği Bütünlüğü:** 8 pattern'in tamamını içeren 20.800 baytlık pattern belleği (`0x20010000`) basış sırasında tek bir bayt dahi değişmez.
4. **Edit Buffer Bütünlüğü:** `st1`, `st2`, `selection`, `note` ve aktif durum değişkenleri stok ile birebir aynı kalır.
5. **Release ve Commit:** Adım bırakıldığında (`0x0805CCF0`), nota bilgisi pattern belleğine stok kodla tamamen aynı şekilde commit edilir ve LED aktif adım rengine döner.

---

## 4. Donanım Testi Önkoşul ve Güvenlik Kontrol Listesi

Fiziksel cihaza yükleme teklif edilmeden veya yapılmadan önce aşağıdaki kontrol listesi eksiksiz tamamlanmalıdır:

- [ ] **Mevcut Firmware Teyidi:** Cihaz Novation Components'a bağlanarak kurulu sürümün stok 5706 olduğu doğrulanmalı.
- [ ] **Proje ve Pack Yedeklemesi:** Cihazdaki tüm kullanıcı projeleri ve sample pack'leri Novation Components üzerinden yedeklenmeli.
- [ ] **SD Kart Tam Klonu:** MicroSD kart cihazdan çıkarılarak bir kart okuyucu yardımıyla bilgisayara tam olarak kopyalanmalı.
- [ ] **İkinci Bağımsız Yedek:** Bu yedeklerin ikinci bir kopyası çalışma klasörünün (`circuitRhythm-midi`) dışında güvenli bir dizinde saklanmalı.
- [ ] **Güç ve Bağlantı Güvenliği:** Cihazın şarjının tam olduğu veya kesintisiz USB-C gücü sağlandığı doğrulanmalı.
- [ ] **Çakışan Yazılımların Kapatılması:** Aktarım sırasında port çakışması olmaması için DAW, MIDI monitör veya WebMIDI kullanan diğer sekmeler kapatılmalı.
- [ ] **Temiz Test Alanı:** Cihazda aktif proje olarak boş ve önemsiz bir test projesi seçilmeli.
- [ ] **Stok Dosya Hazırlığı:** İhtiyaç anında derhal geri yüklemek üzere `stock/circuitrhythm-firmware-5706.syx` dosyasının hazır olduğu ve SHA-256 hash'inin doğrulandığı teyit edilmeli.

---

## 5. Donanım Test Protokolü (Fiziksel Gözlem)

Kullanıcı onayı ile yükleme yapıldığında uygulanacak test adımları:

1. **Yükleme:** Üretilen `build/circuitrhythm-5706-m2-candidate.syx` dosyası cihaza aktarılır.
2. **Yeniden Başlatma:** Cihazın normal şekilde yeniden açıldığı gözlemlenir.
3. **Step Görünümü:** Boş bir projede Track 1 seçilir ve Step görünümüne geçilir.
4. **Basılı Tutma Testi:** 1, 16, 17 ve 32. adımlara basılı tutulur.
   - *Beklenen Davranış:* Basılı tutulan pad'in LED'i stok beyaz (palet 31) yerine palet 30 renginde yanmalıdır.
5. **Bırakma (Release) Testi:** Pad bırakıldığında adımın normale döndüğü (adım aktifleştiyse track rengine geçtiği) görülmelidir.
6. **Genel Fonksiyonlar:** Çalma/Durdurma (Play/Stop), sayfa değişimi (1–16 / 17–32) ve track geçişleri test edilir.
7. **Anormallik Durumu:** Beklenmeyen bir takılma, donma veya ses çıkışı durumunda test derhal durdurulur ve kurtarma prosedürüne geçilir.

---

## 6. Kurtarma ve Stok Firmware'e Dönüş Prosedürü

Olası bir uyumsuzluk durumunda [docs/RECOVERY.md](RECOVERY.md) yönergeleri uygulanır:

### Senaryo A: Yalnızca Proje Açılış Sorunu
- Cihaz kapalıyken **Shift + Clear** basılı tutularak açılır (cihazı boş proje yükleyerek başlatır).

### Senaryo B: Firmware Açılmıyorsa veya Stok Versiyona Dönüş
1. Cihazı kapatın.
2. **Sample Rec + Sample + Note** düğmelerini basılı tutarken cihazı açın (Bootloader moduna giriş).
3. Novation Components'ı açın ve **Updates -> Reinstall firmware** seçeneğini kullanarak resmî firmware'i yeniden yükleyin; veya `stock/circuitrhythm-firmware-5706.syx` dosyasını gönderin.
4. Cihazın normal şekilde başladığını ve verilerin korunduğunu teyit edin.
