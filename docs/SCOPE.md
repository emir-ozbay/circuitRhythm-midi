# Proje Kapsamı ve Hedefleri

Bu belge projenin güncel hedeflerini, kapsam sınırlarını ve uygulama sırasını tanımlar.

## 1. Temel Amaç ve Ürün Hedefi

Circuit Rhythm normalde sample tabanlı bir groovebox'tır. Bu projenin amacı:

- **Harici MIDI Kontrolcüsü / Sequencer:** Cihazın dahili sample çalma motorundan bağımsız, harici synth ve ses modüllerini süren bir sequencer olarak çalışmasını sağlamak.
- **Tek Ekranda 32 Adım:** Normalde 16'şar adımlık sayfalar (1–16 ve 17–32) halinde gezilen step sequencer'ı, 32 pad'in tamamını kullanarak aynı pattern'in 1–32 adımlarını tek bir ekranda aynı anda gösterecek ve düzenletecek hale getirmek.

---

## 2. Kapsam ve Sınırlar

### İlk Sürüm (Şu Anki Kapsam - 32 Adım)
- **32 Pad Görünümü:** 32 pad üzerinde aynı pattern'in 32 adımı birlikte görüntülenir ve düzenlenir.
- **8 Track ve Pattern Korunumu:** 8 track ve pattern yapısı aynen korunur (track sayısı veya pattern sayısı azaltılmaz).
- **Sequencer Davranışları:** Gate, Velocity, Microstep, Probability, Tie ve Mutate gibi stok sequencer yetenekleri ve parametreleri eksiksiz korunur.
- **Mod Geçişi:** Henüz çakışması olmayan güvenli bir tuş kombinasyonuyla stok mod ve Sequencer Only modu arasında geçiş sağlanır. Normal moda dönüşte tüm normal işlevler korunur.
- **Proje ve Sayfa Yönetimi:** Sequencer Only modunda Packs sayfası devre dışı bırakılır; ileride projelerin stok projelerle karışmaması için ayrı proje alanı oluşturulur.
- **Görünüm Bağımsızlığı:** Note ve parametre görünümleri kendi ihtiyaç duydukları düzeni korur (her görünümde 32 pad zorunlu adım düğmesi değildir; tek adım sayfasında oklarla sayfa değiştirme gerekmez).

### Gelecek Hedef (64 Adım)
- Tek bir mantıksal pattern'de 64 adım desteği ve sayfalar arasında gezinme.

> [!NOTE]
> Bellek analizi ([LONG-PATTERN-TESTS.md](../analysis/LONG-PATTERN-TESTS.md)), stok veri yapısında doğrudan 33. adıma yazmanın veri çakışmasına yol açtığını göstermiştir. Bu nedenle 64 adıma geçiş için RAM/kayıt mimarisi kanıtlanmadan sınır artırılmayacaktır.

### Kapsam Dışı
- Şimdilik 128 adım, polifoni, Elektron ek özellikleri, yeni synth/sampling/DSP motoru geliştirilmeyecektir.

---

## 3. Açık Kararlar
- Güvenli mod geçiş tuş kombinasyonu seçimi.
- Pattern uzunluğu kısaltıldığında dışarıda kalan adımların korunması.
- Kaydedilmemiş projeyle mod değiştirme davranışı.
- Ayrı sequencer projelerinin dosya ve disk biçimi.
- Gerçek MIDI çıkış aralığı ve gate davranışı.
