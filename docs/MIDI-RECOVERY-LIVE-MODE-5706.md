> Tarihsel621a4e49… readiness düzeltmesi ve76 girişlik ilk akış aşağıdadır.
> Güncel aday afbab4f2… B8 latch reddini de düzeltir;release sonrası track
> değiştirmeden mode geçişi32 pad'de geçer. Aşağıdaki pending-red davranışı
> eski adaya aittir. Güncel sonuç:STATUS.md veMIDI-RECOVERY-MODE-LATCH-5706.md.

---

# Tam açılıştan sonra native mod geçişi — 5706

30 Ekim 2026. Yerel emülasyon;fiziksel port/cihaz erişimi yok. M7 NO-GO.
Bu tur gerçek bir admission kusuru giderildi;firmware'de tek bayt değişti.

## Bulgu ve düzeltme

Native açılışın oluşturduğu controller `200487C8`,Projects view `2004DA10`,
Project Controller `20042FF4`,raw proje `20012C48`'dir. Sekiz native recorder'ın
`+50` pattern pointer'ı aynı raw'un `2E4+track*5140` aralığına bağlanır.
Başlangıç nesnesi,store veya ready sonucu host'ta oluşturulmadı.

Projects view+24 store değeri `0E` iken gerçek proje phase.word1=0 ve
Project Controller+4C flags.word0=0'dır. İlk yorumda `0E`'nin bit1'i proje
I/O meşgul sanıldı;16 native Main turunda değişmeyince bağlantılar izlendi.
Bu store Project Controller+4C ile aynı değildir. Projects view+28 ise
Project Controller+48 phase store'una gerçekten bağlıdır.

Stok `4F0A4..4F0B0` ve `4ED80..4ED8A` readiness için yalnız bit3'e bakar.
Eski ek guard `(ready & 0B)==08` beklediği için native idle `0E`'yi sürekli
reddediyordu. Yeni guard `(ready & 08)==08` kullanır. Sonraki phase.word1==0
kontrolü aynıdır;transport,MIDI/nota,pad/step ownership ve context kontrolleri
korunur. Queued/running phase1/2 hâlâ reddedilir. Dirty/raw veri okunup
değiştirilmez;mod geçişi Load/New/Save/Duplicate/Clear başlatmaz.

`src/seq_Patch.py` değişikliği üretilen image'da yalnız `0806A882` adresindeki
`MOVS R2,#0B → #08` immediate baytıdır. Code size,label,stack/RAM rezervasyonu,
core/glue/accepted guard ve CTRL_SYNC helper değişmedi. Builder orijinal stock
baytlarını ve hash'i doğrular;SysEx/MPEG2 CRC'leri yeniden üretir. Stock ve
ilk512B vector/identity korunur. Ayrıntılı before/after manifest ve diff logdadır.

Yeni recovery SYX SHA256:
`621a4e49e097bda696ce2cb6f054d110d3cffd2ce26e2df15003960f3fd02745`.
Image SHA256:
`1f3930424b91c7d88fce539fb1c7d0c4ed2f9a3f3655814bd834735b18253164`.
MPEG2 CRC `434FF0EF`;42 patch/7546 değişen bayt,458296B image/630213B SYX.
Önceki recovery07c2305d… before pakette saklanır. Eski legacy sequencer SYX
tarihsel dosyadır;güncel kaynakla doğrulanmış paket recovery adayıdır.

## Native giriş ve sonuçlar

Yeni `LiveModeSession`,heap'teki native vtable'ları bulup obje/alias bağlarını
doğrular. Giriş constructed controller'ın vtable slotundan yapılır:Shift27,
Sample Rec18,pad31 ve track1. Mod baytı host'ta değiştirilmez;stub yoktur.
Main CPU context'i native input callback dönüşünde adapter tarafından korunur.
Bu,GPIO taraması veya gerçek input-event kuyruğu/zamanlama kanıtı değildir.

Kanonik yeni SYX resetten açılır ve76 giriş yürütür.18 admission çağrısının6'sı
mod değiştirir,12'si reddedilir.24 native sample force-off çağrısı unmasked'dir;
admission masked'dir. Alt pad31,gerçek step32'yi düzenler. Basılıyken ve
release sonrası native pendingB8 varken geçiş reddedilir. Native track değişimi
pending/held/bit3 sahipliğini temizler;ardından kaydedilmemiş düzenleme aynı
raw pointer ve baytlarda korunarak Normal moda dönülür. Ownership host'ta
temizlenmedi.

