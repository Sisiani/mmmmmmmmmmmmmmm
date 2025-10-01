# bot.py
import logging
import os
import json
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ============== CONFIG ==============
TOKEN = os.environ.get("TOKEN", "8311865694:AAHrQDLSJcFKOztBj8X2PtMafk7U7AML0Uo")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "191196976"))  # آیدی عددی ادمین
GROUP_ID = int(os.environ.get("GROUP_ID", "-1003015735672"))
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "https://t.me/+oiQXD3OP35YzMDQ0")

EXCHANGE_LINKS = {
    "XT": "https://www.xtfarsi.net/en/accounts/register?ref=1133",
    "TOOBIT": "https://www.toobit.com/t/lpOdP4",
    "OURBIT": "https://www.ourbit.com/register?inviteCode=S3ZCNR",
    "BITUNIX": "https://www.bitunix.com/register?vipCode=hajamin",
}

USERS_FILE = "users.json"

# ============== LABELS ==============
BTN_JOIN_ACADEMY = "⚡️ عضویت در Neuran academy 💰"
BTN_SUBS = "💳 دریافت اشتراک"
BTN_BONUS = "🚀 دریافت بونس ویژه"
BTN_PROFILE = "📊 مشخصات حساب"
BTN_SUPPORT = "🛠 پشتیبانی"

BTN_HAVE_ACCOUNT = "از قبل حساب دارم"
BTN_NEED_ACCOUNT = "حساب ندارم ساخت حساب"

# ============== LOGGER ==============
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ============== storage helpers ==============
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_or_update_user(user_id, username=None, exchange=None, uid=None, approved=None):
    users = load_users()
    key = str(user_id)
    entry = users.get(key, {})
    if username is not None:
        entry["username"] = username
    if exchange is not None:
        entry["exchange"] = exchange
    if uid is not None:
        entry["uid"] = uid
    if approved is not None:
        entry["approved"] = approved
    users[key] = entry
    save_users(users)

# ============== Handlers ==============
def build_main_keyboard():
    keyboard = [
        [KeyboardButton(BTN_JOIN_ACADEMY)],
        [KeyboardButton(BTN_SUBS), KeyboardButton(BTN_BONUS)],
        [KeyboardButton(BTN_PROFILE), KeyboardButton(BTN_SUPPORT)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_or_update_user(user.id, username=user.username or "")
    reply_markup = build_main_keyboard()
    await update.message.reply_text("به ربات Neuran Academy خوش آمدید 🚀\nلطفا یکی از گزینه‌ها را انتخاب کنید:", reply_markup=reply_markup)

    # اگر ادمین است، یک دکمهٔ ادمینی (Inline) نمایش بده
    if user.id == ADMIN_ID:
        admin_kb = InlineKeyboardMarkup([[InlineKeyboardButton("📣 ارسال پیام همگانی", callback_data="admin_broadcast")]])
        await update.message.reply_text("منوی ادمین:", reply_markup=admin_kb)

# وقتی کاربر متنی می‌فرستد
async def message_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return
    text = update.message.text.strip()
    user = update.effective_user
    tg_id = user.id

    # اگر ادمین در حالت ارسال همگانی است
    if user.id == ADMIN_ID and context.user_data.get("waiting_broadcast"):
        broadcast_text = text
        users = load_users()
        sent = 0
        for target_id in list(users.keys()):
            try:
                await context.bot.send_message(int(target_id), broadcast_text)
                sent += 1
            except Exception:
                pass
        context.user_data["waiting_broadcast"] = False
        await update.message.reply_text(f"پیام برای {sent} کاربر ارسال شد ✅")
        return

    # اگر در حالت انتظار UID هستیم
    if context.user_data.get("waiting_for_uid"):
        exchange = context.user_data.get("exchange", "صرافی")
        entered_uid = text
        add_or_update_user(tg_id, username=user.username or "", exchange=exchange, uid=entered_uid, approved=False)

        group_msg = (
            f"درخواست عضویت جدید 🔔\n"
            f"صرافی: {exchange}\n"
            f"UID: {entered_uid}\n"
            f"یوزر: @{user.username if user.username else 'ندارد'}\n"
            f"تله آیدی: {tg_id}"
        )
        # دکمهٔ تایید برای گروه (callback شامل آیدی تلگرام هدف)
        try:
            approve_kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ تایید کاربر", callback_data=f"approve:{tg_id}")]])
            await context.bot.send_message(GROUP_ID, group_msg, reply_markup=approve_kb)
            await update.message.reply_text("UID شما برای بررسی به ادمین ارسال شد. منتظر تایید بمانید.")
        except Exception as e:
            await update.message.reply_text("خطا در ارسال به گروه بررسی. لطفا مطمئن شوید ربات عضو گروه است و GROUP_ID درست است.")
            logger.exception(e)

        context.user_data["waiting_for_uid"] = False
        return

    # منوی اصلی -- دکمه‌ها
    if text == BTN_SUBS:
        # نمایش گزینه‌های صرافی به صورت inline (callback برای انتخاب صرافی)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(name, callback_data=f"exchange:{name}")] for name in EXCHANGE_LINKS.keys()])
        await update.message.reply_text("لطفا یکی از صرافی‌ها را انتخاب کنید:", reply_markup=kb)
        return

    if text == BTN_SUPPORT:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("مراجعه به پشتیبانی", url="https://t.me/e11_S33")]])
        await update.message.reply_text("برای پشتیبانی روی دکمه زیر بزنید:", reply_markup=kb)
        return

    if text == BTN_BONUS:
        # متن دقیقِ ارسالی شما
        bonus_text = (
            "🧑‍💻👩‍💻 برای ورود به کانال  VIP NEURANAcademy\n\n"
            "🔹ابتدا حسابتونو با یکی از لینک های زیر در صرافی انتخابیتون بسازید \n\n"
            "🤑سپس حسابتونو حداقل 100 دلار شارژ کنید و در مرحله بعد UID تونو بفرستید\n\n"
            "❗️نکته : برای ورود به کانال ViP اگر در یکی از این صرافی ها از قبل اکانت دارید ، باید با لینکی که گذاشتیم اکانت جدید بسازید"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(name, url=link)] for name, link in EXCHANGE_LINKS.items()])
        await update.message.reply_text(bonus_text, reply_markup=kb)
        return

    if text == BTN_JOIN_ACADEMY:
        users = load_users()
        entry = users.get(str(tg_id), {})
        if entry.get("approved"):
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("پیوستن به کانال VIP", url=CHANNEL_LINK)]])
            await update.message.reply_text("تبریک! شما تایید شده‌اید — برای ورود روی دکمه زیر بزنید:", reply_markup=kb)
        else:
            # متن دقیقا طبق خواستهٔ شما
            await update.message.reply_text("شما هنوز واحد شرایط نیستید لطفاً ابتدا اشتراک تهیه کنید")
        return

    if text == BTN_PROFILE:
        users = load_users()
        entry = users.get(str(tg_id))
        if not entry:
            await update.message.reply_text("اطلاعاتی برای شما ثبت نشده است. لطفاً ابتدا دریافت اشتراک را انجام دهید.")
            return
        exchange = entry.get("exchange", "-")
        user_uid = entry.get("uid", "-")
        approved = entry.get("approved", False)
        approved_text = "تایید شده ✅" if approved else "تایید نشده ❌\nشما باید اول اشتراک تهیه کنید."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("پشتیبانی", url="https://t.me/e11_S33")]])
        await update.message.reply_text(f"📊 مشخصات حساب شما:\nصرافی: {exchange}\nUID: {user_uid}\nوضعیت: {approved_text}", reply_markup=kb)
        return

    # گزینه‌های بعد از انتخاب صرافی (Reply keyboard)
    if text == BTN_HAVE_ACCOUNT:
        exchange = context.user_data.get("exchange", "صرافی")
        context.user_data["waiting_for_uid"] = True
        await update.message.reply_text(f"لطفا UID صرافی ({exchange}) خود را وارد کنید تا ادمین تایید کند و عضویت در کانال VIP برای شما آزاد شود.")
        return

    if text == BTN_NEED_ACCOUNT:
        # نمایش لینک‌های صرافی (باز کردن لینک)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(name, url=link)] for name, link in EXCHANGE_LINKS.items()])
        await update.message.reply_text("برای ساخت حساب یکی از لینک‌های زیر را باز کنید:", reply_markup=kb)
        return

    # fallback
    await update.message.reply_text("متوجه نشدم. لطفاً از منوی اصلی یکی از گزینه‌ها را انتخاب کنید یا /start را بزنید.")

