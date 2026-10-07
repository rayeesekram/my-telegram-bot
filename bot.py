import os
import ast
import operator as op
import re

from telegram import Update, ChatPermissions
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    ContextTypes,
    filters,
)

# =========================
# SETTINGS
# =========================

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "10000"))
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

WEBHOOK_PATH = "telegram-webhook"

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

if not RENDER_URL:
    raise RuntimeError("RENDER_EXTERNAL_URL is not set")


# =========================
# START / HELP
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\n"
        "من ربات همه‌کاره شما هستم 🤖\n\n"
        "دستورات:\n"
        "/start - شروع\n"
        "/help - راهنما\n"
        "/id - آیدی شما\n"
        "/info - معلومات شما\n"
        "/calc 2+2 - ماشین حساب\n"
        "/ping - تست ربات\n\n"
        "دستورات مدیریت گروپ:\n"
        "/ban - بن کردن عضو\n"
        "/unban - آزاد کردن عضو\n"
        "/kick - اخراج عضو\n"
        "/mute - سکوت عضو\n"
        "/unmute - رفع سکوت\n"
        "/del - حذف پیام\n"
        "/pin - پین پیام\n\n"
        "برای دستورات مدیریت، روی پیام شخص ریپلای کنید."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 ربات فعال است!")


# =========================
# USER INFO
# =========================

async def user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await update.message.reply_text(
        f"👤 نام: {user.full_name}\n"
        f"🆔 ID: `{user.id}`\n"
        f"🔗 Username: @{user.username if user.username else 'ندارد'}",
        parse_mode="Markdown"
    )


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await update.message.reply_text(
        f"👤 معلومات کاربر\n\n"
        f"نام: {user.full_name}\n"
        f"ID: `{user.id}`\n"
        f"Username: @{user.username if user.username else 'ندارد'}\n"
        f"Bot: {'بلی' if user.is_bot else 'نخیر'}",
        parse_mode="Markdown"
    )


# =========================
# CALCULATOR
# =========================

OPERATORS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}


def safe_calculate(expression):
    if len(expression) > 100:
        raise ValueError("عبارت خیلی طولانی است")

    tree = ast.parse(expression, mode="eval")

    def calculate(node):
        if isinstance(node, ast.Expression):
            return calculate(node.body)

        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError()

        if isinstance(node, ast.BinOp):
            if type(node.op) not in OPERATORS:
                raise ValueError()

            left = calculate(node.left)
            right = calculate(node.right)

            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ValueError()

            return OPERATORS[type(node.op)](left, right)

        if isinstance(node, ast.UnaryOp):
            if type(node.op) not in OPERATORS:
                raise ValueError()

            return OPERATORS[type(node.op)](calculate(node.operand))

        raise ValueError()

    return calculate(tree)


async def calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "مثال:\n/calc 10+5*2"
        )
        return

    expression = " ".join(context.args)

    try:
        result = safe_calculate(expression)

        await update.message.reply_text(
            f"🧮 نتیجه:\n`{result}`",
            parse_mode="Markdown"
        )

    except Exception:
        await update.message.reply_text(
            "❌ عبارت ریاضی درست نیست."
        )


# =========================
# ADMIN CHECK
# =========================

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.effective_user:
        return False

    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            update.effective_user.id
        )

        return member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )

    except Exception:
        return False


async def get_target(update: Update):
    if not update.message:
        return None

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❗ روی پیام شخص مورد نظر ریپلای کن و بعد دستور را بفرست."
        )
        return None

    return update.message.reply_to_message.from_user


# =========================
# BAN
# =========================

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ فقط ادمین می‌تواند این کار را انجام دهد.")
        return

    target = await get_target(update)

    if not target:
        return

    try:
        await context.bot.ban_chat_member(
            update.effective_chat.id,
            target.id
        )

        await update.message.reply_text(
            f"🚫 {target.full_name} بن شد."
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ نتوانستم کاربر را بن کنم.\n"
            "مطمئن شو ربات ادمین است."
        )


# =========================
# UNBAN
# =========================

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ فقط ادمین می‌تواند این کار را انجام دهد.")
        return

    target = await get_target(update)

    if not target:
        return

    try:
        await context.bot.unban_chat_member(
            update.effective_chat.id,
            target.id,
            only_if_banned=True
        )

        await update.message.reply_text(
            f"✅ {target.full_name} آزاد شد."
        )

    except Exception:
        await update.message.reply_text(
            "❌ عملیات انجام نشد."
        )


