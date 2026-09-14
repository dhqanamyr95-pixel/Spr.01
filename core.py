"""منطق اصلی ربات — مستقل از روش اجرا (Polling یا Webhook)."""
import db
import tg_api
from config import ADMIN_IDS, BOT_USERNAME
from membership import get_not_joined_channels, build_join_keyboard


UPLOAD_BUTTON_TEXT = "📤 آپلود ویدیو"
MAIN_MENU = {"keyboard": [[UPLOAD_BUTTON_TEXT]], "resize_keyboard": True}


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ---------------- /start و تحویل ویدیو ----------------

def deliver_video_or_ask_join(chat_id, user_id, video_id):
    video = db.get_video(video_id)
    if not video:
        tg_api.send_message(chat_id, "❌ این لینک معتبر نیست یا فیلم حذف شده است.")
        return

    not_joined = get_not_joined_channels(user_id)
    if not_joined:
        tg_api.send_message(
            chat_id,
            "⛔️ برای دریافت فیلم، ابتدا باید عضو کانال‌های زیر شوید:",
            reply_markup=build_join_keyboard(not_joined, check_callback_data=f"check:{video_id}"),
        )
        return

    tg_api.copy_message(chat_id, video["chat_id"], video["message_id"])


def handle_start(msg):
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")
    tg_api.send_message(
        chat_id,
        "سلام 👋 به ربات خوش آمدید.\nاز منوی پایین می‌توانید ویدیوی خودتان را برای بررسی ارسال کنید.",
        reply_markup=MAIN_MENU,
    )
    parts = text.split(maxsplit=1)
    if len(parts) > 1:
        payload = parts[1].strip()
        if payload.startswith("v_"):
            video_id = payload[2:]
            deliver_video_or_ask_join(chat_id, msg["from"]["id"], video_id)


def handle_check_membership_callback(cq):
    data = cq["data"]
    video_id = data.split("check:", 1)[1]
    user_id = cq["from"]["id"]
    message = cq["message"]
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]

    tg_api.answer_callback_query(cq["id"])

    not_joined = get_not_joined_channels(user_id)
    if not_joined:
        tg_api.edit_message_text(
            chat_id, message_id,
            "⛔️ هنوز عضو همه کانال‌ها نشده‌اید. لطفا عضو شوید و دوباره بررسی کنید:",
            reply_markup=build_join_keyboard(not_joined, check_callback_data=f"check:{video_id}"),
        )
        return

    tg_api.edit_message_text(chat_id, message_id, "✅ عضویت شما تایید شد. در حال ارسال فیلم...")
    video = db.get_video(video_id)
    if not video:
        tg_api.send_message(chat_id, "❌ این لینک معتبر نیست یا فیلم حذف شده است.")
        return
    tg_api.copy_message(chat_id, video["chat_id"], video["message_id"])


# ---------------- مدیریت کانال‌ها (فقط ادمین) ----------------

def cmd_add_channel(msg):
    chat_id = msg["chat"]["id"]
    parts = msg.get("text", "").split(maxsplit=1)
    if len(parts) < 2:
        tg_api.send_message(chat_id, "استفاده: /addchannel @username_کانال")
        return
    identifier = parts[1].strip()
    chat = tg_api.get_chat(identifier)
    if not chat:
        tg_api.send_message(chat_id, "❌ خطا در دریافت اطلاعات کانال. مطمئن شوید ربات را ادمین کانال کرده‌اید.")
        return
    db.add_channel(chat["id"], chat.get("username"), chat.get("title") or identifier)
    tg_api.send_message(chat_id, f"✅ کانال «{chat.get('title')}» اضافه شد.")


def cmd_remove_channel(msg):
    chat_id = msg["chat"]["id"]
    parts = msg.get("text", "").split(maxsplit=1)
    if len(parts) < 2:
        tg_api.send_message(chat_id, "استفاده: /removechannel @username_کانال")
        return
    identifier = parts[1].strip()
    chat = tg_api.get_chat(identifier)
    if chat:
        db.remove_channel(chat["id"])
    else:
        db.remove_channel(identifier)
    tg_api.send_message(chat_id, "🗑 کانال حذف شد.")


def cmd_list_channels(msg):
    chat_id = msg["chat"]["id"]
    channels = db.get_channels()
    if not channels:
        tg_api.send_message(chat_id, "هیچ کانالی ثبت نشده است.")
        return
    lines = [f"• {ch['title']} ({ch['username'] or ch['chat_id']})" for ch in channels]
    tg_api.send_message(chat_id, "📋 کانال‌های اجباری:\n" + "\n".join(lines))