# ============== CallbackQuery handler ==============
async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None or query.data is None:
        return
    await query.answer()
    data = query.data

    # انتخاب صرافی
    if data.startswith("exchange:"):
        exchange = data.split(":", 1)[1]
        context.user_data["exchange"] = exchange
        try:
            await query.edit_message_text(f"صرافی انتخاب شده: {exchange}")
        except Exception:
            pass
        # حالا دو دکمهٔ اصلی به صورت ReplyKeyboard برای کاربر نشان داده شوند
        keyboard = [
            [KeyboardButton(BTN_HAVE_ACCOUNT), KeyboardButton(BTN_NEED_ACCOUNT)]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await query.message.reply_text("آیا از قبل در این صرافی حساب دارید یا خیر؟", reply_markup=reply_markup)
        return

    # ادمین درخواست ارسال پیام همگانی
    if data == "admin_broadcast":
        if query.from_user.id != ADMIN_ID:
            await query.answer("شما دسترسی لازم را ندارید.", show_alert=True)
            return
        context.user_data["waiting_broadcast"] = True
        await query.message.reply_text("لطفا متن پیام همگانی را ارسال کنید. (متن را در همین چت ارسال کنید)")
        return

    # دکمهٔ تایید در گروه (callback_data = approve:<telegram_id>)
    if data.startswith("approve:"):
        # فقط ادمین می‌تواند این را اجرا کند
        if query.from_user.id != ADMIN_ID:
            await query.answer("شما دسترسی لازم را ندارید.", show_alert=True)
            return
        parts = data.split(":", 1)
        if len(parts) != 2:
            await query.answer("اطلاعات نامعتبر")
            return
        try:
            target_id = int(parts[1])
        except ValueError:
            await query.answer("آی‌دی نامعتبر")
            return
        # set approved
        add_or_update_user(target_id, approved=True)
        try:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("پیوستن به کانال VIP", url=CHANNEL_LINK)]])
            await context.bot.send_message(target_id, "تبریک 🎉 حساب شما توسط ادمین تایید شد. اکنون میتوانید به کانال VIP بپیوندید 🚀", reply_markup=kb)
            # حذف یا غیرفعال کردن دکمه در پیام گروه (حذف reply_markup)
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass
            await query.message.reply_text(f"کاربر {target_id} تایید شد و اطلاع‌رسانی ارسال شد ✅")
        except Exception as e:
            await query.message.reply_text("خطا در ارسال پیام به کاربر. ممکن است کاربر ربات را استارت نکرده باشد.")
            logger.exception(e)
        return

# ============== MAIN ==============
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_text_handler))

    logger.info("Bot started")
    # اجرای هم‌زمان polling (همان سبک اولیه)
    app.run_polling()

if __name__ == "__main__":
    main()
