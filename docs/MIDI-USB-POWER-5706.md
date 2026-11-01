> Güncel28 Ekim:447 toplam/87 aday PASS. Native main25870..25880 artık
> SysEx retry ve power service'e ulaşır;query,READ/CSW ve borçsuz uyku/uyanma
> manuel pump olmadan çalışır. Worker648AE..648B8 de gerçek native döngüdür;
> RTOS wait/return,ACK/IRQ/flash sınırları sentetik. Önemli açık:uyku öncesi
> retained MIDI debt,FROZEN consumer/ss_quiet döngüsünde wake sonrası64 main
> geçişinde de ilerlemez. Task kapısı bütünüyle kapanmadı.2584B checked RAM /
> init,diğer caller/boot/timing/Packs/storage alias/DIN açık. Üretim aynı /
> Off-Stop FAIL,M7 NO-GO. STATUS.md ve MIDI-USB-TASK-5706.md güncel.

---

# Normal USB suspend/wakeup — 28 Ekim 2026

Emülasyon prototipi,eski MIDI/MSC reader bırakılmadan USB saatinin durmasını
engeller. Wake/reset eski sleep isteğinden önceliklidir. Üretime eklenmedi;
M7 NO-GO. Fiziksel cihaz/MIDI/USB API erişimi yoktur.

## Native kanıt

- IRQ4293E bit31 wake'i bit11 suspend'den önce işler.11+DSTS808 bit0,
 42CD0→2C7E6→4279E yolunu çağırır. Controller+274 önce+275'e kopyalanır,
  +274=4 olur. USB+E00 bit0 reader/ACK beklenmeden set edilir.
- Wake42CB0→2C802→427AE yalnız eski state'i geri kopyalar.2C9F8(handle,0)
  USB+E00 bit0'ı temizleyip427AE'ye gider. Handle+20hex düşük güç flag'i
  system register'larını da etkileyebilir;prototip yalnız0 kabul eder.
-2C7E6'nın ikinci direct çağrısı42D12 LPM yolundadır. LPM27 desteklenmez.
  Direct byte/ref taraması bütün power/caller grafiğinin kanıtı değildir.

## Yeni sıra

1. IRQ preflight bilinen suspend için ortak control request ile kabulü
   dondurur. Native completion,eski snapshot'ı yeni completion gibi yayımlayamaz.
2. Ana servis mevcut storage/MIDI cancellation'ı yürütür. MC ve SS SEALED,
   eski reader/borç/disable ACK/AHB/shared FIFO/TX flush tamamlanmış olmalıdır.
3. Native4279E durum kaydı sonrası generation yeniden kontrol edilir.
   Kısa maskeli bölüm global IRQ maskesini wake/reset'e indirir;DSB sonrası
   clock-stop ve ASLEEP birlikte yayımlanır. Yarış varsa clock-stop yapılmaz.
4. ASLEEP servis/native factory çalıştırmaz;normal MMIO okunmaz. Yeni factory
   isteği bekler. Model yalnız GINT status/mask ve clock register erişimine
   izin verir. Bunların gerçek silicon wake-clock erişilebilirliği kanıtlanmadı.
5. Wake native ungate ve state restore yapar;eski global mask açılır. Sonra
   normal IRQ/class init yürür. Reset varsa eski configuration replay edilmez;
   yeni host enumeration/config gerekir. Erken wake,uyumadan yeniden kurar.

Native save içindeki wake testi,geç gelen clock-stop'ı engeller. Coalesced
wake+suspend ve reset+suspend öncelikleri testlidir. Tekrar suspend tek stop
yapar. LPM/deep-system-stop/DMA ve generation wrap terminal kapalı hatadır.

## Kanıt düzeyi ve çıktılar

D:pin'li stok byte'ları/direct refs/disassembly;3 stok gate+1 generated
service gate ve IRQ allow-mask MOVW/MOVT farkı. E:16 Unicorn testi;aktif READ,
admitted MIDI debt/eksik ACK,early/coalesced/racing wake/reset,MIDI-only query /
composite READ,asleep factory,DIN Off/project RAM ve MMIO guard. Korumasız
native suspend reader aktifken clock-stop yapar:zorunlu negatif. H:434 toplam
test/87 aday regresyon/6 sınırlı kriter,baseline/build/production audit PASS.
Paket16 PASS;probe/verifier exit2,NO-GO. Fiziksel test yapılmadı.

Kod1176B:0807C000..0807C498. State96B:20048320..20048380;toplam2520B state
sentetiktir. Default codegen ve önceki kaynaklar aynı. Audit SP delta0,BL8,
max24B local frame;3 yeni maskeli bölüm/max30 komut,call-loop yok. Bunlar
tam native call stack/ISR latency/cycle veya checked production RAM kanıtı değil.

Code SHA256:0965c37caf44ea8e5b64e667f02172ce121a7d7f4d98ac460afd0125d71af4bb.
IRQ variant:80a130b0e33ba70eeef52bc3bf3ed0f03a2fa30bda48f42702f6b5abea9ccaf9.
Kaynaklar src/midi_usb_power_prototype.py;scripts/{midi_usb_power_test_support,
audit_midi_usb_power_prototype,trace_midi_usb_power,probe_midi_usb_power}.py;
tests/test_midi_usb_power.py. Log/diff/hash ve komutlar STATUS.md'de.

İlk16 testte legacy IRQ error propagation,LPM hatasını BROKEN'dan CLOSING'e
gevşetti. Üst power error latch'i bunu düzeltti. Sonra ordinary-MMIO read guard
ve asleep global mask eklendi. İlk suite/probe eskidir;full-tests-final ve
probe-final son kaynağı doğrular. Negatifler kaldırılmadı.

Clock/PHY/wakeup erişilebilirliği,disable ACK/flush/NVIC/cache/RTOS/flash ve
latency sentetik sınırlar olarak sürer. Remote wake policy,LPM/deep stop/DMA,
tam Packs UI/project ve power grafiği,gerçek periodic task wiring,boot/OOM /
2520B reservation-init,storage project short-read/live-pattern alias,DIN input
ve üretim entegrasyonu açık. Bozuk bariyer sonrası eski untagged XFRC negatif
kanıtı ve üretim Off/Stop kaybı sürer. Stok/candidate syx
aynı;özel SD filesystem eklenmedi. Sonraki iş gerçek task/main-service bağıdır.