İki modda10 ayrı negatif koşul için mevcut native store'a geçici fault değeri
yazılır:transport1/2,phase1/2,track7 note-owner. Bunlar gerçek Play/Stop/Save /
MIDI girişinin uçtan uca testi değildir. Her enjeksiyon sonrası özgün store
baytları geri konur. Pozitif pad/track/Shift/mod yollarında bu enjeksiyon yoktur.

Her mod commit'inde169092B raw proje ve metadata iki bankı/hash'i aynıdır.
Pad düzenlemesi raw hash'i değiştirir,fakat mod geçişleri onu değiştirmez.
Root/raw pointer'ları aynı,proje I/O çağrısı0,NOR mutation artışı0,ek tahsis0.
2331 allocation/heap2004EA98 ve2184B alan korunur. Canary ve instruction image
aynıdır;kanonik koşuda geçersiz bellek erişimi yoktur.

Son statik izde B8'in yalnız bir render kuyruğu olduğu varsayımı zayıfladı:
native press `5CC86`,timer6/delay300 için `5CE48` callback'ini kurar. Callback
`B8 &= ~C0` yapar;yani hâlâ basılı bitleri çıkarır. Release `5CD66`'da timer6'yı
şartlı iptal eder. Release ardından kalan B8'in kısa basış latch'i ile canlı
ownership ayrımı ve arm/cancel garantisi ayrıca doğrulanmalıdır. UI yenilemesi
B8'i otomatik temizleyecek diye kabul edilmez;bir sonraki yerel görev budur.

## Çevre girdileri ve negatif sınırlar

Main'in ilk tam turu `E0001004 DWT_CYCCNT` okur. Sınırlı yeni DWT modeli
disabled counter'ı tutar;enable isteğini/aktif counter okumalarını reddeder.
Elapsed cycle veya gerçek performans değeri uydurulmaz. Native25864/2592A
okumaları yalnız profil/diagnostic çevresindedir. Sayaç adresi/reset alanı için
[Arm Cortex-M4 TRM](https://documentation-service.arm.com/static/5f19da2a20b7cf4bc524d99a)
esas alınır;gerçek bootloader'ın DWT kurulumu kanıtlanmış değildir.

Main ayrıca DSP register802F'yi native305F4'ten okur. Varsayılan model burada
wire/RAM/TC yazmadan durur;tekrarlanan deneme RAM/MMIO'yu değiştirmez. Probe
sonradan iki açık `000000` register girdisi ekleyip iki Main turu tamamlar;
üçüncü tur liste tükendiği için yine durur. Native305F8 karşılaştırması400
dönüşünü ayrıca işler;802F'nin gerçek DSP davranışı yürütülmüş sayılmaz.

Önceki altı DSP mailbox girdisi,sentetik FAT12 NOR,ADC/calibration,802B-ready,
boş USB ACK ve non-nested FPU frame modelinin sınırları sürer. Yeni model
GPIO,NVIC,nesting,UART/DIN/USB receiver,timing,gerçek medya veya DSP kanıtı
sağlamaz. Ara keşif `before-live` /`exploratory-*` vehot replacement kaydıdır;
ana kanıt sıfırdan yeni SYX ile `probe/report.json` ve paket testidir.

## Yeniden üretim

`.venv\Scripts\python.exe` kullanılır;`-O` yoktur.

- `scripts/build_recovery_candidate.py`
- `scripts/probe_recovery_live_mode.py logs/recovery-live-mode-20261030/probe`
- `scripts/verify_recovery_candidate.py logs/recovery-live-mode-20261030/packaged`
- `scripts/audit_recovery_candidate.py logs/recovery-live-mode-20261030/audit`

Tam test için önce PowerShell'de `$env:PYTHONPATH='scripts;src;tests'`,sonra
`python -m unittest discover -s tests -v`. İlk import-path hatalı çağrı kesilip
ayrı loga saklandı;son tam sonuç `full-tests.txt`'dedir. Probe/verifier NO-GO
nedeniyle uygulama düzeyinde exit2 döner. Kesin sayımlar ve tek sonraki görev
`STATUS.md`'dedir.
