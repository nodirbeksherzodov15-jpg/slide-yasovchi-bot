# PowerPoint Telegram bot (v2) — Android orqali sozlash

## Nimalarni qiladi?
- Telegramda ism, familiya, fan, mavzu, slayd soni (5–20) va dizaynni (12 ta) so'raydi.
- `.pptx` fayl yaratib, chatga yuboradi.
- **Matn:** `GEMINI_API_KEY` berilsa — AI yozadi (o'zbekcha, har slaydga 3–4 band + taqdimotchi izohi). Berilmasa yoki AI xato bersa — namunaviy zaxira matn.
- **Rasm:** Wikimedia Commons'dan (faqat CC BY / CC0 / Public domain), muallif va litsenziya rasm ostida yoziladi. Rasm so'rovi AI rejimida inglizcha, shuning uchun mosligi yaxshiroq.
- Slaydlar orasida haqiqiy *fade* o'tish effekti bor.

## Muhim cheklovlar
- AI matni xato yoki o'ylab topilgan ma'lumot bo'lishi mumkin. Raqam, sana va faktlarni manbadan tekshiring.
- Zaxira matn umumiy; to'liq tadqiqot emas.
- Slayd ichidagi obyektlar uchun (kirish) animatsiyalar yo'q; faqat slaydlar orasidagi o'tish effekti bor.
- Bepul hosting uxlab qolishi yoki limitga yetishi mumkin; 24/7 kafolati yo'q. Bot o'zini har 10 daqiqada "uyg'otib" turadi (`KEEPALIVE=0` bilan o'chiriladi), bu bepul soat limitini sarflaydi.
- Wikimedia'da mos rasm topilmasa, slayd rasmsiz chiqadi.

## 1-qadam: Telegram bot
1. Telegramda `@BotFather` → `/newbot`.
2. Nom va username tanlang, tokenni nusxalang. Tokenni hech kimga bermang.

## 2-qadam (ixtiyoriy): AI kaliti
1. Google AI Studio'da (aistudio.google.com) API key oling. Bepul limit bo'lishi mumkin, shartlarini o'zingiz tekshiring.
2. Kalitni faqat Render'ning Environment bo'limiga kiriting, kodga yozmang.

## 3-qadam: GitHub
1. ZIP'ni telefonda oching (fayllar menejeri).
2. github.com → `+` → `New repository` → `powerpoint-telegram-bot`.
3. `Add file` → `Upload files` va **barcha fayllarni** yuklang: `bot.py`, `content.py`, `deck.py`, `images.py`, `requirements.txt`, `render.yaml`, `.gitignore`, `.env.example`. Hammasi kerak, aks holda bot ishga tushmaydi.
4. `Commit changes`.

## 4-qadam: Render
1. render.com → GitHub bilan ulang → `New` → `Blueprint` (render.yaml avtomatik o'qiladi) yoki `Web Service`.
2. Environment Variables: `BOT_TOKEN` (majburiy), `GEMINI_API_KEY` (ixtiyoriy).
3. Web Service tanlasangiz: Build `pip install -r requirements.txt`, Start `python bot.py`, Plan `Free`.
4. Logs'da `Bot starting... AI: yoqilgan` (yoki `o'chiq`) chiqishini kuting, so'ng botga `/start` yuboring.

## Xatolarni tekshirish
- `BOT_TOKEN environment variable is missing` → Render Environment'ga `BOT_TOKEN` qo'shing.
- `Conflict: terminated by other getUpdates request` → bot boshqa joyda ham ishlayapti; eskisini to'xtating.
- `ModuleNotFoundError: content/deck/images` → o'sha fayl GitHub'ga yuklanmagan.
- Matn namunaviy chiqyapti → `GEMINI_API_KEY` yo'q, noto'g'ri yoki limit tugagan (Logs'da sababi yoziladi). Model nomi eskirgan bo'lsa, `GEMINI_MODEL` ni yangilang.
- Bot javob bermayapti → Render Logs va deploy holatini ko'ring; bepul xizmat uxlab qolgan bo'lishi mumkin.

## Keyingi bosqichlar
1. Diagramma/jadval slaydlari (faqat haqiqiy ma'lumot bilan).
2. Har shablon uchun alohida kompozitsiya.
3. Obyektlar uchun haqiqiy kirish animatsiyalari (OOXML) va PowerPoint'da tekshirish.