# ---------------- آپلود ویدیو توسط ادمین ----------------

def handle_admin_video(msg):
    chat_id = msg["chat"]["id"]
    title = msg.get("caption") or "بدون عنوان"
    video_id = db.add_video(
        chat_id=chat_id,
        message_id=msg["message_id"],
        title=title,
        added_by=msg["from"]["id"],
    )
    link = f"https://t.me/{BOT_USERNAME}?start=v_{video_id}"
    tg_api.send_message(chat_id, f"✅ ویدیو ذخیره شد.\n\n🔗 لینک اختصاصی:\n{link}")


# ---------------- ارسال ویدیو توسط کاربران عادی برای بررسی ----------------

def handle_ask_for_video(msg):
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    db.set_awaiting_upload(user_id, True)
    tg_api.send_message(
        chat_id,
        "🎬 لطفا ویدیوی خود را ارسال کنید.\nپس از بررسی توسط ادمین به شما اطلاع داده می‌شود.",
    )


def notify_admins_of_submission(sub_id, user):
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ تایید", "callback_data": f"approve_sub:{sub_id}"},
            {"text": "❌ رد", "callback_data": f"reject_sub:{sub_id}"},
        ]]
    }
    sub = db.get_pending_submission(sub_id)
    for admin_id in ADMIN_IDS:
        tg_api.copy_message(
            admin_id, sub["user_chat_id"], sub["message_id"],
            caption=f"📥 ویدیوی جدید از کاربر (آیدی: {user['id']}, نام: {user.get('first_name', '')})\nشناسه: {sub_id}",
            reply_markup=keyboard,
        )


def handle_user_video(msg):
    user_id = msg["from"]["id"]
    chat_id = msg["chat"]["id"]

    if not db.is_awaiting_upload(user_id):
        tg_api.send_message(chat_id, f"برای ارسال ویدیو ابتدا دکمه «{UPLOAD_BUTTON_TEXT}» را بزنید.")
        return

    db.set_awaiting_upload(user_id, False)
    sub_id = db.add_pending_submission(user_id, chat_id, msg["message_id"])
    notify_admins_of_submission(sub_id, msg["from"])
    tg_api.send_message(chat_id, "✅ ویدیوی شما برای بررسی ارسال شد. لطفا منتظر تایید بمانید.")


def handle_submission_decision(cq):
    action, sub_id = cq["data"].split(":", 1)
    message = cq["message"]
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]

    tg_api.answer_callback_query(cq["id"])

    sub = db.get_pending_submission(sub_id)
    if not sub:
        tg_api.edit_message_caption(chat_id, message_id, "این درخواست دیگر معتبر نیست.")
        return

    if action == "approve_sub":
        video_id = db.add_video(
            chat_id=sub["user_chat_id"],
            message_id=sub["message_id"],
            title=f"ارسالی کاربر {sub['user_id']}",
            added_by=cq["from"]["id"],
        )
        db.set_submission_status(sub_id, "approved")
        link = f"https://t.me/{BOT_USERNAME}?start=v_{video_id}"
        tg_api.edit_message_caption(chat_id, message_id, f"✅ تایید شد و به کتابخانه اضافه شد.\n🔗 {link}")
        tg_api.send_message(sub["user_id"], "✅ ویدیوی شما بررسی و تایید شد.")
    else:
        db.set_submission_status(sub_id, "rejected")
        tg_api.edit_message_caption(chat_id, message_id, "❌ رد شد.")
        tg_api.send_message(sub["user_id"], "❌ متاسفانه ویدیوی شما تایید نشد.")


# ---------------- روتر اصلی ----------------

def handle_message(msg):
    text = msg.get("text", "") or ""
    user_id = msg["from"]["id"]

    if text.startswith("/start"):
        handle_start(msg)
        return
    if text.startswith("/addchannel") and is_admin(user_id):
        cmd_add_channel(msg)
        return
    if text.startswith("/removechannel") and is_admin(user_id):
        cmd_remove_channel(msg)
        return
    if text.startswith("/channels") and is_admin(user_id):
        cmd_list_channels(msg)
        return
    if text == UPLOAD_BUTTON_TEXT:
        handle_ask_for_video(msg)
        return
    if "video" in msg:
        if is_admin(user_id):
            handle_admin_video(msg)
        else:
            handle_user_video(msg)
        return


def handle_callback(cq):
    data = cq.get("data", "")
    if data.startswith("check:"):
        handle_check_membership_callback(cq)
    elif data.startswith("approve_sub:") or data.startswith("reject_sub:"):
        handle_submission_decision(cq)



