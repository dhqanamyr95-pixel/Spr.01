import requests

from config import BOT_TOKEN

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"


def _call(method: str, payload: dict, request_timeout: int = 15):
    resp = requests.post(f"{API_BASE}/{method}", json=payload, timeout=request_timeout)
    data = resp.json()
    if not data.get("ok"):
        # فقط لاگ می‌کنیم، جلوی اجرای ربات را نمی‌گیریم
        print(f"[tg_api] {method} failed: {data}")
    return data.get("result")


def get_updates(offset=None, timeout=25):
    payload = {"timeout": timeout, "allowed_updates": ["message", "callback_query"]}
    if offset is not None:
        payload["offset"] = offset
    # تایم‌اوت درخواست HTTP باید بیشتر از long-poll timeout خود تلگرام باشد
    return _call("getUpdates", payload, request_timeout=timeout + 10) or []


def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _call("sendMessage", payload)


def copy_message(chat_id, from_chat_id, message_id, caption=None, reply_markup=None):
    payload = {"chat_id": chat_id, "from_chat_id": from_chat_id, "message_id": message_id}
    if caption is not None:
        payload["caption"] = caption
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _call("copyMessage", payload)


def get_chat(chat_identifier):
    return _call("getChat", {"chat_id": chat_identifier})


def get_chat_member(chat_id, user_id):
    return _call("getChatMember", {"chat_id": chat_id, "user_id": user_id})


def answer_callback_query(callback_query_id, text=None):
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    return _call("answerCallbackQuery", payload)


def edit_message_text(chat_id, message_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _call("editMessageText", payload)


def edit_message_reply_markup(chat_id, message_id, reply_markup=None):
    payload = {"chat_id": chat_id, "message_id": message_id}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _call("editMessageReplyMarkup", payload)


def edit_message_caption(chat_id, message_id, caption, reply_markup=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "caption": caption}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _call("editMessageCaption", payload)


def set_my_commands(commands):
    return _call("setMyCommands", {"commands": commands})


def set_webhook(url):
    return _call("setWebhook", {"url": url})


def get_webhook_info():
    return _call("getWebhookInfo", {})
