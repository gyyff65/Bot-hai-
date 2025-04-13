import asyncio
import requests
import json
import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Bot config
BOT_TOKEN = '7816501933:AAHDFDFRqRhxXD92Doc7BdeRMZ44PTH9oSE'
API_URL = "https://gmg-id-like.vercel.app/like"
USAGE_FILE = "like_usage.json"
GROUP_STATUS_FILE = "group_status.json"
USER_DAILY_LIMIT = 2
DEFAULT_DAILY_LIMIT = 50
UNLIMITED_USER_ID = '7943593819'

# --- Helper Functions ---

def load_usage():
    today = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(USAGE_FILE):
        try:
            with open(USAGE_FILE, "r") as f:
                data = json.load(f)
                if data.get("date") == today:
                    return data
        except json.JSONDecodeError:
            pass
    return {"date": today, "total_count": 0, "users": {}}

def save_usage(data):
    with open(USAGE_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_group_status():
    if os.path.exists(GROUP_STATUS_FILE):
        try:
            with open(GROUP_STATUS_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {}

def save_group_status(data):
    with open(GROUP_STATUS_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def is_group_active(chat_id):
    status = load_group_status()
    group = status.get(str(chat_id))
    if not group or not group.get("active"):
        return False
    expiry = group.get("expires")
    if expiry:
        return datetime.now() <= datetime.strptime(expiry, "%Y-%m-%d")
    return True

def get_group_limit(chat_id):
    status = load_group_status()
    return status.get(str(chat_id), {}).get("limit", DEFAULT_DAILY_LIMIT)

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not is_group_active(chat_id):
        return
    await update.message.reply_text(
        f"👋 Welcome! Use /like <uid> to send likes. (Each user: {USER_DAILY_LIMIT}/day, Group Limit Varies)"
    )

async def like(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not is_group_active(chat_id):
        return

    usage = load_usage()
    user_id = str(update.message.from_user.id)
    group_limit = get_group_limit(chat_id)

    if usage["total_count"] >= group_limit:
        await update.message.reply_text("❌ Daily group limit reached. Try again tomorrow!")
        return

    if user_id != UNLIMITED_USER_ID:
        user_count = usage["users"].get(user_id, 0)
        if user_count >= USER_DAILY_LIMIT:
            await update.message.reply_text(f"❌ You used your {USER_DAILY_LIMIT} likes for today.")
            return

    if len(context.args) != 1:
        await update.message.reply_text("❗ Usage: /like <uid>")
        return

    uid = context.args[0]
    server = "ind"
    temp_msg = await update.message.reply_text(f"⏳ Sending likes to UID: {uid}...")
    await asyncio.sleep(10)

    try:
        response = requests.get(API_URL, params={"uid": uid, "server_name": server})
        if response.status_code == 200:
            data = response.json()
            nickname = data.get("PlayerNickname", "Unknown Player")
            before_likes = data.get("LikesbeforeCommand", data.get("Likes", "0"))
            after_likes = data.get("LikesafterCommand", data.get("Likes", "0"))

            try:
                likes_given = int(after_likes) - int(before_likes)
            except ValueError:
                likes_given = 0

            usage["total_count"] += 1
            if user_id != UNLIMITED_USER_ID:
                usage["users"][user_id] = usage["users"].get(user_id, 0) + 1
            save_usage(usage)

            remaining_group = group_limit - usage["total_count"]
            user_remaining = (
                "GMG" if user_id == UNLIMITED_USER_ID else USER_DAILY_LIMIT - usage["users"].get(user_id, 0)
            )

            await temp_msg.edit_text(
                f"""*✅ Like Sent Successfully\\!*
*├─ Player Name:* `{nickname}`
*├─ Before Likes:* `{before_likes}`
*├─ After Likes:* `{after_likes}`
*├─ Likes Given:* `{likes_given}`
*├─ Your Remaining:* `{user_remaining}`
*└─ Remaining Group Likes Today:* `{remaining_group}`

*BOT BY GRANDMIXTURE GAMER*""",
                parse_mode="MarkdownV2"
            )
        else:
            await temp_msg.edit_text("❌ Failed to send likes. Server error.")
    except Exception as e:
        print(f"[ERROR] like command failed: {e}")
        await temp_msg.edit_text("❌ An error occurred while sending likes.")

async def remain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not is_group_active(chat_id):
        return

    usage = load_usage()
    user_id = str(update.message.from_user.id)
    group_limit = get_group_limit(chat_id)

    group_remaining = group_limit - usage.get("total_count", 0)
    user_remaining = "GMG" if user_id == UNLIMITED_USER_ID else USER_DAILY_LIMIT - usage["users"].get(user_id, 0)

    await update.message.reply_text(
        f"📊 *Your LIMIT Likes:* {user_remaining}/{USER_DAILY_LIMIT}\n"
        f"👥 *Group Limit Likes:* {group_remaining}/{group_limit}",
        parse_mode="Markdown"
    )

async def boton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    chat_id = str(update.effective_chat.id)
    if user_id != UNLIMITED_USER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    status = load_group_status()
    if str(chat_id) not in status:
        status[str(chat_id)] = {
            "active": True,
            "limit": DEFAULT_DAILY_LIMIT,
            "expires": "2099-12-31"
        }
    else:
        status[str(chat_id)]["active"] = True
    save_group_status(status)
    await update.message.reply_text("✅ Bot is now ON for this group.")

async def botoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    chat_id = str(update.effective_chat.id)
    if user_id != UNLIMITED_USER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    status = load_group_status()
    if str(chat_id) in status:
        status[str(chat_id)]["active"] = False
        save_group_status(status)
        await update.message.reply_text("❌ Bot is now OFF for this group.")
    else:
        await update.message.reply_text("⚠️ Group not found in status file.")

async def allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id != UNLIMITED_USER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if len(context.args) != 3:
        await update.message.reply_text("❗ Usage: /allow <chat_id> <limit> <days>")
        return

    chat_id, limit_str, days_str = context.args

    try:
        limit = int(limit_str)
        days = int(days_str.lower().replace("days", ""))
    except ValueError:
        await update.message.reply_text("❌ Invalid limit or days format.")
        return

    expiry_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    status = load_group_status()
    status[chat_id] = {
        "active": True,
        "limit": limit,
        "expires": expiry_date
    }
    save_group_status(status)
    await update.message.reply_text(f"✅ Allowed group {chat_id} with {limit} likes/day until {expiry_date}.")

async def unallow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id != UNLIMITED_USER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("❗ Usage: /unallow <chat_id>")
        return

    chat_id = context.args[0]
    status = load_group_status()

    if chat_id in status:
        del status[chat_id]
        save_group_status(status)
        await update.message.reply_text(f"❌ Group {chat_id} is now unallowed and removed from access.")
    else:
        await update.message.reply_text(f"⚠️ Group {chat_id} not found in allowed list.")

# --- New Command: /removeremain ---
async def removeremain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    if user_id != UNLIMITED_USER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("❗ Usage: /removeremain <group_id> <count>")
        return

    group_id = context.args[0]
    try:
        count = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Invalid number provided.")
        return

    status = load_group_status()

    if group_id not in status:
        await update.message.reply_text(f"⚠️ Group {group_id} not found.")
        return

    # Reduce the total count for the group
    group_data = status[group_id]
    group_data["limit"] -= count
    if group_data["limit"] < 0:
        group_data["limit"] = 0
    status[group_id] = group_data
    save_group_status(status)

    await update.message.reply_text(
        f"✅ Removed {count} from the group {group_id}'s remaining limit.\n"
        f"🧮 New Group Limit: {group_data['limit']}"
    )

# --- Main Bot Run ---

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("like", like))
    app.add_handler(CommandHandler("remain", remain))
    app.add_handler(CommandHandler("boton", boton))
    app.add_handler(CommandHandler("botoff", botoff))
    app.add_handler(CommandHandler("allow", allow))
    app.add_handler(CommandHandler("unallow", unallow))
    app.add_handler(CommandHandler("removeremain", removeremain))  # New Command
    print("Bot is running...")
    app.run_polling()
