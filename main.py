import json
import os
import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ------------------------------
# Paths
# ------------------------------

DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
REPORTS_FILE = os.path.join(DATA_DIR, "reports.json")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")

# Ensure data folder exists
os.makedirs(DATA_DIR, exist_ok=True)

# ------------------------------
# Helper functions
# ------------------------------

def load_json(path, default):
    if not os.path.exists(path):
        save_json(path, default)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        save_json(path, default)
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

users = load_json(USERS_FILE, {})
reports = load_json(REPORTS_FILE, {})
tasks = load_json(TASKS_FILE, {})

def get_username(user_id):
    return users.get(str(user_id), "Unknown")

def ensure_user(user_id, name):
    user_id = str(user_id)
    if user_id not in users:
        users[user_id] = name
        save_json(USERS_FILE, users)

# ------------------------------
# Productivity Tips Generator
# ------------------------------

def generate_tip(user_id):
    uid = str(user_id)
    user_reports = reports.get(uid, [])
    user_tasks = tasks.get(uid, [])

    pending = [t for t in user_tasks if not t["done"]]
    repeated = {}
    idle_time = 0
    volume = len(user_reports)

    for r in user_reports[-5:]:  # last 5 reports
        txt = r["text"]
        for word in txt.split():
            repeated[word] = repeated.get(word, 0) + 1

    if len(pending) > 3:
        txt = "چند تا کار عقب‌افتاده داری، پیشنهاد می‌کنم فردا اول صبح همون‌ها رو جمع کنی 🌱"
    elif volume < 2:
        txt = "گزارش‌هات کم بود امروز؛ پیشنهاد می‌کنم چند کار کوچیک هم بنویسی تا جریان کارت منظم‌تر باشه ⚡️"
    else:
        txt = "کارها مرتب بود! فقط سعی کن وقفه‌های طولانی بین کارها رو کمتر کنی تا انرژی‌ت بهتر بمونه 💪"

    return txt

# ------------------------------
# Telegram Commands
# ------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    ensure_user(user.id, user.first_name)
    await update.message.reply_text(f"سلام {user.first_name}! گزارش روزانه‌ت رو بفرست 🌟")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    ensure_user(user.id, user.first_name)

    text = update.message.text.replace("/report ", "")
    uid = str(user.id)

    if uid not in reports:
        reports[uid] = []

    reports[uid].append({
        "text": text,
        "time": datetime.datetime.now().isoformat()
    })
    save_json(REPORTS_FILE, reports)

    await update.message.reply_text("گزارشت ذخیره شد ✔️")

async def show_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    target = update.message.text.replace("/show ", "").strip()

    # If asking for someone else
    name_to_find = target if target else user.first_name

    # Reverse lookup
    for uid, name in users.items():
        if name == name_to_find:
            selected = uid
            break
    else:
        await update.message.reply_text("کاربری با این نام پیدا نشد ❌")
        return

    user_reports = reports.get(selected, [])
    if not user_reports:
        await update.message.reply_text("هیچ گزارشی وجود ندارد.")
        return

    txt = "\n\n".join([f"- {r['text']}" for r in user_reports[-10:]])
    await update.message.reply_text(f"آخرین گزارش‌ها:\n\n{txt}")

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    ensure_user(user.id, user.first_name)

    text = update.message.text.replace("/task ", "")
    uid = str(user.id)

    if uid not in tasks:
        tasks[uid] = []

    tasks[uid].append({
        "title": text,
        "done": False,
        "time": datetime.datetime.now().isoformat()
    })
    save_json(TASKS_FILE, tasks)

    await update.message.reply_text("کار به لیست اضافه شد 📝")

async def daily_summary():
    # This sends automatic summaries at 00:00
    for uid, name in users.items():
        user_reports = reports.get(uid, [])
        user_tasks = tasks.get(uid, [])

        pending = [t for t in user_tasks if not t["done"]]
        tip = generate_tip(uid)

        text = f"خلاصه روزانه {name}:\n\n" \
               f"تعداد گزارش‌ها: {len(user_reports)}\n" \
               f"کارهای عقب‌افتاده: {len(pending)}\n\n" \
               f"پیشنهاد امروز:\n{tip}"

        try:
            await app.bot.send_message(chat_id=int(uid), text=text)
        except:
            pass

async def tip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    tip = generate_tip(user.id)
    await update.message.reply_text(tip)

# ------------------------------
# App / Scheduler
# ------------------------------

scheduler = BackgroundScheduler(timezone=pytz.timezone("Asia/Tehran"))
scheduler.add_job(daily_summary, "cron", hour=0, minute=0)
scheduler.start()

TOKEN = "PUT-YOUR-BOT-TOKEN-HERE"

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("report", report))
app.add_handler(CommandHandler("show", show_reports))
app.add_handler(CommandHandler("task", add_task))
app.add_handler(CommandHandler("tip", tip_command))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, report))

if __name__ == "__main__":
    print("Bot is running...")
    app.run_polling()
