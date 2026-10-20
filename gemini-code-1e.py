import asyncio
import logging
import os
import re
import tempfile
import time
from threading import Thread

import requests
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters,
)

from content import ai_enabled, build_content
from deck import THEMES, create_presentation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("werkzeug").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("bot")

# ------------------------------------------------------------------ Veb qism
web = Flask(__name__)


@web.get("/")
def health():
    return "PowerPoint bot is running", 200


def run_web():
    web.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))


def keepalive():
    """Bepul Render xizmati uxlab qolmasligi uchun vaqti-vaqti bilan ping yuboradi."""
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url or os.environ.get("KEEPALIVE", "1") == "0":
        return
    while True:
        time.sleep(600)
        try:
            requests.get(url, timeout=15)
        except Exception as e:
            log.warning("keepalive xato: %s", e)


# ---------------------------------------------------------------- Suhbat
NAME, SURNAME, SUBJECT, TOPIC, COUNT, THEME = range(6)
LIMIT = asyncio.Semaphore(int(os.environ.get("MAX_PARALLEL", "2")))


def clean_filename(s):
    return re.sub(r'[\\/:*?"<>|\n\r]', "", s).strip()[:70] or "Taqdimot"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Assalomu alaykum! 🎓\nMen PowerPoint taqdimot tayyorlovchi botman.\n"
        "Bekor qilish: /cancel\n\nIsmingizni kiriting:"
    )
    return NAME


async def _text_step(update, context, key, maxlen, next_prompt, next_state, current_state):
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("Iltimos, matn yuboring.")
        return current_state
    context.user_data[key] = text[:maxlen]
    await update.message.reply_text(next_prompt)
    return next_state


async def get_name(u, c):
    return await _text_step(u, c, "name", 60, "Familiyangizni kiriting:", SURNAME, NAME)


async def get_surname(u, c):
    return await _text_step(u, c, "surname", 60, "Qaysi fan uchun taqdimot kerak?", SUBJECT, SURNAME)


async def get_subject(u, c):
    return await _text_step(u, c, "subject", 100, "Taqdimot mavzusini yozing:", TOPIC, SUBJECT)


async def get_topic(u, c):
    return await _text_step(u, c, "topic", 180, "Nechta slayd kerak? 5 dan 20 gacha son kiriting:", COUNT, TOPIC)


async def get_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        count = int((update.message.text or "").strip())
        if not 5 <= count <= 20:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Iltimos, 5 dan 20 gacha butun son kiriting.")
        return COUNT
    context.user_data["count"] = count
    items = list(THEMES.items())
    keyboard = [
        [InlineKeyboardButton(f"{k}. {v[0]}", callback_data=f"theme:{k}") for k, v in items[i:i + 2]]
        for i in range(0, len(items), 2)
    ]
    await update.message.reply_text("Dizayn shablonini tanlang (12 ta):", reply_markup=InlineKeyboardMarkup(keyboard))
    return THEME


async def get_theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    theme_id = query.data.split(":", 1)[1]
    if theme_id not in THEMES or "topic" not in context.user_data:
        await query.edit_message_text("Ma'lumotlar topilmadi. /start orqali qaytadan boshlang.")
        return ConversationHandler.END
    context.user_data["theme"] = theme_id
    data = dict(context.user_data)
    chat_id = query.message.chat_id
    await query.edit_message_text(
        f"Tanlandi: {THEMES[theme_id][0]}\n"
        f"{'AI yordamida matn yozilmoqda' if ai_enabled() else 'Taqdimot tayyorlanmoqda'}. "
        "Bir oz kuting (30–60 soniya)..."
    )
    try:
        async with LIMIT:
            n_body = max(1, data["count"] - 3)
            content, used_ai = await asyncio.to_thread(build_content, data["topic"], data["subject"], n_body)
            with tempfile.TemporaryDirectory() as td:
                filename = clean_filename(data["topic"]) + ".pptx"
                path = os.path.join(td, filename)
                total, n_img = await asyncio.to_thread(create_presentation, data, content, path)
                caption = (
                    f"✅ Taqdimot tayyor ({total} slayd)\n"
                    f"Fan: {data['subject']}\nMavzu: {data['topic']}\n"
                    f"Shablon: {THEMES[theme_id][0]}\n\n"
                    + ("Matn AI yordamida yozilgan: faktlar va raqamlarni manbadan tekshiring. "
                       if used_ai else
                       "Matnlar namunaviy (AI ulanmagan yoki ishlamadi): o'zingiz tahrir qiling. ")
                    + (f"{n_img} ta rasm Wikimedia Commons'dan, muallif/litsenziya slayd ostida yozilgan."
                       if n_img else "")
                )
                with open(path, "rb") as f:
                    await context.bot.send_document(
                        chat_id=chat_id, document=f, filename=filename,
                        caption=caption[:1020], write_timeout=120, read_timeout=120,
                    )
    except Exception:
        log.exception("Taqdimot yaratishda xato")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Fayl yaratishda xatolik yuz berdi. Birozdan keyin /start orqali qayta urinib ko‘ring.",
        )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Bekor qilindi. Qayta boshlash uchun /start bosing.")
    return ConversationHandler.END


async def fallback_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Boshlash uchun /start yuboring.")


async def on_error(update, context: ContextTypes.DEFAULT_TYPE):
    log.error("Kutilmagan xato", exc_info=context.error)


def main():
    # Python 3.14 event loop xatoligini to'g'rilash (Render uchun)
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is missing.")
    Thread(target=run_web, daemon=True).start()
    Thread(target=keepalive, daemon=True).start()

    app = Application.builder().token(token).build()
    text = filters.TEXT & ~filters.COMMAND
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(text, get_name)],
            SURNAME: [MessageHandler(text, get_surname)],
            SUBJECT: [MessageHandler(text, get_subject)],
            TOPIC: [MessageHandler(text, get_topic)],
            COUNT: [MessageHandler(text, get_count)],
            THEME: [CallbackQueryHandler(get_theme, pattern=r"^theme:\d+$")],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
        allow_reentry=True,
        per_message=False,
    )
    app.add_handler(conv)
    app.add_handler(MessageHandler(text, fallback_text))
    app.add_error_handler(on_error)
    log.info("Bot starting... AI: %s", "yoqilgan" if ai_enabled() else "o'chiq (zaxira matn)")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()