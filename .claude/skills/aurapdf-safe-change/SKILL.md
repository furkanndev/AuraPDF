---
name: aurapdf-safe-change
description: AuraPDF'te hata düzeltme, yeni özellik veya yeniden düzenleme yapılan her görevde kod değiştirmeden önce kullan. Önceki düzeltmeleri bozmamak için git geçmişini, korunan çözümleri, açık worktree'leri ve testleri kontrol ettirir.
---

# AuraPDF Güvenli Değişiklik

Amaç: Yeni bir sorunu çözerken önceki bir düzeltmeyi sessizce geri almamak.

## Koda dokunmadan önce

1. `AGENTS.md` dosyasının 9. bölümündeki Korunan Çözümler tablosunu oku.
2. Değiştireceğin kodun neden öyle yazıldığını öğren:

   ```bash
   git log --oneline -10 -- <dosya>
   git log -L <başlangıç>,<bitiş>:<dosya> -3
   ```

3. Değişikliğin başka bir çalışma ağacındaki işle çakışıp çakışmadığına bak:

   ```bash
   git worktree list
   git -C <worktree-yolu> status --short
   ```

   Aradığın özellik bu dalda yoksa önce diğer worktree'lerde ara. Yoksa baştan yazma.

4. Temel durumu al: `python -m unittest tests.test_static_guards tests.test_icon_sets`. Görev öncesi kırık bir test varsa kullanıcıya bildir.

## Değişiklik sırasında

- Yalnızca görevin gerektirdiği satırları değiştir. Toplu biçimlendirme, yeniden adlandırma veya "temizlik" yapma.
- Tuhaf görünen kodu silmeden önce geçmişini oku. Çoğu bir kenar durumu çözer.
- Mevcut bir koruma testi kırılıyorsa kodu düzelt. Testi gevşetme, silme veya atlama.
- Commit edilmemiş işi `git checkout`, `git restore`, `git reset --hard` veya `git clean` ile silme.
- Başka bir worktree'nin dosyalarını düzenleme.

## Bitirmeden önce

1. Testleri yeniden çalıştır ve sonucu olduğu gibi raporla.
2. Yeni bir hata düzelttiysen bu hatayı yakalayan bir test ekle ve `AGENTS.md` tablosuna satır ekle.
3. Arayüz değiştiyse `aurapdf-ui-verify` skill'ini uygula.
4. Doğrulayamadığın her şeyi kullanıcıya açıkça söyle.
