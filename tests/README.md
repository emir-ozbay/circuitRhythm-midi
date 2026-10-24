# Yerel testler

Proje kökünde, `-O` kullanmadan:

```powershell
.\.venv\Scripts\python.exe scripts/run_baseline.py
.\.venv\Scripts\python.exe scripts/run_ui_audit.py
```

Baseline tarihsel sonuçları tekrar üretir. UI audit, `test_ui_contracts.py` testlerini ve stock disassembly pencerelerini yeni bir `logs/ui-audit-*` klasörüne kaydeder.
Tek test: `.\.venv\Scripts\python.exe tests/test_ui_contracts.py Contracts.test_toggle_commit_and_led_observer`.

Testler stock makine kodunu sentetik RAM'de çalıştırır; dispatcher testindeki son callback'ler sahtedir.
Cihaz boot edilmez; fiziksel MIDI/USB/pad/LED erişimi yoktur. Uçtan uca cihaz doğrulaması veya firmware build'i değildir.
Kapsam: [UI-TRACE-5706.md](../docs/UI-TRACE-5706.md).
