import aiohttp
import asyncio
import nest_asyncio
import os
import json
import yt_dlp
import tempfile
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, filters, ContextTypes
)

nest_asyncio.apply()

# ✅ ЗАМЕНИ НА СВОИ ДЕЙСТВУЮЩИЕ КЛЮЧИ (НЕ ОСТАВЛЯЙ СТАРЫЕ)
TELEGRAM_TOKEN = "8274784522:AAGSUr02zVaqDmFJSmlNdCXvig5_TD-oTSs"
OPENROUTER_API_KEY = "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"

API_URL = 'https://openrouter.ai/api/v1/chat/completions'
MODEL = 'deepseek/deepseek-r1:free'
HISTORY_FILE = "history.json"

user_histories = {}

if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        user_histories = json.load(f)

def save_history():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(user_histories, f, ensure_ascii=False, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я SmartShaxx 🤖\nПиши мне что угодно, и я буду помнить наш диалог!")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id in user_histories:
        del user_histories[user_id]
        save_history()
        await update.message.reply_text("🧠 Память очищена! Начни заново.")
    else:
        await update.message.reply_text("У меня ещё нет истории с тобой.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_text = update.message.text

    if user_id not in user_histories:
        user_histories[user_id] = [
            {"role": "system", "content": "Ты умный, дружелюбный ИИ, говори по-русски, кратко и понятно."}
        ]

    user_histories[user_id].append({"role": "user", "content": user_text})

    if len(user_histories[user_id]) > 30:
        user_histories[user_id] = [user_histories[user_id][0]] + user_histories[user_id][-29:]

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": user_histories[user_id],
        "temperature": 0.7,
        "max_tokens": 500,
        "stream": False
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=data, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    answer = result['choices'][0]['message']['content']
                    user_histories[user_id].append({"role": "assistant", "content": answer})
                    save_history()
                    await update.message.reply_text(answer)
                else:
                    await update.message.reply_text(f"⚠️ Ошибка API: {resp.status}")
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка: {str(e)}")

# Команда /music — ищет и отправляет аудиофайл с YouTube
async def send_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Напиши название песни после команды, например:\n/music Imagine Dragons")
        return

    await update.message.reply_text(f"🎵 Ищу: {query}...")

    with tempfile.TemporaryDirectory() as tmpdir:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(tmpdir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=True)
                if not info or 'entries' not in info or len(info['entries']) == 0:
                    await update.message.reply_text("Не удалось найти музыку 😞")
                    return

                video = info['entries'][0]
                filename = ydl.prepare_filename(video)
                audio_file = os.path.splitext(filename)[0] + ".mp3"

                if os.path.exists(audio_file):
                    with open(audio_file, 'rb') as f:
                        await update.message.reply_audio(audio=f, title=video.get('title', 'Музыка'))
                else:
                    await update.message.reply_text("Ошибка при создании аудиофайла 😞")
        except Exception as e:
            await update.message.reply_text(f"Ошибка загрузки музыки: {str(e)}")

async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("music", send_music))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app.run_polling()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
