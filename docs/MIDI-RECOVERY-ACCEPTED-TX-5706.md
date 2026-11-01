> Tarihsel5dc7fd8a... accepted-job milestone'u:aşağıdaki nativeIRQ sonraki iş,
> güncel adayda IRQ/reset/EP0 modeliyle tamamlandı. Fiziksel sözleşme vefull
> boot hâlâ açık. Güncel karar STATUS veMIDI-RECOVERY-IRQ-5706.md içindedir.

# Kabul edilmiş MIDI IN işi:journal,retirement,kapatma tekrarı

29 Ekim 2026. **M7 NO-GO.** Offline firmware ve Unicorn/register-model kanıtı;
fiziksel cihaz/USB/MIDI API erişimi yoktur. Güncel hash/komutlar STATUS'tadır.

## Düzeltilen kayıp

Önceki56d4c10f... recovery adayı,USB submit'i Off+Stop8B'sini kabul edince
MAIN length'i sıfırlıyordu. Native close işi iptal edip reconnect olursa ne
FIFO'da ne MAIN'de borç kalıyordu. Yeni aday,aynı iki mod/128 poll senaryosunda
eski Off0/Stop0 → yeni Off1/Stop1 üretir. Önceki üç kayıp düzeltmesi korunur.

Native5261C→2C90C→42F92→52EDC ve normal5268E→268E0→268D0 completion walker'ı
gerçek stock kodudur. Configuration/open,ACK,AHB/FIFO flush,cancellation ve
completion olayı register/RAM modelindedir;tam4293E IRQ/EP0/PHY kanıtı değildir.
52EDC artık no-op stub değildir. İki aday da aynı yeni fixture/modeli alır.

## Bellek ve kontrol

Yeni `midi_accepted_tx_patch.py` kodu0807F000..0807FBAC içinde2988B'dir.
128B journal2004F6E0..2004F760,mevcut256B seq state'in son yarısını kullanır.
seq.OFF alanlarının üst sınırı80h'den büyükse build reddedilir. Ek heap
rezervasyonu yoktur;832+256=1088B aynı allocator tarafından sıfırlanır.
Bir native MAIN job:ARMING/ACTIVE/DONE,state phase,endpoint/controller,
pointer/length,generation,64B snapshot ve yalnız IN1 mask/ACK bilgisi tutulur.

- MAIN submit öncesi bounded16-word copy;close ARMING sırasında gelirse
  phase kapanır. Rejected submit borcu MAIN'de tutar. Başarılı submit ACTIVE
  olur;completion önce geldiyse DONE tek kez IDLE'a döner.
- Native2B4B2 full gate,job/close sahibiyken yeni writer'ı durdurur. Flush ve
  poll kapıları eski tamponu yeniden kullanamaz. Native268D0 doğru caller
  080526A9 ve açık phase ile kaydı bitirir. Close sırasında untagged veya
  native walker completion,eski job'ı serbest bırakamaz.
- Native5261C giriş kapısı,MIDI endpoint81/controller/list binding'i eşleşince
  generation artırıp freeze eder. Aktif/arming işte core FAULT ve mode-admission
  fault latch'i koyar. Yeni On/Clock/SysEx reboot'a kadar kabul edilmez.
  OFF/Stop alınabilir;mevcut FIFO'nun sahipliği silinmez.
- Her main poll en fazla bir retirement fazı ilerletir. Yalnız IN1 DAINT/
  DEACH/empty maskesi kapatılır. EPENA varsa EPDIS/SNAK istenir. EPENA0 ve
  gerekli disable ACK;AHB idle ve FIFO1 flush tamamlanmadan release yoktur.
  W1C/DSB sonrası XFRC/disable cause'ları yeniden kontrol edilir. Bit7'nin
  modelde sürekli1 kalması beklemeyi sonsuzlaştırmaz.
- Bariyerden sonra yalnız closing USB event'leri MAIN'e **kalan FIFO'dan
  önce** kopyalanır:Off,velocity0 On veStop. On/Clock/SysEx tekrar edilmez.
  Native HAL pointer/count ve timer cleanup'ı bundan sonra yapılır. IN1
  availability ve kaydedilmiş maskeler generation kontrolüyle atomik açılır.
  Diğer maskeler/RX/MSC/global RX FIFO guard tarafından değiştirilmez.

