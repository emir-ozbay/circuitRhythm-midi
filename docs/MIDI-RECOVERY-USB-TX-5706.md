> Tarihsel ilk MAIN düzeltmesi (56d4c10f...):aşağıdaki accepted-TX negatifi,
> güncel adayda retirement modeli altında PASS'e çevrildi. Tam IRQ/fiziksel
> sözleşme hâlâ açık. Güncel karar STATUS'ta;ayrıntı MIDI-RECOVERY-ACCEPTED-TX-5706.md.

# USB MAIN kabul öncesi Off/Stop koruması — 5706

29 Ekim 2026. Offline byte/disassembly + sentetik RAM Unicorn kanıtı.
**M7 NO-GO.** Fiziksel cihaz/USB/MIDI API erişimi yoktur. Güncel hash STATUS'ta.

## Hata ve üretim değişikliği

Native output worker, FIFO veya borrowed SysEx'ten USB-MIDI event'lerini
2B460 ile MAIN'e yazar. Port FIFO/cursor artık ilerlemiştir. 2B498, raw adapter
2B3BC→26880 üzerinden flush eder; 2B3BC koşulsuz ret1 üretir. Endpoint credit
yoksa 26880 submit yapmaz ve R0 sözleşmesi olmadan döner. 2B4AE yine MAIN
length'i sıfırlar. Böylece Off/Stop artık ne FIFO'da ne USB job'ındadır.

Yeni asserted patch'ler:

| Stok yer / byte | Yeni davranış |
| --- | --- |
| 0802B498 / 38b50446 | Kayıtlı ilk USB output driver için checked MAIN flush |
| 080268CC / 71bc7047 | Yalnız yeni submit BL'nin LR'sinde zero-credit ret1 |

Owner core magic/registry ile doğrulanır. Driver/raw vtable, endpoint81/64B,
RAM sınırları, configured/readiness, MAIN seçimi ve length0..64/multiple4
kontrol edilir. Sıfır length submit edilmez. Native26880 başarılı CPU submit
sonucu0'dır: 4301A'nın `002032bd` dönüşü stock pin'iyle denetlenir. Bu case'te
MAIN length tüketilir. Credit yoksa veya readiness kapalıysa MAIN korunur.
No-credit shim native16B frame'i aynı şekilde retire eder; foreign caller'ın
orijinal R0/pop/LR davranışı değişmez. Native26880'nin atomic credit döngüsü
ve HAL register yazımları aynen stoktur.

Retained full MAIN için ip_poll, önce aynı core port lease'i altında preflush
yapar; sonra normal core poll devam eder. Full MAIN aksi halde native402FC'nin
başta dönmesine neden olurdu. Flush owner mevcut recovery entry byte11'dir:
2004F33B. 832B core state/1088B toplam rezervasyon ve allocator init değişmez.
Core bu byte'ı başka yerde kullanmaz; ilk checked init tüm state'i sıfırlar.
Claim/release kısa maskeli commit'lerdir; HAL çağrısı maskesizdir. IRQ/masked
ve nested flush ret0 alır. ALT/foreign sağlıklı flush stock trampoline'a gider;
preflush ALT'yi tüketmez. Otomatik USB session resume veya fault clear yoktur.

## Negatif karşılaştırma ve testler

Önceki recovery SYX SHA256:
`09551fae9e0d36d42aa9e5964f7b342a262bca388c830bf847d5ff85768ec508`.
İki adaya da aynı native port/formatter, modeled configuration/zero-credit,
native5261C→2C90C→42F92 class-deinit ve128 output poll uygulanır.
52EDC hardware-close ve USB completion/UART drain dış sınırdır. Zero credit
native close tarafından üretildiği kanıtlanmış bir fiziksel register olayı
değildir; testte açıkça sağlanan kapalı bus/availability durumudur.

| Vaka, her iki mod | Eski aday | Yeni aday |
| --- | --- | --- |
| MAIN'e geçmiş Off+Stop, submit öncesi kapatma | MAIN0B, Off0/Stop0 | MAIN8B korunur; reconnect Off1/Stop1 |

11 yeni test: yukarıdaki iki mod; configured halde credit race; full64B MAIN
ve kalan FIFO; 64 Off+son Stop; nested poll/flush; IRQ/PRIMASK; foreign driver;
foreign no-credit caller ABI; stok ALT; borrowed150B SysEx partial cursor;
accepted-TX cancellation negatif kontrolü. Exact output, cursor ilerlemesi,
owner byte release ve payload sabitliği denetlenir. 60 odaklı test / 31 paket
test +6 Faz1 ölçütü PASS. Paket31'in içindeki bir test aşağıdaki ürün kaybının
sürdüğünü doğrulayarak geçer; test sayısı bir donanım GO ölçütü değildir.

## Kapanmayan kabul edilmiş TX sınırı

Native submit Off+Stop'un8B'sini kabul ettiyse MAIN length0/FIFO0 olur.
Model hardware close job'ı iptal eder ve reconnect olursa ikisi de yeniden
üretilmez. Test bu kaybı korur. Bu değişiklik kabul edilmiş TX'i geri almaz,
ACK/disable/flush bariyeri kurmaz, geç callback'i etiketlemez ve eski buffer'ın
yeni job'a verilmesini tek başına güvenceye almaz. Host'un kısmi teslimi de
modellenmez. Tam EP0/reset IRQ/PHY/gerçek receiver güvenliği iddiası yoktur.

Sonraki tek görev kabul edilmiş job'ın kapanış borcunu native close/init
arasında koruyan policy'dir; reader retirement olmadan buffer reuse yapılamaz.
Full boot/OOM/RTOS, zamanlama ve miras storage etkileri de M7 için açıktır.

## Kanıt dosyaları

`logs/off-stop-tx-20261029`: önceki/yeni SYX, manifest/scope, comparison,
11 yeni/60 odaklı/31 paket test,98 eski native/session/IRQ/control/staging /
composite testi, önceki burst/parent/driver regresyonu, strict audit, session.diff
ve hashes.json. 125 önceki source pin'inden4 değişti;121'i aynı. 3 yeni kaynak
ile128 pin var. Önceki tam529 sonucu hash'iyle korunur; discovery549, tam549
yeniden koşulmadı. Tüm549'un yeni firmware üstünde geçtiği iddia edilmez.

Core SHA ee158962... ve default seq codegen6a72a09d... aynıdır. Yeni glue
14 maskeli yolun üç kısa owner commit'ini ekler; max23 komut, masked call/loop
yok. Yeni glue frame max24B; no-credit shim +16B native frame tüketir.
İlk init1155/1147 maskeli; tam call stack veya fiziksel timing kanıtı değildir.

İlk close prologue tahmini yanlıştı; gerçek stok byte'ları pin'lendi. Önceki
submit fixture'ı native success R0 sözleşmesini taklit etmiyordu; ret0 düzeltildi
ve98 bağımlı test koşuldu. Audit tail-frame modeli ayrı tanımlandı. Stock
SHA/assert/overlap/vector/CRC veya source comparison kontrolü gevşetilmedi.
