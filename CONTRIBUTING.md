# Katkıda Bulunma

Katkıların için teşekkürler! Hata bildirimi, öneri ve pull request'ler memnuniyetle karşılanır.

## Hata bildirimi ve öneriler

[Issues](../../issues) bölümünden yeni bir kayıt aç. Hata bildiriyorsan şunları yaz:
- Windows sürümü, Python sürümü, telefon modeli ve tarayıcı
- Ne yaptın, ne bekliyordun, ne oldu
- Terminaldeki hata mesajı (varsa)

**Güvenlik açıklarını issue olarak açma**, [SECURITY.md](SECURITY.md) dosyasındaki yolu izle.

## Pull request süreci

1. Büyük bir değişiklik yapmadan önce bir issue açıp fikri tartış.
2. Depoyu fork'la ve ayrı bir dal (branch) üzerinde çalış: `git switch -c duzeltme/kisa-aciklama`
3. Değişikliğini yap ve testleri çalıştır:
   ```
   python -m unittest discover -s tests -v
   ```
   Yeni bir davranış ekliyorsan `tests/test_yolla.py` dosyasına test de ekle.
4. Kullanıcıyı etkileyen her değişikliği `CHANGELOG.md` içindeki **[Yayınlanmamış]** bölümüne bir satır olarak yaz.
5. PR aç. CI testleri otomatik çalışır; testler geçmeden PR birleştirilmez.

Kurallar:
- Yolla'nın tek bağımlılığı `qrcode`. Yeni bağımlılık eklemeden önce issue'da konuş.
- Güvenliği zayıflatan değişiklikler (onayı atlamak, anahtarı kaldırmak, dosya okuma/listeleme eklemek) kabul edilmez.
- Kod stilinde çevredeki koda uy.

## Bakımcılar için

### PR birleştirme
- PR'lar **Squash and merge** ile birleştirilir; `main` geçmişinde her PR tek bir commit olur.
- Squash commit başlığı, değişikliği kısa ve açık anlatmalı (ör. `Android Chrome'da yükleme hatası düzeltildi`).
- Birleştirmeden önce: CI yeşil, CHANGELOG güncel, davranış elle denenmiş (telefondan en az bir gönderim).

### Sürüm (release) alma
Sürümler [SemVer](https://semver.org/lang/tr/) kurallarına uyar: `MAJOR.MINOR.PATCH`
- **PATCH** (0.1.0 → 0.1.1): Hata düzeltmesi.
- **MINOR** (0.1.0 → 0.2.0): Geriye uyumlu yeni özellik.
- **MAJOR** (0.x → 1.0.0): Uyumluluğu bozan değişiklik (ör. kestirme adres biçiminin değişmesi).

Adımlar:
1. `yolla.py` içindeki `__version__` değerini yeni sürüme güncelle.
2. `CHANGELOG.md` içinde **[Yayınlanmamış]** altındakileri yeni bir `## [X.Y.Z] - YYYY-AA-GG` başlığına taşı.
3. Commit'le ve etiketle:
   ```
   git commit -am "Surum X.Y.Z"
   git tag vX.Y.Z
   git push origin main vX.Y.Z
   ```
4. Etiket push edilince [Release iş akışı](.github/workflows/release.yml) şunları otomatik yapar: sürüm numarasını ve testleri kontrol eder, `Yolla-vX.Y.Z.zip` paketini hazırlar, CHANGELOG'daki notlarla GitHub Release yayınlar.

Bir release hatalı çıkarsa etiketi silip yeniden kullanma. Düzeltmeyi yeni bir PATCH sürümüyle yayınla.
