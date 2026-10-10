"""Read pending Bale updates once and print the sender/chat IDs to configure the admin chat."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.core.config import settings
from app.integrations.bale.client import BaleClient

async def main():
    if not settings.bale_bot_token:
        raise SystemExit("Set BALE_BOT_TOKEN in the root .env file first.")
    print("در بله به ربات خود /start بفرستید. در حال بررسی updateهای معلق...")
    updates = await BaleClient(settings.bale_bot_token).get_updates(timeout_seconds=5)
    if not updates:
        print("Updateای پیدا نشد. در بله به ربات /start بفرستید و دوباره این اسکریپت را اجرا کنید.")
        return
    for update in updates:
        msg = update.get("message") or {}
        user = msg.get("from") or {}
        chat = msg.get("chat") or {}
        print(f"message={msg.get('text', '')!r} | user_id={user.get('id')} | chat_id={chat.get('id')} | name={user.get('first_name', '')}")
    print("برای مدیر معمولاً BALE_ADMIN_CHAT_ID باید برابر chat_id باشد. این اسکریپت updateها را دریافت می‌کند؛ سپس ربات را اجرا کنید.")

if __name__ == "__main__":
    asyncio.run(main())
