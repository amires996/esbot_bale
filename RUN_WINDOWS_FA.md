# راهنمای اجرای ESBot در ویندوز

## ۱. آماده‌سازی
- Python 3.12 یا جدیدتر
- Node.js 20 یا جدیدتر
- فایل ZIP را استخراج کنید.
- در ریشه پوشه `esbot` فایل `.env.example` را به `.env` کپی کنید.

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
notepad .env
```

مقدار خروجی را در مقدار `SECRET_KEY` قرار دهید و فایل را ذخیره کنید.

## ۲. اجرای بک‌اند
در PowerShell:

```powershell
cd C:\مسیر\شما\esbot\backend
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
python ..\scripts\create_admin.py
python -m uvicorn app.main:app --reload
```

یک نام کاربری و رمز عبور حداقل ۱۲ کاراکتری برای مدیر تعیین کنید. این پنجره را باز نگه دارید.

- API: `http://127.0.0.1:8000`
- مستندات: `http://127.0.0.1:8000/docs`

## ۳. اجرای رابط کاربری
یک PowerShell دوم باز کنید:

```powershell
cd C:\مسیر\شما\esbot\frontend
npm.cmd install
npm.cmd run dev
```

آدرس اعلام‌شده توسط Vite را باز کنید؛ معمولاً `http://localhost:5173`.

اگر `npm` به دلیل Execution Policy خطا داد، از `npm.cmd` استفاده کنید. اگر نصب وابستگی‌ها خطا داد، متن کامل خطا مهم است؛ آن را بدون توکن‌ها/رمزهای خصوصی ارسال کنید.

## ۴. استفاده اولیه
۱. با حساب مدیری که در مرحلهٔ بک‌اند ساختید وارد شوید.
۲. ابتدا مشتری بسازید.
۳. سپس محصول بسازید.
۴. برای ثبت خرید، شناسه مشتری و شناسه محصول را از جدول‌ها بردارید و تاریخ را با قالب `YYYY-MM-DD` وارد کنید.
۵. ثبت خرید در صورت فعال بودن یادآوری محصول، یادآور سرویس بعدی ایجاد می‌کند.
۶. برای پیام واقعی بله، در بخش اتصال ربات توکن معتبر و chat ID واقعی را وارد کنید. این کار یک درخواست خارجی واقعی ارسال می‌کند.

## ۵. توقف و راه‌اندازی مجدد
در هر پنجره‌ای که سرور اجرا می‌شود `Ctrl+C` بزنید. برای اجرای مجدد همان دستور Uvicorn و Vite را اجرا کنید. پایگاه داده توسعه در `backend/esbot.db` قرار می‌گیرد؛ از آن نسخهٔ پشتیبان بگیرید و آن را عمومی نکنید.
