# Yolla

iPhone'dan (ya da herhangi bir telefondan) Windows'a, aynı Wi-Fi üzerinden fotoğraf ve video gönder. Uygulama kurmak gerekmez, internete ya da buluta hiçbir şey çıkmaz. Her gönderim isteği bilgisayarda **onaylanmadan** tek bir dosya bile yazılmaz.

> Neden AirDrop değil? AirDrop, Apple'ın AWDL protokolünü kullanır ve Windows Wi-Fi sürücüleri bunu desteklemez. Yolla aynı işi yerel ağ üzerinden yapar.

## Kurulum (bir kez)

1. [Python](https://www.python.org/downloads/) kur. Kurulumda **"Add python.exe to PATH"** kutusunu işaretle.
2. Bu klasörü indir (GitHub'da **Code → Download ZIP**) ve bir yere çıkar.
3. `kurulum.bat` dosyasına çift tıkla ve yönetici iznini onayla. Bu adım güvenlik duvarında yalnızca Yolla'nın portunu, yalnızca ev ağına açar. Wi-Fi'yi "Özel" yapmana gerek yoktur.

## Kullanım

1. `Yolla.bat` dosyasına çift tıkla. Terminalde bir QR kod çıkar.
2. Telefonu bilgisayarla aynı Wi-Fi'ye bağla ve QR kodu kamerayla okut.
3. **Fotoğraf / Video Seç** düğmesine dokunup dosyaları seç.
4. Terminalde istek görünür:
   ```
   >> 192.168.1.23 12 dosya gondermek istiyor (48.3 MB):
        IMG_4021.HEIC  (3.1 MB)
        ...
   Kabul edilsin mi? [e/H]:
   ```
   `e` yazıp Enter'a basarsan dosyalar `Resimler\Yolla` klasörüne iner. Başka bir şey yazarsan ya da 5 dakika boyunca yanıt vermezsen istek reddedilir.

Başka bir klasöre kaydetmek için: `Yolla.bat --dir "D:\Fotolar"`

## Paylaş menüsünden gönderme (isteğe bağlı, iPhone)

Fotoğraflar uygulamasında **Paylaş → Yolla** ile göndermek için bir Kestirme oluştur:

1. **Kestirmeler** uygulaması → **+** → adını `Yolla` koy.
2. Ayarlar (ⓘ) → **Paylaşım Sayfasında Göster**'i aç, kabul edilen türleri **Görüntüler** ve **Ortam** olarak bırak.
3. **Tekrarla: Kestirme Girdisi'ndeki her öge** eylemini ekle. İçine:
   - **URL'nin İçeriğini Al**
     - URL: `http://<bilgisayar-ip>:8765/upload/` + **Tekrar Ögesi → Ad** + `?k=<anahtar>`. Adres ve anahtar, terminalde yazan bağlantıdan alınır. Uzantı da gelsin diye "Ad"a dokunup "Dosya Uzantısı Dahil" seç.
     - Yöntem: **PUT**, İstek Gövdesi: **Dosya** → **Tekrar Ögesi**

Kestirme dosyaları tek tek gönderdiği için terminal ilk dosyada `[e]vet / [h]ayir / [t]umu` diye sorar. `t` yazarsan o telefondan sonraki 10 dakika boyunca gelen dosyalar sormadan kabul edilir.

Not: Bilgisayarın IP adresi değişirse kestirmedeki adresi güncellemen gerekir. Bunun olmaması için modemden bilgisayara sabit IP (DHCP rezervasyonu) verebilirsin.

## Güvenlik

- Yolla yalnızca `Yolla.bat` penceresi açıkken çalışır.
- **İki katmanlı koruma:** İstek gönderebilmek için QR koddaki gizli anahtar (`?k=...`) gerekir. Anahtar doğru olsa bile her gönderim terminalde onaylanmalıdır. Onaylanan istek yalnızca listelenen dosyaları, listelenen boyutlarda ve yalnızca bir kez kabul eder.
- Yolla bilgisayardaki dosyaları **okumaz** ve listelemez; yalnızca kayıt klasörüne yeni dosya yazar.
- Anahtar `token.txt` dosyasında saklanır ve ilk çalıştırmada her bilgisayar için ayrı üretilir. Sızdığını düşünürsen dosyayı sil; bir sonraki açılışta yenisi oluşur. Bu klasörü başkasıyla paylaşırken `token.txt` dosyasını paylaşma.
- Bağlantı HTTP olduğu için şifrelenmez. Ev ağında sorun değil, ama kafe ya da otel gibi ortak ağlarda kullanma.

## Sorun giderme

- **Telefon sayfayı açamıyor:** `kurulum.bat`'ı çalıştırdığından emin ol. Telefon ile bilgisayar aynı Wi-Fi'de olmalı; misafir ağları genellikle cihazları birbirinden yalıtır.
- **"Yasak/403" hatası:** Adresin sonundaki `?k=...` eksik ya da eski. QR kodu tekrar okut.
- **Güvenlik duvarı izin penceresi açılırsa:** "İptal"e basma. İptal, Python'u engelleyen bir kural oluşturur. Pencereyi **X** ile kapat ve `kurulum.bat`'ı çalıştır.
- **Fotoğraflar JPEG geliyor, HEIC istiyorum (ya da tersi):** Seçim ekranında sağ üstteki **Seçenekler**'den formatı seç.
- **HEIC dosyaları açılmıyor:** Microsoft Store'dan "HEIF Görüntü Uzantıları"nı kur.

## Gereksinimler

Windows 10/11, Python 3.9+. Telefon tarafında yalnızca bir tarayıcı yeter: iPhone'da Safari, Android'de Chrome.

## Lisans

[MIT](LICENSE): Ücretsiz olarak kullanabilir, değiştirebilir ve paylaşabilirsin.
