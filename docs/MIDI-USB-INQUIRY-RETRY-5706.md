> Devam:ordered=True varyantında Note On/Stop sıra bozulması kapatıldı;
> 14 yeni/244 toplam test PASS.616B kod,aynı RAM. Tam kapasite arkasındaki
> Clock/Stop gecikmesi açık,M7 NO-GO. MIDI-USB-ORDER-5706.md ve STATUS.md güncel;
> aşağıdaki722B tek-token/bypass deneyi aynı hash ve negatif testlerle korunur.

# USB inquiry sahipliği deneyi — 27 Ekim 2026 / NO-GO

Önceki tıkanmanın dar USB inquiry kısmı aşıldı: TX slotu doluyken gelen
`F0 7E 7F 06 01 F7`, host yeniden göndermeden daha sonra tek bir17B yanıt
üretir. Bu **Unicorn/sentetik RAM kanıtıdır**; üretim firmware'ine eklenmedi.
DIN giriş retry'si, genel SysEx geri basıncı ve M7 tamamlanmadı.

## Sahiplik ve tüketim noktası

Stok `29AC8`, `269F0 -> 25B1A` ile USB ring kaydını önce pop eder; buffer'ı
geçici cursor ile tüketir. `404BC` parser'ı SysEx tamamlandığında2 döndürür;
`29BAA -> 24B68` void multicast zinciri producer ret'ini kullanmaz.

Yeni `src/midi_usb_inquiry_prototype.py`, yalnız emülatörde `29AC8` girişinin
assert edilmiş4B prologue'unu değiştirir. Bir kayıtlı USB endpoint/cable0:

1. Tur başına en fazla bir64B RX buffer'ı native pop ile kendine ait alana alır.
   Cursor, paket içi byte indeksi ve işlenmiş realtime işaretleri kalıcıdır.
   Önceki buffer'da işlenmemiş byte varsa sonraki buffer pop edilmez.
2. Native `404BC` ve kısa mesaj ring/`24B68` zinciri yürür. Yalnız tam6B inquiry
   tanınır. Bekleyen istek bir token ile temsil edilir: input payload'ına veya
   parser tamponuna bağımlı değildir. Yanıt pin'li flash'taki17B sabit dizidir.
3. `sr_submit` kabul0 vermeden token temizlenmez. Dolu/fault durumda sonraki
   USB poll bir kez daha dener. Bu kabul, sahipli TX kopyasıdır; wire completion
   anlamına gelmez. Retry modülünün önceki port/notification sözleşmesi sürer.
4. Token beklerken aynı buffer'daki `F8..FF` byte'ları native `29C1A` ile bir
   kez işlenir. CIN padding'i veri sayılmaz. İşaretler, normal cursor dönünce
   ikinci Clock/Stop dispatch'ini önler. Yalnız realtime kalan buffer bırakılır;
   sonraki realtime-only buffer'lar da ilerleyebilir.
5. Diğer SysEx native registry'ye gider; onların retry'si çözülmüş değildir.
   Tam update/storage handler zinciri testlerde çalıştırılmaz. Tam inquiry
   native multicast'i atladığından diğer listener yan etkileri kanıtlanmadı.

Yeni kod **722B**, ek sentetik RAM **172B**, önceki recovery832B + retry428B
ile **1432B**. `20047C00`, `20047800`, `20047000` üretimde boş RAM değildir.
Üretim heap/init entegrasyonu yoktur. Yeni kod SHA256:
`b1b24f86615963f3a4cc08366c51a4bade7604cc53b880412877aa54edfe0b0b`.
Eski üç retry varyantı ve recovery kodu değişmedi.

## Olumlu emülasyon kanıtı

17 yeni test; bütün suite **230 PASS**. Gerçek paketlenmiş aday üzerine
yalnız Unicorn overlay ile aynı17 test tekrar PASS:

- Meşgul slot, açık host resend olmadan tam bir yanıt; burst8 inquiry için8 yanıt.
- Tek retained buffer/queued buffer sahipliği, FIFO wrap ve her byte sınırında
  parçalanmış inquiry; parser/pop kaynakları ezilse de pending token korunumu.
- SysEx içinde realtime, CIN padding ayrımı ve aynı Clock/Stop'un tekrarlanmaması.
- PRIMASK/IPSR/nested poll reddi; cursor/token ve canary korunumu.
- Native USB endpoint/UART buffer stall'ında360B ilk aktarım ve iki inquiry
  yanıtının tam USB baytları; DIN **çıkışında** ilk360B aynen korunur.
