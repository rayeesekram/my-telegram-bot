import os
import logging
import ast
import operator

from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ---------- Calculator ----------

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def calculate(expression):
    def solve(node):
        if isinstance(node, ast.Expression):
            return solve(node.body)

        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError

        if isinstance(node, ast.BinOp):
            op = OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError
            return op(solve(node.left), solve(node.right))

        if isinstance(node, ast.UnaryOp):
            op = OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError
            return op(solve(node.operand))

        raise ValueError

    return solve(ast.parse(expression, mode="eval"))


# ---------- Admin ----------

async def is_admin(update):
    if update.effective_chat.type == "private":
        return True

    member = await update.effective_chat.get_member(
        update.effective_user.id
    )

    return member.status in (
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.OWNER,
    )


def get_reply_user(update):
    if not update.message or not update.message.reply_to_message:
        return None

    return update.message.reply_to_message.from_user


# ---------- Start ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 سلام!\n\n"
        "من ربات همه‌کاره شما هستم.\n\n"
        "📌 دستورات عمومی:\n"
        "/help - راهنما\n"
        "/id - نمایش ID\n"
        "/info - اطلاعات کاربر\n"
        "/calc 10+5 - ماشین حساب\n\n"
        "🛡 مدیریت گروپ:\n"
        "/ban - بن کردن کاربر\n"
        "/unban - رفع بن\n"
        "/kick - اخراج کاربر\n"
        "/mute - ساکت کردن کاربر\n"
        "/unmute - رفع سکوت\n"
        "/del - حذف پیام\n"
        "/pin - سنجاق پیام\n\n"
        "برای دستورات مدیریتی باید ادمین باشی."
    )


async def help_command(update, context):
    await start(update, context)


# ---------- User information ----------

async def user_id(update, context):
    await update.message.reply_text(
        f"🆔 User ID: {update.effective_user.id}\n"
        f"💬 Chat ID: {update.effective_chat.id}"
    )


async def info(update, context):
    user = update.effective_user

    username = (
        f"@{user.username}"
        if user.username
        else "ندارد"
    )

    await update.message.reply_text(
        "👤 اطلاعات کاربر\n\n"
        f"نام: {user.first_name}\n"
        f"Username: {username}\n"
        f"ID: {user.id}"
    )


# ---------- Calculator ----------

async def calc(update, context):
    if not context.args:
        await update.message.reply_text(
            "مثال:\n"
            "/calc 10+5\n"
            "/calc (20*3)/2"
        )
        return

    expression = " ".join(context.args)

    try:
        result = calculate(expression)

        if abs(result) > 10**100:
            raise ValueError

        await update.message.reply_text(
            f"🧮 نتیجه: {result}"
        )

    except Exception:
        await update.message.reply_text(
            "❌ عبارت ریاضی درست نیست."
        )


# ---------- Ban ----------

async def ban(update, context):
    if not await is_admin(update):
        await update.message.reply_text(
            "❌ فقط ادمین‌ها می‌توانند."
        )
        return

    user = get_reply_user(update)

    if not user:
        await update.message.reply_text(
            "⚠️ روی پیام کاربر ریپلای کن و /ban بزن."
        )
        return

    try:
        await update.effective_chat.ban_member(user.id)

        await update.message.reply_text(
            f"🚫 {user.first_name} بن شد."
        )

    except Exception as e:
        logger.error(e)
        await update.message.reply_text(
            "❌ نتوانستم کاربر را بن کنم."
        )


# ---------- Unban ----------

async def unban(update, context):
    if not await is_admin(update):
        await update.message.reply_text(
            "❌ فقط ادمین‌ها می‌توانند."
        )
        return

    user = get_reply_user(update)

    if not user:
        await update.message.reply_text(
            "⚠️ روی پیام کاربر ریپلای کن."
        )
        return

    try:
        await update.effective_chat.unban_member(
            user.id,
            only_if_banned=True
        )

        await update.message.reply_text(
            f"✅ بن {user.first_name} برداشته شد."
        )

    except Exception:
        await update.message.reply_text(
            "❌ عملیات انجام نشد."
        )


# ---------- Kick ----------

async def kick(update, context):
    if not await is_admin(update):
        await update.message.reply_text(
            "❌ فقط ادمین‌ها می‌توانند."
        )
        return

    user = get_reply_user(update)

    if not user:
        await update.message.reply_text(
            "⚠️ روی پیام کاربر ریپلای کن."
        )
        return

    try:
        await update.effective_chat.ban_member(user.id)
        await update.effective_chat.unban_member(user.id)

        await update.message.reply_text(
            f"👢 {user.first_name} اخراج شد."
        )

    except Exception:
        await update.message.reply_text(
            "❌ نتوانستم کاربر را اخراج کنم."
        )


