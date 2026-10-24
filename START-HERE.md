# Circuit Rhythm MIDI — buradan başla

Bu paket yerel Codex'e devretmek için hazırlanmıştır. **Çalışan custom firmware değildir.** Kullanıcının sağladığı orijinal 5706 firmware'i, analizler, sınırlı emülasyon testleri ve geliştirme talimatları içerir. Testler Linux'ta çalıştırıldı; Windows'ta ilk çalıştırma senin bilgisayarında yapılacak.

## İlk 10 dakika

1. ZIP'i kısa bir yerel yola çıkar: örneğin `C:\Projects\CircuitRhythmMidi`. `AGENTS.md` dosyasının bulunduğu klasörü VS Code/Codex'te proje olarak aç. ZIP'in içinden çalışma.
2. Python 3.11+ (64-bit, `py` launcher ile), Git ve tercih ettiğin Codex yerel istemcisini kur. VS Code kullanıyorsan OpenAI'nin Codex eklentisini kurup giriş yap. Bu paket ayrıca API anahtarı gerektirmez; Codex erişimi kendi hesabına bağlıdır.
3. `CODEX-FIRST-MESSAGE.txt` içeriğini Codex'e gönder. İlk görev yalnızca paketi ve testleri doğrulamaktır. CR'yi bağlaman gerekmiyor.
4. Sonuçları birlikte inceleyin: başlangıç testleri geçmeden firmware değişikliğine geçmeyin. `docs/STATUS.md` güncellensin.
5. Sonra `docs/ROADMAP.md` içindeki M1'e geç: pad/LED/step edit zincirini kanıtla. Daha sonra küçük, incelenmiş bir cihaz denemesi hazırlanacak.

## Kendin çalıştırmak istersen

Bu klasörde PowerShell aç:

```powershell
py -3 scripts\check_package.py
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\run_baseline.py
```

Alternatif: `scripts\setup.ps1` ve `scripts\test.ps1` aynı akışı sunar. PowerShell script policy engellerse sistem policy'sini değiştirmek yerine yukarıdaki komutları kullan. Venv activation gerekmez. Paket yükleme internet gerektirir; baseline testleri internet veya MIDI cihazı kullanmaz.

Başarı çıktısı `BASELINE PASS` olmalı. Log ve JSON sonuçları `logs/baseline-...` altında oluşur. Bu, firmware'in cihaza yüklenebilir olduğunu göstermez.

## Klasörler

| Yol | Amaç |
|---|---|
| AGENTS.md | Codex'in uyması gereken proje kuralları |
| docs/SCOPE.md | Güncel kullanıcı hedefi; eski raporlardan öncelikli |
| docs/STATUS.md | Gerçekte tamamlananlar ve bilinmeyenler |
| docs/ROADMAP.md | Küçük adımlarla geliştirme sırası |
| docs/RECOVERY.md | Yedek, bootloader ve kurtarma ayrımı |
| docs/HARDWARE-TEST.md | Her cihaz denemesinin kayıt şablonu |
| stock/ | Orijinal, değiştirilmemiş kullanıcı firmware'i |
| analysis/ | Önceki raporlar, testler, lisanslı kısmi kaynak snapshot'ları |
| reference-results/ | Önceki Linux analizinin sonuçları |
| src/, tests/ | Yeni mod kodu ve testlerinin geleceği yerler |
| build/ | Geçici çıktılar; paylaşma/yükleme otomatik değildir |
| logs/ | Yerel test çalıştırmalarının sonuçları |
| backups/ | İsteğe bağlı yerel yedek alanı; ayrıca dışarıda ikinci kopya tut |

ARM derleyicisi, çalışan firmware builder ve uploader henüz pakette yoktur. İlk aşama için gerekmez; doğru yaklaşım belirlendikten sonra sürümü sabitlenmiş toolchain kurulmalıdır. `analysis/sources/` tam ve bağımsız derlenebilir repo değildir. Kaynak commit'leri ve hash'ler `analysis/provenance.json` içindedir.

Paket orijinal Novation firmware'ini içerdiğinden tamamını halka açık depoya yükleme. `.gitignore` firmware, build, log ve yedekleri dışarıda tutar. Yerel Git başlangıcı: `git init`, sonra `git status --short --ignored` ile hariç tutulanları incele; henüz remote eklemek gerekmez.

## Paket doğrulaması

`scripts/check_package.py`, dağıtılan dosyaların hash'lerini `PACKAGE-MANIFEST.json` ile karşılaştırır. Bu ilk açılış kontrolüdür; bilinçli kod/doküman değişikliklerinden sonra fark bulması normaldir. Baseline runner ise her çalışmada orijinal firmware'i beklenen hash'e karşı doğrular. Manifest kendi kendini doğrulayan dijital imza değildir.

Bu paketin hazırlanma tarihi: 24 Ekim 2026.
