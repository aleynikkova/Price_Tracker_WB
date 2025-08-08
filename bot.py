from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests

TOKEN = '7837058200:AAEPoPqGCw6h1e_EOaY35pX843Krp2IMT_4'
BASE_URL = 'http://127.0.0.1:5000'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    username = update.effective_user.username

    # отправка chat_id и username
    response = requests.post(f"{BASE_URL}/save_chat_id", json={
        'telegram_username': username,
        'chat_id': chat_id
    })

    if response.ok:
        await update.message.reply_text("✅ Telegram успешно привязан к сайту!")
    else:
        await update.message.reply_text("❌ Не удалось привязать Telegram. Убедитесь, что вы указали правильный username при регистрации.")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