# =========================
# KICK
# =========================

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ فقط ادمین می‌تواند این کار را انجام دهد.")
        return

    target = await get_target(update)

    if not target:
        return

    try:
        await context.bot.ban_chat_member(
            update.effective_chat.id,
            target.id
        )

        await context.bot.unban_chat_member(
            update.effective_chat.id,
            target.id
        )

        await update.message.reply_text(
            f"👢 {target.full_name} از گروپ اخراج شد."
        )

    except Exception:
        await update.message.reply_text(
            "❌ نتوانستم کاربر را اخراج کنم."
        )


# =========================
# MUTE
# =========================

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ فقط ادمین می‌تواند این کار را انجام دهد.")
        return

    target = await get_target(update)

    if not target:
        return

    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            target.id,
            permissions=ChatPermissions.no_permissions()
        )

        await update.message.reply_text(
            f"🔇 {target.full_name} ساکت شد."
        )

    except Exception:
        await update.message.reply_text(
            "❌ نتوانستم کاربر را mute کنم."
        )


# =========================
# UNMUTE
# =========================

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ فقط ادمین می‌تواند این کار را انجام دهد.")
        return

    target = await get_target(update)

    if not target:
        return

    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            target.id,
            permissions=ChatPermissions.all_permissions()
        )

        await update.message.reply_text(
            f"🔊 {target.full_name} از حالت سکوت خارج شد."
        )

    except Exception:
        await update.message.reply_text(
            "❌ نتوانستم unmute کنم."
        )


# =========================
# DELETE
# =========================

async def delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ فقط ادمین می‌تواند این کار را انجام دهد.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❗ روی پیامی که می‌خواهی حذف شود ریپلای کن."
        )
        return

    try:
        await update.message.reply_to_message.delete()
        await update.message.delete()

    except Exception:
        await update.message.reply_text(
            "❌ نتوانستم پیام را حذف کنم."
        )


# =========================
# PIN
# =========================

async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ فقط ادمین می‌تواند این کار را انجام دهد.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❗ روی پیامی که می‌خواهی پین شود ریپلای کن."
        )
        return

    try:
        await update.message.reply_to_message.pin(
            disable_notification=True
        )

        await update.message.reply_text("📌 پیام پین شد.")

    except Exception:
        await update.message.reply_text(
            "❌ نتوانستم پیام را پین کنم."
        )


# =========================
# WELCOME
# =========================

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.chat_member:
        return

    old_status = update.chat_member.old_chat_member.status
    new_status = update.chat_member.new_chat_member.status

    if new_status not in (
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.RESTRICTED,
    ):
        return

    if old_status in (
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.RESTRICTED,
    ):
        return

    user = update.chat_member.new_chat_member.user

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            f"🎉 خوش آمدی {user.mention_html()}!\n"
            f"به گروپ خوش آمدی ❤️"
        ),
        parse_mode="HTML"
    )


# =========================
# ANTI LINK
# =========================

async def anti_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    text = update.message.text or update.message.caption or ""

    if not text:
        return

    link_pattern = r"(https?://|www\.|t\.me/|telegram\.me/)"

    if not re.search(link_pattern, text, re.IGNORECASE):
        return

    # ادمین‌ها را حذف نکن
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            update.effective_user.id
        )

        if member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        ):
            return

        await update.message.delete()

    except Exception:
        pass


# =========================
# ERROR HANDLER
# =========================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print("ERROR:", context.error)


# =========================
# MAIN
# =========================

def main():

    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    # Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("id", user_id))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("calc", calc))

    # Admin commands
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("unban", unban))
    application.add_handler(CommandHandler("kick", kick))
    application.add_handler(CommandHandler("mute", mute))
    application.add_handler(CommandHandler("unmute", unmute))
    application.add_handler(CommandHandler("del", delete_message))
    application.add_handler(CommandHandler("pin", pin_message))

    # Welcome
    application.add_handler(
        ChatMemberHandler(
            welcome,
            ChatMemberHandler.CHAT_MEMBER
        )
    )

    # Anti-link
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            anti_link
        )
    )

    application.add_error_handler(error_handler)

    webhook_url = f"{RENDER_URL.rstrip('/')}/{WEBHOOK_PATH}"

    print("================================")
    print("BOT STARTED")
    print("Webhook:", webhook_url)
    print("Port:", PORT)
    print("================================")

    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=webhook_url,
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
