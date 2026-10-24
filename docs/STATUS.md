# Devralma durumu

24 Ekim 2026. **M0 tamamlandı. M1'in ilk adres haritası ve dar davranış doğrulamaları tamamlandı; tam press/release yaşam döngüsü açık. M2 teknik aday kapsamı hazır, build yok.**
Güncel sınır 32 adım; 64 adım, polifoni ve Elektron davranışları geliştirilmedi.

## Ortam ve bütünlük

- Dosya değişikliklerinden önce PowerShell hash kontrolü ve ardından `python scripts/check_package.py`: **PACKAGE PASS, 55 dosya**. Manifest dijital imza değildir.
- Stock: 508861 bayt; SHA-256 `11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf`. Stock/reference dosyaları değiştirilmedi; provenance'daki 24 upstream dosya yeniden doğrulandı.
- Windows AMD64 build **26200.9711**, DisplayVersion **25H2**; CPU **AMD Ryzen 7 3700X 8-Core Processor**.
  Kullanıcının ortamı Windows 11; registry ProductName `Windows 10 Pro`, Python platform çıktısı `Windows-10-10.0.26200-SP0`. Bu eski adlandırmayı Windows 10 kurulum kanıtı saymıyoruz.
- Python **3.11.9**, MSC v.1938, 64 bit; mevcut Microsoft Store kurulumundan proje `.venv` oluşturuldu.
  `py` launcher yok. Store alias/venv sandbox içinde açılamadı; Python komutları yürütme izniyle çalıştı.
- Capstone paket **5.0.9**, modülün bildirdiği **5.0.7**; runner paket metadata'sını kontrol etti. Unicorn **2.1.4**, pip **24.0**. `-O` kullanılmadı. Yalnızca bağımlılık kurulumu ağ kullandı.
- Git **2.53.0.windows.2**. Başlangıçta depo yoktu; yerel devralma checkpoint'i **77d997f** oluşturuldu. Remote yok.
  Firmware/build/log/venv/backups ignored; dumps/captures/personal-projects kuralları da eklendi.
  `analysis/**` ve `reference-results/**` checkout satır sonu dönüşümünden korundu.

## Komutlar ve sonuçlar

Proje kökünde PowerShell, venv activation gerekmeden:

```powershell
python scripts/check_package.py
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/run_baseline.py
.\.venv\Scripts\python.exe tests/test_ui_contracts.py
.\.venv\Scripts\python.exe scripts/run_ui_audit.py
git check-ignore -v stock/circuitrhythm-firmware-5706.syx backups/example.dat dumps/example.raw
git ls-files '*.syx' '*.bin' '*.elf' '*.hex' 'backups/*' 'logs/*' 'build/*'
git remote -v
```

Git indeks/commit yazımı da sandbox izni gerektirdi. Başlangıç `git diff --cached --check` upstream dosyaların mevcut sondaki boş satırlarını raporladı; tarihsel kaynaklar değiştirilmedi.
Yeni diff ayrı kontrol edilir. Sonraki paket kontrolünde bilinçli belge/ignore değişikliklerinin manifest farkı vermesi beklenir; manifest yenilenmedi.

**BASELINE PASS:** `logs/baseline-20261024T173416590494Z/`.
Üç taze sonuç dosyası reference-results ile satır sonları normalize edildiğinde birebir eşleşti.
Ham dosya hash farkının nedeni Windows CRLF/LF farkıdır; referans dosyaları değiştirilmedi.

| Sonuç | Gerçekte kanıtladığı |
|---|---|
| 3 decoder aynı 370032 baytı, 2 encoder orijinali birebir üretti | Dosya/taşıma; image SHA-256 `d5b9ff5dadf2e284f80d69ecb7087486cf0df315a697bed8272af9de0e90df15`, CRC `9EEE802C` |
| 77 hook/çağrı/pointer kontrolü | Stock bayt/adres uyumluluğu |
| 1536 setter senaryosu | Stock setter/accessor, sentetik RAM; baseline tek başına commit/LED sınamaz |
| 8 MIDI-mask senaryosu | Gerçek dispatcher, sahte port callback'leri; MIDI gönderilmedi |
| 96 yanlış-indeks çakışması | >31 indeksin veri alanlarını çakıştırdığı olumsuz deney; kapasite desteği değil |
| 384 edit, 128 player argümanı | Önceki sayfalı host fixture; 64/128 adım firmware uygulaması değil |
| 3456 microstep/probability senaryosu | Sentetik ön geçiş; RNG/clock/gate-tie yaşam döngüsü değil |

