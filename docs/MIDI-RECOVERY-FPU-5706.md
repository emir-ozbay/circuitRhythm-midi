# Cortex-M4F bağlamı ve koşullu tam açılış — 5706

30 Ekim 2026. Firmware değişmedi. Bu kayıt ARM emülasyonu ve dış test girdileri
ile elde edilen sonucu anlatır;fiziksel cihaz testi değildir. M7 NO-GO sürer.

## Çerçeve sözleşmesi

[ARM DAI0298A](https://documentation-service.arm.com/static/5f0352c0cafe527e86f5bc66),
Şekil1 ve Bölüm2–3 esas alındı. Basic frame32B;extended frame104B'dir.
Alt adresindeki ilk8 word R0–R3,R12,LR,PC,xPSR;sonraki alan S0–S15,FPSCR ve
ayrılmış word'dür. Dört bayt hizalama gerekiyorsa xPSR bit9 işaretler.
CONTROL.FPCA aktifken EXC_RETURN bit4 sıfırdır. Lazy kayıtta FP alanı önce
ayrılır;FPCCR.LSPACT/FPCAR bekleyen alanı gösterir. Handler ilk FP komutuna
geldiğinde alt kayıtlar yazılır. S16–S31'i görev değiştirici saklar.

Stok PendSV `25C22 VSTMDBEQ` ve `25C5E VLDMIAEQ` yollarını içerir. Bu yollar
host'ta yeniden uygulanmadı;native komutlar Unicorn'da yürür. Hardware frame
ile basic/extended exception return ise ayrı host shim tarafından sağlanır.

## Uygulama

`scripts/recovery_fpu_test_support.py` içindeki opt-in `FPUStartup`,önceki DSP /
medya katmanını genişletir. Varsayılan `WorkerStartup` FP/coprocessor komutlarını
reddetmeye devam eder. Firmware komutu,allocator veya TCB/ready-list sonucu
değiştirilmez. Önceki medya modeline yalnız `_qspi_irq` extension point eklendi;
varsayılan çağrı gövdesi aynı kaldı.

- Native CP10/CP11 ve ASPEN kurulumu aranır;desteksiz coprocessor ve manual
  context durumları reddedilir.
- Görev değişiminde outgoing R4–R11/LR,üst16 FP kaydı,alt16 FP kaydı veFPSCR
  native saklanan baytlarla karşılaştırılır. Incoming bank native restore ile
  doğrulanır;hardware kısmı frame'den çözülür.
- IRQ'lar PSP frame'i ayırıp native handler'ı MSP üzerinde çağırır. Normal
  dönüşte bütün CPU context snapshot'ı kopyalanmaz;alt kayıtlar gerçek emüle
  frame'den geri alınır. Üst bank ve callee kayıtları ayrıca karşılaştırılır.
- Lazy IRQ'da FP kullanılmazsa ayrılan72B dokunulmadan kalır. FP kullanılırsa
  alt bank ilk komuttan önce yazılır. Eager vealignment yolları da testlidir.
- Çerçeve boyutu ve yazılacak alanın tamamı task stack sınırı içinde olmalıdır.
  İç içe exception/lazy ownership,eksik CPACR/ASPEN ve geçersiz Thumb durumu
  devam ettirilmez.

İlk test bir host dönüş kusuru buldu:Unicorn'a çift PC yazmak Thumb bitini
silebiliyordu. Yeni katman PC'yi Thumb adresiyle geri yükler;giriş frame'inde
T=1/IPSR=0 arar. Üç görevde farklı FP/FPSCR ve R4–R11 sentinel değerleriyle
15 native geçiş bu düzeltmeyi sınar. Emulatorun açığa çıkardığı ek CONTROL bit3
fiziksel M4F kanıtı sayılmaz;frame türü mimari FPCA bit2'den seçilir.

## Testler ve kanıt ayrımı

Yeni testler gerçek native task stack/TCB/port başlangıcı üstünde sentineller
kullanır. Bir IRQ testi kullanılmayan RAM'de VMOV S0,R0 /BX LR çalıştırarak
alt FP kaydını özellikle bozar;firmware byte'ı değiştirilmez. Başka bir negatif
native saklanan üst FP kaydını bozup assertion'ın yakaladığını gösterir.
Bunlar sentetik kayıt/RAM testleridir,gerçek pad veya IRQ zamanlaması değildir.

Kanonik probe ise firmware'i resetten ana çalışma döngüsü `25864`'e kadar
yürütür;FPU bank/TCB/nesne seed etmez. Önceki altı açık DSP mailbox yanıtı,
sentetik FAT12 NOR,ADC2048/calibration1500,802B-ready,boş USB reset/flush ACK ve
yanıtsız SDIO çevre varsayımları sürer. Yardımcı DSP kodu yürütülmez.

Bu katman yalnız kontrollü sınırlarda,nesting olmadan çalışır. Tam NVIC,
öncelik/tail-chain,fault/stacking-fault/FPDSCR lifecycle ve çevrim/zaman
modeli değildir. IRQ body çağrısı MSP-call adaptörüdür;BX EXC_RETURN donanımı
Unicorn tarafından tümüyle yürütülmüş sayılmaz. Bu sınırlar M7'yi kapatmaz.

## Yeniden üretim

`.venv\Scripts\python.exe` (`-O` yok):

- `scripts/probe_recovery_fpu.py logs/recovery-fpu-20261030/probe-current`
- `scripts/verify_recovery_candidate.py logs/recovery-fpu-20261030/packaged`
- `scripts/audit_recovery_candidate.py logs/recovery-fpu-20261030/audit`

Probe/verifier uygulama düzeyinde exit2 ile NO-GO bildirir. İlk `probe/`
keşif kaydı Thumb dönüş düzeltmesinden öncedir;son kanıt `probe-current/`
ve güncel kaynak hash'leridir. Önceki7-test ara kayıt,son paket çalışmasının
yerine kullanılmaz. Kesin sonuçlar,heap/stack sınırları ve tek sonraki görev
`STATUS.md` içindedir.
