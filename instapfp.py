# instapfp_bot.py
import os
import re
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# 🔑 Secrets
BOT_TOKEN = os.environ.get("BOT_TOKEN")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var is missing")
if not RAPIDAPI_KEY:
    raise RuntimeError("RAPIDAPI_KEY env var is missing")

# 🧾 Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("instapfp")

API_URL = "https://save-insta1.p.rapidapi.com/profile"
API_HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": "save-insta1.p.rapidapi.com",
    "Content-Type": "application/json",
}

def _sanitize_username(raw: str) -> str:
    # strip @, whitespace; Instagram usernames are [a-z0-9._] up to 30 chars
    u = raw.strip().lstrip("@")
    u = u[:30]
    if not re.fullmatch(r"[A-Za-z0-9._]+", u):
        # remove illegal chars silently
        u = re.sub(r"[^A-Za-z0-9._]", "", u)
    return u

def _extract_pic_urls(data: dict):
    """
    Try multiple known shapes:
    - {"result": {"user": {...}}}
    - {"result": [{"user": {...}}]}
    - {"result": {...}}
    - top-level fields
    Returns (hd_url or None, normal_url or None)
    """
    def _from_user(user: dict):
        hd = None
        normal = None
        if isinstance(user, dict):
            if isinstance(user.get("hd_profile_pic_url_info"), dict):
                hd = user["hd_profile_pic_url_info"].get("url")
            hd = hd or user.get("hd_profile_pic_url")
            normal = user.get("profile_pic_url") or user.get("profile_pic_url_hd")
        return hd, normal

    if not isinstance(data, dict):
        return None, None

    result = data.get("result")
    if isinstance(result, dict):
        if "user" in result and isinstance(result["user"], dict):
            return _from_user(result["user"])
        hd, normal = _from_user(result)
        if hd or normal:
            return hd, normal

    if isinstance(result, list) and result:
        first = result[0]
        if isinstance(first, dict):
            if "user" in first and isinstance(first["user"], dict):
                return _from_user(first["user"])
            hd, normal = _from_user(first)
            if hd or normal:
                return hd, normal

    if "user" in data and isinstance(data["user"], dict):
        return _from_user(data["user"])

    hd, normal = _from_user(data)
    return hd, normal

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
        "/pfp <username> — Fetch HD profile picture\n"
        "/start — Welcome message\n"
        "/help — Show this help",
        parse_mode="Markdown"
    )

# /pfp
async def pfp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide a username.\nExample: `/pfp cristiano`",
            parse_mode="Markdown"
        )
        return

    username = _sanitize_username(context.args[0])
    if not username:
        await update.message.reply_text("⚠️ Invalid username format.")
        return

    try:
        resp = requests.post(
            API_URL,
            json={"username": username},
            headers=API_HEADERS,
            timeout=20
        )
    except requests.RequestException as net_err:
        logger.exception("Network error")
        await update.message.reply_text(f"🌐 Network error: {net_err}")
        return

    raw_text = resp.text
    try:
        data = resp.json()
    except Exception:
        data = None

    logger.info("API status=%s body=%s", resp.status_code, raw_text)

    if resp.status_code != 200:
        msg = None
        if isinstance(data, dict):
            msg = data.get("message") or data.get("error") or data.get("detail")
        await update.message.reply_text(
            f"❌ API returned {resp.status_code}"
            + (f": {msg}" if msg else "")
        )
        return

    if not isinstance(data, dict):
        await update.message.reply_text("❌ Invalid JSON response from API.")
        return

    if any(k in data for k in ("error", "errors")) and not data.get("result"):
        await update.message.reply_text(f"❌ API error: {data.get('error') or data.get('errors')}")
        return

    hd_url, normal_url = _extract_pic_urls(data)

    if hd_url:
        await update.message.reply_photo(hd_url, caption=f"📸 HD Profile picture of @{username}")
        return
    if normal_url:
        await update.message.reply_photo(normal_url, caption=f"📸 Profile picture of @{username}")
        return

    snippet = raw_text[:300].replace("\n", " ")
    await update.message.reply_text(
        "❌ User not found or unexpected response shape.\n"
        f"Debug: {snippet}..."
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("pfp", pfp))
    app.run_polling()

if __name__ == "__main__":
    main()
