> Güncel31 Ekim /Probability — Native yardımcı görünüm sayfa/pad grubu
> tamamlandı: Note1/7, Velocity2/Gate3, Pattern Settings4, Microstep5, Probability6.
> Yeni mode6 testi:512 üst pad/64 uç/128 LED/32 zengin Mutate PASS;26 hedefli PASS.
> Önceki147 aynı image'de, tekrar koşulmadı. Genel verifier148/core-only143.
> Firmware3f979b70…/CRC5AB3F54B, üretim ve1088B RAM aynı; M7 NO-GO.
> Sonraki iş: native Play17/Stop17→player/scheduler→1–32 playhead izi.
> STATUS veMIDI-RECOVERY-PROBABILITY-5706.md güncel; altı tarihseldir.

---

> Güncel31 Ekim /Microstep — Native mode5 iki sayfa/8 track/iki mod PASS.
>512 üst-pad eşlemesi,64 uç senaryo,tüm64 maske,128 LED bileşimi ve64 held
> guard sınandı.32 velocity/gate koruması +32 durdurulmuş idle edit PASS.
> Yeni1 paket ve26 hedefli test PASS;önceki146 aynı image'de,tekrar koşulmadı.
> Genel verifier147/core-only143. Firmware3f979b70…/CRC5AB3F54B veüretim aynı.
>1088B rezervasyon/2184B workload payı aynı;M7 NO-GO. Sonraki:native Probability6.
> STATUS veMIDI-RECOVERY-MICROSTEP-5706.md güncel;altı tarihseldir.

---

# Native Pattern Settings — 31 Ekim 2026

Güncel aday, koşu sonuçları ve kalan işler `STATUS.md` içindedir.
Bu belge native Pattern Settings testinin sözleşmesini ve sınırlarını açıklar.
Fiziksel cihaz veya port erişimi yoktur; M7 NO-GO.

## Gerçek nesne ve düzen

Stock4DC50 mode4'te4DBDC'ye gider.4DBE6 jump table'ının mode-1 girişindeki
21 değeri4DC28'e, oradan `grid+FC+4*track` nesnesine götürür. Her iki pad
yarısı aynı Pattern Settings nesnesidir. FC alanını nesne sırasından tahmin
etmek doğru değildir;DC alanı Microstep mode5'e aittir.

- Vtable08067EA4;pad handler08057218,release08052116,LED0805737C.
- `view+C` üç word'lük pattern ayar store'udur. Word0 byte0 End,byte1 Start;
  word1 sync rate,word2 yön seçimini taşır.
- `view+10` gerçek controller Shift store'u ile aynıdır.
- `view+14` aynı track'in gerçek StepView nesnesidir.
- `view+18` aynı StepView+60 page store'udur.

Aktif ilk pattern için raw parametre tabanı
`2E4+track*5140+100`'dür. Test başlangıç pattern'ini RAM'de değiştirmez.

| Girdi (iç pad numarası0..31) | Stok sonuç | İzin verilen raw yazı |
| --- | --- | --- |
|Üst0..15 |End=page*16+pad |parametre+0 |
|Shift+üst0..15 |Start=page*16+pad |parametre+1 |
|Alt16..23 |Sync enum=23-pad (7..0) |parametre+2 |
|Alt24..27 |Ayrılmış/boş |yok |
|Alt28..31 |Yön enum=pad-28 (0..3) |parametre+3 |

Native572A2 seçili hız/yönün LED'ini stok62AB0 renk tablosuyla günceller.
5737C üst satırda seçili Start/End hücresi dışındaki StepView LED'lerini
kopyalar. Native4DD1C compositor'ının64B sonucu Pattern Settings tamponuyla
karşılaştırılır;alt pad'lerin seçili/seçili-değil renkleri de her girdide sınanır.
Bu fiziksel LED ölçümü değildir.

## Mutate ve tuş numarası düzeltmesi

