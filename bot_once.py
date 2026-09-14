"""
نقطه‌ی ورود برای اجرا داخل GitHub Actions.
هر بار که این اسکریپت اجرا می‌شود، تا حدود ۴ دقیقه و نیم به‌صورت long-polling
از تلگرام آپدیت می‌گیرد (تقریباً real-time در همین بازه)، آن‌ها را پردازش
می‌کند و در پایان offset را ذخیره می‌کند تا اجرای بعدی از همانجا ادامه دهد.
"""
import time

import core
import db
import tg_api

# کمی کمتر از ۵ دقیقه، تا وقت کافی برای کامیت و پوش نتیجه در ورک‌فلو باقی بماند
MAX_RUN_SECONDS = 260
LONG_POLL_TIMEOUT = 25


def main():
    db.init_db()

    offset_raw = db.get_state("last_update_id")
    offset = int(offset_raw) + 1 if offset_raw else None

    start = time.time()
    processed = 0

    while time.time() - start < MAX_RUN_SECONDS:
        remaining = MAX_RUN_SECONDS - (time.time() - start)
        poll_timeout = min(LONG_POLL_TIMEOUT, max(1, int(remaining)))

        updates = tg_api.get_updates(offset=offset, timeout=poll_timeout)
        for update in updates:
            try:
                if "message" in update:
                    core.handle_message(update["message"])
                elif "callback_query" in update:
                    core.handle_callback(update["callback_query"])
            except Exception as e:  # هیچ آپدیتی نباید کل اجرا را متوقف کند
                print(f"[bot_once] error while handling update {update.get('update_id')}: {e}")
            offset = update["update_id"] + 1
            processed += 1
            db.set_state("last_update_id", str(update["update_id"]))

    print(f"[bot_once] finished, processed {processed} update(s).")


if __name__ == "__main__":
    main()
