import db
import tg_api

NOT_MEMBER_STATUSES = {"left", "kicked"}


def get_not_joined_channels(user_id: int):
    channels = db.get_channels()
    not_joined = []
    for ch in channels:
        member = tg_api.get_chat_member(ch["chat_id"], user_id)
        if member is None:
            # اگر ربات ادمین کانال نباشد یا کانال در دسترس نباشد، برای اطمینان
            # آن را جزو کانال‌های عضو‌نشده در نظر می‌گیریم
            not_joined.append(ch)
            continue
        if member.get("status") in NOT_MEMBER_STATUSES:
            not_joined.append(ch)
    return not_joined


def build_join_keyboard(not_joined_channels, check_callback_data: str):
    rows = []
    for ch in not_joined_channels:
        if ch["username"]:
            url = f"https://t.me/{ch['username'].lstrip('@')}"
        else:
            url = f"https://t.me/c/{str(ch['chat_id']).replace('-100', '')}"
        rows.append([{"text": f"📢 عضویت در {ch['title']}", "url": url}])
    rows.append([{"text": "✅ عضو شدم، بررسی کن", "callback_data": check_callback_data}])
    return {"inline_keyboard": rows}
