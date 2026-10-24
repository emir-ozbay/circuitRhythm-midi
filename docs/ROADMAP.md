# Geliştirme sırası

Her milestone ayrı küçük commit ve test kaydı üretir. Görev gerektirmedikçe kapsam genişletme.

| Aşama | İş | Çıkış ölçütü |
|---|---|---|
| M0 | Ortam, hash, baseline, yerel Git | Beklenen sonuçlar tekrar üretildi; hardware erişimi yok |
| M1 | Pad/view/edit/notify/LED ve MIDI yollarını incele | Kod ve bayt kanıtlı adres haritası; dokümante açık sınırlar |
| M2 | Çok küçük ilk firmware denemesi hazırla | Örneğin tek LED göstergesi; kesin değişiklik inceleme sonrasında seçilir. Pinned toolchain, patch range/hash raporu ve geri dönüş hazırlığı |
| M3 | 32-adım LED görünümü | Aynı pattern'in iki yarısı, doğru playhead; diğer görünümler korunur |
| M4 | 32 pad'den düzenleme | 1/16/17/32 sınırları, press/release, tutulan adım, Clear/Duplicate/commit doğru |
| M5 | Basılı tut + pad ile uzunluk | 1..32, kısalt/uzat, stock start/end ilişkisi ve kısa basış doğru |
| M6 | Mevcut işlevlerin regresyonu | Gate, velocity, microstep, probability, tie, Mutate, pattern zinciri, Note, Pattern Settings, kayıt/tekrar açma |
| M7 | Sequencer Only moduna giriş/çıkış ve MIDI-only | Shortcut çakışmasız; normal moda dönüş; note cleanup; sample engellemesi MIDI/recorder'ı kesmez |
| M8 | Ayrı Projects, bu modda Packs'i kapat | İki alan arasında yanlış yazma yok; normal projeler korunur; save/load ve power cycle |
| Sonra | 64-adım mimari araştırması | RAM ve kalıcılık çözümü kanıtlanmadan sınır artırılmaz |

M2 öncesinde yedekler, mevcut sürümler ve stock recovery yolu doğrulanır; cihaz yüklemesi ayrı onaylı adımdır. Uygulama kaynakları doğru hazırlanmadan bir LED denemesi bile 'güvenli' diye sunulmaz. Gerekirse M3/M4 yalnızca host fixture ile başlar.

İleride 64 için yerel pad numarasını logical adımla karıştırma. Ekran sayfası playback konumunu değiştirmemeli. Çok sayıda testin tek dar fonksiyonu kapsadığını belirt; bu sayıları uçtan uca garantiye dönüştürme.
