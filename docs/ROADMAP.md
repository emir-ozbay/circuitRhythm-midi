# Geliştirme Sırası ve Kilometre Taşları

Geliştirmenin %95'i bilgisayar üzerindeki Unicorn ARM Cortex-M emülatöründe doğrulanır. Fiziksel cihaza her adımda yükleme yapılmaz; yalnızca emülatörde tamamlanmış ve tüm testlerden geçmiş toplu paketler cihazda sınanır.

| Aşama | İş | Durum / Çıkış Ölçütü |
|---|---|---|
| **M0** | Ortam, hash, baseline, yerel Git | **TAMAMLANDI** — Beklenen sonuçlar tekrar üretildi; donanım erişimi yok |
| **M1** | Pad/view/edit/notify/LED ve Projects yollarını incele | **TAMAMLANDI** — Kod ve bayt kanıtlı adres haritası (`docs/UI-TRACE-5706.md`) |
| **M2** | Güvenli Patcher aracı ve tek baytlık kanıt yaması | **TAMAMLANDI** — `scripts/patch_firmware.py` ve 32 testlik Unicorn doğrulaması |
| **M3** | Genişletilmiş Patcher (`Code Cave` `0x0806A570+`) ve Güvenli Heap Durum Bloğu (`0x2004F660`) | **TAMAMLANDI** — Patcher'ın `0x0806A570..0x08080000` arasına Thumb-2 kod eklemesi ve `c_seq_state` RAM bloğu (`46 test PASS`) |
| **M4** | Mod Geçişi + 32-Pad Step Yönlendirmesi + Sayfa Kilidi + Sahiplik Temizliği | `grid_mode == 0`'da 32 pad -> Step View (`step == pad`), `grid_mode != 0`'da `1–16` tuşu aktif; makine kodu Unicorn'da doğrulandı |
| **M5** | 32-Adım LED Compositor Makine Kodu Yaması | `0x0804DD1C` kancasıyla `grid_mode == 0`'da 32 adım LED + Playhead birleştirme; diğer modlarda alt pad korunumu |
| **M6** | Bağımsız 32 Sequencer Projesi (`[proj_view + 0x36]`) + Packs Kilidi + Sample Susturma (MIDI-Only) | Normal modda Proje 1–32 (`sayfa 0`), Sequencer modunda Proje 33–64 (`sayfa 1`), Packs kapalı, dahili sample tetikleme susturulmuş |
| **M7** | **1. Gerçek Cihaz Testi Hazırlığı ve Doğrulaması (Faz 1 Paketi)** | M3–M6 birleşik `.syx` üretimi, tam Unicorn regresyon testi, SHA-256/CRC-32 manifesti ve kullanıcı onayıyla ilk fiziksel cihaz testi |
| **M8** | Faz 2: Root Nota + Knob ile Akor/Triad Üretici ve Hızlı Uzunluk Kısayolu | Akor tablosu, Note On/Off ses takibi ve 2. gerçek cihaz testi |

## Temel Kurallar
- **64 adım kapsam dışıdır:** Tüm geliştirmeler stok 32 adım (`0..31`) sınırları içinde kalır.
- **Emülatör Öncelikli Doğrulama:** Hiçbir yama cihaza yüklenmeden önce Unicorn üzerinde gerçek makine koduyla test edilmezse "hazır" kabul edilmez.
- **Kurtarma Hazırlığı:** M7'deki ilk fiziksel cihaz yüklemesinden önce `docs/RECOVERY.md` adımları ve proje yedekleri kontrol edilir.