# ---------- Mute ----------

async def mute(update, context):
    if not await is_admin(update):
        await update.message.reply_text(
            "❌ فقط ادمین‌ها می‌توانند."
        )
        return

    user = get_reply_user(update)

    if not user:
        await update.message.reply_text(
            "⚠️ روی پیام کاربر ریپلای کن."
        )
        return

    try:
        await update.effective_chat.restrict_member(
            user.id,
            permissions={
                "can_send_messages": False,
                "can_send_audios": False,
                "can_send_documents": False,
                "can_send_photos": False,
                "can_send_videos": False,
                "can_send_video_notes": False,
                "can_send_voice_notes": False,
                "can_send_polls": False,
                "can_send_other_messages": False,
                "can_add_web_page_previews": False,
            },
        )

        await update.message.reply_text(
            f"🔇 {user.first_name} ساکت شد."
        )

    except Exception as e:
        logger.error(e)
        await update.message.reply_text(
            "❌ نتوانستم کاربر را mute کنم."
        )


# ---------- Unmute ----------

async def unmute(update, context):
    if not await is_admin(update):
        await update.message.reply_text(
            "❌ فقط ادمین‌ها می‌توانند."
        )
        return

    user = get_reply_user(update)

    if not user:
        await update.message.reply_text(
            "⚠️ روی پیام کاربر ریپلای کن."
        )
        return

    try:
        await update.effective_chat.restrict_member(
            user.id,
            permissions={
                "can_send_messages": True,
                "can_send_audios": True,
                "can_send_documents": True,
                "can_send_photos": True,
                "can_send_videos": True,
                "can_send_video_notes": True,
                "can_send_voice_notes": True,
                "can_send_polls": True,
                "can_send_other_messages": True,
                "can_add_web_page_previews": True,
            },
        )

        await update.message.reply_text(
            f"🔊 {user.first_name} آزاد شد."
        )

    except Exception:
        await update.message.reply_text(
            "❌ عملیات انجام نشد."
        )


# ---------- Delete ----------

async def delete_message(update, context):
    if not await is_admin(update):
        await update.message.reply_text(
            "❌ فقط ادمین‌ها می‌توانند."
        )
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "⚠️ روی پیامی که می‌خواهی حذف شود ریپلای کن."
        )
        return

    try:
        await update.message.reply_to_message.delete()
        await update.message.delete()

    except Exception:
        await update.message.reply_text(
            "❌ نتوانستم پیام را حذف کنم."
        )


# ---------- Pin ----------

async def pin(update, context):
    if not await is_admin(update):
        await update.message.reply_text(
            "❌ فقط ادمین‌ها می‌توانند."
        )
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "⚠️ روی پیام موردنظر ریپلای کن."
        )
        return

    try:
        await update.message.reply_to_message.pin(
            disable_notification=True
        )

        await update.message.reply_text(
            "📌 پیام سنجاق شد."
        )

    except Exception:
        await update.message.reply_text(
            "❌ نتوانستم پیام را سنجاق کنم."
        )


# ---------- Welcome ----------

async def welcome(update, context):
    if not update.chat_member:
        return

    old = update.chat_member.old_chat_member
    new = update.chat_member.new_chat_member

    if (
        old.status in ("left", "kicked")
        and new.status in ("member", "administrator")
    ):
        try:
            await context.bot.send_message(
                update.effective_chat.id,
                f"👋 خوش آمدی {new.user.first_name}!"
            )
        except Exception:
            pass


# ---------- Anti Link ----------

async def anti_link(update, context):
    if not update.message:
        return

    if update.effective_chat.type == "private":
        return

    text = update.message.text or ""

    if not any(
        x in text.lower()
        for x in ("http://", "https://", "t.me/")
    ):
        return

    try:
        member = await update.effective_chat.get_member(
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


# ---------- Main ----------

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(CommandHandler("id", user_id))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("calc", calc))

    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("del", delete_message))
    app.add_handler(CommandHandler("pin", pin))

    app.add_handler(
        ChatMemberHandler(
            welcome,
            ChatMemberHandler.CHAT_MEMBER
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            anti_link
        )
    )

    print("🤖 Bot is running...")

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
