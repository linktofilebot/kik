import os
import sys
import time
import threading

# --- অটোমেটিক লাইব্রেরি ইনস্টলার (বট রান করলেই লাইব্রেরি ইনস্টল হবে) ---
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

# ================== কনফিগারেশন (এখানে নিজের তথ্য দিন) ==================
BOT_TOKEN = "8017252349:AAE6ETJcBqiaVe5o9PfoXs3ED5JOsFY8oQk"  # @BotFather থেকে পাওয়া টোকেন
OWNER_ID = 7525127704              # আপনার টেলিগ্রাম আইডি (এখানে অবশ্যই সংখ্যা দিন)
MONGO_URL = "mongodb+srv://freelancermaruf1735:6XaThbuVG2zOUWm4@cluster0.ywwppvf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"    # আপনার মঙ্গোডিবি কানেকশন ইউআরএল
# ====================================================================

# --- MongoDB কানেকশন ---
client = pymongo.MongoClient(MONGO_URL)
db = client["member_kick_pro"]
chats_col = db["chats"]

# --- Uptime সিস্টেম (বট ২৪ ঘণ্টা সচল রাখার জন্য ওয়েব সার্ভার) ---
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

# --- টাইম কনভার্টার (10m, 1h, 1d কে সেকেন্ডে রূপান্তর) ---
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

# --- বটের কমান্ডসমূহ ---

# ১. স্টার্ট কমান্ড
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    await update.message.reply_text("বট অনলাইন আছে। আপনি এখন আপনার কমান্ডগুলো ব্যবহার করতে পারেন।")

# ২. আইডি অ্যাড করা (/add cnl -100xxx বা /add grp -100xxx)
async def add_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if len(context.args) < 2:
        await update.message.reply_text("সঠিক নিয়ম: `/add cnl -100xxx` বা `/add grp -100xxx`", parse_mode=ParseMode.MARKDOWN)
        return
    
    c_type = context.args[0].lower() # cnl বা grp
    c_id = context.args[1]

    if c_type not in ['cnl', 'grp']:
        await update.message.reply_text("টাইপ ভুল! শুধু cnl অথবা grp ব্যবহার করুন।")
        return

    if chats_col.find_one({"chat_id": c_id}):
        await update.message.reply_text("এই আইডিটি আগেই যোগ করা হয়েছে।")
    else:
        chats_col.insert_one({"chat_id": c_id, "type": c_type})
        await update.message.reply_text(f"✅ {c_type.upper()} আইডি `{c_id}` সফলভাবে সেভ হয়েছে।", parse_mode=ParseMode.MARKDOWN)

# ৩. আইডি ডিলিট করা (/del -100xxx)
async def del_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not context.args:
        await update.message.reply_text("সঠিক নিয়ম: `/del -100xxx`", parse_mode=ParseMode.MARKDOWN)
        return
    
    c_id = context.args[0]
    result = chats_col.delete_one({"chat_id": c_id})
    if result.deleted_count > 0:
        await update.message.reply_text(f"🗑 আইডি `{c_id}` ডাটাবেস থেকে মুছে ফেলা হয়েছে।", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ এই আইডিটি পাওয়া যায়নি।")

# ৪. লিস্ট দেখা (/list)
async def list_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    all_data = list(chats_col.find())
    cnls = [d['chat_id'] for d in all_data if d['type'] == 'cnl']
    grps = [d['chat_id'] for d in all_data if d['type'] == 'grp']
    
    msg = "📋 **ডাটাবেস ইনফো:**\n\n"
    msg += f"📢 **চ্যানেল ({len(cnls)}টি):**\n`{', '.join(cnls) if cnls else 'নেই'}`\n\n"
    msg += f"👥 **গ্রুপ ({len(grps)}টি):**\n`{', '.join(grps) if grps else 'নেই'}`"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

# ৫. চ্যানেল কিক কমান্ড (/cnlkik uid time)
async def channel_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if len(context.args) < 2:
        await update.message.reply_text("ব্যবহার: `/cnlkik <user_id> <time>`", parse_mode=ParseMode.MARKDOWN)
        return

    uid = int(context.args[0])
    duration = parse_time(context.args[1])
    until = int(time.time() + duration)
    
    # ইউজারকে ইনবক্সে মেসেজ ও ওনার লিঙ্ক পাঠানো
    try:
        owner_link = f"tg://user?id={OWNER_ID}"
        msg_to_user = (
            f"আপনার প্রিমিয়াম এর সময় শেষ, প্রিমিয়াম নিতে ওনারকে মেসেজ দিন। ধন্যবাদ।\n\n"
            f"👤 **ওনার:** [এখানে ক্লিক করুন]({owner_link})"
        )
        await context.bot.send_message(chat_id=uid, text=msg_to_user, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        print(f"মেসেজ পাঠানো যায়নি ইউজার {uid} কে: {e}")

    # সব চ্যানেল থেকে কিক/ব্যান করা
    channels = chats_col.find({"type": "cnl"})
    success, fail = 0, 0
    for c in channels:
        try:
            await context.bot.ban_chat_member(chat_id=c['chat_id'], user_id=uid, until_date=until)
            success += 1
        except: fail += 1
    
    await update.message.reply_text(f"📢 **চ্যানেল কিক রেজাল্ট:**\n✅ সফল: {success}\n❌ ব্যর্থ: {fail}")

# ৬. গ্রুপ কিক কমান্ড (/grpkik uid time)
async def group_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if len(context.args) < 2:
        await update.message.reply_text("ব্যবহার: `/grpkik <user_id> <time>`", parse_mode=ParseMode.MARKDOWN)
        return

    uid = int(context.args[0])
    duration = parse_time(context.args[1])
    until = int(time.time() + duration)

    # ইউজারকে ইনবক্সে মেসেজ ও ওনার লিঙ্ক পাঠানো
    try:
        owner_link = f"tg://user?id={OWNER_ID}"
        msg_to_user = (
            f"আপনার প্রিমিয়াম এর সময় শেষ, প্রিমিয়াম নিতে ওনারকে মেসেজ দিন। ধন্যবাদ।\n\n"
            f"👤 **ওনার:** [এখানে ক্লিক করুন]({owner_link})"
        )
        await context.bot.send_message(chat_id=uid, text=msg_to_user, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        print(f"মেসেজ পাঠানো যায়নি ইউজার {uid} কে: {e}")
    
    # সব গ্রুপ থেকে কিক/ব্যান করা
    groups = chats_col.find({"type": "grp"})
    success, fail = 0, 0
    for g in groups:
        try:
            await context.bot.ban_chat_member(chat_id=g['chat_id'], user_id=uid, until_date=until)
            success += 1
        except: fail += 1
    
    await update.message.reply_text(f"👥 **গ্রুপ কিক রেজাল্ট:**\n✅ সফল: {success}\n❌ ব্যর্থ: {fail}")

# --- মেইন রানার (বট শুরু করার ফাংশন) ---
if __name__ == '__main__':
    # আপটাইম সার্ভার চালু করা
    keep_alive()
    print("বট স্টার্ট হচ্ছে...")
    
    # অ্যাপ্লিকেশন সেটআপ
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # কমান্ড হ্যান্ডলার রেজিস্ট্রেশন
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_id))
    application.add_handler(CommandHandler("del", del_id))
    application.add_handler(CommandHandler("list", list_ids))
    application.add_handler(CommandHandler("cnlkik", channel_kick))
    application.add_handler(CommandHandler("grpkik", group_kick))

    # বট রান করা
    application.run_polling()
