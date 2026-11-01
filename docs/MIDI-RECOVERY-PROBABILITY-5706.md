# Native Probability — 31 Ekim 2026

Güncel aday ve biten koşunun sonuçları `STATUS.md` içindedir. Bu belge
Probability testinin kapsamını açıklar. Fiziksel cihaz/port erişimi yoktur;
M7 NO-GO.

## Nesne ve veri sözleşmesi

Probability mode6, Pattern Settings iç düğme12'nin ikinci görünümüdür.
Üst16 pad aynı track'in StepView'ına, alt16 pad `grid+11C+4*track` nesnesine
gider. Vtable08067E6C, pad handler080574C4, release08052116'dır. Stok pad
dönüşümü alt pad'in fiziksel numarasından16 çıkarır.

`view+C` adım modeline işaret eder. Model+0 ST1, +4 ST2, +C seçili adım
store'udur; aynı StepView'ın gerçek pointer'larıyla karşılaştırılır.
`view+10` transport store'u, `view+18` varsayılan nota store'udur.

Native574C4 yalnız yerel0..7'yi işler; 8..15 işlem yapmaz. Aktif adımda
yalnız olasılık baytı değişir. İlk pattern için raw adresi
`2E4+track*5140+step*8+4`'tür. Değerler0..7'dir; istatistiksel çalma sıklığı
bu testte ölçülmez.

Boş adımda geçerli olasılık pad'i; varsayılan nota, gate6, microstep1,
velocity96, seçilen olasılık, sample flipFF ve flags0 ile adım oluşturur.
Olasılık0 da aktif adım oluşturur; boş kayıt olarak yorumlanmaz.
Native durdurulmuş görünüm, üst pad bırakıldıktan sonra son seçili adımı
düzenlemeye devam eder. Bu yolda C0/bit3 sahibi oluşturulmamalıdır.

Native5761E, aktif adımda0'dan seçilen değere kadar LED'leri stok62AB0
tablosunun45+i girişleriyle doldurur. Kalan ilk sekiz hücre tablo0 rengidir;
diğer sekiz hücre0 kalır. Boş adımda ilk sekiz hücre tablo0 rengidir.
Her yazıda bu tampon, her senaryonun0/7 uçlarında da native4DD1C
compositor'ının üst page32B +alt Probability32B sonucu denetlenir.
Bu fiziksel LED veya olasılık dağılımı ölçümü değildir.

## Native test matrisi

- 8 track ×Normal/Sequencer ×iki sayfa: üst16 pad için512 adım eşlemesi.
- 64 uç senaryosu: ilk pad Shift'siz, son pad Shift ile; adım32 dahil.
  Sekiz değer ileri/geri ve tekrar denenir; işlem yapmayan sekiz pad de sınanır.
- Boş adım, native Microstep görünümünde bitleri kapatarak hazırlanır.
  Başlangıç nesnesi, store, page, raw veya ownership RAM'i host'ta seed edilmez.
- 32 senaryoda velocity120/gate96/microstep33 native editörlerle oluşturulur;
  olasılık değişirken diğer yedi bayt aynen kalmalıdır.
- 32 durdurulmuş/üst pad basılı değil senaryosu son seçili adımı düzenler.
  Her Probability pad girişinde canlı C0/bit3 sahipliği aynı kalmalıdır.
- 64 basılı-pad mod denemesi reddedilir. Release sonrasında fiziksel ve
  canlı adım sahipleri boşalır.128 tam LED bileşimi karşılaştırılır.

## Mutate kapsamının genişletilmesi

Her sayfadan sonra aynı adımda farklı olasılık3, microstep33, gate96 ve
velocity120 taşıyan kayıt bulunur. Shift27+Duplicate24 ile toplam32 native
Mutate senaryosu çalıştırılır. Önce/sonra32 tam8B adımın multiset'i aynı
olmalı, yalnız seçili track'in ilk pattern'inin256B adım alanı değişmelidir.
Her track/mod için iki denemeden en az birinde gerçek yer değişimi gözlenir.
Rastgele bir permütasyonun bazen aynı veriyi üretmesi hata sayılmaz.

Bu, önceki Velocity/Gate ağırlıklı Mutate kapsamına olasılık ve microstep'in
diğer parametrelerle birlikte taşınması kanıtını ekler. Sample flip ve
automation farklı değerlerle zenginleştirilmedi; bu kapsam açık kalır.
Rastgelelik dağılımı ve oynarken Mutate zamanlaması da sınanmaz.

## Yürütme sınırları ve tekrar

Native Main her16 callback girdisinde ve belirli sınır noktalarında çalışır.
Sonlu2048 açık802F=000000 DSP yanıtı ve65536 UART TXE kredisi vardır.
Native IRQ53/54, FPU frame ve TDR yazıları kullanılır; FIFO/consumer/fault /
ownership RAM'i host'ta temizlenmez. Image, canary, metadata, raw pointer,
heap, tahsis, proje I/O ve NOR mutation sayaçları karşılaştırılır.
Native Probability kodu stokla bayt bayt aynıdır.

Controller callback girdisi GPIO/input kuyruğu değildir. Transport durur;
gerçek çalma sıklığı, playhead, Note Off/Clock zamanlaması veya fiziksel MIDI
teslimi kanıtlanmaz. DSP/NOR/ADC/USB sınırları, disabled DWT ve non-nested
FPU varsayımları sürer.2184B heap payı yalnız bu workload için gözlemdir.

`scripts/probe_recovery_probability.py` bir paket unittest'ini kaynak
codegen=image=SYX koşuluyla çalıştırır. Probe ve unittest aynı koşudur.
Başarıda da M7 NO-GO nedeniyle exit2 döner. Genel verifier testi içerir;
`--core-only` beş uzun native UI matrisini açıkça hariç tutar. Testler
`.venv\Scripts\python.exe` ile, `-O` olmadan çalıştırılır.
