> Bu belge parent korumasının ilk 09551fae... adayıyla doğrulanmasını kaydeder.
> Aynı koruma yeni USB MAIN adayında yeniden PASS. Güncel kimlik/karar STATUS'ta;
> ek koruma ve açık accepted-TX kaybı MIDI-RECOVERY-USB-TX-5706.md içindedir.

# Native MIDI class re-init sırasında output sahipliğinin korunması

29 Ekim 2026. Yerel byte/disassembly ve sentetik RAM Unicorn kanıtıdır.
**M7 NO-GO; fiziksel cihaz testi yapılmadı.** Güncel aday kimliği STATUS'ta.

## Hata ve dar düzeltme

Native MIDI class init 08068A2C, global 20006F04 router'ını okuyup
08068A32'de BL 080297C0 yapar (stok `c0f7c5fe`, LR 08068A37).
297C0 üç output portunu dolaşıp vtable+4 / 401AC clear'ını çağırır.
Bu yol FIFO'yu, borrowed cursor/total alanlarını ve driver reset'ini işler.
Recovery bitmap'inde duran Off yaşarken FIFO'da duran Off silinebilir.
Son Stop'un ulaşması, notaların kapanmış olduğunu tek başına göstermez.

Yeni checked patch yalnız bu BL'yi `ip_parent_clear` kapısına yönlendirir.
Kapı LR, global router eşitliği, hizalı RAM sınırları, recovery magic,
port_count=3, port array ve üç registry girdisinin tam eşleşmesini denetler.
Eşleşirse native destructive clear çağrılmadan parent'a döner. Parent'ın
29AB0 RX rearm çağrısı aynen sürer. Eşleşmezse stock 297C0'a frame'i geri
alarak tail-branch yapar. 297C0 void'dir; R0 sonuç sözleşmesi yoktur.

Kapı salt okunur (16B stack frame hariç), döngüsüzdür; yeni RAM veya
PRIMASK değişikliği yoktur. HAL/MMIO, epoch, TX buffer, availability,
job release veya fiziksel reader retirement işlemez. Normal router/port
clear girişleri stok kalır. Recovery core baytları değişmedi; önceki
fault/quarantine ve reboot gerektiren yeniden kabul politikası korunur.

## Aynı senaryoda FAIL → PASS

Önceki gerçek recovery SYX dondurulmuştur:
`logs/off-stop-reset-20261029/before-recovery.syx`, SHA256
`2e12191f4649e32390e4c47d0ffc6e8bd3633da5a94ec0fba7ccdbed4add1540`.
İlk düzeltilmiş SYX SHA256:
`09551fae9e0d36d42aa9e5964f7b342a262bca388c830bf847d5ff85768ec508`.

Native port constructor/registration ve flash vtable'ları kullanılır;
recovery overlay'i veya elle bitmap seed'i yoktur. Her portta 64 On önce
gönderilir. Sonra iki kuyruk durumu kurulup gerçek 68A2C çalıştırılır;
iki aday da aynı 128 native output poll / çağrı başına 500k komut sınırını alır.

| Kapanışın konumu | Önceki aday, her port | Yeni aday, her port |
| --- | --- | --- |
| 64 Off FIFO'da, Stop deferred | 0 Off + 1 Stop | 64 Off + 1 son Stop |
| 32 Off + 32 Clock FIFO'da, 32 Off + Stop deferred | 32 Off + 1 Stop | 64 Off + 1 son Stop |

Normal/Sequencer modlarında toplam 4 karşılaştırmalı vaka. Eski native
router clear bir, port clear üç kez çalışır; yenide bu clear'lar sıfır,
native parent ve RX rearm yine birer kez çalışır.

9 yeni test: 64 Off, sağlıklı On/Off sırası, IRQ/PRIMASK korunumu, aktif
native output worker içinde parent, borrowed 60B SysEx, bağımsız native clear,
yanlış caller, eksik registry fallback ve native USB TX sırasında parent.
Son vaka iki modda 516B USB / her DIN'de 259B exact stream doğrular.
Paketlenmiş SYX üzerinde önceki 11 ile toplam 20 test + 6 Faz 1 ölçütü PASS.
49 odaklı Safety/ABI/integration testi PASS. Önceki burst testleri de PASS.

## Test sınırı ve açık risk

Fixture RX portuna kapasitesi sıfır olan 67B ring bağlar; gerçek 29AB0/269AC
semaphore dalı çalışır. Fiziksel RX başlatma ve tam EP0/IRQ reset zinciri bu
test değildir. Kontrollü final driver veya native formatter kullanılır;
USB completion/UART drain dışarıdan modellenir. Aktif TX'in korunması testi
gerçek USB cancellation/disable ACK/flush bariyeri çalıştırmaz.

FIFO'dan çıktıktan sonra staging'e/USB'ye kabul edilmiş Off/Stop'un reset
ile kaybolması, raw MAIN/ALT yeniden kurulumu, geç callback ve yeniden
bağlanma politikası hâlâ açıktır. Bu belge tam USB reset güvenliği iddiası
değildir. Tam boot/OOM/RTOS ve gerçek süre ölçümü de açık kalır.

Sonraki tek görev: mevcut adayda staging veya kabul edilmiş TX'teki
kapatma mesajına native reset/iptal uygula; kayıp/tekrarın ilk sınırını bul.

## Yeniden üretim ve denetim

Komutlar STATUS'ta; kanıtlar `logs/off-stop-reset-20261029` altında.
`comparison/report.json` eski/yeni hash ve vaka bazında sayaçları içerir.
`hashes.json` source/evidence pinleri ve exact session diff'i bağlar.
`audit/report.json` 31 asserted/disjoint app patch, CRC/vector/identity,
CFG/stack/çağrı ve parent salt-okunur/döngüsüz kontrolünü içerir.
İlk init 1155 / 1147 maskeli komut; normal core/glue maskeli maksimum 23.
Ek RAM yok; mevcut 832B recovery + 256B seq rezervasyonu korunur.

İlk fixture reset slotu eksikti; native clear unmapped fetch verdi. Sonra
void R0 beklentisi ve worker gözlemcisinin yanlış portu okuması düzeltildi.
İlk başarısız çıktılar silinmedi. Üretim düzeltmesi bunları maskelemez.
