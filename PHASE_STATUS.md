# وضعیت نسخه 0.2.0

## پیاده‌سازی‌شده در MVP
- احراز هویت مدیر با JWT و هش رمز عبور
- داشبورد با شمارنده‌های واقعی
- مشتریان: فهرست، جست‌وجو، ایجاد، ویرایش، بایگانی و Excel import/export
- محصولات: فهرست، ایجاد، ویرایش و غیرفعال‌سازی
- خریدها: ثبت و فهرست؛ ثبت خرید می‌تواند یادآور سرویس بسازد
- تیکت‌ها: ثبت، فهرست و ویرایش وضعیت/اطلاعات
- یادآورها: ایجاد و فهرست
- کمپین‌ها: ایجاد و ارسال مستقیم به مشتریانی که شناسه گفت‌وگوی بله دارند
- بله: بررسی اتصال با getMe و ارسال پیام با sendMessage
- گزارش پیام‌ها و رویدادهای حسابرسی

## هنوز لازم برای انتشار Enterprise
- صف پایدار با worker، retry/backoff، محدودیت نرخ و idempotency
- زمان‌بند واقعی یادآوری‌ها و سیاست timezone دقیق
- webhook دریافت updateهای بله و اتصال خودکار کاربر/گفت‌وگو
- نقش‌ها و مجوزهای تفصیلی، throttling ورود و نشست‌های قابل ابطال
- مدیریت رمزنگاری‌شدهٔ توکن بله
- Alembic migrations، PostgreSQL production profile و فرآیند deploy/backup/restore آزموده‌شده
- صفحه‌بندی سروری کامل، گزارش‌های پیشرفته، تست یکپارچه/امنیتی و پایش
- تأیید کامل build فرانت‌اند در این محیط به علت نبود دسترسی شبکه برای نصب npm packages انجام نشد

این نسخه MVP است و ادعای production-ready بودن ندارد.


## Bale bot update
- Implemented long-polling update receiver, persistent subscriber registration, welcome message, user keyboard, support-ticket capture and admin notification.
- Implemented an admin-only Bale menu with dashboard, recent customers/products/purchases/tickets/reminders, ticket status update/reply, basic customer/product creation, and broadcast.
- Admin authorization uses an exact `BALE_ADMIN_CHAT_ID` match.
- Configure using `BALE_BOT_TOKEN` and `BALE_ADMIN_CHAT_ID`; see `BALE_BOT_FA.md`.
- Broadcast remains synchronous and should be replaced by a durable queue before large-scale production use.
