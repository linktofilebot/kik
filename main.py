import os
import sys
import time
import threading
import asyncio

# --- অটোমেটিক লাইব্রেরি ইনস্টলার ---
def install_libraries():
    libs = ['python-telegram-bot', 'pymongo', 'dnspython', 'flask']
    for lib in libs:
        try:
            __import__(lib.replace('-', '_'))
        except ImportError:
            print(f"Installing {lib}...")
            os.system(f"{sys.executable} -m pip install {lib}")

install_libraries()

# --- লাইব্রেরি ইমপোর্ট ---
import pymongo
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.constants import ParseMode

# ================== কনফিগারেশন (আপনার তথ্য দিন) ==================
BOT_TOKEN = "8017252349:AAE6ETJcBqiaVe5o9PfoXs3ED5JOsFY8oQk"
OWNER_ID = 7525127704
MONGO_URL = "mongodb+srv://freelancermaruf1735:6XaThbuVG2zOUWm4@cluster0.ywwppvf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
# =============================================================

# --- MongoDB কানেকশন ---
client = pymongo.MongoClient(MONGO_URL)
db = client["member_kick_pro"]
chats_col = db["chats"]

# --- Uptime সিস্টেম (ওয়েব সার্ভার) ---
flask_app = Flask('')
@flask_app.route('/')
def home():
    return "Bot is running 24/7!"

def run_web_server():
    flask_app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run_web_server)
    t.daemon = True
    t.start()

# --- টাইম কনভার্টার (10s, 1m, 1h, 1d) ---
def parse_time(time_str):
    try:
        unit = time_str[-1].lower()
        value = int(time_str[:-1])
        if unit == 's': return value
        if unit == 'm': return value * 60
        if unit == 'h': return value * 3600
        if unit == 'd': return value * 86400
        return value
    except:
        return 0