Novation'ın [resmî kılavuzuna](https://userguides.novationmusic.com/hc/en-gb/articles/25494352385810-Using-Circuit-Rhythm-s-patterns)
göre Mutate,Shift+Duplicate ile pattern adımlarını yeniden dağıtır ve adım
parametrelerini birlikte taşır. Bu bir üretici açıklamasıdır;testin kanıtıyla
karıştırılmaz.

5706 controller iç enum'unda Shift27,Duplicate24'tür.3D96C dispatch table'ı
23/24'ü controller+24'e,oradaki native4B620 handler'ına gönderir. Shift+24,
modifier2 üzerinden stok Mutate yolunu çalıştırır.

**Eski keşif notlarındaki16/17=Clear/Duplicate etiketi yanlıştır.17 Play'dir.**
Yeni keşifte bu varsayım transport'u başlatınca aynı native17 ile durduruldu;
o oturum kanonik test değildir. Kanonik test yeni resetten başlar,17'yi
kullanmaz ve her girdide transport0 koşulunu denetler. Kaynak/firmware
düzeltmesi yapılmadı;test girdisinin etiketi düzeltildi. Trace saklandı.

Test32-step Start0/End31 aralığını native pad'lerle kurar. İki sayfada
Velocity/Gate girişleriyle farklı aktif8B kayıtlar üretir;RAM seed edilmez.
Pattern Settings'e dönüp her iki sayfada Shift27+Duplicate24 uygulanır.
Önce/sonra32 tam8B kaydın multiset'i aynı olmalıdır. Yalnız seçili track'in
ilk pattern'inin256B adım bölgesi değişebilir;parametre başlığı,diğer pattern /
track'ler ve global raw alanları aynıdır. Sıralamanın gerçekten değiştiği de
denetlenir. Zenginleştirilmiş automation/sample flip/probability/microstep
örnekleri bu testte yoktur;bu alanların farklı değerlerle eşleşme kanıtı
ayrıca gereklidir. Rastgelelik dağılımı sınanmaz.

## Test sınırları ve tekrar çalıştırma

`test_recovery_pattern_settings.py` bir kez resetten kurulan nesnelerde8 track,
Normal/Sequencer veiki sayfayı dolaşır.1024 üst-pad/Shift ve1024 alt-pad
eşlemesi,64 LED bileşimi,64 basılı-pad mod reddi ve32 Mutate senaryosu sınanır.
Boş alt pad24 de fiziksel sahipliği nedeniyle mod geçişini reddetmelidir.
Üst/alt Pattern Settings pad'leri StepView C0/bit3 sahipliği oluşturmamalıdır.

Native Main her16 callback girdisinde ve belirli sınır noktalarında çalışır.
Sonlu2048 açık802F=000000 DSP yanıtı ve65536 UART TXE kredisi vardır.
Native IRQ53/54,FPU çerçeveleri ve TDR yazıları kullanılır;FIFO,consumer
indeksleri,ownership veya fault RAM'i host'ta temizlenmez. Tam instruction
image,canary,heap,metadata,raw pointer ve I/O/NOR sayaçları karşılaştırılır.
Native Pattern Settings kodu stokla bayt bayt aynıdır.

Controller callback girdisi GPIO/input kuyruğu değildir. Native Main turu
geçen zaman veya tam playback kanıtı değildir. DSP/NOR/ADC/USB sınırları,
disabled DWT ve non-nested FPU varsayımları sürer.8B kayıtların taşınması
fiziksel MIDI Note Off/Clock ömrünü kanıtlamaz.2184B heap payı bu workload
içindir. Cihaz için test onayı veya firmware gönderme adımı yoktur.

`.venv\Scripts\python.exe scripts/probe_recovery_pattern_settings.py
logs/recovery-native-pattern-settings-20261031/probe` yeni tek unittest'i
kaynak codegen=image=SYX koşuluyla çalıştırır. Başarıda da M7 NO-GO nedeniyle
exit2 döner. Genel verifier varsayılan olarak bu testi de içerir;
`--core-only` artık üç uzun native UI matrisini açıkça hariç tutar.