CPU mode0 dışı veya generation wrap fail-closed olur;shadow/job korunur.
Yeni native close,ilerleyen fazın generation commit'ini bozar ve request'i
yeniden başlatır. HAL işlemi veya copy/filter döngüsü maskeli çalışmaz.

## Kanıt ve kalan sınır

18 yeni test:iki modda kabul/cancel;64 Off ilk chunk iptali;eksik disable ACK /
flush;normal completion sonrası no replay;ARMING-completion veclose yarışları;
tekrar close/generation;yalnız IN1 maskeleri;IRQ/PRIMASK reddi;wrap/DMA reddi;
karma On/Clock/SysEx filtreleme;untagged/wrong caller;TXFE modeli ve mevcut
allocator'ın journal'ı A5'ten sıfırlaması. Source+paket üzerinde testli.

78 odaklı test,49 paket test+6 sınırlı Faz1 ölçütü,98 eski native/session/IRQ /
control/staging/composite testi PASS. Önceki FIFO/parent/MAIN/USB-DIN exact
stream testleri de geçer. Tam567 suite koşulmadı;önceki tam529 hash'i korunur.
Default seq/core kaynak/codegen aynı;130 kaynak pini121 önceki unchanged içerir.

**Bu fiziksel exactly-once kanıtı değildir.** Model iptal edilmiş işi teslim
edilmemiş sayar. Host kısmi/tam teslimi bilinmiyorsa güvenlik için kapanış
tekrarlanabilir. Yeni nota/clock/payload replay edilmez;iptal edilmiş SysEx
yanıtının tamamlandığı da iddia edilmez. Eski untagged XFRC
retirement sözleşmesini ihlal ederek yeni job'dan sonra zorla verilirse stock
ABI'sinde epoch yoktur;guard bunu yeni işten ayıramaz. Bir negatif test bu
sınırı korur. Gerçek IRQ/W1C/disable/flush/late-event sözleşmesi doğrulanmadan
USB reconnect güvenliği veya M7 GO iddiası yoktur.

Native IRQ reset/enum/EP0/class-init akışı,boot/OOM/RTOS/tam stack ve fiziksel
zamanlama henüz tam değil. RAM modeli/sıfırlama bir tam boot kanıtı değildir.
Stock storage riskleri bu oturumda genişletilmedi. Sonraki tek iş,güncel
guard'ın native4293E dispatch ve kontrol IRQ akışında sınanmasıdır.

## Audit ve yerel kanıt

`logs/off-stop-cancel-20261029` önceki/yeni SYX+manifest/scope,comparison,
tests,audit,session.diff vehashes.json içerir.37 asserted/disjoint app patch,
6884 değişen bayt,512B vektör/identity korunumu ve MPEG2 CRC strict doğrulanır.
Kaynak/manifest eşleşmesi gevşetilmez. Yeni guard SHA256:
`2eec4443a8abd2f318dc65d52f45a145e4bfb57094f266a468ccd0572fdee50c`.

24 maskeli yol,max38 komut;masked call/loop yok. Copy en fazla16 word,filtre16
unrolled slot;ABI/direct CFG/SP8 call alignment testli. Guard local frame max24B;
native trampoline frame'leri ayrı(-8/-24),no-credit shim native16B'yi tüketir.
İlk allocator init1155/1147 maskeli komut değişmedi. Cycle/IRQ latency ölçümü değil.

İlk request'te MOVS,TST flags'ini bozup EPDIS'i atlıyordu;borç tutuldu ama
ilerleme yoktu. Pozitif teslim assertion'ı ve ACK/flush negatifleriyle düzeltildi.
TXFE modelindeki1 değeri clear beklemesine dahil edilmez. İlk late-event testinde
deferred enqueue'dan sonra ikinci native poll gerekti;aynı sınırlı poll bütçesi
korundu. Eski fiziksel sınır veya negatif senaryo PASS diye gizlenmedi.