# --- কিক করার মূল টাস্ক (টাইমার শেষ হলে এটি চলবে) ---
async def execute_kick_task(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    uid = job.data['uid']
    chat_type = job.data['type']
    owner_id = job.data['owner_id']
    msg_status = "❌ মেসেজ পাঠানো যায়নি (ইউজার বট স্টার্ট করেনি)"

    # ১. ইউজারকে ইনবক্সে মেসেজ পাঠানোর চেষ্টা করা
    try:
        owner_link = f"tg://user?id={OWNER_ID}"
        msg_to_user = (
            f"⚠️ **আপনার প্রিমিয়াম মেয়াদ শেষ!**\n\n"
            f"আপনার সময়সীমা অতিক্রম হয়েছে। পুনরায় প্রিমিয়াম নিতে ওনারকে মেসেজ দিন। ধন্যবাদ।\n\n"
            f"👤 **ওনার:** [এখানে ক্লিক করুন]({owner_link})"
        )
        await context.bot.send_message(chat_id=uid, text=msg_to_user, parse_mode=ParseMode.MARKDOWN)
        msg_status = "✅ মেসেজ ইনবক্সে পাঠানো হয়েছে"
    except Exception as e:
        print(f"User {uid} message failed: {e}")

    # ২. ডাটাবেস থেকে সংশ্লিষ্ট সব চ্যাট আইডি নিয়ে কিক করা
    chats = list(chats_col.find({"type": chat_type}))
    success, fail = 0, 0
    
    for c in chats:
        try:
            # ব্যান করা
            await context.bot.ban_chat_member(chat_id=c['chat_id'], user_id=uid)
            # সাথে সাথে আনব্যান করা (যাতে শুধু কিক হিসেবে গণ্য হয় এবং ভবিষ্যতে জয়েন করতে পারে)
            await context.bot.unban_chat_member(chat_id=c['chat_id'], user_id=uid)
            success += 1
        except Exception as e:
            print(f"Kick failed for {c['chat_id']}: {e}")
            fail += 1
    
    # ৩. ওনারকে কিক রিপোর্ট পাঠানো
    type_label = "চ্যানেল" if chat_type == "cnl" else "গ্রুপ"
    report = (
        f"🏁 **টাস্ক সম্পন্ন হয়েছে!**\n\n"
        f"👤 ইউজার আইডি: `{uid}`\n"
        f"📂 টাইপ: {type_label}\n"
        f"✉️ নোটিফিকেশন: {msg_status}\n"
        f"✅ সফল রিমুভ: {success}\n"
        f"❌ ব্যর্থ: {fail}"
    )
    await context.bot.send_message(chat_id=owner_id, text=report, parse_mode=ParseMode.MARKDOWN)

# --- বটের কমান্ড হ্যান্ডলার ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == OWNER_ID:
        await update.message.reply_text("বট অনলাইন! আপনি অ্যাডমিন হিসেবে এটি নিয়ন্ত্রণ করতে পারবেন।")
    else:
        await update.message.reply_text("স্বাগতম! নোটিফিকেশন পেতে বটটি স্টার্ট করে রাখুন।")

async def add_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if len(context.args) < 2:
        await update.message.reply_text("সঠিক নিয়ম: `/add cnl ID` অথবা `/add grp ID`")
        return
    c_type, c_id = context.args[0].lower(), context.args[1]
    if c_type not in ['cnl', 'grp']:
        await update.message.reply_text("টাইপ শুধু cnl অথবা grp হবে।")
        return
    chats_col.update_one({"chat_id": c_id}, {"$set": {"type": c_type}}, upsert=True)
    await update.message.reply_text(f"✅ সফলভাবে {c_type.upper()} আইডি `{c_id}` সেভ করা হয়েছে।")

async def list_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    all_data = list(chats_col.find())
    if not all_data:
        await update.message.reply_text("ডাটাবেস খালি।")
        return
    msg = "📋 **সংরক্ষিত লিস্ট:**\n"
    for d in all_data:
        msg += f"• `{d['chat_id']}` ({d['type'].upper()})\n"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def del_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not context.args: return
    c_id = context.args[0]
    chats_col.delete_one({"chat_id": c_id})
    await update.message.reply_text(f"🗑 আইডি `{c_id}` মুছে ফেলা হয়েছে।")

# কিক কমান্ড (চ্যানেল)
async def channel_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if len(context.args) < 2:
        await update.message.reply_text("ব্যবহার: `/cnlkik <ID> <সময়>`\nউদাহরণ: `/cnlkik 123456 1m`")
        return
    
    uid = int(context.args[0])
    time_str = context.args[1]
    delay = parse_time(time_str)

    if delay <= 0:
        await update.message.reply_text("ভুল সময়! উদাহরণ: 1m, 1h, 1d")
        return

    # টাইমার জব তৈরি করা
    context.job_queue.run_once(
        execute_kick_task,
        delay,
        data={'uid': uid, 'type': 'cnl', 'owner_id': update.effective_chat.id},
        name=f"cnl_{uid}"
    )
    await update.message.reply_text(f"⏳ টাইমার সেট! ঠিক {time_str} পর ইউজার `{uid}` কে সব চ্যানেল থেকে কিক করা হবে।")

# কিক কমান্ড (গ্রুপ)
async def group_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if len(context.args) < 2:
        await update.message.reply_text("ব্যবহার: `/grpkik <ID> <সময়>`\nউদাহরণ: `/grpkik 123456 1m`")
        return
    
    uid = int(context.args[0])
    time_str = context.args[1]
    delay = parse_time(time_str)

    if delay <= 0:
        await update.message.reply_text("ভুল সময়!")
        return

    # টাইমার জব তৈরি করা
    context.job_queue.run_once(
        execute_kick_task,
        delay,
        data={'uid': uid, 'type': 'grp', 'owner_id': update.effective_chat.id},
        name=f"grp_{uid}"
    )
    await update.message.reply_text(f"⏳ টাইমার সেট! ঠিক {time_str} পর ইউজার `{uid}` কে সব গ্রুপ থেকে কিক করা হবে।")

# --- মেইন রানার ---
if __name__ == '__main__':
    keep_alive() # ওয়েব সার্ভার স্টার্ট
    print("বট সচল হচ্ছে...")
    
    # অ্যাপ্লিকেশন বিল্ড করা
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # কমান্ডগুলো যুক্ত করা
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_id))
    application.add_handler(CommandHandler("list", list_ids))
    application.add_handler(CommandHandler("del", del_id))
    application.add_handler(CommandHandler("cnlkik", channel_kick))
    application.add_handler(CommandHandler("grpkik", group_kick))

    # পোলিং শুরু
    application.run_polling()
