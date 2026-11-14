---
name: insta-reader
description: >-
  قراية وتحميل من إنستجرام بـ instaloader (MIT): بيانات حساب (متابعين، بايو، عدد بوستات)، آخر البوستات بلايكاتها وكومنتاتها ومشاهداتها وكابشنها، أعلى البوستات أداءً لدراسة الترند، تحميل بوست أو ريل أو ألبوم كامل بالكابشن، وتحميل بوستات حساب. الفيديو من أي موقع تاني بـ video-grabber (yt-dlp). Use when the user wants to see, read, analyse or download from Instagram: شوف الانستجرام، حمّل الريل ده، بوستات الحساب ده، أعلى ريلز، الكابشن، المتابعين، instagram profile, reels, download post.
---

# insta-reader — إنستجرام

```bash
R="python -X utf8 scripts/rd.py"
$R insta doctor                         # instaloader وyt-dlp متثبتين؟
$R insta profile khaledragab_official --posts 12
$R insta top majed_alzaabi_ --posts 50 --by views --n 10   # أعلى الريلز (للترند)
$R insta post https://www.instagram.com/reel/XXXX/ --out D:\insta\reel1   # الميديا + caption.txt + meta.json
$R insta download USER --out D:\insta\USER --max 12 [--reels-only] [--since 2026-10-01]
$R insta login MY_ACCOUNT               # على جهازك بس، للخاص والستوريز (--session MY_ACCOUNT)
```

- **التثبيت:** `pip install instaloader` (وyt-dlp موجود في video-grabber).
- **الحدود:** الحسابات العامة من غير دخول. إنستجرام بيحظر الطلبات الكتير: الافتراضي 12 بوست، و1.5 ث بين كل طلب. ماتجمعش بيانات ناس بالجملة.
- **الأمان:** الباسورد بيتكتب في instaloader نفسه، والتنين مابيشوفهوش ولا بيحفظه. السيشن في مجلد instaloader على الجهاز، وممنوع ترفعها في أي مكان.
- **ده شغل روتيني:** في الخطة بيتعلّم 🤖، فممكن يتعمل بالعامل الرخيص `rd-runner` (Haiku).
- على السحابة غالبًا إنستجرام بيحظر. جرّب على اللابتوب.
- `selftest`: 11 فحص من غير نت.
