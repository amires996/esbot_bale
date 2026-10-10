"""Bale long-polling bot: subscriber registration, user support tickets and admin tools."""
from __future__ import annotations

import asyncio
import logging
import calendar
from datetime import datetime, timezone, date
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import SessionLocal
from app.models import (
    Admin, AuditLog, BaleSubscriber, Campaign, Customer, MessageLog, Product,
    Purchase, ServiceReminder, SupportTicket,
)
from app.integrations.bale.client import BaleAPIError, BaleClient

logger = logging.getLogger("esbot.bale")

USER_KEYBOARD = {
    "keyboard": [[{"text": "🎫 پشتیبانی و ثبت تیکت"}], [{"text": "👤 اطلاعات من"}]],
    "resize_keyboard": True,
    "is_persistent": True,
}
ADMIN_KEYBOARD = {
    "keyboard": [
        [{"text": "📊 داشبورد"}, {"text": "👥 مشتریان"}],
        [{"text": "📦 محصولات"}, {"text": "🧾 خریدها"}],
        [{"text": "🎫 تیکت‌ها"}, {"text": "🔔 یادآورها"}],
        [{"text": "📣 پیام همگانی"}, {"text": "❔ راهنمای مدیریت"}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}


def _now():
    return datetime.now(timezone.utc)


def _name(user: dict) -> tuple[str, str]:
    first = (user.get("first_name") or "کاربر بله").strip()[:100]
    last = (user.get("last_name") or "").strip()[:100]
    return first, last


def _upsert_subscriber(db: Session, user: dict, chat_id: str) -> BaleSubscriber:
    user_id = str(user.get("id") or "").strip()
    if not user_id:
        raise ValueError("Incoming Bale update has no user id")
    subscriber = db.scalar(select(BaleSubscriber).where(BaleSubscriber.bale_user_id == user_id))
    first, last = _name(user)
    if subscriber is None:
        subscriber = BaleSubscriber(
            bale_user_id=user_id, bale_chat_id=str(chat_id), first_name=first,
            last_name=last, username=(user.get("username") or None),
            started_at=_now(), last_seen_at=_now(),
        )
        db.add(subscriber)
    else:
        subscriber.bale_chat_id = str(chat_id)
        subscriber.first_name = first
        subscriber.last_name = last
        subscriber.username = user.get("username") or None
        subscriber.last_seen_at = _now()
        subscriber.is_blocked = False
    db.flush()
    return subscriber


def _ensure_customer(db: Session, subscriber: BaleSubscriber) -> Customer:
    customer = db.get(Customer, subscriber.customer_id) if subscriber.customer_id else None
    if customer is None:
        customer = db.scalar(select(Customer).where(Customer.bale_user_id == subscriber.bale_user_id))
    if customer is None:
        customer = Customer(
            first_name=subscriber.first_name or "کاربر بله",
            last_name=subscriber.last_name or "",
            mobile=f"BALE-{subscriber.bale_user_id}",
            bale_user_id=subscriber.bale_user_id,
            bale_chat_id=subscriber.bale_chat_id,
            notes="ثبت‌نام خودکار از طریق ربات بله؛ شماره موبایل هنوز دریافت نشده است.",
        )
        db.add(customer)
        db.flush()
    else:
        customer.first_name = subscriber.first_name or customer.first_name
        customer.last_name = subscriber.last_name or customer.last_name
        customer.bale_user_id = subscriber.bale_user_id
        customer.bale_chat_id = subscriber.bale_chat_id
    subscriber.customer_id = customer.id
    return customer


def _admin_help() -> str:
    return (
        "راهنمای مدیریت ESBot در بله\n\n"
        "از دکمه‌های منو برای مشاهده داشبورد، مشتریان، محصولات، خریدها، تیکت‌ها و یادآورها استفاده کنید.\n\n"
        "دستورهای مدیریتی:\n"
        "/dashboard — آمار سامانه\n"
        "/customers — آخرین مشتریان\n"
        "/products — محصولات\n"
        "/tickets — تیکت‌های اخیر\n"
        "/ticket ID — جزئیات تیکت\n"
        "/ticketstatus ID open|in_progress|resolved|closed — تغییر وضعیت تیکت\n"
        "/reply ID متن پاسخ — پاسخ به کاربر تیکت\n"
        "/addcustomer نام|نام‌خانوادگی|موبایل — افزودن مشتری\n"
        "/editcustomer ID|نام|نام‌خانوادگی|موبایل — ویرایش مشتری\n"
        "/archivecustomer ID — بایگانی مشتری\n"
        "/addproduct نام|برند|مدل|فاصله‌سرویس‌به‌ماه — افزودن محصول\n"
        "/editproduct ID|نام|برند|مدل|فاصله‌سرویس‌به‌ماه — ویرایش محصول\n"
        "/disableproduct ID — غیرفعال‌کردن محصول\n"
        "/addpurchase customer_id|product_id|YYYY-MM-DD|شماره‌فاکتور — ثبت خرید\n"
        "/addreminder purchase_id|YYYY-MM-DD|متن یادآور — ثبت یادآور\n"
        "/broadcast متن پیام — پیام همگانی برای کاربران استارت‌زده\n\n"
        "فقط شناسه مدیریتی تنظیم‌شده در .env اجازه استفاده از این بخش را دارد."
    )


class BaleBotService:
    def __init__(self, token: str, admin_chat_id: str):
        self.client = BaleClient(token)
        self.admin_chat_id = str(admin_chat_id).strip()
        self._offset: int | None = None
        self._broadcast_waiting = False

    async def run_forever(self):
        logger.info("Bale polling started")
        while True:
            try:
                updates = await self.client.get_updates(self._offset, settings.bale_poll_timeout_seconds)
                for update in updates:
                    try:
                        await self.handle_update(update)
                    except Exception:
                        logger.exception("Failed to process Bale update id=%s", update.get("update_id"))
                    if isinstance(update.get("update_id"), int):
                        self._offset = update["update_id"] + 1
            except asyncio.CancelledError:
                raise
            except BaleAPIError as exc:
                logger.warning("Bale polling error %s: %s", exc.code, exc.message)
                await asyncio.sleep(3 if exc.retryable else 8)
            except Exception:
                logger.exception("Unexpected Bale polling failure")
                await asyncio.sleep(5)

    async def _send(self, chat_id: str | int, text: str, keyboard: dict | None = None):
        return await self.client.send_text(chat_id, text[:4096], keyboard)

    async def handle_update(self, update: dict):
        message = update.get("message") or update.get("edited_message")
        if not isinstance(message, dict):
            return
        chat = message.get("chat") or {}
        user = message.get("from") or {}
        chat_id = str(chat.get("id") or "").strip()
        text = (message.get("text") or "").strip()
        if not chat_id or not user.get("id") or not text:
            return
        is_admin = chat_id == self.admin_chat_id
        with SessionLocal() as db:
            subscriber = _upsert_subscriber(db, user, chat_id)
            db.commit()
            if is_admin:
                await self._handle_admin(db, subscriber, text)
            else:
                await self._handle_user(db, subscriber, text)

    async def _handle_user(self, db: Session, subscriber: BaleSubscriber, text: str):
        low = text.lower().split("@", 1)[0]
        if low in ("/start", "/start esbot", "شروع", "شروع مجدد"):
            subscriber.support_mode = False
            db.commit()
            first = subscriber.first_name or "دوست عزیز"
            await self._send(
                subscriber.bale_chat_id,
                f"سلام {first} عزیز 🌷\nبه ربات پشتیبانی خوش آمدید.\nثبت‌نام شما با موفقیت انجام شد. از منوی پایین می‌توانید درخواست پشتیبانی ثبت کنید.",
                USER_KEYBOARD,
            )
            return
        if text == "🎫 پشتیبانی و ثبت تیکت" or low in ("/support", "پشتیبانی", "تیکت"):
            subscriber.support_mode = True
            db.commit()
            await self._send(subscriber.bale_chat_id, "لطفاً درخواست یا مشکل خود را در یک پیام بنویسید. پیام شما به مدیریت پشتیبانی ارسال می‌شود.", USER_KEYBOARD)
            return
        if text == "👤 اطلاعات من" or low in ("/me", "اطلاعات من"):
            await self._send(subscriber.bale_chat_id, f"اطلاعات ثبت‌شده شما:\nنام: {subscriber.first_name} {subscriber.last_name}\nشناسه کاربری بله: {subscriber.bale_user_id}\nوضعیت: ثبت‌شده در سامانه", USER_KEYBOARD)
            return
        if subscriber.support_mode:
            customer = _ensure_customer(db, subscriber)
            title = "درخواست پشتیبانی"
            ticket = SupportTicket(customer_id=customer.id, title=title, description=text, priority="normal", status="open")
            db.add(ticket)
            db.flush()
            subscriber.support_mode = False
            db.add(AuditLog(action="bale_support_ticket_created", entity="support_ticket", entity_id=str(ticket.id), details={"subscriber_id": subscriber.id}))
            db.commit()
            await self._send(subscriber.bale_chat_id, f"درخواست شما با موفقیت ثبت شد. 🎫\nشماره تیکت: #{ticket.id}\nمدیریت پس از بررسی پاسخ خواهد داد.", USER_KEYBOARD)
            admin_text = (
                f"🎫 تیکت پشتیبانی جدید #{ticket.id}\n"
                f"کاربر: {subscriber.first_name} {subscriber.last_name}\n"
                f"شناسه بله: {subscriber.bale_user_id}"
            )
            if subscriber.username:
                admin_text += f"\nنام کاربری: @{subscriber.username}"
            admin_text += f"\n\nمتن درخواست:\n{text}\n\nبرای پاسخ:\n/reply {ticket.id} متن پاسخ"
            try:
                await self._send(self.admin_chat_id, admin_text, ADMIN_KEYBOARD)
            except BaleAPIError:
                logger.exception("Could not notify admin about ticket %s", ticket.id)
            return
        await self._send(subscriber.bale_chat_id, "برای ثبت درخواست، دکمه «🎫 پشتیبانی و ثبت تیکت» را بزنید. برای شروع دوباره می‌توانید /start را ارسال کنید.", USER_KEYBOARD)

    async def _handle_admin(self, db: Session, subscriber: BaleSubscriber, text: str):
        low = text.lower()
        if low in ("/start", "/admin", "❔ راهنمای مدیریت"):
            await self._send(self.admin_chat_id, "پنل مدیریت ESBot فعال است. یک بخش را انتخاب کنید یا /help بفرستید.", ADMIN_KEYBOARD)
            return
        if low in ("/help", "راهنما"):
            await self._send(self.admin_chat_id, _admin_help(), ADMIN_KEYBOARD)
            return
        if text in ("📊 داشبورد", "/dashboard"):
            counts = {
                "subscribers": db.scalar(select(func.count()).select_from(BaleSubscriber).where(BaleSubscriber.is_blocked.is_(False))) or 0,
                "customers": db.scalar(select(func.count()).select_from(Customer).where(Customer.is_archived.is_(False))) or 0,
                "products": db.scalar(select(func.count()).select_from(Product).where(Product.is_active.is_(True))) or 0,
                "purchases": db.scalar(select(func.count()).select_from(Purchase)) or 0,
                "tickets": db.scalar(select(func.count()).select_from(SupportTicket).where(SupportTicket.status.in_(["open", "in_progress"]))) or 0,
                "reminders": db.scalar(select(func.count()).select_from(ServiceReminder).where(ServiceReminder.status == "pending")) or 0,
            }
            await self._send(self.admin_chat_id, "📊 داشبورد ESBot\n\n" + f"کاربران استارت‌زده: {counts['subscribers']}\nمشتریان: {counts['customers']}\nمحصولات فعال: {counts['products']}\nسوابق خرید: {counts['purchases']}\nتیکت‌های باز: {counts['tickets']}\nیادآورهای در انتظار: {counts['reminders']}", ADMIN_KEYBOARD)
            return
        if text in ("👥 مشتریان", "/customers"):
            items = list(db.scalars(select(Customer).where(Customer.is_archived.is_(False)).order_by(Customer.id.desc()).limit(15)))
            body = "👥 آخرین مشتریان\n\n" + ("\n".join(f"#{x.id} {x.first_name} {x.last_name} | {x.mobile or 'بدون شماره'}" for x in items) or "مشتری‌ای ثبت نشده است.")
            await self._send(self.admin_chat_id, body, ADMIN_KEYBOARD); return
        if text in ("📦 محصولات", "/products"):
            items = list(db.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.id.desc()).limit(15)))
            body = "📦 محصولات فعال\n\n" + ("\n".join(f"#{x.id} {x.name} | سرویس هر {x.service_interval} {x.service_interval_unit}" for x in items) or "محصولی ثبت نشده است.")
            await self._send(self.admin_chat_id, body, ADMIN_KEYBOARD); return
        if text in ("🧾 خریدها", "/purchases"):
            items = list(db.scalars(select(Purchase).order_by(Purchase.id.desc()).limit(10)))
            body = "🧾 آخرین خریدها\n\n" + ("\n".join(f"#{x.id} مشتری {x.customer_id} | محصول {x.product_id} | {x.purchase_date}" for x in items) or "خریدی ثبت نشده است.")
            await self._send(self.admin_chat_id, body, ADMIN_KEYBOARD); return
        if text in ("🎫 تیکت‌ها", "/tickets"):
            items = list(db.scalars(select(SupportTicket).order_by(SupportTicket.id.desc()).limit(15)))
            body = "🎫 تیکت‌های اخیر\n\n" + ("\n".join(f"#{x.id} مشتری {x.customer_id} | {x.status} | {x.title}" for x in items) or "تیکتی وجود ندارد.")
            await self._send(self.admin_chat_id, body, ADMIN_KEYBOARD); return
        if text in ("🔔 یادآورها", "/reminders"):
            items = list(db.scalars(select(ServiceReminder).order_by(ServiceReminder.due_date).limit(15)))
            body = "🔔 یادآورها\n\n" + ("\n".join(f"#{x.id} | خرید {x.purchase_id} | {x.due_date} | {x.status}" for x in items) or "یادآوری‌ای ثبت نشده است.")
            await self._send(self.admin_chat_id, body, ADMIN_KEYBOARD); return
        if text == "📣 پیام همگانی" or low == "/broadcast" or low.startswith("/broadcast "):
            parts = text.split(maxsplit=1)
            if len(parts) == 2 and parts[1].strip():
                await self._broadcast(db, parts[1].strip()); return
            self._broadcast_waiting = True
            await self._send(self.admin_chat_id, "متن پیام همگانی را در پیام بعدی بفرستید. برای لغو /cancel را ارسال کنید.", ADMIN_KEYBOARD)
            return
        if self._broadcast_waiting:
            self._broadcast_waiting = False
            if low == "/cancel":
                await self._send(self.admin_chat_id, "ارسال پیام همگانی لغو شد.", ADMIN_KEYBOARD); return
            await self._broadcast(db, text); return
        if low.startswith("/ticket "):
            await self._ticket_detail(db, text); return
        if low.startswith("/ticketstatus "):
            await self._ticket_status(db, text); return
        if low.startswith("/reply "):
            await self._ticket_reply(db, text); return
        if low.startswith("/addcustomer "):
            await self._add_customer(db, text); return
        if low.startswith("/addproduct "):
            await self._add_product(db, text); return
        if low.startswith("/editcustomer "):
            await self._edit_customer(db, text); return
        if low.startswith("/archivecustomer "):
            await self._archive_customer(db, text); return
        if low.startswith("/editproduct "):
            await self._edit_product(db, text); return
        if low.startswith("/disableproduct "):
            await self._disable_product(db, text); return
        if low.startswith("/addpurchase "):
            await self._add_purchase(db, text); return
        if low.startswith("/addreminder "):
            await self._add_reminder(db, text); return
        await self._send(self.admin_chat_id, "دستور شناخته نشد. /help را ارسال کنید.", ADMIN_KEYBOARD)

    async def _broadcast(self, db: Session, message: str):
        if len(message) > 4000:
            await self._send(self.admin_chat_id, "پیام برای ارسال همگانی بیش از حد طولانی است؛ حداکثر ۴۰۰۰ نویسه.", ADMIN_KEYBOARD); return
        subscribers = list(db.scalars(select(BaleSubscriber).where(BaleSubscriber.is_blocked.is_(False), BaleSubscriber.bale_chat_id != self.admin_chat_id)))
        campaign = Campaign(title=f"پیام همگانی بله {datetime.now().strftime('%Y-%m-%d %H:%M')}", message=message, status="sending", recipient_count=len(subscribers), sent_count=0)
        db.add(campaign); db.flush()
        sent = failed = 0
        for sub in subscribers:
            log = MessageLog(customer_id=sub.customer_id, recipient=sub.bale_chat_id, text=message, status="sending")
            db.add(log); db.flush()
            try:
                await self.client.send_text(sub.bale_chat_id, message, USER_KEYBOARD)
                log.status = "sent"; sent += 1
            except BaleAPIError as exc:
                log.status = "failed"; log.error = exc.message; failed += 1
                if exc.code in ("403", "BOT_BLOCKED", "CHAT_NOT_FOUND"):
                    sub.is_blocked = True
            db.commit()
            await asyncio.sleep(0.08)  # conservative pacing; use a durable queue for large audiences
        campaign.sent_count = sent
        campaign.status = "sent" if failed == 0 else ("partial" if sent else "failed")
        db.add(AuditLog(action="bale_broadcast", entity="campaign", entity_id=str(campaign.id), details={"recipients": len(subscribers), "sent": sent, "failed": failed}))
        db.commit()
        await self._send(self.admin_chat_id, f"گزارش ارسال همگانی\nگیرندگان: {len(subscribers)}\nموفق: {sent}\nناموفق: {failed}", ADMIN_KEYBOARD)

    async def _ticket_detail(self, db: Session, text: str):
        try: ident = int(text.split()[1])
        except (ValueError, IndexError):
            await self._send(self.admin_chat_id, "فرمت: /ticket ID", ADMIN_KEYBOARD); return
        ticket = db.get(SupportTicket, ident)
        if not ticket:
            await self._send(self.admin_chat_id, "تیکت پیدا نشد.", ADMIN_KEYBOARD); return
        customer = db.get(Customer, ticket.customer_id)
        await self._send(self.admin_chat_id, f"تیکت #{ticket.id}\nمشتری: {customer.first_name} {customer.last_name if customer else ''}\nوضعیت: {ticket.status}\nعنوان: {ticket.title}\n\n{ticket.description}\n\nپاسخ: /reply {ticket.id} متن پاسخ", ADMIN_KEYBOARD)

    async def _ticket_status(self, db: Session, text: str):
        parts = text.split()
        valid = {"open", "in_progress", "resolved", "closed"}
        if len(parts) != 3 or parts[2] not in valid:
            await self._send(self.admin_chat_id, "فرمت: /ticketstatus ID open|in_progress|resolved|closed", ADMIN_KEYBOARD); return
        try: ticket = db.get(SupportTicket, int(parts[1]))
        except ValueError: ticket = None
        if not ticket:
            await self._send(self.admin_chat_id, "تیکت پیدا نشد.", ADMIN_KEYBOARD); return
        ticket.status = parts[2]; ticket.updated_at = _now(); db.commit()
        await self._send(self.admin_chat_id, f"وضعیت تیکت #{ticket.id} به {ticket.status} تغییر کرد.", ADMIN_KEYBOARD)

    async def _ticket_reply(self, db: Session, text: str):
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            await self._send(self.admin_chat_id, "فرمت: /reply ID متن پاسخ", ADMIN_KEYBOARD); return
        try: ticket = db.get(SupportTicket, int(parts[1]))
        except ValueError: ticket = None
        if not ticket:
            await self._send(self.admin_chat_id, "تیکت پیدا نشد.", ADMIN_KEYBOARD); return
        customer = db.get(Customer, ticket.customer_id)
        if not customer or not customer.bale_chat_id:
            await self._send(self.admin_chat_id, "برای این تیکت شناسه چت بله ثبت نشده است.", ADMIN_KEYBOARD); return
        reply = parts[2].strip()
        try:
            await self.client.send_text(customer.bale_chat_id, f"پاسخ پشتیبانی به تیکت #{ticket.id}:\n\n{reply}", USER_KEYBOARD)
            ticket.status = "in_progress"; ticket.updated_at = _now()
            db.add(MessageLog(customer_id=customer.id, recipient=customer.bale_chat_id, text=reply, status="sent"))
            db.commit()
            await self._send(self.admin_chat_id, f"پاسخ تیکت #{ticket.id} برای کاربر ارسال شد.", ADMIN_KEYBOARD)
        except BaleAPIError as exc:
            await self._send(self.admin_chat_id, f"ارسال پاسخ ناموفق بود: {exc.message}", ADMIN_KEYBOARD)

    async def _add_customer(self, db: Session, text: str):
        parts = text.split(maxsplit=1)
        fields = parts[1].split("|") if len(parts) > 1 else []
        if len(fields) != 3 or not all(x.strip() for x in fields):
            await self._send(self.admin_chat_id, "فرمت: /addcustomer نام|نام‌خانوادگی|موبایل", ADMIN_KEYBOARD); return
        first, last, mobile = [x.strip() for x in fields]
        if db.scalar(select(Customer).where(Customer.mobile == mobile)):
            await self._send(self.admin_chat_id, "این شماره موبایل قبلاً ثبت شده است.", ADMIN_KEYBOARD); return
        customer = Customer(first_name=first, last_name=last, mobile=mobile)
        db.add(customer); db.commit()
        await self._send(self.admin_chat_id, f"مشتری #{customer.id} ثبت شد.", ADMIN_KEYBOARD)

    async def _add_product(self, db: Session, text: str):
        parts = text.split(maxsplit=1)
        fields = parts[1].split("|") if len(parts) > 1 else []
        if len(fields) != 4:
            await self._send(self.admin_chat_id, "فرمت: /addproduct نام|برند|مدل|فاصله‌سرویس‌به‌ماه", ADMIN_KEYBOARD); return
        try: interval = int(fields[3].strip())
        except ValueError:
            await self._send(self.admin_chat_id, "فاصله سرویس باید عدد باشد.", ADMIN_KEYBOARD); return
        if interval < 1 or interval > 120:
            await self._send(self.admin_chat_id, "فاصله سرویس باید بین ۱ تا ۱۲۰ ماه باشد.", ADMIN_KEYBOARD); return
        product = Product(name=fields[0].strip(), brand=fields[1].strip() or None, model=fields[2].strip() or None, service_interval=interval, service_interval_unit="months")
        db.add(product); db.commit()
        await self._send(self.admin_chat_id, f"محصول #{product.id} ثبت شد.", ADMIN_KEYBOARD)


    async def _edit_customer(self, db: Session, text: str):
        parts = text.split(maxsplit=1)
        fields = parts[1].split("|") if len(parts) > 1 else []
        if len(fields) != 4:
            await self._send(self.admin_chat_id, "فرمت: /editcustomer ID|نام|نام‌خانوادگی|موبایل", ADMIN_KEYBOARD); return
        try: customer = db.get(Customer, int(fields[0].strip()))
        except ValueError: customer = None
        if not customer:
            await self._send(self.admin_chat_id, "مشتری پیدا نشد.", ADMIN_KEYBOARD); return
        mobile = fields[3].strip()
        duplicate = db.scalar(select(Customer).where(Customer.mobile == mobile, Customer.id != customer.id))
        if duplicate:
            await self._send(self.admin_chat_id, "این شماره موبایل برای مشتری دیگری ثبت شده است.", ADMIN_KEYBOARD); return
        customer.first_name, customer.last_name, customer.mobile = fields[1].strip(), fields[2].strip(), mobile
        db.commit()
        await self._send(self.admin_chat_id, f"اطلاعات مشتری #{customer.id} به‌روزرسانی شد.", ADMIN_KEYBOARD)

    async def _archive_customer(self, db: Session, text: str):
        try: ident = int(text.split()[1])
        except (ValueError, IndexError):
            await self._send(self.admin_chat_id, "فرمت: /archivecustomer ID", ADMIN_KEYBOARD); return
        customer = db.get(Customer, ident)
        if not customer:
            await self._send(self.admin_chat_id, "مشتری پیدا نشد.", ADMIN_KEYBOARD); return
        customer.is_archived = True; db.commit()
        await self._send(self.admin_chat_id, f"مشتری #{ident} بایگانی شد.", ADMIN_KEYBOARD)

    async def _edit_product(self, db: Session, text: str):
        parts = text.split(maxsplit=1)
        fields = parts[1].split("|") if len(parts) > 1 else []
        if len(fields) != 5:
            await self._send(self.admin_chat_id, "فرمت: /editproduct ID|نام|برند|مدل|فاصله‌سرویس‌به‌ماه", ADMIN_KEYBOARD); return
        try:
            product_id, interval = int(fields[0].strip()), int(fields[4].strip())
        except ValueError:
            await self._send(self.admin_chat_id, "شناسه و فاصله سرویس باید عدد باشند.", ADMIN_KEYBOARD); return
        product = db.get(Product, product_id)
        if not product:
            await self._send(self.admin_chat_id, "محصول پیدا نشد.", ADMIN_KEYBOARD); return
        if not 1 <= interval <= 120 or not fields[1].strip():
            await self._send(self.admin_chat_id, "نام محصول الزامی است و فاصله سرویس باید بین ۱ تا ۱۲۰ ماه باشد.", ADMIN_KEYBOARD); return
        product.name = fields[1].strip(); product.brand = fields[2].strip() or None
        product.model = fields[3].strip() or None; product.service_interval = interval; product.service_interval_unit = "months"
        db.commit()
        await self._send(self.admin_chat_id, f"محصول #{product.id} ویرایش شد.", ADMIN_KEYBOARD)

    async def _disable_product(self, db: Session, text: str):
        try: ident = int(text.split()[1])
        except (ValueError, IndexError):
            await self._send(self.admin_chat_id, "فرمت: /disableproduct ID", ADMIN_KEYBOARD); return
        product = db.get(Product, ident)
        if not product:
            await self._send(self.admin_chat_id, "محصول پیدا نشد.", ADMIN_KEYBOARD); return
        product.is_active = False; db.commit()
        await self._send(self.admin_chat_id, f"محصول #{ident} غیرفعال شد.", ADMIN_KEYBOARD)

    async def _add_purchase(self, db: Session, text: str):
        parts = text.split(maxsplit=1)
        fields = parts[1].split("|") if len(parts) > 1 else []
        if len(fields) not in (3, 4):
            await self._send(self.admin_chat_id, "فرمت: /addpurchase customer_id|product_id|YYYY-MM-DD|شماره‌فاکتور (اختیاری)", ADMIN_KEYBOARD); return
        try:
            customer_id, product_id = int(fields[0].strip()), int(fields[1].strip())
            purchase_date = date.fromisoformat(fields[2].strip())
        except ValueError:
            await self._send(self.admin_chat_id, "شناسه‌ها یا تاریخ نامعتبر است؛ تاریخ باید YYYY-MM-DD باشد.", ADMIN_KEYBOARD); return
        customer, product = db.get(Customer, customer_id), db.get(Product, product_id)
        if not customer or customer.is_archived or not product or not product.is_active:
            await self._send(self.admin_chat_id, "مشتری فعال یا محصول فعال پیدا نشد.", ADMIN_KEYBOARD); return
        purchase = Purchase(customer_id=customer_id, product_id=product_id, purchase_date=purchase_date.isoformat(), invoice_number=fields[3].strip() if len(fields) == 4 and fields[3].strip() else None, service_interval=product.service_interval, service_interval_unit=product.service_interval_unit)
        db.add(purchase); db.flush()
        interval = product.service_interval
        if product.service_interval_unit == "days":
            due = date.fromordinal(purchase_date.toordinal() + interval)
        elif product.service_interval_unit == "years":
            year = purchase_date.year + interval
            due = date(year, purchase_date.month, min(purchase_date.day, calendar.monthrange(year, purchase_date.month)[1]))
        else:
            idx = purchase_date.year * 12 + purchase_date.month - 1 + interval
            year, month0 = divmod(idx, 12); month = month0 + 1
            due = date(year, month, min(purchase_date.day, calendar.monthrange(year, month)[1]))
        if product.reminders_enabled:
            db.add(ServiceReminder(purchase_id=purchase.id, due_date=due.isoformat()))
        db.commit()
        await self._send(self.admin_chat_id, f"خرید #{purchase.id} ثبت شد. تاریخ سرویس بعدی: {due.isoformat()}", ADMIN_KEYBOARD)

    async def _add_reminder(self, db: Session, text: str):
        parts = text.split(maxsplit=1)
        fields = parts[1].split("|", 2) if len(parts) > 1 else []
        if len(fields) != 3:
            await self._send(self.admin_chat_id, "فرمت: /addreminder purchase_id|YYYY-MM-DD|متن یادآور", ADMIN_KEYBOARD); return
        try:
            purchase_id = int(fields[0].strip())
            due = date.fromisoformat(fields[1].strip())
        except ValueError:
            await self._send(self.admin_chat_id, "شناسه خرید یا تاریخ نامعتبر است.", ADMIN_KEYBOARD); return
        if not db.get(Purchase, purchase_id):
            await self._send(self.admin_chat_id, "سابقه خرید پیدا نشد.", ADMIN_KEYBOARD); return
        reminder = ServiceReminder(purchase_id=purchase_id, due_date=due.isoformat(), message=fields[2].strip() or "زمان سرویس دوره‌ای محصول شما فرا رسیده است.")
        db.add(reminder); db.commit()
        await self._send(self.admin_chat_id, f"یادآور #{reminder.id} برای {due.isoformat()} ثبت شد.", ADMIN_KEYBOARD)
