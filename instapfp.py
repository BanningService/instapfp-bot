import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# 🔑 Secrets
BOT_TOKEN = "7980643751:AAF5ROTeFclCLvE_U8ScBPfsg4EoYDpAGm0"
RAPIDAPI_KEY = "d5a06a28f9msha01cc5c23dfc50bp164a9ajsn6c4412ff8c45"

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to InstaPFP Bot!\n\n"
        "Use /pfp <username> to fetch the HD profile picture.\n\n"
        "Example: /pfp cristiano"
    )

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Commands:*\n\n"
        "/pfp <username> - Fetch HD profile picture\n"
        "/start - Welcome message\n"
        "/help - Show this help",
        parse_mode="Markdown"
    )

# /pfp
async def pfp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Please provide a username.\nExample: `/pfp cristiano`")
        return

    username = context.args[0]

    url = "https://save-insta1.p.rapidapi.com/profile"
    payload = f'{{"username":"{username}"}}'
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "save-insta1.p.rapidapi.com",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, data=payload, headers=headers)
        data = response.json()

        # Extract user data
        if "result" in data and len(data["result"]) > 0 and "user" in data["result"][0]:
            user = data["result"][0]["user"]

            # Prefer HD profile pic if available
            hd_pic = user.get("hd_profile_pic_url_info")
            normal_pic = user.get("profile_pic_url")

            if hd_pic and isinstance(hd_pic, dict) and "url" in hd_pic:
                await update.message.reply_photo(hd_pic["url"])
            elif normal_pic:
                await update.message.reply_photo(normal_pic)
            else:
                await update.message.reply_text("❌ Couldn't find profile picture in user data.")
        else:
            await update.message.reply_text("❌ User not found or invalid response.")

    except Exception as e:
        logging.error(e, exc_info=True)
        await update.message.reply_text(f"⚠️ Error: {e}")

# Run bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("pfp", pfp))
    app.run_polling()

if __name__ == "__main__":
    main()