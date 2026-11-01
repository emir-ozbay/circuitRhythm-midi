> Güncel1 Kasım /Load short-read — Stock köprünün hata4'ü başarı apply'ına
> çevirmesi native reset/file worker ile yeniden üretildi. Yeni guard yanlış
> başarıyı atlar,native Close ve kalıcı taint ile mod geçişini kapatır. Raw alias
> rollback/toparlanma çözülmedi. Yeni aday272a8128… /CRC985753F7;M7 NO-GO.
> Güncel sayım ve tek sonraki görev STATUS.md'de;ayrıntı
> [MIDI-RECOVERY-LOAD-SHORT-READ-5706.md](MIDI-RECOVERY-LOAD-SHORT-READ-5706.md).
> Alt bölümler tarihsel sonuçlardır.

---

> Güncel: ortak proje ve onaylı test migrasyonu tamamlandı.
> 101 regresyon ve35 packaged test PASS; bekleyen test onayı yok.
> Mod değişiminde dosya erişimi yok. Stok storage hatası onarılmış sayılmaz.
> Kalan3 GO engeli ve güncel hash için STATUS.md ilk bölümü geçerlidir. NO-GO.

---

> Ortak proje kapsamında banka ayrımı ve otomatik Load kaldırıldı.
> Mod değişimi dosya erişimi yapmaz. Eski Load engeli adaydan çıkarıldı.
> Stok storage hata riski onarılmadı. Tam test migrasyonu onay bekliyor.
> Güncel aday ve NO-GO kararı için STATUS.md ilk bölümü önceliklidir.

---

> Güncel: 26 Ekim 2026, Load/New continuation okuma öncesinde kapatıldı.
> Tüm raw proje baytları korunuyor; işlevsel Load ve boot kabul edilmedi.
> NO-GO;131 regresyon. STATUS.md ilk bölümü önceliklidir.
> Aşağıdaki bozulma deneyi koruma kaldırıldığında hâlâ geçerlidir.

---

# Project Load: canlı pattern alias riski

**SON KARAR: TEHLİKELİ / YÜKLENEMEZ — NO-GO.** 26 Ekim 2026.

Ham project read hedefi canlı pattern verisini içeriyor. Hata callback'inin
başarı uygulamasını durdurması, read sırasında değişen baytları geri getirmiyor.

## Bağımsız kanıt

| Bağlantı | Stok kod kanıtı |
|---|---|
| Project Controller raw pointer | Main0x080283F2 aynı raw r6'yı r1'e verir;0x08036FDC bunu P+14'e yazar. |
| Track span | Main0x080281C2 aynı raw r6'yı0x08033120'ye verir: raw+2E4, stride5140, count8. |
| Recorder pattern pointer |0x08036950 factory ->0x08048AE0 kurucusu ->0x08048B58: recorder+50 bu span'in ilgili track tabanıdır. |

scripts/project_alias_test_support.py gerçek span ve sekiz recorder kurucusunu
çalıştırır. Project Controller'ın pointer bağlama prefix'i yürütülür. Main/full
boot ve fiziksel RAM dump çalıştırıldığı iddia edilmez. Store argümanları
sentetiktir. Kuyruk nesneleri raw alanıyla çakışmayacak şekilde taşınmıştır.

scripts/probe_project_alias.py aynı raw alanını gerçek Load request'inin read
hedefi yapar. File API stub'ı741 bayt yazar ve short-read4 döndürür; ardından
Close ve error cleanup gerçek kuyruk/callback koduyla yürür. Stok read API'nin
kısa okumada4 dönüşü disassembly'de vardır.

Gözlenen sonuç: canlı pattern nota60 ->34, apply_calls=0, transition_error
sonrasında idle. Bu sentetik hata enjeksiyonudur; fiziksel SD olayı değildir.
Fakat pointer alias'ı ve bozulma sonucu gerçek makine koduyla oluşur.
Kanıtlar: logs/project-alias-probe.json, logs/project-alias-constructors.txt,
logs/alias-audit/ ve verifier report'undaki critical blocker.

## Eklenen koruma ve sınırı

Owned Load error state+64 project_tainted, dirty ve save-edited set eder.
Save dispatch ve doğrudan0x08037ED0 Save/Duplicate girişleri tainted projeyi
reddeder. State doğrulanamazsa doğrudan Save de reddedilir. Başarıyla tamamlanan
apply sınırı karantinayı temizleyebilir. Testte hata sonrası Save reddediliyor.

Bu koruma bozulan RAM'i geri almaz. Playback/tick reader'ları, diğer I/O yolları,
New/Clear ve global callback ömrü için tam güvenlik kanıtı değildir.
Verifier bunu CRITICAL_RUNTIME_PROBE_FAILED / NO-GO olarak raporlar.
128 unit/regresyon ve59 packaged regresyonun geçmesi kritik probe sonucunu örtmez.

## Staging/rollback için kapanış ölçütü

Proje169092 bayt; iki tam tampon338184 bayttır. Mevcut320KiB ana SRAM modelinin
327680 bayt sınırını, diğer nesneler hesaba katılmadan aşar. Harici RAM veya audio
alanı serbest kabul edilemez; sahiplik, sınır ve ömür stok kodla kanıtlanmalıdır.
Custom SD filesystem katmanı proje kapsamı dışındadır.

Güvenli çözüm read hedefini canlı veriden ayırmalı veya kayıpsız rollback'i her
hata konumunda kanıtlamalıdır. Commit sırasında reader/writer ve scheduler/IRQ
sahipliği doğrulanmalı; bir bölüm yeni/bir bölüm eski proje görülmemelidir.
Kısa okuma, read error, Close error ve araya giren edit/Stop olayları için önceki
canlı baytlar korunmalı ya da doğrulanmış geri dönüş tamamlanmalıdır.

Bu mimari kanıt sağlanmadan firmware yüklenmemeli. Güncel aday hash'i ve tüm
komut sonuçları docs/STATUS.md ilk bölümündedir.