- Her iki modda64 gerçek player sesi + Clock/Stop:64 Off ve1 Stop çıkışı,
  raw proje baytları korunur. Oluşan recovery fault'unda inquiry token'ı bekler;
  test SysEx'i bitirmek için fault'u temizlemez.

Yerel Capstone CFG/ABI: SP delta0, BL noktalarında8B hizalama, en büyük yerel
frame32B. Yeni kod IRQ maskesi eklemez.64B buffer'a bağlı tarama döngüleri
sınırlıdır; TX-ready bekleme döngüsü yoktur. Native toplam stack/cycle, gerçek
IRQ/RTOS/task-switch ve unarmed USB rearm yolu bu kanıtın dışında kalır.

## İki gerekli negatif kontrol

**1. Sonraki buffer'daki Clock/Stop bekliyor.**
İlk buffer'da iki inquiry, sonraki buffer'da F8+FC olsun. TX doluyken ilk
inquiry token olur; ikinci inquiry'nin baytları cursor'u tutar. Sonraki buffer
pop edilmediği için F8+FC'ye ulaşılamaz. Test, TX boşalana kadar clock sayacının
0 kaldığını ve boşalınca1 olduğunu doğrular. Dolayısıyla genel realtime
hizmeti **FAIL**; yalnız aynı buffer testinin geçmesi bu kapıyı kapatmaz.

**2. Realtime bypass, önceki Note On'un önüne geçebilir.**
Aynı buffer'da `inquiry, Note On, Stop` ve dolu TX durumunda Stop önce
dispatch edilir; TX açılınca gecikmiş Note On dispatch edilir. Native kısa
mesaj dağıtıcısında bu ters sıra ölçüldü. Sıra politikası **FAIL**; bu prototip
üretime alınamaz. Kısa mesaj callback sınırı gözlenmiştir, gerçek dış notanın
ses üretimi bu negatif testte çalıştırılmamıştır.

Finite buffer sayısını artırmak bu iki sorunun genel çözümü değildir. Sonraki
tasarım inquiry yanıt yükümlülüğünü müzikal RX cursor'undan ayırmalı; kapasite
dolduğunda isteğin nasıl kabul/ret edildiğini açıkça tanımlamalı ve Note On/Off
ile Stop sırasını korumalıdır. Sınırsız trafik için kayıpsızlık iddiası yoktur.

## Tekrarlanabilir komutlar ve kayıt

Python yalnız `.venv\Scripts\python.exe`; `-O` kullanılmaz:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_midi_usb_inquiry.py -v
.\.venv\Scripts\python.exe scripts/probe_midi_usb_inquiry.py logs/usb-inquiry-retry-20261027/probe-final
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Probe exit2/NO-GO beklenir; `report.json` olumlu kriterleri ve iki FAIL'i ayrı
yazar. `probe-final/audit/` native disassembly pencereleri, yeni kod CFG/ABI
raporu ve emulator overlay manifestini içerir. `tests-first.txt`,
`tests-second.txt`, `tests-final.txt` ilk yanlış fixture beklentilerini korur:
ready0/full1 ayrımı, durmuş transport'un Stop'u yok sayması, playback fixture'ın
note receiver içermemesi ve1B realtime sonrası stack padding'inin tanımsızlığı.
Beklentiler native sözleşmeye göre düzeltildi; negatif ürün kriterleri korunur.

Build/baseline/üretim audit PASS. Verifier87 regresyon/6 sınırlı kriter PASS;
üretim Off/Stop probe'ları hâlâ FAIL, exit2. Aday/stok hash'leri STATUS.md'de.
Donanım/MIDI/USB portu veya donanım API'sine erişilmedi.

**Sonraki tek iş:** inquiry kabul/yanıt yükümlülüğünü müzikal RX cursor'undan
ayıran bounded admission tasarımını uygulayıp bu iki negatif senaryoyu, yeni
kapasite doluluğu ve sıra testleriyle birlikte kapatmak. DIN input, bütün
producer/observer uyumu, checked RAM/init, boot/OOM, mode/reset-resume, storage
hata kurtarma, IRQ/DMA/disconnect ve süre bütçesi daha sonra da açık olacaktır.