**UI AUDIT PASS:** `logs/ui-audit-20261024T182014064195Z/`.
Beş davranış testi geçti: pad dispatch; track/subview/index seçimi; setter-notify-commit; normal toggle-commit-LED observer; vtable ve basılı-adım renk dalı.
Ayrıntılı kapsam, mock sınırları ve adres haritası: [UI-TRACE-5706.md](UI-TRACE-5706.md).

## Yeni kesin bulgular

- Step view vtable `0x080682CC`, press `0x0805CB04`, release `0x0805CCF0`.
  İki handler da view+0x60 sayfa durumuna göre +16 ekliyor; container mapping'ini tek başına değiştirmek yetmez.
- Normal toggle `0x0805D610`, eski rapordaki held-sample `0x0805E5A0` yolundan farklı.
- Notify `0x0803FBEC` dirty word'lerin aktif-buffer bitlerini çevirir; listener `0x08048208` seçili pattern'e 32 kaydı yazar. Sonraki edit'in önceki edit'i koruduğu gerçek çağrılarla doğrulandı.
- Step view 32 mantıksal LED kaydı tutar; getter `0x0805D3BC` yalnızca 16'lık pencere sunar. Grid compositor `0x0804DD1C` üst/alt yarıyı farklı subview kaynaklarından birleştirir.
- `0x0805CF68` basılı-adım renk komutunun `1f22` baytları ve hedef LED yazma davranışı doğrulandı. `1e22` adayının kapsamı [FIRST-PATCH-SCOPE.md](FIRST-PATCH-SCOPE.md) içinde; uygulanmadı.

## Değişen dosyalar

`.gitattributes`, `.gitignore`, `CHANGELOG.md`, `docs/STATUS.md`, `tests/README.md`, `README.md`, `docs/SCOPE.md`;
yeni `docs/UI-TRACE-5706.md`, `docs/FIRST-PATCH-SCOPE.md`, `scripts/inspect_ui.py`, `scripts/run_ui_audit.py`, `tests/test_ui_contracts.py`.
Yeni test/analiz çıktıları ignored `logs/` altında; `.venv` ignored.
Stock, baseline runner, eski analizler ve reference-results korunmuştur.

## Başarısız denemeler ve açık sınırlar

- `py -0p`: launcher yok. Python/venv sandbox erişimi ve Git index yazımı izinle çözüldü.
  CIM ortam sorguları erişim hatası verdi; OS/CPU bilgisi registry/Python'dan alındı. MIDI/USB envanteri sorgulanmadı.
- Container mode 2/3 için ilk fixture ofseti yanlıştı; test başarısız oldu. TBB disassembly ile +0x9C/+0xBC olarak düzeltildi; test tekrar geçti.
- Başka bir 32-entry görünümü step view sanma hipotezi constructor zinciriyle elendi; PC-relative literal'deki ilk dört baytlık hizalama yanılgısı düzeltildi.
- Tam cihaz emülatörü yok. Gerçek nesne başlangıcı, RTOS/listener eşzamanlılığı, held-pad sahipliği, timer, pressure, Clear/Duplicate, gate/tie, Mutate, SD ve MIDI timing ölçülmedi.
- Cihazdaki firmware/bootloader ve yedek durumu bilinmiyor. Recovery fiziksel olarak denenmedi.
  Bu oturumda ARM toolchain kurulmadı veya upload paketi üretilmedi; build/transport kimliği ve stock'a dönüş kabulü açık.

Hiçbir MIDI/USB cihazı açılmadı, komut gönderilmedi veya firmware yüklenmedi. Custom firmware derlenmedi.
Mod kısayolu, ayrı Projects, Packs engellemesi ve MIDI-only uygulaması henüz yok.

## Sonraki tek somut görev

M1 devamı: `0x0805CB04` press → `0x0805CCF0` release zincirini timer sınırlarını açıkça ayırarak sentetik fixture'da birleştir; 1/16/17/32 ve basılıyken sayfa/track değişiminde step sahipliğini doğrula.
Ardından M2 adayını kontrollü patch aracı ve bağımsız diff testleriyle üretmek değerlendirilebilir.
Cihaz testi ancak kesin dosya/hash, test ve recovery paketi hazırlandıktan sonra ayrı kullanıcı onayıyla yapılır.
